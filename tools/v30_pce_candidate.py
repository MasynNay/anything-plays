"""Verify the four pinned-source PCE Libretro research artifacts before use.

Only for the 3.0 developer trial installer. Never certifies license compatibility,
real retail-game support, or approved distribution; never changes normal cores.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "config/v3.0-pce-pinned-source-candidates.json"
COMMIT = "2de1ce1c3f237b161c126c54ba407990bb86d1e9"
REPO = "https://github.com/libretro/beetle-pce-fast-libretro"
RUN_ID = 42444367068
SHA = re.compile(r"[a-f0-9]{64}\Z")
TARGETS = {
    "linux-x64": (".so", b"\x7fELF"),
    "windows-x64": (".dll", b"MZ"),
    "macos-arm64": (".dylib", b"\xcf\xfa\xed\xfe"),
    "macos-x64": (".dylib", b"\xcf\xfa\xed\xfe"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_index(path=INDEX):
    index = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "status": "UNAPPROVED-SOURCE-BUILT-PCE-3.0-FOUR-TARGET-CANDIDATE",
        "original_run_id": RUN_ID,
        "upstream_source_repository": REPO,
        "pinned_source_commit": COMMIT,
        "source_license": "GPL-2.0",
        "new_binaries_built_from_pinned_source": True,
        "source_equivalence_to_existing_buildbot_core_verified": False,
        "added_to_existing_preview": False,
        "approved_for_public_binary_distribution": False,
        "mixed_license_combined_distribution_reviewed": False,
        "full_real_game_acceptance_verified": False,
    }
    if not isinstance(index, dict) or any(index.get(k) != v for k, v in expected.items()):
        raise ValueError("Unapproved pinned PCE identity/status changed")
    if index.get("source_archive_name") != f"pce-fast-{COMMIT}-SOURCE.tar.gz":
        raise ValueError("Pinned PCE source archive name mismatch")
    rows = index.get("targets")
    if not isinstance(rows, dict) or set(rows) != set(TARGETS):
        raise ValueError("All four source-built PCE platforms must remain present")
    for name, row in rows.items():
        ext, _ = TARGETS[name]
        if not isinstance(row, dict) or row.get("core_filename") != "mednafen_pce_fast_libretro" + ext:
            raise ValueError(f"{name}: PCE native target filename mismatch")
        if type(row.get("artifact_id")) is not int or row["artifact_id"] <= 0:
            raise ValueError(f"{name}: missing original source-build evidence artifact")
        for field in ("native_sha256", "source_archive_sha256", "native_report_sha256"):
            if not isinstance(row.get(field), str) or not SHA.fullmatch(row[field]):
                raise ValueError(f"{name}: missing immutable {field}")
        for field in ("native_bytes", "source_archive_bytes", "native_video_frames", "native_nonzero_pcm_values"):
            if type(row.get(field)) is not int or row[field] <= 0:
                raise ValueError(f"{name}: missing original {field}")
        if row["native_bytes"] < 50_000 or row["native_video_frames"] < 300 or row["native_nonzero_pcm_values"] < 100:
            raise ValueError(f"{name}: original PCE native gameplay evidence is insufficient")
    return index


def inspect_artifact(path, target, index=None):
    """Prove source, binary, report and notices match original Actions artifact.

    Does not extract anything from an untrusted ZIP. Returns validated core
    bytes only so the caller can generate a fresh, local TEST-ONLY core ZIP.
    """
    index = load_index() if index is None else index
    if target not in TARGETS:
        raise ValueError("Unsupported PCE research platform")
    row = index["targets"][target]
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or symlinked original PCE Actions artifact")
    source_file = index["source_archive_name"]
    needed = {
        "PCE_COPYING_GPL-2.0.txt",
        "PCE_SOURCE_BUILD_UNAPPROVED.json",
        "PCE_ORIGINAL_HUCARD_NATIVE_AV.json",
        "pce-frame.png",
        row["core_filename"],
        source_file,
    }
    with zipfile.ZipFile(path) as bundle:
        entries = bundle.infolist()
        if len(entries) != len(needed) or {entry.filename for entry in entries} != needed:
            raise ValueError("PCE original artifact has missing/extra/duplicate files")
        if any(entry.is_dir() or ((entry.external_attr >> 16) & 0o170000) == 0o120000
               or entry.file_size > 32 * 1024 * 1024 for entry in entries):
            raise ValueError("Unsafe PCE original artifact entry")
        binary = bundle.read(row["core_filename"])
        source = bundle.read(source_file)
        report_bytes = bundle.read("PCE_ORIGINAL_HUCARD_NATIVE_AV.json")
        notice = bundle.read("PCE_COPYING_GPL-2.0.txt")
        provenance = json.loads(bundle.read("PCE_SOURCE_BUILD_UNAPPROVED.json"))
    if len(binary) != row["native_bytes"] or digest(binary) != row["native_sha256"]:
        raise ValueError("Pinned PCE original native library bytes changed")
    extension, magic = TARGETS[target]
    if extension == ".dylib":
        if binary[:4] not in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
            raise ValueError("PCE candidate has invalid macOS native binary magic")
    elif not binary.startswith(magic):
        raise ValueError("PCE candidate has wrong platform binary header")
    if len(source) != row["source_archive_bytes"] or digest(source) != row["source_archive_sha256"]:
        raise ValueError("Pinned PCE source archive has changed")
    if digest(report_bytes) != row["native_report_sha256"]:
        raise ValueError("Original PCE native test evidence hash changed")
    if b"GNU GENERAL PUBLIC LICENSE" not in notice or b"Version 2" not in notice:
        raise ValueError("Original PCE source GPL-2.0 notice missing")
    if (provenance.get("status") != "UNAPPROVED-EXPERIMENTAL-PINNED-PCE-SOURCE-BUILD"
            or provenance.get("target") != target
            or provenance.get("source_repository") != REPO
            or provenance.get("source_commit") != COMMIT
            or provenance.get("native_core") != row["core_filename"]
            or provenance.get("native_core_sha256") != row["native_sha256"]
            or provenance.get("source_archive_sha256") != row["source_archive_sha256"]
            or provenance.get("third_party_distribution_approved") is not False
            or provenance.get("mixed_core_licenses_reviewed") is not False):
        raise ValueError("PCE source-built evidence is altered or falsely approved")
    playback = json.loads(report_bytes)
    details = playback.get("details", {})
    if (playback.get("passed") is not True
            or not isinstance(details, dict) or details.get("passed") is not True
            or details.get("native_video_frames") != row["native_video_frames"]
            or details.get("native_nonzero_pcm_samples") != row["native_nonzero_pcm_values"]):
        raise ValueError("PCE original native video and audio evidence mismatch")
    return binary


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, default=INDEX)
    p.add_argument("--artifact", type=Path, required=True)
    p.add_argument("--target", choices=sorted(TARGETS), required=True)
    a = p.parse_args()
    native = inspect_artifact(a.artifact, a.target, load_index(a.index))
    print(f"{a.target}: verified {len(native)} original source-built PCE bytes, status UNAPPROVED")
