"""StarGunner cold-start native flash experiment source and file safeguards."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.probe_ngp_flash_persistence import (
    COMMON_SEQUENCE, MODIFY_SEQUENCE, ROI, STOP_FRAME, SNAPSHOT_FRAME,
    _flash_entries,
)


class NeoGeoPocketFlashRestartExperimentTests(unittest.TestCase):
    def test_three_sessions_use_real_game_options_controls(self):
        self.assertEqual(COMMON_SEQUENCE, (
            (55, "A"), (100, "Down"), (145, "A")
        ))
        self.assertEqual(MODIFY_SEQUENCE, ((230, "Right"), (305, "B")))
        self.assertLess(COMMON_SEQUENCE[-1][0], MODIFY_SEQUENCE[0][0])
        self.assertLess(MODIFY_SEQUENCE[0][0], SNAPSHOT_FRAME)
        self.assertLess(SNAPSHOT_FRAME, MODIFY_SEQUENCE[1][0])
        self.assertLess(MODIFY_SEQUENCE[1][0], STOP_FRAME)
        self.assertEqual(ROI, (120, 48, 136, 56))

    def test_flash_inventory_uses_actual_safe_files_without_following_links(self):
        with TemporaryDirectory() as root:
            folder = Path(root)
            file = folder / "StarGunner.flash"
            file.write_bytes(b"native-flash-test")
            (folder / "ignored.sav").write_bytes(b"legacy format")
            symlink = folder / "aliased.flash"
            try:
                symlink.symlink_to(file)
            except (OSError, NotImplementedError):
                pass
            observed = _flash_entries(folder)
            self.assertEqual([x["name"] for x in observed], [file.name])
            self.assertEqual(observed[0]["bytes"], len(b"native-flash-test"))
            self.assertEqual(
                observed[0]["sha256"],
                hashlib.sha256(b"native-flash-test").hexdigest(),
            )

    def test_actual_restart_gate_requires_restored_game_pixel_evidence(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "tools/probe_ngp_flash_persistence.py"
        ).read_text("utf-8")
        for contract in (
            '("baseline", "modified", "restored")',
            'baseline["number_roi_sha256"] != changed["number_roi_sha256"]',
            'changed["number_roi_sha256"] == restored["number_roi_sha256"]',
            'actual_flash_file_survives_relaunch',
            'native_nonzero_input_polls',
            'fetch_test_fixture("ngpc", rom)',
        ):
            self.assertIn(contract, script)


if __name__ == "__main__":
    unittest.main()
