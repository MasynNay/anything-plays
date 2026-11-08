#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Stable builds are allowed only with independently approved source/rights,
# four-platform real-device acceptance and an exact immutable native core lock.
AP_V30_PRODUCTION="0"
BUNDLE_FILE="AnythingPlays30Preview.app"
DMG_NAME="AnythingPlays-3.0.0-alpha.1.dmg"
DMG_VOLUME="Anything Plays 3.0 Preview"
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  [[ "${AP_RELEASE_BUILD:-0}" == "1" ]] || { echo "Production requires AP_RELEASE_BUILD=1"; exit 1; }
  [[ -n "${AP_CORE_ARCHIVE_DIR:-}" ]] || { echo "Production requires pinned AP_CORE_ARCHIVE_DIR"; exit 1; }
  python3 tools/check_v30_release.py
  python3 -c 'from tools.v30_release_lock import load_approved_lock; load_approved_lock()'
  AP_V30_PRODUCTION="1"
  BUNDLE_FILE="AnythingPlays.app"
  DMG_VOLUME="Anything Plays"
  case "$(uname -m)" in
    arm64) DMG_NAME="AnythingPlays-3.0.0-macos-arm64.dmg" ;;
    x86_64) DMG_NAME="AnythingPlays-3.0.0-macos-x64.dmg" ;;
    *) echo "Unsupported 3.0 production macOS architecture"; exit 1 ;;
  esac
fi
APP_BUNDLE="dist/$BUNDLE_FILE"
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
.build-venv/bin/python -m PyInstaller --collect-all glcontext --noconfirm --clean --windowed --onedir --name AnythingPlays --add-data "assets/anything_plays.png:assets" --add-data "assets/anything_plays_v21.webp:assets" app.py
# The testing app deliberately has a separate .app name and bundle identity.
# Do not overwrite a user's installed AnythingPlays.app (the stable 2.0 app).
if [[ "$AP_V30_PRODUCTION" != "1" ]]; then
  mv dist/AnythingPlays.app dist/AnythingPlays30Preview.app
fi
# Generate a native macOS icon from the branded PNG.
ICONSET="build/AnythingPlays.iconset"
mkdir -p "$ICONSET"
for SIZE in 16 32 128 256 512; do
  sips -z "$SIZE" "$SIZE" build/v21-icon/anything_plays.png --out "$ICONSET/icon_${SIZE}x${SIZE}.png" >/dev/null
  DOUBLE=$((SIZE * 2))
  sips -z "$DOUBLE" "$DOUBLE" build/v21-icon/anything_plays.png --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP_BUNDLE/Contents/Resources/AnythingPlays.icns"
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AnythingPlays.icns" "$APP_BUNDLE/Contents/Info.plist"
mkdir -p "$APP_BUNDLE/Contents/Resources/cores"
CORE_LIST=(mgba snes9x)
if [[ "${AP_V30_MINIMAL_CORE_BUILD:-0}" == "1" ]]; then
  CORE_LIST=(mgba)
