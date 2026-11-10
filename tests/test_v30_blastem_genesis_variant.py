"""Native Genesis alternative diagnostic preserves all user-facing gameplay code."""
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from tools.genesis_homebrew_fixture import ENTRY, build_genesis_probe_rom
from tools.probe_v30_blastem_genesis_variant import (
    NOP, OFFSET, TMSS, original_without_unconditional_tmss,
)


class BlastEmGenesisTMSSDiagnosticTests(unittest.TestCase):
    def test_only_unconditional_tmss_write_is_nopped_from_original_homebrew(self):
        original, modified = original_without_unconditional_tmss()
        self.assertEqual(original, build_genesis_probe_rom("full"))
        self.assertEqual(len(original), 65536)
        self.assertEqual(len(modified), 65536)
        self.assertEqual(OFFSET, ENTRY+4)
        self.assertEqual(len(TMSS), len(NOP))
        self.assertEqual(original[OFFSET:OFFSET+10], TMSS)
        self.assertEqual(modified[OFFSET:OFFSET+10], NOP)
        self.assertEqual(modified[:OFFSET], original[:OFFSET])
        self.assertEqual(modified[OFFSET+10:], original[OFFSET+10:])
        self.assertNotEqual(hashlib.sha256(original).digest(),
                            hashlib.sha256(modified).digest())

    def test_original_fixture_is_unmodified_for_shipping_core_regressions(self):
        original, modified = original_without_unconditional_tmss()
        self.assertEqual(original[ENTRY+4:ENTRY+14], TMSS)
        from tools.genesis_homebrew_fixture import write_genesis_probe
        self.assertTrue(callable(write_genesis_probe))
        self.assertTrue((Path(__file__).resolve().parents[1] /
                         "tools/probe_genesis_homebrew.py").is_file())

    def test_no_retail_game_patching_or_public_core_promotion(self):
        root=Path(__file__).resolve().parents[1]
        tool=(root/"tools/probe_v30_blastem_genesis_variant.py").read_text("utf-8")
        workflow=(root/"docs/history/workflows/v30-gpl-alternative-research.yml").read_text("utf-8")
        self.assertIn("UNAPPROVED-BLASTEM-GENESIS-NON-TMSS",tool)
        self.assertIn("retail_genesis_compatibility_verified",tool)
        self.assertIn("public_release_approved",tool)
        self.assertIn("probe_v30_blastem_genesis_variant.py",workflow)
        self.assertNotIn("gh release create",workflow)
        self.assertNotIn("APPROVED-3.0-DISTRIBUTION",workflow)


if __name__=="__main__":
    unittest.main()
