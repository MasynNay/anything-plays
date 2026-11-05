"""Download the native Libretro cores required for all four supported systems.
Run before PyInstaller. Fail loudly if the dependency cannot be retrieved.
"""
import io
import platform
from pathlib import Path
import sys
import urllib.request
import zipfile

BASE = "https://buildbot.libretro.com/nightly"
MACHINE = platform.machine().lower()
if sys.platform == "win32":
    if MACHINE not in ("amd64", "x86_64"):
        sys.exit("Unsupported Windows architecture: " + MACHINE + " (x64 required)")
    folder, ext = "windows/x86_64/latest", ".dll"
elif sys.platform == "darwin":
    if MACHINE not in ("arm64", "x86_64"):
        sys.exit("Unsupported macOS architecture: " + MACHINE)
    folder, ext = f"apple/osx/{MACHINE}/latest", ".dylib"
elif sys.platform.startswith("linux"):
    if MACHINE not in ("x86_64", "amd64", "i386", "i686"):
        sys.exit("Unsupported Linux architecture: " + MACHINE)
    folder, ext = ("linux/x86_64/latest" if MACHINE in ("x86_64", "amd64") else "linux/x86/latest"), ".so"
else:
    sys.exit("Unsupported platform: " + sys.platform)

CORE_NAMES = ("gambatte", "mgba", "snes9x")

def fetch_core(name):
    filename = name + "_libretro" + ext
    url = f"{BASE}/{folder}/{filename}.zip"
    target = Path(__file__).resolve().parent / "cores" / filename
    print("Fetching", name, "core:", url, flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AnythingPlays-build/2.0.0"})
        with urllib.request.urlopen(req, timeout=45) as response:
            data = response.read(30 * 1024 * 1024 + 1)
        if len(data) > 30 * 1024 * 1024:
            raise ValueError("Core archive exceeds 30 MB")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            matching = [i for i in archive.infolist() if Path(i.filename).name == filename and not i.is_dir()]
            if len(matching) != 1:
                raise ValueError(f"Expected exactly one {filename} in core archive")
            info = matching[0]
            if not (10_000 < info.file_size < 60 * 1024 * 1024):
                raise ValueError("Unexpected core binary size")
            content = archive.read(info)
        # Reject a mislabeled download before packaging it.
        if ext == ".dll" and content[:2] != b"MZ":
            raise ValueError("Downloaded core is not a Windows PE binary")
        if ext == ".so" and content[:4] != b"\x7fELF":
            raise ValueError("Downloaded core is not an ELF binary")
        if ext == ".dylib" and content[:4] not in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
            raise ValueError("Downloaded core is not a Mach-O binary")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        print(f"{name} ready: {target} ({len(content):,} bytes)", flush=True)
    except Exception as exc:
        raise RuntimeError(f"Could not download {name} core: {exc}") from exc

if __name__ == "__main__":
    try:
        for core_name in CORE_NAMES:
            fetch_core(core_name)
    except Exception as exc:
        sys.exit(f"ERROR: {exc}\nBuild stopped; retry when online.")
