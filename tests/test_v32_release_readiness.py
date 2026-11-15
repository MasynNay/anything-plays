"""Prevent private 18-profile research from silently authorizing publication."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.check_v32_release_readiness import assess, read_status, PUBLIC, SOFTWARE


class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "config/v3.2-release-readiness.json"
        cls.source = json.loads(path.read_text("utf-8"))

    def test_actual_complete_qa_is_still_not_public(self):
        state = assess(self.source,
                       tested_sha="9f6950bc2a532375d2da5a6011571c9af11cf828")
        self.assertTrue(state["software_qa_complete"])
        self.assertFalse(state["public_release_ready"])
        self.assertEqual(set(state["pending_publication_gates"]), set(PUBLIC))

    def test_tampering_with_bool_identity_and_source_is_rejected(self):
        bad = copy.deepcopy(self.source)
        bad["software_evidence"][SOFTWARE[0]] = 1
        with self.assertRaises(ValueError):
            assess(bad)
        bad = copy.deepcopy(self.source)
        bad["console_profiles"] = 19
        with self.assertRaises(ValueError):
            assess(bad)
        with self.assertRaises(ValueError):
            assess(self.source, tested_sha="b" * 40)

    def test_only_all_reviewed_gates_plus_owner_approval_can_mark_ready(self):
        data = copy.deepcopy(self.source)
        for key in PUBLIC:
            data["publication_gates"][key] = True
        self.assertFalse(assess(data)["public_release_ready"])
        data["public_release_approved"] = True
        self.assertTrue(assess(data)["public_release_ready"])
        data["software_evidence"][SOFTWARE[-1]] = False
        self.assertFalse(assess(data)["public_release_ready"])

    def test_schema_and_symlink_cannot_bypass_checker(self):
        data = copy.deepcopy(self.source)
        data["auto_publish"] = True
        with self.assertRaises(ValueError):
            assess(data)
        with TemporaryDirectory() as td:
            path = Path(td) / "status.json"
            path.write_text(json.dumps(self.source), "utf-8")
            self.assertFalse(read_status(path)["public_release_ready"])
            link = path.with_name("link.json")
            try:
                link.symlink_to(path)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ValueError):
                    read_status(link)


if __name__ == "__main__":
    unittest.main()
