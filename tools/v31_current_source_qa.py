"""Fail-closed source revision selector for refreshed, unreleased 3.1 QA.

The original RC1 assembly remains pinned to its historical immutable source.
Only the new, explicitly gated GitHub PR workflow may assemble a fresh RC
from the *exact checked-out* commit verified in both frozen stage and receipt.
A QA receipt cannot grant stable-release or native redistribution approval.
"""
from __future__ import annotations

import os
import re
import subprocess

PIN_PATTERN = re.compile(r"[a-f0-9]{40}\Z")


def reviewed_source_revision(original, *, rc1, override=None, environ=None,
                             checkout=None):
    if override is None:
        return original
    env = os.environ if environ is None else environ
    if (not rc1 or env.get("AP_V31_NEXT_QA") != "1"
            or env.get("AP_V31_RC") != "1"
            or env.get("AP_V31_FULL_TEST_CORES") != "1"
            or env.get("AP_V31_PREVIEW") == "1"
            or env.get("AP_RELEASE_BUILD") == "1"
            or env.get("AP_V30_APPROVED_RELEASE") == "1"
            or env.get("AP_V30_STABLE_CANDIDATE") == "1"):
        raise ValueError("Fresh RC source override requires nonrelease owner QA")
    if not isinstance(override, str) or PIN_PATTERN.fullmatch(override) is None:
        raise ValueError("Fresh RC source revision must be a full git SHA")
    expected = env.get("AP_V31_QA_CHECKOUT_SHA")
    if expected != override:
        raise ValueError("Candidate revision differs from pinned QA workflow commit")
    if checkout is None:
        try:
            checkout = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, timeout=15,
            ).strip()
        except (OSError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as exc:
            raise ValueError("Cannot authenticate the checked-out source") from exc
    if checkout != override:
        raise ValueError("Checked-out repository does not match frozen candidate")
    return override
