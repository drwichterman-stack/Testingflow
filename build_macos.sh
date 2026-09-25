#!/usr/bin/env bash
# Build dist/ClinAssess.app with PyInstaller. Run on the Mac, inside the venv.
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest -q
pyinstaller --noconfirm --windowed --name ClinAssess \
  --add-data "clinassess/schema.sql:clinassess" \
  --osx-bundle-identifier org.clinassess.app \
  run_clinassess.py
echo "Built dist/ClinAssess.app"
