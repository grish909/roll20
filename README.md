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

## Adding macros

Follow the conventions in [`AGENTS.md`](AGENTS.md), then check your work:

```sh
python3 lint.py                     # whole repo
python3 lint.py Monsters/NewMonster # one folder
```

To run the linter automatically before every commit, enable the bundled hook once per clone:

```sh
git config core.hooksPath .githooks
```
