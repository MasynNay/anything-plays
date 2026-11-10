"""Optional SDL gamepad support for local, embedded emulator manual play.

SDL's GameController mapping normalizes common Xbox/PlayStation-style pads.
No device driver, background thread, network service, or OS key injection is
started at import time. SDL initializes only when the user enables a pad.
All reading happens on Tk's UI thread. InputBuffer receives an atomic snapshot
separate from keyboard and camera state.
"""
from __future__ import annotations

import importlib
import os
import time

from anything_plays.system_profiles import BUTTONS_BY_SYSTEM

DISABLED = "(None)"
SOURCES = (
    "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
    "LEFT_STICK_UP", "LEFT_STICK_DOWN", "LEFT_STICK_LEFT", "LEFT_STICK_RIGHT",
    "RIGHT_STICK_UP", "RIGHT_STICK_DOWN", "RIGHT_STICK_LEFT", "RIGHT_STICK_RIGHT",
    "A", "B", "X", "Y", "BACK", "START",
    "LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_TRIGGER", "RIGHT_TRIGGER",
)
BUTTON_CONST = {
    "DPAD_UP": "DPAD_UP", "DPAD_DOWN": "DPAD_DOWN",
    "DPAD_LEFT": "DPAD_LEFT", "DPAD_RIGHT": "DPAD_RIGHT",
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "BACK": "BACK", "START": "START",
    "LEFT_SHOULDER": "LEFTSHOULDER", "RIGHT_SHOULDER": "RIGHTSHOULDER",
}
AXES = {
    "LEFT_STICK_LEFT": ("LEFTX", -1),
    "LEFT_STICK_RIGHT": ("LEFTX", 1),
    "LEFT_STICK_UP": ("LEFTY", -1),
    "LEFT_STICK_DOWN": ("LEFTY", 1),
    "RIGHT_STICK_LEFT": ("RIGHTX", -1),
    "RIGHT_STICK_RIGHT": ("RIGHTX", 1),
    "RIGHT_STICK_UP": ("RIGHTY", -1),
    "RIGHT_STICK_DOWN": ("RIGHTY", 1),
}
DEADZONE = 12000  # SDL signed-stick range is -32768..32767.
TRIGGER_THRESHOLD = 15000
SCAN_INTERVAL = 1.5


def default_bindings(system):
    """An ordinary gamepad's face buttons, D-pad, and sticks."""
    if system not in BUTTONS_BY_SYSTEM:
        raise ValueError("Unknown console")
    result = {
        "DPAD_UP": "Up", "DPAD_DOWN": "Down",
        "DPAD_LEFT": "Left", "DPAD_RIGHT": "Right",
        "LEFT_STICK_UP": "Up", "LEFT_STICK_DOWN": "Down",
        "LEFT_STICK_LEFT": "Left", "LEFT_STICK_RIGHT": "Right",
        "A": "A", "B": "B", "X": "X", "Y": "Y",
        "BACK": "Select", "START": "Start",
        "LEFT_SHOULDER": "L", "RIGHT_SHOULDER": "R",
        "LEFT_TRIGGER": "L", "RIGHT_TRIGGER": "R",
        "RIGHT_STICK_UP": "C Up", "RIGHT_STICK_DOWN": "C Down",
        "RIGHT_STICK_LEFT": "C Left", "RIGHT_STICK_RIGHT": "C Right",
    }
    if system == "genesis":
        result.update(X="C", BACK="Mode", LEFT_SHOULDER="X",
                      RIGHT_SHOULDER="Z", LEFT_TRIGGER="X",
                      RIGHT_TRIGGER="Z")
    elif system == "n64":
        result.update(LEFT_TRIGGER="Z", RIGHT_TRIGGER="Z")
    elif system == "gamecube":
        result.update(LEFT_TRIGGER="L", RIGHT_TRIGGER="R", BACK="Z")
    allowed = set(BUTTONS_BY_SYSTEM[system])
    return {source: target for source, target in result.items()
            if target in allowed}


def normalize_bindings(system, saved=None):
    """Reject malformed settings while allowing disabled and duplicate targets."""
    result = default_bindings(system)
    if not isinstance(saved, dict):
        return result
    allowed = set(BUTTONS_BY_SYSTEM[system])
    for source, target in saved.items():
        # Preferences are user-editable JSON. Invalid types must never crash
        # polling or disable an otherwise healthy physical controller.
        if (source in SOURCES and isinstance(target, str)
                and (target in allowed or target == DISABLED)):
            result[source] = target
    return result