elif [[ "${AP_V30_TEST_CORES:-0}" == "1" || "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  CORE_LIST+=(fceumm genesis_plus_gx parallel_n64 dolphin stella2014 prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan)
fi
# Lab-only full offline 11-slot variant: use genuinely differently named
# pinned-source GPL binaries, not renamed noncommercial Snes9x/Genesis GX.
if [[ "${AP_V30_GPL_TRIAL:-0}" == "1" ]]; then
  [[ "${AP_V30_TEST_CORES:-0}" == "1" && "${AP_V30_APPROVED_RELEASE:-0}" != "1" && "${AP_RELEASE_BUILD:-0}" != "1" ]] || exit 1
  CORE_LIST=(mgba mednafen_supafaust fceumm blastem parallel_n64 dolphin stella2014 prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan)
fi
# The complete GPL-alternative engineering test is distinct from PRODUCTION.
# Production core names come ONLY from the fully rights-reviewed native lock.
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  reviewed_names="$("$PYTHON" -m tools.v30_release_lock --print-approved-core-names)" || exit 1
  read -r -a CORE_LIST <<< "$reviewed_names"
  [[ "${#CORE_LIST[@]}" == 11 ]] || { echo "Wrong approved 3.0 core list"; exit 1; }
fi
for name in "${CORE_LIST[@]}"; do
  core="cores/${name}_libretro.dylib"
  [[ -f "$core" ]] || { echo "Missing required core: $core"; exit 1; }
  cp "$core" "$APP_BUNDLE/Contents/Resources/cores/"
done
# Include a hash manifest identifying the exact nightly cores in this build.
cp cores/CORE_PROVENANCE.json "$APP_BUNDLE/Contents/Resources/cores/"
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" && -f cores/V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json ]]; then
  cp cores/V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json "$APP_BUNDLE/Contents/Resources/cores/"
fi
if [[ "${AP_V30_GPL_TRIAL:-0}" == "1" ]]; then
  cp cores/V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json "$APP_BUNDLE/Contents/Resources/cores/"
fi
if [[ "${AP_V30_TEST_CORES:-0}" == "1" || "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  # Dolphin's self-contained core needs compatibility tables under Sys/.
  # Ship them with the signed app; never ask the player to download them.
  [[ -f cores/dolphin-emu/Sys/codehandler.bin ]] || { echo 'Missing Dolphin Sys'; exit 1; }
  cp -R cores/dolphin-emu "$APP_BUNDLE/Contents/Resources/cores/"
  cp cores/DOLPHIN_SYS_PROVENANCE.json "$APP_BUNDLE/Contents/Resources/cores/"
fi
# Required for Finder launches: macOS kills camera-using apps without this key.
PLIST="${APP_BUNDLE}/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :NSCameraUsageDescription" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string Anything Plays uses the camera to track moving objects for game controls." "$PLIST"
if [[ "$AP_V30_PRODUCTION" == "1" ]]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.anythingplays.release30" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string Anything Plays" "$PLIST" || true
else
  /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.anythingplays.preview30" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string Anything Plays 3.0 Preview" "$PLIST" || true
fi
# Include project and third-party licensing documentation.
LICENSE_DIR="${APP_BUNDLE}/Contents/Resources/licenses"
mkdir -p "$LICENSE_DIR"

cp LICENSE "$LICENSE_DIR/AnythingPlays-MIT.txt"
cp CODE_OF_CONDUCT.md "$LICENSE_DIR/"
cp docs/THIRD_PARTY_NOTICES.md "$LICENSE_DIR/"
cp docs/THIRD_PARTY_COMPONENTS.md "$LICENSE_DIR/"
cp licenses/*.txt "$LICENSE_DIR/"
if [[ "${AP_V30_GPL_TRIAL:-0}" == "1" ]]; then
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-Supafaust-COPYING.txt" "$LICENSE_DIR/"
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-BlastEm-COPYING.txt" "$LICENSE_DIR/"
  if [[ "${AP_V30_PINNED_PCE:-0}" == "1" ]]; then
    cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-PCE-COPYING.txt" "$LICENSE_DIR/"
  fi
  if [[ "${AP_V30_PINNED_MGBA:-0}" == "1" ]]; then
    cp "${AP_CORE_ARCHIVE_DIR}/MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt" "$LICENSE_DIR/"
  fi
  if [[ "${AP_V30_PINNED_FIVE:-0}" == "1" ]]; then
    for name in fceumm stella2014 prosystem mednafen_ngp mednafen_wswan; do
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-${name}-ORIGINAL-COPYING.txt" "$LICENSE_DIR/"
    done
  fi
fi
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" && -f cores/V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json ]]; then
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-Supafaust-COPYING.txt" "$LICENSE_DIR/Supafaust-COPYING.txt"
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-BlastEm-COPYING.txt" "$LICENSE_DIR/BlastEm-COPYING.txt"
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-PCE-COPYING.txt" "$LICENSE_DIR/PCE-COPYING.txt"
  if [[ "${AP_V30_APPROVED_EIGHT:-0}" == "1" ]]; then
    for name in fceumm stella2014 prosystem mednafen_ngp mednafen_wswan; do
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-${name}-ORIGINAL-COPYING.txt" "$LICENSE_DIR/"
    done
  fi
fi
.build-venv/bin/python tools/collect_python_notices.py "$LICENSE_DIR"

"$PYTHON" verify_bundle.py --check-native macos "$APP_BUNDLE"
if [[ "${AP_V30_TEST_CORES:-0}" == "1" || "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  .build-venv/bin/python tools/probe_embedded_3d.py macos "$APP_BUNDLE"
fi
# Sign the outer application only. --deep would mutate nested Libretro dylibs
# after their SHA-256 values were recorded in CORE_PROVENANCE.json.
codesign --force --sign - "$APP_BUNDLE"
# Verify again after signing; reject even a successfully signed but modified
# bundle instead of shipping a DMG with invalid core provenance.
"$PYTHON" verify_bundle.py --check-native macos "$APP_BUNDLE"
codesign --verify --verbose=2 "$APP_BUNDLE"
mkdir -p release
# CI's shared macOS disk-image service intermittently returns Resource busy
# after a clean ad-hoc signed bundle. Retry ONLY the DMG mount operation:
# never suppress a permanent packaging/verification failure.
DMG="release/$DMG_NAME"
DMG_READY=0
for ATTEMPT in 1 2 3 4; do
  rm -f "$DMG"
  if hdiutil create -volname "$DMG_VOLUME" \
      -srcfolder "$APP_BUNDLE" -ov -format UDZO "$DMG"; then
    DMG_READY=1
    break
  fi
  echo "macOS disk-image service failed on attempt $ATTEMPT"
  sleep "$((ATTEMPT * 3))"
done
[[ "$DMG_READY" == "1" && -s "$DMG" ]] || {
  echo "DMG packaging failed after four attempts" >&2
  exit 1
}
# Verify bytes after they have been packaged into the actual distributable DMG.
MOUNT_DIR="$(mktemp -d /tmp/anything-plays-release.XXXXXX)"
trap 'hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1 || true; rmdir "$MOUNT_DIR" >/dev/null 2>&1 || true' EXIT
hdiutil attach -readonly -nobrowse -mountpoint "$MOUNT_DIR" "$DMG"
"$PYTHON" verify_bundle.py --check-native macos "$MOUNT_DIR/${BUNDLE_FILE}"
hdiutil detach "$MOUNT_DIR"
rmdir "$MOUNT_DIR"
trap - EXIT
echo "Created $DMG (ad-hoc signed app; Apple notarization is NOT claimed)"
