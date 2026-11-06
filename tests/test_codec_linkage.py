"""Synthetic Mach-O linkage evidence tests (no macOS runner required)."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.audit_codec_linkage import inspect_macos_bundle, parse_otool


class LinkageAuditTests(unittest.TestCase):
    def test_parse_otool_ignores_binary_header(self):
        sample = (
            "/app/cv2/libavcodec.dylib:\n"
            "\t@rpath/libx264.164.dylib (compatibility version 1.0.0, current version 1.0.0)\n"
            "\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1319.0.0)\n"
        )
        self.assertEqual(parse_otool(sample), [
            "@rpath/libx264.164.dylib", "/usr/lib/libSystem.B.dylib"
        ])

    def test_records_direct_encoder_links_and_does_not_authorize_removal(self):
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / "AnythingPlays.app"
            folder = bundle / "Contents" / "Frameworks" / "cv2" / "__dot__dylibs"
            folder.mkdir(parents=True)
            codec = folder / "libx264.164.dylib"
            codec.write_bytes(b"mock MachO")
            encoder = folder / "libavcodec.61.dylib"
            encoder.write_bytes(b"mock MachO")

            def output(path):
                line = "@rpath/libx264.164.dylib" if path == encoder else "/usr/lib/libSystem.B.dylib"
                return (str(path) + ":\n" + "\t" + line +
                        " (compatibility version 1.0.0, current version 1.0.0)\n")

            report = inspect_macos_bundle(bundle, command=output)
            self.assertEqual(report["examined_files"], 2)
            self.assertFalse(report["redistribution_approved"])
            self.assertFalse(report["safe_to_delete_codec_libraries"])
            self.assertEqual(len(report["codec_direct_link_referrers"]["libx264"]), 1)
            self.assertTrue(report["codec_direct_link_referrers"]["libx264"][0].endswith("libavcodec.61.dylib"))

    def test_fails_if_bundle_missing(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Missing packaged OpenCV"):
                inspect_macos_bundle(Path(directory))


if __name__ == "__main__":
    unittest.main()
