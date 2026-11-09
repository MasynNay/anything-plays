"""Atomic candidate lock writing must preserve existing evidence on failures."""
import json
from pathlib import Path
from unittest import TestCase, mock
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from create_v30_candidate_lock import write_candidate_atomic


class AtomicCandidateLockTests(TestCase):
    def test_success_replaces_complete_json_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "lock.json"
            output.write_text("old", encoding="utf-8")
            write_candidate_atomic(output, {"approved_for_binary_distribution": False})
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")),
                             {"approved_for_binary_distribution": False})
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_replace_failure_preserves_previous_lock_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "lock.json"
            output.write_text("previous valid bytes", encoding="utf-8")
            with mock.patch("create_v30_candidate_lock.os.replace",
                            side_effect=OSError("simulated disk failure")):
                with self.assertRaisesRegex(OSError, "simulated disk failure"):
                    write_candidate_atomic(output, {"status": "UNAPPROVED"})
            self.assertEqual(output.read_text(encoding="utf-8"), "previous valid bytes")
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_serialization_failure_preserves_previous_lock_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "lock.json"
            output.write_text("previous valid bytes", encoding="utf-8")
            with self.assertRaises(TypeError):
                write_candidate_atomic(output, {"bad": object()})
            self.assertEqual(output.read_text(encoding="utf-8"), "previous valid bytes")
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_symlink_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            target.write_text("protected", encoding="utf-8")
            link = Path(directory) / "lock.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symlinked"):
                write_candidate_atomic(link, {"status": "UNAPPROVED"})
            self.assertEqual(target.read_text(encoding="utf-8"), "protected")
