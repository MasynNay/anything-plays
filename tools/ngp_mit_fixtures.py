"""Pin legally redistributable third-party Neo Geo Pocket homebrew for CI only.

No homebrew ROM is stored in this repository, built into Anything Plays or
fetched when a user starts a game. This helper ONLY runs in GitHub Actions
acceptance tests. Verify the complete Git blob SHA-1 and byte length before
passing downloaded test data to a native core. Copyright and MIT attribution
are recorded in docs/V3_NGP_TEST_LICENSE.md.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

FIXTURES = {
    "ngp": {
        "name": "NGPCraft original alignment calibration v12 (mono)",
        "repo": "Tixul/Ngpcraft_emulator",
        "commit": "93b1fd666ff375afcbb48079fbcf61dbb99b86b4",
        "path": "hw_calibration/a_align_calib_v12.ngp",
        "blob_sha1": "8942344acbc23b80fa6f72c10e0fada5b58cdd7a",
        "bytes": 10630, "license": "MIT", "ext": ".ngp",
    },
    "ngpc": {
        "name": "StarGunner original Neo Geo Pocket Color demo",
        "repo": "Tixul/Stargunner",
        "commit": "de49e240e7b715f1d1f666931b1ad082adff5069",
        "path": "Stargunner.ngc",
        "blob_sha1": "27a06c37743460fcb85832b25b1754103b99e09d",
        "bytes": 79765, "license": "MIT", "ext": ".ngc",
    },
}
MAX_FIXTURE_BYTES = 2 * 1024 * 1024


def fetch_test_fixture(system, destination):
    """Download only a pinned public MIT test ROM for verification, not games."""
    if system not in FIXTURES:
        raise ValueError("Unknown Neo Geo Pocket test profile")
    spec = FIXTURES[system]
    path = Path(destination)
    if path.suffix.casefold() != spec["ext"]:
        raise ValueError("Neo Geo Pocket ROM extension does not match profile")
    uri = (
        f"https://raw.githubusercontent.com/{spec['repo']}/"
        f"{spec['commit']}/{spec['path']}"
    )
    request = Request(uri, headers={"User-Agent": "AnythingPlays-3.0-CI-verification"})
    with urlopen(request, timeout=40) as response:
        data = response.read(MAX_FIXTURE_BYTES + 1)
    if len(data) > MAX_FIXTURE_BYTES or len(data) != spec["bytes"]:
        raise ValueError("Pinned MIT fixture length mismatch")
    git_blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    actual = hashlib.sha1(git_blob).hexdigest()
    if actual != spec["blob_sha1"]:
        raise ValueError("Pinned MIT fixture integrity SHA-1 mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "system": system, "name": spec["name"], "license": spec["license"],
        "source_repo": spec["repo"], "pinned_commit": spec["commit"],
        "git_blob_sha1": actual, "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data), "included_in_user_installer": False,
        "runtime_download": False,
    }
