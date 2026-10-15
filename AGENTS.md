# AGENTS.md

Conventions for adding Roll20 macros to this repo.

Whenever you learn a new convention, correction, or pattern while doing this work, add it to this file so future sessions don't have to rediscover it.

## Layout

Each creature/NPC is a folder under `Monsters/`, `NPCs/`, or `PCs/`. One file per macro, no file extension. Filename = macro name, lowerCamelCase (e.g. `shortSwordFA`, `swallowWhole`). Multi-word creature folder names are PascalCase with no spaces (e.g. `CrimsonWorm`, `PurpleWorm`), except where the source stat block uses a comma-separated proper name (e.g. `Giant, Stone`, `Hora, Autumn`).

Every creature folder has an `init` macro. That's the only mandatory file.

## Macro format

Every macro is a single line:

```
&{template:default} {{name=**<Label>**}} {{**<Field>:**= [[<roll>]]}} ...
```

- `init`: `&{template:default} {{name=**Initiative**}} {{**Roll:**=[[1d20 + N &{tracker}]] }} {{**Modifier:**= +N}}` (use `- N` for negative modifiers).
- Attack macros: `{{**Attack vs AC:**= [[1d20 + N]]}} {{**Damage (<type letters>):**= [[XdY+Z]]}}`. Damage type uses letter codes: B = bludgeoning, P = piercing, S = slashing (combine as needed, e.g. `(B,P,S)`).
- Crit range weapons (19-20, 18-20): use `1d20cs>19 + N` / `1d20cs>17 + N` instead of a plain `1d20` — this flags a critical on the raw die without doubling damage automatically (GM doubles manually). Note `(x3)`/`(x4)` in the field label for multiplier weapons but still don't auto-multiply damage.
- Full-attack routines get their own `*FA` or `Full Attack` macro with numbered fields: `Attack 1 vs AC`, `Damage 1`, `Attack 2 vs AC`, `Damage 2`, etc. The single-attack macro (no suffix) always uses the *highest* iterative attack bonus.
- Saves/special abilities with no attack roll still get their own macro, e.g. `{{**Will Save:**= DC18 negates}}`. Only give a dice roll ([[ ]]) where the ability actually deals rollable damage/duration — pure buffs with no save and no roll (mage armor, levitate, haste-type self-buffs) are skipped entirely, they don't get macros.
- Poison: separate `poison` macro — `{{**Save:**= Fort DCn (Con-based)}} {{**Frequency:**=...}} {{**Effect:**= [[dice]] ...}} {{**Cure:**=...}}`. Reference it from the attack macro that delivers it (e.g. `{{**Poison:**= Fort DCn negates}}` on the `bite`/`sting` macro) rather than duplicating the full text there.
- Grab/grapple: include a `Grab: [[1d20 + CMB_grapple]]` field directly on the triggering attack macro, plus a separate `maintain` macro for maintaining the grapple on subsequent rounds.
- Swallow whole: separate `swallowWhole` macro — `{{**Damage (B):**= [[dice]] per round}} {{**Stomach:**= ACn, n hp to cut free}}`.
- Spell-like abilities (SLA): one macro per ability, named after the spell (e.g. `suggestion`, `mindFog`), with `{{**Frequency:**= n/day}} {{**Will/Fort Save:**= DCn ...}} {{**CL:**= nth}}`. Look up the actual spell mechanics (d20pfsrd spell page) rather than guessing — e.g. *mind fog* is Will negates / no further saves if passed / -10 Wis checks & Will saves while in the fog; *phantasmal killer* is Will disbelief then Fortitude partial (3d6 dmg) or death.

## Sourcing stat blocks

Pull stats from d20pfsrd via WebFetch. The first fetch summarizes — always do a second, narrower fetch to pull the verbatim **Special Abilities** text block (poison, auras, swallow whole, etc.), since the header stat block alone often omits full mechanics/DCs. Cross-check attack bonus/CMB arithmetic (BAB + Str mod + size mod + weapon focus) against the stated totals as a sanity check before writing macros — the fetch summarizer occasionally garbles a number (e.g. splitting `+12` into `+6+12`).

## Reference examples already in the repo

- `Allip`, `Bodak`, `Gug`, `DenizenOfLeng` — minimal attack-only creatures.
- `GenieMarid`, `Cyclops` — single attack + full-attack (`*FA`) pairing, crit-range weapon syntax.
- `Devourer` — special attack with no roll, text-only effect field.
- `Tendriculos`, `FormlessSpawn`, `SnakeConstrictorGiantAnaconda`, `JellyTar` — grab/maintain/swallow/constrict patterns.
- `Seugathi` — full SLA set (at-will/n-per-day abilities with Will DCs), aura, poison, confusion-table special attack.
- `CrimsonWorm`, `PurpleWorm` — grab + swallow-whole worm pattern, paired CR12/CR13 variants.
