"""Core download metadata and native-header verification without network access."""

import unittest

from fetch_mgba_core import _validate_binary, build_target


class DownloaderTests(unittest.TestCase):
    def test_all_supported_build_targets(self):
        self.assertEqual(build_target("darwin", "arm64"),
                         ("apple/osx/arm64/latest", ".dylib"))
        self.assertEqual(build_target("win32", "AMD64"),
                         ("windows/x86_64/latest", ".dll"))
        self.assertEqual(build_target("linux", "x86_64"),
                         ("linux/x86_64/latest", ".so"))

    def test_unsupported_platform_rejected(self):
        with self.assertRaises(ValueError):
            build_target("plan9", "arm64")

    def test_native_headers_are_checked(self):
        for data, extension in ((b"MZ\x00", ".dll"),
                                (b"\x7fELFxxx", ".so"),
                                (b"\xcf\xfa\xed\xfex", ".dylib")):
            _validate_binary(data, extension)
        with self.assertRaises(ValueError):
            _validate_binary(b"<html>not a binary", ".so")


if __name__ == "__main__":
    unittest.main()
