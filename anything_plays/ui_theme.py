"""Apply the sixteen color palettes without rebuilding the application UI."""

import json
from tkinter import ttk


class ThemeMixin:
    """Tkinter behavior shared with the main application controller.

    These methods use widgets and state initialized by ``App.__init__``
    and ``LayoutMixin.build``. They are not standalone widgets.
    """

    THEMES = {
        # Original themes: unchanged for existing saved preferences.
        'Dark': ('#081425', '#10243e', '#e0ebff', '#5aa9ff', '#23456f', '#152f50'),
        'Light': ('#e9eef5', '#ffffff', '#17283d', '#195baf', '#d5e2f2', '#f2f6fc'),
        'Midnight': ('#090b16', '#161b2e', '#e6e9ff', '#a59bff', '#343459', '#222840'),
        'Retro': ('#18271d', '#253b2c', '#e5f2c9', '#b9ed75', '#446043', '#304b35'),
        # New dark variations.
        'Charcoal': ('#111315', '#1c2024', '#edf0f2', '#86c5d8', '#323b42', '#252c31'),
        'Slate': ('#151b25', '#222c39', '#edf3fb', '#93b7ed', '#384b60', '#2d394a'),
        'Ocean Dark': ('#071b25', '#102d3b', '#e6f7fa', '#55c9d9', '#205063', '#183b4b'),
        'Forest Dark': ('#101d18', '#1c3027', '#ecf5eb', '#90d6a1', '#345744', '#294337'),
        'Plum Dark': ('#211725', '#32253b', '#f8edf9', '#d4a0e8', '#554064', '#412e4d'),
        'Graphite': ('#141414', '#242424', '#f3f3f3', '#f0b86b', '#414141', '#303030'),
        # New light variations.
        'Soft White': ('#f3f5f7', '#ffffff', '#243142', '#487cae', '#dfe7ef', '#f8fafc'),
        'Warm Cream': ('#f2eadc', '#fffaf0', '#45392b', '#aa713c', '#e9d8bd', '#f8eedc'),
        'Ocean Light': ('#e0f1f4', '#f7fdff', '#193c4a', '#167d98', '#c5e5ec', '#e8f6fa'),
        'Sage Light': ('#e6efe6', '#f8fcf6', '#294438', '#4c8b68', '#d0e4d1', '#edf6ec'),
        'Lavender Light': ('#eee9f8', '#fcfaff', '#3b3151', '#8660b7', '#dfd3f1', '#f4effc'),
        'Rose Light': ('#f8eaf0', '#fffafd', '#523342', '#b36c8d', '#f0d6e1', '#fff0f5'),
    }

    def apply_dark_theme(self):
        """Legacy theme entry point kept for existing integrations.

        The unified palette engine now owns every theme, including the original
        dark one. This method is intentionally a compatibility-only alias.
        """
        self.apply_theme('Dark')

    def read_theme_preference(self):
        try:
            data = json.loads(self.preferences_path.read_text(encoding='utf-8'))
            value = data.get('theme', 'Dark')
            return value if value in self.THEMES else 'Dark'
        except (OSError, ValueError, TypeError):
            return 'Dark'

    def select_theme(self, *_):
        theme = self.theme_name.get()
        if theme not in self.THEMES:
            return
        self.apply_theme(theme)
        try:
            self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if self.preferences_path.exists():
                data = json.loads(self.preferences_path.read_text(encoding='utf-8'))
                if not isinstance(data, dict):
                    data = {}
            data['theme'] = theme
            self.preferences_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except (OSError, ValueError, TypeError):
            self.status.set('Theme applied, but could not save preference.')

    def apply_theme(self, name):
        outer, surface, text, accent, button, field = self.THEMES.get(name, self.THEMES['Dark'])
        self.root.configure(bg=outer)
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', background=surface, foreground=text, font=('DejaVu Sans', 11))
        style.configure('TFrame', background=surface)
        style.configure('TLabel', background=surface, foreground=text)
        # Intentional typographic hierarchy: section titles, readable values
        # and short helpers instead of dozens of indistinguishable labels.
        style.configure('Value.TLabel', background=surface, foreground=text,
                        font=('DejaVu Sans', 11, 'bold'))
        style.configure('Helper.TLabel', background=surface, foreground=text,
                        font=('DejaVu Sans', 10))
        style.configure('Primary.TCheckbutton', background=surface,
                        foreground=text, font=('DejaVu Sans', 11, 'bold'),
                        padding=(2, 5))
        style.map('Primary.TCheckbutton', background=[('active', surface)])
        style.configure('Title.TLabel', background=surface, foreground=text, font=('DejaVu Sans', 22, 'bold'))
        style.configure('Subtitle.TLabel', background=surface, foreground=text)
        style.configure('TLabelframe', background=surface, bordercolor=accent, relief='solid')
        style.configure('TLabelframe.Label', background=surface, foreground=accent, font=('DejaVu Sans', 11, 'bold'))
        for key, padding, font_size in [('TButton', (12, 9), 11), ('Compact.TButton', (9, 7), 10)]:
            style.configure(key, background=button, foreground=text, borderwidth=0, padding=padding,
                            font=('DejaVu Sans', font_size, 'bold'))
            style.map(key, background=[('active', accent)], foreground=[('disabled', text)])
        style.configure('Accent.TButton', background=accent, foreground=text)
        style.map('Accent.TButton', background=[('active', button)])
        style.configure('Danger.TButton', background='#a34d62', foreground='#ffffff')
        style.map('Danger.TButton', background=[('active', '#bd6275')])
        style.configure('TCombobox', fieldbackground=field, background=button, foreground=text, arrowcolor=text, padding=6)
        style.map('TCombobox', fieldbackground=[('readonly', field)], foreground=[('readonly', text)])
        style.configure('TSpinbox', fieldbackground=field, background=button, foreground=text)
        style.configure('TCheckbutton', background=surface, foreground=text)
        style.map('TCheckbutton', background=[('active', surface)])
        style.configure('TPanedwindow', background=outer)
        style.configure('Vertical.TScrollbar', background=button, troughcolor=surface, arrowcolor=text)
        self.root.option_add('*TCombobox*Listbox.background', field)
        self.root.option_add('*TCombobox*Listbox.foreground', text)
        for attr in ('library_canvas',):
            canvas = getattr(self, attr, None)
            if canvas is not None:
                canvas.configure(bg=surface)
        # Transparent cartridge corners should match the newly selected theme.
        grid = getattr(self, 'library_grid', None)
        if grid is not None:
            for tile in grid.winfo_children():
                for widget in tile.winfo_children():
                    if getattr(widget, 'is_cartridge_tile', False):
                        widget.configure(bg=surface)
        for attr in ('canvas', 'game_canvas'):
            canvas = getattr(self, attr, None)
            if canvas is not None:
                canvas.configure(bg=outer)
        # Chrome is composed of small native frames around the existing
        # display widgets; update its palette without touching video pixels.
        for attr in ('camera_bezel', 'game_bezel'):
            bezel = getattr(self, attr, None)
            if bezel is not None:
                bezel.apply_palette((outer, surface, text, accent, button, field))
        game = getattr(self, 'game_canvas', None)
        if game is not None:
            game.configure(highlightbackground=button, highlightcolor=accent)
        if hasattr(self, 'refresh_controller_artwork'):
            self.refresh_controller_artwork()
