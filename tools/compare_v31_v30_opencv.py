"""Compare exact stable 3.0 and private final 3.1.0 frozen OpenCV runtimes.

The check is read-only. Matching filenames, ABI tags or checksums alone
cannot establish replaceability, corresponding source or distribution rights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

RISKY = ("ffmpeg", "libavcodec", "libavformat", "libavutil", "libavdevice",
         "libswscale", "libswresample", "libx264", "libx265", "gstreamer")
CODEC_RELATED = (*RISKY, "libaom", "libdav1d", "libvpx")
STATUS = "PRIVATE_3_0_VS_3_1_OPENCV_REUSE_FEASIBILITY_UNAPPROVED"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(2 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def relevant(relative):
    p = relative.lower().split("/")
    last = p[-1]
    return ("cv2" in p or "opencv_python_headless.libs" in p
            or last.startswith("libopencv") or last.startswith("opencv_videoio_"))


def scan(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Expected an extracted, unlinked, native frozen application")
    files, symlinks = [], []
    for parent, directories, names in os.walk(root, topdown=True, followlinks=False):
        here = Path(parent)
        for d in list(directories):
            if (here / d).is_symlink():
                directories.remove(d)
                symlinks.append((here/d).relative_to(root).as_posix())
        directories.sort()
        for name in sorted(names):
            file = here / name
            relative = file.relative_to(root).as_posix()
            if file.is_symlink():
                if relevant(relative):
                    symlinks.append(relative)
                continue
            if not relevant(relative) or not file.is_file():
                continue
            files.append({"path": relative, "sha256": sha256(file),
                          "size_bytes": file.stat().st_size})
    if not files:
        raise ValueError("No frozen OpenCV files in native application")
    risky = sorted(x["path"] for x in files if any(t in x["path"].lower() for t in RISKY))
    codecs = sorted(x["path"] for x in files if any(t in x["path"].lower() for t in CODEC_RELATED))
    native = [x["path"] for x in files if x["path"].lower().endswith((".so",".pyd",".dylib",".dll"))
              or ".so." in x["path"].lower()]
    return {"files": files, "symlinks": sorted(symlinks),
            "total_files": len(files), "native_file_count": len(native),
            "native_filenames": native, "risky_codec_paths": risky,
            "codec_related_paths": codecs}


def compare(stable, final, *, platform, final_source_sha):
    if platform not in ("linux-x64", "windows-x64", "macos-arm64", "macos-x64"):
        raise ValueError("Unexpected frozen target")
    if final_source_sha != "d852de9a513f83a329c14647ddc86bf3690fb5f5":
        raise ValueError("Only the exact reviewed 3.1 source input is accepted")
    old, new = scan(Path(stable)), scan(Path(final))
    old_hashes = {x["sha256"] for x in old["files"]}
    common_native = sorted(x["path"] for x in new["files"]
                           if x["sha256"] in old_hashes
                           and x["path"] in new["native_filenames"])
    return {
        "schema_version": 1, "status": STATUS,
        "target": platform, "final_source_revision": final_source_sha,
        "stable_3_0_opencv": old, "final_3_1_opencv": new,
        "identical_native_file_hashes": common_native,
        "stable_has_ffmpeg_or_gpl_codec_name_candidates":
            bool(old["risky_codec_paths"]),
        "final_has_ffmpeg_or_gpl_codec_name_candidates":
            bool(new["risky_codec_paths"]),
        "old_native_3_0_reusable_without_rebuild_or_test": False,
        "binary_corresponding_source_verified": False,
        "technical_replacement_and_camera_verified": False,
        "redistribution_approved": False,
        "public_release_approved": False,
        "next_check": "Inspect exact stable 3.0 custom OpenCV provenance, Python ABI, "
                      "copied wheel runtime linkage and real camera backend. "
                      "Do not graft into published 3.1 without new installed QA.",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stable", type=Path, required=True)
    p.add_argument("--final", type=Path, required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    a=p.parse_args()
    r=compare(a.stable,a.final,platform=a.target,final_source_sha=a.source_sha)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+"\n","utf-8")
    print(a.target,"stable OpenCV files",r["stable_3_0_opencv"]["total_files"],
          "final",r["final_3_1_opencv"]["total_files"])
    print("Risky names stable",len(r["stable_3_0_opencv"]["risky_codec_paths"]),
          "final",len(r["final_3_1_opencv"]["risky_codec_paths"]))
    print("No binary reuse, GPL review or public release approval is inferred.")


if __name__=="__main__":
    main()
