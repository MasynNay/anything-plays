"""Regression tests for Windows source-built runtime DLL handle lifetime.

No actual Windows library is loaded. We exercise the exact real SHA validator
and the OS registration boundary in unit tests on every CI platform.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from anything_plays import v30_gpl_trial as trial


class WindowsGPLTrialDllHandleLifetime(unittest.TestCase):
    def _fixture(self, root):
        root = Path(root)
        root.mkdir(exist_ok=True, parents=True)
        raw = b"MZ" + b"source-built-test-only-winpthread" * 1200
        (root / trial.WINDOWS_RUNTIME).write_bytes(raw)
        info = {"runtime_dependencies": {
            trial.WINDOWS_RUNTIME: hashlib.sha256(raw).hexdigest(),
        }}
        return info

    def test_500_launches_keep_one_handle_for_one_directory(self):
        with TemporaryDirectory() as tmp:
            core = Path(tmp) / "installed"
            info = self._fixture(core)
            handle = mock.Mock()
            with mock.patch.object(trial.os, "add_dll_directory", return_value=handle,
                                   create=True) as register:
                try:
                    for _ in range(500):
                        trial._register_windows_runtime_directory(core, info)
                    register.assert_called_once_with(str(core.resolve()))
                    self.assertEqual(len(trial._WINDOWS_NATIVE_DLL_HANDLES), 1)
                    self.assertIs(
                        trial._WINDOWS_NATIVE_DLL_HANDLES[str(core.resolve())], handle)
                    # A second real installed core directory is independent.
                    second = Path(tmp) / "second"
                    second_info = self._fixture(second)
                    trial._register_windows_runtime_directory(second, second_info)
                    self.assertEqual(register.call_count, 2)
                    self.assertEqual(len(trial._WINDOWS_NATIVE_DLL_HANDLES), 2)
                finally:
                    trial._WINDOWS_NATIVE_DLL_HANDLES.clear()

    def test_tampered_runtime_fails_even_when_directory_is_cached(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            info = self._fixture(root)
            with mock.patch.object(trial.os, "add_dll_directory",
                                   return_value=object(), create=True) as register:
                try:
                    trial._register_windows_runtime_directory(root, info)
                    raw = (root / trial.WINDOWS_RUNTIME).read_bytes()
                    (root / trial.WINDOWS_RUNTIME).write_bytes(raw[:-1] + b"x")
                    with self.assertRaisesRegex(ValueError, "modified"):
                        trial._register_windows_runtime_directory(root, info)
                    self.assertEqual(register.call_count, 1)
                finally:
                    trial._WINDOWS_NATIVE_DLL_HANDLES.clear()

    def test_missing_and_symlinked_windows_runtime_never_register(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "core"
            info = self._fixture(root)
            path = root / trial.WINDOWS_RUNTIME
            with mock.patch.object(trial.os, "add_dll_directory",
                                   return_value=object(), create=True) as register:
                try:
                    path.unlink()
                    with self.assertRaises(ValueError):
                        trial._register_windows_runtime_directory(root, info)
                    with TemporaryDirectory() as other:
                        target = Path(other) / "original.dll"
                        target.write_bytes(b"MZ" + b"source-built-test-only-winpthread" * 1200)
                        path.symlink_to(target)
                        with self.assertRaises(ValueError):
                            trial._register_windows_runtime_directory(root, info)
                    self.assertEqual(register.call_count, 0)
                    self.assertEqual(len(trial._WINDOWS_NATIVE_DLL_HANDLES), 0)
                finally:
                    trial._WINDOWS_NATIVE_DLL_HANDLES.clear()


if __name__ == "__main__":
    unittest.main()
