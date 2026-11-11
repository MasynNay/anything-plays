"""Authenticate private 3.1.0 original-core assembly against its source build.

A correctly versioned app is not public redistribution approval. Every
full offline installer must use the exact, untouched native 3.0 source-built
core set plus the source-verified new 3.1.0 GUI/runtime for its own OS.
"""
from __future__ import annotations

import os
import re
import subprocess

STAGE_STATUS = "PRIVATE_SOURCE_STAGE_FINAL_IDENTITY_QA_ONLY"
FULL_STATUS = "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA"


def checked_final_source_revision(expected, *, environ=None, checkout=None):
    env = os.environ if environ is None else environ
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{40}", expected) is None:
        raise ValueError("Full 3.1.0 candidate requires an exact source SHA")
    for flag in ("AP_V31_FINAL_CANDIDATE", "AP_V31_FULL_TEST_CORES"):
        if env.get(flag) != "1":
            raise ValueError("Full 3.1.0 candidate missing isolated QA flag: " + flag)
    for flag in ("AP_V31_PREVIEW", "AP_V31_RC", "AP_V31_RC2",
                 "AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
                 "AP_V30_STABLE_CANDIDATE", "AP_V30_GPL_TRIAL",
                 "AP_V30_TIA_TRIAL", "AP_V30_TEST_CORES"):
        if env.get(flag) == "1":
            raise ValueError("Mixed source, release or native approval flags: " + flag)
    if env.get("AP_V31_QA_CHECKOUT_SHA") != expected:
        raise ValueError("Expected source SHA does not match the checked-out QA revision")
    if checkout is None:
        try:
            checkout = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, timeout=15,
            ).strip()
        except (OSError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as exc:
            raise ValueError("Source checkout could not be independently verified") from exc
    if checkout != expected:
        raise ValueError("Final candidate cannot mix source revisions")
    return expected


def require_final_receipt(receipt, *, source, target, installer, digest, size):
    """Match the original native build's output, not a mutable tag or filename."""
    if not isinstance(receipt, dict):
        raise ValueError("Final 3.1 source-stage evidence missing")
    expected = {
        "schema_version": 1,
        "status": STAGE_STATUS,
        "target": target,
        "source_revision": source,
        "installer": installer,
        "sha256": digest,
        "version": "3.1.0",
        "identity_channel": "final_candidate",
        "settings_namespace": "anything-plays-31",
        "public_release_approved": False,
        "only_mgba_source_stage": True,
        "native_core_count": 1,
        "full_18_console_release_ready": False,
        "relinking_approved": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError("Final 3.1 source-stage evidence mismatch: " + key)
    if (not isinstance(size, int) or isinstance(size, bool) or size < 1024 * 1024
            or not isinstance(receipt.get("size_bytes"), int)
            or isinstance(receipt.get("size_bytes"), bool)
            or receipt["size_bytes"] != size):
        raise ValueError("Source-stage installer size mismatch")
    return True
