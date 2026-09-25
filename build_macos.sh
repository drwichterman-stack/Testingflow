#!/usr/bin/env bash
# Build ClinAssess.app and a distributable ClinAssess-<version>.dmg.
# Run on a Mac, inside the project's virtual environment:
#   source .venv/bin/activate && pip install -r requirements-dev.txt && ./build_macos.sh
#
# Optional signing and notarization (required for smooth installs by customers):
#   export SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
#   export NOTARY_PROFILE="clinassess-notary"   # created with: xcrun notarytool store-credentials
set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(python -c "from clinassess import config; print(config.APP_VERSION)")
APP="dist/ClinAssess.app"
DMG="dist/ClinAssess-${VERSION}.dmg"

echo "== 1. Tests"
python -m pytest -q

echo "== 1b. Third-party license texts"
cp THIRD_PARTY_NOTICES.txt build_notices.tmp
pip-licenses --format=plain-vertical --with-license-file --no-license-path \
  --packages PySide6 PySide6-Essentials PySide6-Addons shiboken6 cryptography reportlab pypdf \
  numpy pillow \
  pyobjc-core pyobjc-framework-Speech pyobjc-framework-AVFoundation >> build_notices.tmp || true
mkdir -p build && mv build_notices.tmp build/THIRD_PARTY_NOTICES.txt

echo "== 2. App icon"
rm -rf build/icon.iconset && mkdir -p build/icon.iconset
QT_QPA_PLATFORM=offscreen python - <<'PY'
from PySide6.QtWidgets import QApplication
app = QApplication([])
from clinassess.ui.branding import logo_pixmap
for s in (16, 32, 128, 256, 512):
    logo_pixmap(s).save(f"build/icon.iconset/icon_{s}x{s}.png")
    logo_pixmap(s * 2).save(f"build/icon.iconset/icon_{s}x{s}@2x.png")
PY
iconutil -c icns build/icon.iconset -o build/ClinAssess.icns

echo "== 3. Bundle (network modules excluded)"
pyinstaller --noconfirm --clean --windowed --name ClinAssess \
  --icon build/ClinAssess.icns \
  --osx-bundle-identifier org.clinassess.app \
  --add-data "clinassess/schema.sql:clinassess" \
  --add-data "docs:docs" \
  --add-data "README.md:." \
  --add-data "LICENSE.txt:." \
  --add-data "build/THIRD_PARTY_NOTICES.txt:." \
  --exclude-module PySide6.QtNetwork \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module PySide6.QtWebSockets \
  --exclude-module tkinter \
  run_clinassess.py

echo "== 4. Info.plist privacy strings (required for dictation and camera capture)"
PL="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'ClinAssess uses the microphone only while you dictate notes. Audio is processed on this Mac and never saved or sent anywhere.'" "$PL" || true
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string 'ClinAssess uses the camera only while you capture a completed paper form. Photos are read on this Mac, never saved, and never sent anywhere.'" "$PL" || true
/usr/libexec/PlistBuddy -c "Add :NSSpeechRecognitionUsageDescription string 'Dictation is transcribed on this Mac using on-device speech recognition. Nothing is sent to Apple or any server.'" "$PL" || true
/usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$PL" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PL"
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 13.0" "$PL" || true

if [[ -n "${SIGN_IDENTITY:-}" ]]; then
  echo "== 5. Code signing (hardened runtime)"
  cat > build/entitlements.plist <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>com.apple.security.device.audio-input</key><true/>
  <key>com.apple.security.device.camera</key><true/>
</dict></plist>
XML
  codesign --deep --force --options runtime --timestamp \
    --entitlements build/entitlements.plist --sign "$SIGN_IDENTITY" "$APP"
  codesign --verify --deep --strict "$APP"
fi

echo "== 6. Disk image"
STAGE=build/dmg && rm -rf "$STAGE" && mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp LICENSE.txt "$STAGE/License Agreement.txt"
cp README.md "$STAGE/README.md"
cp docs/GETTING_STARTED.md "$STAGE/Quick Start Guide.md"
cp build/THIRD_PARTY_NOTICES.txt "$STAGE/Third-Party Notices.txt"
rm -f "$DMG"
hdiutil create -volname "ClinAssess $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DMG"

if [[ -n "${SIGN_IDENTITY:-}" && -n "${NOTARY_PROFILE:-}" ]]; then
  echo "== 7. Notarization"
  codesign --sign "$SIGN_IDENTITY" --timestamp "$DMG"
  xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
fi

shasum -a 256 "$DMG"
echo "Built $DMG"
