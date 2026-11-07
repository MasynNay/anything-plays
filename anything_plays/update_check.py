"""Published-bundle update discovery for Anything Plays and its emulators.

Bundled native cores are updated together with a vetted application release.
This module deliberately does NOT fetch or execute third-party code: changing
an installed signed app bundle in place can invalidate its signature.
"""
from dataclasses import dataclass
import json
import re
import urllib.request
from urllib.parse import urlsplit

RELEASE_API = "https://api.github.com/repos/MasynNay/anything-plays/releases"
RELEASES_PAGE = "https://github.com/MasynNay/anything-plays/releases"
CURRENT_VERSION = "3.0.0-alpha.1"
MAX_RESPONSE_BYTES = 512 * 1024
_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-.]?(alpha|beta|rc)[.-]?(\d+))?$", re.I)
_RELEASE_LINK = re.compile(
    r"^https://github\.com/MasynNay/anything-plays/releases/tag/"
    r"[a-zA-Z0-9._-]+$"
)
_ORDER = {"alpha": 0, "beta": 1, "rc": 2}


@dataclass(frozen=True)
class BundleUpdate:
    version: str
    url: str
    label: str


def version_key(value):
    """Pre-releases sort before stable releases with matching version."""
    parsed = _VERSION.fullmatch(str(value).strip())
    if parsed is None:
        return None
    major, minor, patch, channel, sequence = parsed.groups()
    kind = 3 if channel is None else _ORDER[channel.lower()]
    return (int(major), int(minor), int(patch), kind, int(sequence or 0))


def choose_update(releases, *, current=CURRENT_VERSION):
    """Return the newest vetted app bundle, not an upstream nightly core."""
    installed = version_key(current)
    if installed is None:
        raise ValueError("Invalid installed Anything Plays version")
    best = None
    best_key = installed
    if not isinstance(releases, list):
        raise ValueError("Invalid release response")
    for item in releases:
        if not isinstance(item, dict) or item.get("draft"):
            continue
        tag = item.get("tag_name", "")
        url = item.get("html_url", "")
        key = version_key(tag)
        if key is None or key <= best_key or not _RELEASE_LINK.fullmatch(url):
            continue
        # Keep test builds on a separate channel until the stable release
        # genuinely supersedes this alpha.
        label = str(item.get("name") or tag)[:100]
        best_key, best = key, BundleUpdate(str(tag), url, label)
    return best


def check_published_updates(*, current=CURRENT_VERSION, opener=None):
    """Look for newer app + bundled-core packages over HTTPS; never install.

    Caller runs this on a background thread. Network failure is handled by
    the caller, and no ROM paths or private configuration are transmitted.
    """
    url = urlsplit(RELEASE_API)
    if url.scheme != "https" or url.hostname != "api.github.com":
        raise ValueError("Untrusted update endpoint")
    request = urllib.request.Request(
        RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AnythingPlays/3.0-update-check",
        },
    )
    opener = opener or urllib.request.urlopen
    with opener(request, timeout=6) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("Update response is too large")
    releases = json.loads(data)
    return choose_update(releases, current=current)
