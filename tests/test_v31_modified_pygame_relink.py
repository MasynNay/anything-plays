"""Reject bogus pygame-ce source modifications and unsafe RC1 native swaps."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

from tools import build_v31_modified_pygame_probe as build
from tools import verify_v31_modified_pygame_linux as replace
from tools import probe_v31_linux_windows_pygame_replacement as native
from tools.prepare_v31_sdl_source_review import WHEELS


def fake_clone(root):
    root=Path(root)
    src=root/"src_c/base.c"
    src.parent.mkdir(parents=True)
    src.write_text(
        "#include \"base.h\"\n"
        +build.C_ANCHOR+"\n"
        +build.METHOD_ANCHOR+"\n", "utf-8")
    lic=root/"docs/LGPL.txt"
    lic.parent.mkdir(parents=True)
    lic.write_bytes(b"synthetic LGPL fixture")
    return src,lic


def fake_pinned_git(command, **kwargs):
    return SimpleNamespace(stdout=build.PYGAME_COMMIT+"\n",returncode=0)


def fixture(root):
    root=Path(root)
    bundle=root/"actual-frozen"
    lib=bundle/"_internal/pygame/base.cpython-313-x86_64-linux-gnu.so"
    lib.parent.mkdir(parents=True)
    lib.write_bytes(b"original official native" * 70)
    (bundle/"AnythingPlays").write_bytes(b"frozen desktop fixture")
    filename="anything-plays-31-rc1_3.1.0~rc1full_amd64.deb"
    installer=root/filename
    installer.write_bytes(b"immutable original installer fake bytes")
    receipt={
        "target":"linux-x64",
        "status":native.TARGETS["linux-x64"][0],
        "source_preview_revision":replace.RC_APP_COMMIT,
        "installer":filename,
        "sha256":native.digest(installer),
        "native_core_count":11,
        "console_profiles":18,
        "public_release_approved":False,
        "final_release_approved":False,
    }
    audit={
        "target":"linux-x64",
        "status":"UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
        "pygame_version":"2.5.8",
        "pygame_distribution":"pygame-ce",
        "redistribution_approved":False,
        "lgpl_relinking_reviewed":False,
        "native_candidates":[{"path":"_internal/pygame/base.cpython-313-x86_64-linux-gnu.so",
                               "sha256":native.digest(lib)}],
    }
    for index in range(native.COUNTS["linux-x64"]-1):
        audit["native_candidates"].append({
            "path":f"_internal/pygame/libSDL{index}.so",
            "sha256":"a"*64,
        })
    wheel=root/WHEELS["linux-x64"][0]
    with zipfile.ZipFile(wheel,"w") as z:
        z.writestr("pygame/base.cpython-313-x86_64-linux-gnu.so",lib.read_bytes())
        z.writestr("padding",b"\0"*1_001_000)
    modified=root/"base.cpython-313-x86_64-linux-gnu.so"
    modified.write_bytes(b"compiled genuinely modified native" * 6000)
    manifest={
        "original_source_revision":build.PYGAME_COMMIT,
        "original_base_c_sha256":"a"*64,
        "patched_base_c_sha256":"b"*64,
        "expected_modified_native_method":"_ap31_relink_probe",
        "expected_modified_native_result":build.PROBE_VALUE,
        "full_lgpl_compliance_approved":False,
        "stable_3_1_release_approved":False,
        "not_official_unmodified_pygame_wheel":True,
    }
    return bundle,installer,receipt,audit,wheel,modified,manifest


class ActualSourceModifiedNativeContracts(unittest.TestCase):
    def test_source_patch_inserts_genuine_callable_c_method_only_once(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            src,lic=fake_clone(root)
            with patch.object(build,"TAG_LGPL_SHA256",hashlib.sha256(lic.read_bytes()).hexdigest()):
                out=build.patch_source(root,runner=fake_pinned_git)
            changed=src.read_text()
            self.assertIn("PyUnicode_FromString",changed)
            self.assertEqual(changed.count("_ap31_relink_probe"),3)
            self.assertNotEqual(out["original_base_c_sha256"],out["patched_base_c_sha256"])
            self.assertFalse(out["full_lgpl_compliance_approved"])
            self.assertFalse(out["stable_3_1_release_approved"])
            with patch.object(build,"TAG_LGPL_SHA256",hashlib.sha256(lic.read_bytes()).hexdigest()),self.assertRaises(ValueError):
                build.patch_source(root,runner=fake_pinned_git)

    def test_source_patch_rejects_forged_git_and_license(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            fake_clone(root)
            with self.assertRaises(ValueError):
                build.patch_source(root,runner=lambda *a,**kw:SimpleNamespace(stdout="0"*40,returncode=0))
            with self.assertRaises(ValueError):
                build.patch_source(root,runner=fake_pinned_git)

    def test_source_compiled_native_must_differ_from_original_wheel_and_never_touch_original(self):
        with TemporaryDirectory() as tmp:
            args=fixture(tmp)
            bundle,installer,receipt,audit,wheel,modified,manifest=args
            original=native.digest(bundle/"_internal/pygame/base.cpython-313-x86_64-linux-gnu.so")
            with patch.dict(native.WHEELS,{"linux-x64":(wheel.name,native.digest(wheel))}):
                output=replace.stage(*args,Path(tmp)/"copied-frozen")
            self.assertTrue(output["compiled_binary_is_not_original_wheel_binary"])
            self.assertTrue(output["original_installer_untouched"])
            self.assertNotEqual(output["compiled_modified_native_sha256"],original)
            self.assertEqual(native.digest(bundle/"_internal/pygame/base.cpython-313-x86_64-linux-gnu.so"),original)
            for flag in ("source_modified_method_observed_by_native_python",
                         "real_frozen_app_gui_boot_after_source_swap",
                         "full_lgpl_2_1_relinking_approved",
                         "stable_3_1_release_approved"):
                self.assertFalse(output[flag],flag)

    def test_tampered_source_manifest_binaries_and_existing_destination_fail_closed(self):
        with TemporaryDirectory() as tmp:
            bundle,installer,receipt,audit,wheel,modified,manifest=fixture(tmp)
            target=Path(tmp)/"copied-frozen"
            with patch.dict(native.WHEELS,{"linux-x64":(wheel.name,native.digest(wheel))}):
                for field,val in (("original_source_revision","f"*40),
                                  ("full_lgpl_compliance_approved",True),
                                  ("original_base_c_sha256","b"*64),
                                  ("expected_modified_native_result","fake")):
                    with self.subTest(field=field),self.assertRaises(ValueError):
                        replace.stage(bundle,installer,receipt,audit,wheel,
                                      dict(manifest,**{field:val}),modified,target)
                with self.assertRaises(ValueError):
                    replace.stage(bundle,installer,receipt,audit,wheel,manifest,modified,bundle)
                with self.assertRaises(ValueError):
                    replace.stage(bundle,installer,receipt,audit,wheel,manifest,
                                  bundle/"_internal/pygame/base.cpython-313-x86_64-linux-gnu.so",
                                  target)
                receipt["public_release_approved"]=True
                with self.assertRaises(ValueError):
                    replace.stage(bundle,installer,receipt,audit,wheel,manifest,modified,target)


if __name__=="__main__":
    unittest.main()
