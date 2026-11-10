"""Native Mac virtual controller probe must reject false/hardware acceptance."""
from pathlib import Path
from types import SimpleNamespace
import json
import unittest
from unittest.mock import patch

from tools.probe_v31_macos_virtual_joystick import (
    evaluate_results, probe, _NATIVE_PROBE,
)


def data(slots=("cv2","pygame")):
    return {slot: {"path":"/signed/"+slot+".dylib",
                   "expected_runtime_version":"2.32.8" if slot=="cv2"
                   else "2.32.10","audited_sha256":"a"*64} for slot in slots}


def response(order, *, pressed=1, released=0):
    return [
        {"path":"/signed/"+slot+".dylib",
         "runtime_version":"2.32.8" if slot=="cv2" else "2.32.10",
         "virtual_joystick_added":True,
         "native_button_press_read":pressed,
         "native_button_release_read":released,
         "virtual_joystick_removed":True,
         "real_hid_hardware_tested":False}
        for slot in order
    ]


class SignedVirtualJoystickTests(unittest.TestCase):
    def test_both_sdl_versions_and_reverse_order_must_observe_native_buttons(self):
        report=evaluate_results("macos-arm64",data(),lambda order:response(order))
        self.assertTrue(report["passed"])
        self.assertEqual([x["load_order"] for x in report["native_button_roundtrips"]],
                         [["cv2","pygame"],["pygame","cv2"]])
        self.assertFalse(report["physical_gamepad_verified"])
        self.assertFalse(report["redistribution_approved"])
        self.assertFalse(report["corresponding_source_complete"])

    def test_intel_only_tries_one_signed_library(self):
        report=evaluate_results("macos-x64",data(("pygame",)),
                                lambda order:response(order))
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["native_button_roundtrips"]),1)

    def test_reject_stuck_button_mismatched_version_and_fake_hid_acceptance(self):
        slots=data()
        cases=[
            lambda rows: rows[0].update(native_button_press_read=0),
            lambda rows: rows[0].update(native_button_release_read=1),
            lambda rows: rows[0].update(runtime_version="2.0.0"),
            lambda rows: rows[0].update(virtual_joystick_removed=False),
            lambda rows: rows[0].update(real_hid_hardware_tested=True),
            lambda rows: rows[0].update(path="/different-lib.dylib"),
        ]
        for tamper in cases:
            with self.subTest(tamper=tamper):
                def fake(order):
                    rows=response(order)
                    tamper(rows)
                    return rows
                self.assertFalse(evaluate_results("macos-arm64",slots,fake)["passed"])
        self.assertFalse(evaluate_results("macos-arm64",slots,lambda _order:[])["passed"])

    def test_native_code_uses_real_sdl_attach_press_release_detach(self):
        for symbol in ("SDL_JoystickAttachVirtual","SDL_JoystickIsVirtual",
                       "SDL_JoystickSetVirtualButton","SDL_JoystickGetButton",
                       "SDL_JoystickDetachVirtual","SDL_JoystickUpdate"):
            self.assertIn(symbol,_NATIVE_PROBE)
        self.assertIn("SDL_INIT",_NATIVE_PROBE) if "SDL_INIT" in _NATIVE_PROBE else self.assertIn("0x00000200",_NATIVE_PROBE)

    def test_process_error_or_bad_json_marks_report_failed(self):
        with patch("tools.probe_v31_macos_virtual_joystick.select_libs",
                   return_value=data(("pygame",))):
            def runner(cmd,**_):
                return SimpleNamespace(returncode=3,stdout="",stderr="probe refused")
            report=probe("unused",{},"macos-x64",runner=runner)
            self.assertFalse(report["passed"])
            def garbage(cmd,**_):
                return SimpleNamespace(returncode=0,stdout="not-json",stderr="")
            report=probe("unused",{},"macos-x64",runner=garbage)
            self.assertFalse(report["passed"])

    def test_workflow_does_not_publish_and_pins_refreshed_qa(self):
        path=Path(__file__).resolve().parents[1] / ".github/workflows/v31-rc1-macos-virtual-joystick.yml"
        flow=path.read_text("utf-8")
        self.assertIn("42886791394",flow)
        self.assertIn("42888996877",flow)
        self.assertIn("actions/upload-artifact@v4",flow)
        self.assertNotIn("contents: write",flow)
        self.assertNotIn("gh release create",flow)


if __name__=="__main__":
    unittest.main()
