"""No approved LGPL claims from a mere pygame native extension swap."""
import hashlib
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from tools import probe_v31_macos_lgpl_replacement as probe


def macho(text=b"\x11" * 160, flags=0):
    start = 32 + 72 + 80
    return (
        struct.pack("<IIIIIIII", 0xfeedfacf, 0x0100000c, 0, 6, 1, 152, flags, 0)
        + struct.pack("<II16sQQQQiiII", 0x19, 152, b"__TEXT", 0,
                      start + len(text), 0, start + len(text), 7, 5, 1, 0)
        + struct.pack("<16s16sQQIIIIIIII", b"__text", b"__TEXT",
                      start, len(text), start, 0, 0, 0, 0, 0, 0, 0)
        + text
    )


def setup(root):
    root = Path(root)
    app = root / "frozen.app"
    file = app / probe.FROZEN_PATH
    file.parent.mkdir(parents=True)
    file.write_bytes(macho(flags=0x42))
    (app / "Contents/MacOS").mkdir(parents=True)
    (app / "Contents/MacOS/App").write_bytes(b"not a real app")
    target = "macos-arm64"
    installer = root / "AnythingPlays-3.1.0-rc1-full-macos-arm64.dmg"
    installer.write_bytes(b"fake pinned DMG")
    receipt = {
        "status": probe.TARGETS[target][0], "target": target,
        "source_preview_revision": probe.RC_APP_COMMIT,
        "installer": installer.name, "sha256": probe.digest(installer),
        "native_core_count": 11, "console_profiles": 18,
        "public_release_approved": False, "final_release_approved": False,
    }
    audit = {
        "target": target,
        "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
        "pygame_version": "2.5.8", "pygame_distribution": "pygame-ce",
        "redistribution_approved": False,
        "lgpl_relinking_reviewed": False,
        "native_candidates": [{
            "path": probe.FROZEN_PATH, "sha256": probe.digest(file),
        }],
    }
    wheel = root / probe.WHEELS[target][0]
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr(probe.WHEEL_MEMBER, macho(flags=0))
        z.writestr("pygame-data/padding.bin", b"\x00" * 1_001_000)
    return app, installer, receipt, audit, wheel


class NativeReplacementSafety(unittest.TestCase):
    def test_copy_official_pygame_native_into_sandbox_without_approval(self):
        with TemporaryDirectory() as td:
            app, installer, receipt, audit, wheel = setup(td)
            old = probe.digest(app / probe.FROZEN_PATH)
            with patch.dict(probe.WHEELS, {"macos-arm64": (
                    wheel.name, probe.digest(wheel))}):
                result = probe.stage_replacement(
                    app, installer, receipt, audit, wheel,
                    "macos-arm64", Path(td) / "disposable.app")
            self.assertEqual(probe.digest(app / probe.FROZEN_PATH), old)
            self.assertNotEqual(probe.digest(Path(td)/"disposable.app"/probe.FROZEN_PATH), old)
            self.assertTrue(result["original_unmodified_after_staging"])
            self.assertTrue(result["original_and_upstream_text_section_equal"])
            for field in ("re_signed_modified_app",
                          "frozen_app_startup_after_swap_verified",
                          "modified_pygame_source_compiled_and_tested",
                          "lgpl_replacement_and_relinking_compliance_approved",
                          "complete_corresponding_source_approved",
                          "stable_3_1_release_approved"):
                self.assertFalse(result[field], field)

    def test_tampered_native_and_original_installer_fails(self):
        with TemporaryDirectory() as td:
            app, installer, receipt, audit, wheel = setup(td)
            with patch.dict(probe.WHEELS, {"macos-arm64": (
                    wheel.name, probe.digest(wheel))}):
                for key, bad in (
                    ("source_preview_revision", "0" * 40),
                    ("public_release_approved", True),
                    ("native_core_count", 1),
                    ("sha256", "f" * 64),
                ):
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        probe.stage_replacement(
                            app, installer, dict(receipt, **{key: bad}),
                            audit, wheel, "macos-arm64", Path(td)/"copy.app")
                edited = dict(audit, native_candidates=[
                    dict(audit["native_candidates"][0], sha256="0"*64)])
                with self.assertRaises(ValueError):
                    probe.stage_replacement(
                        app, installer, receipt, edited, wheel,
                        "macos-arm64", Path(td)/"copy.app")

    def test_different_upstream_machine_code_is_not_accepted(self):
        with TemporaryDirectory() as td:
            app, installer, receipt, audit, wheel = setup(td)
            with zipfile.ZipFile(wheel, "w") as z:
                z.writestr(probe.WHEEL_MEMBER, macho(text=b"\x12"*160))
                z.writestr("padding", b"\0" * 1_001_000)
            with patch.dict(probe.WHEELS, {"macos-arm64": (
                    wheel.name, probe.digest(wheel))}):
                with self.assertRaises(ValueError):
                    probe.stage_replacement(app, installer, receipt, audit,
                                            wheel, "macos-arm64", Path(td)/"copy.app")

    def test_copy_cannot_overwrite_original_or_escape_via_native_link(self):
        with TemporaryDirectory() as td:
            app, installer, receipt, audit, wheel = setup(td)
            with patch.dict(probe.WHEELS, {"macos-arm64": (
                    wheel.name, probe.digest(wheel))}):
                with self.assertRaises(ValueError):
                    probe.stage_replacement(app, installer, receipt, audit,
                                            wheel, "macos-arm64", app)
                original = app / probe.FROZEN_PATH
                original.unlink()
                original.symlink_to(installer)
                with self.assertRaises(ValueError):
                    probe.stage_replacement(app, installer, receipt, audit,
                                            wheel, "macos-arm64", Path(td)/"copy.app")


if __name__ == "__main__":
    unittest.main()
