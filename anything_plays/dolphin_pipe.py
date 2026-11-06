"""GameCube camera/keyboard controller via Dolphin's named-pipe input API.

The Dolphin executable and GPU renderer remain external. A dedicated alpha
Dolphin user directory keeps controller configuration and game saves separate
from a person's normal Dolphin installation. No OS keyboard injection.
"""
from pathlib import Path
from threading import Event, Lock, Thread
import errno
import os
import stat
import sys
import time

GAMECUBE_KEYS = frozenset((
    "Left", "Right", "Up", "Down", "A", "B", "X", "Y",
    "Z", "L", "R", "Start", "C Up", "C Down", "C Left", "C Right",
))
DIGITAL_NAMES = {
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "Z": "Z", "L": "L", "R": "R", "Start": "START",
}
PIPE_NAME = "anythingplays21"


def dolphin_profile(user_dir):
    """Configure an independent Dolphin profile and a named input pipe.

    Regular Dolphin preferences, memory cards and controller bindings are
    never modified. Dolphin's --user option selects this test-only profile.
    """
    if sys.platform == "win32":
        raise RuntimeError("Dolphin pipe controls require macOS or Linux")
    root = Path(user_dir).expanduser()
    config = root / "Config"
    pipes = root / "Pipes"
    config.mkdir(parents=True, exist_ok=True)
    pipes.mkdir(parents=True, exist_ok=True)
    named_pipe = pipes / PIPE_NAME
    if named_pipe.is_symlink():
        raise RuntimeError("Refusing symlinked controller pipe")
    if not named_pipe.exists():
        os.mkfifo(named_pipe, mode=0o600)
    if not stat.S_ISFIFO(named_pipe.stat().st_mode):
        raise RuntimeError("A non-pipe file occupies the Dolphin controller path")
    mapping = {
        "Buttons/A": "Button A",
        "Buttons/B": "Button B",
        "Buttons/X": "Button X",
        "Buttons/Y": "Button Y",
        "Buttons/Z": "Button Z",
        "Buttons/Start": "Button START",
        "Triggers/L": "Button L",
        "Triggers/R": "Button R",
        "Main Stick/Up": "Axis MAIN Y +",
        "Main Stick/Down": "Axis MAIN Y -",
        "Main Stick/Left": "Axis MAIN X -",
        "Main Stick/Right": "Axis MAIN X +",
        "Main Stick/Center": "0.00 0.00",
        "C-Stick/Up": "Axis C Y +",
        "C-Stick/Down": "Axis C Y -",
        "C-Stick/Left": "Axis C X -",
        "C-Stick/Right": "Axis C X +",
        "C-Stick/Center": "0.00 0.00",
    }
    lines = ["[GCPad1]", f"Device = Pipe/0/{PIPE_NAME}"]
    for key, name in mapping.items():
        value = name if key.endswith("/Center") else "`" + name + "`"
        lines.append(f"{key} = {value}")
    (config / "GCPadNew.ini").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    # Standard GameCube controller at port 1; allow background pipe input.
    (config / "Dolphin.ini").write_text(
        "[Core]\nSIDevice0 = 6\n\n"
        "[Input]\nBackgroundInput = True\n",
        encoding="utf-8",
    )
    return named_pipe


def gamecube_commands(buttons, previous):
    """Emit changed Dolphin PIPE protocol commands with explicit releases."""
    desired = set(buttons)
    before = set(previous)
    result = []
    for button, label in DIGITAL_NAMES.items():
        if (button in desired) != (button in before):
            result.append(("PRESS " if button in desired else "RELEASE ") + label)
    def stick_state(keys, prefix=""):
        return (
            0.5 + 0.5 * (int((prefix + "Right") in keys) -
                         int((prefix + "Left") in keys)),
            0.5 + 0.5 * (int((prefix + "Up") in keys) -
                         int((prefix + "Down") in keys)),
        )
    main = stick_state(desired)
    if main != stick_state(before):
        result.append(f"SET MAIN {main[0]:.2f} {main[1]:.2f}")
    c_stick = stick_state(desired, "C ")
    if c_stick != stick_state(before, "C "):
        result.append(f"SET C {c_stick[0]:.2f} {c_stick[1]:.2f}")
    return result


class DolphinPipeController:
    def __init__(self, user_dir, *, clock=None):
        self.pipe = dolphin_profile(user_dir)
        self.clock = clock or time.monotonic
        self._lock = Lock()
        self._manual = set()
        self._pulse_until = {}
        self._last = set()
        self._fd = None
        self._stop = Event()
        self._thread = None
        self._closed = False

    def press(self, button, frames=8):
        if button not in GAMECUBE_KEYS:
            return
        with self._lock:
            if not self._closed:
                expiry = self.clock() + max(1, min(60, int(frames))) / 60
                self._pulse_until[button] = max(
                    expiry, self._pulse_until.get(button, 0)
                )

    def set_manual(self, button, down):
        if button not in GAMECUBE_KEYS:
            return
        with self._lock:
            if self._closed:
                return
            if down:
                self._manual.add(button)
            else:
                self._manual.discard(button)

    def release_camera(self):
        with self._lock:
            self._pulse_until.clear()

    def release_manual(self):
        with self._lock:
            self._manual.clear()

    def _connect(self):
        if self._fd is not None:
            return True
        try:
            self._fd = os.open(self.pipe, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as exc:
            if exc.errno not in (errno.ENXIO, errno.ENOENT):
                raise
            return False
        self._last = set()
        return True

    def flush(self):
        with self._lock:
            now = self.clock()
            self._pulse_until = {
                name: until for name, until in self._pulse_until.items()
                if until > now
            }
            if not self._connect():
                return
            current = self._manual | self._pulse_until.keys()
            commands = gamecube_commands(current, self._last)
            if not commands:
                return
            try:
                os.write(self._fd, ("\n".join(commands) + "\n").encode("ascii"))
            except OSError as exc:
                if exc.errno in (errno.EPIPE, errno.ENXIO, errno.EAGAIN):
                    os.close(self._fd)
                    self._fd = None
                    self._last = set()
                    return
                raise
            self._last = set(current)

    def start(self):
        with self._lock:
            if self._thread is not None or self._closed:
                return
            self._thread = Thread(
                target=self._run, daemon=True, name="gamecube-camera-input"
            )
            worker = self._thread
        worker.start()

    def _run(self):
        while not self._stop.wait(1 / 60):
            try:
                self.flush()
            except OSError:
                break

    def close(self):
        self._stop.set()
        worker = self._thread
        if worker is not None and worker.is_alive():
            worker.join(timeout=1)
        with self._lock:
            self._pulse_until.clear()
            self._manual.clear()
        try:
            self.flush()
        except OSError:
            pass
        with self._lock:
            self._closed = True
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
