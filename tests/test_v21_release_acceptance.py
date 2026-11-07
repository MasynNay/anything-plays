"""A green installer build is NOT a completed all-console 2.1 release."""
import copy
import json
from pathlib import Path
import unittest

from tools.check_v21_release import (
    ACCEPTANCE_FILE, PLATFORM_FLAGS, RELEASE_FLAGS, SYSTEM_FLAGS,
    PLATFORMS, release_blockers, main,
)


class ReleaseAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(ACCEPTANCE_FILE.read_text(encoding="utf-8"))

    def test_alpha_is_blocked_until_all_eight_consoles_work_in_one_window(self):
        errors = release_blockers(self.policy)
        self.assertTrue(any("gamecube: bundled" in error for error in errors))
        self.assertTrue(any("gamecube: in_app_video" in error for error in errors))
        self.assertTrue(any("n64: real_game_verified" in error for error in errors))
        self.assertTrue(any("gamecube: real_game_verified" in error for error in errors))
        self.assertEqual(main([]), 1)
        self.assertEqual(main(["--report-only"]), 0)

    def test_every_console_and_platform_must_have_evidence(self):
        policy = copy.deepcopy(self.policy)
        policy["systems"].pop("gb")
        errors = release_blockers(policy)
        self.assertTrue(any("Console inventory mismatch" in error for error in errors))
        self.assertTrue(any("gb: no evidence record" in error for error in errors))

        policy = copy.deepcopy(self.policy)
        policy["platform_validation"].pop("macos-arm64")
        errors = release_blockers(policy)
        self.assertTrue(any("macos-arm64: no installation" in error for error in errors))

    def test_missing_and_nonboolean_fields_fail_closed(self):
        policy = copy.deepcopy(self.policy)
        policy["systems"]["gba"]["bundled"] = "yes"
        policy["required_release_evidence"]["no_external_emulator_setup_required"] = 1
        policy["platform_validation"]["windows-x64"]["clean_install"] = None
        errors = release_blockers(policy)
        self.assertTrue(any("gba: bundled" in error for error in errors))
        self.assertTrue(any("clean_install" in error for error in errors))
        self.assertTrue(any("no_external_emulator_setup_required" in error
                            for error in errors))

    def test_external_gamecube_never_passes_even_if_record_is_prematurely_signed(self):
        policy = copy.deepcopy(self.policy)
        for row in policy["systems"].values():
            for name in SYSTEM_FLAGS:
                row[name] = True
        for row in policy["platform_validation"].values():
            for name in PLATFORM_FLAGS:
                row[name] = True
        for name in RELEASE_FLAGS:
            policy["required_release_evidence"][name] = True
        # Every other requirement is marked complete, but a developer
        # mistakenly changes GameCube's primary runtime to external Dolphin.
        policy["systems"]["gamecube"]["primary_runtime"] = "external-dolphin"
        errors = release_blockers(policy)
        self.assertEqual(
            errors, ["gamecube: in-app Libretro runtime not selected/verified"]
        )
        # With a correct in-app runtime and reviewed evidence, the gate
        # can in principle pass; the real alpha policy remains false.
        policy["systems"]["gamecube"]["primary_runtime"] = (
            "embedded-libretro-software"
        )
        self.assertEqual(release_blockers(policy), [])


if __name__ == "__main__":
    unittest.main()
