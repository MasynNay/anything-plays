"""Native Windows source-built Dolphin PE, ABI and provenance rejection tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock

from tools.verify_v30_dolphin_original_windows import (
    AMD64, PE32_PLUS, MANDATORY_LIBRETRO_SYMBOLS,
    audit, verify_original_windows_native,
)


def fake_image(root, *, machine=AMD64, magic=PE32_PLUS):
    body = bytearray(300_100)
    body[:2] = b"MZ"
    struct.pack_into("<I", body, 0x3c, 0x80)
    body[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<H", body, 0x84, machine)
    struct.pack_into("<H", body, 0x80 + 24, magic)
    path = Path(root) / "dolphin_libretro.dll"
    path.write_bytes(body)
    return path


class OriginalDolphinWindowsTests(unittest.TestCase):
    def test_exact_amd64_pe_loader_and_real_hash(self):
        with TemporaryDirectory() as temp:
            p = fake_image(temp)
            fake = MagicMock()
            for name in MANDATORY_LIBRETRO_SYMBOLS:
                setattr(fake, name, MagicMock())
            record = verify_original_windows_native(p, loader=lambda *_: fake)
            self.assertEqual(record["source_build_target"], "windows-x64")
            self.assertEqual(record["native_sha256"], hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(set(record["verified_libretro_exports"]),
                             set(MANDATORY_LIBRETRO_SYMBOLS))
            self.assertTrue(record["native_loadable_on_original_target_os"])

    def test_rejects_non_pe_wrong_cpu_and_missing_libretro_export(self):
        with TemporaryDirectory() as temp:
            p = fake_image(temp)
            p.write_bytes(b"FAKE " + b"0" * 300_100)
            with self.assertRaisesRegex(ValueError, "PE"):
                verify_original_windows_native(p, loader=lambda *_: MagicMock())
            p = fake_image(temp, machine=0x014c)
            with self.assertRaisesRegex(ValueError, "not AMD64"):
                verify_original_windows_native(p, loader=lambda *_: MagicMock())
            p = fake_image(temp, magic=0x10b)
            with self.assertRaisesRegex(ValueError, "not PE32"):
                verify_original_windows_native(p, loader=lambda *_: MagicMock())
            p = fake_image(temp)
            with self.assertRaisesRegex(ValueError, "exports unavailable"):
                verify_original_windows_native(p, loader=lambda *_: object())

    def test_source_build_audit_requires_37_pins_and_never_grants_rights(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            p = fake_image(root)
            native = verify_original_windows_native(p, loader=lambda *_: MagicMock())
            original = lambda *_: {
                "parent_commit": "32c61f9d0e933331bb7087ba57e96883241b4960",
                "direct_gitlinks_verified": 34,
                "nested_gitlinks_verified": 3,
            }
            output = root / "candidate.json"
            record = audit(root, p, output, verify_source=original,
                           verify_library=lambda *_: native)
            self.assertEqual(record, json.loads(output.read_text("utf-8")))
            for name in ("old_buildbot_binary_equivalence_claimed",
                         "physical_gameplay_tested",
                         "complete_corresponding_source_and_runtime_dependencies_reviewed",
                         "combined_gpl_distribution_reviewed",
                         "public_binary_distribution_approved"):
                self.assertIs(record[name], False)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                audit(root, p, output, verify_source=original,
                      verify_library=lambda *_: native)
            with self.assertRaisesRegex(ValueError, "37-source"):
                audit(root, p, root/"bad.json", verify_source=lambda *_: {
                    "direct_gitlinks_verified": 33, "nested_gitlinks_verified": 3,
                }, verify_library=lambda *_: native)


if __name__ == "__main__":
    unittest.main()
