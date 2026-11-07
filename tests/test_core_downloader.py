"""Core download metadata and native-header verification without network access."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from fetch_mgba_core import (
    _read_core_archive,
    fetch_core,
    _validate_binary,
    build_target,
    reported_git_revision,
    _inspect_core_identity_isolated,
)


class DownloaderTests(unittest.TestCase):
    def test_all_supported_build_targets(self):
        self.assertEqual(build_target("darwin", "arm64"),
                         ("apple/osx/arm64/latest", ".dylib"))
        self.assertEqual(build_target("win32", "AMD64"),
                         ("windows/x86_64/latest", ".dll"))
        self.assertEqual(build_target("linux", "x86_64"),
                         ("linux/x86_64/latest", ".so"))

    def test_embedded_source_revision_detection(self):
        self.assertEqual(reported_git_revision("0.11-212-7a12d6d"), "7a12d6d")
        self.assertEqual(reported_git_revision("1.63 fae2fea"), "fae2fea")
        self.assertIsNone(reported_git_revision("1.63"))
        self.assertIsNone(reported_git_revision("unknown-version"))

    def test_release_never_fetches_mutable_nightly_urls(self):
        with (
            patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "1", "AP_CORE_ARCHIVE_DIR": "",
            }),
            patch("fetch_mgba_core.request.urlopen") as network,
        ):
            with self.assertRaisesRegex(ValueError, "AP_CORE_ARCHIVE_DIR"):
                _read_core_archive(
                    "https://example.invalid/latest/mgba_libretro.so.zip",
                    "mgba_libretro.so",
                )
            network.assert_not_called()

    def test_release_uses_preserved_offline_archives(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "mgba_libretro.so.zip"
            path.write_bytes(b"Preserved test ZIP input")
            with (
                patch.dict(os.environ, {
                    "AP_RELEASE_BUILD": "1", "AP_CORE_ARCHIVE_DIR": directory,
                }),
                patch("fetch_mgba_core.request.urlopen") as network,
            ):
                content = _read_core_archive(
                    "https://example.invalid/latest/mgba_libretro.so.zip",
                    "mgba_libretro.so",
                )
                self.assertEqual(content, b"Preserved test ZIP input")
                network.assert_not_called()

    def test_release_missing_preserved_archive_fails(self):
        with TemporaryDirectory() as directory:
            with (
                patch.dict(os.environ, {
                    "AP_RELEASE_BUILD": "1", "AP_CORE_ARCHIVE_DIR": directory,
                }),
                patch("fetch_mgba_core.request.urlopen") as network,
            ):
                with self.assertRaises(FileNotFoundError):
                    _read_core_archive(
                        "https://example.invalid/latest/mgba_libretro.so.zip",
                        "mgba_libretro.so",
                    )
                network.assert_not_called()

    def test_candidate_archive_capture_preserves_exact_zip_bytes(self):
        import hashlib
        import io
        import zipfile

        payload = b"\x7fELF" + b"X" * 12000
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w") as archive:
            archive.writestr("mgba_libretro.so", payload)
        original = mem.getvalue()
        with TemporaryDirectory() as temp:
            destination = Path(temp) / "cores"
            archived = Path(temp) / "release-inputs"
            with (
                patch.dict(os.environ, {
                    "AP_RELEASE_BUILD": "0",
                    "AP_CORE_ARCHIVE_CAPTURE_DIR": str(archived),
                    "AP_CORE_ARCHIVE_DIR": "",
                }),
                patch("fetch_mgba_core.build_target",
                      return_value=("linux/x86_64/latest", ".so")),
                patch("fetch_mgba_core._read_core_archive", return_value=original),
                patch("fetch_mgba_core.inspect_core_identity", return_value={
                    "libretro_library_name": "mGBA",
                    "libretro_library_version": "test 7a12d6d",
                    "reported_source_revision": "7a12d6d",
                    "source_repository_url": "https://github.com/libretro/mgba",
                    "reported_source_commit_url": None,
                }),
            ):
                result = fetch_core("mgba", destination)
            self.assertEqual(
                (archived / "mgba_libretro.so.zip").read_bytes(), original
            )
            self.assertEqual(result["archive_sha256"],
                             hashlib.sha256(original).hexdigest())
            self.assertEqual(result["archive_size_bytes"], len(original))

    def test_windows_native_metadata_probe_releases_dll_in_child_process(self):
        import json
        from subprocess import CompletedProcess

        metadata = {
            "libretro_library_name": "Stella 2014",
            "libretro_library_version": "3.9",
            "reported_source_revision": None,
        }
        output = "Native status message\\nAP_NATIVE_IDENTITY=" + json.dumps(metadata) + "\\n"
        with patch("fetch_mgba_core.subprocess.run",
                   return_value=CompletedProcess([], 0, output, "")) as run:
            value = _inspect_core_identity_isolated(
                Path("temporary-libretro.dll"), "stella2014"
            )
        self.assertEqual(value, metadata)
        argv = run.call_args.args[0]
        self.assertEqual(argv[1], "-c")
        self.assertIn("_inspect_core_identity_in_process", argv[2])
        self.assertEqual(argv[-1], "stella2014")
        self.assertEqual(run.call_args.kwargs["timeout"], 20)

    def test_windows_identity_subprocess_crash_fails_closed(self):
        from subprocess import CompletedProcess
        with patch("fetch_mgba_core.subprocess.run",
                   return_value=CompletedProcess([], 1, "", "native crash")):
            with self.assertRaisesRegex(RuntimeError, "native crash"):
                _inspect_core_identity_isolated(
                    Path("temporary-libretro.dll"), "stella2014"
                )

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
