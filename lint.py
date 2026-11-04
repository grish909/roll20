#!/usr/bin/env python3
"""Lint the Roll20 macro repo against the conventions in AGENTS.md.

Usage: python3 lint.py            # lint everything
       python3 lint.py PATH...    # lint only these files/folders

Exits non-zero if any errors are found.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MACRO_DIRS = ["Monsters", "NPCs", "PCs", "Spells", "Status", "Traps", "Other"]
CREATURE_DIRS = ["Monsters", "NPCs", "PCs"]
FILE_NAME_RE = re.compile(r"^[a-z][A-Za-z0-9]*$")    # lowerCamelCase
DIR_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")    # PascalCase (or lowerCamelCase companions)

INIT_RE = re.compile(
    r"^&\{template:default\} \{\{name=\*\*Initiative\*\*\}\} "
    r"\{\{\*\*Roll:\*\*=\[\[1d20 ([+-]) (\d+) &\{tracker\}\]\] \}\} "
    r"\{\{\*\*Modifier:\*\*= ([+-])(\d+)\}\}$"
)
ATTACK_BONUS_RE = re.compile(r"Attack[^=]*?vs[^=]*=\s*\[\[1d20(?:cs>\d+)?\s*([+-])\s*(\d+)")
DC_RE = re.compile(r"DC\s*(\d+)")

errors = []


def err(path, msg):
    errors.append(f"{path}: {msg}")


def check_brackets(rel, text):
    """Every {, [ must be closed in order. Markdown links `[ ](url)` are balanced too."""
    pairs = {"}": "{", "]": "["}
    stack = []
    for i, ch in enumerate(text):
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if not stack or stack[-1] != pairs[ch]:
                err(rel, f"unmatched '{ch}' at char {i}")
                return
            stack.pop()
    if stack:
        err(rel, f"unclosed '{stack[-1]}'")


def check_macro(path):
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    body = text.strip()

    if not body:
        err(rel, "empty macro")
        return
    if not body.startswith("&{template:"):
        err(rel, "does not start with '&{template:'")

    check_brackets(rel, body)

    # Each {{...}} field: bold markers must pair up, and bold must hug its text.
    for field in re.findall(r"\{\{(.*?)\}\}", body, re.S):
        label = field.split("=", 1)[0]
        if label.count("**") % 2:
            err(rel, f"unbalanced '**' in field label {label.strip()!r}")
        if re.match(r"\s*\*\*\s", label):
            err(rel, f"space after opening '**' in {label.strip()!r} (won't render bold)")
        if re.match(r"\s*\*[^*]", label):
            err(rel, f"single '*' around label {label.strip()!r} renders italic; use '**' for bold")

    if path.name == "init":
        m = INIT_RE.match(body)
        if not m:
            err(rel, "init does not match the standard init template")
        elif (m.group(1), m.group(2)) != (m.group(3), m.group(4)):
            err(rel, f"roll modifier {m.group(1)}{m.group(2)} != displayed modifier {m.group(3)}{m.group(4)}")


def first_attack_bonus(path):
    m = ATTACK_BONUS_RE.search(path.read_text(encoding="utf-8"))
    return int(m.group(2)) * (-1 if m.group(1) == "-" else 1) if m else None


def check_creature(folder):
    """Folder-level checks for a creature folder (one that directly holds macros)."""
    rel = folder.relative_to(ROOT)
    files = {p.name: p for p in folder.iterdir() if p.is_file() and p.name != "stats.yaml"}

    has_init = "init" in files or any(n.endswith("Initiative") for n in files)
    # Companions nested under a PC (e.g. PCs/Kage/rubyTiger) act on the PC's initiative.
    is_companion = rel.parts[0] == "PCs" and len(rel.parts) > 2
    if not has_init and not is_companion:
        err(rel, "creature folder has no 'init' macro")

    # Single attack macro should use the highest iterative = Attack 1 of its FA.
    for name, p in files.items():
        if name.endswith("FA") and name[:-2] in files:
            fa, single = first_attack_bonus(p), first_attack_bonus(files[name[:-2]])
            if fa is not None and single is not None and fa != single:
                err(rel, f"{name} Attack 1 is +{fa} but {name[:-2]} is +{single}")

    # Poison DC quoted on attack macros should match the poison macro.
    if "poison" in files:
        m = DC_RE.search(files["poison"].read_text(encoding="utf-8"))
        if m:
            dc = m.group(1)
            for name, p in files.items():
                if name == "poison":
                    continue
                for field in re.findall(r"\{\{([^}]*Poison[^}]*)\}\}", p.read_text(encoding="utf-8")):
                    for other in DC_RE.findall(field):
                        if other != dc:
                            err(rel / name, f"poison DC{other} doesn't match poison macro DC{dc}")


def check_git_case(files):
    """macOS is case-insensitive, so a rename like Init -> init can look done on disk
    while git still tracks the old name. Compare git's names against the convention."""
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return
    on_disk = {str(p.relative_to(ROOT)) for p in files}
    for tracked in out.splitlines():
        if tracked not in on_disk and tracked.lower() in {f.lower() for f in on_disk}:
            err(tracked, "git tracks this name with different case than the file on disk "
                         "(fix with: git mv OLD tmp && git mv tmp NEW)")


def iter_targets(args):
    if not args:
        for d in MACRO_DIRS:
            if (ROOT / d).is_dir():
                yield ROOT / d
        return
    for a in args:
        yield Path(a).resolve()


def main():
    files, folders = set(), set()
    for target in iter_targets(sys.argv[1:]):
        paths = [target] + (list(target.rglob("*")) if target.is_dir() else [])
        for p in paths:
            rel = p.relative_to(ROOT)
            if any(part.startswith(".") for part in rel.parts) or p.name == "stats.yaml":
                continue  # stats.yaml is build.py's input, not a macro
            if p.is_file():
                if not FILE_NAME_RE.match(p.name):
                    err(rel, "macro filename should be lowerCamelCase with no extension")
            elif not DIR_NAME_RE.match(p.name):
                err(rel, "folder name should be PascalCase (no spaces, commas or punctuation)")
            if p.is_file():
                files.add(p)
                if rel.parts[0] in CREATURE_DIRS and len(rel.parts) >= 3:
                    folders.add(p.parent)

    check_git_case(files)
    for p in sorted(files):
        check_macro(p)
    for f in sorted(folders):
        check_creature(f)

    for e in errors:
        print(f"error: {e}")
    print(f"{len(files)} macros checked, {len(errors)} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
