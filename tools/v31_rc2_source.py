"""Authenticate an unreleased full RC2 assembly against its exact PR source.

This helper is intentionally separate from the frozen public RC1 pins:
a new QA head cannot pretend to be the historical RC1 source. Every
installer remains nonpublic and requires its own original 3.0 core audit.
"""
from __future__ import annotations

import os
import re
import subprocess

FULL_SHA = re.compile(r"[a-f0-9]{40}\Z")
STAGE_STATUS = "UNRELEASED_3_1_RC2_APP_STAGE_ONLY"
FULL_STATUS = "UNRELEASED_3_1_FULL_RC2_QA"


def checked_rc2_source_revision(expected, *, environ=None, checkout=None):
    env = os.environ if environ is None else environ
    if not isinstance(expected, str) or FULL_SHA.fullmatch(expected) is None:
        raise ValueError("RC2 full QA requires the exact forty-digit source commit")
    if any(env.get(flag) != "1" for flag in (
        "AP_V31_RC2", "AP_V31_NEXT_QA", "AP_V31_FULL_TEST_CORES"
    )):
        raise ValueError("RC2 full assembly requires explicit isolated QA flags")
    if any(env.get(flag) == "1" for flag in (
        "AP_V31_RC", "AP_V31_PREVIEW", "AP_RELEASE_BUILD",
        "AP_V30_APPROVED_RELEASE", "AP_V30_STABLE_CANDIDATE",
        "AP_V30_TEST_CORES", "AP_V30_GPL_TRIAL", "AP_V30_TIA_TRIAL"
    )):
        raise ValueError("RC2 owner QA cannot imply RC1/3.0 or rights approval")
    if env.get("AP_V31_QA_CHECKOUT_SHA") != expected:
        raise ValueError("RC2 full QA input differs from the pinned runner checkout")
    if checkout is None:
        try:
            checkout = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, timeout=15
            ).strip()
        except (OSError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as exc:
            raise ValueError("Cannot authenticate checked-out RC2 source") from exc
    if checkout != expected:
        raise ValueError("RC2 full assembly and source-stage receipt disagree")
    return expected


def require_rc2_receipt(receipt, *, source, target, installer, digest):
    """Validate the original source-stage signed receipt, not a guessed ID."""
    if not isinstance(receipt, dict):
        raise ValueError("Missing original frozen RC2 application receipt")
    expected = {
        "schema_version": 1,
        "status": STAGE_STATUS,
        "public_release_approved": False,
        "final_release_candidate": False,
        "target": target,
        "source_revision": source,
        "version": "3.1.0-rc2",
        "settings_namespace": "anything-plays-31-rc2",
        "installer": installer,
        "sha256": digest,
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "hardware_controller_verified": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError("Original source-build RC2 receipt mismatch: " + key)
    if not isinstance(receipt.get("size_bytes"), int) or receipt["size_bytes"] <= 1024 * 1024:
        raise ValueError("RC2 source stage size is unverified")
    return True
