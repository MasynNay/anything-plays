"""Validate release-approval commits without an impossible self-referential Git SHA.

A reviewed application source commit can precede final approval-file commits:
the final commit containing its own source-lock SHA cannot have that same SHA.
Allow ONLY the explicitly enumerated approval metadata files to change after
the separately reviewed executable-source commit. ALL runtime, package,
native-core tooling, dependencies, assets and license text must be unchanged.

This verifies the repository's actual Git content, not an attestation flag.
No distribution permission or independent source legal review is conferred.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
REVIEW_ONLY_FILES = frozenset({
    "config/v3.0-core-lock.json",
    "config/v3.0-release-acceptance.json",
    "config/v3.0-corresponding-source-inventory.json",
    "docs/V3_LICENSE_COMPATIBILITY_APPROVED.md",
    "docs/V3_RELEASE_NOTES_APPROVED.md",
    "CONTINUE_HERE.md",
})


def _git(repo, *args, allow_nonzero=False):
    done = subprocess.run(
        ["git", *args], cwd=repo,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=25,
    )
    if done.returncode and not allow_nonzero:
        tail = done.stderr.decode("utf-8", "replace")[-600:]
        raise ValueError(f"Reviewed source Git verification failed: {tail}")
    return done


def verify_runtime_code_unchanged(reviewed_source_commit, actual_build_commit,
                                   *, repo=ROOT):
    """Reject ANY changed build input between the reviewed and published code.

    Tests and unrelated docs are deliberately NOT ignored: approval metadata
    must be explicitly whitelisted, or the reviewer should pin a newer source
    commit. The actual HEAD and both tree identities are checked using Git.
    """
    for label, value in (
        ("Reviewed source", reviewed_source_commit),
        ("Actual build", actual_build_commit),
    ):
        if not isinstance(value, str) or not COMMIT.fullmatch(value):
            raise ValueError(f"{label} must be an immutable full Git commit SHA")
    repo = Path(repo).resolve()
    if (not repo.is_dir() or
            _git(repo, "rev-parse", "--show-toplevel").stdout.decode("utf-8").strip()
            != str(repo)):
        raise ValueError("Cannot verify source outside the exact checkout root")
    head = _git(repo, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    if head != actual_build_commit:
        raise ValueError("Actual application source revision is not checkout HEAD")
    for label, value in (("reviewed", reviewed_source_commit),
                         ("actual", actual_build_commit)):
        if _git(repo, "cat-file", "-t", value).stdout.strip() != b"commit":
            raise ValueError(f"{label} source is not a real Git commit")
    # The production preflight must run on an unmodified tracked checkout.
    # Untracked outputs are legitimate later during installer compilation.
    for args in (("diff", "--quiet"), ("diff", "--cached", "--quiet")):
        if _git(repo, *args, allow_nonzero=True).returncode:
            raise ValueError("Production checkout has uncommitted tracked changes")
    changed = _git(
        repo, "diff", "--name-only", "--no-renames", "-z",
        reviewed_source_commit, actual_build_commit,
    ).stdout
    names = sorted({name.decode("utf-8") for name in changed.split(b"\x00") if name})
    unauthorized = sorted(set(names) - REVIEW_ONLY_FILES)
    if unauthorized:
        raise ValueError(
            "Unreviewed application/build source differs from pinned approved "
            "commit: " + ", ".join(unauthorized[:20])
        )
    return {
        "status": "REVIEWED-APPLICATION-BUILD-TREE-BYTE-IDENTICAL-OUTSIDE-APPROVAL-METADATA",
        "reviewed_application_source_commit": reviewed_source_commit,
        "actual_build_commit": actual_build_commit,
        "metadata_only_git_differences": names,
        "runtime_and_packaging_source_unchanged": True,
        "release_approval_automatically_granted": False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reviewed-source-commit", required=True)
    p.add_argument("--actual-build-commit", required=True)
    p.add_argument("--checkout", type=Path, default=ROOT)
    args=p.parse_args(argv)
    try:
        report=verify_runtime_code_unchanged(
            args.reviewed_source_commit,
            args.actual_build_commit, repo=args.checkout,
        )
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
        p.exit(1, f"REVIEWED APP SOURCE IDENTITY NOT PROVEN: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
