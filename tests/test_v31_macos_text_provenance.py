"""Adversarial tests for macOS machine-code section correspondence review."""
import hashlib
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import inspect_v31_macos_text_provenance as review


def fake_macho(code=b"\x92" * 120, arch="arm64", flags=0):
    cpu = {"arm64": 0x0100000C, "x86_64": 0x01000007}[arch]
    start = 32 + 72 + 80
    header = struct.pack("<IIIIIIII", 0xFEEDFACF, cpu, 0, 6, 1, 152, flags, 0)
    segment = struct.pack("<II16sQQQQiiII", 0x19, 152, b"__TEXT", 0,
                          start + len(code), 0, start + len(code), 7, 5, 1, 0)
    section = struct.pack("<16s16sQQIIIIIIII", b"__text", b"__TEXT",
                          start, len(code), start, 0, 0, 0, 0, 0, 0, 0)
    return header + segment + section + code


def fake_fat(thin, arch="arm64"):
    cpu = {"arm64": 0x0100000C, "x86_64": 0x01000007}[arch]
    return (b"\xca\xfe\xba\xbe" + struct.pack(">I", 1)
            + struct.pack(">IIIII", cpu, 0, 32, len(thin), 0) + b"\0" * 4 + thin)


def install_fixture(root):
    root = Path(root)
    app = root / "App.app"
    root_dir = app / "Contents" / "Frameworks"
    root_dir.mkdir(parents=True)
    binary = fake_macho()
    natives = []
    for i in range(121):
        rel = f"Contents/Frameworks/libSDL-fixture-{i}.dylib"
        entry = app / rel
        entry.write_bytes(binary)
        natives.append({"path": rel, "sha256": review.sha256_file(entry)})
    dmg = root / "AnythingPlays-3.1.0-rc1-full-macos-arm64.dmg"
    dmg.write_bytes(b"An original package fixture")
    receipt = {
        "status": review.EXPECTED_RECEIPT_STATUS["macos-arm64"],
        "target": "macos-arm64",
        "source_preview_revision": review.RC_APP_COMMIT,
        "native_core_count": 11,
        "console_profiles": 18,
        "installer": dmg.name,
        "sha256": review.sha256_file(dmg),
        "public_release_approved": False,
        "final_release_approved": False,
    }
    audit = {
        "target": "macos-arm64",
        "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
        "pygame_version": "2.5.8",
        "pygame_distribution": "pygame-ce",
        "redistribution_approved": False,
        "lgpl_relinking_reviewed": False,
        "native_candidates": natives,
    }
    return app, dmg, receipt, audit


class MachOTextCorrespondenceTests(unittest.TestCase):
    def test_exact_text_survives_header_and_signature_metadata_changes(self):
        original = fake_macho()
        transformed = fake_macho(flags=0x100)
        a = review.executable_text_fingerprint(original, "arm64")
        b = review.executable_text_fingerprint(transformed, "arm64")
        self.assertEqual(a, b)
        self.assertEqual(a["sha256"], hashlib.sha256(b"\x92" * 120).hexdigest())
        self.assertEqual(a["size"], 120)
        self.assertNotEqual(hashlib.sha256(original).hexdigest(),
                            hashlib.sha256(transformed).hexdigest())
        self.assertNotEqual(a, review.executable_text_fingerprint(
            fake_macho(code=b"\x93" * 120), "arm64"))

    def test_universal2_slice_extract_and_wrong_arch_is_not_matched(self):
        fat = fake_fat(fake_macho(arch="x86_64"), arch="x86_64")
        result = review.executable_text_fingerprint(fat, "x86_64")
        self.assertEqual(result["size"], 120)
        self.assertIsNone(review.executable_text_fingerprint(fat, "arm64"))
        with self.assertRaises(ValueError):
            review.executable_text_fingerprint(
                fat[:20] + fat[20:28].replace(fat[20:28], b"\xff" * 8)
                + fat[28:], "x86_64")

    def test_corrupt_command_and_out_of_bounds_section_refused(self):
        original = bytearray(fake_macho())
        original[20:24] = (1024 * 1024 + 1).to_bytes(4, "little")
        with self.assertRaises(ValueError):
            review.executable_text_fingerprint(bytes(original), "arm64")
        original = bytearray(fake_macho())
        # section data offset at 32-byte header + 72-byte segment + 48.
        original[152:156] = (999999).to_bytes(4, "little")
        with self.assertRaises(ValueError):
            review.executable_text_fingerprint(bytes(original), "arm64")
        self.assertIsNone(review.executable_text_fingerprint(b"not macho", "arm64"))

    def test_installed_digest_validation_and_all_rights_remain_unapproved(self):
        with TemporaryDirectory() as tmp:
            app, dmg, receipt, audit = install_fixture(tmp)
            sample = review.executable_text_fingerprint(fake_macho(), "arm64")
            matching = {(sample["size"], sample["sha256"]): ["pygame/base.so"]}
            with patch.object(review, "build_wheel_index", return_value=(matching, 24)):
                result = review.audit_bundle(
                    app, dmg, receipt, audit, Path(tmp) / "wheel.whl", "macos-arm64")
                self.assertEqual(result["installed_frozen_native_files_audited"], 121)
                self.assertEqual(result["exact_executable_text_section_matches"], 121)
                for field in ("wheel_build_source_provenance_verified",
                              "native_corresponding_source_complete",
                              "lgpl_library_replacement_verified",
                              "redistribution_approved",
                              "stable_3_1_release_approved"):
                    self.assertFalse(result[field], field)
                target = app / audit["native_candidates"][0]["path"]
                target.write_bytes(b"tamper")
                with self.assertRaises(ValueError):
                    review.audit_bundle(
                        app, dmg, receipt, audit, Path(tmp) / "wheel.whl",
                        "macos-arm64")

    def test_unsafe_paths_and_forged_license_approval_rejected(self):
        with TemporaryDirectory() as tmp:
            app, dmg, receipt, audit = install_fixture(tmp)
            with patch.object(review, "build_wheel_index", return_value=({}, 12)):
                for path in ("../../outside", "/etc/passwd", "Contents//bad",
                             "Contents/../bad"):
                    with self.subTest(path=path):
                        modified = dict(audit, native_candidates=[
                            dict(audit["native_candidates"][0], path=path)
                        ] + audit["native_candidates"][1:])
                        with self.assertRaises(ValueError):
                            review.audit_bundle(
                                app, dmg, receipt, modified, Path(tmp) / "wheel.whl",
                                "macos-arm64")
                for field in ("redistribution_approved", "lgpl_relinking_reviewed"):
                    with self.subTest(field=field):
                        with self.assertRaises(ValueError):
                            review.audit_bundle(
                                app, dmg, receipt, dict(audit, **{field: True}),
                                Path(tmp) / "wheel.whl", "macos-arm64")
                with self.assertRaises(ValueError):
                    review.audit_bundle(
                        app, dmg, dict(receipt, sha256="0" * 64), audit,
                        Path(tmp) / "wheel.whl", "macos-arm64")
                file = app / audit["native_candidates"][0]["path"]
                file.unlink()
                file.symlink_to(Path(tmp) / dmg.name)
                with self.assertRaises(ValueError):
                    review.audit_bundle(
                        app, dmg, receipt, audit, Path(tmp) / "wheel.whl",
                        "macos-arm64")


if __name__ == "__main__":
    unittest.main()
