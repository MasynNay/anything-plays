"""Isolated native startup probe for both bundled 3D Libretro cores.

Run from packaging jobs after building a bundle, not from the UI. A core must
initialize/deinitialize using Anything Plays' real frontend callbacks without
installing RetroArch or Dolphin. No ROM, BIOS, camera or game is bundled.
This is NOT a playable-frame or real-game compatibility test.

If a native core segfaults, this process exits nonzero and the installer is
rejected. Run this as a subprocess so a broken core cannot kill the packager.
"""

import argparse
import ctypes as C
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anything_plays.gba_emulator import CoreSession, Emulator, NativeCore
from anything_plays.libretro_abi import CoreInfo
from anything_plays.core_locator import _library_extension


def probe_native_session(system, path):
    """Exercise the real callback ABI but never load a commercial game file."""
    emu = Emulator()
    emu.system = system
    emu.inputs.system = system
    session = CoreSession(emu, system, Path("synthetic-not-loaded"), path)
    native = NativeCore(path)
    session.native = native
    try:
        native.configure(
            session.environment, session.video, session.audio, emu.inputs
        )
        native.init()
        native.initialized = True
        info = CoreInfo()
        native.system_info(C.byref(info))
        name = (info.library_name or b"").decode("utf-8", "replace")
        if not name.strip():
            raise ValueError(f"{system} core supplied no library identity")
        print(
            f"Native startup OK: {system}, {name}, "
            f"version {(info.library_version or b'').decode('utf-8', 'replace')}",
            flush=True,
        )
    finally:
        native.close()
        session.audio.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=("macos", "windows", "linux"))
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()

    bundle = args.bundle.resolve(strict=True)
    prefix = (bundle / "Contents" / "Resources" if args.platform == "macos"
              else bundle)
    cores = prefix / "cores"
    suffix = {"macos": ".dylib", "windows": ".dll", "linux": ".so"}[
        args.platform
    ]
    with TemporaryDirectory(prefix="anything-plays-native-probe-") as temp:
        with patch("pathlib.Path.home", return_value=Path(temp)):
            for system, name in (("n64", "parallel_n64"),
                                 ("gamecube", "dolphin")):
                core = cores / f"{name}_libretro{suffix}"
                if not core.is_file():
                    raise FileNotFoundError(
                        f"Missing required embedded core: {core}"
                    )
                probe_native_session(system, core)
    print("Native 3D Libretro startup probes completed.", flush=True)


if __name__ == "__main__":
    main()
