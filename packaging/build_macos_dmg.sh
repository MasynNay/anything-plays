#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
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
.build-venv/bin/python -m pip install --upgrade pip==26.3
.build-venv/bin/python -m pip install -r requirements-build.txt
# Optional, exact-hash-verified Apple Silicon OpenCV build with FFmpeg disabled.
# Ordinary macOS builds continue to use the pinned, upstream headless wheel.
if [[ -n "${AP_CUSTOM_OPENCV_WHEEL:-}" ]]; then
  : "${AP_CUSTOM_OPENCV_SHA256:?Set SHA-256 for the custom OpenCV wheel}"
  case "$(uname -m)" in
    arm64) CUSTOM_TARGET=macos-arm64 ;;
    x86_64) CUSTOM_TARGET=macos-x86_64 ;;
    *) echo "Unsupported custom OpenCV macOS architecture"; exit 1 ;;
  esac
  "$PYTHON" tools/verify_custom_opencv_wheel.py "$AP_CUSTOM_OPENCV_WHEEL" "$AP_CUSTOM_OPENCV_SHA256" "$CUSTOM_TARGET"
  .build-venv/bin/python -m pip install --force-reinstall --no-deps "$AP_CUSTOM_OPENCV_WHEEL"
  export AP_REQUIRE_OPENCV_FFMPEG_OFF=1
fi
.build-venv/bin/python tools/check_opencv_build.py
# Generate platform icons from the corrected v3.0 source, not the v2.0 PNG.
.build-venv/bin/python tools/render_v21_icon.py
.build-venv/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir --name AnythingPlays --add-data "assets/anything_plays.png:assets" --add-data "assets/anything_plays_v21.webp:assets" app.py
# The testing app deliberately has a separate .app name and bundle identity.
# Do not overwrite a user's installed AnythingPlays.app (the stable 2.0 app).
mv dist/AnythingPlays.app dist/AnythingPlays30Preview.app
# Generate a native macOS icon from the branded PNG.
ICONSET="build/AnythingPlays.iconset"
mkdir -p "$ICONSET"
for SIZE in 16 32 128 256 512; do
  sips -z "$SIZE" "$SIZE" build/v21-icon/anything_plays.png --out "$ICONSET/icon_${SIZE}x${SIZE}.png" >/dev/null
  DOUBLE=$((SIZE * 2))
  sips -z "$DOUBLE" "$DOUBLE" build/v21-icon/anything_plays.png --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o dist/AnythingPlays30Preview.app/Contents/Resources/AnythingPlays.icns
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AnythingPlays.icns" dist/AnythingPlays30Preview.app/Contents/Info.plist
mkdir -p dist/AnythingPlays30Preview.app/Contents/Resources/cores
CORE_LIST=(mgba snes9x)
if [[ "${AP_V30_MINIMAL_CORE_BUILD:-0}" == "1" ]]; then
  CORE_LIST=(mgba)
elif [[ "${AP_V30_TEST_CORES:-0}" == "1" ]]; then
  CORE_LIST+=(fceumm genesis_plus_gx parallel_n64 dolphin stella2014 prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan)
fi
for name in "${CORE_LIST[@]}"; do
  core="cores/${name}_libretro.dylib"
  [[ -f "$core" ]] || { echo "Missing required core: $core"; exit 1; }
  cp "$core" dist/AnythingPlays30Preview.app/Contents/Resources/cores/
done
# Include a hash manifest identifying the exact nightly cores in this build.
cp cores/CORE_PROVENANCE.json dist/AnythingPlays30Preview.app/Contents/Resources/cores/
if [[ "${AP_V30_TEST_CORES:-0}" == "1" ]]; then
  # Dolphin's self-contained core needs compatibility tables under Sys/.
  # Ship them with the signed app; never ask the player to download them.
  [[ -f cores/dolphin-emu/Sys/codehandler.bin ]] || { echo 'Missing Dolphin Sys'; exit 1; }
  cp -R cores/dolphin-emu dist/AnythingPlays30Preview.app/Contents/Resources/cores/
  cp cores/DOLPHIN_SYS_PROVENANCE.json dist/AnythingPlays30Preview.app/Contents/Resources/cores/
fi
# Required for Finder launches: macOS kills camera-using apps without this key.
PLIST="dist/AnythingPlays30Preview.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :NSCameraUsageDescription" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string Anything Plays uses the camera to track moving objects for game controls." "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.anythingplays.test21" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string Anything Plays 3.0 Preview" "$PLIST" || true
# Include project and third-party licensing documentation.
LICENSE_DIR="dist/AnythingPlays30Preview.app/Contents/Resources/licenses"
mkdir -p "$LICENSE_DIR"

cp LICENSE "$LICENSE_DIR/AnythingPlays-MIT.txt"
cp CODE_OF_CONDUCT.md "$LICENSE_DIR/"
cp docs/THIRD_PARTY_NOTICES.md "$LICENSE_DIR/"
cp docs/THIRD_PARTY_COMPONENTS.md "$LICENSE_DIR/"
cp licenses/*.txt "$LICENSE_DIR/"
.build-venv/bin/python tools/collect_python_notices.py "$LICENSE_DIR"

"$PYTHON" verify_bundle.py --check-native macos dist/AnythingPlays30Preview.app
if [[ "${AP_V30_TEST_CORES:-0}" == "1" ]]; then
  .build-venv/bin/python tools/probe_embedded_3d.py macos dist/AnythingPlays30Preview.app
fi
# Sign the outer application only. --deep would mutate nested Libretro dylibs
# after their SHA-256 values were recorded in CORE_PROVENANCE.json.
codesign --force --sign - dist/AnythingPlays30Preview.app
# Verify again after signing; reject even a successfully signed but modified
# bundle instead of shipping a DMG with invalid core provenance.
"$PYTHON" verify_bundle.py --check-native macos dist/AnythingPlays30Preview.app
codesign --verify --verbose=2 dist/AnythingPlays30Preview.app
mkdir -p release
hdiutil create -volname 'Anything Plays 3.0 Preview' -srcfolder dist/AnythingPlays30Preview.app -ov -format UDZO release/AnythingPlays-3.0.0-alpha.1.dmg
# Verify bytes after they have been packaged into the actual distributable DMG.
MOUNT_DIR="$(mktemp -d /tmp/anything-plays-release.XXXXXX)"
trap 'hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1 || true; rmdir "$MOUNT_DIR" >/dev/null 2>&1 || true' EXIT
hdiutil attach -readonly -nobrowse -mountpoint "$MOUNT_DIR" release/AnythingPlays-3.0.0-alpha.1.dmg
"$PYTHON" verify_bundle.py --check-native macos "$MOUNT_DIR/AnythingPlays30Preview.app"
hdiutil detach "$MOUNT_DIR"
rmdir "$MOUNT_DIR"
trap - EXIT
echo 'Created release/AnythingPlays-3.0.0-alpha.1.dmg (unsigned; notarization required for normal public distribution)'
