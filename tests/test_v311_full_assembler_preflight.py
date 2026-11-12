"""Reject wrong-source 3.1.1 full installers before touching OS packaging.

These tests never unzip, install, execute, sign or publish any installer.
The subprocess boundary is deliberately mocked; the native CI matrix must
still test actual DEBs, EXEs and DMGs separately.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.assemble_v311_full_linux import (
    prepare as linux_prepare, BASELINE_NAME as LINUX_BASE,
)
from tools.assemble_v311_full_windows import (
    build as windows_build, OLD as WINDOWS_BASE,
)
from tools.assemble_v311_full_macos import build as mac_build
from tools.verify_v311_source_stage import (
    INSTALLERS as QA_INSTALLERS, STATUS as QA_STATUS,
)
from tools.verify_v311_stable_source_stage import (
    INSTALLERS as STABLE_INSTALLERS, STATUS as STABLE_STATUS,
)
from tools.v311_camera_source_gate import SOURCE_RUN_BY_TARGET
from tools.qa_v31_linux_camera_only_wheel import SOURCE_SHA256

SHA = "a" * 40


def hash_bytes(filename):
    h = hashlib.sha256()
    with Path(filename).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class FullVersion311GateTests(unittest.TestCase):
    def fixture(self, target, *, stable_update):
        td = tempfile.TemporaryDirectory(prefix="ap311-native-source-contract-")
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        old_name = (
            LINUX_BASE if target == "linux-x64"
            else WINDOWS_BASE if target == "windows-x64"
            else "AnythingPlays-3.1.0-macos-" + target.split("-")[1] + ".dmg"
        )
        new_name = (STABLE_INSTALLERS if stable_update else QA_INSTALLERS)[target]
        old = root / old_name
        fresh = root / new_name
        old.write_bytes(b"O" * (1024 * 1024 + 5))
        fresh.write_bytes(b"N" * (1024 * 1024 + 5))
        checksums = root / "SHA256SUMS.txt"
        checksums.write_text(hash_bytes(old) + "  " + old_name + "\n", "utf-8")
        receipt = root / "source.json"
        receipt.write_text(json.dumps({
            "status": STABLE_STATUS if stable_update else QA_STATUS,
            "target": target, "installer": new_name,
            "sha256": hash_bytes(fresh), "size_bytes": fresh.stat().st_size,
            "source_revision": SHA,
            "version": "3.1.1" if stable_update else "3.1.1-qa1",
            "identity_channel": "v311_stable_candidate"
                                if stable_update else "v311_candidate",
            "settings_namespace": "anything-plays-31"
                                  if stable_update else "anything-plays-311-candidate",
            "native_core_count": 1,
            "full_18_console_installer": False,
            "public_release_approved": False,
        }), "utf-8")
        camera = root / "opencv.json"
        camera.write_text(json.dumps({
            "source_ci_run_id": SOURCE_RUN_BY_TARGET[target],
            "target": target, "source_sha256": SOURCE_SHA256,
            "native_wheel_sha256": "b" * 64,
            "native_camera_capture_backend_proven": True,
            "frozen_installer_tested": False,
            "redistribution_approved": False,
            "public_release_approved": False,
        }), "utf-8")
        return old, fresh, checksums, receipt, camera, root / "output"

    def enter_linux(self, target, stable_update):
        old, fresh, sums, receipt, camera, output = self.fixture(
            target, stable_update=stable_update,
        )
        with patch("tools.assemble_v311_full_linux.subprocess.run",
                   side_effect=RuntimeError("native dpkg boundary")) as runner:
            with self.assertRaisesRegex(RuntimeError, "native dpkg boundary"):
                linux_prepare(old, fresh, sums, receipt, camera, SHA, output,
                              stable_update=stable_update)
            runner.assert_called_once()

    def test_linux_accepts_both_versioned_source_channels_up_to_native_boundary(self):
        for stable in (False, True):
            with self.subTest(stable_update=stable):
                self.enter_linux("linux-x64", stable)

    def test_windows_accepts_both_3_1_1_source_channels_to_unpack_boundary(self):
        for stable in (False, True):
            with self.subTest(stable_update=stable):
                args = self.fixture("windows-x64", stable_update=stable)
                with patch("tools.assemble_v311_full_windows.unpack",
                           side_effect=RuntimeError("native Inno boundary")) as unpack:
                    with self.assertRaisesRegex(RuntimeError, "native Inno boundary"):
                        windows_build(*args[:5], SHA, args[5], stable_update=stable)
                    unpack.assert_called_once()

    def test_macos_accepts_both_source_channels_up_to_diskimages_boundary(self):
        for arch in ("arm64", "x64"):
            for stable in (False, True):
                with self.subTest(arch=arch, stable_update=stable):
                    args=self.fixture("macos-"+arch, stable_update=stable)
                    with patch("tools.assemble_v311_full_macos.mount",
                               side_effect=RuntimeError("native DMG boundary")) as mount:
                        with self.assertRaisesRegex(RuntimeError, "native DMG boundary"):
                            mac_build(arch, *args[:5], SHA, args[5],
                                      stable_update=stable)
                        mount.assert_called_once()

    def test_wrong_channel_identity_fails_before_linux_native_install(self):
        old, fresh, sums, receipt, camera, output = self.fixture(
            "linux-x64", stable_update=True)
        meta=json.loads(receipt.read_text("utf-8"))
        meta["settings_namespace"]="anything-plays-311-candidate"
        receipt.write_text(json.dumps(meta),"utf-8")
        with patch("tools.assemble_v311_full_linux.subprocess.run") as runner:
            with self.assertRaisesRegex(ValueError, "receipt"):
                linux_prepare(old, fresh, sums, receipt, camera, SHA, output,
                              stable_update=True)
            runner.assert_not_called()

    def test_original_public_core_checksum_cannot_be_substituted(self):
        old, fresh, sums, receipt, camera, output=self.fixture(
            "linux-x64", stable_update=True)
        sums.write_text("0"*64+"  "+old.name+"\n","utf-8")
        with patch("tools.assemble_v311_full_linux.subprocess.run") as runner:
            with self.assertRaisesRegex(ValueError, "checksum"):
                linux_prepare(old,fresh,sums,receipt,camera,SHA,output,
                              stable_update=True)
            runner.assert_not_called()

    def test_missing_original_camera_wheel_receipt_refuses_all_full_builds(self):
        old,fresh,sums,receipt,camera,output=self.fixture(
            "linux-x64",stable_update=True)
        camera.unlink()
        with patch("tools.assemble_v311_full_linux.subprocess.run") as runner:
            with self.assertRaisesRegex(ValueError, "OpenCV wheel receipt"):
                linux_prepare(old,fresh,sums,receipt,camera,SHA,output,
                              stable_update=True)
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
