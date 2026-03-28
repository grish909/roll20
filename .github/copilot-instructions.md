# Project Guidelines

## Code Style

- Files are plain-text Roll20 scripts grouped under `Monsters/`, `NPCs/`, `Spells/`, `Traps/`, `Status/`, and `Other/`.
- Follow the existing filename casing and names in the same directory (most files are lowercase). Keep one action per file (e.g., `init`, `bite`, `FullAttack`).
- Use Unix line endings (LF) and avoid trailing whitespace.

## Architecture

- This repository is a library of Roll20 macro/script snippets organized by category folders. Each file represents a single action or routine to paste or import into Roll20.
- Typical examples: Monsters/Ankheg/init and Monsters/Cyclops/FullAttack.

## Build and Test

- There is no build system or automated tests for this project. Agents should not attempt to run builds.
- Validation steps for changes:
  - Review nearby files in the same folder to match style and naming.
  - Manually paste and smoke-test the script in Roll20 when appropriate.
  - Quick local checks: `git status`, `git diff --name-only HEAD`, or `grep -R "init" Monsters/`.

## Project Conventions

- One action per file; keep files small and focused on a single macro or routine.
- When adding a new monster or NPC, create a directory named after it and include action files (`init`, attack names, etc.).
- Preserve existing patterns and casing in a folder—use neighboring files as the canonical example.

## Integration Points

- Scripts are intended to be used directly in Roll20. There are no external services or CI integrations in this repo.

## Security

- Do not commit API keys, tokens, or other secrets. Keep any credentials out of the repository.

## Contribution & PRs

- Commit messages should be concise: "Add <Monster> <action> script".
- In PR descriptions, mention where the script will be used and any Roll20-specific assumptions.

## Feedback

- If naming/casing is unclear, ask the maintainers before renaming many files.

---

If anything here is unclear or you'd like more detail (examples, lint rules, or a small smoke-test harness), tell me which area to expand.
