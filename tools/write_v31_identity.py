"""Produce reviewed, channel-specific identity embedded by frozen 3.1 builds.

Only use the isolated non-public mGBA build mode. Neither selecting RC1 nor
embedding the correct version name grants redistribution permission.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from anything_plays.build_identity import make_identity


def choose_channel(env):
    preview = env.get("AP_V31_PREVIEW") == "1"
    candidate = env.get("AP_V31_RC") == "1"
    if preview == candidate:
        raise ValueError("Select exactly one 3.1 build channel")
    if env.get("AP_V30_MINIMAL_CORE_BUILD") != "1":
        raise ValueError("Only isolated mGBA source-build stage allowed")
    for forbidden in (
        "AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
        "AP_V30_STABLE_CANDIDATE", "AP_V30_TEST_CORES",
        "AP_V30_GPL_TRIAL", "AP_V30_TIA_TRIAL",
    ):
        if env.get(forbidden) == "1":
            raise ValueError("3.1 candidate cannot use release/native approval flags")
    return "rc1" if candidate else "preview1"


def write_identity(destination, environ=None):
    env = os.environ if environ is None else environ
    identity = make_identity(choose_channel(env))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    value = write_identity(args.output)
    print("Frozen 3.1 identity", value["channel"],
          value["settings_namespace"], "(public release not approved)")


if __name__ == "__main__":
    main()
