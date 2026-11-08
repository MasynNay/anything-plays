"""Capture reproducible candidate identities for source-built GPLv3 SNES/Sega cores.

This is a developer research lane only. Genuine reviewed corresponding
sources and a binary from the matching git checkout are retained together,
but legal redistribution of the *combined app*, effective GPL versions,
plugin linking and physical compatibility are NOT automatically approved.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

SOURCE = {
    "bsnes": {
        "repository": "https://github.com/libretro/bsnes",
        "commit": "63ee22f7af8f5d1ada295c2c98fd7bf261fa62a7",
        "license_file": "LICENSE.txt",
        "binary": "bsnes_libretro",
    },
    "blastem": {
        "repository": "https://github.com/libretro/blastem",
        "commit": "2230addc4dd74dd094fd264987fd808abba32d0e",
        "license_file": "COPYING",
        "binary": "blastem_libretro",
    },
}
EXT = {"linux-x64":".so", "windows-x64":".dll",
       "macos-arm64":".dylib", "macos-x64":".dylib"}
MAGIC = {
    ".so": (b"\x7fELF",),
    ".dll": (b"MZ",),
    ".dylib": (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
               b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
}
SHA = re.compile(r"[0-9a-f]{40}\Z")


def _git(root, *args, binary=False):
    p=subprocess.run(["git","-C",str(root),*args],check=True,
                     capture_output=True,timeout=40)
    return p.stdout if binary else p.stdout.decode("utf-8").strip()


def capture_source_built_candidate(*, source, native, output, candidate, target):
    if candidate not in SOURCE or target not in EXT:
        raise ValueError("Unsupported GPL candidate or native architecture")
    spec=SOURCE[candidate]
    root=Path(source).resolve()
    native=Path(native).resolve()
    out=Path(output).resolve()
    if any(p.is_symlink() for p in (Path(source),Path(native),Path(output))):
        raise ValueError("Source/native/output symlinks forbidden")
    if not root.is_dir() or not native.is_file() or not native.stat().st_size>40000:
        raise ValueError("Source checkout or actual compiled native binary missing")
    if native.parent!=root or native.name!=spec["binary"]+EXT[target]:
        raise ValueError("Actual compiled library not in the exact pinned source root")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("New empty evidence directory required")
    if root==out or out in root.parents or root in out.parents:
        raise ValueError("Source and output must be distinct")
    if _git(root,"rev-parse","HEAD")!=spec["commit"]:
        raise ValueError("Source revision does not match immutable GPL research pin")
    origin=_git(root,"remote","get-url","origin").rstrip("/").removesuffix(".git")
    if origin!=spec["repository"]:
        raise ValueError("Compiler source repository identity changed")
    if _git(root,"status","--porcelain","--untracked-files=no"):
        raise ValueError("Original tracked upstream source modified by build")
    lic=root/spec["license_file"]
    if not lic.is_file() or lic.is_symlink():
        raise ValueError("Missing original license text")
    licdata=lic.read_bytes()
    if b"GNU GENERAL PUBLIC LICENSE" not in licdata or b"version 3" not in licdata.lower():
        raise ValueError("Unverified original GPLv3 license notice")
    native_bytes=native.read_bytes()
    if not any(native_bytes.startswith(sig) for sig in MAGIC[EXT[target]]):
        raise ValueError("Compiled library format differs from requested platform")
    tar=_git(root,"archive","--format=tar","HEAD",binary=True)
    if not tar or len(tar)>200*1024*1024:
        raise ValueError("Upstream pinned git archive unavailable or excessive")
    with tarfile.open(fileobj=io.BytesIO(tar),mode="r:") as archive:
        members={m.name for m in archive.getmembers()}
        if spec["license_file"] not in members:
            raise ValueError("Exact original source archive lacks GPL notice")
    tarball=gzip.compress(tar,mtime=0,compresslevel=6)
    if len(tarball)>80*1024*1024:
        raise ValueError("Original source snapshot ZIP exceeds 80MB")
    out.mkdir(parents=True,exist_ok=True)
    source_name=f"{candidate}-{spec['commit']}-source.tar.gz"
    (out/source_name).write_bytes(tarball)
    shutil.copyfile(native,out/native.name)
    (out/(candidate+"-GPLv3-NOTICE.txt")).write_bytes(licdata)
    evidence={
        "status":"UNAPPROVED-RESEARCH-SOURCE-BUILT-GPLV3-ALTERNATIVE",
        "target":target,
        "candidate":candidate,
        "native_filename":native.name,
        "native_sha256":hashlib.sha256(native_bytes).hexdigest(),
        "native_size_bytes":len(native_bytes),
        "source_repository":spec["repository"],
        "source_commit":spec["commit"],
        "source_archive_filename":source_name,
        "source_archive_sha256":hashlib.sha256(tarball).hexdigest(),
        "source_archive_size_bytes":len(tarball),
        "license_filename":spec["license_file"],
        "license_sha256":hashlib.sha256(licdata).hexdigest(),
        "compiled_from_exact_pinned_source_checkout":True,
        "matches_current_3_0_shipped_libretro_library":False,
        "four_platform_gameplay_verified":False,
        "complete_corresponding_source_and_dependencies_reviewed":False,
        "combined_gpl_2_and_gpl_3_license_reviewed":False,
        "source_to_binary_independently_reproducible":False,
        "public_binary_distribution_approved":False,
        "3_0_native_core_substitution_approved":False,
        "notes":"Candidate source+binary preserved for independent build/licensing review ONLY.",
    }
    (out/"PINNED_GPL_ALTERNATIVE_SOURCE_BUILD_UNAPPROVED.json").write_bytes(
        (json.dumps(evidence,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    lines=[]
    for path in sorted(out.iterdir()):
        if path.name=="SHA256SUMS.txt":
            continue
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (out/"SHA256SUMS.txt").write_bytes(("\n".join(lines)+"\n").encode("ascii"))
    return evidence


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--native",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--candidate",required=True,choices=sorted(SOURCE))
    p.add_argument("--target",required=True,choices=sorted(EXT))
    a=p.parse_args(argv)
    try:
        item=capture_source_built_candidate(source=a.source,native=a.native,
            output=a.output,candidate=a.candidate,target=a.target)
    except (OSError,ValueError,TypeError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired,tarfile.TarError) as e:
        p.exit(1,f"GPL SOURCE-BUILT CANDIDATE FAILED: {e}\n")
    print(f"Pinned {item['candidate']} native {item['native_sha256']} "
          f"source {item['source_commit']}, GPLv3 notice; 3.0 distribution NOT APPROVED")
    return 0


if __name__=="__main__":
    sys.exit(main())
