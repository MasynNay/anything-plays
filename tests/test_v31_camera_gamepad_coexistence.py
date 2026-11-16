"""End-to-end virtual aquarium and SDL gamepad coexistence regression.

No physical cameras, gamepads, ROMs or native cores are used. Unlike pure
InputBuffer tests, real OpenCV color contours pass through CameraMixin's
actual draw_camera controller routing, GamepadReader's SDL API polling,
GamepadMixin's focus/disconnect policy, and native Libretro input callbacks.
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

import cv2
import numpy as np

from anything_plays.gamepad import GamepadReader
from anything_plays.libretro_input import InputBuffer, TWO_PLAYER_SYSTEMS
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_gamepad import GamepadMixin
from anything_plays.ui_gameplay import GameplayMixin


RGB_PRIMARY = (40, 230, 85)
RGB_SECONDARY = (235, 50, 190)
BGR_PRIMARY = RGB_PRIMARY[::-1]
BGR_SECONDARY = RGB_SECONDARY[::-1]


class Variable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class VirtualEvents:
    def __init__(self):
        self.pumps = 0
        self.drains = 0

    def pump(self):
        self.pumps += 1

    def get(self):
        self.drains += 1
        return []


class VirtualSubsystem:
    def init(self):
        pass

    def quit(self):
        pass


class VirtualPygame:
    def __init__(self):
        self.display = VirtualSubsystem()
        self.joystick = VirtualSubsystem()
        self.event = VirtualEvents()


class VirtualPhysicalPad:
    def __init__(self):
        self.buttons = set()
        self.axes = {}
        self.connected = True
        self.closed = False

    def attached(self):
        return self.connected and not self.closed

    def get_button(self, code):
        if not self.connected:
            raise OSError("Virtual gamepad unplugged")
        return code in self.buttons

    def get_axis(self, code):
        if not self.connected:
            raise OSError("Virtual gamepad unplugged")
        return self.axes.get(code, 0)

    def quit(self):
        self.closed = True


class VirtualSDL:
    def __init__(self, devices):
        self.devices = devices
        names = ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
                 "A", "B", "X", "Y", "BACK", "START",
                 "LEFTSHOULDER", "RIGHTSHOULDER")
        for name in names:
            setattr(self, "CONTROLLER_BUTTON_" + name, name)
        for name in ("LEFTX", "LEFTY", "RIGHTX", "RIGHTY",
                     "TRIGGERLEFT", "TRIGGERRIGHT"):
            setattr(self, "CONTROLLER_AXIS_" + name, name)

    def init(self):
        pass

    def quit(self):
        pass

    def get_count(self):
        return len(self.devices)

    def is_controller(self, index):
        return 0 <= index < len(self.devices)

    def Controller(self, index):
        return self.devices[index]

    def name_forindex(self, index):
        return "Virtual SDL controller"


class VirtualRoot:
    def __init__(self):
        self.focus = object()
        self.jobs = []

    def focus_get(self):
        return self.focus

    def after(self, delay, callback):
        self.jobs.append((delay, callback))
        return len(self.jobs)


class VirtualEmulator:
    def __init__(self, system="snes"):
        self.inputs = InputBuffer()
        self.inputs.system = system
        self.running = True
        self.armed = True

    def set_camera_buttons(self, p1=(), p2=(), *, sample_started_at=None):
        if self.running and self.armed:
            self.inputs.set_camera_buttons(
                p1, p2, sample_started_at=sample_started_at
            )

    def set_gamepad_buttons(self, buttons):
        self.inputs.set_gamepad_buttons(buttons)

    def release_gamepad(self):
        self.inputs.release_gamepad()

    def set_manual(self, button, held):
        self.inputs.set_manual(button, held)

    def release_manual(self):
        self.inputs.release_manual()

    def press(self, button, frames=8, port=0):
        if self.armed and self.running:
            self.inputs.queue_press(button, frames, port=port)

    def disarm(self):
        self.armed = False
        self.inputs.disarm()

    def frame(self):
        self.inputs.before_frame(self.armed)

    def held(self, button, port=0):
        identity = self.inputs.id_for(button)
        if identity is None:
            raise AssertionError("Unknown console button: " + str(button))
        # N64 and GameCube use distinct *internal identity* tuples
        # before_frame() translates into native (device,index,id) polls.
        # Query the actual Libretro callback arguments rather than passing
        # the tuple itself as a native id (which would always read zero).
        if isinstance(identity, tuple):
            if identity[0] not in ("joypad", "digital"):
                raise AssertionError("held() only checks digital buttons")
            return bool(self.inputs.state(port, 1, 0, identity[1]))
        return bool(self.inputs.state(port, 1, 0, identity))


class VirtualAquarium(CameraMixin, GamepadMixin, GameplayMixin):
    """Minimal Tk-like context, invoking the real camera and gamepad methods."""

    def __init__(self, reader, system="snes"):
        self._closing = False
        self.root = VirtualRoot()
        self.emu = VirtualEmulator(system)
        self.system_key = Variable(system)
        self._gamepad = reader
        self._gamepad_bindings = {}
        self.gamepad_enabled = Variable(True)
        self.gamepad_status = Variable("Controller enabled")
        self.gamepad_live_input = Variable("")
        self.action = Variable("")
        self.status = Variable("")
        self.armed = True
        self.external_input = None
        self.tolerance = Variable(18)
        self.min_area = Variable(55)
        self.multi_fish_enabled = Variable(False)
        self.color2_enabled = Variable(True)
        self.color2_player = Variable("Player 2")
        self.camera_input_mode = Variable("Held while visible")
        self.hold_frames = Variable(4)
        self.cooldown = Variable(100)
        self.shuffle_enabled = Variable(False)
        self._shuffle_latched = False
        self._last_camera_pulses = {}
        self.cfg = {
            "rgb": list(RGB_PRIMARY),
            "rgb2": list(RGB_SECONDARY),
            "zones": {
                "PrimaryZone": [0, 0, 0.5, 1.0],
                "SecondaryZone": [0.5, 0, 1.0, 1.0],
            },
        }
        self.mapping_vars = {
            "PrimaryZone": Variable("A"),
            "SecondaryZone": Variable("B"),
        }
        self.frame = None
        self.cap = None
        self.reference_image = False
        self.camera_photo = None
        self.refresh_controller_artwork = lambda: None
        self.save_preferences = lambda: None
        self.uses_embedded_emulator = lambda: True
        self.render_zones = lambda frame, active: frame
        self.geometry = lambda: None

    def set_pixels(self, *, primary=(), secondary=()):
        picture = np.zeros((128, 192, 3), dtype=np.uint8)
        for point in primary:
            cv2.circle(picture, point, 13, BGR_PRIMARY, -1)
        for point in secondary:
            cv2.circle(picture, point, 13, BGR_SECONDARY, -1)
        self.frame = picture

    def one_frame(self):
        self.draw_camera()
        self.gamepad_tick()
        self.emu.frame()


class PixelAndControllerCoexistenceTests(TestCase):
    def setUp(self):
        self.pad = VirtualPhysicalPad()
        self.devices = [self.pad]
        self.api = VirtualSDL(self.devices)
        self.pygame = VirtualPygame()
        self.reader = GamepadReader(
            clock=lambda: 100, loader=lambda: self.pygame
        )
        self.module_patch = patch(
            "anything_plays.gamepad.importlib.import_module",
            return_value=self.api,
        )
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.reader.start()
        self.addCleanup(self.reader.stop)
        self.app = VirtualAquarium(self.reader)

    def test_two_real_color_contours_plus_gamepad_and_keyboard_same_frame(self):
        app = self.app
        self.pad.buttons = {"B"}
        app.emu.set_manual("Start", True)
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A", 0), "primary camera object")
        self.assertTrue(app.emu.held("B", 0), "physical SDL controller")
        self.assertTrue(app.emu.held("Start", 0), "keyboard")
        self.assertTrue(app.emu.held("B", 1), "secondary camera object")
        self.assertFalse(app.emu.held("A", 1))
        self.assertIn("P2: B", app.action.get())

        app.set_pixels()
        app.one_frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))
        self.assertTrue(app.emu.held("B", 0))
        self.assertTrue(app.emu.held("Start", 0))

    def test_broken_optional_stream_rgb_cannot_block_native_button_release(self):
        """A native OBS converter crash must not affect P1/P2 held controls."""
        import time
        from types import MethodType
        from anything_plays.ui_stream import StreamMixin

        app = self.app
        app._stream_output_window = object()
        app._stream_options = {"frame_rate": "24 FPS"}
        app._stream_camera_last_snapshot = None
        app._stream_camera_frame = None
        app._stream_camera_serial = 0
        app._stream_last_render = ("before error",)
        app.stream_camera_snapshot = MethodType(
            StreamMixin.stream_camera_snapshot, app
        )
        app.stream_clear_camera = MethodType(
            StreamMixin.stream_clear_camera, app
        )
        app._invalidate_stream = MethodType(
            StreamMixin._invalidate_stream, app
        )
        original = cv2.cvtColor
        rgb_fails = [False]

        def convert(pixels, mode):
            if mode == cv2.COLOR_BGR2RGB and rgb_fails[0]:
                raise RuntimeError(
                    "private webcam /Users/private/usb-serial-123 failed"
                )
            return original(pixels, mode)

        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with (
            patch.object(time, "monotonic", side_effect=(10.0, 10.100)),
            patch.object(cv2, "cvtColor", side_effect=convert),
        ):
            app.draw_camera()
            app.emu.frame()
            self.assertTrue(app.emu.held("A", 0))
            self.assertTrue(app.emu.held("B", 1))
            self.assertIsNotNone(app._stream_camera_frame)
            self.assertEqual(app._stream_camera_serial, 1)

            rgb_fails[0] = True
            app.set_pixels()
            app.draw_camera()
            app.emu.frame()
        self.assertFalse(app.emu.held("A", 0),
                         "native P1 button must release on the next frame")
        self.assertFalse(app.emu.held("B", 1),
                         "native P2 button must release on the next frame")
        self.assertIsNone(app._stream_camera_frame,
                          "OBS may never retain a stale private camera image")
        self.assertIsNone(app._stream_last_render)
        self.assertEqual(app._stream_camera_serial, 2)
        self.assertEqual(app._stream_camera_last_snapshot, 10.100)

    def test_broken_stream_clock_never_blocks_both_player_input_releases(self):
        """P1/P2 native snapshots survive a failed optional OBS clock."""
        import time
        from types import MethodType
        from anything_plays.ui_stream import StreamMixin

        app = self.app
        app._stream_output_window = object()
        app._stream_options = {"frame_rate": "24 FPS"}
        app._stream_camera_last_snapshot = None
        app._stream_camera_frame = None
        app._stream_camera_serial = 0
        app._stream_last_render = None
        app.stream_camera_snapshot = MethodType(
            StreamMixin.stream_camera_snapshot, app
        )
        app.stream_clear_camera = MethodType(
            StreamMixin.stream_clear_camera, app
        )
        app._invalidate_stream = MethodType(
            StreamMixin._invalidate_stream, app
        )
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(time, "monotonic", return_value=10.0):
            app.draw_camera()
        app.emu.frame()
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))
        self.assertIsNotNone(app._stream_camera_frame)
        self.assertEqual(app._stream_camera_serial, 1)

        app.set_pixels()  # Both tracked objects disappeared.
        with patch.object(time, "monotonic", side_effect=OSError(
            "Native clock /Users/private/usb-camera-serial-007"
        )):
            app.draw_camera()
        app.emu.frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))
        self.assertIsNone(app._stream_camera_frame)
        self.assertEqual(app._stream_camera_serial, 2)
        self.assertEqual(app.emu.inputs.commands.qsize(), 0)
        self.assertIsNone(app._stream_camera_last_snapshot)

        # The next valid camera frame must rebuild the optional stream image
        # without reopening the webcam or needing new player permissions.
        with patch.object(time, "monotonic", return_value=10.1):
            app.draw_camera()
        self.assertIsNotNone(app._stream_camera_frame)
        self.assertEqual(app._stream_camera_serial, 3)

    def test_stream_preview_throttle_never_skips_native_camera_button_release(self):
        """OBS-only RGB throttling cannot stall the actual game input path."""
        import time
        from types import MethodType
        from anything_plays.ui_stream import StreamMixin

        app = self.app
        app._stream_output_window = object()
        app._stream_options = {"frame_rate": "15 FPS"}
        app._stream_camera_last_snapshot = None
        app._stream_camera_frame = None
        app._stream_camera_serial = 0
        app.stream_camera_snapshot = MethodType(
            StreamMixin.stream_camera_snapshot, app
        )
        app.stream_clear_camera = MethodType(
            StreamMixin.stream_clear_camera, app
        )
        convert_original = cv2.cvtColor
        app.set_pixels(primary=[(45, 60)])
        with (
            patch.object(time, "monotonic",
                         side_effect=(20.0, 20.010)),
            patch.object(cv2, "cvtColor", wraps=convert_original) as convert,
        ):
            app.draw_camera()
            app.emu.frame()
            self.assertTrue(app.emu.held("A", 0))
            first_preview = app._stream_camera_frame
            self.assertIsNotNone(first_preview)
            app.set_pixels()  # Object disappears 10 ms after the first frame.
            app.draw_camera()
            app.emu.frame()
            self.assertFalse(app.emu.held("A", 0))

        rgb = [call for call in convert.call_args_list
               if call.args[1] == cv2.COLOR_BGR2RGB]
        hsv = [call for call in convert.call_args_list
               if call.args[1] == cv2.COLOR_BGR2HSV]
        self.assertEqual(len(rgb), 1, "OBS conversion skipped only")
        self.assertEqual(len(hsv), 2, "native tracking still runs every frame")
        self.assertEqual(app._stream_camera_serial, 1)
        self.assertIs(app._stream_camera_frame, first_preview)

    def test_opt_in_input_probe_bad_clock_never_sticks_p1_or_p2(self):
        """Optional timing faults must not change real held control state."""
        import time
        import math
        from anything_plays.ui_camera import optional_camera_latency_start

        app = self.app
        app.emu.inputs.enable_latency_probe(clock=lambda: 50.02)
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(time, "perf_counter", return_value=50.0):
            app.draw_camera()
        app.emu.frame()
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))
        self.assertEqual(app.emu.inputs.latency_snapshot()["samples"], 1)

        # Releasing the two fish happens even if the optional clock raises,
        # and the emulator does not acquire a stale pending timing sample.
        app.set_pixels()
        with patch.object(time, "perf_counter", side_effect=OSError(
            "private camera driver /Users/owner/serial-452"
        )):
            app.draw_camera()
        app.emu.frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))
        self.assertEqual(app.emu.inputs.latency_snapshot()["samples"], 1)
        self.assertTrue(app.emu.inputs._latency_enabled)
        self.assertEqual(app.emu.inputs.commands.qsize(), 0)

        # The measurement can resume without toggling the feature.
        app.emu.inputs.latency_probe._clock = lambda: 50.12
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(time, "perf_counter", return_value=50.10):
            app.draw_camera()
        app.emu.frame()
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))
        self.assertEqual(app.emu.inputs.latency_snapshot()["samples"], 2)

    def test_opt_in_probe_refuses_untrustworthy_timestamps(self):
        import time
        from anything_plays.ui_camera import optional_camera_latency_start
        with patch.object(time, "perf_counter",
                          side_effect=RuntimeError("secret ROM path")) as clock:
            self.assertIsNone(optional_camera_latency_start(False))
            clock.assert_not_called()
            self.assertIsNone(optional_camera_latency_start(True))
        for invalid in (
            None, True, float("nan"), float("inf"), float("-inf"),
            -1.0, 10**1000, "private /home/person/ROMs", [], {},
        ):
            with self.subTest(kind=type(invalid).__name__):
                with patch.object(time, "perf_counter", return_value=invalid):
                    self.assertIsNone(optional_camera_latency_start(True))
        with patch.object(time, "perf_counter", return_value=123.456):
            self.assertEqual(optional_camera_latency_start(True), 123.456)

    def test_bad_newer_camera_probe_clock_cannot_relabel_old_native_inputs(self):
        import time
        app = self.app
        app.emu.inputs.enable_latency_probe(
            clock=iter((50.01, 50.21, 50.25)).__next__
        )
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(time, "perf_counter", return_value=50.0):
            app.draw_camera()  # Pending, not yet consumed by native loop.
        self.assertIsNotNone(app.emu.inputs.latency_probe._pending)

        # Newer camera observation loses both fish while the optional
        # clock fails. Native release still happens, and the pending older
        # sample must be invalidated rather than counted as current input.
        app.set_pixels()
        with patch.object(time, "perf_counter", side_effect=OSError(
            "private /Users/owner/usb-camera"
        )):
            app.draw_camera()
        app.emu.frame()
        report = app.emu.inputs.latency_snapshot()
        self.assertEqual(report["samples"], 0)
        self.assertEqual(report["discarded_pending"], 1)
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))

        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(time, "perf_counter", return_value=50.2):
            app.draw_camera()
        app.emu.frame()
        report = app.emu.inputs.latency_snapshot()
        self.assertEqual(report["samples"], 1)
        self.assertEqual(report["discarded_pending"], 1)
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))

    def test_opt_in_tracking_is_consumed_on_next_real_input_snapshot(self):
        # Exercise actual OpenCV contours -> CameraMixin -> native InputBuffer
        # with a deterministic clock. This is software only: no webcam glass,
        # USB, monitor or real libretro core is involved.
        import time
        app = self.app
        app.emu.inputs.enable_latency_probe(
            clock=iter((10.013, 10.040)).__next__
        )
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(time, "perf_counter", return_value=10.0):
            app.draw_camera()
        self.assertEqual(app.emu.inputs.latency_snapshot()["samples"], 0)
        app.emu.frame()
        result = app.emu.inputs.latency_snapshot()
        self.assertEqual(result["samples"], 1)
        self.assertEqual(
            result["stages"]["tracking_to_native"]["p95_bucket_ms"],
            "33-50",
        )
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))

    def test_opt_in_stop_discards_pending_camera_timestamp(self):
        import time
        app = self.app
        app.emu.inputs.enable_latency_probe(clock=lambda: 10.02)
        app.set_pixels(primary=[(45, 60)])
        with patch.object(time, "perf_counter", return_value=10.0):
            app.draw_camera()
        app.stop_controls()
        app.emu.frame()
        report = app.emu.inputs.latency_snapshot()
        self.assertEqual(report["samples"], 0)
        self.assertEqual(report["discarded_pending"], 1)
        self.assertFalse(app.emu.held("A", 0))

    def test_two_colors_share_one_hsv_conversion_and_release_on_loss(self):
        app = self.app
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        converter = cv2.cvtColor
        with patch.object(cv2, "cvtColor", wraps=converter) as convert:
            app.draw_camera()
        conversions = [call for call in convert.call_args_list
                       if call.args[1] == cv2.COLOR_BGR2HSV]
        self.assertEqual(len(conversions), 1, "one camera HSV conversion per frame")
        app.emu.frame()
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))
        app.set_pixels()
        app.draw_camera()
        app.emu.frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))

    def test_optional_camera_action_label_fault_never_disarms_native_ports(self):
        from unittest.mock import Mock
        app = self.app
        for stage in ("get", "set"):
            with self.subTest(stage=stage):
                action = Mock()
                action.get.return_value = ""
                getattr(action, stage).side_effect = OSError(
                    "private device path /Users/person/USB-serial"
                )
                app.action = action
                app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
                app.one_frame()
                self.assertTrue(app.armed)
                self.assertTrue(app.emu.held("A", 0))
                self.assertTrue(app.emu.held("B", 1))
                app.set_pixels()
                app.one_frame()
                self.assertFalse(app.emu.held("A", 0))
                self.assertFalse(app.emu.held("B", 1))
                self.assertTrue(app.armed)

    def test_post_dispatch_annotation_and_calibration_faults_keep_both_ports(self):
        app = self.app
        self.pad.buttons = {"X"}
        app.emu.set_manual("Start", True)
        original_draw = cv2.drawContours
        for broken in ("contours", "zones", "calibration"):
            with self.subTest(stage=broken):
                app.render_zones = lambda pixels, zones: pixels
                app.calibration_note_frame = lambda *args: None
                if broken == "zones":
                    def fail_zone(*args):
                        raise RuntimeError("private /home/user/driver")
                    app.render_zones = fail_zone
                if broken == "calibration":
                    def fail_calibration(*args):
                        raise OSError("USB serial /Users/owner")
                    app.calibration_note_frame = fail_calibration
                app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
                with patch.object(
                    cv2, "drawContours",
                    side_effect=(RuntimeError("private OpenCV display")
                                 if broken == "contours" else original_draw),
                ):
                    app.one_frame()
                self.assertTrue(app.armed)
                self.assertTrue(app.emu.held("A", 0))
                self.assertTrue(app.emu.held("B", 1))
                self.assertTrue(app.emu.held("X", 0))
                self.assertTrue(app.emu.held("Start", 0))
                app.set_pixels()
                app.one_frame()
                self.assertFalse(app.emu.held("A", 0))
                self.assertFalse(app.emu.held("B", 1))
                self.assertTrue(app.emu.held("X", 0))
                self.assertTrue(app.emu.held("Start", 0))

    def test_broken_primary_tk_resize_never_sticks_native_camera_buttons(self):
        from unittest.mock import MagicMock
        app = self.app
        app.geometry = lambda: (0, 0, 192, 128, 192, 128)
        app.canvas = MagicMock()
        app.camera_photo = object()
        app._camera_canvas_item = 8
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(cv2, "resize",
                          side_effect=OSError("private camera id /home/user")):
            app.one_frame()
        self.assertTrue(app.armed)
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))
        self.assertIsNone(app.camera_photo)
        self.assertIsNone(app._camera_canvas_item)
        app.canvas.delete.assert_called_once_with("all")
        app.set_pixels()
        with patch("anything_plays.ui_camera.ImageTk.PhotoImage") as photo:
            photo.return_value.width.return_value = 192
            photo.return_value.height.return_value = 128
            app.one_frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))
        self.assertIsNotNone(app.camera_photo)
        self.assertTrue(app.armed)

    def test_broken_optional_stream_hook_does_not_interrupt_native_camera(self):
        from unittest.mock import Mock
        app = self.app
        app._stream_output_window = object()
        app.stream_camera_snapshot = Mock(
            side_effect=OSError("private OBS camera serial")
        )
        app.stream_clear_camera = Mock()
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))
        app.set_pixels()
        app.one_frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))
        self.assertEqual(app.stream_clear_camera.call_count, 2)
        self.assertTrue(app.armed)

    def test_camera_controls_dispatch_before_contour_annotations(self):
        app = self.app
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        unmarked = app.frame.copy()
        original_draw = cv2.drawContours
        decorations = []

        def observed_draw(*args, **kwargs):
            # Native InputBuffer receives complete held snapshots for both
            # players before any cosmetic OpenCV contour is rendered.
            self.assertIn(app.emu.inputs.id_for("A"),
                          app.emu.inputs._camera_held[0])
            self.assertIn(app.emu.inputs.id_for("B"),
                          app.emu.inputs._camera_held[1])
            decorations.append(True)
            return original_draw(*args, **kwargs)

        with patch.object(cv2, "drawContours", side_effect=observed_draw):
            app.draw_camera()
        self.assertEqual(len(decorations), 2)
        self.assertTrue(np.array_equal(unmarked, app.frame),
                        "annotating the preview must not mutate input pixels")
        app.emu.frame()
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))

    def test_overlapping_camera_and_gamepad_hold_releases_independently(self):
        app = self.app
        self.pad.buttons = {"A"}
        app.color2_enabled.set(False)
        app.set_pixels(primary=[(44, 56)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        app.set_pixels()
        app.one_frame()
        self.assertTrue(app.emu.held("A"), "SDL should retain its own hold")
        app.emu.set_manual("A", True)
        self.pad.connected = False
        self.devices.clear()
        app.one_frame()
        self.assertTrue(app.emu.held("A"), "keyboard remains after unplug")
        self.assertFalse(self.reader.physical_buttons)
        app.emu.release_manual()
        app.emu.frame()
        self.assertFalse(app.emu.held("A"))

    def test_focus_loss_drops_gamepad_not_armed_camera_or_player_two(self):
        app = self.app
        self.pad.buttons = {"A"}
        app.set_pixels(primary=[(44, 56)], secondary=[(144, 60)])
        app.one_frame()
        app.root.focus = None
        app.one_frame()
        self.assertTrue(app.emu.held("A"), "camera should remain armed")
        self.assertTrue(app.emu.held("B", 1))
        self.assertFalse(app.emu.inputs.gamepad_buttons)
        app.set_pixels()
        app.one_frame()
        self.assertFalse(app.emu.held("A"))
        self.assertFalse(app.emu.held("B", 1))
        app.root.focus = object()
        app.one_frame()
        self.assertFalse(app.emu.held("A"),
                         "a held SDL press must not resume on focus return")
        self.pad.buttons = set()
        app.one_frame()
        self.assertFalse(app.emu.inputs.gamepad_buttons)
        self.pad.buttons = {"A"}
        app.one_frame()
        self.assertTrue(app.emu.held("A"),
                        "a fresh press resumes after releasing the controller")

    def test_camera_stop_does_not_release_keyboard_or_controller(self):
        app = self.app
        self.pad.buttons = {"B"}
        app.emu.set_manual("Start", True)
        app.set_pixels(primary=[(44, 56)], secondary=[(144, 60)])
        app.one_frame()
        app.stop_controls()
        app.emu.frame()
        self.assertFalse(app.emu.held("A"))
        self.assertFalse(app.emu.held("B", 1))
        self.assertTrue(app.emu.held("B"))
        self.assertTrue(app.emu.held("Start"))
        self.assertFalse(app.armed)
        self.assertEqual(app.emu.inputs.commands.qsize(), 0)

    def test_rescan_drops_only_controller_while_both_camera_ports_remain(self):
        app = self.app
        self.pad.buttons = {"START"}
        app.set_pixels(primary=[(44, 56)], secondary=[(144, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("Start"))
        app.refresh_gamepad()
        app.emu.frame()
        self.assertFalse(app.emu.held("Start"))
        self.assertTrue(app.emu.held("A"))
        self.assertTrue(app.emu.held("B", 1))
        self.assertFalse(self.reader.physical_buttons)

    def test_multi_target_color_tracking_does_not_drop_controller_state(self):
        app = self.app
        app.color2_enabled.set(False)
        app.multi_fish_enabled.set(True)
        self.pad.buttons = {"START"}
        app.set_pixels(primary=[(44, 60), (145, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        self.assertTrue(app.emu.held("B"))
        self.assertTrue(app.emu.held("Start"))
        self.assertIn("Primary objects: 2", app.action.get())

    def test_classic_pulse_clock_fault_never_interrupts_two_player_tracking(self):
        from unittest.mock import patch
        import time

        app = self.app
        app.camera_input_mode.set("Pulse (classic)")
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        with patch.object(time, "monotonic", side_effect=OSError(
            "/Users/private/camera cooldown driver 786"
        )):
            app.draw_camera()  # Must not throw or issue accidental presses.
        app.emu.frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))
        self.assertEqual(app.emu.inputs.commands.qsize(), 0)
        self.assertEqual(app._last_camera_pulses, {})

        with patch.object(time, "monotonic", return_value=101.0):
            app.draw_camera()
        app.emu.frame()
        self.assertTrue(app.emu.held("A", 0))
        self.assertTrue(app.emu.held("B", 1))
        self.assertEqual(app._last_camera_pulses[(0, "A")], 101.0)
        self.assertEqual(app._last_camera_pulses[(1, "B")], 101.0)

        # A resumed/restarted clock must not freeze pulse controls until the
        # machine's previous monotonic value is reached again.
        app._last_camera_pulses[(0, "A")] = 1000.0
        app._last_camera_pulses[(1, "B")] = 1000.0
        with patch.object(time, "monotonic", return_value=1.0):
            app.draw_camera()
        self.assertEqual(app.emu.inputs.commands.qsize(), 2)
        self.assertEqual(app._last_camera_pulses[(0, "A")], 1.0)
        self.assertEqual(app._last_camera_pulses[(1, "B")], 1.0)

    def test_external_pulse_bridge_skips_bad_clock_and_recovers(self):
        from unittest.mock import Mock
        import time

        app = self.app
        app.external_input = Mock()
        app.color2_enabled.set(False)
        app.set_pixels(primary=[(45, 60)])
        with patch.object(time, "monotonic", return_value=float("nan")):
            app.draw_camera()
        app.external_input.press.assert_not_called()
        self.assertEqual(app._last_camera_pulses, {})
        with patch.object(time, "monotonic", return_value=200.0):
            app.draw_camera()
        app.external_input.press.assert_called_once_with("A", 4)
        self.assertEqual(app._last_camera_pulses[(0, "A")], 200.0)

    def test_pulse_helpers_reject_invalid_timestamps_and_clock_reversals(self):
        from anything_plays.ui_camera import (
            optional_camera_pulse_now, camera_pulse_due,
        )
        import time

        for value in (None, True, float("nan"), float("inf"),
                      -1, 10**1000, "private", {}, []):
            with self.subTest(kind=type(value).__name__):
                with patch.object(time, "monotonic", return_value=value):
                    self.assertIsNone(optional_camera_pulse_now())
        with patch.object(time, "monotonic",
                          side_effect=RuntimeError("private GPU driver")):
            self.assertIsNone(optional_camera_pulse_now())
        self.assertFalse(camera_pulse_due(None, None, .1))
        self.assertTrue(camera_pulse_due(None, 1.0, .1))
        self.assertFalse(camera_pulse_due(1.0, 1.05, .1))
        self.assertTrue(camera_pulse_due(1.0, 1.11, .1))
        self.assertTrue(camera_pulse_due(1000.0, 1.0, .1))

    def test_pulse_camera_queue_expires_but_controller_remains(self):
        app = self.app
        app.color2_enabled.set(False)
        app.camera_input_mode.set("Pulse (classic)")
        self.pad.buttons = {"B"}
        app.set_pixels(primary=[(44, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        self.assertTrue(app.emu.held("B"))
        app.set_pixels()
        for _ in range(7):
            app.one_frame()
            app.emu.inputs.after_frame()
        app.emu.frame()
        self.assertFalse(app.emu.held("A"))
        self.assertTrue(app.emu.held("B"))
        self.assertEqual(app.emu.inputs.commands.qsize(), 0)

    def test_camera_and_gamepad_work_for_all_eighteen_system_profiles(self):
        app = self.app
        self.pad.buttons = {"START"}
        app.color2_enabled.set(False)
        app.set_pixels(primary=[(44, 60)])
        self.assertEqual(len(BUTTONS_BY_SYSTEM), 18)
        for system in BUTTONS_BY_SYSTEM:
            with self.subTest(system=system):
                app.system_key.set(system)
                app.emu.inputs.system = system
                app.emu.inputs.disarm()
                app.one_frame()
                self.assertTrue(app.emu.held("A"),
                                "primary color zone was not delivered")
                self.assertTrue(app.emu.held("Start"),
                                "gamepad input was not delivered")
                self.assertEqual(app.emu.inputs.commands.qsize(), 0)

    def test_thousand_camera_and_controller_frames_remain_bounded(self):
        app = self.app
        app.color2_enabled.set(False)
        app.multi_fish_enabled.set(True)
        for i in range(1000):
            self.pad.buttons = {"A"} if i % 2 else {"START"}
            app.set_pixels(primary=[(44, 60)] if i % 3 else [(145, 60)])
            app.one_frame()
            self.assertEqual(app.emu.held("A"),
                             i % 3 != 0 or i % 2 == 1)
            self.assertEqual(app.emu.held("B"), i % 3 == 0)
            self.assertEqual(app.emu.inputs.commands.qsize(), 0)
            app.emu.inputs.after_frame()
        self.assertEqual(self.pygame.event.pumps, 1000)
        self.assertEqual(self.pygame.event.drains, 1000)
        self.assertEqual(len(app.root.jobs), 1000)
        self.assertLessEqual(len(app.emu.inputs.gamepad_buttons), 1)

    def test_unsupported_second_player_rejected_without_silencing_controller(self):
        app = self.app
        self.pad.buttons = {"A"}
        app.system_key.set("gba")
        app.emu.inputs.system = "gba"
        app.set_pixels(secondary=[(145, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        self.assertFalse(app.emu.held("B", 1))
        self.assertIn("Secondary object cannot use Player 2", app.action.get())


class CameraScanErrorPrivacyTests(TestCase):
    """Background discovery must not leak raw camera driver exceptions."""

    def test_failed_worker_reports_only_safe_failure_flag(self):
        from unittest.mock import Mock

        class ImmediateThread:
            def __init__(self, *, target, **_kwargs):
                self.target = target

            def start(self):
                self.target()

        app = CameraMixin()
        app.camera_scanning = False
        app.stop_camera = Mock()
        app.status = Variable("")
        app.root = Mock()
        with (
            patch("anything_plays.ui_camera.discover",
                  side_effect=OSError(
                      "private webcam serial XYZ /home/user/driver.log"
                  )),
            patch("anything_plays.ui_camera.threading.Thread",
                  ImmediateThread),
        ):
            app.scan_cameras()
        self.assertTrue(app.camera_scanning)
        found, failure = app._camera_scan_results.get_nowait()
        self.assertEqual(found, [])
        self.assertIs(failure, True)
        self.assertNotIn("XYZ", str((found, failure)))
        app.root.after.assert_called_once()

    def test_error_ui_redacts_raw_exception_and_normal_discovery_still_works(self):
        app = CameraMixin()
        app.camera_name = Variable("Previously selected (device 3)")
        app.camera_options = {}
        app.camera_combo = {}
        app.status = Variable("")
        app.camera_scanning = True

        app.finish_scan([], "/Users/private/Driver/secret-device serial ABC")
        self.assertFalse(app.camera_scanning)
        self.assertIn("Camera search failed", app.status.get())
        for private in ("/Users", "secret-device", "ABC"):
            self.assertNotIn(private, app.status.get())
        app.finish_scan([(3, "Previously selected")])
        self.assertEqual(app.camera_name.get(), "Previously selected (device 3)")
        self.assertEqual(app.camera_options, {
            "Previously selected (device 3)": 3
        })


if __name__ == "__main__":
    import unittest
    unittest.main()
