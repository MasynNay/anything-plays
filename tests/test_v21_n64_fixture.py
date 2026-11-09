"""The N64 runtime fixture must be pinned and never packaged with the app."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import n64_homebrew_fixture as fixture


class N64HomebrewFixtureTests(unittest.TestCase):
    def test_pinned_rom_header_hash_and_size(self):
        data = fixture.N64_MAGIC + bytes(range(16)) * 16
        digest = hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest()
        with patch.object(fixture, "ROM_BYTES", len(data)), \
             patch.object(fixture, "GIT_BLOB_SHA1", digest), \
             patch.object(fixture, "ROM_SHA256", hashlib.sha256(data).hexdigest()):
            result = fixture.checked_rom(data)
            with patch.object(fixture, "ROM_SHA256", "0" * 64):
                with self.assertRaisesRegex(ValueError, "reviewed SHA-256"):
                    fixture.checked_rom(data)
            self.assertEqual(result["bytes"], len(data))
            self.assertEqual(result["git_blob_sha1"], digest)
            self.assertEqual(result["license"], "Unlicense (public domain)")
            with self.assertRaisesRegex(ValueError, "reviewed upstream"):
                fixture.checked_rom(data[:-1] + b"X")

    def test_unexpected_size_and_magic_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unexpected length"):
            fixture.checked_rom(b"")
        with patch.object(fixture, "ROM_BYTES", len(b"not a rom")):
            with self.assertRaisesRegex(ValueError, "incorrect ROM"):
                fixture.checked_rom(b"not a rom")

    def test_fixture_is_not_bundled_and_download_is_ci_only(self):
        self.assertIn("/savetest.z64", fixture.SOURCE_URL)
        self.assertEqual(len(fixture.SOURCE_COMMIT), 40)
        self.assertEqual(len(fixture.GIT_BLOB_SHA1), 40)
        self.assertEqual(len(fixture.ROM_SHA256), 64)
        self.assertLess(fixture.ROM_BYTES, fixture.MAX_DOWNLOAD_BYTES)
        self.assertNotIn("anything_plays/", fixture.SOURCE_URL)
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "savetest.z64"
            # Avoid creating real symlinks: Windows CI may lack the privilege.
            with self.assertRaisesRegex(ValueError, "symlink"):
                with patch.object(Path, "is_symlink", return_value=True):
                    with patch.object(fixture, "checked_rom", return_value={}):
                        with patch.object(fixture, "urlopen") as fake:
                            fake.return_value.__enter__.return_value.read.return_value = b"abc"
                            fixture.verified_homebrew(destination)


if __name__ == "__main__":
    unittest.main()
