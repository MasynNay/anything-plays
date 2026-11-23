"""3.3.1: persistent settings survive transient Windows filesystem locks.

All JSON content is synthetic and written into disposable local temp dirs.
Tests simulate Windows replace errors even on Linux/macOS and exercise native
os.replace on every runner. No user settings or profile files are touched.
"""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from anything_plays.atomic_storage import write_json_atomically


class SettingsAtomicReplaceRecoveryTests(unittest.TestCase):
    def setUp(self):
        holder = TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        self.target = self.root / "settings" / "preferences.json"
        write_json_atomically(self.target, {"theme": "Existing"})
        self.original_replace = os.replace
        self.original_fsync = os.fsync

    @staticmethod
    def fake_windows(replace):
        # Patch the module's os binding, not global os.name: Path on POSIX
        # must continue to instantiate real local paths during a test.
        return SimpleNamespace(
            name="nt", replace=replace, fsync=os.fsync,
        )

    def assert_no_temp(self):
        self.assertEqual(list(self.target.parent.glob("*.tmp")), [])

    def test_native_atomic_replace_writes_complete_unicode_settings(self):
        self.assertIsNone(write_json_atomically(
            self.target, {"theme": "New", "note": "Pokémon"},
        ))
        self.assertEqual(
            json.loads(self.target.read_text(encoding="utf-8")),
            {"theme": "New", "note": "Pokémon"},
        )
        self.assert_no_temp()

    def test_windows_transient_sharing_error_retries_original_snapshot(self):
        for winerror in (5, 32, 33):
            with self.subTest(winerror=winerror):
                attempts = [0]

                def transient(source, destination):
                    attempts[0] += 1
                    if attempts[0] == 1:
                        error = PermissionError(13, "Windows share lock")
                        error.winerror = winerror
                        raise error
                    self.assertEqual(Path(source).parent, self.target.parent)
                    self.assertEqual(Path(destination), self.target)
                    return self.original_replace(source, destination)

                with (
                    patch("anything_plays.atomic_storage.os",
                          self.fake_windows(transient)),
                    patch("anything_plays.atomic_storage.time.sleep") as wait,
                ):
                    write_json_atomically(self.target, {"theme": str(winerror)})
                self.assertEqual(attempts[0], 2)
                wait.assert_called_once_with(0.025)
                self.assertEqual(json.loads(self.target.read_text()),
                                 {"theme": str(winerror)})
                self.assert_no_temp()

    def test_windows_multiple_sharing_errors_backoff_then_write_once(self):
        attempts = [0]
        staged_names = []

        def busy(source, destination):
            staged_names.append(Path(source))
            attempts[0] += 1
            if attempts[0] < 4:
                error = PermissionError(13, "Scanner busy")
                error.winerror = 32
                raise error
            return self.original_replace(source, destination)

        with (
            patch("anything_plays.atomic_storage.os",
                  self.fake_windows(busy)),
            patch("anything_plays.atomic_storage.time.sleep") as sleeper,
        ):
            write_json_atomically(self.target, {"theme": "Recovered"})
        self.assertEqual(attempts[0], 4)
        self.assertEqual(len(set(staged_names)), 1)
        self.assertEqual(
            [call.args[0] for call in sleeper.call_args_list],
            [0.025, 0.05, 0.07500000000000001],
        )
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Recovered"})
        self.assert_no_temp()

    def test_persistent_windows_sharing_errors_preserve_last_good_json(self):
        attempts = [0]

        def unavailable(_source, _destination):
            attempts[0] += 1
            error = PermissionError(13, "Permanent Windows lock")
            error.winerror = 32
            raise error

        with (
            patch("anything_plays.atomic_storage.os",
                  self.fake_windows(unavailable)),
            patch("anything_plays.atomic_storage.time.sleep") as sleeper,
        ):
            with self.assertRaises(PermissionError):
                write_json_atomically(self.target, {"theme": "NotSaved"})
        self.assertEqual(attempts[0], 4)
        self.assertEqual(sleeper.call_count, 3)
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Existing"})
        self.assert_no_temp()

    def test_nonsharing_permission_error_does_not_retry_or_touch_old_data(self):
        attempts = [0]

        def denied(_source, _destination):
            attempts[0] += 1
            error = PermissionError(13, "Read-only storage")
            error.winerror = 65
            raise error

        with (
            patch("anything_plays.atomic_storage.os",
                  self.fake_windows(denied)),
            patch("anything_plays.atomic_storage.time.sleep") as sleeper,
        ):
            with self.assertRaises(PermissionError):
                write_json_atomically(self.target, {"theme": "NotSaved"})
        self.assertEqual(attempts[0], 1)
        sleeper.assert_not_called()
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Existing"})
        self.assert_no_temp()

    def test_non_windows_permission_error_never_retries(self):
        attempts = [0]

        def denied(_source, _destination):
            attempts[0] += 1
            error = PermissionError(13, "POSIX write denied")
            error.winerror = 32
            raise error

        simulated = SimpleNamespace(
            name="posix", replace=denied, fsync=os.fsync,
        )
        with (
            patch("anything_plays.atomic_storage.os", simulated),
            patch("anything_plays.atomic_storage.time.sleep") as sleeper,
        ):
            with self.assertRaises(PermissionError):
                write_json_atomically(self.target, {"theme": "NotSaved"})
        self.assertEqual(attempts[0], 1)
        sleeper.assert_not_called()
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Existing"})
        self.assert_no_temp()

    def test_native_disk_failure_preserves_last_good_preferences(self):
        with patch("anything_plays.atomic_storage.os.replace",
                   side_effect=OSError("disconnected storage")):
            with self.assertRaises(OSError):
                write_json_atomically(self.target, {"theme": "NotSaved"})
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Existing"})
        self.assert_no_temp()

    def test_temporary_cleanup_fault_does_not_mask_completed_commit(self):
        old_unlink = Path.unlink
        seen = []

        def fail_only_temporary(path, *args, **kwargs):
            if path.name.endswith(".tmp"):
                seen.append(path)
                raise OSError("Vendor scanner denies temporary cleanup")
            return old_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_only_temporary):
            write_json_atomically(self.target, {"theme": "Committed"})
        self.assertEqual(len(seen), 1)
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Committed"})
        self.assert_no_temp()

    def test_temporary_cleanup_fault_never_masks_primary_write_failure(self):
        old_unlink = Path.unlink

        def fail_only_temporary(path, *args, **kwargs):
            if path.name.endswith(".tmp"):
                raise OSError("PRIVATE cleanup failure")
            return old_unlink(path, *args, **kwargs)

        with (
            patch.object(Path, "unlink", fail_only_temporary),
            patch("anything_plays.atomic_storage.os.replace",
                  side_effect=OSError("PRIMARY disconnected data drive")),
        ):
            with self.assertRaisesRegex(OSError, "PRIMARY disconnected"):
                write_json_atomically(self.target, {"theme": "NotSaved"})
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Existing"})
        # The unremovable temporary file is acceptable; the original was
        # neither overwritten nor replaced with partial JSON.

    def test_serialization_failure_preserves_old_json_and_cleans_temp(self):
        with self.assertRaises(TypeError):
            write_json_atomically(self.target, {"bad": object()})
        self.assertEqual(json.loads(self.target.read_text()),
                         {"theme": "Existing"})
        self.assert_no_temp()


if __name__ == "__main__":
    unittest.main()
