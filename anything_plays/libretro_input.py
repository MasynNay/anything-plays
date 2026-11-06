"""Thread-safe, bounded game input without OS keyboard injection.

Camera presses are finite-duration pulses. Manual key presses remain held until
released and continue to work when object controls are disarmed.
"""

from queue import Empty, Full, Queue
from threading import Lock

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

    def id_for(self, button):
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
        with self.state_lock:
            self.remaining.clear()
            self.pressed.clear()
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
            # Drain a bounded command batch off-lock, then update the active
            # pulse state atomically. UI disarm can never corrupt iteration.
            commands = []
            for _ in range(8):
                try:
                    commands.append(self.commands.get_nowait())
                except Empty:
                    break
            with self.state_lock:
                for button_id, duration in commands:
                    self.remaining[button_id] = duration
                self.pressed.clear()
                self.pressed.update(self.remaining)
        with self.manual_lock:
            manual = {self.id_for(name) for name in self.manual_buttons}
        with self.state_lock:
            self.pressed.update(item for item in manual if item is not None)

    def after_frame(self):
        with self.state_lock:
            for button_id in tuple(self.remaining):
                self.remaining[button_id] -= 1
                if self.remaining[button_id] <= 0:
                    del self.remaining[button_id]

    def state(self, port, device, index, button_id):
        """Libretro callback: only player one's joypad is supported."""
        with self.state_lock:
            return int(port == 0 and device == 1 and button_id in self.pressed)
