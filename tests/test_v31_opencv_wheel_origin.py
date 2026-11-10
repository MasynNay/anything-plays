"""The last Mac SDL2 library cannot be silently called pygame or approved."""
import hashlib
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from tools import inspect_v31_opencv_wheel_origin as origin
from tools.inspect_v31_macos_text_provenance import executable_text_fingerprint


def mach_o(code):
    offset = 32 + 72 + 80
    return (
        struct.pack("<IIIIIIII", 0xfeedfacf, 0x0100000c, 0, 6, 1, 152, 0, 0)
        + struct.pack("<II16sQQQQiiII", 0x19, 152, b"__TEXT", 0,
                      offset + len(code), 0, offset + len(code), 7, 5, 1, 0)
        + struct.pack("<16s16sQQIIIIIIII", b"__text", b"__TEXT",
                      offset, len(code), offset, 0, 0, 0, 0, 0, 0, 0)
        + code
    )


def fixture(original_text):
    rows = []
    for n in range(120):
        rows.append({
            "path": f"Contents/Frameworks/pygame/{n}.so",
            "sha256": "a" * 64,
            "upstream_matching_wheel_members": ["pygame/test.so"],
        })
    rows.append({
        "path": origin.MISSING_PATH,
        "sha256": origin.MISSING_SHA,
        "text_section": original_text,
        "upstream_matching_wheel_members": [],
    })
    return {
        "status": "PUBLIC_RC1_READ_ONLY_MACOS_TEXT_SECTION_AUDIT",
        "target": "macos-arm64",
        "source_app_commit": origin.RC_APP_COMMIT,
        "installed_frozen_native_files_audited": 121,
        "exact_executable_text_section_matches": 120,
        "unmatched_installed_native_sections": 1,
        "redistribution_approved": False,
        "stable_3_1_release_approved": False,
        "native_file_evidence": rows,
    }


class OpenCVWheelOriginContracts(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / origin.WHEEL
        self.original = mach_o(b"\x88" * 96)
        self.text = executable_text_fingerprint(self.original, "arm64")
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("cv2/.dylibs/libSDL2-2.0.0.dylib", self.original)
        self.wheel_sha = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def inspect(self, report=None):
        if report is None:
            report = fixture(self.text)
        with patch.object(origin, "WHEEL_SHA", self.wheel_sha), \
             patch.object(origin, "TEXT_SHA", self.text["sha256"]), \
             patch.object(origin, "TEXT_LENGTH", self.text["size"]), \
             patch.object(origin, "MIN_WHEEL_BYTES", 1):
            return origin.inspect(report, self.path)

    def test_exact_machine_code_fingerprint_from_official_wheel(self):
        result = self.inspect()
        self.assertTrue(result["additional_opencv_code_section_match"])
        self.assertEqual(result["total_native_code_section_matches"], 121)
        self.assertEqual(result["wheel_native_text_comparison"]["wheel_member"],
                         "cv2/.dylibs/libSDL2-2.0.0.dylib")
        for field in ("upstream_opencv_sdl_source_tree_correspondence_verified",
                      "complete_transitive_license_reviewed",
                      "lgpl_relinking_verified",
                      "redistribution_approved",
                      "stable_3_1_release_approved"):
            self.assertFalse(result[field], field)

    def test_wrong_wheel_code_can_never_be_mistaken_for_match(self):
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("cv2/.dylibs/libSDL2-2.0.0.dylib",
                       mach_o(b"\x89" * 96))
        self.wheel_sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        result = self.inspect()
        self.assertFalse(result["additional_opencv_code_section_match"])
        self.assertEqual(result["total_native_code_section_matches"], 120)

    def test_wrong_original_report_flags_or_unmatched_identity_refused(self):
        for field, value in (("target", "macos-x64"),
                             ("redistribution_approved", True),
                             ("stable_3_1_release_approved", True),
                             ("exact_executable_text_section_matches", 121),
                             ("unmatched_installed_native_sections", 0),
                             ("source_app_commit", "0" * 40)):
            with self.subTest(field=field):
                report = fixture(self.text)
                report[field] = value
                with self.assertRaises(ValueError):
                    self.inspect(report)
        report = fixture(self.text)
        report["native_file_evidence"][-1]["sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.inspect(report)

    def test_official_wheel_filename_digest_and_contents_must_match(self):
        with self.assertRaises(ValueError):
            origin.inspect(fixture(self.text), self.path)  # no fake official SHA
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("cv2/.dylibs/wrong-libSDL2-2.0.0.dylib", self.original)
        self.wheel_sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.inspect()
        self.path.unlink()
        with self.assertRaises(ValueError):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
