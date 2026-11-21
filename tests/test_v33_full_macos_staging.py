"""Safe pure 3.3 Mac full-native QA source, identity and provenance contracts.

No DMG, native device, webcam, ROM or public release is made by tests.
"""
import hashlib
import json
from pathlib import Path
import plistlib
from tempfile import TemporaryDirectory
import unittest

from anything_plays.build_identity import make_identity
from tools.stage_v33_full_macos import names, source_gate, verify_identity


SHA = "b" * 40


class MacFullNativeStageTests(unittest.TestCase):
    def fixture(self, root, arch):
        root = Path(root)
        stable_name, preview_name, _ = names(arch)
        stable, candidate = root / stable_name, root / preview_name
        stable.write_bytes(b"published-3.2-macos-dmg" * 70000)
        candidate.write_bytes(b"3.3-qa-mgba-only-dmg" * 70000)
        sums = root / "SHA256SUMS.txt"
        sums.write_text(
            hashlib.sha256(stable.read_bytes()).hexdigest()
            + "  " + stable_name + "\n", encoding="utf-8",
        )
        record = {
            "format": "anything-plays-v33-owner-qa",
            "target": f"macos-{arch}", "source_sha": SHA,
            "channel": "v33_candidate", "version": "3.3.0-qa",
            "settings_namespace": "anything-plays-33-candidate",
            "installer_filename": preview_name,
            "installer_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "bundled_core_names": ["mgba_libretro.dylib"],
            "bundled_core_count": 1, "public_release_approved": False,
            "hardware_input_tested": False, "physical_camera_tested": False,
            "gamecube_bundled": False,
            "full_18_console_gameplay_tested": False,
            "installer_fully_tested_on_real_host": False,
        }
        receipt = root / "V33_CANDIDATE_QA_RECEIPT.json"
        receipt.write_text(json.dumps(record), encoding="utf-8")
        return stable, candidate, sums, receipt, record

    def test_both_architectures_accept_only_exact_v32_and_v33_bytes(self):
        with TemporaryDirectory() as root:
            for arch in ("x64", "arm64"):
                with self.subTest(arch=arch):
                    subdir = Path(root) / arch
                    subdir.mkdir()
                    stable, candidate, sums, receipt, _ = self.fixture(
                        subdir, arch,
                    )
                    self.assertEqual(
                        source_gate(arch, stable, candidate, sums, receipt, SHA),
                        (stable, candidate),
                    )
                    self.assertIn("3.2.0-macos-", stable.name)
                    self.assertIn("3.3.0-fullqa1-", names(arch)[2])

    def test_rejects_nonbaseline_checksum_wrong_arch_and_untrusted_flags(self):
        with TemporaryDirectory() as root:
            stable, preview, sums, receipt, record = self.fixture(root, "arm64")
            for field, bad in (
                ("target", "macos-x64"), ("source_sha", "c" * 40),
                ("channel", "v32_preview"),
                ("settings_namespace", "anything-plays-31"),
                ("bundled_core_count", 11), ("gamecube_bundled", True),
                ("public_release_approved", True),
                ("unknown", "/Users/private/ROM"),
            ):
                with self.subTest(field=field):
                    receipt.write_text(json.dumps({**record, field: bad}),
                                       encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "reviewed"):
                        source_gate("arm64", stable, preview, sums, receipt, SHA)
            receipt.write_text(json.dumps(record), encoding="utf-8")
            stable.write_bytes(b"changed stable app" * 90000)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                source_gate("arm64", stable, preview, sums, receipt, SHA)
            for arch in ("invalid", "amd64", "", None):
                with self.subTest(arch=arch), self.assertRaises(ValueError):
                    names(arch)

    def test_frozen_mac_bundle_uses_separate_private_33_identity(self):
        with TemporaryDirectory() as directory:
            app = Path(directory) / "AnythingPlays33Candidate.app"
            identity = app / "Contents/Resources/assets/v31_build_identity.json"
            identity.parent.mkdir(parents=True)
            identity.write_text(json.dumps(make_identity("v33_candidate")),
                                encoding="utf-8")
            plist = app / "Contents/Info.plist"
            expected = {
                "CFBundleIdentifier": "com.anythingplays.privateqa33",
                "CFBundleShortVersionString": "3.3.0",
                "CFBundleVersion": "3.3.0.1",
            }
            plist.write_bytes(plistlib.dumps(expected))
            verify_identity(app)
            for key, wrong in (
                ("CFBundleIdentifier", "com.anythingplays.release31"),
                ("CFBundleShortVersionString", "3.2.0"),
                ("CFBundleVersion", "3.3.0.99"),
            ):
                with self.subTest(key=key):
                    plist.write_bytes(plistlib.dumps({**expected, key: wrong}))
                    with self.assertRaises(ValueError):
                        verify_identity(app)


if __name__ == "__main__":
    unittest.main()
