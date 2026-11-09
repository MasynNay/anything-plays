"""Research-only Linux native Libretro candidates that avoid noncommercial core licenses.

These are NOT v3.0 production inputs and this tool grants no distribution
rights. Download the original live nightly binaries for isolated *CI only*
tests, write byte-exact SHA256 evidence, and NEVER upload the DLL/SO itself.
The candidate source-to-build correspondence is unknown until independently
reproduced from source and reviewed by a qualified licensing reviewer.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile

BASE = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/"
MAX_ZIP = 32 * 1024 * 1024
MAX_ELF = 64 * 1024 * 1024
CANDIDATES = {
    "snes": {
        "native_name": "bsnes_libretro.so",
        "source": "https://github.com/libretro/bsnes",
        "license": "GPLv3",
        "systems": ("snes",),
    },
    "sega": {
        "native_name": "blastem_libretro.so",
        "source": "https://github.com/libretro/blastem",
        "license": "GPLv3",
        "systems": ("genesis", "mastersystem", "gamegear", "sg1000"),
    },
}

def checked_candidate_zip(name, payload):
    if name not in CANDIDATES:
        raise ValueError("Unknown alternative emulation core")
    if not isinstance(payload, bytes) or not 10000 < len(payload) <= MAX_ZIP:
        raise ValueError("Candidate ZIP is missing or exceeds size limits")
    target = CANDIDATES[name]["native_name"]
    with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
        infos = bundle.infolist()
        if len(infos) != 1 or infos[0].filename != target or infos[0].is_dir():
            raise ValueError("Candidate ZIP must contain exactly one named native Linux core")
        item = infos[0]
        if not 10000 < item.file_size < MAX_ELF or item.compress_size > MAX_ZIP:
            raise ValueError("Candidate native binary outside safe size limits")
        if item.external_attr >> 16 & 0o170000 == 0o120000:
            raise ValueError("Native core ZIP symlink prohibited")
        native = bundle.read(item)
    if not native.startswith(b"\x7fELF"):
        raise ValueError("Candidate must be a real Linux ELF shared library")
    return native

def stage_candidate(name, output, *, source_bytes=None):
    if name not in CANDIDATES:
        raise ValueError("Unknown alternative native core")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Candidate staging directory must not already exist")
    output.mkdir(parents=True, exist_ok=False)
    spec = CANDIDATES[name]
    url = BASE + spec["native_name"] + ".zip"
    if source_bytes is None:
        req = Request(url, headers={"User-Agent": "AnythingPlays-3.0-GPL-candidate-research"})
        with urlopen(req, timeout=60) as response:
            source_bytes = response.read(MAX_ZIP + 1)
    native = checked_candidate_zip(name, source_bytes)
    library = output / spec["native_name"]
    library.write_bytes(native)
    evidence = {
        "status": "GPL-ALTERNATIVE-CANDIDATE-UNAPPROVED",
        "source_url": spec["source"],
        "archive_url": url,
        "candidate_core": library.name,
        "native_elf_sha256": hashlib.sha256(native).hexdigest(),
        "native_elf_bytes": len(native),
        "original_zip_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "original_zip_bytes": len(source_bytes),
        "license_index_label": spec["license"],
        "systems_under_test": list(spec["systems"]),
        "binary_source_correspondence_verified": False,
        "redistribution_license_review_complete": False,
        "combined_gpl_family_license_review_complete": False,
        "physical_hardware_qa_complete": False,
        "public_release_approved": False,
        "selected_for_release": False,
        "notes": "Original mutable buildbot candidate for isolated compatibility testing only.",
    }
    (output / "UNAPPROVED_CANDIDATE.json").write_bytes(
        (json.dumps(evidence, indent=2, sort_keys=True)+"\n").encode("utf-8"))
    return evidence

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    p.add_argument("--output", type=Path, required=True)
    a=p.parse_args(argv)
    result=stage_candidate(a.candidate, a.output)
    print(f"{a.candidate}: staged test-only {result['candidate_core']} "
          f"SHA256 {result['native_elf_sha256']}; rights NOT APPROVED.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
