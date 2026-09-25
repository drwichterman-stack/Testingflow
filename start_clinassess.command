#!/bin/bash
# Double-click this file in Finder to start ClinAssess.
# First run: creates a private Python environment in this folder (.venv)
# and installs the required libraries (needs internet once, a few minutes).
# Later runs start the app directly and work fully offline.
cd "$(dirname "$0")" || exit 1

PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.11 or newer is required. Install it from https://www.python.org/downloads/macos/ and run this again."
  read -r -p "Press Return to close." _
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "First-time setup: installing ClinAssess libraries. This takes a few minutes."
  "$PY" -m venv .venv || exit 1
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  if ! .venv/bin/python -m pip install -r requirements.txt; then
    rm -rf .venv
    echo "Setup failed. Check the internet connection and run this again."
    read -r -p "Press Return to close." _
    exit 1
  fi
fi

exec .venv/bin/python -m clinassess
