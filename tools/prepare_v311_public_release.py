"""Convert exact privately verified 3.1.1 review bytes into public release assets.

Preserves original third-party source archives verbatim from 3.1.0.
Does not give any legal compliance guarantee: displays licensing/physical QA
limits and requires full source/core/frozen-Tk receipts from *four* hosts.
Run ONLY after verifying exact successfully completed original CI source SHA.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from tools.stage_v311_private_release_review import (
    SOURCE_ZIP, SOURCE_ZIP_SHA, STAGED_STATUS,
)
from tools.verify_v311_stable_source_stage import INSTALLERS, digest

SOURCE_RE = re.compile(r"[0-9a-f]{40}\Z")
OUTPUT_FILES = {
    *INSTALLERS.values(),SOURCE_ZIP,"FINAL_QA_MANIFEST.json",
    "FINAL_SOURCE_ACCESS_REVIEW.md","SHA256SUMS.txt",
}

def read_review(root, source_sha):
    root=Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Missing actual original eight-file private review")
    inputs={p.name:p for p in root.iterdir()}
    required={
        *INSTALLERS.values(),SOURCE_ZIP,
        "V311_PRIVATE_RELEASE_REVIEW_MANIFEST.json",
        "V311_SOURCE_ACCESS_REVIEW_DRAFT.md","SHA256SUMS.txt",
    }
    if set(inputs)!=required:
        raise ValueError("Unexpected/missing private reviewed source or installer asset")
    for p in inputs.values():
        if not p.is_file() or p.is_symlink() or p.stat().st_size<=0:
            raise ValueError("Unsafe or empty private staged asset "+p.name)
    checks=(root/"SHA256SUMS.txt").read_text("ascii").splitlines()
    hashes={}
    for line in checks:
        if not re.fullmatch(r"[0-9a-f]{64}  [A-Za-z0-9_.-]+",line):
            raise ValueError("Unsafe private source checksum manifest")
        sha,name=line.split("  ")
        if name in hashes or name=="SHA256SUMS.txt":
            raise ValueError("Duplicate or self-referential source checksum")
        hashes[name]=sha
    if set(hashes)!=required-{"SHA256SUMS.txt"}:
        raise ValueError("Private staged SHA256 list not exhaustive")
    for name,sha in hashes.items():
        if digest(inputs[name])!=sha:
            raise ValueError("Original verified QA bytes corrupted: "+name)
    if hashes[SOURCE_ZIP]!=SOURCE_ZIP_SHA:
        raise ValueError("Original LGPL source archive changed")
    manifest=json.loads(inputs["V311_PRIVATE_RELEASE_REVIEW_MANIFEST.json"].read_text("utf-8"))
    if (not isinstance(manifest,dict) or manifest.get("status")!=STAGED_STATUS
            or manifest.get("source_revision")!=source_sha
            or manifest.get("version")!="3.1.1"
            or manifest.get("public_release_approved") is not False
            or manifest.get("complete_corresponding_source_and_relink_review_approved") is not False
            or manifest.get("real_frozen_gui_tests_passed_on_four_native_hosts") is not True):
        raise ValueError("Private full-source QA manifest is untrusted or unverified")
    entries=manifest.get("native_installers")
    if not isinstance(entries,list) or len(entries)!=4:
        raise ValueError("All four native 3.1.1 full installers required")
    seen=set()
    for item in entries:
        if not isinstance(item,dict):
            raise ValueError("Malformed native QA entry")
        target=item.get("target")
        if target not in INSTALLERS or target in seen:
            raise ValueError("Unknown/duplicate native 3.1.1 target")
        seen.add(target)
        name=INSTALLERS[target]
        expected={
            "installer":name, "sha256":hashes[name],
            "app_source_sha":source_sha,"native_core_count":11,
            "console_profiles":18,"installed_frozen_gui_verified":True,
        }
        for key,value in expected.items():
            if type(item.get(key)) is not type(value) or item.get(key)!=value:
                raise ValueError("Altered native core/source evidence "+target+"/"+key)
    if seen!=set(INSTALLERS):
        raise ValueError("Missing native platform")
    return manifest,hashes


def package(root, output, source_sha, qa_run, *, authorized):
    if not isinstance(source_sha,str) or SOURCE_RE.fullmatch(source_sha) is None:
        raise ValueError("Exact forty-character source revision required")
    if not isinstance(qa_run,int) or qa_run<=0:
        raise ValueError("Exact origin QA workflow run required")
    if authorized is not True:
        raise ValueError("Owner has not explicitly authorized this exact scoped release")
    root,output=Path(root),Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite any existing public release output")
    private,hashes=read_review(root,source_sha)
    # Original image/libraries source companion remains the SAME 3.1.0 ZIP
    # (whose internal provenance document *correctly* labels 3.1.0).
    # The 3.1.1 Python app itself is supplied as GitHub's tag source archive.
    output.mkdir(parents=True)
    for filename in (*INSTALLERS.values(),SOURCE_ZIP):
        shutil.copyfile(root/filename, output/filename)
        if digest(output/filename)!=hashes[filename]:
            raise ValueError("Copied original native installer/source changed")
    inventory={
        "schema_version":1,
        "status":"PASSED_SCOPED_NATIVE_RELEASE_QA_WITH_HARDWARE_LIMITATIONS",
        "release_version":"3.1.1",
        "release_tag":"v3.1.1",
        "source_revision":source_sha,
        "original_qa_run_id":qa_run,
        "original_qa_url":f"https://github.com/MasynNay/anything-plays/actions/runs/{qa_run}",
        "native_installers":private["native_installers"],
        "original_unchanged_3_1_0_source_companion":SOURCE_ZIP,
        "original_source_companion_sha256":SOURCE_ZIP_SHA,
        "new_application_source_is_exact_release_git_tag":True,
        "native_core_families":11,
        "console_profiles":18,
        "original_core_bytes_inherited_from_verified_3_1_0":True,
        "native_gui_and_stream_mode_passed_on_four_hosts":True,
        "camera_driver_error_and_save_safety_ci_passed":True,
        "physical_controller_hardware_accepted":False,
        "physical_webcam_accepted":False,
        "retail_gameplay_save_audio_all_hosts_accepted":False,
        "complete_native_corresponding_source_proven_reproducible":False,
        "all_transitive_lgpl_replacements_verified":False,
        "noncommercial_nonpromotional_release_only":True,
        "owner_scoped_release_authorized":True,
    }
    (output/"FINAL_QA_MANIFEST.json").write_text(
        json.dumps(inventory,indent=2)+"\n","utf-8")
    source_note=f"""# Anything Plays 3.1.1 — source and licensing disclosure

