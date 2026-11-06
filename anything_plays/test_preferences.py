"""Give the 2.1 alpha a private copy of the stable user's settings.

The 2.0 preferences and profiles are never written by the test branch.
A later production 2.1 release should use the explicit upgrade/migration
path rather than treating this test-only location as the stable default.
"""
from pathlib import Path


LEGACY_DIR = Path(".config") / "fish-plays-pokemon-studio"
TEST_DIR = Path(".config") / "anything-plays-21-test"


def prepare_test_preferences(home=None):
    """Seed a separate alpha settings directory once, without editing 2.0."""
    home = Path.home() if home is None else Path(home)
    source = home / LEGACY_DIR
    destination = home / TEST_DIR
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
