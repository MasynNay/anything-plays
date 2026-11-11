"""Safety and evidence guards on disposable Linux/Windows pygame extension swap."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import zipfile

from tools import probe_v31_linux_windows_pygame_replacement as p


def setup(root, target):
    root = Path(root)
    bundle = root / "frozen"
    library = ("base.cpython-313-x86_64-linux-gnu.so"
               if target == "linux-x64" else "base.cp313-win_amd64.pyd")
    relative = "_internal/pygame/" + library
    native = bundle / relative
    native.parent.mkdir(parents=True)
    native.write_bytes(b"synthetic original native bytes" * 50)
    (bundle / ("AnythingPlays.exe" if target == "windows-x64" else "AnythingPlays")).write_bytes(b"app")
    name = p.TARGETS[target][1]
    installer = root / name
    installer.write_bytes(b"synthetic installer receipt fixture")
    receipt = {
        "target": target, "status": p.TARGETS[target][0],
        "source_preview_revision": p.RC_APP_COMMIT,
        "installer": name, "sha256": p.digest(installer),
        "native_core_count": 11, "console_profiles": 18,
        "public_release_approved": False, "final_release_approved": False,
    }
    entries = [{"path": relative, "sha256": p.digest(native)}]
    entries.extend({"path": f"_internal/pygame/libSDL{i}.{p.PLATFORMS[target][1:]}",
                    "sha256": "a"*64} for i in range(p.COUNTS[target]-1))
    audit = {
        "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
        "target": target, "pygame_version": "2.5.8",
        "pygame_distribution": "pygame-ce",
        "redistribution_approved": False,
        "lgpl_relinking_reviewed": False,
        "native_candidates": entries,
    }
    wheel = root / p.WHEELS[target][0]
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr("pygame/"+library, native.read_bytes())
        z.writestr("padding", b"\0" * 1_001_000)
    return bundle, installer, receipt, audit, wheel, relative


class LinuxWindowsLibraryReplacementContracts(unittest.TestCase):
    def test_original_upstream_extension_swap_on_each_os_only_in_disposable_copy(self):
        for target in p.PLATFORMS:
            with self.subTest(target=target), TemporaryDirectory() as root:
                bundle, installer, receipt, audit, wheel, rel = setup(root, target)
                original_sha = p.digest(bundle/rel)
                with patch.dict(p.WHEELS, {target: (
                        wheel.name, p.digest(wheel))}):
                    report=p.stage(bundle, installer, receipt, audit, wheel,
                                   target, Path(root)/"copy")
                self.assertTrue(report["original_installed_native_unchanged"])
                self.assertEqual(report["upstream_wheel_member"],"pygame/"+Path(rel).name)
                self.assertFalse(report["extension_bytes_differ_from_original"])
                self.assertEqual(p.digest(bundle/rel), original_sha)
                self.assertEqual(p.digest(Path(root)/"copy"/rel), original_sha)
                for flag in ("copied_frozen_app_gui_started",
                             "user_compiled_modified_library_tested",
                             "full_lgpl_2_1_section_6_compliance_approved",
                             "corresponding_source_complete",
                             "stable_3_1_release_approved"):
                    self.assertFalse(report[flag],flag)

    def test_wrong_signed_receipts_and_dependency_evidence_rejected(self):
        with TemporaryDirectory() as root:
            target="linux-x64"
            bundle, installer, receipt, audit, wheel, rel=setup(root,target)
            with patch.dict(p.WHEELS, {target:(wheel.name,p.digest(wheel))}):
                for field,bad in (("source_preview_revision","0"*40),
                                  ("sha256","f"*64),
                                  ("public_release_approved",True),
                                  ("native_core_count",10)):
                    with self.subTest(field=field),self.assertRaises(ValueError):
                        p.stage(bundle,installer,dict(receipt,**{field:bad}),audit,wheel,
                                target,Path(root)/"copy")
                with self.assertRaises(ValueError):
                    p.stage(bundle,installer,receipt,
                            dict(audit,redistribution_approved=True),wheel,target,
                            Path(root)/"copy")
                with self.assertRaises(ValueError):
                    p.stage(bundle,installer,receipt,
                            dict(audit,native_candidates=[{"path":"../../escape",
                                                           "sha256":"f"*64}]+audit["native_candidates"][1:]),
                            wheel,target,Path(root)/"copy")
                with self.assertRaises(ValueError):
                    p.stage(bundle,installer,receipt,audit,wheel,target,bundle)
                (bundle/rel).write_bytes(b"corrupted binary")
                with self.assertRaises(ValueError):
                    p.stage(bundle,installer,receipt,audit,wheel,target,Path(root)/"copy")

    def test_tampered_donor_and_missing_member_cannot_pass(self):
        with TemporaryDirectory() as root:
            target="windows-x64"
            bundle,installer,receipt,audit,wheel,rel=setup(root,target)
            with self.assertRaises(ValueError):
                p.stage(bundle,installer,receipt,audit,wheel,target,Path(root)/"copy")
            with zipfile.ZipFile(wheel,"w") as z:
                z.writestr("pygame/wrong.pyd",b"1"*100)
                z.writestr("padding",b"\0"*1_001_000)
            with patch.dict(p.WHEELS,{target:(wheel.name,p.digest(wheel))}):
                with self.assertRaises(ValueError):
                    p.stage(bundle,installer,receipt,audit,wheel,target,Path(root)/"copy")


if __name__ == "__main__":
    unittest.main()
