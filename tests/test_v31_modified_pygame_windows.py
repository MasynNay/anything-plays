"""Adversarial native C source and Windows PE swap tests, no legal overclaims."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import struct
import unittest
from unittest.mock import patch
import zipfile

from tools import build_v31_modified_pygame_windows as builder
from tools import verify_v31_modified_pygame_windows as verifier
from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE


def pe_data(machine=0x8664):
    data = bytearray(40_000)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", data, 0x84, machine)
    data[-64:] = (b"original compiled source test marker " * 2)[:64]
    return bytes(data)


def minimal_fixture(root):
    root=Path(root)
    bundle=root/"original-app"
    original=bundle/"_internal/pygame/base.cp313-win_amd64.pyd"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"Original verified upstream pygame native" * 1000)
    compiled=root/builder.OUTPUT_NAME
    compiled.write_bytes(pe_data())
    wheel=root/"original.whl"
    wheel.write_bytes(b"fixture upstream wheel")
    installer=root/"AnythingPlaysSetup-3.1.0-rc1-full.exe"
    installer.write_bytes(b"fixture RC1 package")
    manifest={
        "original_source_revision":PYGAME_COMMIT,
        "original_base_c_sha256":"0"*64,
        "patched_base_c_sha256":builder.PINNED_CHANGED_C_SHA256,
        "expected_modified_native_method":"_ap31_relink_probe",
        "expected_modified_native_result":PROBE_VALUE,
        "not_official_unmodified_pygame_wheel":True,
        "full_lgpl_compliance_approved":False,
        "stable_3_1_release_approved":False,
    }
    return bundle,original,installer,wheel,compiled,manifest


class WindowsModifiedNativeContracts(unittest.TestCase):
    def test_native_pe_must_be_amd64(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/builder.OUTPUT_NAME
            p.write_bytes(pe_data())
            self.assertEqual(builder.validate_pe_amd64(p), 40_000)
            p.write_bytes(pe_data(0x14c))
            with self.assertRaisesRegex(ValueError,"x64"):
                builder.validate_pe_amd64(p)
            p.write_bytes(b"not executable")
            with self.assertRaises(ValueError):
                builder.validate_pe_amd64(p)

    def test_stages_only_separate_copy_with_different_c_binary(self):
        with TemporaryDirectory() as tmp:
            bundle,original,installer,wheel,compiled,manifest=minimal_fixture(tmp)
            before=verifier.digest(original)
            with patch.object(verifier,"validate_original",return_value=(
                    original,original.read_bytes(),"pygame/base.cp313-win_amd64.pyd")):
                report=verifier.stage(bundle,installer,{}, {},wheel,
                                      manifest,compiled,Path(tmp)/"copied-app")
            self.assertEqual(verifier.digest(original),before)
            copied=Path(tmp)/"copied-app"/original.relative_to(bundle)
            self.assertEqual(copied.read_bytes(),compiled.read_bytes())
            self.assertTrue(report["source_modified_native_is_distinct_pe_amd64"])
            self.assertTrue(report["original_signed_installer_and_frozen_app_untouched"])
            for field in ("modified_native_method_executed_from_copied_app",
                          "copied_original_rc1_frozen_tk_gui_started",
                          "all_lgpl_relinking_requirements_approved",
                          "full_corresponding_source_approved",
                          "stable_3_1_release_approved"):
                self.assertFalse(report[field],field)

    def test_refuses_fake_source_and_tampered_copied_app(self):
        with TemporaryDirectory() as tmp:
            bundle,original,installer,wheel,compiled,manifest=minimal_fixture(tmp)
            with patch.object(verifier,"validate_original",return_value=(
                    original,original.read_bytes(),"pygame/base.cp313-win_amd64.pyd")):
                for name,val in (
                    ("original_source_revision","f"*40),
                    ("patched_base_c_sha256","a"*64),
                    ("expected_modified_native_method","unmodified"),
                    ("expected_modified_native_result","fake"),
                    ("not_official_unmodified_pygame_wheel",False),
                    ("full_lgpl_compliance_approved",True),
                    ("stable_3_1_release_approved",True),
                    ("original_base_c_sha256",builder.PINNED_CHANGED_C_SHA256),
                ):
                    with self.subTest(name=name),self.assertRaises(ValueError):
                        verifier.stage(bundle,installer,{}, {},wheel,
                            dict(manifest,**{name:val}),compiled,Path(tmp)/"copied")
                with self.assertRaises(ValueError):
                    verifier.stage(bundle,installer,{}, {},wheel,
                                   manifest,compiled,bundle)
                compiled.write_bytes(original.read_bytes())
                with self.assertRaises(ValueError):
                    verifier.stage(bundle,installer,{}, {},wheel,
                                   manifest,compiled,Path(tmp)/"copied")

    def test_archive_pins_and_rejects_unsafe_member(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=root/builder.SDL_ARCHIVE_NAME
            with zipfile.ZipFile(archive,"w") as z:
                for i in range(34):
                    z.writestr(f"{builder.SDL_ARCHIVE_ROOT}/include/SDL_fixture_{i}.h",
                               b"#define A 1\n")
                z.writestr(f"{builder.SDL_ARCHIVE_ROOT}/include/SDL.h",b"header")
                z.writestr(f"{builder.SDL_ARCHIVE_ROOT}/lib/x64/SDL2.lib",b"import")
                z.writestr(f"{builder.SDL_ARCHIVE_ROOT}/docs/test_padding.dat",b"x"*120_000)
            with patch.object(builder,"SDL_ARCHIVE_SHA1",
                    hashlib.sha1(archive.read_bytes()).hexdigest()):
                include,lib=builder.unpack_pinned_sdl(archive,root/"extract")
                self.assertTrue((include/"SDL.h").is_file())
                self.assertTrue((lib/"SDL2.lib").is_file())
            with zipfile.ZipFile(archive,"a") as z:
                z.writestr(f"{builder.SDL_ARCHIVE_ROOT}/../evil",b"evil")
            with patch.object(builder,"SDL_ARCHIVE_SHA1",
                    hashlib.sha1(archive.read_bytes()).hexdigest()):
                with self.assertRaises(ValueError):
                    builder.unpack_pinned_sdl(archive,root/"reject")
            self.assertFalse((root/"evil").exists())


if __name__=="__main__":
    unittest.main()
