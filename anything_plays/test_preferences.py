"""Give the 3.1 preview a private copy of the stable user's settings.

The 2.0 and 2.1 preferences and profiles are never written by the test branch.
A later production 3.0 release should use the explicit upgrade/migration
path rather than treating this test-only location as the stable default.
"""
from pathlib import Path
from anything_plays.build_identity import current_identity, make_identity


LEGACY_DIR = Path(".config") / "fish-plays-pokemon-studio"
TEST_DIR = Path(".config") / "anything-plays-31-preview"
PREVIOUS_PREVIEW_DIR = Path(".config") / "anything-plays-30-preview"
CANDIDATE_DIR = Path(".config") / "anything-plays-31-rc1"


def prepare_test_preferences(home=None, *, channel=None):
    """Seed only the chosen 3.1 identity's private settings directory."""
    home = Path.home() if home is None else Path(home)
    if channel is None:
        channel = current_identity()["channel"]
    # Do not trust a malformed channel or permit a write into stable settings.
    make_identity(channel)
    previous_preview = home / PREVIOUS_PREVIEW_DIR
    preview = home / TEST_DIR
    if channel == "rc1" and preview.is_dir():
        source = preview
    else:
        source = previous_preview if previous_preview.is_dir() else home / LEGACY_DIR
    destination = home / (CANDIDATE_DIR if channel == "rc1" else TEST_DIR)
    destination.mkdir(parents=True, exist_ok=True)
    for filename in ("preferences.json", "system_profiles.json"):
        previous = source / filename
        target = destination / filename
        if not previous.is_file() or target.exists():
            continue
        # Exclusive create means even concurrent test starts cannot overwrite
        # a user's existing alpha preferences or profiles.
        try:
            with previous.open("rb") as original, target.open("xb") as copy:
                while True:
                    data = original.read(1024 * 1024)
                    if not data:
                        break
                    copy.write(data)
        except FileExistsError:
            pass
        except OSError:
            # A corrupt/unreadable legacy file should not stop startup.
            # ProfileStore handles an absent test file with safe defaults.
            target.unlink(missing_ok=True)
    return destination / "preferences.json"
