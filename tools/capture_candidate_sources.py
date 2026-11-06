"""Archive the exact upstream Git source trees reported by candidate cores.

This preserves source bytes and verified Git commit IDs, not a proof that
the third-party buildbot used only these bytes when compiling the ZIPs.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import tarfile

from tools.core_release_lock import CORE_NAMES, LOCK_PATH
from tools.stage_candidate_assets import sha256_file

EXPECTED_REPOS = {
    "mgba": "https://github.com/libretro/mgba",
    "snes9x": "https://github.com/libretro/snes9x",
}
REQUIRED_TARGETS = {"windows-x86_64", "linux-x86_64",
                    "macos-arm64", "macos-x86_64"}


def source_revisions(lock):
    """All architectures must declare the same verified 40-character Git IDs."""
    targets = lock.get("targets", {})
    if set(targets) != REQUIRED_TARGETS:
        raise ValueError("Incomplete four-target source lock")
    sources = {}
    for name in CORE_NAMES:
        observations = set()
        for target in REQUIRED_TARGETS:
            record = targets[target][name]
            repo = record.get("source_repository_url")
            sha = record.get("source_commit_sha")
            if repo != EXPECTED_REPOS[name]:
                raise ValueError(f"Unexpected upstream source for {name}: {repo}")
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise ValueError(f"Missing source SHA for {name}")
            observations.add(sha)
        if len(observations) != 1:
            raise ValueError(f"Architecture source revisions disagree: {name}")
        sources[name] = {"source_repository_url": EXPECTED_REPOS[name],
                         "source_commit_sha": next(iter(observations))}
    return sources


def run(command, *, cwd=None, stdout=None):
    subprocess.run(command, cwd=cwd, stdout=stdout, check=True)


def capture_sources(lock, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sources = source_revisions(lock)
    verified = []
    with TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        for name, record in sorted(sources.items()):
            sha = record["source_commit_sha"]
            checkout = temporary / name
            run(["git", "init", "-q", str(checkout)])
            run(["git", "remote", "add", "origin", record["source_repository_url"]],
                cwd=checkout)
            run(["git", "fetch", "--depth=1", "--no-tags", "origin", sha],
                cwd=checkout)
            run(["git", "checkout", "--detach", "--quiet", "FETCH_HEAD"],
                cwd=checkout)
            observed = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
            ).strip()
            if observed != sha:
                raise ValueError(f"Source checkout SHA mismatch: {name}")
            prefix = f"{name}-source-{sha}/"
            tarpath = temporary / f"{name}.tar"
            with tarpath.open("wb") as handle:
                run(["git", "archive", "--format=tar", "--prefix=" + prefix, "HEAD"],
                    cwd=checkout, stdout=handle)
            archive = output / f"source-{name}-{sha}.tar.gz"
            with tarpath.open("rb") as original, archive.open("wb") as target:
                with gzip.GzipFile(fileobj=target, mode="wb", filename="", mtime=0) as zipped:
                    shutil.copyfileobj(original, zipped)
            with tarfile.open(archive, "r:gz") as contents:
                if prefix + "LICENSE" not in contents.getnames():
                    raise ValueError(f"Missing upstream LICENSE in {name} snapshot")
                if name == "snes9x" and prefix + "filter/snes_ntsc-license.txt" not in contents.getnames():
                    raise ValueError("Missing LGPL source notice in Snes9x snapshot")
            verified.append({
                "name": name,
                "source_repository_url": record["source_repository_url"],
                "source_commit_sha": sha,
                "file": archive.name,
                "sha256": sha256_file(archive),
                "size_bytes": archive.stat().st_size,
            })
    status = {
        "schema_version": 1,
        "source_git_commits_verified": True,
        "independent_binary_to_source_build_match_verified": False,
        "redistribution_approved": False,
        "source_snapshots": verified,
    }
    (output / "SOURCE_SNAPSHOT_PROVENANCE.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    (output / "SOURCE_SNAPSHOT_SHA256SUMS.txt").write_text(
        "".join(f"{x['sha256']}  {x['file']}\n" for x in verified),
        encoding="utf-8"
    )
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    print(json.dumps(capture_sources(lock, args.output), indent=2))


if __name__ == "__main__":
    main()
