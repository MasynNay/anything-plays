"""All 3.0 emulators must be already present: no first-run download UI."""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from anything_plays.ui_updates import UpdatesMixin

ROOT = Path(__file__).resolve().parents[1]

class AllEmulatorsOfflineGUIContracts(unittest.TestCase):
    def test_application_does_not_present_first_run_emulator_download(self):
        layout = (ROOT/"anything_plays/ui_layout.py").read_text("utf-8")
        updates = (ROOT/"anything_plays/ui_updates.py").read_text("utf-8")
        self.assertNotIn("download_emulator_button", layout)
        self.assertNotIn("download_selected_emulator", layout)
        self.assertNotIn("def download_selected_emulator(", updates)
        self.assertNotIn("optional download", updates)
        self.assertIn("Install approved updates", layout)
        self.assertIn("Emulator status:", layout)

    def test_missing_core_is_a_broken_package_not_a_optional_download(self):
        panel = UpdatesMixin()
        panel._selected_emulator_status = Mock()
        panel.system_key = Mock()
        panel.system_key.get.return_value = "gbc"
        panel._core_install_busy = False
        with patch("anything_plays.core_locator.find_core", return_value=None):
            panel.refresh_selected_emulator_state()
        message = panel._selected_emulator_status.set.call_args.args[0]
        self.assertIn("reinstall", message)
        self.assertNotIn("download", message.lower())

if __name__ == "__main__":
    unittest.main()
