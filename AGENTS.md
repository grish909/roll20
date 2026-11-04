# AGENTS.md

Conventions for adding Roll20 macros to this repo.

Whenever you learn a new convention, correction, or pattern while doing this work, add it to this file so future sessions don't have to rediscover it.

## Layout

Each creature/NPC is a folder under `Monsters/`, `NPCs/`, or `PCs/`. One file per macro, no file extension. Filename = macro name, lowerCamelCase, letters and digits only (e.g. `shortSwordFA`, `swallowWhole`, `lanceCharge`, `greataxePA` — no parentheses, underscores or capitals at the start). Creature folder names are PascalCase with no spaces, commas or punctuation (e.g. `CrimsonWorm`, `PurpleWorm`). For comma-separated stat block names, drop the comma: `Giant, Stone` → `GiantStone`, `Hora, Autumn` → `HoraAutumn`.

Every creature folder has an `init` macro. That's the only mandatory file. Exceptions:
- **Variant groups:** a folder can hold one subfolder per variant instead of macros (e.g. `FireElemental/{Tiny,Small,Medium}`, `Inevitables/{Arbiter,Zelekhut,...}`). Each variant subfolder then has its own `init`, and the grouping folder has none.
- **PCs** name their initiative macro `<pc>Initiative` (e.g. `clixInitiative`). Companions nested under a PC (e.g. `PCs/Kage/rubyTiger`) act on the PC's initiative and don't need an `init`.

Renaming on macOS: the filesystem is case-insensitive, so `git mv Init init` (or a plain Finder rename) can leave git tracking the old capitalisation. Rename in two steps: `git mv Init tmp && git mv tmp init`. The linter flags this.

## Generating macros from stats.yaml (preferred for new creatures)

New monsters and NPCs should be written as a `stats.yaml` in the creature folder, not as hand-written macros:

1. `python3 build.py --new Monsters/CreatureName` — copies `templates/stats.yaml` (which documents every option) into the folder.
2. Fill it in from the stat block (see *Sourcing stat blocks*), deleting sections you don't need.
3. `python3 build.py Monsters/CreatureName` — writes the macro files. Commit both `stats.yaml` and the generated macros.

Rules:
- In a folder with `stats.yaml`, every macro comes from it. Never hand-edit a generated macro — change `stats.yaml` and rebuild. Anything that doesn't fit `attacks`/`fullAttacks`/`poison`/`maintain`/`swallowWhole`/`slas`/`spells` goes under `abilities:` as free-form fields.
- `build.py --check` (run by the pre-commit hook) fails if a generated macro is out of date or a folder has a macro that isn't in its `stats.yaml`. It never deletes files — remove stale ones yourself.
- `slas:` is for spell-like abilities (labelled "(SLA)", with a Frequency). `spells:` is for prepared/known class spells (magus, cleric...), with level, prepared count, touch attack and `rays`. Following the buff rule above, only damage- or save-based spells get macros.
- An attack's extra `fields` (e.g. `Cold: "[[1d6]]"` for a frost weapon, energy drain on a slam) are repeated and numbered on every hit in its full attack (`Cold 1`, `Cold 2`).
- Bake the creature's real numbers into its own spell macros (DC, CL, touch bonus) rather than pointing at the generic `Spells/` macros, which prompt for caster level and use other DCs.
- Stat-block bonuses usually already include the creature's own auras or constant buffs (e.g. the nightwing's +2 desecrating aura, *magic fang*); don't add them again. Derive touch bonuses from BAB + Str (melee) / Dex (ranged) + size, plus the same always-on bonuses, and note the arithmetic in a YAML comment.
- `bonus: [11, 6]` lists iteratives. In a full attack, each repeat of a weapon takes the next iterative; repeated natural attacks (2 claws) reuse their single bonus.
- Older creatures are hand-written macros with no `stats.yaml`; leave them unless asked to convert. To convert one, write the `stats.yaml`, rebuild, and diff the output against the old files (whitespace changes are expected; anything else is a mistake in the yaml or a bug in the old macro).
- If a new macro pattern keeps recurring under `abilities:`, add a proper section for it to `build.py` and `templates/stats.yaml`.
- `build.py` needs PyYAML: run `./setup.sh` once per clone. `lint.py` and the hook's lint step need only plain `python3`.

## Macro format

Every macro is a single line. The exception is long descriptive text (status conditions in `Status/`, `rules` cards, spell/ability effect lists), which may break across lines inside a `{{ }}` field:

```
&{template:default} {{name=**<Label>**}} {{**<Field>:**= [[<roll>]]}} ...
```

