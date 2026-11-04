#!/usr/bin/env python3
"""Generate Roll20 macros from a creature's stats.yaml.

Usage:
  python3 build.py                     # build every stats.yaml in the repo
  python3 build.py Monsters/Seugathi   # build one creature
  python3 build.py --check             # exit 1 if any generated macro is out of date
  python3 build.py --new Monsters/Foo  # start a new creature from the template

The schema is documented in templates/stats.yaml. Generated macros are normal
files that get committed, so Roll20 copy-paste works without any of this.
"""
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
STATS = "stats.yaml"
TEMPLATE = ROOT / "templates" / STATS
CREATURE_DIRS = ["Monsters", "NPCs", "PCs"]

try:
    import yaml
except ImportError:
    # Fall back to the project venv created by setup.sh, so `python3 build.py` just works.
    # (Compare sys.prefix, not the executable: the venv's python is a symlink to the system one.)
    if VENV_PY.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        os.execv(str(VENV_PY), [str(VENV_PY), __file__, *sys.argv[1:]])
    sys.exit("build.py needs PyYAML. Run ./setup.sh once (see README), then try again.")


class StatsError(Exception):
    pass


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def macro(name, fields):
    """Render a default-template macro. `fields` is a list of (label, value)."""
    parts = [f"&{{template:default}} {{{{name=**{name}**}}}}"]
    parts += [f"{{{{**{label}:**= {value}}}}}" for label, value in fields]
    return " ".join(parts)


def signed(n):
    return f"+ {n}" if n >= 0 else f"- {-n}"


def title(key):
    """shortSword -> Short Sword"""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key).split(" ")
    small = {"of", "the", "and", "a", "an", "to", "in", "on", "for"}
    out = []
    for i, w in enumerate(words):
        out.append(w.lower() if i and w.lower() in small else w[:1].upper() + w[1:])
    return " ".join(out)


def roll(expr):
    return f"[[{expr}]]"


def check_keys(where, spec, allowed, required=()):
    if not isinstance(spec, dict):
        raise StatsError(f"{where}: expected a mapping, got {spec!r}")
    unknown = set(spec) - set(allowed)
    if unknown:
        raise StatsError(f"{where}: unknown key(s) {', '.join(sorted(unknown))}; allowed: {', '.join(allowed)}")
    missing = [k for k in required if k not in spec]
    if missing:
        raise StatsError(f"{where}: missing required key(s) {', '.join(missing)}")


def extra_fields(spec):
    return [(str(k), str(v)) for k, v in (spec.get("fields") or {}).items()]


def save_field(text):
    """'Will DC17 negates' -> ('Will Save', 'DC17 negates')"""
    m = re.match(r"(Fort(?:itude)?|Ref(?:lex)?|Will)\s+(.*)", str(text))
    return (f"{m.group(1)} Save", m.group(2)) if m else ("Save", str(text))


# ---------------------------------------------------------------------------
# Macro builders
# ---------------------------------------------------------------------------

ATTACK_KEYS = ["label", "bonus", "damage", "type", "crit", "multiplier", "vs", "poison", "grab", "fields"]


def attack_roll(atk, bonus):
    die = f"1d20cs>{atk['crit']}" if atk.get("crit") else "1d20"
    return roll(f"{die} {signed(bonus)}")


def attack_labels(atk, n=None, show_name=False):
    num = f" {n}" if n else ""
    name = f" ({atk['label']})" if show_name else ""
    mult = f" (x{atk['multiplier']})" if atk.get("multiplier") else ""
    dtype = f" ({atk['type']})" if atk.get("type") else ""
    return f"Attack{num}{name} vs {atk.get('vs', 'AC')}{mult}", f"Damage{num}{dtype}"


def poison_ref(stats):
    p = stats.get("poison")
    if not p:
        raise StatsError("an attack has `poison: true` but there is no `poison:` section")
    return f"{p.get('save', 'Fort')} DC{p['dc']}"


def grab_roll(stats):
    if "cmb" not in stats:
        raise StatsError("an attack has `grab: true` but there is no top-level `cmb:`")
    return roll(f"1d20 {signed(stats['cmb'])}")


def build_attack(key, atk, stats):
    atk_label, dmg_label = attack_labels(atk)
    fields = [(atk_label, attack_roll(atk, atk["bonuses"][0])), (dmg_label, roll(atk["damage"]))]
    if atk.get("grab"):
        fields.append(("Grab", grab_roll(stats)))
    if atk.get("poison"):
        fields.append(("Poison", f"{poison_ref(stats)} negates"))
    return macro(atk["label"], fields + extra_fields(atk))


def numbered(label, n):
    """'Cold' -> 'Cold 3'; 'Con Drain (Fort DC23)' -> 'Con Drain 3 (Fort DC23)'"""
    head, sep, tail = label.partition(" (")
    return f"{head} {n}{sep}{tail}"


