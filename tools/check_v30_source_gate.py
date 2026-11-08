"""Fail fast on unapproved 3.0 source/binary evidence *before* production builds.

Neither this CLI nor a green source CI grants a third-party license. It
checks the owner's separately reviewed files against all 44 frozen native
binary records, 4 Dolphin Sys archives and the source/archive provenance.
The existing emitter repeats these checks after each platform build.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.emit_v30_production_provenance import (
    LICENSE_REVIEW_FILE, SOURCE_FILE, validate_source_inventory,
)
from tools.v30_release_lock import LOCK_PATH, load_approved_lock


def check_approved_source_package(*, lock_path=LOCK_PATH,
                                  inventory_path=SOURCE_FILE,
                                  license_review_path=LICENSE_REVIEW_FILE):
    lock = load_approved_lock(lock_path)
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    validate_source_inventory(lock, inventory)
    review = Path(license_review_path).read_text(encoding="utf-8")
    # This confirms an identified review document was supplied; only human
    # rights holders/reviewers can determine whether its conclusion is valid.
    if (len(review) < 200
            or "APPROVED-3.0-DISTRIBUTION" not in review):
        raise ValueError("Missing independently reviewed GPL/noncommercial distribution decision")
    return {
        "native_cores": 11,
        "target_architectures": 4,
        "native_binaries_source_reviewed": 44,
        "dolphin_sys_archives_reviewed": 4,
        "public_release_approval_automatically_granted": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lock", type=Path, default=LOCK_PATH)
    p.add_argument("--inventory", type=Path, default=SOURCE_FILE)
    p.add_argument("--license-review", type=Path, default=LICENSE_REVIEW_FILE)
    a = p.parse_args(argv)
    try:
        result = check_approved_source_package(
            lock_path=a.lock, inventory_path=a.inventory,
            license_review_path=a.license_review,
        )
    except (OSError, ValueError, TypeError, KeyError) as error:
        p.exit(1, f"3.0 SOURCE RIGHTS PREFLIGHT BLOCKED: {error}\n")
    print("REVIEWED 3.0 SOURCE PACKAGE CHECKED:",
          result["native_binaries_source_reviewed"], "native cores and",
          result["dolphin_sys_archives_reviewed"], "Dolphin Sys archives;",
          "independent rights documentation must remain on record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
