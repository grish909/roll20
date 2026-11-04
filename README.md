# roll20

Roll20 macros for a Pathfinder 1e campaign. Each file is one macro, ready to copy and paste into a Roll20 macro or a character's ability (token action).

| Folder | Contents |
| --- | --- |
| `Monsters/` | One folder per creature; every creature has an `init` macro plus its attacks and abilities |
| `NPCs/` | Named NPCs, same layout as monsters |
| `PCs/` | Player-character macros (`<pc>Initiative`, attacks, skills); companions nested in subfolders |
| `Spells/` | Generic spell macros (prompt for caster level/modifiers) |
| `Status/` | Condition reference cards (blinded, confused, …) |
| `Traps/` | Traps and haunts |
| `Other/` | Siege weapons, magic items and other one-offs |

## Setup (once per clone)

You need `python3` 3.11 or newer (macOS: `brew install python`). After cloning, run:

```sh
./setup.sh
```

This creates a local `.venv` with PyYAML (used by `build.py`) and turns on the pre-commit hook. Git doesn't copy hook settings when you clone, so every new clone needs this step. The hook runs the linter and checks that generated macros are up to date, and it blocks the commit if either fails. Skip it for a single commit with `git commit --no-verify`.

On Windows, run `python -m venv .venv`, then `.venv\Scripts\pip install -r requirements.txt`, then `git config core.hooksPath .githooks`.

## Adding a creature

Write the stats once in YAML and generate the macros:

```sh
python3 build.py --new Monsters/Ettin   # creates Monsters/Ettin/stats.yaml from the template
# ...fill in stats.yaml (templates/stats.yaml documents every option)...
python3 build.py Monsters/Ettin         # writes init, attacks, full attacks, poison, SLAs, ...
```

Commit `stats.yaml` along with the macros it generates. To change a creature, edit its `stats.yaml` and rebuild rather than editing the macros. `Monsters/Seugathi`, `Monsters/CrimsonWorm` and `Monsters/Cyclops` are worked examples. Older creatures are hand-written and have no `stats.yaml`.

## Checking your work

Follow the conventions in [`AGENTS.md`](AGENTS.md), then run:

```sh
python3 lint.py                     # lint every macro (no install needed)
python3 lint.py Monsters/NewMonster # one folder
python3 build.py --check            # generated macros match their stats.yaml
```
