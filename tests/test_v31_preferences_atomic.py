"""Adversarial 3.1 settings migration: never clobber stable preferences.

The RC migration uses a completed temporary file and a create-only hard
link. All test cases use temporary homes, including simulated races.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.test_preferences import (
    CANDIDATE_DIR, LEGACY_DIR, MAX_SETTINGS_BYTES,
    PREVIOUS_PREVIEW_DIR, TEST_DIR, _copy_once_atomic,
    prepare_test_preferences,
)


def seed(home, folder, *, preferences=b'{"theme":"Ocean"}', profile=b'{"gb":{}}'):
    directory = home / folder
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "preferences.json").write_bytes(preferences)
    (directory / "system_profiles.json").write_bytes(profile)
    return directory


def leftovers(directory):
    return list(directory.glob(".anything-plays-31-seed-*.tmp"))


class AtomicCandidatePreferencesTests(unittest.TestCase):
    def test_rc_seeds_both_files_without_overwriting_stable_or_preview(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            old = seed(home, LEGACY_DIR, preferences=b'{"theme":"Stable"}')
            preview = seed(home, TEST_DIR, preferences=b'{"theme":"Preview"}')
            path = prepare_test_preferences(home, channel="rc1")
            self.assertEqual(path, home / CANDIDATE_DIR / "preferences.json")
            self.assertEqual(path.read_bytes(), b'{"theme":"Preview"}')
            self.assertEqual(path.with_name("system_profiles.json").read_bytes(),
                             b'{"gb":{}}')
            path.write_bytes(b'{"theme":"Custom RC"}')
            self.assertEqual(prepare_test_preferences(home, channel="rc1"), path)
            self.assertEqual(path.read_bytes(), b'{"theme":"Custom RC"}')
            self.assertEqual((old / "preferences.json").read_bytes(),
                             b'{"theme":"Stable"}')
            self.assertEqual((preview / "preferences.json").read_bytes(),
                             b'{"theme":"Preview"}')
            self.assertEqual(leftovers(path.parent), [])

    def test_previous_preview_only_seeds_preview_channel_and_rc_fallback(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            old = seed(home, LEGACY_DIR, preferences=b'{"theme":"Stable"}')
            previous = seed(home, PREVIOUS_PREVIEW_DIR,
                            preferences=b'{"theme":"Earlier Preview"}')
            preview_path = prepare_test_preferences(home, channel="preview1")
            self.assertEqual(preview_path.read_bytes(),
                             b'{"theme":"Earlier Preview"}')
            self.assertEqual(prepare_test_preferences(home, channel="rc1").read_bytes(),
                             b'{"theme":"Earlier Preview"}')
            self.assertEqual((old / "preferences.json").read_bytes(),
                             b'{"theme":"Stable"}')
            self.assertEqual((previous / "preferences.json").read_bytes(),
                             b'{"theme":"Earlier Preview"}')

    def test_corrupt_channel_does_not_create_any_settings_directory(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            with self.assertRaises(ValueError):
                prepare_test_preferences(home, channel="anything-plays")
            self.assertFalse((home / ".config").exists())

    def test_failed_write_never_publishes_partial_file_or_deletes_stable(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            old = seed(home, LEGACY_DIR, preferences=b'{"theme":"Original"}')
            with patch("anything_plays.test_preferences.os.link",
                       side_effect=OSError("volume does not support atomic link")):
                path = prepare_test_preferences(home, channel="rc1")
            self.assertFalse(path.exists(), "An incomplete migration is worse than defaults")
            self.assertEqual(leftovers(path.parent), [])
            self.assertEqual((old / "preferences.json").read_bytes(),
                             b'{"theme":"Original"}')

    def test_failed_copy_file_does_not_remove_concurrently_created_candidate(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            seed(home, LEGACY_DIR)
            candidate = home / CANDIDATE_DIR
            candidate.mkdir()
            target = candidate / "preferences.json"
            original_link = os.link

            def competing_writer(_staged, final):
                final_path = Path(final)
                if final_path.name == "preferences.json":
                    final_path.write_bytes(b'{"theme":"Other Instance"}')
                    raise FileExistsError("concurrent writer won")
                return original_link(_staged, final)

            with patch("anything_plays.test_preferences.os.link",
                       side_effect=competing_writer):
                result = prepare_test_preferences(home, channel="rc1")
            self.assertEqual(result, target)
            self.assertEqual(target.read_bytes(), b'{"theme":"Other Instance"}')
            self.assertEqual(leftovers(candidate), [])

    def test_multithreaded_startup_never_overwrites_accepted_settings(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            old = seed(home, LEGACY_DIR, preferences=b'{"theme":"Stable"}')
            with ThreadPoolExecutor(max_workers=8) as pool:
                paths = list(pool.map(
                    lambda _: prepare_test_preferences(home, channel="rc1"),
                    range(32),
                ))
            self.assertEqual(len(set(paths)), 1)
            self.assertEqual(paths[0].read_bytes(), b'{"theme":"Stable"}')
            self.assertEqual(leftovers(paths[0].parent), [])
            self.assertEqual((old / "preferences.json").read_bytes(),
                             b'{"theme":"Stable"}')

    def test_source_symlinks_are_not_read_and_destination_symlinks_rejected(self):
        if os.name == "nt":
            self.skipTest("Ordinary Windows CI users may lack symlink permissions")
        with TemporaryDirectory() as d:
            home = Path(d)
            old = seed(home, LEGACY_DIR)
            preview = home / TEST_DIR
            preview.mkdir()
            (preview / "preferences.json").symlink_to(old / "preferences.json")
            copied = prepare_test_preferences(home, channel="rc1")
            self.assertFalse(copied.exists())
            self.assertTrue(copied.with_name("system_profiles.json").exists() is False)
            copied.symlink_to(old / "preferences.json")
            with self.assertRaises(ValueError):
                prepare_test_preferences(home, channel="rc1")
            self.assertEqual((old / "preferences.json").read_bytes(),
                             b'{"theme":"Ocean"}')

    def test_symlinked_rc_directory_cannot_target_stable_settings(self):
        if os.name == "nt":
            self.skipTest("Ordinary Windows CI users may lack symlink permissions")
        with TemporaryDirectory() as d:
            home = Path(d)
            stable = seed(home, LEGACY_DIR)
            (home / CANDIDATE_DIR).symlink_to(stable, target_is_directory=True)
            with self.assertRaises(ValueError):
                prepare_test_preferences(home, channel="rc1")
            self.assertEqual((stable / "preferences.json").read_bytes(),
                             b'{"theme":"Ocean"}')

    def test_source_directory_symlink_cannot_import_arbitrary_settings(self):
        if os.name == "nt":
            self.skipTest("Ordinary Windows CI users may lack symlink permissions")
        with TemporaryDirectory() as d:
            home = Path(d)
            storage = home / "outside"
            storage.mkdir()
            (storage / "preferences.json").write_bytes(b'{"private":"no"}')
            (home / LEGACY_DIR).parent.mkdir()
            (home / LEGACY_DIR).symlink_to(storage, target_is_directory=True)
            result = prepare_test_preferences(home, channel="rc1")
            self.assertFalse(result.exists())
            self.assertEqual((storage / "preferences.json").read_bytes(),
                             b'{"private":"no"}')

    def test_concurrent_symlink_creation_cannot_redirect_later_app_save(self):
        if os.name == "nt":
            self.skipTest("Ordinary Windows CI users may lack symlink permissions")
        with TemporaryDirectory() as d:
            home = Path(d)
            stable = seed(home, LEGACY_DIR,
                          preferences=b'{"theme":"Never overwrite stable"}')
            def race_with_symlink(_temp, dest):
                if Path(dest).name == "preferences.json":
                    Path(dest).symlink_to(stable / "preferences.json")
                    raise FileExistsError("malicious competing write")
                return os.link(_temp, dest)
            with patch("anything_plays.test_preferences.os.link",
                       side_effect=race_with_symlink):
                with self.assertRaises(ValueError):
                    prepare_test_preferences(home, channel="rc1")
            self.assertEqual((stable / "preferences.json").read_bytes(),
                             b'{"theme":"Never overwrite stable"}')

    def test_oversized_legacy_file_never_materializes_partial_rc_file(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            legacy = seed(home, LEGACY_DIR)
            (legacy / "preferences.json").write_bytes(b"p" * (MAX_SETTINGS_BYTES + 1))
            result = prepare_test_preferences(home, channel="rc1")
            self.assertFalse(result.exists())
            self.assertEqual(leftovers(result.parent), [])
            self.assertTrue(result.with_name("system_profiles.json").exists())

    def test_temp_copy_is_fully_written_before_atomic_publication(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            seed(home, LEGACY_DIR, preferences=b"valid bytes" * 200)
            destination = home / CANDIDATE_DIR
            destination.mkdir()
            original_link = os.link
            observed = []

            def check_link(temp, target):
                observed.append(Path(temp).read_bytes())
                self.assertFalse(Path(target).exists())
                return original_link(temp, target)

            with patch("anything_plays.test_preferences.os.link", side_effect=check_link):
                _copy_once_atomic(home / LEGACY_DIR / "preferences.json",
                                  destination / "preferences.json")
            self.assertEqual(observed, [b"valid bytes" * 200])
            self.assertEqual((destination / "preferences.json").read_bytes(),
                             b"valid bytes" * 200)
            self.assertEqual(leftovers(destination), [])


if __name__ == "__main__":
    unittest.main()
