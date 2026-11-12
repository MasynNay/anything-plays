"""Version identity embedded in frozen 3.1 QA and release-candidate apps.

The identity is read from an immutable file included by PyInstaller, never
from an external environment variable on an end user's computer. Source
development defaults to the existing safe Preview 1 settings namespace.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

IDENTITIES = {
    "preview1": {
        "version": "3.1.0",
        "channel": "preview1",
        "title": "Anything Plays 3.1 · Preview 1",
        "settings_namespace": "anything-plays-31-preview",
        "public_release_approved": False,
    },
    "rc1": {
        "version": "3.1.0",
        "channel": "rc1",
        "title": "Anything Plays 3.1 · Release Candidate 1",
        "settings_namespace": "anything-plays-31-rc1",
        "public_release_approved": False,
    },
    "rc2": {
        "version": "3.1.0",
        "channel": "rc2",
        "title": "Anything Plays 3.1 · Release Candidate 2",
        "settings_namespace": "anything-plays-31-rc2",
        "public_release_approved": False,
    },
    # Actual 3.1.0 package/version identity for private, independently
    # validated final-candidate builds. Release rights are NOT approved
    # merely by selecting the identity or uploading a QA artifact.
    "final_candidate": {
        "version": "3.1.0",
        "channel": "final_candidate",
        "title": "Anything Plays 3.1",
        "settings_namespace": "anything-plays-31",
        "public_release_approved": False,
    },
}
FALLBACK_CHANNEL = "preview1"


def make_identity(channel):
    """Return an independent copy of the approved, closed identity schema."""
    if channel not in IDENTITIES:
        raise ValueError("Unsupported 3.1 build identity")
    return dict(IDENTITIES[channel])


def validate_identity(value):
    if not isinstance(value, dict):
        raise ValueError("Build identity must be a JSON object")
    channel = value.get("channel")
    if not isinstance(channel, str) or channel not in IDENTITIES:
        raise ValueError("Unknown or corrupt build identity")
    if value != IDENTITIES[channel]:
        raise ValueError("Build identity does not match the reviewed version/channel")
    return dict(value)


def embedded_identity_path():
    """Resources are under _MEIPASS when frozen, in source assets otherwise."""
    bundle = getattr(sys, "_MEIPASS", None)
    root = Path(bundle) if bundle else Path(__file__).resolve().parents[1]
    return root / "assets" / "v31_build_identity.json"


def current_identity(path=None):
    """Fail closed on a corrupt embedded marker; never guess an RC identity."""
    marker = Path(path) if path is not None else embedded_identity_path()
    if not marker.is_file():
        return make_identity(FALLBACK_CHANNEL)
    return validate_identity(json.loads(marker.read_text(encoding="utf-8")))


def app_title():
    return current_identity()["title"]
