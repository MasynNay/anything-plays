"""Native SDL loader probe strictly checks installed Mac bytes and versions."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from tools.probe_v31_macos_sdl_load import (
    SOURCE_COMMIT, probe, select_libs, run_load_order,
)


def setup_fixture(d, arch):
    app=Path(d)/"AnythingPlays31RC.app"
    files=[]
    names=(("cv2","3201.8.0") if arch=="macos-arm64" else (), ("pygame","3201.10.0"))
    pairs=[("pygame","3201.10.0")]
    if arch=="macos-arm64":
        pairs.insert(0,("cv2","3201.8.0"))
    for slot,version in pairs:
        path=f"Contents/Frameworks/{slot}/__dot__dylibs/libSDL2-2.0.0.dylib"
        data=(slot+version).encode()
        f=app/path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        files.append({
            "path":path,
            "sha256":hashlib.sha256(data).hexdigest(),
            "otool_dependencies":[{"current_version":version}],
        })
    files += [{"path":f"Contents/Frameworks/libdummy{i}.dylib"} for i in range(120)]
    info={
        "target":arch,
        "status":"UNRELEASED_3_1_MACOS_NATIVE_LINKAGE_REVIEW",
        "source_app_commit":SOURCE_COMMIT,
        "redistribution_approved":False,
        "native_files":files,
    }
    return app,info


def successful_subprocess(cmd,**_):
    paths=cmd[3:]
    output=[{"path":x, "runtime_version":"2.32.8" if "/cv2/" in x
             else "2.32.10",
             "joystick_controller_initialized":True,
             "enumerated_joystick_count":0} for x in paths]
    return SimpleNamespace(returncode=0,stdout=json.dumps(output),stderr="")


class ActualSDLLoadContracts(unittest.TestCase):
    def test_source_signed_audit_and_macho_versions_are_required(self):
        with TemporaryDirectory() as d:
            app,source=setup_fixture(d,"macos-arm64")
            res=select_libs(app,source,"macos-arm64")
            self.assertEqual(set(res),{"pygame","cv2"})
            self.assertEqual(res["cv2"]["expected_runtime_version"],"2.32.8")
            self.assertEqual(res["pygame"]["expected_runtime_version"],"2.32.10")
            copied=dict(source,source_app_commit="0"*40)
            with self.assertRaises(ValueError):
                select_libs(app,copied,"macos-arm64")
            copied=dict(source,redistribution_approved=True)
            with self.assertRaises(ValueError):
                select_libs(app,copied,"macos-arm64")

    def test_both_load_orders_must_return_their_own_actual_versions(self):
        with TemporaryDirectory() as d:
            app,source=setup_fixture(d,"macos-arm64")
            result=probe(app,source,"macos-arm64",runner=successful_subprocess)
            self.assertEqual(len(result["load_orders"]),2)
            self.assertTrue(result["all_native_load_orders_passed"])
            self.assertTrue(result["hardware_free_joystick_and_controller_subsystems_exercised"])
            self.assertFalse(result["real_camera_controller_coexistence_tested"])
            self.assertFalse(result["redistribution_approved"])

    def test_mismatched_same_install_name_cannot_report_success(self):
        with TemporaryDirectory() as d:
            app,source=setup_fixture(d,"macos-arm64")
            def coalesced(cmd,**kw):
                records=[{"path":p,"runtime_version":"2.32.8",
                          "joystick_controller_initialized":True,
                          "enumerated_joystick_count":0} for p in cmd[3:]]
                return SimpleNamespace(returncode=0,stdout=json.dumps(records),stderr="")
            result=probe(app,source,"macos-arm64",runner=coalesced)
            self.assertFalse(result["all_native_load_orders_passed"])

    def test_failure_or_tampering_keeps_probe_unverified(self):
        with TemporaryDirectory() as d:
            app,source=setup_fixture(d,"macos-x64")
            def failed(*args,**kw):
                return SimpleNamespace(returncode=3,stdout="",stderr="dyld missing")
            result=probe(app,source,"macos-x64",runner=failed)
            self.assertFalse(result["all_native_load_orders_passed"])
            bad=app/"Contents/Frameworks/pygame/__dot__dylibs/libSDL2-2.0.0.dylib"
            bad.write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                select_libs(app,source,"macos-x64")

    def test_workflow_only_reads_exact_signed_qa(self):
        workflow=(Path(__file__).resolve().parents[1] /
                  ".github/workflows/v31-rc1-macos-dyld-load-probe.yml").read_text("utf-8")
        self.assertIn("42906227613",workflow)
        self.assertIn("42905694504",workflow)
        self.assertIn("actions/upload-artifact@v4",workflow)
        self.assertNotIn("contents: write",workflow)
        self.assertNotIn("gh release create",workflow)


if __name__ == "__main__":
    unittest.main()
