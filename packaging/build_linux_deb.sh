#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${VERSION:-3.0.0~alpha1}"
ARCH="$(dpkg --print-architecture)"
PACKAGE_NAME="anything-plays-preview"
INSTALL_ID="anything-plays-30-preview"
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  [[ "${AP_RELEASE_BUILD:-0}" == "1" ]] || { echo "Production requires AP_RELEASE_BUILD=1"; exit 1; }
  [[ -n "${AP_CORE_ARCHIVE_DIR:-}" ]] || { echo "Production requires pinned AP_CORE_ARCHIVE_DIR"; exit 1; }
  python3 tools/check_v30_release.py
  python3 -c 'from tools.v30_release_lock import load_approved_lock; load_approved_lock()'
  VERSION="3.0.0"
  PACKAGE_NAME="anything-plays"
  INSTALL_ID="anything-plays"
fi
# A version-correct nonpublic source-built candidate for technical review.
# This does NOT enable AP_V30_APPROVED_RELEASE or public redistribution.
if [[ "${AP_V30_STABLE_CANDIDATE:-0}" == "1" ]]; then
  [[ "${AP_RELEASE_BUILD:-0}" != "1" && "${AP_V30_APPROVED_RELEASE:-0}" != "1" &&
     "${AP_V30_TEST_CORES:-0}" == "1" && "${AP_V30_GPL_TRIAL:-0}" == "1" &&
     "${AP_V30_TIA_TRIAL:-0}" == "1" ]] || {
    echo "Stable-identity candidate requires exact original Tia source trial, not approved release"; exit 1;
  }
  VERSION="3.0.0"
  PACKAGE_NAME="anything-plays"
  INSTALL_ID="anything-plays"
fi
# 3.1 owner-review installers use a unique package identity and directory.
# This never enables either 3.0 production flag or the stable package name.
if [[ "${AP_V31_PREVIEW:-0}" == "1" ]]; then
  [[ "${AP_RELEASE_BUILD:-0}" != "1" && "${AP_V30_APPROVED_RELEASE:-0}" != "1" &&
     "${AP_V30_STABLE_CANDIDATE:-0}" != "1" && "${AP_V30_MINIMAL_CORE_BUILD:-0}" == "1" ]] || {
    echo "3.1 preview requires separate, minimal non-release core set" >&2; exit 1;
  }
  VERSION="3.1.0~preview1"
  PACKAGE_NAME="anything-plays-31-preview"
  INSTALL_ID="anything-plays-31-preview"
fi
# Source-built, isolated RC1 application stage (mGBA only until full
# eleven-native-core QA assembly). Never replace stable 3.0.
if [[ "${AP_V31_RC:-0}" == "1" ]]; then
  [[ "${AP_V31_PREVIEW:-0}" != "1" && "${AP_RELEASE_BUILD:-0}" != "1" &&
     "${AP_V30_APPROVED_RELEASE:-0}" != "1" &&
     "${AP_V30_STABLE_CANDIDATE:-0}" != "1" &&
     "${AP_V30_MINIMAL_CORE_BUILD:-0}" == "1" ]] || {
    echo "3.1 RC application stage requires isolated non-release mode" >&2; exit 1;
  }
  VERSION="3.1.0~rc1"
  PACKAGE_NAME="anything-plays-31-rc1"
  INSTALL_ID="anything-plays-31-rc1"
fi
OUTPUT_DEB="release/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
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
V31_IDENTITY_ARGS=()
if [[ "${AP_V31_PREVIEW:-0}" == "1" || "${AP_V31_RC:-0}" == "1" ]]; then
  .build-venv/bin/python -m tools.write_v31_identity build/v31_build_identity.json
  V31_IDENTITY_ARGS=(--add-data "build/v31_build_identity.json:assets")
fi
.build-venv/bin/python -m PyInstaller --collect-all pygame --collect-all glcontext --noconfirm --clean --onedir --windowed --name AnythingPlays "${V31_IDENTITY_ARGS[@]}" --collect-all cv2 --collect-all PIL --add-data "assets/anything_plays.png:assets" --add-data "assets/anything_plays_v21.webp:assets" app.py
# The DEB depends on OS libportaudio2. Do not redistribute frozen copies of
# PortAudio, JACK, ALSA, Berkeley DB, or the unused GPL Readline extension.
python3 tools/prune_linux_system_libs.py dist/AnythingPlays
# A 3.0 starter installer ships only mGBA; other cores are approved in-app downloads.
mkdir -p dist/AnythingPlays/cores
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
  if [[ "${AP_V30_TIA_TRIAL:-0}" == "1" ]]; then
    CORE_LIST=(mgba mednafen_supafaust fceumm blastem parallel_n64 dolphin tia prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan)
  fi
