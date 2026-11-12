"""Stage pinned pygame/SDL/mpg123 original sources for 3.1 distribution.

This creates recipient-accessible upstream source and notice materials. It
does not assert that every compiled native dependency is reproducible from
these inputs, that all alternative LGPL paths are satisfied, or that release
approval exists. Never rename a source *candidate* as proven correspondence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile

APP_SOURCE = "104b96621ec4cb8dc39fde8c3fe96fc854c406ed"
SOURCE_ARCHIVES = {
    "pygame-ce-2.5.8-tagged-upstream-source.tar.gz":
        "a5c27ac5a333e66e9ff8abb45c5f47d51171da70ea1532e30a32cf0e8c4c405c",
    "SDL-original-tagged-source-candidates/sdl2-2.32.10.tar.gz":
        "bb59eef6147f37ec44300b6ed1782d1894d91e6ef75ee9edcbddb1bb6916f8a1",
    "SDL-original-tagged-source-candidates/sdl2-2.32.8.tar.gz":
        "0027b6882cd11969bc71bcb6a44b40c09a7b989a5018a233f43de0b64eb24f6f",
    "SDL-original-tagged-source-candidates/sdl2-image-2.8.12.tar.gz":
        "495328adb6b18fb878689e6809cafff3c909eaa4d36007263e6f3a9a671de51f",
    "SDL-original-tagged-source-candidates/sdl2-mixer-2.8.2.tar.gz":
        "899969f9ab7ed9f2ec9ddd112b9e2d04e929e599ea92c012d2263570c1f8ad3a",
    "SDL-original-tagged-source-candidates/sdl2-ttf-2.24.0.tar.gz":
        "f89b1e90c12a11842f480437e5bd96c0f56460abba6c16d6ff515cd030f7b439",
    "mpg123-1.33.7.tar.bz2":
        "31d0e35a4ca567ec9b5ebda6c3062bb4435d6d3eacd6ef0d95cadd7854dc03ee",
}
EVIDENCE = (
    "SDL-original-tagged-source-candidates/SDL_CANDIDATE_SOURCE_MANIFEST.json",
    "SDL-original-tagged-source-candidates/Pygame-CE-LGPL-2.1.txt",
    "SDL-original-tagged-source-candidates/sdl2-2.32.10-ORIGINAL-LICENSE.txt",
    "SDL-original-tagged-source-candidates/sdl2-2.32.8-ORIGINAL-LICENSE.txt",
    "SDL-original-tagged-source-candidates/sdl2-image-2.8.12-ORIGINAL-LICENSE.txt",
    "SDL-original-tagged-source-candidates/sdl2-mixer-2.8.2-ORIGINAL-LICENSE.txt",
    "SDL-original-tagged-source-candidates/sdl2-ttf-2.24.0-ORIGINAL-LICENSE.txt",
    "SIX_ORIGINAL_SOURCE_CANDIDATE_SHA256SUMS.txt",
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_file(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size < 100:
        raise ValueError("Source file missing or linked: " + str(path))
    if sha(path) != expected:
        raise ValueError("Not original SHA-pinned upstream source: " + path.name)


def archive_members(path):
    with tarfile.open(path, "r:*") as arc:
        return {n.name for n in arc.getmembers() if n.isfile()}


def stage(source_root, mpg123, output):
    source_root, mpg123, output = map(Path, (source_root, mpg123, output))
    if not source_root.is_dir() or source_root.is_symlink() or output.exists():
        raise ValueError("Required original source directory and fresh output")
    strict_file(mpg123, SOURCE_ARCHIVES["mpg123-1.33.7.tar.bz2"])
    pygame = source_root / "pygame-ce-2.5.8-tagged-upstream-source.tar.gz"
    strict_file(pygame, SOURCE_ARCHIVES[pygame.name])
    pygame_members = archive_members(pygame)
    if ("pygame-ce-2.5.8/docs/LGPL.txt" not in pygame_members
            or "pygame-ce-2.5.8/docs/licenses/LICENSE.mpg123.txt"
               not in pygame_members
            or "pygame-ce-2.5.8/src_c/base.c" not in pygame_members):
        raise ValueError("pygame original C source or LGPL dependency text absent")
    mpg = archive_members(mpg123)
    if (not any(x.endswith("/COPYING") for x in mpg)
            or not any(x.endswith("/src/libmpg123/frame.c") for x in mpg)):
        raise ValueError("Original mpg123 1.33.7 C sources or LGPL COPYING absent")
    for relative, digest in SOURCE_ARCHIVES.items():
        if relative == mpg123.name:
            continue
        strict_file(source_root / relative, digest)
    for relative in EVIDENCE:
        p = source_root / relative
        if p.is_symlink() or not p.is_file():
            raise ValueError("Original source and notice evidence missing: " + relative)
    manifest = json.loads(
        (source_root / EVIDENCE[0]).read_text("utf-8"))
    if (manifest.get("status") !=
            "UNRELEASED_3_1_SDL_OBSERVED_VERSION_SOURCE_CANDIDATES"
            or manifest.get("original_binary_source_correspondence_verified") is not False
            or manifest.get("redistribution_approved") is not False):
        raise ValueError("Unexpected origin or forged rights approval in SDL source manifest")
    output.mkdir(parents=True)
    sources = output / "original-sources"
    sources.mkdir()
    for relative in SOURCE_ARCHIVES:
        src = mpg123 if relative == mpg123.name else source_root / relative
        dest = sources / Path(relative).name
        shutil.copyfile(src, dest)
    notices = output / "notices-and-manifests"
    notices.mkdir()
    for relative in EVIDENCE:
        shutil.copyfile(source_root / relative, notices / Path(relative).name)
    receipts = {
        "status": "SOURCE_INPUTS_HASH_VERIFIED_NO_LEGAL_APPROVAL",
        "application_version": "3.1.0",
        "exact_application_source_revision": APP_SOURCE,
        "source_archives": {Path(k).name: v for k, v in SOURCE_ARCHIVES.items()},
        "original_source_archive_review_run": 42909893531,
        "original_installer_qa_run": 43140637755,
        "full_library_source_match_independently_proven": False,
        "complete_lgpl_redistribution_approved": False,
        "real_controller_hardware_verified": False,
        "public_release_approved": False,
    }
    (output / "SOURCE_RECEIPT.json").write_text(
        json.dumps(receipts, indent=2) + "\n", "utf-8")
    summary = [
        "# Anything Plays 3.1.0 — Original pygame, SDL and mpg123 sources",
        "",
        "This bundle preserves original SHA-256-pinned upstream source and license",
        "candidates for the new 3.1.0 controller dependencies. The original app",
        "source and packaging tools are publicly available at:",
        f"https://github.com/MasynNay/anything-plays/tree/{APP_SOURCE}",
        "",
        "Eleven original Libretro emulator core families, source archives and",
        "license notices remain available alongside the app at:",
        "https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources",
        "OpenCV 4.14.0.94 original source and Windows packaging patch are",
        "documented and linked at:",
        "https://github.com/MasynNay/anything-plays/blob/main/docs/V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md",
        "",
        "pygame-ce 2.5.8 LGPL 2.1 or later. Bundled mpg123 is also LGPL 2.1;",
        "SDL 2.x and its extension libraries use separate license texts.",
        "All archives in this bundle are original upstream source snapshots.",
        "For actual installed module replacement examples on four native OSes:",
        "https://github.com/MasynNay/anything-plays/blob/main/docs/V3_1_RELEASE_ACCEPTANCE.md",
        "",
        "Important: these are source candidates and convenience access, NOT",
        "independent proof of binary source correspondence or legal clearance",
        "for every native/transitive component. Free noncommercial distribution",
        "of the emulator binaries remains subject to all applicable licenses.",
        "",
    ]
    (output / "README.md").write_text("\n".join(summary), "utf-8")
    checks = sorted(p for p in output.rglob("*") if p.is_file())
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{sha(p)}  {p.relative_to(output).as_posix()}\n" for p in checks),
        "ascii",
    )
    return receipts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", required=True, type=Path)
    p.add_argument("--mpg123", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = stage(args.source_root, args.mpg123, args.output)
    print(json.dumps(result, indent=2))
    print("Source archives staged and SHA-256-verified; legal approval remains separate.")


if __name__ == "__main__":
    main()
