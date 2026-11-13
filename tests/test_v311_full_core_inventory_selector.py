"""Source-verified 3.1.1 full package may select 11 cores ONLY in QA assembly.

Never grant release rights or turn mGBA-only source-stage jobs into full
bundles. These tests do not open a camera, install a ROM or run a core.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fetch_mgba_core import core_names_for_build
from tools.v30_release_lock import ALTERNATIVE_TIA_CORE_ORDER

SHA = "f" * 40
RELEASE_BLOCKERS = ("AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
                    "AP_V30_STABLE_CANDIDATE")


class Version311FullCoreSelector(unittest.TestCase):
    def config(self, channel):
        return {
            "AP_V31_FULL_TEST_CORES": "1",
            "AP_V31_NEXT_QA": "1",
            "AP_V31_QA_CHECKOUT_SHA": SHA,
            channel: "1",
            "AP_RELEASE_BUILD": "0",
            "AP_V30_APPROVED_RELEASE": "0",
            "AP_V30_STABLE_CANDIDATE": "0",
        }

    def test_each_311_channel_maps_to_complete_original_source_inventory(self):
        for channel in ("AP_V311_CANDIDATE", "AP_V311_STABLE_CANDIDATE"):
            with self.subTest(channel=channel), patch.dict(
                os.environ, self.config(channel), clear=True
            ):
                records = core_names_for_build()
                self.assertEqual(tuple(records), tuple(ALTERNATIVE_TIA_CORE_ORDER))
                self.assertEqual(len(records), 11)
                self.assertIn("dolphin", records)
                self.assertIn("tia", records)

    def test_one_core_source_shell_still_selects_only_mgba(self):
        for channel in ("AP_V311_CANDIDATE", "AP_V311_STABLE_CANDIDATE"):
            with self.subTest(channel=channel), patch.dict(
                os.environ, {channel: "1", "AP_V30_MINIMAL_CORE_BUILD": "1"},
                clear=True,
            ):
                self.assertEqual(tuple(core_names_for_build()), ("mgba",))

    def test_missing_checkout_sha_or_explicit_qa_refuses_full_core_set(self):
        for name, value in (
            ("AP_V31_NEXT_QA", "0"),
            ("AP_V31_QA_CHECKOUT_SHA", ""),
            ("AP_V31_QA_CHECKOUT_SHA", "deadbeef"),
        ):
            with self.subTest(name=name):
                flags = self.config("AP_V311_STABLE_CANDIDATE")
                flags[name] = value
                with patch.dict(os.environ, flags, clear=True):
                    with self.assertRaises(ValueError):
                        core_names_for_build()

    def test_mixed_version_channels_refused(self):
        for extra in ("AP_V31_FINAL_CANDIDATE", "AP_V31_RC2",
                      "AP_V311_CANDIDATE"):
            with self.subTest(extra=extra):
                flags = self.config("AP_V311_STABLE_CANDIDATE")
                flags[extra] = "1"
                with patch.dict(os.environ, flags, clear=True):
                    with self.assertRaises(ValueError):
                        core_names_for_build()

    def test_release_approval_flags_refused_even_with_full_source_hash(self):
        for flag in RELEASE_BLOCKERS:
            with self.subTest(flag=flag):
                flags = self.config("AP_V311_STABLE_CANDIDATE")
                flags[flag] = "1"
                with patch.dict(os.environ, flags, clear=True):
                    with self.assertRaises(ValueError):
                        core_names_for_build()


if __name__ == "__main__":
    unittest.main()
