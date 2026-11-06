"""Exclude redundant system audio libraries and unused Readline from Linux DEBs.

PyInstaller freezes libportaudio2 (and JACK, ALSA, Berkeley DB) along with a
Python Readline extension, although Anything Plays neither uses Readline nor
needs private copies of OS audio libraries. Ubuntu/Debian provides PortAudio
through the installed DEB dependency: libportaudio2.

The exact RC5 ELF linkage audit established:
  readline extension -> libreadline
  frozen PortAudio -> JACK, ALSA
  JACK -> Berkeley DB

This only acts on the *Linux frozen app staging directory*, never on system
libraries or the user's Python environment.
"""
from pathlib import Path

EXCLUDED_RELATIVE_FILES = (
    "_internal/libportaudio.so.2",
    "_internal/libjack.so.0",
    "_internal/libdb-5.3.so",
    "_internal/libasound.so.2",
    "_internal/libreadline.so.8",
)
READLINE_GLOB = "_internal/python3.13/lib-dynload/readline*.so"


def prune_staged_linux_app(bundle):
    bundle = Path(bundle).resolve(strict=True)
    if not bundle.is_dir() or not (bundle / "_internal").is_dir():
        raise ValueError("Expected a frozen Linux PyInstaller onedir app")
    removed = []
    for relative in EXCLUDED_RELATIVE_FILES:
        file = bundle / relative
        if file.is_symlink():
            raise ValueError(f"Refusing symlinked audio-system candidate {relative}")
        if file.is_file():
            file.unlink()
            removed.append(relative)
    for file in sorted(bundle.glob(READLINE_GLOB)):
        if file.is_symlink():
            raise ValueError("Refusing symlinked Readline extension")
        if not file.is_file():
            continue
        removed.append(file.relative_to(bundle).as_posix())
        file.unlink()
    remaining = [
        file.relative_to(bundle).as_posix()
        for file in bundle.rglob("*")
        if file.is_file() and (
            file.name.startswith(("libportaudio.so", "libjack.so",
                                  "libdb-5.3.so", "libasound.so",
                                  "libreadline.so"))
            or (
                file.name.startswith("readline.")
                and file.name.endswith(".so")
                and "lib-dynload" in file.parts
            )
        )
    ]
    if remaining:
        raise ValueError("Unremoved Linux system libraries: " + ", ".join(remaining))
    return removed


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    removed = prune_staged_linux_app(args.app)
    print("Removed redundant frozen Linux system-library files:", len(removed))
    for name in removed:
        print("  " + name)
    print("The Debian package must retain the libportaudio2 Depends entry")


if __name__ == "__main__":
    main()
