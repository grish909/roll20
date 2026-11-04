#!/bin/sh
# One-time setup for a fresh clone: Python venv with PyYAML (for build.py) + git pre-commit hook.
# Safe to re-run. Needs python3 (3.11+).
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install it first (macOS: 'brew install python', or https://www.python.org/downloads/)." >&2
  exit 1
fi

[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
git config core.hooksPath .githooks

echo "Setup done:"
echo "  - .venv created with PyYAML ($(.venv/bin/python -c 'import yaml; print(yaml.__version__)'))"
echo "  - pre-commit hook enabled (runs lint.py and build.py --check)"
echo "Try: python3 build.py --check"
