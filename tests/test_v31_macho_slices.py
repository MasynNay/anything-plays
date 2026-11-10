"""Pure-Python Mach-O slice audit: exact bytes only, no signature edits."""
from __future__ import annotations

import hashlib
import struct
import unittest

from tools.macho_wheel_slices import architecture_slices


def thin(cpu, payload):
    return b"\xcf\xfa\xed\xfe" + struct.pack("<I", cpu) + payload


def universal():
    arm = thin(0x0100000C, b"a" * 60)
    intel = thin(0x01000007, b"x" * 100)
    start = 8 + 2 * 20
    headers = (
        struct.pack(">IIIII", 0x0100000C, 0, start, len(arm), 2)
        + struct.pack(">IIIII", 0x01000007, 0,
                      start + len(arm), len(intel), 2)
    )
    return b"\xca\xfe\xba\xbe" + struct.pack(">I", 2) + headers + arm + intel, arm, intel


class UniversalSliceEvidenceTests(unittest.TestCase):
    def test_both_architectures_are_exact_original_slice_bytes(self):
        whole, arm, intel = universal()
        result = architecture_slices(whole)
        self.assertEqual(result["arm64"], hashlib.sha256(arm).hexdigest())
        self.assertEqual(result["x86_64"], hashlib.sha256(intel).hexdigest())
        self.assertNotEqual(result["arm64"], hashlib.sha256(whole).hexdigest())

    def test_single_architecture_or_unknown_file(self):
        file = thin(0x0100000C, b"original")
        self.assertEqual(
            architecture_slices(file),
            {"arm64": hashlib.sha256(file).hexdigest()},
        )
        self.assertEqual(architecture_slices(b"not Mach-O"), {})

    def test_signature_or_other_byte_change_is_not_treated_as_original(self):
        whole, arm, _intel = universal()
        bad = bytearray(arm)
        bad[-1] ^= 1
        self.assertNotEqual(
            hashlib.sha256(bad).hexdigest(),
            architecture_slices(whole)["arm64"],
        )

    def test_rejects_missing_or_overlapping_slice_bytes(self):
        file, _arm, _intel = universal()
        incomplete = bytearray(file)
        # Second entry's offset at 8 + 20 + 8.
        struct.pack_into(">I", incomplete, 8 + 20 + 8, 49)
        with self.assertRaises(ValueError):
            architecture_slices(bytes(incomplete))
        truncated = file[:-6]
        with self.assertRaises(ValueError):
            architecture_slices(truncated)

    def test_rejects_excessive_slice_count(self):
        with self.assertRaises(ValueError):
            architecture_slices(b"\xca\xfe\xba\xbe" + struct.pack(">I", 100))

    def test_wheel_attestation_does_not_mark_sdl_rights_approved(self):
        from tools.prepare_v31_sdl_source_review import (
            match_installed_runtime, EXPECTED_RECEIPT_STATUS,
            RC_APP_COMMIT,
        )
        whole, arm, _intel = universal()
        digest = hashlib.sha256(arm).hexdigest()
        receipt = {
            "status": EXPECTED_RECEIPT_STATUS["macos-arm64"],
            "source_preview_revision": RC_APP_COMMIT,
            "native_core_count": 11, "console_profiles": 18,
            "public_release_approved": False,
            "final_release_approved": False,
            "sdl_runtime_audit": "SDL_RUNTIME_AUDIT.json",
        }
        audit = {
            "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
            "target": "macos-arm64", "pygame_version": "2.5.8",
            "pygame_distribution": "pygame-ce",
            "redistribution_approved": False,
            "original_sources_verified": False,
            "lgpl_relinking_reviewed": False,
            "native_candidates": [{"path": "pygame/base.so", "sha256": digest}],
        }
        output = match_installed_runtime("macos-arm64", receipt, audit, {
            digest: ["pygame/base.so [exact arm64 slice]"]
        })
        self.assertEqual(output["exact_architecture_slice_matches"], 1)
        self.assertEqual(output["wheel_match_count"], 1)
        self.assertFalse(output["runtime_relinking_verified"])
        self.assertFalse(output["sdl_native_source_correspondence_proven"])


if __name__ == "__main__":
    unittest.main()
