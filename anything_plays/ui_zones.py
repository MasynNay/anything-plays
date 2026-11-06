"""Manage editable camera control zones and their visual overlays."""

import io
from pathlib import Path
import random
from tkinter import filedialog, messagebox, simpledialog
import urllib.request

from PIL import Image
from anything_plays.zone_rendering import render_zone_overlay

from anything_plays.system_profiles import DISABLED_MAPPING, fit_to_grid


class ZonesMixin:
    """Tkinter behavior shared with the main application controller.

    These methods use widgets and state initialized by ``App.__init__``
    and ``LayoutMixin.build``. They are not standalone widgets.
    """

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
            cache = Path.home() / '.config' / 'anything-plays' / 'zone-art.png'
            cache.parent.mkdir(parents=True, exist_ok=True)
            image.save(cache)
            self.zone_image_path.set(str(cache))
            self.load_zone_art()
        except Exception as exc:
            messagebox.showerror('Image URL', f'Could not load image: {exc}')

    def load_zone_art(self, silent=False):
        self._zone_art = None
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

    def update_shuffle_visibility(self):
        """The checkbox controls whether the tracked Shuffle zone is active/visible."""
        self._shuffle_latched = False

    def toggle_custom_draw(self):
        self.drag_start = None
        self.status.set('Custom zone drawing enabled: drag on the camera preview.'
                        if self.custom_draw_enabled.get()
                        else 'Custom drawing disabled. Symmetrical zones remain active.')

    def make_symmetric_grid(self):
        """Reset only the active console's controls to an even grid."""
        self.read_settings()
        fit_to_grid(self.cfg, self.system_key.get())
        self._shuffle_latched = False
        self.profile_store.put(self.system_key.get(), self.cfg)
        self.status.set('Enabled buttons fitted to an even grid for this console.')

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
        )
