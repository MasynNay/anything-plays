#!/usr/bin/env bash
# Experimental Anything Plays 2.1: compile Dolphin's modified Libretro CPU core.
# Run only on a CI/developer build host. End users must NOT build or download it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
SOURCE_SHA="32c61f9d0e933331bb7087ba57e96883241b4960"
WORK_DIR="${AP_DOLPHIN_BUILD_WORK:-${RUNNER_TEMP:-/tmp}/anything-plays-dolphin-native}"
SOURCE_DIR="$WORK_DIR/upstream"
BUILD_DIR="$WORK_DIR/build"
CORE_DIR="$WORK_DIR/cores"

echo "Preparing isolated upstream Dolphin source at $SOURCE_SHA"
mkdir -p "$WORK_DIR" "$CORE_DIR"
if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  git clone --filter=blob:none --no-checkout \
    https://github.com/libretro/dolphin.git "$SOURCE_DIR"
fi
git -C "$SOURCE_DIR" fetch --filter=blob:none origin "$SOURCE_SHA"
git -C "$SOURCE_DIR" checkout --detach "$SOURCE_SHA"
git -C "$SOURCE_DIR" submodule update --init --recursive --jobs 4 --depth 1

# Strict source revision and byte-level source anchor checks; compiler receives
# the altered C++ file. No runtime monkey-patching or in-place dylib editing.
python tools/patch_dolphin_software.py "$SOURCE_DIR"
# Record exactly what native source the compiler receives. Keep this next to
# the output binary so CI can distinguish the patched build from upstream.
git -C "$SOURCE_DIR" diff --check
git -C "$SOURCE_DIR" diff -- \
  Source/Core/DolphinLibretro/Video.h \
  Source/Core/DolphinLibretro/Boot.cpp \
  Source/Core/DolphinLibretro/CMakeLists.txt \
  Source/Core/VideoBackends/Software/SWmain.cpp \
  > "$WORK_DIR/dolphin-video-software.patch"
sha256sum "$WORK_DIR/dolphin-video-software.patch" \
  | tee "$WORK_DIR/dolphin-video-patch-sha256.txt"

echo "Configuring GameCube Libretro CPU-rendered native test core"
cmake -S "$SOURCE_DIR" -B "$BUILD_DIR" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIBRETRO=ON \
  -DENABLE_QT=OFF -DENABLE_TESTS=OFF \
  -DENABLE_LTO=OFF -DENABLE_VULKAN=OFF -DENABLE_CCACHE=ON \
  -DENABLE_ANALYTICS=OFF -DUSE_RETRO_ACHIEVEMENTS=OFF \
  -DUSE_SYSTEM_LIBS=OFF -DUSE_MGBA=OFF

echo "Building native Dolphin Libretro core (not an Anything Plays release)"
cmake --build "$BUILD_DIR" --target dolphin_libretro --parallel "${AP_DOLPHIN_BUILD_JOBS:-2}"
BINARY="$BUILD_DIR/dolphin_libretro.so"
[[ -s "$BINARY" ]] || { echo "Dolphin core was not produced at $BINARY"; exit 1; }
cp "$BINARY" "$CORE_DIR/dolphin_libretro.so"
sha256sum "$CORE_DIR/dolphin_libretro.so" | tee "$WORK_DIR/dolphin-core-sha256.txt"

# Bundle required Dolphin Sys files on the builder. Player installation will
# eventually contain these exact audited files, not download them itself.
python tools/fetch_dolphin_sys.py "$CORE_DIR"

echo "Patched GameCube binary ready for the isolated licensed-homebrew probe"
printf '%s\n' "$CORE_DIR/dolphin_libretro.so"
