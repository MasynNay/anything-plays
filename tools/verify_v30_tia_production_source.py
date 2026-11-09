"""Verify genuine original source-built GPL2+ Tia for an exact reviewed 3.0.

Run only after the immutable 44-native distribution/source license lock has
been checked independently. This verifier never asserts legal permission or
changes any release approval bit. The pinned original source TAR, pristine
Git checkout, native architecture, original COPYING/source SPDX and actual
Atari2600 homebrew video/audio all have to correspond.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile

from tools.stage_v30_gpl_trial_inputs import TARGET_EXT
from tools.stage_v30_tia_source_overlay import (
    _source, TIA_COMMIT, TIA_REPOSITORY, TIA_INDEPENDENT_TEST_RUN,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_file(path, max_size):
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size < max_size):
        raise ValueError(f"Missing or unsafe original Tia source/native evidence: {path}")
    return path.read_bytes()


def validate_production_tia(*, source_checkout, source_tar, native,
                             playback_report, target):
    """Return original bytes/provenance for an already reviewed release lock.

    This function alone does NOT approve, stage or distribute any binary.
    The independent lock and source inventory must still match every hash.
    """
    if target not in TARGET_EXT:
        raise ValueError("Unrecognized Tia native platform")
    checkout = Path(source_checkout)
    copying, spdx = _source(checkout)
    tar_data = regular_file(source_tar, 100 * 1024 * 1024)
    with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:") as archive:
        if len(archive.getmembers()) < 7:
            raise ValueError("Incomplete original pinned Tia source TAR")
        for name, original in (
            ("COPYING", copying),
            ("src/libretro.c", spdx),
            ("README.md", regular_file(checkout / "README.md", 256 * 1024)),
        ):
            item = archive.getmember(name)
            if (not item.isfile() or item.issym() or item.islnk()
                    or item.size != len(original)):
                raise ValueError(f"Malformed Tia source TAR member: {name}")
            stream = archive.extractfile(item)
            if stream is None or stream.read(item.size + 1) != original:
                raise ValueError(f"Original pinned Git source differs from TAR: {name}")
    path = Path(native)
    extension = TARGET_EXT[target]
    if path.name != f"tia_libretro{extension}":
        raise ValueError("Compiled Tia is not the original target native")
    raw = regular_file(path, 60 * 1024 * 1024)
    headers = {
        ".so": (b"\x7fELF",),
        ".dll": (b"MZ",),
        ".dylib": (b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"),
    }
    if len(raw) < 10000 or not raw.startswith(headers[extension]):
        raise ValueError("Invalid original Tia PE/Mach-O/ELF compiled native")
    proof = json.loads(regular_file(playback_report, 512 * 1024))
    details = proof.get("details")
    if (not isinstance(details, dict) or proof.get("passed") is not True
            or proof.get("timed_out") is not False
            or proof.get("native_exit_code") != 0
            or details.get("passed") is not True
            or details.get("video_frames", 0) < 30
            or details.get("unique_frame_hashes", 0) < 2
            or details.get("pcm_nonzero_samples", 0) < 100
            or details.get("pcm_sample_peak", 0) <= 0):
        raise ValueError("Tia original homebrew video/PCM gameplay failed")
    return {
        "native": raw,
        "copying": copying,
        "source_spdx": spdx,
        "source_archive_sha256": digest(tar_data),
        "source_commit": TIA_COMMIT,
        "source_repository": TIA_REPOSITORY,
        "playback_report_sha256": digest(regular_file(playback_report, 512 * 1024)),
        "original_source_build_run_id": TIA_INDEPENDENT_TEST_RUN,
        "public_binary_distribution_approved_by_this_verifier": False,
    }
