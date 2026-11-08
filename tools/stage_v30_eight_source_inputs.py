"""Assemble COMPLETE 18-profile 11-core offline test with EIGHT source-built cores.

Research ONLY; never publicly distributes core binaries or grants any source
or license permission. Reuses original rigorously checked three-family full
offline archive builder then substitutes five more exact original Git-source
built binaries in their genuine original name slots. The unchanged native
families are mGBA, ParaLLEl-N64 and Dolphin, plus original Dolphin Sys.

The 20 original compiled source/native artifacts are from Actions run
42513615955 (not five guessed replacements for the old buildbot sources).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from anything_plays.v30_gpl_trial import MARKER
from fetch_mgba_core import V30_GPL_TRIAL_CORES
from tools.stage_v30_gpl_trial_inputs import stage_inputs, TARGET_EXT, package_native_zip
from tools.capture_v30_2d_five_source_build import CANDIDATES, PINNED_COMMITS

STATUS = "UNAPPROVED-EIGHT-SOURCE-FAMILY-FULL-3.0-OFFLINE-TEST"
ORIGINAL_RUN = 42513615955
FAMILIES = frozenset(PINNED_COMMITS)
LEFT_UNCHANGED = frozenset(("mgba", "parallel_n64", "dolphin"))
assert len(FAMILIES) == 5
assert len(FAMILIES | LEFT_UNCHANGED | {"mednafen_supafaust", "blastem", "mednafen_pce_fast"}) == 11


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_original_five_artifact(folder, name, target, extension):
    """Verify original tracked source, compiled binary, license and A/V.

    This proves a NEW source-built candidate's source/native correspondence,
    NOT the source corresponding to the prior, now discarded, buildbot core.
    """
    if name not in FAMILIES or target not in TARGET_EXT:
        raise ValueError("Unknown original five-family source candidate")
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing exact original source-built family artifact")
    marker = folder / "PINNED_ORIGINAL_SOURCE_RESEARCH_UNAPPROVED.json"
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 20000:
        raise ValueError("Missing/unsafe original source-build manifest")
    info = json.loads(marker.read_text("utf-8"))
    native_name = f"{name}_libretro{extension}"
    source_name = f"{name}-{PINNED_COMMITS[name]}-SOURCE.tar"
    repo, notice_path = CANDIDATES[name]
    if (not isinstance(info, dict)
            or info.get("schema_version") != 1
            or info.get("status") != "UNAPPROVED-ORIGINAL-5-CORE-SOURCE-NATIVE-RESEARCH"
            or info.get("candidate") != name
            or info.get("target") != target
            or info.get("original_source_repository") != f"https://github.com/{repo}"
            or info.get("exact_source_revision") != PINNED_COMMITS[name]
            or info.get("real_checkout_head_verified") is not True
            or info.get("original_source_archive") != source_name
            or info.get("native_filename") != native_name
            or info.get("original_license_source_file") != notice_path
            or info.get("original_license_notice_copied") is not (notice_path is not None)):
        raise ValueError("Wrong original Git-source candidate or platform")
    for field in (
            "binary_redistribution_approved", "combined_gpl_version_license_review_approved",
            "physical_gameplay_and_webcam_qa_approved", "production_source_to_binary_approved",
            "source_submodules_and_deps_independently_reviewed"):
        if info.get(field) is not False:
            raise ValueError("Unexpected granted third-party rights or physical QA in research")
    required = {
        marker.name, native_name, source_name,
        *(
            ["ORIGINAL_UPSTREAM_GPL_NOTICE.txt"]
            if notice_path is not None else []
        ),
    }
    reports = {
        "fceumm": ("ORIGINAL_NES_NATIVE_AV.json",),
        "stella2014": ("ORIGINAL_ATARI2600_NATIVE_AV.json",),
        "prosystem": ("ORIGINAL_ATARI7800_NATIVE_AV.json",),
        "mednafen_ngp": ("ORIGINAL_NGPC_NATIVE_AV.json",),
        "mednafen_wswan": ("ORIGINAL_WSWAN_NATIVE_AV.json", "ORIGINAL_WS_COLOR_NATIVE_AV.json"),
    }[name]
    required.update(reports)
    # Probes also write an original screen capture. It is checked for safety
    # and ignored for core identity; the original library byte hash decides.
    allowed = {
        p.name for p in folder.iterdir()
        if p.name.endswith(".png") and len(p.name) < 90
    }
    items=list(folder.iterdir())
    if (len(items)>12 or any(p.is_symlink() or not p.is_file() for p in items)
            or not required.issubset({p.name for p in items})
            or {p.name for p in items} - required - allowed):
        raise ValueError("Unexpected or missing original source/native evidence")
    def original(member, expected_sha, expected_size, max_size=130*1024*1024):
        path = folder/member
        if (path.is_symlink() or not path.is_file()
                or not 0<path.stat().st_size<max_size):
            raise ValueError(f"Unsafe source/native original: {member}")
        data=path.read_bytes()
        if len(data) != expected_size or sha(data) != expected_sha:
            raise ValueError(f"Original source/native checksum changed: {member}")
        return data
    native = original(native_name, info.get("native_sha256"), info.get("native_size_bytes"), 60*1024*1024)
    original(source_name, info.get("source_archive_sha256"),
             info.get("source_archive_size_bytes"))
    notice = None
    if notice_path is not None:
        n=folder/"ORIGINAL_UPSTREAM_GPL_NOTICE.txt"
        notice=original(n.name, info.get("original_license_notice_sha256"),
                        n.stat().st_size, 1024*1024)
        if b"GNU GENERAL PUBLIC LICENSE" not in notice or b"Version 2" not in notice:
            raise ValueError("Original GPLv2 notice lost")
    elif info.get("original_license_notice_sha256") is not None:
        raise ValueError("Stella original source license cannot be falsely inferred")
    for report in reports:
        row=json.loads((folder/report).read_text("utf-8"))
        details=row.get("details")
        child_passed = (
            details.get("playback_probe_passed") is True
            if name=="fceumm" and isinstance(details,dict)
            else isinstance(details,dict) and details.get("passed") is True
        )
        if (row.get("passed") is not True or row.get("native_exit_code") != 0
                or not child_passed):
            raise ValueError(f"Original source-built native A/V failed: {name}/{report}")
    return native, notice, info


def stage_eight(*, original_dir, snes_dir, sega_dir, pce_artifact,
                five_dirs, output, evidence, target, windows_runtime=None):
    if (os.environ.get("AP_V30_GPL_TRIAL") != "1"
            or os.environ.get("AP_V30_PINNED_PCE") != "1"
            or os.environ.get("AP_V30_PINNED_FIVE") != "1"
            or os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("ONLY complete 8-family UNAPPROVED research lane is allowed")
    output, evidence = Path(output),Path(evidence)
    if (output.exists() or output.is_symlink() or evidence.exists()
            or evidence.is_symlink() or output.resolve()==evidence.resolve()):
        raise ValueError("Both final research destination and report must be NEW")
    if not isinstance(five_dirs, dict) or set(five_dirs)!=FAMILIES:
        raise ValueError("Five exact original source build artifacts required")
    ext=TARGET_EXT[target]
    sources={}
    for name,path in sorted(five_dirs.items()):
        native,notice,info=check_original_five_artifact(path,name,target,ext)
        native_zip=package_native_zip(name,ext,native)
        sources[name]={
            "source_repository":info["original_source_repository"],
            "source_commit":info["exact_source_revision"],
            "native_filename":info["native_filename"],
            "native_sha256":info["native_sha256"],
            "source_archive_sha256":info["source_archive_sha256"],
            "native_archive_sha256":sha(native_zip),
            "original_license_notice_sha256":info["original_license_notice_sha256"],
            "original_license_notice_copied":notice is not None,
            "source_build_run_id":ORIGINAL_RUN,
            "old_unknown_source_buildbot_replaced":True,
        }
        sources[name]["_ZIP"]=native_zip
        sources[name]["_NOTICE"]=notice
    with tempfile.TemporaryDirectory(prefix="anything-plays-v30-8-original-sources-") as temp:
        tmp=Path(temp)
        intermediate=tmp/"three"
        source_row=stage_inputs(
            original_dir,snes_dir,sega_dir,intermediate,tmp/"three-proof.json",
            target,windows_runtime=windows_runtime,pce_artifact=pce_artifact)
        if source_row["original_unchanged_core_archives"]!=8:
            raise ValueError("Original complete 3-family archive set changed")
        if source_row["source_built_pce"] is None:
            raise ValueError("Source-built original PCE is missing")
        names={p.name for p in intermediate.iterdir()}
        expected_zip={f"{name}_libretro{ext}.zip" for name in V30_GPL_TRIAL_CORES}
        if not expected_zip.issubset(names):
            raise ValueError("Original full 11-native alternative ZIP set incomplete")
        output.mkdir(parents=True)
        for path in intermediate.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError("Symlinked input in preserved complete 11-native ZIP set")
            data = (
                sources[path.name.split("_libretro")[0]]["_ZIP"]
                if path.name.endswith("_libretro"+ext+".zip")
                and path.name.split("_libretro")[0] in sources
                else path.read_bytes()
            )
            (output/path.name).write_bytes(data)
        for name,row in sources.items():
            if row["_NOTICE"] is not None:
                (output/f"GPL-TRIAL-{name}-ORIGINAL-COPYING.txt").write_bytes(row["_NOTICE"])
            del row["_ZIP"]
            del row["_NOTICE"]
        source_row["source_built_remaining_five"] = sources
        source_row["original_unchanged_core_archives"] = 3
        source_row["total_source_built_core_families"] = 8
        source_row["five_source_family_run_id"] = ORIGINAL_RUN
        source_row["public_binary_distribution_approved"]=False
        source_row["combined_gpl_license_reviewed"]=False
        source_row["physical_qa_approved"]=False
        source_row["production_core_substitution_approved"]=False
        (output/MARKER).write_text(json.dumps(source_row,indent=2,sort_keys=True)+"\n","utf-8")
        evidence.parent.mkdir(parents=True,exist_ok=True)
        evidence.write_text(json.dumps(source_row,indent=2,sort_keys=True)+"\n","utf-8")
    return source_row


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("original-dir","snes-dir","sega-dir","pce-artifact","output","evidence","target"):
        p.add_argument("--"+arg,required=True)
    p.add_argument("--windows-runtime")
    for name in sorted(FAMILIES):
        p.add_argument("--"+name.replace("_","-")+"-dir",required=True)
    args=vars(p.parse_args(argv))
    five={
        n: Path(args[n+"_dir"])
        for n in FAMILIES
    }
    try:
        row=stage_eight(
            original_dir=args["original_dir"],
            snes_dir=args["snes_dir"],sega_dir=args["sega_dir"],
            pce_artifact=args["pce_artifact"],five_dirs=five,
            output=args["output"],evidence=args["evidence"],
            target=args["target"],windows_runtime=args["windows_runtime"])
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        p.exit(1,f"8-family offline 3.0 research BLOCKED: {exc}\n")
    print(f"{row['target']}: full 18-profile 11-core archive set with 8 original-source built cores, RELEASE NOT APPROVED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