fi
# The complete GPL-alternative engineering test is distinct from PRODUCTION.
# Production core names come ONLY from the fully rights-reviewed native lock.
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  reviewed_names="$(python3 -m tools.v30_release_lock --print-approved-core-names)" || exit 1
  read -r -a CORE_LIST <<< "$reviewed_names"
  [[ "${#CORE_LIST[@]}" == 11 ]] || { echo "Wrong approved 3.0 core list"; exit 1; }
fi
for name in "${CORE_LIST[@]}"; do
  core="cores/${name}_libretro.so"
  [[ -f "$core" ]] || { echo "Missing required core: $core"; exit 1; }
  cp "$core" dist/AnythingPlays/cores/
done
cp cores/CORE_PROVENANCE.json dist/AnythingPlays/cores/
# Approved source-built production uses a DIFFERENT runtime map than the
# unapproved GPL research preview. The reviewed lock fully gates its creation.
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" && -f cores/V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json ]]; then
  cp cores/V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json dist/AnythingPlays/cores/
fi
if [[ "${AP_V30_GPL_TRIAL:-0}" == "1" ]]; then
  cp cores/V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json dist/AnythingPlays/cores/
fi
if [[ "${AP_V30_TEST_CORES:-0}" == "1" || "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  [[ -f cores/dolphin-emu/Sys/codehandler.bin ]] || { echo 'Missing Dolphin Sys'; exit 1; }
  cp -R cores/dolphin-emu dist/AnythingPlays/cores/
  cp cores/DOLPHIN_SYS_PROVENANCE.json dist/AnythingPlays/cores/
  # REAL Linux startup regression: upstream Sys archive's dolphin-emu/
  # directory can have mode 2700. With dpkg --root-owner-group this becomes
  # root-only, so choosing GameCube as the saved profile crashes the entire
  # app at startup (even before a ROM is played). Reset directory traverse
  # permissions explicitly; GNU chmod 0755 *preserves* a directory's setgid
  # bit, hence the deliberate symbolic g-s. Never make Sys files writable to
  # all users or alter the original source downloaded into cores/.
  find dist/AnythingPlays/cores/dolphin-emu -type d \
    -exec chmod u=rwx,g=rx,o=rx,g-s {} +
  find dist/AnythingPlays/cores/dolphin-emu -type f \
    -exec chmod u=rw,g=r,o=r {} +
fi

# Include project and third-party licensing documentation.
mkdir -p dist/AnythingPlays/licenses
cp LICENSE dist/AnythingPlays/licenses/AnythingPlays-MIT.txt
cp .github/CODE_OF_CONDUCT.md dist/AnythingPlays/licenses/
cp docs/THIRD_PARTY_NOTICES.md dist/AnythingPlays/licenses/
cp docs/THIRD_PARTY_COMPONENTS.md dist/AnythingPlays/licenses/
cp licenses/*.txt dist/AnythingPlays/licenses/
# Genuine original-source Dolphin's 5 notices are required for the 11th
# family, never inferred from the earlier retained buildbot core.
if [[ -n "${AP_CORE_ARCHIVE_DIR:-}" && -f "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-DOLPHIN-ORIGINAL-COPYING.txt" ]]; then
  for notice in COPYING GPL2-OR-LATER BSD3 CC0 MIT; do
    test -s "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-DOLPHIN-ORIGINAL-${notice}.txt"
    cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-DOLPHIN-ORIGINAL-${notice}.txt" dist/AnythingPlays/licenses/
  done
fi
if [[ "${AP_V30_GPL_TRIAL:-0}" == "1" ]]; then
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-Supafaust-COPYING.txt" dist/AnythingPlays/licenses/
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-BlastEm-COPYING.txt" dist/AnythingPlays/licenses/
  if [[ "${AP_V30_PINNED_PCE:-0}" == "1" ]]; then
    cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-PCE-COPYING.txt" dist/AnythingPlays/licenses/
  fi
  if [[ "${AP_V30_PINNED_N64:-0}" == "1" ]]; then
    for suffix in 01 02 03 04 05 06 07 08 09 10 11; do
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-N64-NOTICE-${suffix}.txt" dist/AnythingPlays/licenses/
    done
  fi
  if [[ "${AP_V30_PINNED_MGBA:-0}" == "1" ]]; then
    cp "${AP_CORE_ARCHIVE_DIR}/MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt" dist/AnythingPlays/licenses/
  fi
  if [[ "${AP_V30_PINNED_FIVE:-0}" == "1" ]]; then
    remaining_names=(fceumm stella2014 prosystem mednafen_ngp mednafen_wswan)
    if [[ "${AP_V30_TIA_TRIAL:-0}" == "1" ]]; then
      remaining_names=(fceumm tia prosystem mednafen_ngp mednafen_wswan)
    fi
    for name in "${remaining_names[@]}"; do
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-${name}-ORIGINAL-COPYING.txt" dist/AnythingPlays/licenses/
    done
    if [[ "${AP_V30_TIA_TRIAL:-0}" == "1" ]]; then
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-tia-ORIGINAL-SPDX.txt" dist/AnythingPlays/licenses/
    fi
  fi
fi
# A reviewed production alternative needs ORIGINAL source license texts, not
# only SPDX labels. These exact bytes are checked against the 44-core lock.
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" && -f cores/V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json ]]; then
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-Supafaust-COPYING.txt" dist/AnythingPlays/licenses/Supafaust-COPYING.txt
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-BlastEm-COPYING.txt" dist/AnythingPlays/licenses/BlastEm-COPYING.txt
  cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-PCE-COPYING.txt" dist/AnythingPlays/licenses/PCE-COPYING.txt
  if [[ "${AP_V30_APPROVED_EIGHT:-0}" == "1" ]]; then
    reviewed_five=(fceumm stella2014 prosystem mednafen_ngp mednafen_wswan)
    if [[ " ${CORE_LIST[*]} " == *" tia "* ]]; then
      reviewed_five=(fceumm tia prosystem mednafen_ngp mednafen_wswan)
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-tia-ORIGINAL-SPDX.txt" dist/AnythingPlays/licenses/
    fi
    for name in "${reviewed_five[@]}"; do
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-${name}-ORIGINAL-COPYING.txt" dist/AnythingPlays/licenses/
    done
  fi
  if [[ "${AP_V30_APPROVED_TEN:-0}" == "1" ]]; then
    cp "${AP_CORE_ARCHIVE_DIR}/MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt" dist/AnythingPlays/licenses/
    for number in 01 02 03 04 05 06 07 08 09 10 11; do
      cp "${AP_CORE_ARCHIVE_DIR}/GPL-TRIAL-N64-NOTICE-$number.txt" dist/AnythingPlays/licenses/
    done
  fi
fi
.build-venv/bin/python tools/collect_python_notices.py dist/AnythingPlays/licenses

python3 verify_bundle.py --check-native linux dist/AnythingPlays
if [[ "${AP_V30_TEST_CORES:-0}" == "1" || "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  .build-venv/bin/python tools/probe_embedded_3d.py linux dist/AnythingPlays
fi

PKG="build/deb/${PACKAGE_NAME}_${VERSION}_${ARCH}"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt/$INSTALL_ID" "$PKG/usr/bin" "$PKG/usr/share/applications"
cp -a dist/AnythingPlays/. "$PKG/opt/$INSTALL_ID/"
mkdir -p "$PKG/usr/share/icons/hicolor/256x256/apps"
cp build/v21-icon/anything_plays_small.png "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays-preview.png"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: $PACKAGE_NAME
Version: $VERSION
Section: games
Priority: optional
Architecture: $ARCH
Maintainer: Anything Plays Project <noreply@example.invalid>
Depends: libc6, libgl1, libegl1, libglib2.0-0, libportaudio2
Description: Anything Plays camera-controlled multi-system gaming studio
 Embedded GB/GBC/GBA, SNES, NES, Genesis and experimental 3D cores.
CONTROL
cat > "$PKG/usr/bin/$INSTALL_ID" <<'LAUNCH'
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
chmod +x "$PKG/usr/bin/$INSTALL_ID"
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
# 3.1 gets a third distinct Linux installation and launcher.
if [[ "${AP_V31_PREVIEW:-0}" == "1" ]]; then
  sed -i \
    -e 's@anything-plays-30-preview@anything-plays-31-preview@g' \
    -e 's@anything-plays-preview@anything-plays-31-preview@g' \
    -e 's@Anything Plays 3.0@Anything Plays 3.1@g' \
    "$PKG/usr/bin/$INSTALL_ID"
  sed -i \
    -e 's@Name=Anything Plays 3.0 Preview@Name=Anything Plays 3.1 Preview 1@g' \
    -e 's@Exec=anything-plays-30-preview@Exec=anything-plays-31-preview@g' \
    -e 's@Icon=anything-plays-preview@Icon=anything-plays-31-preview@g' \
    "$PKG/usr/share/applications/anything-plays-preview.desktop"
  mv "$PKG/usr/share/applications/anything-plays-preview.desktop" \
     "$PKG/usr/share/applications/anything-plays-31-preview.desktop"
  mv "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays-preview.png" \
     "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays-31-preview.png"
fi
# RC1 installs beside stable and both previous previews.
if [[ "${AP_V31_RC:-0}" == "1" ]]; then
  sed -i \
    -e 's@anything-plays-30-preview@anything-plays-31-rc1@g' \
    -e 's@anything-plays-preview@anything-plays-31-rc1@g' \
    -e 's@Anything Plays 3.0@Anything Plays 3.1@g' \
    "$PKG/usr/bin/$INSTALL_ID"
  sed -i \
    -e 's@Name=Anything Plays 3.0 Preview@Name=Anything Plays 3.1 Release Candidate 1@g' \
    -e 's@Exec=anything-plays-30-preview@Exec=anything-plays-31-rc1@g' \
    -e 's@Icon=anything-plays-preview@Icon=anything-plays-31-rc1@g' \
    "$PKG/usr/share/applications/anything-plays-preview.desktop"
  mv "$PKG/usr/share/applications/anything-plays-preview.desktop" \
     "$PKG/usr/share/applications/anything-plays-31-rc1.desktop"
  mv "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays-preview.png" \
     "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays-31-rc1.png"
fi
# Preview installs side by side with 2.0. The stable Linux package identity
# is selected only after exact 3.0 source/rights/real-device checks pass.
if [[ "${AP_V30_APPROVED_RELEASE:-0}" == "1" || "${AP_V30_STABLE_CANDIDATE:-0}" == "1" ]]; then
  mv "$PKG/opt/anything-plays-30-preview" "$PKG/opt/anything-plays"
  sed -i \
    -e 's@anything-plays-30-preview@anything-plays@g' \
    -e 's@anything-plays-preview@anything-plays@g' \
    -e 's@Preview launch@Application launch@g' \
    "$PKG/usr/bin/anything-plays-30-preview"
  mv "$PKG/usr/bin/anything-plays-30-preview" "$PKG/usr/bin/anything-plays"
  sed -i \
    -e 's@Package: anything-plays-preview@Package: anything-plays@g' \
    -e 's@and experimental 3D cores@and embedded 3D cores@g' \
    "$PKG/DEBIAN/control"
  sed -i \
    -e 's@Name=Anything Plays 3.0 Preview@Name=Anything Plays@g' \
    -e 's@Exec=anything-plays-30-preview@Exec=anything-plays@g' \
    -e 's@Icon=anything-plays-preview@Icon=anything-plays@g' \
    "$PKG/usr/share/applications/anything-plays-preview.desktop"
  mv "$PKG/usr/share/applications/anything-plays-preview.desktop" \
     "$PKG/usr/share/applications/anything-plays.desktop"
  mv "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays-preview.png" \
     "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays.png"
fi
mkdir -p release
chmod g-s "$PKG/DEBIAN"
chmod 0755 "$PKG/DEBIAN"
dpkg-deb --build --root-owner-group "$PKG" "$OUTPUT_DEB"
# Verify the exact DEB payload, not only the staging folder.
AUDIT_DIR="$(mktemp -d)"
trap 'rm -rf "$AUDIT_DIR"' EXIT
dpkg-deb -x "$OUTPUT_DEB" "$AUDIT_DIR"
python3 verify_bundle.py --check-native linux "$AUDIT_DIR/opt/$INSTALL_ID"
python3 - "$AUDIT_DIR/opt/$INSTALL_ID" <<'PY'
import sys
from pathlib import Path
from tools.prune_linux_system_libs import EXCLUDED_RELATIVE_FILES
root=Path(sys.argv[1])
assert all(not (root/p).exists() for p in EXCLUDED_RELATIVE_FILES)
assert not list(root.glob("_internal/python3.13/lib-dynload/readline*.so"))
print("Validated clean Linux installed payload without redundant audio system libraries")
PY
# CI and local builds must reject a Debian package that an ordinary user
# cannot traverse. stat() is enough to check root-owned package mode bits
# without needing to grant sudo or read any private user files.
if [[ "${AP_V30_TEST_CORES:-0}" == "1" || "${AP_V30_APPROVED_RELEASE:-0}" == "1" ]]; then
  python3 - "$AUDIT_DIR/opt/$INSTALL_ID/cores/dolphin-emu" <<'PY'
from pathlib import Path
import stat
import sys
root = Path(sys.argv[1])
directories = [root, *(p for p in root.rglob("*") if p.is_dir())]
files = [p for p in root.rglob("*") if p.is_file()]
assert directories and files, "Dolphin Sys missing"
for path in directories:
    mode = stat.S_IMODE(path.stat().st_mode)
    assert (mode & 0o005) == 0o005, (
        f"Root-owned Dolphin Sys directory is not public-traversable: {path} {mode:o}"
    )
    assert (mode & 0o2000) == 0, f"Unexpected setgid Dolphin Sys dir: {path}"
for path in files:
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode & 0o004, f"Bundled Sys file cannot be read: {path} {mode:o}"
assert (root / "Sys" / "codehandler.bin").stat().st_size > 0
print("Verified installed root-owned Dolphin Sys is readable/traversable")
PY
fi
rm -rf "$AUDIT_DIR"
trap - EXIT
echo "Created $OUTPUT_DEB"
