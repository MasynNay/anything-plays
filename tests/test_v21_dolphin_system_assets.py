"""Self-contained Dolphin Sys download/extraction contract, offline and safe."""
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import zipfile

from tools.fetch_dolphin_sys import (
    ARCHIVE_NAME, MANIFEST_NAME, MAX_DOWNLOAD_BYTES,
    extract_dolphin_sys, read_system_archive,
)
from verify_bundle import verify_dolphin_sys


def sample_archive(extras=None):
    files = {
        "dolphin-emu/Sys/codehandler.bin": b"fixture data",
        "dolphin-emu/Sys/GameSettings/AAA.ini": b"[Core]\n",
        "dolphin-emu/Sys/GameSettings/BBB.ini": b"[Video]\n",
        "dolphin-emu/Sys/Resources/font.bin": b"font fixture",
        "dolphin-emu/Sys/Resources/keys.txt": b"synthetic",
    }
    files.update(extras or {})
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, blob in files.items():
            archive.writestr(name, blob)
    return memory.getvalue()


class SystemAssetsTests(unittest.TestCase):
    def test_gamecube_bundle_contains_full_sys_with_verified_manifest(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "cores"
            archive = sample_archive()
            manifest = extract_dolphin_sys(archive, root)
            self.assertEqual(manifest["file_count"], 5)
            self.assertEqual(
                manifest["archive_sha256"], hashlib.sha256(archive).hexdigest()
            )
            self.assertTrue((root / "dolphin-emu/Sys/codehandler.bin").is_file())
            self.assertTrue((root / MANIFEST_NAME).is_file())
            verify_dolphin_sys(root, {"dolphin_system_assets": manifest})

    def test_corrupt_or_missing_sys_fails_installer_verification(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = extract_dolphin_sys(sample_archive(), root)
            (root / "dolphin-emu/Sys/GameSettings/AAA.ini").write_bytes(b"CORRUPT")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_dolphin_sys(root, {"dolphin_system_assets": manifest})
            (root / "dolphin-emu/Sys/codehandler.bin").unlink()
            with self.assertRaisesRegex(ValueError, "Missing Dolphin Sys file"):
                verify_dolphin_sys(root, {"dolphin_system_assets": manifest})

    def test_missing_codehandler_rejected_before_writing_any_files(self):
        archive = sample_archive()
        with zipfile.ZipFile(io.BytesIO(archive)) as inputs:
            files = {item.filename: inputs.read(item.filename)
                     for item in inputs.infolist()
                     if not item.filename.endswith("codehandler.bin")}
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "missing required system data"):
                extract_dolphin_sys(sample_archive(files), Path(tmp) / "cores")

    def test_path_traversal_and_symlinks_are_rejected(self):
        for malicious in (
            "dolphin-emu/Sys/../outside.txt",
            "dolphin-emu/Sys/../../escape.txt",
        ):
            with self.subTest(malicious=malicious):
                with TemporaryDirectory() as tmp:
                    with self.assertRaisesRegex(ValueError, "Unsafe"):
                        extract_dolphin_sys(
                            sample_archive({malicious: b"evil"}), tmp
                        )

    def test_test_build_may_read_preserved_archive_without_network(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = sample_archive()
            (root / ARCHIVE_NAME).write_bytes(payload)
            with patch.dict("os.environ", {
                "AP_RELEASE_BUILD": "0",
                "AP_CORE_ARCHIVE_DIR": str(root),
            }), patch("tools.fetch_dolphin_sys.request.urlopen") as network:
                self.assertEqual(read_system_archive(), payload)
                network.assert_not_called()

    def test_release_build_rejects_mutable_dolphin_system_download(self):
        with patch.dict("os.environ", {"AP_RELEASE_BUILD": "1"}):
            with self.assertRaisesRegex(ValueError, "approved/pinned"):
                read_system_archive()


if __name__ == "__main__":
    unittest.main()
