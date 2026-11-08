"""Reconcile the exact 11th source identity from independently built PCE CI.

Preserves all 40 unaffected native core records and four Dolphin Sys records,
then substitutes ONLY the four TEST-ONLY source-built PCE native identities.
A valid source-built candidate is NOT an approval for GPL/noncommercial mixed
distribution; source correspondence and redistribution flags remain false.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

from tools.v30_pce_candidate import load_index, TARGETS as PCE_TARGETS
from tools.v30_release_lock import CORE_NAMES, TARGETS

TARGET_FROM_REVIEW = {
    "windows-x86_64": "windows-x64",
    "linux-x86_64": "linux-x64",
    "macos-arm64": "macos-arm64",
    "macos-x86_64": "macos-x64",
}
SHA = re.compile(r"[a-f0-9]{64}\Z")
RESULT = "UNAPPROVED-11-SOURCE-IDENTITY-REVIEW-REPLACEMENT-CANDIDATE"


def reconcile(base, candidates, trial_evidence):
    if (not isinstance(base, dict)
            or base.get("schema_version") != 1
            or base.get("status") != "UNAPPROVED-SOURCE-REVIEW-CANDIDATE"
            or base.get("native_core_count") != 11
            or base.get("system_profile_count") != 18
            or base.get("source_snapshots_captured") != 10
            or base.get("source_snapshots_missing") != ["mednafen_pce_fast"]):
        raise ValueError("Expected original independently audited 10/11 source matrix")
    for key in (
        "approved_for_public_binary_distribution",
        "corresponding_source_inventory_verified",
        "independent_binary_to_source_match_proven",
    ):
        if base.get(key) is not False:
            raise ValueError("Original source candidate cannot claim release approval")
    existing = base.get("targets")
    if not isinstance(existing, dict) or set(existing) != TARGETS:
        raise ValueError("Base source matrix must cover all four architectures")
    if not isinstance(trial_evidence, dict) or set(trial_evidence) != set(PCE_TARGETS):
        raise ValueError("Missing four successfully integrated PCE platform trials")
    if (candidates.get("approved_for_public_binary_distribution") is not False
            or candidates.get("mixed_license_combined_distribution_reviewed") is not False
            or candidates.get("new_binaries_built_from_pinned_source") is not True):
        raise ValueError("Pinned-source PCE candidate isn't an unapproved source-built revision")
    updated = copy.deepcopy(base)
    replaced = {}
    for full_target, trial_target in sorted(TARGET_FROM_REVIEW.items()):
        target_record = updated["targets"][full_target]
        rows = target_record.get("cores")
        if (not isinstance(rows, dict) or set(rows) != CORE_NAMES
                or target_record.get("dolphin_sys", {}).get("source_and_license_reviewed") is not False):
            raise ValueError(f"Missing complete original core/source review for {full_target}")
        pce = rows["mednafen_pce_fast"]
        if (pce.get("source_commit_sha") is not None
                or pce.get("source_archive_sha256") is not None
                or pce.get("source_to_binary_verified") is not False
                or pce.get("redistribution_license_reviewed") is not False
                or pce.get("source_build_dependencies_reviewed") is not False):
            raise ValueError(f"{full_target}: expected unresolved old buildbot PCE provenance")
        trial, replacement = trial_evidence[trial_target], candidates["targets"][trial_target]
        if (not isinstance(trial, dict)
                or trial.get("status") != "SOURCE-BUILT-PCE-INTEGRATION-PREVIEW-ONLY-UNAPPROVED"
                or trial.get("target") != trial_target
                or trial.get("cores") != 11 or trial.get("profiles") != 18
                or trial.get("original_other_cores_and_dolphin_archive_count") != 11
                or trial.get("gamecube_and_all_other_original_core_archives_unchanged") is not True
                or trial.get("public_release_approved") is not False
                or trial.get("mixed_license_review_complete") is not False):
            raise ValueError(f"{trial_target}: missing successful unapproved complete-core integration")
        sha = trial.get("staged_archive_sha256")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError(f"{trial_target}: missing exact staged source-built PCE ZIP hash")
        if (trial.get("native_sha256") != replacement["native_sha256"]
                or trial.get("pce_git_commit") != candidates["pinned_source_commit"]
                or trial.get("pce_source_archive_sha256") != replacement["source_archive_sha256"]
                or trial.get("substituted_core") != replacement["core_filename"]
                or trial.get("substituted_archive") != replacement["core_filename"] + ".zip"):
            raise ValueError(f"{trial_target}: archived PCE native/ZIP/source identity changed")
        for field in ("native_sha256", "original_native_archive_sha256"):
            if not isinstance(pce.get(field), str) or not SHA.fullmatch(pce[field]):
                raise ValueError(f"{full_target}: original PCE provenance missing")
        if pce["native_sha256"] == replacement["native_sha256"]:
            raise ValueError("New test source-built candidate cannot be mislabeled unchanged old binary")
        old = {
            "native_sha256": pce["native_sha256"],
            "original_native_archive_sha256": pce["original_native_archive_sha256"],
            "source_commit_sha": None,
            "source_to_binary_correspondence_resolved": False,
        }
        replaced[trial_target] = old
        pce.update({
            "native_sha256": replacement["native_sha256"],
            "original_native_archive_sha256": sha,
            "source_repository": candidates["upstream_source_repository"],
            "source_commit_sha": candidates["pinned_source_commit"],
            "source_archive_sha256": replacement["source_archive_sha256"],
            "source_archive_size_bytes": replacement["source_archive_bytes"],
            "source_built_in_isolated_original_hucard_ci": True,
            "technical_native_video_pcm_verified": True,
            # These MUST remain false pending independently approved rights
            # and corresponding source/build-dependency audits.
            "source_build_dependencies_reviewed": False,
            "source_to_binary_verified": False,
            "redistribution_license_reviewed": False,
        })
    updated.update({
        "status": RESULT,
        "source_snapshots_captured": 11,
        "source_snapshots_missing": [],
        "source_built_pce_test_run": candidates["original_run_id"],
        "source_built_pce_integration_run": 42445580786,
        "pce_source_identified_only_for_trial_replacement": True,
        "unresolved_old_pce_buildbot_source_by_target": replaced,
        "approved_for_public_binary_distribution": False,
        "corresponding_source_inventory_verified": False,
        "independent_binary_to_source_match_proven": False,
        "release_readiness_note": (
            "11 source identities now present for the NEW PCE-replacement trial only. "
            "The existing old nightly PCE source remains unknown. The other ten "
            "core source snapshots, Dolphin submodule source archives, license "
            "compatibility, source-to-native and physical acceptance remain "
            "unreviewed; no public release approved."
        ),
    })
    task = "Determine matching Beetle PCE Fast source revision from build provenance"
    existing_tasks = updated.get("unresolved_tasks")
    if not isinstance(existing_tasks, list) or existing_tasks.count(task) != 1:
        raise ValueError("Expected exactly one original missing-PCE task")
    updated["unresolved_tasks"] = [
        ("Promote source-built PCE only after reviewed licensing and 4-platform release acceptance; old nightly source remains unknown"
         if x == task else x)
        for x in existing_tasks
    ]
    return updated


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-source-review", required=True, type=Path)
    p.add_argument("--trial-evidence-directory", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("Refusing to overwrite source review evidence")
        original = json.loads(args.original_source_review.read_text(encoding="utf-8"))
        trial = {
            name: json.loads((args.trial_evidence_directory / name /
                             "PCE_SOURCE_BUILT_TRIAL.json").read_text("utf-8"))
            for name in PCE_TARGETS
        }
        result = reconcile(original, load_index(), trial)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError, TypeError, KeyError) as err:
        p.exit(1, f"PINNED PCE SOURCE DELTA REJECTED: {err}\n")
    sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"11 source identities for SOURCE-BUILT TRIAL only: {sha}; "
          "rights, unverified dependencies, old nightly source and public release remain BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
