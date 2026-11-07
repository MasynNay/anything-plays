#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${VERSION:-3.0.0~alpha1}"
ARCH="$(dpkg --print-architecture)"
python3 fetch_mgba_core.py
python3 -m venv .build-venv
.build-venv/bin/python -m pip install --upgrade pip==26.3
.build-venv/bin/python -m pip install -r requirements-build.txt
# Optional, hash-locked camera-only OpenCV replacement for audited builds.
if [[ -n "${AP_CUSTOM_OPENCV_WHEEL:-}" ]]; then
  : "${AP_CUSTOM_OPENCV_SHA256:?Set custom wheel SHA-256}"
  python3 tools/verify_custom_opencv_wheel.py "$AP_CUSTOM_OPENCV_WHEEL" "$AP_CUSTOM_OPENCV_SHA256" linux-x86_64
  .build-venv/bin/python -m pip install --force-reinstall --no-deps "$AP_CUSTOM_OPENCV_WHEEL"
  export AP_REQUIRE_OPENCV_FFMPEG_OFF=1
fi
.build-venv/bin/python tools/check_opencv_build.py
# Preserve stable source art and generate corrected test-only Linux icons.
.build-venv/bin/python tools/render_v21_icon.py
.build-venv/bin/python -m PyInstaller --collect-all glcontext --noconfirm --clean --onedir --windowed --name AnythingPlays --collect-all cv2 --collect-all PIL --add-data "assets/anything_plays.png:assets" --add-data "assets/anything_plays_v21.webp:assets" app.py
# The DEB depends on OS libportaudio2. Do not redistribute frozen copies of
# PortAudio, JACK, ALSA, Berkeley DB, or the unused GPL Readline extension.
python3 tools/prune_linux_system_libs.py dist/AnythingPlays
# A 3.0 starter installer ships only mGBA; other cores are approved in-app downloads.
mkdir -p dist/AnythingPlays/cores
CORE_LIST=(mgba snes9x)
if [[ "${AP_V30_MINIMAL_CORE_BUILD:-0}" == "1" ]]; then
  CORE_LIST=(mgba)
elif [[ "${AP_V30_TEST_CORES:-0}" == "1" ]]; then
  CORE_LIST+=(fceumm genesis_plus_gx parallel_n64 dolphin stella2014 prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan)
fi
for name in "${CORE_LIST[@]}"; do
  core="cores/${name}_libretro.so"
  [[ -f "$core" ]] || { echo "Missing required core: $core"; exit 1; }
  cp "$core" dist/AnythingPlays/cores/
done
cp cores/CORE_PROVENANCE.json dist/AnythingPlays/cores/
if [[ "${AP_V30_TEST_CORES:-0}" == "1" ]]; then
  [[ -f cores/dolphin-emu/Sys/codehandler.bin ]] || { echo 'Missing Dolphin Sys'; exit 1; }
  cp -R cores/dolphin-emu dist/AnythingPlays/cores/
  cp cores/DOLPHIN_SYS_PROVENANCE.json dist/AnythingPlays/cores/
fi

