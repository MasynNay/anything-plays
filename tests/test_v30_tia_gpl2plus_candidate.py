"""Prevent a research-only Atari2600 GPL2+ alternative from becoming a release."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "docs/history/workflows/v30-tia-gpl2plus-candidate.yml"


class TiaAlternativeContracts(unittest.TestCase):
    def test_pinned_and_license_verified_from_original_upstream(self):
        s = WORKFLOW.read_text("utf-8")
        for text in (
            "6ae5bf998fe7a7842294089db17fc86fd73db1f0",
            "https://github.com/warmenhoven/tia",
            "SPDX-License-Identifier: GPL-2.0-or-later",
            "original-tia/COPYING",
            'test "$(git -C original-tia rev-parse HEAD)" = "$TIA_SHA"',
        ):
            self.assertIn(text, s)

    def test_four_platforms_and_actual_homebrew_video_audio(self):
        s = WORKFLOW.read_text("utf-8")
        for value in (
            "windows-2025", "ubuntu-24.04", "macos-15-intel",
            "macos-15", "windows-x64", "linux-x64", "macos-x64",
            "macos-arm64", "tools/probe_atari_homebrew.py",
            "video_frames", "pcm_nonzero_samples", "unique_frame_hashes",
        ):
            self.assertIn(value, s)

    def test_not_a_fake_release_or_unrequested_console_change(self):
        s = WORKFLOW.read_text("utf-8")
        for value in (
            '"additional_console_profiles":0',
            '"stella2014_replaced_in_main":False',
            '"public_binary_distribution_approved":False',
            '"combined_license_compliance_approved":False',
            "TIA_ATARI2600_NATIVE_PLAYBACK_UNAPPROVED.json",
        ):
            self.assertIn(value, s)
        for forbidden in (
            "gh release create", "gh release upload",
            "AP_V30_APPROVED_RELEASE: '1'", "\n  push:",
        ):
            self.assertNotIn(forbidden, s)


if __name__ == "__main__":
    unittest.main()
