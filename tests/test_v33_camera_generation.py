"""3.3 camera input generation and classic pulse safety regressions.

All tests use synthetic controls; no native cores, webcam, or private paths.
"""
import threading
import unittest
from unittest.mock import patch

from anything_plays.gba_emulator import Emulator
from anything_plays.libretro_input import IDS, InputBuffer


class CameraGenerationSafetyTests(unittest.TestCase):
    @staticmethod
    def emulator():
        # Avoid any real core discovery or native ROM initialization.
        emulator = object.__new__(Emulator)
        emulator.inputs = InputBuffer()
        emulator.running = True
        emulator.armed = True
        return emulator

    def test_stop_invalidates_prior_held_buttons_and_both_pulse_ports(self):
        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=lambda: 2.0)
        original = inputs.camera_generation()
        inputs.set_camera_buttons(("A",), ("B",), generation=original)
        inputs.queue_press("X", 4, port=0, generation=original)
        inputs.queue_press("Y", 4, port=1, generation=original)
        inputs.disarm()
        # Simulate a delayed camera frame that finished tracking before Stop.
        inputs.set_camera_buttons(("A",), ("B",), generation=original)
        inputs.queue_press("X", 4, port=0, generation=original)
        inputs.queue_press("Y", 4, port=1, generation=original)
        self.assertTrue(inputs.commands.empty())
        report = inputs.latency_snapshot()
        self.assertEqual(report["late_camera_updates_dropped"], 3)
        from anything_plays.ui_setup_diagnostics import _input_timing_summary_lines
        notices = _input_timing_summary_lines(report)
        self.assertTrue(any("Rejected 3 late camera updates" in line for line in notices))
        inputs.before_frame(True)
        for port, name in ((0, "A"), (1, "B"), (0, "X"), (1, "Y")):
            self.assertEqual(inputs.state(port, 1, 0, IDS[name]), 0)
        fresh = inputs.camera_generation()
        self.assertGreater(fresh, original)
        inputs.set_camera_buttons(("A",), ("B",), generation=fresh)
        inputs.before_frame(True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)

    def test_stop_during_facade_handoff_cannot_restore_old_controls(self):
        for kind in ("held", "pulse"):
            with self.subTest(kind=kind):
                emu = self.emulator()
                if kind == "held":
                    original = emu.inputs.set_camera_buttons
                    def late(*args, **kwargs):
                        emu.disarm()
                        original(*args, **kwargs)
                    with patch.object(emu.inputs, "set_camera_buttons", side_effect=late):
                        emu.set_camera_buttons(("A",), ("B",))
                else:
                    original = emu.inputs.queue_press
                    def late(*args, **kwargs):
                        emu.disarm()
                        original(*args, **kwargs)
                    with patch.object(emu.inputs, "queue_press", side_effect=late):
                        emu.press("A", frames=4, port=1)
                emu.inputs.before_frame(True)
                self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 0)
                self.assertEqual(emu.inputs.state(1, 1, 0, IDS["B"]), 0)
                self.assertEqual(emu.inputs.state(1, 1, 0, IDS["A"]), 0)
                self.assertTrue(emu.inputs.commands.empty())

    def test_disarm_while_camera_builds_snapshot_drops_expired_result(self):
        inputs = InputBuffer()
        token = inputs.camera_generation()
        started = threading.Event()
        resume = threading.Event()
        original = inputs.id_for
        failures = []
        def gated(button):
            started.set()
            if not resume.wait(3):
                raise AssertionError("camera test barrier did not resume")
            return original(button)
        def produce():
            try:
                inputs.set_camera_buttons(("A",), ("B",), generation=token)
            except Exception as exc:
                failures.append(type(exc).__name__)
        with patch.object(inputs, "id_for", side_effect=gated):
            worker = threading.Thread(target=produce)
            worker.start()
            try:
                self.assertTrue(started.wait(3))
                inputs.disarm()
            finally:
                resume.set()
                worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(inputs._camera_held, {0: set(), 1: set()})

    def test_invalid_classic_pulse_settings_do_not_break_manual_controls(self):
        inputs = InputBuffer()
        inputs.set_manual("B", True)
        for frames in (None, [], {}, object(), True, float("nan"),
                       float("inf"), float("-inf"), "bad", "1e9999"):
            with self.subTest(frames_type=type(frames).__name__):
                inputs.queue_press("A", frames)
        for port in (None, True, False, 2, -1, "1"):
            inputs.queue_press("A", 3, port=port)
        for label in (None, [], {}, "not-a-retropad-key"):
            inputs.queue_press(label, 3)
        self.assertTrue(inputs.commands.empty())
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 1)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)
        inputs.queue_press("A", "3")
        inputs.queue_press("B", 999, port=1)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.remaining[IDS["A"]], 3)
        self.assertEqual(inputs.remaining_p2[IDS["B"]], 60)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)
        inputs.disarm()
        inputs.before_frame(armed=False)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 1)



