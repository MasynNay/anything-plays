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


# Beetle NeoPop labels physical Pocket button A as RetroPad B (ID 0), and
# physical Pocket button B as RetroPad A (ID 8). Unlike the generic
# Game Boy layout, keeping the default IDs would swap both buttons in
# manual keyboard controls AND the camera-driven fish commands.
NEO_GEO_POCKET_IDS = {
    **{name: IDS[name] for name in ("Up", "Down", "Left", "Right", "Start")},
    "A": IDS["B"],
    "B": IDS["A"],
}


# Name -> stable identity, so the existing frame-pulse buffer can hold
# both N64 digital buttons and analog stick directions without changing
# other consoles' controller IDs.
N64_INPUT = {
    **{button: ("joypad", number) for button, number in N64_DIGITAL.items()},
    **{button: ("analog", index, axis, value)
       for button, (index, axis, value) in N64_AXES.items()},
}

# Only consoles with a supported second controller port are presented as
# two-player options. Individual games still need their own co-op support.
TWO_PLAYER_SYSTEMS = frozenset((
    "nes", "snes", "genesis", "mastersystem", "sg1000",
    "atari2600", "atari7800", "pce", "n64", "gamecube",
))


class InputBuffer:
    """Combine camera pulses with manually held buttons for one emulator frame."""

    def __init__(self):
        self.system = "gba"
        self.commands = Queue(maxsize=32)
        self.manual_buttons = set()
        self.manual_lock = Lock()
        # The Tk thread can disarm while the Libretro worker advances a frame.
        self.state_lock = Lock()
        self.remaining = {}  # Existing player-one camera pulses.
        self.remaining_p2 = {}
        self.pressed = set()
        self.pressed_p2 = set()
        # Every camera tick provides both players' *complete* held-button
        # snapshots. Two fish in two zones are pressed in the SAME emulated
        # frame; missing fish are released on the next camera update.
        self._camera_held = {0: set(), 1: set()}
        # N64 and GameCube may poll many analogue inputs per frame. Cache
        # each port's full state exactly once per emulation step.
        self._n64_state = {}
        self._p2_analog = {}

    def id_for(self, button):
        if self.system == "n64":
            return N64_INPUT.get(button)
        if self.system == "gamecube":
            return GAMECUBE_INPUT.get(button)
        if self.system in ("ngp", "ngpc"):
            return NEO_GEO_POCKET_IDS.get(button)
        return (GENESIS_IDS if self.system == "genesis" else IDS).get(button)

    def queue_press(self, button, frames, port=0):
        """Queue bounded camera pulses; simultaneous presses support P1/P2."""
        button_id = self.id_for(button)
        if button_id is None or port not in (0, 1):
            return
        duration = max(1, min(60, int(frames)))
        try:
            # Preserve the existing two-item queue format for player one.
            self.commands.put_nowait(
                (button_id, duration) if port == 0
                else (button_id, duration, 1)
            )
        except Full:
            pass

    def set_camera_buttons(self, player_one=(), player_two=()):
        """Set the latest held buttons from all tracked fish, atomically."""
        one = {identity for button in tuple(player_one)[:32]
               if (identity := self.id_for(button)) is not None}
        two = {identity for button in tuple(player_two)[:32]
               if (identity := self.id_for(button)) is not None}
        with self.state_lock:
            self._camera_held[0] = one
            self._camera_held[1] = two

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
            self.remaining_p2.clear()
            self.pressed.clear()
            self.pressed_p2.clear()
            self._camera_held[0].clear()
            self._camera_held[1].clear()
            self._n64_state.clear()
            self._p2_analog.clear()
            while True:
                try:
                    self.commands.get_nowait()
                except Empty:
                    break

    def before_frame(self, armed):
        """Snapshot both players' controls before each native retro_run()."""
        if not armed:
            self.disarm()
        else:
            with self.state_lock:
                for _ in range(8):
                    try:
                        item = self.commands.get_nowait()
                    except Empty:
                        break
                    button_id, duration = item[:2]
                    port = item[2] if len(item) == 3 else 0
                    remaining = self.remaining if port == 0 else self.remaining_p2
                    remaining[button_id] = duration
                self.pressed.clear()
                self.pressed.update(self.remaining)
                self.pressed.update(self._camera_held[0])
                self.pressed_p2.clear()
                self.pressed_p2.update(self.remaining_p2)
                self.pressed_p2.update(self._camera_held[1])
        with self.manual_lock:
            manual = {self.id_for(name) for name in self.manual_buttons}
        with self.state_lock:
            self.pressed.update(item for item in manual if item is not None)
            if self.system in ("n64", "gamecube"):
                mapping = N64_INPUT if self.system == "n64" else GAMECUBE_INPUT
                decoder = desired_state if self.system == "n64" else gamecube_state
                active_one = (
                    name for name, identity in mapping.items()
                    if identity in self.pressed
                )
                self._n64_state = decoder(active_one)
                if self.pressed_p2:
                    active_two = (
                        name for name, identity in mapping.items()
                        if identity in self.pressed_p2
                    )
                    self._p2_analog = decoder(active_two)
                else:
                    self._p2_analog.clear()
            else:
                self._n64_state.clear()
                self._p2_analog.clear()

    def after_frame(self):
        with self.state_lock:
            for remaining in (self.remaining, self.remaining_p2):
                for button_id in tuple(remaining):
                    remaining[button_id] -= 1
                    if remaining[button_id] <= 0:
                        del remaining[button_id]

    def state(self, port, device, index, button_id):
        """Native callback: independent digital and analogue P1/P2 states."""
        if port not in (0, 1):
            return 0
        with self.state_lock:
            if self.system not in ("n64", "gamecube"):
                buttons = self.pressed if port == 0 else self.pressed_p2
                return int(device == 1 and button_id in buttons)
            data = self._n64_state if port == 0 else self._p2_analog
            return data.get((device, index, button_id), 0)