**This is a free, noncommercial maintenance release.** Native emulators,
artwork, pygame, SDL, mpg123 and OpenCV have separate copyright terms.
The original Python application is MIT licensed; that does not relicense
third-party material.

## Exact new application source
Release tag: https://github.com/MasynNay/anything-plays/tree/{source_sha}

All four complete 3.1.1 installers, installed frozen GUI/Stream Mode
checks, and original native core fingerprints were verified in:
https://github.com/MasynNay/anything-plays/actions/runs/{qa_run}

## Original third-party libraries and source access
The bundled `{SOURCE_ZIP}` is **byte-identical** to the source
archive first publicly provided with stable 3.1.0. Its SHA256 is
`{SOURCE_ZIP_SHA}`. Its internal manifest intentionally still
identifies 3.1.0; do not treat it as a newly rebuilt 3.1.1 archive.
Those upstream pygame-ce 2.5.8, SDL 2.x and mpg123 1.33.7 sources and
notices are reused because the original frozen libraries remain
at the same reviewed dependency versions.

Eleven source-built libretro emulator families were copied unchanged
from verified public 3.1.0 and independently checked on each platform.
Core original sources and separate upstream copyright notices:
https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources
OpenCV source reproduction:
https://github.com/MasynNay/anything-plays/blob/{source_sha}/docs/V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md
Recipient LGPL rebuild and modified-library replacement instructions:
https://github.com/MasynNay/anything-plays/blob/{source_sha}/docs/V3_1_LGPL_REBUILD_REPLACEMENT.md

The library licenses allow modification according to their own terms.
Prior 3.1 tests successfully replaced a deliberately modified genuine
pygame CE native extension, but **not** every ABI-compatible SDL/mpg123
library replacement was independently exercised. These source archives
are reviewed upstream source versions, not a universal byte-for-byte
reproducible build or legal compliance warranty. Respect all individual
core licenses; no commercial distribution rights are offered.

## Hardware and end-user QA boundaries
Four native operating-system runners verified source, eleven core
families, versioned upgrade identity and actual Tk+Stream Mode launch.
Native controller/webcam faults and long virtual-time input/save
regressions were exercised. Physical USB/Bluetooth hardware pairing,
real camera capture, licensed game compatibility, audio and game saves
across all four real devices remain unverified. Problems may be
reported at https://github.com/MasynNay/anything-plays/issues.
"""
    (output/"FINAL_SOURCE_ACCESS_REVIEW.md").write_text(source_note,"utf-8")
    names=[p for p in output.iterdir()]
    (output/"SHA256SUMS.txt").write_text("".join(
        f"{digest(p)}  {p.name}\n" for p in sorted(names,key=lambda x:x.name)
    ),"ascii")
    if {p.name for p in output.iterdir()}!=OUTPUT_FILES:
        raise ValueError("Unexpected public release asset set")
    return inventory


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--qa-run",required=True,type=int)
    p.add_argument("--authorized",action="store_true")
    a=p.parse_args()
    result=package(a.review,a.output,a.source_sha,a.qa_run,
                   authorized=a.authorized)
    print("Prepared exact scoped 3.1.1 release:",result["source_revision"],
          len(result["native_installers"]),"native platforms, eight assets.")


if __name__=="__main__":
    main()