def build_full_attack(key, spec, stats):
    if isinstance(spec, list):
        spec = {"attacks": spec}
    check_keys(f"fullAttacks.{key}", spec, ["label", "attacks", "modifier", "fields"], ["attacks"])
    attacks = stats.get("attacks") or {}
    for a in spec["attacks"]:
        if a not in attacks:
            raise StatsError(f"fullAttacks.{key}: unknown attack {a!r}")
    show_name = len(set(spec["attacks"])) > 1
    seen, fields, poisoned = {}, [], []
    for n, a in enumerate(spec["attacks"], 1):
        atk = attacks[a]
        i = seen.get(a, 0)
        seen[a] = i + 1
        bonus = atk["bonuses"][min(i, len(atk["bonuses"]) - 1)]  # iteratives in order; natural attacks repeat
        bonus += spec.get("modifier", 0)  # e.g. -2 for spell combat / two-weapon fighting
        atk_label, dmg_label = attack_labels(atk, n, show_name)
        fields += [(atk_label, attack_roll(atk, bonus)), (dmg_label, roll(atk["damage"]))]
        if atk.get("grab"):
            fields.append((f"Grab {n}", grab_roll(stats)))
        # Per-attack extras (e.g. "Cold: [[1d6]]") apply on every hit, so number them too.
        fields += [(numbered(label, n), value) for label, value in extra_fields(atk)]
        if atk.get("poison") and a not in poisoned:
            poisoned.append(a)
    for a in poisoned:
        fields.append((f"Poison ({poison_ref(stats)})", f"On {attacks[a]['label'].lower()} hit"))
    return macro(spec.get("label", "Full Attack"), fields + extra_fields(spec))


def build_poison(spec, stats):
    check_keys("poison", spec, ["label", "dc", "save", "basis", "frequency", "effect", "cure", "fields"],
               ["dc", "frequency", "effect", "cure"])
    fields = [("Save", f"{spec.get('save', 'Fort')} DC{spec['dc']} ({spec.get('basis', 'Con')}-based)"),
              ("Frequency", spec["frequency"]), ("Effect", spec["effect"]), ("Cure", spec["cure"])]
    return macro(spec.get("label", "Poison (Ex)"), fields + extra_fields(spec))


def build_maintain(spec, stats):
    spec = {} if spec is True else spec
    check_keys("maintain", spec, ["label", "note", "fields"])
    if "cmb" not in stats:
        raise StatsError("`maintain` needs a top-level `cmb:`")
    fields = [("Grapple", roll(f"1d20 {signed(stats['cmb'])}"))]
    if spec.get("note"):
        fields.append(("Note", spec["note"]))
    return macro(spec.get("label", "Maintain Grapple"), fields + extra_fields(spec))


def build_swallow(spec, stats):
    check_keys("swallowWhole", spec, ["label", "damage", "type", "ac", "hp", "fields"], ["damage", "ac", "hp"])
    dtype = f" ({spec['type']})" if spec.get("type") else ""
    fields = [(f"Damage{dtype}", f"{roll(spec['damage'])} per round"),
              ("Stomach", f"AC{spec['ac']}, {spec['hp']} hp to cut free")]
    return macro(spec.get("label", "Swallow Whole"), fields + extra_fields(spec))


def build_sla(key, spec, stats):
    check_keys(f"slas.{key}", spec, ["label", "frequency", "save", "cl", "fields"], ["frequency"])
    cl = spec.get("cl", stats.get("cl"))
    if cl is None:
        raise StatsError(f"slas.{key}: no caster level (set top-level `cl:` or `cl:` on the SLA)")
    fields = [("Frequency", spec["frequency"])]
    if spec.get("save"):
        fields.append(save_field(spec["save"]))
    fields += extra_fields(spec)
    fields.append(("CL", ordinal(cl)))
    return macro(spec.get("label", f"{title(key)} (SLA)"), fields)


SPELL_KEYS = ["label", "level", "prepared", "attack", "vs", "rays", "damage", "type", "save", "cl", "fields"]


def build_spell(key, spec, stats):
    """A prepared/known spell (not an SLA): optional touch attack(s), damage, save, CL."""
    check_keys(f"spells.{key}", spec, SPELL_KEYS)
    cl = spec.get("cl", stats.get("cl"))
    if cl is None:
        raise StatsError(f"spells.{key}: no caster level (set top-level `cl:` or `cl:` on the spell)")
    if "rays" in spec and "attack" not in spec:
        raise StatsError(f"spells.{key}: `rays` needs an `attack` bonus")
    fields = []
    if spec.get("level") is not None or spec.get("prepared"):
        lvl = "" if spec.get("level") is None else "Cantrip" if spec["level"] == 0 else f"Level {spec['level']}"
        prep = f"prepared x{spec['prepared']}" if spec.get("prepared") else ""
        fields.append(("Spell", ", ".join(x for x in (lvl, prep) if x)))
    dtype = f" ({spec['type']})" if spec.get("type") else ""
    vs = spec.get("vs", "Touch")
    rays = spec.get("rays", 1)
    if "attack" in spec:
        for n in range(1, rays + 1):
            num = f" {n}" if rays > 1 else ""
            fields.append((f"{'Ray' if rays > 1 else 'Attack'}{num} vs {vs}", roll(f"1d20 {signed(spec['attack'])}")))
            if spec.get("damage"):
                fields.append((f"Damage{num}{dtype}", roll(spec["damage"])))
    elif spec.get("damage"):
        fields.append((f"Damage{dtype}", roll(spec["damage"])))
    if spec.get("save"):
        fields.append(save_field(spec["save"]))
    fields += extra_fields(spec)
    fields.append(("CL", ordinal(cl)))
    return macro(spec.get("label", title(key)), fields)


