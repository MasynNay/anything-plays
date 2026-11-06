"""Local-only camera/keyboard gamepad bridge for the N64 RetroArch backend.

This is a transitional control bridge, not an in-process GPU renderer.
RetroArch's Network RetroPad receiver must be enabled for player one.
The bridge binds no listening socket and sends only to 127.0.0.1.
"""
from pathlib import Path
import socket
import struct
from threading import Event, Lock, Thread
import time

# The protocol is struct remote_message { int port, device, index, id;
# uint16_t state; } with 2 bytes of trailing native alignment padding.
# Explicit little-endian packing avoids platform-dependent Python layouts.
PACKET = struct.Struct("<iiiiH2x")
LOCAL_HOST = "127.0.0.1"
DEFAULT_PORT = 55400
JOY = 1
ANALOG = 5
FULL_AXIS = 28000

# RetroPad identifiers used by Mupen64Plus-Next. The C buttons map to the
# right analogue stick and the main N64 analogue stick to the left stick.
N64_DIGITAL = {
    "B": 0, "Start": 3, "A": 8, "L": 10, "R": 11, "Z": 12,
}
N64_AXES = {
    "Left": (0, 0, -FULL_AXIS), "Right": (0, 0, FULL_AXIS),
    "Up": (0, 1, -FULL_AXIS), "Down": (0, 1, FULL_AXIS),
    "C Left": (1, 0, -FULL_AXIS), "C Right": (1, 0, FULL_AXIS),
    "C Up": (1, 1, -FULL_AXIS), "C Down": (1, 1, FULL_AXIS),
}
N64_BUTTONS = frozenset((*N64_DIGITAL, *N64_AXES))


def write_retroarch_config(path, *, port=DEFAULT_PORT):
    """Enable network controls only for this test launch, not global config.

    RetroArch reads this file with --appendconfig. No network command
    interface is enabled, and config_save_on_exit=False prevents the
    temporary gamepad setting from becoming a permanent global preference.
    """
    if not 1024 <= port <= 65535:
        raise ValueError("Invalid local RetroPad UDP port")
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        'network_remote_enable = "true"\\n'
        'network_remote_enable_user_p1 = "true"\\n'
        f'network_remote_base_port = "{port}"\\n'
        'config_save_on_exit = "false"\\n',
        encoding="utf-8",
    )
    return target


def encode_message(device, index, button_id, state, *, player=0):
    """Encode one RetroArch Network RetroPad button or signed stick axis."""
    if not (0 <= player <= 15 and 0 <= state + 32768 <= 65535):
        raise ValueError("Invalid player or controller state")
    if device not in (JOY, ANALOG):
        raise ValueError("Unsupported RetroPad device")
    return PACKET.pack(player, device, index, button_id, state & 0xFFFF)


def desired_state(buttons):
    """Convert camera zones into digital pad and two analog-stick axes."""
    active = frozenset(buttons)
    states = {(JOY, 0, identity): 1 for button, identity in N64_DIGITAL.items()
              if button in active}
    axes = {}
    for button, (index, axis, value) in N64_AXES.items():
        if button in active:
            axes[(ANALOG, index, axis)] = max(
                -32768, min(32767, axes.get((ANALOG, index, axis), 0) + value)
            )
    return {**states, **{key: val for key, val in axes.items() if val}}


class N64RemoteController:
    """Send held key state and short camera pulses over a loopback UDP socket."""

    def __init__(self, *, port=DEFAULT_PORT, sock=None, clock=None):
        if not 1024 <= port <= 65535:
            raise ValueError("Invalid local RetroPad UDP port")
        self.port = port
        self.clock = clock or time.monotonic
        self.socket = sock if sock is not None else socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._owns_socket = sock is None
        self._lock = Lock()
        self._manual = set()
        self._pulse_until = {}
        self._sent = {}
        self._closed = False
        self._stop = Event()
        self._worker = None

    def press(self, button, frames=8):
        if button not in N64_BUTTONS:
            return
        with self._lock:
            if not self._closed:
                expiry = self.clock() + max(1, min(60, int(frames))) / 60.0
                self._pulse_until[button] = max(
                    expiry, self._pulse_until.get(button, 0)
                )

    def set_manual(self, button, down):
        if button not in N64_BUTTONS:
            return
        with self._lock:
            if self._closed:
                return
            if down:
                self._manual.add(button)
            else:
                self._manual.discard(button)

    def release_camera(self):
        """Stop webcam pulses without releasing keys the person still holds."""
        with self._lock:
            self._pulse_until.clear()

    def release_manual(self):
        with self._lock:
            self._manual.clear()

    def flush(self):
        """Emit changed states, including a zero for every released control."""
        with self._lock:
            now = self.clock()
            for button, expiry in tuple(self._pulse_until.items()):
                if expiry <= now:
                    del self._pulse_until[button]
            next_state = desired_state(self._manual | self._pulse_until.keys())
            for key in sorted(set(self._sent) | set(next_state)):
                state = next_state.get(key, 0)
                if state == self._sent.get(key, 0):
                    continue
                data = encode_message(*key, state)
                self.socket.sendto(data, (LOCAL_HOST, self.port))
            self._sent = next_state

    def start(self):
        """Keep pulses responsive even when the GUI redraw is slow."""
        with self._lock:
            if self._worker is not None or self._closed:
                return
            self._worker = Thread(target=self._run, daemon=True, name="n64-camera-input")
            worker = self._worker
        worker.start()

    def _run(self):
        while not self._stop.wait(1 / 60):
            try:
                self.flush()
            except OSError:
                # RetroArch may be exiting while we release the controller.
                break

    def close(self):
        """Release all latched axes/buttons before closing the UDP socket."""
        self._stop.set()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=1)
        with self._lock:
            self._manual.clear()
            self._pulse_until.clear()
        try:
            self.flush()
        finally:
            with self._lock:
                self._closed = True
            if self._owns_socket:
                self.socket.close()
