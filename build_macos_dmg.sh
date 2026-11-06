#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Prefer modern Homebrew Python/Tk on Apple Silicon; avoid system Tk 8.5.
if [[ -x /opt/homebrew/bin/python3.13 ]]; then
  PYTHON=/opt/homebrew/bin/python3.13
elif [[ -x /usr/local/bin/python3.13 ]]; then
  PYTHON=/usr/local/bin/python3.13
else
  PYTHON="$(command -v python3)"
fi
"$PYTHON" -c 'import tkinter; assert tkinter.TkVersion >= 8.6, "Python requires Tk 8.6 or newer"' || { echo 'Install modern Python with Tkinter before building.'; exit 1; }
"$PYTHON" fetch_mgba_core.py
rm -rf .build-venv
"$PYTHON" -m venv .build-venv
.build-venv/bin/python -m pip install --upgrade pip
.build-venv/bin/python -m pip install -r requirements.txt pyinstaller
.build-venv/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir --name AnythingPlays --add-data "assets/anything_plays.png:assets" app.py
# Generate a native macOS icon from the branded PNG.
ICONSET="build/AnythingPlays.iconset"
mkdir -p "$ICONSET"
for SIZE in 16 32 128 256 512; do
  sips -z "$SIZE" "$SIZE" assets/anything_plays.png --out "$ICONSET/icon_${SIZE}x${SIZE}.png" >/dev/null
  DOUBLE=$((SIZE * 2))
  sips -z "$DOUBLE" "$DOUBLE" assets/anything_plays.png --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o dist/AnythingPlays.app/Contents/Resources/AnythingPlays.icns
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AnythingPlays.icns" dist/AnythingPlays.app/Contents/Info.plist
mkdir -p dist/AnythingPlays.app/Contents/MacOS/cores
for name in gambatte mgba snes9x; do
  core="cores/${name}_libretro.dylib"
  [[ -f "$core" ]] || { echo "Missing required core: $core"; exit 1; }
  cp "$core" dist/AnythingPlays.app/Contents/MacOS/cores/
done
# Include a hash manifest identifying the exact nightly cores in this build.
cp cores/CORE_PROVENANCE.json dist/AnythingPlays.app/Contents/MacOS/cores/
# Required for Finder launches: macOS kills camera-using apps without this key.
PLIST="dist/AnythingPlays.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :NSCameraUsageDescription" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string Anything Plays uses the camera to track moving objects for game controls." "$PLIST"
codesign --force --deep --sign - dist/AnythingPlays.app
mkdir -p release
hdiutil create -volname 'Anything Plays' -srcfolder dist/AnythingPlays.app -ov -format UDZO release/AnythingPlays.dmg
echo 'Created release/AnythingPlays.dmg (unsigned; notarization required for normal public distribution)'
