"""Mac LGPL C-source modified native must not mutate signed original or overstate rights."""
import hashlib
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tools import verify_v31_modified_pygame_macos as mac
from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT,PROBE_VALUE


def macho(code, arch="arm64"):
    cpu={"arm64":0x0100000c,"x86_64":0x01000007}[arch]
    start=32+72+80
    return (struct.pack("<IIIIIIII",0xfeedfacf,cpu,0,6,1,152,0,0)
            +struct.pack("<II16sQQQQiiII",0x19,152,b"__TEXT",0,start+len(code),0,start+len(code),7,5,1,0)
            +struct.pack("<16s16sQQIIIIIIII",b"__text",b"__TEXT",start,len(code),start,0,0,0,0,0,0,0)
            +code)


def fixture(root, target):
    root=Path(root)
    app=root/"original.app"
    native=app/mac.FROZEN_PATH
    native.parent.mkdir(parents=True)
    arch=mac.ARCHES[target]
    original=macho(b"\x91"*100_000,arch)
    changed=macho(b"\x92"*100_000,arch)
    native.write_bytes(original)
    compiled=root/"base.cpython-313-darwin.so"
    compiled.write_bytes(changed)
    source_receipt={
        "original_source_revision":PYGAME_COMMIT,
        "expected_modified_native_method":"_ap31_relink_probe",
        "expected_modified_native_result":PROBE_VALUE,
        "original_base_c_sha256":"a"*64,
        "patched_base_c_sha256":"b"*64,
        "not_official_unmodified_pygame_wheel":True,
        "full_lgpl_compliance_approved":False,
        "stable_3_1_release_approved":False,
    }
    return app,native,compiled,source_receipt


class SourceModifiedMacContracts(unittest.TestCase):
    def test_both_macs_copy_real_code_change_and_remain_unapproved(self):
        for target in mac.ARCHES:
            with self.subTest(target=target),TemporaryDirectory() as td:
                app,original,compiled,source_receipt=fixture(td,target)
                before=mac.sha(original)
                with patch.object(mac,"validate_inputs",return_value=(
                        original,original.read_bytes(),{"sha256":before})):
                    r=mac.stage(app,Path(td)/"installer.dmg",{}, {},Path(td)/"wheel",
                                compiled,source_receipt,target,Path(td)/"copy.app")
                self.assertTrue(r["source_modified_c_binary_verified_different"])
                self.assertTrue(r["unmodified_original_mac_rc1_verified"])
                self.assertEqual(mac.sha(original),before)
                self.assertEqual(mac.sha(Path(td)/"copy.app"/mac.FROZEN_PATH),mac.sha(compiled))
                for field in ("actual_modified_method_invoked","copied_app_ad_hoc_codesign_verified",
                              "copied_original_frozen_rc1_tk_boot_verified",
                              "complete_lgpl_section_6_source_and_relinking_approved",
                              "stable_3_1_release_approved"):
                    self.assertFalse(r[field],field)

    def test_tamper_modified_source_and_destinations_refused(self):
        with TemporaryDirectory() as td:
            target="macos-arm64"
            app,original,compiled,manifest=fixture(td,target)
            with patch.object(mac,"validate_inputs",return_value=(
                    original,original.read_bytes(),{})):
                for key,value in (("original_source_revision","0"*40),
                                  ("expected_modified_c_method","false"),
                                  ("not_official_unmodified_pygame_wheel",False),
                                  ("full_lgpl_compliance_approved",True),
                                  ("stable_3_1_release_approved",True),
                                  ("patched_base_c_sha256","a"*64)):
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        bad=dict(manifest,**{key:value})
                        if key=="expected_modified_c_method":
                            bad["expected_modified_native_method"]="fake"
                        mac.stage(app,Path(td)/"dmg",{}, {},Path(td)/"wheel",
                                  compiled,bad,target,Path(td)/"copied")
                with self.assertRaises(ValueError):
                    mac.stage(app,Path(td)/"dmg",{}, {},Path(td)/"wheel",
                              compiled,manifest,target,app)
                compiled.write_bytes(original.read_bytes())
                with self.assertRaises(ValueError):
                    mac.stage(app,Path(td)/"dmg",{}, {},Path(td)/"wheel",
                              compiled,manifest,target,Path(td)/"copied")


if __name__=="__main__":
    unittest.main()