class CameraFrameBoundaryTests(unittest.TestCase):
    """A frame begun before Stop must not control the next ROM session."""

    @staticmethod
    def build_scene(mode):
        import numpy as np
        from unittest.mock import Mock
        from anything_plays.ui_camera import CameraMixin

        class V:
            def __init__(self, value):
                self.value = value
            def get(self):
                return self.value
            def set(self, value):
                self.value = value

        app = CameraMixin()
        emu = object.__new__(Emulator)
        emu.inputs = InputBuffer()
        emu.inputs.system = "snes"
        emu.running = True
        emu.armed = True
        emu.inputs.enable_latency_probe(clock=lambda: 1.0)
        app.emu = emu
        app.armed = True
        app.external_input = None
        app.frame = np.zeros((128, 192, 3), dtype=np.uint8)
        app.tolerance = V(18)
        app.min_area = V(55)
        app.multi_fish_enabled = V(False)
        app.color2_enabled = V(True)
        app.color2_player = V("Player 2")
        app.camera_input_mode = V(mode)
        app.shuffle_enabled = V(False)
        app.system_key = V("snes")
        app.hold_frames = V(4)
        app.cooldown = V(100)
        app.mapping_vars = {"PrimaryZone": V("A"), "SecondaryZone": V("B")}
        app.cfg = {
            "rgb": [50, 250, 90], "rgb2": [240, 50, 190],
            "zones": {
                "PrimaryZone": [0, 0, 0.5, 1],
                "SecondaryZone": [0.5, 0, 1, 1],
            },
        }
        app._last_camera_pulses = {}
        app._shuffle_latched = False
        app.action = V("")
        app.render_zones = lambda frame, active: frame
        app.geometry = lambda: None
        app._stream_output_window = None
        app.camera_photo = None
        return app

    def test_slow_tracking_from_old_game_never_updates_restarted_game(self):
        import numpy as np
        from unittest.mock import patch

        for mode in ("Held while visible", "Pulse (classic)"):
            with self.subTest(mode=mode):
                app = self.build_scene(mode)
                contour = np.array([[[1, 1]], [[2, 1]], [[2, 2]]], dtype=np.int32)
                primary = [((45, 60), contour)]
                secondary = [((145, 60), contour)]
                calls = [0]
                def locate(*args, **kwargs):
                    calls[0] += 1
                    if calls[0] == 1:
                        # Stop and rapid rearm while an earlier image is still
                        # being analyzed by OpenCV. Original image must lose.
                        app.emu.disarm()
                        app.emu.running = True
                        app.emu.armed = True
                    return primary if calls[0] % 2 else secondary
                def zone(center, *args):
                    return "PrimaryZone" if center[0] < 100 else "SecondaryZone"
                with patch("anything_plays.ui_camera.locate_targets",
                           side_effect=locate), patch(
                    "anything_plays.ui_camera.zone_at", side_effect=zone
                ):
                    app.draw_camera()
                    app.emu.inputs.before_frame(True)
                    self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["A"]), 0)
                    self.assertEqual(app.emu.inputs.state(1, 1, 0, IDS["B"]), 0)
                    self.assertEqual(app.emu.inputs.commands.qsize(), 0)
                    self.assertNotIn((0, "A"), app._last_camera_pulses)
                    self.assertNotIn((1, "B"), app._last_camera_pulses)
                    self.assertGreaterEqual(
                        app.emu.inputs.latency_snapshot()[
                            "late_camera_updates_dropped"
                        ], 1
                    )
                    # A fresh real frame from the new session must work,
                    # including classic pulses after a rejected old frame.
                    app.draw_camera()
                    app.emu.inputs.before_frame(True)
                    self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["A"]), 1)
                    self.assertEqual(app.emu.inputs.state(1, 1, 0, IDS["B"]), 1)

    def test_legacy_frame_adapter_receives_no_new_keyword_args(self):
        from unittest.mock import Mock, patch
        app = self.build_scene("Held while visible")
        adapter = Mock()
        adapter.inputs = object()
        app.emu = adapter
        with patch("anything_plays.ui_camera.locate_targets", return_value=[]):
            app.draw_camera()
        adapter.set_camera_buttons.assert_called_once_with(set(), set())


if __name__ == "__main__":
    unittest.main()