def build_ability(key, spec, stats):
    check_keys(f"abilities.{key}", spec, ["label", "fields"], ["fields"])
    return macro(spec.get("label", title(key)), extra_fields(spec))


def build_init(n):
    sign = "+" if n >= 0 else "-"
    return (f"&{{template:default}} {{{{name=**Initiative**}}}} "
            f"{{{{**Roll:**=[[1d20 {signed(n)} &{{tracker}}]] }}}} {{{{**Modifier:**= {sign}{abs(n)}}}}}")


def ordinal(n):
    if isinstance(n, str):
        return n
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# Creature
# ---------------------------------------------------------------------------

TOP_KEYS = ["source", "init", "cmb", "cl", "attacks", "fullAttacks", "poison", "maintain",
            "swallowWhole", "slas", "spells", "abilities"]


def build_creature(stats):
    """Return {filename: macro text} for one stats.yaml."""
    check_keys("stats.yaml", stats, TOP_KEYS, ["init"])
    out = {}

    def add(name, text):
        if name in out:
            raise StatsError(f"two macros would both be named {name!r}; rename one of the keys")
        out[name] = text

    add("init", build_init(stats["init"]))

    attacks = stats.get("attacks") or {}
    for key, atk in attacks.items():
        check_keys(f"attacks.{key}", atk, ATTACK_KEYS, ["bonus", "damage"])
        atk.setdefault("label", title(key))
        atk["bonuses"] = atk["bonus"] if isinstance(atk["bonus"], list) else [atk["bonus"]]
        add(key, build_attack(key, atk, stats))
    for key, spec in (stats.get("fullAttacks") or {}).items():
        add(key, build_full_attack(key, spec, stats))
    if stats.get("poison"):
        add("poison", build_poison(stats["poison"], stats))
    if stats.get("maintain"):
        add("maintain", build_maintain(stats["maintain"], stats))
    if stats.get("swallowWhole"):
        add("swallowWhole", build_swallow(stats["swallowWhole"], stats))
    for key, spec in (stats.get("slas") or {}).items():
        add(key, build_sla(key, spec, stats))
    for key, spec in (stats.get("spells") or {}).items():
        add(key, build_spell(key, spec, stats))
    for key, spec in (stats.get("abilities") or {}).items():
        add(key, build_ability(key, spec, stats))

    for name in out:
        if not re.match(r"^[a-z][A-Za-z0-9]*$", name):
            raise StatsError(f"macro name {name!r} must be lowerCamelCase letters/digits")
    return out


def find_stats(args):
    if not args:
        for d in CREATURE_DIRS:
            yield from sorted((ROOT / d).rglob(STATS))
        return
    for a in args:
        p = Path(a).resolve()
        p = p / STATS if p.is_dir() else p
        if not p.exists():
            sys.exit(f"no {STATS} at {p.relative_to(ROOT)}")
        yield p


def new_creature(folder):
    folder = Path(folder).resolve()
    target = folder / STATS
    if target.exists():
        sys.exit(f"{target.relative_to(ROOT)} already exists")
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(TEMPLATE, target)
    print(f"created {target.relative_to(ROOT)} — fill it in, then run: python3 build.py {folder.relative_to(ROOT)}")


def main():
    args = sys.argv[1:]
    if args[:1] == ["--new"]:
        if len(args) != 2:
            sys.exit("usage: build.py --new Monsters/CreatureName")
        return new_creature(args[1])
    check = "--check" in args
    args = [a for a in args if a != "--check"]

    problems, written = [], 0
    for path in find_stats(args):
        folder = path.parent
        rel = folder.relative_to(ROOT)
        try:
            macros = build_creature(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        except (StatsError, yaml.YAMLError) as e:
            problems.append(f"{rel}/{STATS}: {e}")
            continue

        for name, text in macros.items():
            f = folder / name
            current = f.read_text(encoding="utf-8") if f.exists() else None
            if current == text:
                continue
            if check:
                problems.append(f"{rel}/{name}: out of date (run: python3 build.py {rel})")
            else:
                f.write_text(text, encoding="utf-8")
                written += 1
                print(f"{'updated' if current is not None else 'created'} {rel}/{name}")

        # Every macro in a stats.yaml folder should come from stats.yaml, otherwise edits get lost.
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.name != STATS and f.name not in macros:
                problems.append(f"{rel}/{f.name}: not produced by {STATS} — add it (e.g. under "
                                f"`abilities:`) or delete the file")

    for p in problems:
        print(f"error: {p}")
    if check:
        if not problems:
            print("generated macros up to date")
    else:
        print(f"{written} macro(s) written")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