# Include project and third-party licensing documentation.
mkdir -p dist/AnythingPlays/licenses
cp LICENSE dist/AnythingPlays/licenses/AnythingPlays-MIT.txt
cp CODE_OF_CONDUCT.md dist/AnythingPlays/licenses/
cp docs/THIRD_PARTY_NOTICES.md dist/AnythingPlays/licenses/
cp docs/THIRD_PARTY_COMPONENTS.md dist/AnythingPlays/licenses/
cp licenses/*.txt dist/AnythingPlays/licenses/
.build-venv/bin/python tools/collect_python_notices.py dist/AnythingPlays/licenses

python3 verify_bundle.py --check-native linux dist/AnythingPlays
if [[ "${AP_V30_TEST_CORES:-0}" == "1" ]]; then
  .build-venv/bin/python tools/probe_embedded_3d.py linux dist/AnythingPlays
fi

PKG="build/deb/anything-plays-preview_${VERSION}_${ARCH}"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt/anything-plays-30-preview" "$PKG/usr/bin" "$PKG/usr/share/applications"
cp -a dist/AnythingPlays/. "$PKG/opt/anything-plays-30-preview/"
mkdir -p "$PKG/usr/share/icons/hicolor/256x256/apps"
cp build/v21-icon/anything_plays_small.png "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays-preview.png"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: anything-plays-preview
Version: $VERSION
Section: games
Priority: optional
Architecture: $ARCH
Maintainer: Anything Plays Project <noreply@example.invalid>
Depends: libc6, libgl1, libegl1, libglib2.0-0, libportaudio2
Description: Anything Plays camera-controlled multi-system gaming studio
 Embedded GB/GBC/GBA, SNES, NES, Genesis and experimental 3D cores.
CONTROL
cat > "$PKG/usr/bin/anything-plays-30-preview" <<'LAUNCH'
#!/bin/sh
# Linux desktop launchers otherwise swallow Python/native startup tracebacks.
# Preserve a private, bounded log and show a visible error when the app exits
# before creating a window. No sudo, user-file deletion, or /opt modification.
umask 077
state_base="${XDG_STATE_HOME:-${HOME:-}/.local/state}"
case "$state_base" in /*) ;; *) state_base="${HOME:-/tmp}/.local/state" ;; esac
state_dir="$state_base/anything-plays-preview"
if ! mkdir -p "$state_dir" 2>/dev/null; then
  echo "Anything Plays cannot create diagnostic directory: $state_dir" >&2
  exec /opt/anything-plays-30-preview/AnythingPlays "$@"
fi
log="$state_dir/startup.log"
if [ -f "$log" ] && [ "$(wc -c < "$log")" -gt 262144 ]; then
  tail -c 131072 "$log" > "$log.trimmed" 2>/dev/null && mv -f "$log.trimmed" "$log"
fi
printf '\n== Preview launch %s ==\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$log"
/opt/anything-plays-30-preview/AnythingPlays "$@" >> "$log" 2>&1
status=$?
if [ "$status" -ne 0 ]; then
  error="Anything Plays 3.0 could not open (exit $status).
The startup log was saved to:
$log

Your settings, saved games and ROMs were not deleted."
  printf '%s\n' "$error" >&2
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="Anything Plays startup error" --text="$error" 2>/dev/null || :
  elif command -v kdialog >/dev/null 2>&1; then
    kdialog --error "$error" --title "Anything Plays startup error" 2>/dev/null || :
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send "Anything Plays startup failed" "See $log" 2>/dev/null || :
  fi
fi
exit "$status"
LAUNCH
chmod +x "$PKG/usr/bin/anything-plays-30-preview"
cat > "$PKG/usr/share/applications/anything-plays-preview.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Anything Plays 3.0 Preview
Comment=Camera-controlled multi-system gaming studio
Exec=anything-plays-30-preview
Icon=anything-plays-preview
Terminal=false
Categories=Game;Emulator;
DESKTOP
mkdir -p release
chmod g-s "$PKG/DEBIAN"
chmod 0755 "$PKG/DEBIAN"
dpkg-deb --build --root-owner-group "$PKG" "release/anything-plays-preview_${VERSION}_${ARCH}.deb"
# Verify the exact DEB payload, not only the staging folder.
AUDIT_DIR="$(mktemp -d)"
trap 'rm -rf "$AUDIT_DIR"' EXIT
dpkg-deb -x "release/anything-plays-preview_${VERSION}_${ARCH}.deb" "$AUDIT_DIR"
python3 verify_bundle.py --check-native linux "$AUDIT_DIR/opt/anything-plays-30-preview"
python3 - "$AUDIT_DIR/opt/anything-plays-30-preview" <<'PY'
import sys
from pathlib import Path
from tools.prune_linux_system_libs import EXCLUDED_RELATIVE_FILES
root=Path(sys.argv[1])
assert all(not (root/p).exists() for p in EXCLUDED_RELATIVE_FILES)
assert not list(root.glob("_internal/python3.13/lib-dynload/readline*.so"))
print("Validated clean Linux installed payload without redundant audio system libraries")
PY
rm -rf "$AUDIT_DIR"
trap - EXIT
echo "Created release/anything-plays-preview_${VERSION}_${ARCH}.deb"
