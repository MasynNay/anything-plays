#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
VERSION="${VERSION:-2.0.0}"
ARCH="$(dpkg --print-architecture)"
python3 fetch_mgba_core.py
python3 -m venv .build-venv
.build-venv/bin/python -m pip install --upgrade pip
.build-venv/bin/python -m pip install -r requirements.txt pyinstaller
.build-venv/bin/python -m PyInstaller --noconfirm --clean --onedir --windowed --name AnythingPlays --collect-all cv2 --collect-all PIL --add-data "assets/anything_plays.png:assets" app.py
# All emulator cores are required and shipped inside the installed application.
mkdir -p dist/AnythingPlays/cores
for name in mgba snes9x; do
  core="cores/${name}_libretro.so"
  [[ -f "$core" ]] || { echo "Missing required core: $core"; exit 1; }
  cp "$core" dist/AnythingPlays/cores/
done
cp cores/CORE_PROVENANCE.json dist/AnythingPlays/cores/

# Include project and third-party licensing documentation.
mkdir -p dist/AnythingPlays/licenses
cp LICENSE dist/AnythingPlays/licenses/AnythingPlays-MIT.txt
cp CODE_OF_CONDUCT.md dist/AnythingPlays/licenses/
cp docs/THIRD_PARTY_NOTICES.md dist/AnythingPlays/licenses/
cp docs/THIRD_PARTY_COMPONENTS.md dist/AnythingPlays/licenses/
cp licenses/*.txt dist/AnythingPlays/licenses/

python3 verify_bundle.py linux dist/AnythingPlays

PKG="build/deb/anything-plays_${VERSION}_${ARCH}"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt/anything-plays" "$PKG/usr/bin" "$PKG/usr/share/applications"
cp -a dist/AnythingPlays/. "$PKG/opt/anything-plays/"
mkdir -p "$PKG/usr/share/icons/hicolor/256x256/apps"
cp assets/anything_plays_small.png "$PKG/usr/share/icons/hicolor/256x256/apps/anything-plays.png"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: anything-plays
Version: $VERSION
Section: games
Priority: optional
Architecture: $ARCH
Maintainer: Anything Plays Project <noreply@example.invalid>
Depends: libc6, libgl1, libglib2.0-0, libportaudio2
Description: Anything Plays camera-controlled multi-system gaming studio
 Embedded GB, GBC, GBA and SNES gameplay and configurable camera object tracking.
CONTROL
cat > "$PKG/usr/bin/anything-plays" <<'LAUNCH'
#!/bin/sh
exec /opt/anything-plays/AnythingPlays "$@"
LAUNCH
chmod +x "$PKG/usr/bin/anything-plays"
cat > "$PKG/usr/share/applications/anything-plays.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Anything Plays
Comment=Camera-controlled multi-system gaming studio
Exec=anything-plays
Icon=anything-plays
Terminal=false
Categories=Game;Emulator;
DESKTOP
mkdir -p release
chmod g-s "$PKG/DEBIAN"
chmod 0755 "$PKG/DEBIAN"
dpkg-deb --build --root-owner-group "$PKG" "release/anything-plays_${VERSION}_${ARCH}.deb"
echo "Created release/anything-plays_${VERSION}_${ARCH}.deb"
