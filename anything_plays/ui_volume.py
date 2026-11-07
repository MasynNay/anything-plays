"""Independent application-local game-audio controls for the 3.0 preview.

Keeping volume initialization and callbacks outside app.py preserves its
deliberate <250-line composition boundary and avoids UI/gameplay coupling.
"""
import tkinter as tk


class VolumeMixin:
    """Own the visible game-only volume and remembered mute state."""

    def initialize_game_volume(self, preferences):
        """Restore saved volume without ever changing OS master output."""
        saved_volume = preferences.get("volume", 35)
        if (type(saved_volume) not in (int, float)
                or not 0 <= saved_volume <= 100):
            saved_volume = 35
        self.volume_percent = tk.IntVar(value=int(saved_volume))
        self.volume_label = tk.StringVar(value=f"{int(saved_volume)}%")
        self.mute_button_text = tk.StringVar(
            value="Unmute" if int(saved_volume) == 0 else "Mute"
        )
        previous_audible = preferences.get("last_nonzero_volume", 35)
        if (type(previous_audible) not in (int, float)
                or not 1 <= previous_audible <= 100):
            previous_audible = 35
        self._volume_before_mute = (
            int(saved_volume) if saved_volume > 0 else int(previous_audible)
        )
        self.emu.set_volume(int(saved_volume) / 100.0)

    def set_game_volume(self, _value=None, *, save=False):
        """Update current Libretro PCM gain without altering system volume."""
        volume = max(0, min(100, int(self.volume_percent.get())))
        self.volume_label.set(f"{volume}%")
        self.mute_button_text.set("Unmute" if volume == 0 else "Mute")
        if volume:
            self._volume_before_mute = volume
        self.emu.set_volume(volume / 100.0)
        if save:
            self.save_preferences()

    def toggle_game_mute(self, event=None):
        """Instant mute/unmute, restoring the previous listening level."""
        if self.volume_percent.get():
            self._volume_before_mute = self.volume_percent.get()
            self.volume_percent.set(0)
        else:
            self.volume_percent.set(max(1, self._volume_before_mute))
        self.set_game_volume(save=True)
        return "break"
