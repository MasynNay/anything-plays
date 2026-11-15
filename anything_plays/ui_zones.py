"""Manage editable camera control zones and their visual overlays."""

import copy
import io
from pathlib import Path
import random
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import urllib.request

from PIL import Image
from anything_plays.zone_rendering import render_zone_overlay

from anything_plays.system_profiles import DISABLED_MAPPING, fit_to_grid
from anything_plays.zone_art_storage import save_cached_zone_art


class ZonesMixin:
    """Tkinter behavior shared with the main application controller.

    These methods use widgets and state initialized by ``App.__init__``
    and ``LayoutMixin.build``. They are not standalone widgets.
    """

    def set_zone_label_size(self, size):
        """Apply the camera label size without altering tracking geometry."""
        self.zone_font_size.set(max(8, min(160, int(size))))
        self.schedule_zone_label_size_save()

    def schedule_zone_label_size_save(self, _value=None):
        """Debounce profile writes while a user drags the preview slider."""
        previous = getattr(self, '_zone_label_save_job', None)
        if previous is not None:
            self.root.after_cancel(previous)
        self._zone_label_save_job = self.root.after(
            350, self.save_zone_label_size,
        )

    def save_zone_label_size(self):
        """Keep the chosen label size in the active console's profile."""
        self._zone_label_save_job = None
        if getattr(self, '_closing', False):
            return
        try:
            self.read_settings()
            self.profile_store.put(self.system_key.get(), self.cfg)
        except (OSError, ValueError, TypeError, tk.TclError):
            # A Tk timer callback must not crash the application if the
            # profile disk is unavailable. Keep the new slider value visible
            # so the player can retry saving it.
            self.status.set(
                'Zone label size was not saved. Check profile storage and retry.'
            )

    def choose_zone_art(self):
        path = filedialog.askopenfilename(title='Choose zone artwork',
                                          filetypes=[('PNG images', '*.png')])
        if path:
            self.zone_image_path.set(path)
            self.load_zone_art()

    def ask_zone_url(self):
        url = simpledialog.askstring('Zone image URL',
                                    'Paste a direct HTTPS link to a PNG image:')
        if not url:
            return
        if not url.startswith('https://'):
            messagebox.showerror('Image URL', 'Use a direct HTTPS PNG image URL.')
            return
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'AnythingPlays/2.0'})
            with urllib.request.urlopen(request, timeout=12) as response:
                data = response.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                raise ValueError('Image exceeds 5 MB')
            image = Image.open(io.BytesIO(data))
            if image.format != 'PNG':
                raise ValueError('The URL must point to a PNG image')
            image.thumbnail((1024, 1024))
            # Private 3.2 builds must never write into a stable/legacy
            # artwork cache. The new cache also commits complete PNG bytes
            # atomically and refuses linked preview destinations.
            cache = save_cached_zone_art(image, self.preferences_path)
            self.zone_image_path.set(str(cache))
            self.load_zone_art()
        except Exception as exc:
            messagebox.showerror('Image URL', f'Could not load image: {exc}')

    def load_zone_art(self, silent=False):
        self._zone_art = None
        self._zone_thumbnail_cache.clear()
        path = self.zone_image_path.get()
        if not path:
            return
        try:
            image = Image.open(path)
            if image.format != 'PNG':
                raise ValueError('Only PNG files are supported')
            image.thumbnail((1024, 1024))
            self._zone_art = image.convert('RGBA')
        except Exception as exc:
            if not silent:
                messagebox.showerror('Zone image', str(exc))

    def clear_zone_art(self):
        self.zone_image_path.set('')
        self._zone_art = None
        self._zone_thumbnail_cache.clear()

    def update_shuffle_visibility(self):
        """The checkbox controls whether the tracked Shuffle zone is active/visible."""
        self._shuffle_latched = False

    def toggle_custom_draw(self):
        self.drag_start = None
        self.status.set('Custom zone drawing enabled: drag on the camera preview.'
                        if self.custom_draw_enabled.get()
                        else 'Custom drawing disabled. Symmetrical zones remain active.')

    def make_symmetric_grid(self):
        """Save the active console's fitted grid before showing it as applied."""
        original = copy.deepcopy(self.cfg)
        system = self.system_key.get()
        try:
            self.read_settings()
            candidate = copy.deepcopy(self.cfg)
            fit_to_grid(candidate, system)
            self.profile_store.put(system, candidate)
        except (OSError, ValueError, TypeError, tk.TclError):
            self.cfg = original
            self.status.set(
                'Grid changes were not saved. Previous control zones are kept; '
                'check profile storage and retry.'
            )
            return False
        self.cfg = candidate
        self._shuffle_latched = False
        self.status.set(
            'Enabled buttons and Shuffle snapped to an even grid.'
            if self.shuffle_enabled.get() else
            'Enabled buttons snapped to an even grid; hidden Shuffle preserved.'
        )
        return True

    def shuffle_zones(self):
        """Shuffle every visible control, including the camera-triggered Shuffle zone."""
        names = [name for name in self.cfg['zones']
                 if (name != 'Shuffle' or self.shuffle_enabled.get())
                 and (name == 'Shuffle' or self.mapping_vars[name].get() != DISABLED_MAPPING)]
        positions = [self.cfg['zones'][name][:] for name in names]
        if len(positions) < 2:
            return
        original = positions[:]
        for _ in range(12):
            random.shuffle(positions)
            if positions != original:
                break
        for name, position in zip(names, positions):
            self.cfg['zones'][name] = position
        self.status.set('All visible control zones shuffled, including Shuffle.')

    def render_zones(self, frame, active):
        """Render the current control layout without mutating the camera image."""
        mapping = {name: var.get() for name, var in self.mapping_vars.items()}
        return render_zone_overlay(
            frame, self.cfg['zones'], mapping, active,
            opacity=self.zone_opacity.get(),
            size=self.zone_font_size.get(),
            style=self.zone_style.get(),
            border_width=self.zone_border_width.get(),
            label_position=self.zone_label_position.get(),
            artwork=self._zone_art,
            shuffle_enabled=self.shuffle_enabled.get(),
            artwork_cache=self._zone_thumbnail_cache,
        )