- `init`: `&{template:default} {{name=**Initiative**}} {{**Roll:**=[[1d20 + N &{tracker}]] }} {{**Modifier:**= +N}}` (use `- N` for negative modifiers).
- Attack macros: `{{**Attack vs AC:**= [[1d20 + N]]}} {{**Damage (<type letters>):**= [[XdY+Z]]}}`. Damage type uses letter codes: B = bludgeoning, P = piercing, S = slashing (combine as needed, e.g. `(B,P,S)`).
- Crit range weapons (19-20, 18-20): use `1d20cs>19 + N` / `1d20cs>18 + N` instead of a plain `1d20` — this flags a critical on the raw die (Roll20's `cs>N` means N or higher, so 18-20 is `cs>18`) without doubling damage automatically (GM doubles manually). Note `(x3)`/`(x4)` in the field label for multiplier weapons but still don't auto-multiply damage.
- Full-attack routines get their own `*FA` or `Full Attack` macro with numbered fields: `Attack 1 vs AC`, `Damage 1`, `Attack 2 vs AC`, `Damage 2`, etc. The single-attack macro (no suffix) always uses the *highest* iterative attack bonus.
- Saves/special abilities with no attack roll still get their own macro, e.g. `{{**Will Save:**= DC18 negates}}`. Only give a dice roll ([[ ]]) where the ability actually deals rollable damage/duration — pure buffs with no save and no roll (mage armor, levitate, haste-type self-buffs) are skipped entirely, they don't get macros.
- Poison: separate `poison` macro — `{{**Save:**= Fort DCn (Con-based)}} {{**Frequency:**=...}} {{**Effect:**= [[dice]] ...}} {{**Cure:**=...}}`. Reference it from the attack macro that delivers it (e.g. `{{**Poison:**= Fort DCn negates}}` on the `bite`/`sting` macro) rather than duplicating the full text there.
- Grab/grapple: include a `Grab: [[1d20 + CMB_grapple]]` field directly on the triggering attack macro, plus a separate `maintain` macro for maintaining the grapple on subsequent rounds.
- Swallow whole: separate `swallowWhole` macro — `{{**Damage (B):**= [[dice]] per round}} {{**Stomach:**= ACn, n hp to cut free}}`.
- Spell-like abilities (SLA): one macro per ability, named after the spell (e.g. `suggestion`, `mindFog`), with `{{**Frequency:**= n/day}} {{**Will/Fort Save:**= DCn ...}} {{**CL:**= nth}}`. Look up the actual spell mechanics (d20pfsrd spell page) rather than guessing — e.g. *mind fog* is Will negates / no further saves if passed / -10 Wis checks & Will saves while in the fog; *phantasmal killer* is Will disbelief then Fortitude partial (3d6 dmg) or death.

- Bold labels must hug their text: `{{**Fire Damage:**=`, not `{{** Fire Damage:*=` (a space after `**` or a lone `*` won't render bold).

## Linting

Run `python3 lint.py` after adding or editing macros (or `python3 lint.py Monsters/NewThing` to check one folder). It must report 0 errors. It checks:
- file/folder naming (lowerCamelCase files, PascalCase folders, no spaces/commas/punctuation), including git-tracked names whose case differs from disk
- every creature folder has an init (with the exceptions above)
- macros start with `&{template:` and all `{ }` / `[ ]` pairs balance — a missing `]` silently breaks the roll in Roll20
- `**` bold markup in field labels is balanced and has no leading space
- `init` matches the standard template and the roll modifier equals the displayed one
- `xFA` Attack 1 bonus equals the single-attack macro `x`
- poison DCs quoted on attack macros match the folder's `poison` macro

A pre-commit hook (`.githooks/pre-commit`) runs the linter and `build.py --check` automatically and blocks the commit on errors. `./setup.sh` enables it (once per clone).

When a new convention is added here, add a matching check to `lint.py` if it can be checked mechanically.

- Inline rolls (`[[ ]]`) may contain only dice math and `?{}` queries — put situational notes like "+3 if metal armour" in their own field, e.g. `{{**Metal Armour:**= +3 to attack vs targets in metal armour}}`.

## Sourcing stat blocks

Pull stats from d20pfsrd via WebFetch. The first fetch summarizes — always do a second, narrower fetch to pull the verbatim **Special Abilities** text block (poison, auras, swallow whole, etc.), since the header stat block alone often omits full mechanics/DCs. Cross-check attack bonus/CMB arithmetic (BAB + Str mod + size mod + weapon focus) against the stated totals as a sanity check before writing macros — the fetch summarizer occasionally garbles a number (e.g. splitting `+12` into `+6+12`).

## Reference examples already in the repo

- `Allip`, `Bodak`, `Gug`, `DenizenOfLeng` — minimal attack-only creatures.
- `Seugathi`, `CrimsonWorm`, `Cyclops` — built from `stats.yaml`; copy these when writing a new one.
- `VampireLord` — `stats.yaml` with prepared `spells:` (rays, touch spells with spellstrike notes), weapon extra damage carried into the full attack, vampire abilities.
- `Nightwing` — `stats.yaml` with a large `slas:` set, aura, channel energy. `Sellsword` — fighter with Power Attack and Vital Strike variants. `DreadWraith` — minimal incorporeal touch.
- `GenieMarid`, `Cyclops` — single attack + full-attack (`*FA`) pairing, crit-range weapon syntax.
- `Devourer` — special attack with no roll, text-only effect field.
- `Tendriculos`, `FormlessSpawn`, `SnakeConstrictorGiantAnaconda`, `JellyTar` — grab/maintain/swallow/constrict patterns.
- `Seugathi` — full SLA set (at-will/n-per-day abilities with Will DCs), aura, poison, confusion-table special attack.
- `CrimsonWorm`, `PurpleWorm` — grab + swallow-whole worm pattern, paired CR12/CR13 variants.