def mapped_buttons(system, physical, bindings=None):
    """Return held emulated buttons for a normalized physical input snapshot."""
    mapping = normalize_bindings(system, bindings)
    return frozenset(mapping[src] for src in set(physical) & set(SOURCES)
                     if src in mapping and mapping[src] != DISABLED)


class GamepadReader:
    """Poll a single standard SDL controller, reconnecting after hotplug.

    SDL's dummy video driver allows event pumping without creating an SDL
    window alongside Tk. It never changes Tk's display or installs hooks.
    Call start/stop only from the Tk main thread.
    """

    def __init__(self, *, clock=time.monotonic, loader=None):
        self.clock = clock
        self.loader = loader or (lambda: importlib.import_module("pygame"))
        self.pygame = None
        self.api = None
        self.controller = None
        self.name = ""
        # Raw input is for the settings dialog only, independent of mappings
        # and whether an emulator is currently running.
        self.physical_buttons = frozenset()
        self.last_scan = float("-inf")

    def start(self):
        if self.api is not None:
            return
        # No SDL windows; prevents a second video backend from competing with Tk.
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pg = self.loader()
        try:
            pg.display.init()
            pg.joystick.init()
            api = importlib.import_module("pygame._sdl2.controller")
            api.init()
            self.pygame, self.api = pg, api
        except Exception:
            # A failed SDL initialization must never prevent keyboard play.
            try:
                pg.joystick.quit()
                pg.display.quit()
            except Exception:
                pass
            raise

    def _sdl_constant(self, name):
        """SDL GameController constants live in pygame, not always _sdl2."""
        try:
            return getattr(self.pygame, name)
        except AttributeError:
            # Keep compatibility with SDL wrappers exposing constants locally.
            return getattr(self.api, name)

    def _close_device(self):
        device, self.controller = self.controller, None
        self.name = ""
        self.physical_buttons = frozenset()
        if device is not None:
            try:
                device.quit()
            except Exception:
                pass

    def refresh(self):
        self.last_scan = float("-inf")
        self._close_device()

    def _connect(self):
        now = self.clock()
        if self.controller is not None:
            try:
                attached = self.controller.attached()
            except Exception:
                attached = False
            if attached:
                return
            self._close_device()
        if now - self.last_scan < SCAN_INTERVAL:
            return
        self.last_scan = now
        for index in range(min(16, self.api.get_count())):
            if self.api.is_controller(index):
                try:
                    device = self.api.Controller(index)
                    if not device.attached():
                        device.quit()
                        continue
                except (OSError, RuntimeError, ValueError):
                    continue
                self.controller = device
                self.name = str(self.api.name_forindex(index) or "Gamepad")
                return

    def poll(self, system, bindings=None):
        """Return (held emulated buttons, human-readable connection status)."""
        if self.api is None:
            self.physical_buttons = frozenset()
            return frozenset(), "Controller disabled"
        # SDL requires the video event queue to be pumped/drained for fresh
        # controller states. Avoid accumulating an unbounded event backlog.
        self.pygame.event.pump()
        self.pygame.event.get()
        self._connect()
        if self.controller is None:
            return frozenset(), "No compatible controller connected"
        physical = set()
        pad = self.controller
        try:
            for source, name in BUTTON_CONST.items():
                code = self._sdl_constant("CONTROLLER_BUTTON_" + name)
                if pad.get_button(code):
                    physical.add(source)
            for source, (axis, direction) in AXES.items():
                code = self._sdl_constant("CONTROLLER_AXIS_" + axis)
                if direction * pad.get_axis(code) >= DEADZONE:
                    physical.add(source)
            for name in ("LEFT", "RIGHT"):
                code = self._sdl_constant("CONTROLLER_AXIS_TRIGGER" + name)
                if pad.get_axis(code) >= TRIGGER_THRESHOLD:
                    physical.add(name + "_TRIGGER")
        except Exception:
            # A device can disappear between attached() and a button read.
            # Clear the snapshot now; rescan automatically on the next poll.
            self._close_device()
            self.last_scan = float("-inf")
            return frozenset(), "Controller disconnected · Scanning again"
        self.physical_buttons = frozenset(physical)
        return mapped_buttons(system, physical, bindings), self.name + " connected"

    def stop(self):
        self._close_device()
        api, self.api = self.api, None
        pg, self.pygame = self.pygame, None
        if api is not None:
            api.quit()
        if pg is not None:
            pg.joystick.quit()
            pg.display.quit()
        self.last_scan = float("-inf")
