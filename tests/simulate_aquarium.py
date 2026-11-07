"""End-to-end virtual aquarium acceptance, using the REAL Tk camera pipeline.

Creates an actual Anything Plays window under Xvfb, replaces only
cv2.VideoCapture with deterministic *synthetic BGR frames*, routes those
frames through App.tick() -> CameraMixin.draw_camera() -> Emulator ->
InputBuffer.before_frame() -> the same Libretro input_state callback used
by the embedded native cores.

No real camera, game ROM, fish, OS-keyboard injection, or audio hardware.
Run: PYTHONPATH=. xvfb-run -a python tests/simulate_aquarium.py
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np

from app import App
from anything_plays.libretro_input import IDS


PINK = (180, 30, 255)       # OpenCV BGR, equivalent RGB (255,30,180)
CYAN = (255, 255, 0)        # BGR -> RGB (0,255,255)
WIDTH, HEIGHT = 320, 180


def aquarium(*objects):
    """Every circle is a separate simulated fish (x, y, BGR, radius)."""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for x, y, color, radius in objects:
        cv2.circle(frame, (x, y), radius, color, -1)
    return frame


class VirtualCamera:
    def __init__(self):
        self.frame = aquarium()
        self.failed = False
        self.closed = False

    def isOpened(self):
        return not self.closed

    def read(self):
        if self.failed:
            return False, None
        return True, self.frame.copy()

    def release(self):
        self.closed = True


class Simulator:
    def __init__(self, app, root):
        self.app, self.root = app, root
        self.fish_camera = VirtualCamera()
        self.app.cap = self.fish_camera
        self.app.reference_image = False
        self.results = []

    def verify(self, name, actual, expected):
        passed = actual == expected
        self.results.append({
            "scenario": name, "passed": passed,
            "actual": actual, "expected": expected,
        })
        if not passed:
            raise AssertionError(
                f"{name}: expected {expected!r}; actual {actual!r}"
            )

    def configure(self, system, *, left="A", right="B"):
        app = self.app
        if app.system_key.get() != system:
            app.system_key.set(system)
            app.switch_system()
        app.cfg["zones"] = {
            left: [0.01, 0.01, 0.45, 0.99],
            right: [0.55, 0.01, 0.99, 0.99],
        }
        app.mapping_vars[left].set(left)
        app.mapping_vars[right].set(right)
        app.cfg["rgb"] = [255, 30, 180]
        app.cfg["rgb2"] = [0, 255, 255]
        app.min_area.set(80)
        app.tolerance.set(16)
        app.mirror.set(False)
        app.shuffle_enabled.set(False)
        app.camera_input_mode.set("Held while visible")
        app.multi_fish_enabled.set(False)
        app.color2_enabled.set(False)
        app.color2_player.set("Player 2")
        app._last_camera_pulses.clear()
        app.emu.inputs.system = system
        app.emu.running = True
        # Native core execution is *simulated*, not claimed: only the
        # input_state callback is polled after each genuine Tk camera tick.
        app.toggle()
        if not app.armed or not app.emu.armed:
            raise AssertionError("Could not arm local camera controller")

    def camera_tick(self, *objects):
        self.fish_camera.frame = aquarium(*objects)
        self.app.tick()  # real app webcam read, CV detection, UI and routing
        # Prevent test frames from scheduling an unattended UI timer.
        job = getattr(self.app, "_camera_tick_job", None)
        if job:
            self.root.after_cancel(job)
            self.app._camera_tick_job = None
        self.app.emu.inputs.before_frame(self.app.emu.armed)

    def finish_frame(self):
        self.app.emu.inputs.after_frame()

    def snes_buttons(self, port):
        inputs = self.app.emu.inputs
        return sorted(
            name for name in ("A", "B", "X", "Y")
            if inputs.state(port, 1, 0, IDS[name])
        )

    def analog_x(self, port):
        return self.app.emu.inputs.state(port, 5, 0, 0)

    def run(self):
        app = self.app
        self.configure("snes")
        pink_left = (72, 95, PINK, 18)
        pink_right = (245, 95, PINK, 13)
        cyan_right = (245, 95, CYAN, 18)
        self.verify("default multi-input OFF", app.multi_fish_enabled.get(), False)

        # Original behavior: only the largest same-color fish has input.
        self.camera_tick(pink_left, pink_right)
        self.verify("two pink fish / default tracks only largest",
                    self.snes_buttons(0), ["A"])
        self.verify("player two idle by default", self.snes_buttons(1), [])
        self.verify("preview correctly reports one object",
                    "Tracking Color 1: 1 fish" in app.action.get(), True)
        self.finish_frame()

        # Explicitly enable multi-target tracking, now A+B are simultaneous.
        app.multi_fish_enabled.set(True)
        app.update_tracking_preferences()
        self.camera_tick(pink_left, pink_right)
        self.verify("multi-input two pink fish press A+B at same time",
                    self.snes_buttons(0), ["A", "B"])
        self.verify("two pink shapes reported",
                    "Tracking Color 1: 2 fish" in app.action.get(), True)
        self.finish_frame()
        self.camera_tick(pink_left)
        self.verify("fish leaving right zone releases B", self.snes_buttons(0),
                    ["A"])
        self.finish_frame()
        self.camera_tick()
        self.verify("no fish leaves no stuck keys", self.snes_buttons(0), [])
        self.finish_frame()

        # Color 2 is independent, and OFF unless explicitly selected.
        self.camera_tick(pink_left, cyan_right)
        self.verify("disabled Color 2 does not press B",
                    self.snes_buttons(0), ["A"])
        self.finish_frame()

        app.color2_enabled.set(True)
        app.color2_player.set("Player 1")
        app.update_tracking_preferences()
        self.camera_tick(pink_left, cyan_right)
        self.verify("two colors combine on P1", self.snes_buttons(0), ["A", "B"])
        self.verify("two colors P1 mode keeps P2 idle",
                    self.snes_buttons(1), [])
        self.finish_frame()

        app.color2_player.set("Player 2")
        app.update_tracking_preferences()
        self.camera_tick(pink_left, cyan_right)
        self.verify("pink pressed P1 A", self.snes_buttons(0), ["A"])
        self.verify("cyan pressed P2 B simultaneously",
                    self.snes_buttons(1), ["B"])
        self.finish_frame()

        # Disabling Color 2 must explicitly release its controller port.
        app.color2_enabled.set(False)
        app.update_tracking_preferences()
        self.camera_tick(pink_left, cyan_right)
        self.verify("disabling Color 2 releases P2", self.snes_buttons(1), [])
        self.finish_frame()

        # Classic tap mode is finite even if fish remains in its zone.
        app.color2_enabled.set(True)
        app.camera_input_mode.set("Pulse (classic)")
        app.hold_frames.set(2)
        app.cooldown.set(10000)
        app._last_camera_pulses.clear()
        self.camera_tick(pink_left, cyan_right)
        self.verify("classic pulse P1 first frame", self.snes_buttons(0), ["A"])
        self.verify("classic pulse P2 first frame", self.snes_buttons(1), ["B"])
        self.finish_frame()
        self.camera_tick(pink_left, cyan_right)
        self.verify("classic pulse lasts exactly second native frame",
                    self.snes_buttons(1), ["B"])
        self.finish_frame()
        self.camera_tick(pink_left, cyan_right)
        self.verify("classic pulse expired despite fish still visible",
                    (self.snes_buttons(0), self.snes_buttons(1)), ([], []))
        self.finish_frame()

        # Emergency stop clears BOTH ports, but preserves manual input.
        app.camera_input_mode.set("Held while visible")
        app.emu.set_manual("X", True)
        self.camera_tick(pink_left, cyan_right)
        self.verify("camera with manual X remains independent",
                    self.snes_buttons(0), ["A", "X"])
        self.finish_frame()
        app.stop_controls()
        app.emu.inputs.before_frame(app.emu.armed)
        self.verify("STOP releases camera P1 but keeps manual X",
                    self.snes_buttons(0), ["X"])
        self.verify("STOP immediately releases camera P2",
                    self.snes_buttons(1), [])
        app.emu.release_manual()
        app.emu.inputs.before_frame(app.emu.armed)
        self.verify("release manual X", self.snes_buttons(0), [])

        # Real camera read failure must disarm; no ghost keys from last
        # recognized fish when the webcam is unplugged.
        app.toggle()
        self.camera_tick(pink_left, cyan_right)
        self.finish_frame()
        self.fish_camera.failed = True
        app.tick()  # triggers CameraMixin.stop_camera, clears input and frame
        app.emu.inputs.before_frame(app.emu.armed)
        self.verify("webcam disconnect disarms both trackers", app.armed, False)
        self.verify("disconnect clears both ports",
                    (self.snes_buttons(0), self.snes_buttons(1)), ([], []))
        self.fish_camera = VirtualCamera()
        app.cap = self.fish_camera

        # Simulate native callback's analog P1/P2 inputs for both 3D
        # consoles; a real game image and GPU are deliberately not inferred.
        for system in ("n64", "gamecube"):
            self.configure(system, left="Left", right="Right")
            app.color2_enabled.set(True)
            app.color2_player.set("Player 2")
            app.update_tracking_preferences()
            self.camera_tick(pink_left, cyan_right)
            self.verify(f"{system} Player 1 stick left",
                        self.analog_x(0) < -20000, True)
            self.verify(f"{system} Player 2 stick right",
                        self.analog_x(1) > 20000, True)
            self.finish_frame()
            app.stop_controls()
            app.emu.inputs.before_frame(app.emu.armed)
            self.verify(f"{system} STOP clears both analog sticks",
                        (self.analog_x(0), self.analog_x(1)), (0, 0))
            self.verify(f"{system} controller pulse queue bounded",
                        app.emu.inputs.commands.qsize() <= 32, True)

        # No event handlers or looping timers should accumulate as fish
        # repeatedly move between zones and disappear.
        self.configure("snes")
        app.multi_fish_enabled.set(True)
        for i in range(100):
            spots = (pink_left, pink_right) if i % 2 == 0 else (pink_left,)
            self.camera_tick(*spots)
            self.finish_frame()
        self.verify("100 simulated frames reuse one camera canvas item",
                    len(app.canvas.find_all()), 1)
        self.verify("100 frame simulation has bounded pulse queue",
                    app.emu.inputs.commands.qsize() <= 32, True)
        app.stop_controls()


def main():
    report_path = Path("test-evidence/virtual-aquarium-input.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = {
        "method": "synthetic colored fish frames through real Tk camera/UI "
                  "and Libretro input callback",
        "real_camera_used": False,
        "physical_fish_used": False,
        "real_commercial_game_tested": False,
        "real_audio_device_tested": False,
        "scenarios": [],
        "passed": False,
    }
    with tempfile.TemporaryDirectory(prefix="anything-plays-virtual-tank-") as temp:
        with patch("pathlib.Path.home", return_value=Path(temp)), patch(
                "anything_plays.ui_camera.discover", return_value=[]):
            root = tk.Tk()
            app = None
            try:
                app = App(root)
                root.update_idletasks()
                # No real webcam scans, GUI heartbeat or unattended schedule.
                for key in ("_camera_tick_job", "_game_tick_job",
                            "_updates_start_job"):
                    job = getattr(app, key, None)
                    if job is not None:
                        root.after_cancel(job)
                        setattr(app, key, None)
                test = Simulator(app, root)
                evidence["scenarios"] = test.results
                test.run()
                evidence["passed"] = all(x["passed"] for x in test.results)
            except Exception as exc:
                evidence["error"] = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                if app is not None and not app._closing:
                    app.close()
                elif app is None:
                    root.destroy()
                report_path.write_text(json.dumps(evidence, indent=2) + "\n",
                                       encoding="utf-8")
                print(json.dumps({
                    "passed": evidence["passed"],
                    "total": len(evidence["scenarios"]),
                    "failed": [
                        x for x in evidence["scenarios"] if not x["passed"]
                    ],
                    "error": evidence.get("error"),
                }, indent=2), flush=True)


if __name__ == "__main__":
    main()
