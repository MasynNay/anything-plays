"""No-game tests for isolated full-native v3.3 dynamic-link QA."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest
from unittest.mock import Mock, patch

from tools import v33_full_native_link as link


GOOD = {
    "native_core_count": 11,
    "all_console_profiles": 18,
    "source_built_dolphin": {"source_commit": "synthetic-original"},
    "source_built_tia": {"source_commit": "synthetic-original"},
}


class V33NativeCoreLinkTests(unittest.TestCase):
    def fixture(self, root, extension=".so"):
        cores = Path(root) / "cores"
        cores.mkdir()
        for i in range(11):
            (cores / f"core{i:02d}_libretro{extension}").write_bytes(
                b"only synthetic placeholder bytes"
            )
        return cores

    def test_strict_native_inventory_for_each_host(self):
        for target, suffix in link.EXTENSIONS.items():
            with self.subTest(target=target), TemporaryDirectory() as root:
                cores = self.fixture(root, suffix)
                with patch.object(link, "validate_trial_core_directory",
                                  return_value=dict(GOOD)) as verify:
                    paths = link.core_files(cores, target)
                self.assertEqual(len(paths), 11)
                self.assertEqual(paths, sorted(paths))
                verify.assert_called_once_with(cores, suffix)

    def test_missing_extra_symlink_and_unreviewed_native_inventory_fail(self):
        with TemporaryDirectory() as root:
            cores = self.fixture(root)
            with patch.object(link, "validate_trial_core_directory",
                              return_value=dict(GOOD)):
                (cores / "core10_libretro.so").unlink()
                with self.assertRaisesRegex(ValueError, "11"):
                    link.core_files(cores, "linux-x64")
                (cores / "core10_libretro.so").write_bytes(b"fake")
                extra = cores / "extra_libretro.so"
                extra.write_bytes(b"not reviewed")
                with self.assertRaisesRegex(ValueError, "11"):
                    link.core_files(cores, "linux-x64")
                extra.unlink()
                (cores / "core10_libretro.so").unlink()
                (cores / "core10_libretro.so").symlink_to(
                    cores / "core00_libretro.so"
                )
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    link.core_files(cores, "linux-x64")
            with self.assertRaises(ValueError):
                link.core_files(cores, "macos-x64")

    def test_rejects_misleading_provenance_and_target(self):
        with TemporaryDirectory() as root:
            cores = self.fixture(root)
            for key, bad in (
                ("native_core_count", 10),
                ("all_console_profiles", 3),
                ("source_built_dolphin", False),
                ("source_built_tia", False),
            ):
                with self.subTest(key=key):
                    with patch.object(link, "validate_trial_core_directory",
                                      return_value={**GOOD, key: bad}):
                        with self.assertRaisesRegex(ValueError, "provenance"):
                            link.core_files(cores, "linux-x64")
            with self.assertRaises(ValueError):
                link.core_files(cores, "unknown")

    def test_subprocess_crash_timeout_or_link_error_is_reported_without_paths(self):
        with TemporaryDirectory() as root:
            cores = self.fixture(root)
            with patch.object(link, "validate_trial_core_directory",
                              return_value=dict(GOOD)):
                okay = link.audit(cores, "linux-x64",
                                  run=Mock(return_value=Mock(returncode=0)))
                self.assertTrue(okay["all_core_abi_symbols_loadable"])
                self.assertEqual(okay["native_cores_checked"], 11)
                self.assertFalse(okay["physical_gameplay_tested"])
                self.assertFalse(okay["public_release_approved"])
                self.assertEqual(len(okay["cores"]), 11)
                failing = link.audit(
                    cores, "linux-x64",
                    run=Mock(side_effect=subprocess.TimeoutExpired(
                        ["/home/private/gamecube"], 3)),
                )
                self.assertFalse(failing["all_core_abi_symbols_loadable"])
                self.assertEqual(
                    sum(int(not row["abi_symbols_loadable"])
                        for row in failing["cores"]), 11,
                )
                partial = iter([Mock(returncode=0)] * 10 + [
                    Mock(returncode=-11),
                ])
                result = link.audit(
                    cores, "linux-x64",
                    run=lambda *args, **kwargs: next(partial),
                )
                self.assertFalse(result["all_core_abi_symbols_loadable"])
                encoded = json.dumps(result)
                for private in ("/home", "private", "ROM",
                                "stderr", "device"):
                    self.assertNotIn(private, encoded)
            for t in (0, 61, -1):
                with self.assertRaises(ValueError):
                    link.audit(cores, "linux-x64", timeout=t,
                               run=Mock())

    def test_libretro_abi_version_must_be_one_no_game_initialization(self):
        native = Mock()
        native.retro_api_version.return_value = 1
        with TemporaryDirectory() as directory:
            path = Path(directory) / "demo_libretro.so"
            path.write_bytes(b"fake")
            # On Windows the genuine runtime registrar requires a signed
            # original-source manifest. This fixture is intentionally fake;
            # mock that boundary rather than weaken production provenance.
            with patch.object(link, "enable_windows_trial_runtime"):
                with patch.object(link.ctypes, "CDLL", return_value=native) as loader:
                    link.isolated_probe(path)
                    loader.assert_called_once()
                native.retro_api_version.assert_called_once_with()
                native.retro_init.assert_not_called()
                native.retro_load_game.assert_not_called()
                native.retro_run.assert_not_called()
                native.retro_api_version.return_value = 9
                with patch.object(link.ctypes, "CDLL", return_value=native):
                    with self.assertRaisesRegex(ValueError, "ABI"):
                        link.isolated_probe(path)


if __name__ == "__main__":
    unittest.main()
