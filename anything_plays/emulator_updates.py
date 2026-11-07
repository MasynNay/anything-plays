"""Read-only update checks for the emulators shipped with Anything Plays 2.1.

Packaged emulator cores live inside signed, hash-verified app bundles. NEVER
replace their native libraries in place. A newer upstream commit means a
maintainer should verify and rebuild the entire app, not hot-swap an ABI.
This module does not download executables, open sockets for input or mutate
installed software. Network requests are bounded HTTPS calls to GitHub.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

# The authorized, reviewed upstream repositories from fetch_mgba_core.py.
UPSTREAM_REPOS = {
    "mgba": "libretro/mgba",
    "snes9x": "libretro/snes9x",
    "fceumm": "libretro/libretro-fceumm",
    "genesis_plus_gx": "libretro/Genesis-Plus-GX",
    "parallel_n64": "libretro/parallel-n64",
    # The distributed core is the Libretro Dolphin fork, not Dolphin Qt.
    "dolphin": "libretro/dolphin",
    "stella2014": "libretro/stella2014-libretro",
    "prosystem": "libretro/prosystem-libretro",
    "mednafen_pce_fast": "libretro/beetle-pce-fast-libretro",
    "mednafen_ngp": "libretro/beetle-ngp-libretro",
    "mednafen_wswan": "libretro/beetle-wswan-libretro",
}
DISPLAY_NAMES = {
    "mgba": "Game Boy / GBC / GBA · mGBA",
    "snes9x": "Super Nintendo · Snes9x",
    "fceumm": "NES · FCEUmm",
    "genesis_plus_gx": "Genesis / Master System / Game Gear / SG-1000 · Genesis Plus GX",
    "parallel_n64": "Nintendo 64 · ParaLLEl-N64 (test core)",
    "dolphin": "GameCube · Dolphin Libretro (experimental)",
    "stella2014": "Atari 2600 · Stella 2014",
    "prosystem": "Atari 7800 · ProSystem",
    "mednafen_pce_fast": "TurboGrafx-16 / PC Engine · Beetle PCE Fast",
    "mednafen_ngp": "Neo Geo Pocket / Color · Beetle NeoPop",
    "mednafen_wswan": "WonderSwan / Color · Beetle WonderSwan",
}
MAX_MANIFEST_BYTES = 250_000
MAX_API_BYTES = 150_000
SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{7,40}$")


def find_provenance(search_directories):
    """Find the first bundle manifest alongside its actual native cores."""
    for folder in search_directories:
        manifest = Path(folder) / "CORE_PROVENANCE.json"
        if not manifest.is_file() or manifest.stat().st_size > MAX_MANIFEST_BYTES:
            continue
        try:
            content = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        if isinstance(content, dict) and isinstance(content.get("cores"), list):
            return manifest, content
    return None, None


def _verified_record(record, folder):
    """Verify a manifest entry is a real bundled core with matching SHA-256."""
    name = record.get("name")
    filename = record.get("file", "")
    expected = record.get("sha256", "")
    if name not in UPSTREAM_REPOS:
        return "invalid"
    if (not isinstance(filename, str) or not filename.startswith(name + "_libretro.")
            or Path(filename).name != filename or
            Path(filename).suffix not in (".dll", ".dylib", ".so")):
        return "invalid"
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        return "invalid"
    native = folder / filename
    if not native.is_file():
        return "missing"
    digest = hashlib.sha256()
    with native.open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(piece)
    return "verified" if digest.hexdigest() == expected else "modified"


def github_head(repo, *, opener=None):
    """Read a repository's latest default-branch commit without following user URLs."""
    if repo not in UPSTREAM_REPOS.values():
        raise ValueError("Unapproved update source")
    api = "https://api.github.com/repos/" + repo + "/commits?per_page=1"
    request = urllib.request.Request(
        api,
        headers={
            "User-Agent": "AnythingPlays-2.1-updater/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    fetch = opener or urllib.request.urlopen
    with fetch(request, timeout=5) as response:
        raw = response.read(MAX_API_BYTES + 1)
    if len(raw) > MAX_API_BYTES:
        raise ValueError("Oversized upstream response")
    result = json.loads(raw)
    if not isinstance(result, list) or not result or not isinstance(result[0], dict):
        raise ValueError("Invalid upstream response")
    sha = result[0].get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid upstream commit identity")
    return sha


def _version_status(name, record, sha, integrity):
    """Do not confuse 'upstream advanced' with a vetted binary update."""
    if integrity != "verified":
        return integrity
    revision = record.get("reported_source_revision")
    if not isinstance(revision, str) or not SHA_PATTERN.fullmatch(revision):
        return "unknown-version"
    if sha.lower().startswith(revision.lower()):
        return "current-source"
    # Core builds can derive from different branches; cannot assert an
    # upgrade exists solely from nonmatching commit hashes.
    return "review-upstream"


def check_emulator_updates(search_directories, *, opener=None, online=True):
    """Return a JSON-serializable report, suitable for a UI worker thread.

    Online errors never crash startup; each core retains a useful diagnostic.
    The check does not alter the native binaries or their manifest.
    """
    path, manifest = find_provenance(search_directories)
    items = []
    known = {}
    if manifest:
        for record in manifest["cores"]:
            if not isinstance(record, dict):
                continue
            name = record.get("name")
            if name not in UPSTREAM_REPOS or name in known:
                continue
            try:
                integrity = _verified_record(record, path.parent)
            except OSError:
                integrity = "unreadable"
            known[name] = (record, integrity)

    for name, repo in UPSTREAM_REPOS.items():
        record, integrity = known.get(name, ({}, "not-bundled"))
        items.append({
            "key": name,
            "name": DISPLAY_NAMES[name],
            "repository": "https://github.com/" + repo,
            "installed_version": record.get("libretro_library_version", ""),
            "installed_revision": record.get("reported_source_revision"),
            "integrity": integrity,
            "status": integrity if integrity != "verified" else "not-checked",
            "upstream_revision": None,
        })

    # A verified per-user core pack takes precedence over the bundled binary.
    # Import lazily to avoid the core_packs -> emulator_updates import cycle.
    from anything_plays.core_packs import managed_core_path, managed_core_release
    for item in items:
        name = item["key"]
        if name == "dolphin":
            continue  # Dolphin must be updated with matching Sys assets.
        if managed_core_path(name):
            item["installed_from"] = "approved-core-pack"
            item["installed_version"] = managed_core_release(name) or "approved core pack"
            item["integrity"] = "verified"
            item["status"] = "managed-release"

    if online:
        def fetch(item):
            try:
                sha = github_head(UPSTREAM_REPOS[item["key"]], opener=opener)
                item["upstream_revision"] = sha
                if item["status"] == "managed-release":
                    return item
                if item["integrity"] == "verified":
                    item["status"] = _version_status(
                        item["key"], known[item["key"]][0],
                        sha, item["integrity"]
                    )
            except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
                # Offline source checking must never make an already installed
                # and verified core pack appear to have disappeared.
                if item["status"] != "managed-release":
                    item["status"] = (
                        "offline" if item["integrity"] == "verified" else item["integrity"]
                    )
            return item

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(fetch, item) for item in items]
            for future in as_completed(futures):
                future.result()

    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_found": path is not None,
        "updates_install_automatically": False,
        "update_policy": (
            "New native emulators are reviewed, tested, signed and installed "
            "with an Anything Plays app update, never overwritten in place."
        ),
        "cores": items,
    }


def summary_text(report):
    """Explain updater results without promising updates that are not verified."""
    names = {
        "current-source": "Matches the reported upstream source commit",
        "managed-release": "Verified approved core pack installed",
        "review-upstream": "Upstream changed; requires tested app rebuild",
        "unknown-version": "Source revision unavailable; check during next build",
        "verified": "Bundled and hash verified",
        "modified": "Local core checksum mismatch; reinstall the app",
        "missing": "Bundled core missing; reinstall the app",
        "unreadable": "Unable to read bundled core",
        "invalid": "Invalid core manifest entry",
        "not-bundled": "Not bundled in this test installer",
        "offline": "Could not reach upstream; bundled core unchanged",
        "not-checked": "Installed; online check not requested",
    }
    lines = ["Emulator updates — 2.1 test", ""]
    for item in report["cores"]:
        lines.append(item["name"] + ": " + names.get(item["status"], item["status"]))
    lines += [
        "", "Checks do not replace native core libraries.",
        "New verified binaries must ship in a tested, signed application update.",
        "GameCube and N64 software cores are still experimental.",
        "Real-game validation is required before a public 2.1 release.",
    ]
    return "\n".join(lines)
