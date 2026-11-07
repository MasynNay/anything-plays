"""Thread-safe, bounded game input without OS keyboard injection.

Camera presses are finite-duration pulses. Manual key presses remain held until
released and continue to work when object controls are disarmed.
"""

from queue import Empty, Full, Queue
from threading import Lock

from anything_plays.remote_retropad import N64_AXES, N64_DIGITAL, desired_state
from anything_plays.gamecube_software import GAMECUBE_INPUT, gamecube_state

BUTTONS = ("Up", "Down", "Left", "Right", "A", "B", "Start", "Select",
           "X", "Y", "L", "R")

# These indices are defined by RETRO_DEVICE_ID_JOYPAD_* in libretro.h.
IDS = {
    "B": 0, "Y": 1, "Select": 2, "Start": 3,
    "Up": 4, "Down": 5, "Left": 6, "Right": 7,
    "A": 8, "X": 9, "L": 10, "R": 11,
}


# Sega six-button joypad uses a different RetroPad label mapping. The libretro
# numeric IDs follow the official Genesis Plus GX controls table.
GENESIS_IDS = {
    **{name: IDS[name] for name in ("Up", "Down", "Left", "Right", "B", "Start")},
    "A": IDS["Y"], "C": IDS["A"],
    "X": IDS["L"], "Y": IDS["X"], "Z": IDS["R"], "Mode": IDS["Select"],
}


# Name -> stable identity, so the existing frame-pulse buffer can hold
# both N64 digital buttons and analog stick directions without changing
# other consoles' controller IDs.
N64_INPUT = {
    **{button: ("joypad", number) for button, number in N64_DIGITAL.items()},
    **{button: ("analog", index, axis, value)
       for button, (index, axis, value) in N64_AXES.items()},
}


class InputBuffer:
    """Combine camera pulses with manually held buttons for one emulator frame."""

    def __init__(self):
        self.system = "gba"
        self.commands = Queue(maxsize=32)
        self.manual_buttons = set()
        self.manual_lock = Lock()
        # The Tk thread can disarm while the Libretro worker advances a frame.
        self.state_lock = Lock()
        self.remaining = {}
        self.pressed = set()
        # N64 and GameCube may request dozens of analogue states per
        # emulated frame. Cache the complete 3D controller snapshot once.
        self._n64_state = {}

    def id_for(self, button):
        if self.system == "n64":
            return N64_INPUT.get(button)
        if self.system == "gamecube":
            return GAMECUBE_INPUT.get(button)
        return (GENESIS_IDS if self.system == "genesis" else IDS).get(button)

    def queue_press(self, button, frames):
        """Enqueue one camera button pulse, dropping events if already saturated."""
        button_id = self.id_for(button)
        if button_id is None:
            return
        duration = max(1, min(60, int(frames)))
        try:
            self.commands.put_nowait((button_id, duration))
        except Full:
            pass

    def set_manual(self, button, down):
        if self.id_for(button) is None:
            return
        with self.manual_lock:
            if down:
                self.manual_buttons.add(button)
            else:
                self.manual_buttons.discard(button)

    def release_manual(self):
        with self.manual_lock:
            self.manual_buttons.clear()

    def disarm(self):
        # Clear queued presses under the same lock as before_frame: a pending
        # camera command cannot be applied AFTER the user presses Stop.
        with self.state_lock:
            self.remaining.clear()
            self.pressed.clear()
            self._n64_state.clear()
            while True:
                try:
                    self.commands.get_nowait()
                except Empty:
                    break

    def before_frame(self, armed):
        """Update pressed IDs before a ``retro_run()`` invocation."""
        if not armed:
            self.disarm()
        else:
            # Keep command consumption atomic with the emergency stop.
            with self.state_lock:
                for _ in range(8):
                    try:
                        button_id, duration = self.commands.get_nowait()
                    except Empty:
                        break
                    self.remaining[button_id] = duration
                self.pressed.clear()
                self.pressed.update(self.remaining)
        with self.manual_lock:
            manual = {self.id_for(name) for name in self.manual_buttons}
        with self.state_lock:
            self.pressed.update(item for item in manual if item is not None)
            if self.system == "n64":
                active = (
                    button for button, identity in N64_INPUT.items()
                    if identity in self.pressed
                )
                self._n64_state = desired_state(active)
            elif self.system == "gamecube":
                active = (
                    button for button, identity in GAMECUBE_INPUT.items()
                    if identity in self.pressed
                )
                self._n64_state = gamecube_state(active)
            else:
                self._n64_state.clear()

    def after_frame(self):
        with self.state_lock:
            for button_id in tuple(self.remaining):
                self.remaining[button_id] -= 1
                if self.remaining[button_id] <= 0:
                    del self.remaining[button_id]

    def state(self, port, device, index, button_id):
        """Libretro callback: player-one digital and N64/GameCube analog input."""
        if port != 0:
            return 0
        with self.state_lock:
            if self.system not in ("n64", "gamecube"):
                return int(device == 1 and button_id in self.pressed)
            return self._n64_state.get((device, index, button_id), 0)
