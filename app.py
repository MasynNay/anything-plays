"""Anything Plays — cross-platform object tracking and embedded GBA gameplay."""
import io
import json
import random
import sys
import threading
import time
import urllib.request
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, colorchooser

import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
from cameras import discover
from gba_emulator import Emulator, BUTTONS
from systems import SYSTEMS, DEFAULT_SYSTEM
from system_profiles import ProfileStore, BUTTONS_BY_SYSTEM, normalize, default_for, enabled_zones, fit_to_grid, DISABLED_MAPPING

DEFAULT = {
    'rgb': [255, 0, 0], 'tolerance': 20, 'min_area': 120,
    'hold_frames': 8, 'cooldown_ms': 450, 'mirror': False,
    'zone_font_size': 44, 'zone_opacity': 85, 'zone_style': 'Outline',
    'zone_image': '', 'shuffle_enabled': True,
    'zones': {
        'Left': [0.00000000, 0.00000000, 0.33333333, 0.33333333],
        'Up': [0.33333333, 0.00000000, 0.66666667, 0.33333333],
        'Right': [0.66666667, 0.00000000, 1.00000000, 0.33333333],
        'A': [0.00000000, 0.33333333, 0.33333333, 0.66666667],
        'Start': [0.33333333, 0.33333333, 0.66666667, 0.66666667],
        'B': [0.66666667, 0.33333333, 1.00000000, 0.66666667],
        'Down': [0.00000000, 0.66666667, 0.33333333, 1.00000000],
        'Select': [0.33333333, 0.66666667, 0.66666667, 1.00000000],
        'Shuffle': [0.66666667, 0.66666667, 1.00000000, 1.00000000],
    },
    'mapping': {name: name for name in BUTTONS}
}

ACTIVE_BUTTONS = tuple(BUTTONS)


class App:
    def __init__(self, root):
        self.root = root
        root.title('Anything Plays')
        self.set_app_icon()
        self.apply_dark_theme()
        root.geometry('1400x880')
        root.minsize(820, 540)
        self.cfg = json.loads(json.dumps(DEFAULT))
        self.cap = None
        self.frame = None
        self.reference_image = False
        self.camera_options = {}
        self.camera_scanning = False
        self.pick_mode = False
        self.drag_start = None
        self.custom_draw_enabled = tk.BooleanVar(value=False)
        self.camera_photo = None
        self.game_photo = None
        self.manual_active = False
        self.last_action = 0
        self._shuffle_latched = False
        self.armed = False
        self.emu = Emulator()
        self.preferences_path = Path.home() / '.config' / 'fish-plays-pokemon-studio' / 'preferences.json'  # Preserve existing settings on upgrade
        self.profile_store = ProfileStore(self.preferences_path.with_name('system_profiles.json'), DEFAULT)
        self.theme_name = tk.StringVar(value=self.read_theme_preference())
        self.apply_theme(self.theme_name.get())
        self.system_key = tk.StringVar(value=self.read_selected_system())
        self.rom_directories = self.read_rom_directories()
        self.rom_directory = self.rom_directories.get(self.system_key.get(), '')
        self.emu.system = self.system_key.get()
        self.emu.core_path = self.emu.find_system_core()
        self.library_window = None
        self.shelf_drag = None
        self.shelf_momentum_job = None
        self.shelf_velocity = 0.0
        self.shelf_button_job = None
        self.shelf_button_direction = 0
        self.shelf_animation_job = None
        self.shelf_animation_target = None
        self.library_images = []
        self.current_rom = None
        self.status = tk.StringVar(value='Searching for cameras…')
        self.action = tk.StringVar(value='PREVIEW ONLY — no keyboard events are sent')
        self.game_status = tk.StringVar(value='Load your own game ROM')
        self.camera_name = tk.StringVar()
        self.zone_name = tk.StringVar(value='Up')
        self.color_text = tk.StringVar()
        self.mapping_vars = {}
        self.zone_font_size = tk.IntVar(value=44)
        self.zone_opacity = tk.IntVar(value=85)
        self.zone_style = tk.StringVar(value='Outline')
        self.shuffle_enabled = tk.BooleanVar(value=True)
        self.zone_image_path = tk.StringVar(value='')
        self._zone_art = None
        self.cfg = self.profile_store.get(self.system_key.get())
        self.build()
        self.refresh_settings()
        self.refresh_system_buttons()
        self._active_profile_system = self.system_key.get()
        root.bind('<Control-Alt-F11>', lambda _: self.toggle())
        root.bind('<Control-Alt-F12>', lambda _: self.stop_controls())
        root.bind('<Escape>', lambda _: self.stop_controls())
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.scan_cameras)
        root.after(45, self.tick)

    def set_app_icon(self):
        """Use the same branded icon for source and frozen applications."""
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        icon = base / 'assets' / 'anything_plays.png'
        if icon.is_file():
            try:
                self._app_icon = tk.PhotoImage(file=str(icon))
                self.root.iconphoto(True, self._app_icon)
            except tk.TclError:
                pass

    def apply_dark_theme(self):
        self.root.configure(bg='#081425')
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', background='#10243e', foreground='#eaf8f7', font=('DejaVu Sans', 10))
        style.configure('TFrame', background='#10243e')
        style.configure('TLabel', background='#10243e', foreground='#e0ebff')
        style.configure('Title.TLabel', font=('DejaVu Sans', 22, 'bold'), foreground='#f4f8ff')
        style.configure('Subtitle.TLabel', foreground='#b2c9e7', font=('DejaVu Sans', 10))
        style.configure('TLabelframe', background='#10243e', bordercolor='#385c89', relief='solid')
        style.configure('TLabelframe.Label', background='#10243e', foreground='#5aa9ff', font=('DejaVu Sans', 11, 'bold'))
        style.configure('TButton', background='#23456f', foreground='#f4f8ff', borderwidth=0, padding=(12, 9), font=('DejaVu Sans', 10, 'bold'))
        style.map('TButton', background=[('active','#3566a2'), ('disabled','#182d49')], foreground=[('disabled','#8a9fbc')])
        style.configure('Compact.TButton', background='#23456f', foreground='#f4f8ff', borderwidth=0, padding=(7, 6), font=('DejaVu Sans', 9, 'bold'))
        style.map('Compact.TButton', background=[('active','#3566a2')])
        style.configure('Accent.TButton', background='#2569bd', foreground='#ffffff')
        style.map('Accent.TButton', background=[('active','#3d8ee2')])
        style.configure('Danger.TButton', background='#a34d62', foreground='#ffffff')
        style.map('Danger.TButton', background=[('active','#bd6275')])
        style.configure('TCombobox', fieldbackground='#152f50', background='#29517d', foreground='#f4f8ff', arrowcolor='#d9e9ff', padding=6)
        style.map('TCombobox', fieldbackground=[('readonly','#152f50')], foreground=[('readonly','#f4f8ff')])
        style.configure('TSpinbox', fieldbackground='#152f50', background='#29517d', foreground='#f4f8ff', arrowcolor='#d9e9ff')
        style.configure('TCheckbutton', background='#10243e', foreground='#e0ebff')
        style.map('TCheckbutton', background=[('active','#10243e')])
        style.configure('TPanedwindow', background='#081425')
        style.configure('Vertical.TScrollbar', background='#2c507b', troughcolor='#10243e', arrowcolor='#d9e9ff')
        self.root.option_add('*TCombobox*Listbox.background', '#152f50')
        self.root.option_add('*TCombobox*Listbox.foreground', '#f4f8ff')

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
        style.configure('.', background=surface, foreground=text, font=('DejaVu Sans', 10))
        style.configure('TFrame', background=surface)
        style.configure('TLabel', background=surface, foreground=text)
        style.configure('Title.TLabel', background=surface, foreground=text, font=('DejaVu Sans', 22, 'bold'))
        style.configure('Subtitle.TLabel', background=surface, foreground=text)
        style.configure('TLabelframe', background=surface, bordercolor=accent, relief='solid')
        style.configure('TLabelframe.Label', background=surface, foreground=accent, font=('DejaVu Sans', 11, 'bold'))
        for key, padding, font_size in [('TButton', (12, 9), 10), ('Compact.TButton', (7, 6), 9)]:
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

    def build(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill='both', expand=True)
        ttk.Label(main, text='Anything Plays', style='Title.TLabel').pack(anchor='w')
        theme_row = ttk.Frame(main)
        theme_row.pack(anchor='e', pady=(0, 5))
        ttk.Label(theme_row, text='Theme:').pack(side='left', padx=(0, 6))
        ttk.Combobox(theme_row, textvariable=self.theme_name, state='readonly',
                     values=list(self.THEMES), width=17).pack(side='left')
        self.theme_name.trace_add('write', self.select_theme)
        ttk.Label(main, text='A little world where movement becomes play  •  Camera tracking  •  Game Boy Advance', style='Subtitle.TLabel').pack(anchor='w', pady=(2, 16))
        body = ttk.Panedwindow(main, orient='horizontal')
        body.pack(fill='both', expand=True)
        # Each pane scrolls independently. Large controls never get clipped by
        # short displays, high DPI scaling, or macOS menu/dock space.
        left_host = ttk.Frame(body)
        right_host = ttk.Frame(body)
        body.add(left_host, weight=3)
        body.add(right_host, weight=3)
        left = self.make_scrollable_pane(left_host)
        right = self.make_scrollable_pane(right_host)

        cameras = ttk.LabelFrame(left, text='01   CAMERA  ·  Your window into the tank', padding=8)
        cameras.pack(fill='x')
        # Keep camera selection compact. Buttons live in their own responsive
        # row so a long device name cannot squeeze Stop off the screen.
        selector_row = ttk.Frame(cameras)
        selector_row.pack(fill='x')
        ttk.Label(selector_row, text='Camera').pack(side='left', padx=(0, 8))
        self.camera_combo = ttk.Combobox(selector_row, textvariable=self.camera_name,
                                         state='readonly', width=22)
        self.camera_combo.pack(side='left', fill='x', expand=True)
        camera_actions = ttk.Frame(cameras)
        camera_actions.pack(fill='x', pady=(6, 0))
        for column in range(3):
            camera_actions.columnconfigure(column, weight=1, uniform='camera_actions')
        ttk.Button(camera_actions, text='Refresh', command=self.scan_cameras,
                   style='Compact.TButton').grid(row=0, column=0, sticky='ew', padx=(0, 3))
        ttk.Button(camera_actions, text='Use camera', command=self.start_camera,
                   style='Compact.TButton').grid(row=0, column=1, sticky='ew', padx=3)
        ttk.Button(camera_actions, text='Stop', command=self.stop_camera,
                   style='Compact.TButton').grid(row=0, column=2, sticky='ew', padx=(3, 0))

        self.canvas = tk.Canvas(left, bg='#0a1a30', highlightthickness=0, height=440)
        self.canvas.pack(fill='both', expand=True, pady=(8, 4))
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.shuffle_enabled.trace_add('write', lambda *_: self.update_shuffle_visibility())
        ttk.Label(left, textvariable=self.status).pack(anchor='w')
        ttk.Label(left, textvariable=self.action, font=('DejaVu Sans', 11, 'bold')).pack(anchor='w', pady=4)

        game = ttk.LabelFrame(right, text='02   GAME  ·  Your play space', padding=10)
        game.pack(fill='x', padx=(14, 0), pady=(0, 10))
        system_row = ttk.Frame(game)
        system_row.pack(fill='x', pady=(0, 6))
        ttk.Label(system_row, text='Choose emulator:').pack(side='left', padx=(0, 6))
        self.system_combo = ttk.Combobox(system_row, textvariable=self.system_key, state='readonly',
                                         values=list(SYSTEMS), width=12)
        self.system_combo.pack(side='left')
        self.system_combo.bind('<<ComboboxSelected>>', self.switch_system)
        self.system_description = ttk.Label(system_row, text=SYSTEMS[self.system_key.get()].title)
        self.system_description.pack(side='left', padx=8)
        # Separate, permanently visible actions. Rescan must never replace Browse.
        rom_actions = ttk.Frame(game)
        rom_actions.pack(fill='x', pady=(0, 5))
        rom_actions.columnconfigure(0, weight=1)
        rom_actions.columnconfigure(1, weight=1)
        ttk.Button(rom_actions, text='Browse ROM Folder', command=self.set_rom_directory,
                   style='Accent.TButton').grid(row=0, column=0, sticky='ew', padx=(0, 4))
        ttk.Button(rom_actions, text='Refresh ROM Library', command=self.populate_inline_library).grid(
            row=0, column=1, sticky='ew', padx=(4, 0))
        ttk.Button(game, text='Open game ROM', command=self.load_rom).pack(fill='x', pady=(5, 0))
        # Emulator cores are bundled; no manual core selection required.
        self.game_canvas = tk.Canvas(game, bg='#0a1a30', height=350, highlightthickness=0)
        self.game_canvas.pack(fill='both', expand=True, pady=10)
        self.game_canvas.configure(takefocus=1, highlightthickness=2, highlightbackground='#23456f', highlightcolor='#5aa9ff')
        self.game_canvas.bind('<Button-1>', self.activate_manual)
        self.game_canvas.bind('<KeyPress>', self.manual_key_down)
        self.game_canvas.bind('<KeyRelease>', self.manual_key_up)
        self.game_canvas.bind('<FocusOut>', self.deactivate_manual)
        self.root.bind_all('<Button-1>', self.deactivate_on_outside_click, add='+')
        self.manual_label = tk.StringVar(value='Click the game screen to play manually · Arrows = D-pad · Z = A · X = B · Enter = Start')
        self.below_game = ttk.Frame(game)
        self.below_game.pack(fill='x', pady=(0, 6))
        self.library_strip = ttk.Frame(self.below_game)
        self.library_strip.pack(fill='x')
        library_header = ttk.Frame(self.library_strip)
        library_header.pack(fill='x', pady=(0, 5))
        self.library_summary = tk.StringVar(value='ROM LIBRARY · Choose a ROM folder to begin')
        # Navigation gets a dedicated row: shrinking the game pane must never
        # hide or crush Previous / Next behind the library status text.
        ttk.Label(library_header, textvariable=self.library_summary).pack(fill='x')
        shelf_actions = ttk.Frame(self.library_strip)
        shelf_actions.pack(fill='x', pady=(0, 6))
        shelf_actions.columnconfigure(0, weight=1, uniform='shelf_actions')
        shelf_actions.columnconfigure(1, weight=1, uniform='shelf_actions')
        self.shelf_prev = ttk.Button(shelf_actions, text='◀  Previous', style='Compact.TButton')
        self.shelf_next = ttk.Button(shelf_actions, text='Next  ▶', style='Compact.TButton')
        self.shelf_prev.grid(row=0, column=0, sticky='ew', padx=(0, 3))
        self.shelf_next.grid(row=0, column=1, sticky='ew', padx=(3, 0))
        for button, direction in ((self.shelf_prev, -1), (self.shelf_next, 1)):
            button.bind('<ButtonPress-1>', lambda e, d=direction: self.shelf_button_press(d))
            button.bind('<ButtonRelease-1>', self.shelf_button_release)
            button.bind('<Leave>', self.shelf_button_release)
        self.library_canvas = tk.Canvas(self.library_strip, bg='#10243e', height=155, highlightthickness=0)
        self.library_canvas.pack(fill='x', expand=True)
        self.library_grid = ttk.Frame(self.library_canvas)
        self.library_canvas.create_window((0, 0), window=self.library_grid, anchor='nw')
        self.library_grid.bind('<Configure>', lambda e: self.library_canvas.configure(scrollregion=self.library_canvas.bbox('all')))
        self.root.bind_all('<B1-Motion>', self.shelf_motion, add='+')
        self.root.bind_all('<ButtonRelease-1>', self.shelf_release, add='+')
        self.playing_info = ttk.Frame(self.below_game)
        self.playing_row = ttk.Frame(self.playing_info)
        self.playing_row.pack(fill='x')
        ttk.Label(self.playing_row, textvariable=self.manual_label, wraplength=345).pack(side='left', fill='x', expand=True)
        ttk.Button(self.playing_row, text='Unload ROM', command=self.unload_rom, style='Danger.TButton').pack(side='right', padx=(8, 0))
        ttk.Label(self.playing_info, textvariable=self.game_status, wraplength=470).pack(anchor='w', pady=(4, 0))
        ttk.Label(game, text='Embedded libretro · No system-wide keyboard injection', wraplength=470).pack(anchor='w', pady=5)
        self.populate_inline_library()

        fish = ttk.LabelFrame(right, text='3  Object tracking and control zones', padding=10)
        fish.pack(fill='x', padx=(12, 0), pady=(0, 8))
        buttons = ttk.Frame(fish)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='Pick color from video', command=self.pick_color).pack(side='left')
        ttk.Button(buttons, text='Pick from image', command=self.pick_image).pack(side='left', padx=4)
        ttk.Button(buttons, text='Choose color', command=self.choose_color).pack(side='left')
        ttk.Label(fish, textvariable=self.color_text).pack(anchor='w', pady=4)
        self.tolerance = tk.IntVar()
        self.min_area = tk.IntVar()
        self.hold_frames = tk.IntVar()
        self.cooldown = tk.IntVar()
        self.mirror = tk.BooleanVar()
        for label, variable, lo, hi in [
            ('Color tolerance', self.tolerance, 1, 90),
            ('Minimum detection area', self.min_area, 5, 50000),
            ('Button hold (frames at 60 FPS)', self.hold_frames, 1, 60),
            ('Cooldown (milliseconds)', self.cooldown, 50, 10000),
        ]:
            row = ttk.Frame(fish)
            row.pack(fill='x', pady=2)
            ttk.Label(row, text=label).pack(side='left')
            ttk.Spinbox(row, textvariable=variable, from_=lo, to=hi, width=8).pack(side='right')
        # Overlay appearance controls work on all platforms; these settings
        # affect the camera preview only, not emulator input detection.
        appearance = ttk.LabelFrame(fish, text='Zone appearance', padding=7)
        appearance.pack(fill='x', pady=(8, 5))
        ttk.Label(appearance, text='Label size (8–160 px)').pack(anchor='w')
        font_row = ttk.Frame(appearance)
        font_row.pack(fill='x')
        ttk.Scale(font_row, from_=8, to=160, variable=self.zone_font_size,
                  orient='horizontal').pack(side='left', fill='x', expand=True)
        ttk.Spinbox(font_row, from_=8, to=160, increment=1, width=5,
                    textvariable=self.zone_font_size).pack(side='right', padx=(8, 0))
        ttk.Label(appearance, text='Overlay tint strength (75 subtle → 100 bold)').pack(anchor='w')
        ttk.Scale(appearance, from_=75, to=100, variable=self.zone_opacity,
                  orient='horizontal').pack(fill='x')
        ttk.Label(appearance, text='High contrast: tinted zones + labels; Outline: clear video + borders; Minimal: labels only.', wraplength=360).pack(anchor='w', pady=(4, 2))
        ttk.Combobox(appearance, textvariable=self.zone_style, state='readonly',
                     values=['High contrast', 'Outline', 'Minimal'], width=18).pack(fill='x', pady=4)
        art_row = ttk.Frame(appearance)
        art_row.pack(fill='x', pady=3)
        ttk.Button(art_row, text='Upload PNG', command=self.choose_zone_art,
                   style='Compact.TButton').pack(side='left', padx=(0, 5))
        ttk.Button(art_row, text='Image URL', command=self.ask_zone_url,
                   style='Compact.TButton').pack(side='left', padx=(0, 5))
        ttk.Button(art_row, text='Clear image', command=self.clear_zone_art,
                   style='Compact.TButton').pack(side='left')
        ttk.Label(appearance, text='PNG image is shown inside each control zone.',
                  wraplength=350).pack(anchor='w')
        shuffle_row = ttk.Frame(appearance)
        shuffle_row.pack(fill='x', pady=(7, 0))
        ttk.Checkbutton(shuffle_row, text='Enable camera-tracked Shuffle zone',
                        variable=self.shuffle_enabled).pack(side='left')
        ttk.Button(shuffle_row, text='Shuffle now', command=self.shuffle_zones,
                   style='Compact.TButton').pack(side='right')
        ttk.Button(fish, text='Fit buttons to grid', command=self.make_symmetric_grid,
                   style='Accent.TButton').pack(fill='x', pady=(7, 3))
        ttk.Label(fish, text='Equal-size grid cells for this console. Custom drawing is optional.',
                  wraplength=420).pack(anchor='w')
        ttk.Checkbutton(fish, text='Mirror camera', variable=self.mirror).pack(anchor='w')
        ttk.Checkbutton(fish, text='Enable custom zone drawing', variable=self.custom_draw_enabled,
                        command=self.toggle_custom_draw).pack(anchor='w', pady=(7, 0))
        ttk.Label(fish, text='Zone to redraw (only when custom drawing is enabled):').pack(anchor='w')
        self.zone_combo = ttk.Combobox(fish, textvariable=self.zone_name, values=list(ACTIVE_BUTTONS) + ['Shuffle'], state='readonly')
        self.zone_combo.pack(fill='x')
        mapping = ttk.Frame(fish)
        mapping.pack(fill='x', pady=5)
        for i, name in enumerate(ACTIVE_BUTTONS):
            label = ttk.Label(mapping, text=name)
            label.grid(row=i // 2, column=(i % 2) * 2, sticky='w', padx=(0, 4), pady=2)
            if not hasattr(self, 'mapping_widgets'):
                self.mapping_widgets = {}
            var = tk.StringVar()
            self.mapping_vars[name] = var
            combo = ttk.Combobox(mapping, textvariable=var, values=[DISABLED_MAPPING, *ACTIVE_BUTTONS], state='readonly', width=9)
            combo.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky='w', padx=(0, 12))
            self.mapping_widgets[name] = (label, combo)
            combo.bind('<<ComboboxSelected>>', lambda _event, n=name: self.update_button_mapping(n))

        controls = ttk.LabelFrame(right, text='4  Safe controls', padding=10)
        controls.pack(fill='x', padx=(12, 0), pady=(0, 8))
        self.arm_button = ttk.Button(controls, text='Enable object controls', command=self.toggle, style='Accent.TButton')
        self.arm_button.pack(fill='x')
        ttk.Button(controls, text='STOP ALL OBJECT CONTROLS  (Esc)', command=self.stop_controls, style='Danger.TButton').pack(fill='x', pady=5)
        ttk.Label(controls, text='Ctrl+Alt+F11 toggle / Ctrl+Alt+F12 stop (when this window has focus). The Stop button always works. No global keyboard injection.', wraplength=315).pack(anchor='w')
        profiles = ttk.Frame(right)
        profiles.pack(fill='x', padx=(12, 0))
        ttk.Button(profiles, text='Save profile', command=self.save_profile).pack(side='left')
        ttk.Button(profiles, text='Load profile', command=self.load_profile).pack(side='left', padx=5)
        ttk.Button(profiles, text='Reset', command=self.reset_profile).pack(side='left')

    def make_scrollable_pane(self, host):
        """Create a vertically scrollable column with a visible scrollbar."""
        canvas = tk.Canvas(host, bg='#10243e', highlightthickness=0,
                           borderwidth=0, yscrollincrement=28)
        scrollbar = ttk.Scrollbar(host, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        content = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=content, anchor='nw')

        def update_region(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))

        def update_width(event):
            canvas.itemconfigure(window_id, width=event.width)
            update_region()

        content.bind('<Configure>', update_region)
        canvas.bind('<Configure>', update_width)
        # Bind at the root so the wheel works over nested controls, while
        # preserving the ROM shelf's own horizontal wheel interaction.
        if not hasattr(self, '_vertical_panes'):
            self._vertical_panes = []
        self._vertical_panes.append(canvas)
        if len(self._vertical_panes) == 2:
            self.install_panel_scrolling()
        return content

    def install_panel_scrolling(self):
        """Route wheel/trackpad events to the pane beneath the pointer.

        bind_all is needed because Tk child widgets otherwise swallow wheel events.
        Scrollbars remain available; no change to the ROM shelf's drag controls.
        """
        self._wheel_residual = {pane: 0.0 for pane in self._vertical_panes}
        self.root.bind_all('<MouseWheel>', self.on_panel_wheel, add='+')
        self.root.bind_all('<Button-4>', self.on_panel_wheel, add='+')
        self.root.bind_all('<Button-5>', self.on_panel_wheel, add='+')

    def on_panel_wheel(self, event):
        # The event's widget can be a child (including a button or combobox).
        # Locate the panel under the actual pointer instead of using focus.
        try:
            pointer = self.root.winfo_containing(self.root.winfo_pointerx(), self.root.winfo_pointery())
            if pointer is None:
                return
            ancestor = pointer
            pane = None
            while ancestor is not None:
                if ancestor in self._vertical_panes:
                    pane = ancestor
                    break
                ancestor = getattr(ancestor, 'master', None)
            if pane is None:
                return
            # Preserve native wheel behavior for dropdowns and other popups.
            if pointer.winfo_toplevel() != self.root:
                return
            if getattr(event, 'num', None) == 4:
                units = -3
            elif getattr(event, 'num', None) == 5:
                units = 3
            elif sys.platform == 'darwin':
                # macOS trackpads often emit many small deltas; accumulate them.
                units = -float(event.delta)
            else:
                units = -float(event.delta) / 120.0 * 3
            self._wheel_residual[pane] += units
            whole = int(self._wheel_residual[pane])
            if whole:
                pane.yview_scroll(whole, 'units')
                self._wheel_residual[pane] -= whole
                return 'break'
        except (tk.TclError, AttributeError):
            return

    def scan_cameras(self):
        if self.camera_scanning:
            return
        self.stop_camera()
        self.camera_scanning = True
        self.status.set('Searching for available webcams…')
        def worker():
            try:
                found = discover()
                self.root.after(0, lambda: self.finish_scan(found))
            except Exception as exc:
                self.root.after(0, lambda: self.finish_scan([], str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def finish_scan(self, found, error=None):
        self.camera_scanning = False
        self.camera_options = {f'{name} (device {index})': index for index, name in found}
        self.camera_combo['values'] = list(self.camera_options)
        if found:
            self.camera_name.set(next(iter(self.camera_options)))
            self.status.set(f'{len(found)} camera(s) found. Select one, then click Use camera.')
        else:
            self.camera_name.set('')
            self.status.set('No usable cameras found.' + (f' {error}' if error else ' Check permissions or click Refresh cameras.'))

    def start_camera(self):
        name = self.camera_name.get()
        if name not in self.camera_options:
            messagebox.showinfo('Camera', 'Select an available webcam first.')
            return
        self.stop_camera()
        self.reference_image = False
        index = self.camera_options[name]
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW if __import__('os').name == 'nt' else cv2.CAP_ANY)
        if not self.cap.isOpened():
            self.stop_camera()
            messagebox.showerror('Camera', 'Unable to open this webcam. Close other apps using it, or refresh the list.')
            return
        self.status.set(f'Camera ready: {name}. Click Pick color from video, then click your target.')

    def stop_camera(self):
        self.stop_controls()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.status.set('Camera stopped')

    def choose_core(self):
        path = filedialog.askopenfilename(title='Select libretro core for ' + SYSTEMS[self.system_key.get()].title, filetypes=[('Native libraries', '*.so *.dll *.dylib'), ('All files', '*')])
        if path:
            self.stop_controls()
            self.emu.stop()
            self.emu.core_path = path
            self.save_preferences(core_path=path)
            self.game_status.set('Core selected: ' + Path(path).name)

    KEYMAP = {'Up':'Up', 'Down':'Down', 'Left':'Left', 'Right':'Right',
              'z':'A', 'x':'B', 'a':'Y', 's':'X', 'q':'L', 'w':'R', 'Return':'Start', 'KP_Enter':'Start'}

    def activate_manual(self, event=None):
        self.manual_active = True
        self.game_canvas.focus_set()
        self.manual_label.set('MANUAL PLAY ACTIVE · Arrows D-pad · Z/X A/B · A/S Y/X · Q/W L/R · Enter Start')

    def deactivate_manual(self, event=None):
        self.manual_active = False
        self.emu.release_manual()
        self.manual_label.set('Click game screen · Arrows D-pad · Z/X A/B · A/S Y/X · Q/W L/R · Enter Start')

    def deactivate_on_outside_click(self, event):
        if event.widget is not self.game_canvas and self.manual_active:
            self.deactivate_manual()

    def manual_key_down(self, event):
        button = self.KEYMAP.get(event.keysym)
        if button and self.manual_active:
            self.emu.set_manual(button, True)
            return 'break'

    def manual_key_up(self, event):
        button = self.KEYMAP.get(event.keysym)
        if button:
            self.emu.set_manual(button, False)
            return 'break'

    def read_preferences(self):
        try:
            data = json.loads(self.preferences_path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def read_selected_system(self):
        key = self.read_preferences().get('system', DEFAULT_SYSTEM)
        return key if key in SYSTEMS else DEFAULT_SYSTEM

    def read_rom_directories(self):
        prefs = self.read_preferences()
        directories = prefs.get('rom_directories', {})
        directories = directories if isinstance(directories, dict) else {}
        directories.setdefault('gba', str(prefs.get('rom_directory', '')))
        return {key: str(value) for key, value in directories.items() if key in SYSTEMS and isinstance(value, str)}

    def read_core_paths(self):
        paths = self.read_preferences().get('core_paths', {})
        return paths if isinstance(paths, dict) else {}

    def save_preferences(self, core_path=None):
        prefs = self.read_preferences()
        prefs['theme'] = self.theme_name.get()
        prefs['system'] = self.system_key.get()
        prefs['rom_directories'] = dict(self.rom_directories)
        prefs['rom_directory'] = self.rom_directories.get('gba', '')  # legacy compatibility
        if core_path:
            paths = prefs.get('core_paths', {})
            paths = paths if isinstance(paths, dict) else {}
            paths[self.system_key.get()] = core_path
            prefs['core_paths'] = paths
        try:
            self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
            self.preferences_path.write_text(json.dumps(prefs, indent=2), encoding='utf-8')
        except OSError as exc:
            messagebox.showwarning('Preferences', f'Could not save preferences: {exc}')

    def update_button_mapping(self, name):
        self.cfg.setdefault('mapping', {})[name] = self.mapping_vars[name].get()
        self.profile_store.put(self.system_key.get(), self.cfg)
        self.status.set(f'{name} mapping updated. Use Fit buttons to grid to rearrange enabled zones.')

    def refresh_system_buttons(self):
        names = BUTTONS_BY_SYSTEM[self.system_key.get()]
        self.zone_combo.configure(values=[*names, 'Shuffle'])
        if self.zone_name.get() not in (*names, 'Shuffle'):
            self.zone_name.set(names[0])
        for name, (label, combo) in self.mapping_widgets.items():
            if name in names:
                label.grid()
                combo.grid()
                combo.configure(values=[DISABLED_MAPPING, *names])
            else:
                label.grid_remove()
                combo.grid_remove()

    def persist_system_profile(self):
        self.read_settings()
        self.profile_store.put(self.system_key.get(), self.cfg)

    def switch_system(self, event=None):
        key = self.system_key.get()
        if key not in SYSTEMS:
            return
        self.stop_controls()
        # The combobox has already changed, so save the previous system explicitly.
        previous = getattr(self, '_active_profile_system', DEFAULT_SYSTEM)
        try:
            self.read_settings()
            self.profile_store.put(previous, self.cfg)
        except (ValueError, tk.TclError, OSError):
            pass
        self.cfg = self.profile_store.get(key)
        self.refresh_settings()
        self.refresh_system_buttons()
        self._active_profile_system = key
        self.emu.stop()
        self.emu.system = key
        self.emu.core_path = self.emu.find_system_core()
        self.rom_directory = self.rom_directories.get(key, '')
        self.system_description.configure(text=SYSTEMS[key].title)
        self.current_rom = None
        self.game_canvas.delete('all')
        self.game_status.set('Load your own ' + SYSTEMS[key].title + ' ROM')
        self.show_library()
        self.populate_inline_library()
        self.save_preferences()

    def read_rom_directory(self):
        return self.read_rom_directories().get('gba', '')

    def set_rom_directory(self):
        initial = self.rom_directory
        if not initial or not Path(initial).is_dir():
            initial = str(Path.home())
        directory = filedialog.askdirectory(
            parent=self.root,
            title='Choose your ' + SYSTEMS[self.system_key.get()].title + ' ROM folder',
            initialdir=initial)
        if not directory:
            return
        self.rom_directory = directory
        self.rom_directories[self.system_key.get()] = directory
        self.save_preferences()
        self.populate_inline_library()

    def scan_roms(self):
        directory = Path(self.rom_directory)
        if not self.rom_directory or not directory.is_dir():
            return []
        extensions = SYSTEMS[self.system_key.get()].extensions
        # ROM collections commonly contain one folder per game and nested hacks.
        # Bound traversal and never follow directory symlinks, so an accidentally
        # selected large folder cannot trigger an unlimited recursive walk.
        import os
        found = []
        visited = 0
        try:
            for root, dirs, files in os.walk(directory, followlinks=False):
                visited += 1
                if visited > 2500 or len(found) >= 2000:
                    break
                dirs[:] = sorted(d for d in dirs if not d.startswith('.') and
                                 not (Path(root) / d).is_symlink())
                for name in files:
                    path = Path(root) / name
                    if path.suffix.lower() in extensions and path.is_file():
                        found.append(path)
                        if len(found) >= 2000:
                            break
        except OSError:
            pass
        return sorted(found, key=lambda p: (p.stem.casefold(), str(p).casefold()))

    @staticmethod
    def cartridge_image(filename, system='gba', artwork_path=None):
        """Draw console-specific cartridges on a genuinely transparent canvas.

        All artwork is generated locally; no game cover art or network requests.
        The alpha channel remains transparent outside the plastic shell so tiles
        blend into every dark and light theme without a rectangular halo.
        """
        w, h = 300, 226
        image = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)
        system = system if system in ('gb', 'gbc', 'gba', 'snes') else 'gba'
        if system == 'gb':
            # Original Game Boy: tall, light gray cartridge with a corner notch.
            shell = [(80, 8), (219, 8), (229, 18), (229, 209), (72, 209), (72, 17)]
            d.polygon(shell, fill='#b8bcc0')
            d.line(shell + [shell[0]], fill='#656c72', width=4, joint='curve')
            d.rounded_rectangle((83, 22, 216, 43), radius=5, fill='#979da2')
            d.text((150, 33), 'GAME BOY', anchor='mm', fill='#333b44', font=App.cartridge_font(13, True))
            d.rounded_rectangle((87, 55, 213, 179), radius=5, fill='#f3f0e8', outline='#656c72', width=3)
            d.rectangle((87, 55, 213, 79), fill='#6d7380')
            d.text((150, 68), 'ANYTHING PLAYS', anchor='mm', fill='#ffffff', font=App.cartridge_font(10, True))
            label_box = (95, 85, 205, 170)
            ink = '#24344a'
            d.line((103, 196, 197, 196), fill='#84898e', width=3)
        elif system == 'gbc':
            # Color cartridge: translucent-purple style with tall silhouette.
            shell = [(79, 9), (220, 9), (230, 19), (230, 209), (70, 209), (70, 18)]
            d.polygon(shell, fill='#6c5b9b')
            d.line(shell + [shell[0]], fill='#40375e', width=4, joint='curve')
            d.rounded_rectangle((82, 23, 217, 45), radius=6, fill='#8574b4')
            d.text((150, 34), 'GAME BOY COLOR', anchor='mm', fill='#f4edff', font=App.cartridge_font(11, True))
            d.rounded_rectangle((86, 56, 214, 180), radius=6, fill='#ece7fb', outline='#40375e', width=3)
            d.rectangle((86, 56, 214, 80), fill='#4c75b5')
            d.text((150, 68), 'ANYTHING PLAYS', anchor='mm', fill='#ffffff', font=App.cartridge_font(10, True))
            label_box = (95, 86, 205, 171)
            ink = '#352c55'
            d.line((103, 197, 197, 197), fill='#9c8ec0', width=3)
        elif system == 'snes':
            # North American SNES cartridge: broad rectangular shell, softly
            # rounded upper shoulders, distinctive recessed label and side grips.
            # Draw at high resolution so downscaled tiles retain crisp edges.
            shell = [(37, 18), (263, 18), (275, 24), (282, 39),
                     (282, 196), (274, 206), (26, 206), (18, 196),
                     (18, 39), (25, 24)]
            d.polygon(shell, fill='#c9c8d0')
            d.line(shell + [shell[0]], fill='#696975', width=4, joint='curve')
            # Molded top ridge and stepped shoulder detail.
            d.rounded_rectangle((37, 24, 263, 48), radius=7, fill='#d9d8df', outline='#9b9aa6', width=2)
            d.line((28, 50, 272, 50), fill='#a2a1ad', width=3)
            # Vertical molded grip rails on the left and right.
            d.rounded_rectangle((25, 61, 44, 181), radius=6, fill='#b0afb9', outline='#8a8995', width=2)
            d.rounded_rectangle((256, 61, 275, 181), radius=6, fill='#b0afb9', outline='#8a8995', width=2)
            for x in (31, 37, 263, 269):
                d.line((x, 76, x, 167), fill='#d0cfd7' if x in (31, 263) else '#92919d', width=2)
            # A large rectangular paper label with a thin inset frame.
            d.rounded_rectangle((51, 57, 249, 175), radius=5, fill='#777581', outline='#5f5e6b', width=3)
            d.rounded_rectangle((56, 62, 244, 170), radius=3, fill='#f1eff0', outline='#d7d4d9', width=2)
            d.rectangle((58, 64, 242, 87), fill='#353b59')
            d.text((150, 75), 'SUPER NINTENDO', anchor='mm', fill='#ffffff', font=App.cartridge_font(12, True))
            d.rectangle((58, 88, 242, 92), fill='#8176ae')
            label_box = (65, 98, 235, 161)
            ink = '#27273b'
            # Bottom molded seam and central locking notch.
            d.line((45, 187, 255, 187), fill='#9695a0', width=3)
            d.rounded_rectangle((123, 194, 177, 205), radius=3, fill='#aaa9b4', outline='#777683', width=2)
        else:
            # Compact Game Boy Advance cartridge, with alpha outside the shell.
            d.rounded_rectangle((10, 14, 290, 212), radius=17, fill='#333a46', outline='#657080', width=3)
            d.rounded_rectangle((10, 14, 290, 46), radius=13, fill='#4b5563', outline='#737d8a', width=2)
            d.rectangle((22, 40, 278, 48), fill='#333a46')
            d.text((150, 30), 'GAME BOY ADVANCE', anchor='mm', fill='#d5dce7', font=App.cartridge_font(13, True))
            d.rounded_rectangle((39, 61, 261, 184), radius=9, fill='#10243e', outline='#8c98a8', width=3)
            d.rounded_rectangle((46, 68, 254, 177), radius=5, fill='#1e5182')
            d.polygon([(46, 68), (254, 68), (254, 89), (46, 141)], fill='#2e699d')
            d.text((150, 95), 'ANYTHING PLAYS', anchor='mm', fill='#d8e9ff', font=App.cartridge_font(11, True))
            label_box = (54, 113, 246, 169)
            ink = '#ffffff'
            d.line((112, 200, 188, 200), fill='#1a202b', width=4)

        # Optional game-specific artwork: place cover.png, cover.jpg, or an image
        # with the same filename stem alongside the ROM. No network required.
        if artwork_path is not None:
            try:
                with Image.open(artwork_path) as source:
                    cover = source.convert('RGB')
                box_w = label_box[2] - label_box[0]
                box_h = label_box[3] - label_box[1]
                from PIL import ImageOps
                cover = ImageOps.fit(cover, (box_w, box_h), method=Image.Resampling.LANCZOS)
                image.paste(cover, (label_box[0], label_box[1]))
                return image
            except (OSError, ValueError):
                pass
        max_width = label_box[2] - label_box[0] - 6
        max_lines = 3 if system in ('gb', 'gbc') else 2
        font_size = 14 if system in ('gb', 'gbc') else 16
        font = App.cartridge_font(font_size, bold=True)
        words = filename.replace('_', ' ').split()
        lines = []
        current = ''
        for word in words:
            candidate = f'{current} {word}'.strip()
            if current and d.textbbox((0, 0), candidate, font=font)[2] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines - 1] + [' '.join(lines[max_lines - 1:])]
        line_height = font_size + 4
        top = (label_box[1] + label_box[3] - line_height * len(lines)) // 2 + line_height // 2
        for index, line in enumerate(lines):
            while len(line) > 2 and d.textbbox((0, 0), line, font=font)[2] > max_width:
                line = line[:-2] + '…'
            d.text((150, top + index * line_height), line, anchor='mm', fill=ink, font=font)
        return image

    @staticmethod
    def cartridge_font(size, bold=False):
        paths = (['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                  '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                  'C:/Windows/Fonts/arialbd.ttf'] if bold else
                 ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                  '/System/Library/Fonts/Supplemental/Arial.ttf',
                  'C:/Windows/Fonts/arial.ttf'])
        for path in paths:
            try: return ImageFont.truetype(path, size)
            except OSError: pass
        return ImageFont.load_default()

    def choose_or_rescan_library(self):
        # If no directory exists, ask for one; otherwise refresh without a popup.
        if not self.rom_directory or not Path(self.rom_directory).is_dir():
            self.set_rom_directory()
        else:
            self.populate_inline_library()

    def cancel_shelf_animation(self):
        if self.shelf_animation_job is not None:
            self.root.after_cancel(self.shelf_animation_job)
            self.shelf_animation_job = None
        self.shelf_animation_target = None

    def shelf_button_press(self, direction):
        """Click advances a page; holding continues moving the shelf."""
        self.shelf_button_release()
        self.cancel_shelf_momentum()
        self.cancel_shelf_animation()
        self.shelf_button_direction = direction
        self.scroll_cartridges(direction, pages=0.85)
        self.shelf_button_job = self.root.after(360, self.shelf_button_repeat)
        return 'break'

    def shelf_button_repeat(self):
        self.shelf_button_job = None
        if not self.shelf_button_direction:
            return
        self.scroll_cartridges(self.shelf_button_direction, pages=0.65)
        self.shelf_button_job = self.root.after(190, self.shelf_button_repeat)

    def shelf_button_release(self, event=None):
        self.shelf_button_direction = 0
        if self.shelf_button_job is not None:
            self.root.after_cancel(self.shelf_button_job)
            self.shelf_button_job = None
        return 'break'

    def scroll_cartridges(self, direction, pages=0.85):
        """Smoothly advance by a fraction of the visible shelf, not tiny Tk units."""
        self.cancel_shelf_momentum()
        total = max(1, self.library_grid.winfo_width())
        viewport = self.library_canvas.winfo_width()
        if total <= viewport:
            return
        left, right = self.library_canvas.xview()
        current = self.shelf_animation_target if self.shelf_animation_target is not None else left
        max_left = max(0.0, 1.0 - viewport / total)
        target = max(0.0, min(max_left, current + direction * viewport * pages / total))
        self.shelf_animation_target = target
        if self.shelf_animation_job is None:
            self.animate_shelf()

    def animate_shelf(self):
        target = self.shelf_animation_target
        if target is None:
            self.shelf_animation_job = None
            return
        current = self.library_canvas.xview()[0]
        delta = target - current
        if abs(delta) < 0.0005:
            self.library_canvas.xview_moveto(target)
            self.shelf_animation_job = None
            self.shelf_animation_target = None
            return
        self.library_canvas.xview_moveto(current + delta * 0.28)
        self.shelf_animation_job = self.root.after(16, self.animate_shelf)

    def on_library_wheel(self, event):
        self.scroll_cartridges(-1 if event.delta > 0 else 1)
        return 'break'

    def cancel_shelf_momentum(self):
        if self.shelf_momentum_job is not None:
            self.root.after_cancel(self.shelf_momentum_job)
            self.shelf_momentum_job = None

    def shelf_press(self, event, rom):
        """Begin a gesture on a cartridge; do not launch until mouse release."""
        self.cancel_shelf_momentum()
        self.cancel_shelf_animation()
        self.shelf_drag = {'start': event.x_root, 'last': event.x_root,
                           'last_time': time.monotonic(), 'distance': 0,
                           'rom': rom, 'velocity': 0.0}

    def shelf_motion(self, event):
        drag = self.shelf_drag
        if drag is None:
            return
        now = time.monotonic()
        dx = event.x_root - drag['last']
        drag['distance'] = max(drag['distance'], abs(event.x_root - drag['start']))
        dt = max(0.008, now - drag['last_time'])
        if drag['distance'] >= 7:
            width = max(1, self.library_grid.winfo_width())
            self.library_canvas.xview_moveto(self.library_canvas.xview()[0] - dx / width)
            drag['velocity'] = max(-32.0, min(32.0, dx / dt / 60.0))
        drag['last'] = event.x_root
        drag['last_time'] = now

    def shelf_release(self, event):
        drag = self.shelf_drag
        if drag is None:
            return
        self.shelf_drag = None
        if drag['distance'] < 7 and abs(event.x_root - drag['start']) < 7:
            # A release outside the shelf must not launch a game.
            left = self.library_canvas.winfo_rootx()
            top = self.library_canvas.winfo_rooty()
            if (left <= event.x_root < left + self.library_canvas.winfo_width()
                    and top <= event.y_root < top + self.library_canvas.winfo_height()):
                self.start_rom(drag['rom'])
        elif time.monotonic() - drag['last_time'] < .12:
            self.shelf_velocity = drag['velocity']
            self.shelf_coast()

    def shelf_coast(self):
        if abs(self.shelf_velocity) < 0.35 or not self.library_strip.winfo_ismapped():
            self.shelf_momentum_job = None
            return
        width = max(1, self.library_grid.winfo_width())
        before = self.library_canvas.xview()[0]
        self.library_canvas.xview_moveto(before - self.shelf_velocity / width)
        if abs(self.library_canvas.xview()[0] - before) < 0.000001:
            self.shelf_momentum_job = None
            return
        self.shelf_velocity *= .88
        self.shelf_momentum_job = self.root.after(16, self.shelf_coast)

    def populate_inline_library(self):
        for widget in self.library_grid.winfo_children():
            widget.destroy()
        self.cancel_shelf_momentum()
        self.cancel_shelf_animation()
        self.shelf_drag = None
        self.library_images.clear()
        games = self.scan_roms()
        if not self.rom_directory or not Path(self.rom_directory).is_dir():
            self.library_summary.set('ROM LIBRARY · Choose a ROM folder above')
        else:
            self.library_summary.set(f'ROM LIBRARY · {len(games)} game(s) · Drag or use Previous / Next')
        if not games:
            ttk.Label(self.library_grid, text='No compatible games yet. Choose a folder to browse cartridges.').pack(padx=8, pady=40)
        for rom in games:
            tile = ttk.Frame(self.library_grid, padding=(5, 0))
            tile.pack(side='left', anchor='n')
            art_path = next((candidate for stem in (rom.stem, 'cover', 'folder')
                             for ext in ('.png', '.jpg', '.jpeg', '.webp')
                             if (candidate := rom.parent / (stem + ext)).is_file()), None)
            art = self.cartridge_image(rom.stem, self.system_key.get(), art_path).resize((176, 133), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(art)
            self.library_images.append(photo)
            cartridge = tk.Label(tile, image=photo, bg=self.THEMES.get(self.theme_name.get(), self.THEMES['Dark'])[1],
                                 cursor='hand2', bd=0, highlightthickness=0)
            cartridge.is_cartridge_tile = True
            cartridge.pack()
            caption = ttk.Label(tile, text=rom.stem, width=24, anchor='center', cursor='hand2')
            caption.pack()
            for widget in (cartridge, caption, tile):
                widget.bind('<ButtonPress-1>', lambda e, p=rom: self.shelf_press(e, p))
        self.library_canvas.configure(scrollregion=self.library_canvas.bbox('all'))
        self.library_canvas.xview_moveto(0)

    def show_library(self):
        self.playing_info.pack_forget()
        self.library_strip.pack(fill='x')

    def show_playing_info(self):
        self.library_strip.pack_forget()
        self.playing_info.pack(fill='x')

    def unload_rom(self):
        self.deactivate_manual()
        self.stop_controls()
        self.emu.stop()
        with self.emu.lock:
            self.emu.frame = None
        self.current_rom = None
        self.game_photo = None
        self.game_canvas.delete('all')
        self.game_status.set('No ROM loaded')
        self.show_library()

    def start_rom(self, path):
        self.deactivate_manual()
        self.stop_controls()
        try:
            self.emu.start(str(path))
            self.current_rom = str(path)
            self.game_status.set('Playing ' + Path(path).stem)
            self.show_playing_info()
        except Exception as exc:
            messagebox.showerror('ROM', f'Could not start game: {exc}')

    def load_rom(self):
        system = SYSTEMS[self.system_key.get()]
        path = filedialog.askopenfilename(filetypes=[(system.title + ' ROMs', ' '.join('*' + ext for ext in system.extensions))])
        if not path:
            return
        self.start_rom(path)

    def pick_color(self):
        if self.frame is None:
            messagebox.showinfo('Target color', 'Start a webcam first.')
            return
        self.pick_mode = True
        self.status.set('Click your target in the camera preview to sample its color.')

    def pick_image(self):
        path = filedialog.askopenfilename(filetypes=[('Images', '*.png *.jpg *.jpeg *.bmp *.webp')])
        if not path:
            return
        frame = cv2.imread(path)
        if frame is None:
            messagebox.showerror('Image', 'Unable to read this image.')
            return
        self.stop_camera()
        self.frame = frame
        self.reference_image = True
        self.pick_mode = True
        self.status.set('Click the target color in the reference image. Start the webcam afterward.')

    def choose_color(self):
        color = colorchooser.askcolor(color='#%02x%02x%02x' % tuple(self.cfg['rgb']))
        if color[0]:
            self.cfg['rgb'] = [int(x) for x in color[0]]
            self.refresh_color()

    def refresh_color(self):
        self.color_text.set('Selected target color: #%02X%02X%02X' % tuple(self.cfg['rgb']))

    def geometry(self):
        if self.frame is None:
            return None
        h, w = self.frame.shape[:2]
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        scale = min(cw / w, ch / h)
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        return ((cw - dw) // 2, (ch - dh) // 2, dw, dh, w, h)

    def xy(self, event):
        geom = self.geometry()
        if not geom:
            return None
        x, y, dw, dh, w, h = geom
        if not (x <= event.x < x + dw and y <= event.y < y + dh):
            return None
        return (min(w - 1, int((event.x - x) * w / dw)), min(h - 1, int((event.y - y) * h / dh)))

    def on_click(self, event):
        point = self.xy(event)
        if point is None:
            return
        if self.pick_mode:
            rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)[point[1], point[0]]
            self.cfg['rgb'] = [int(v) for v in rgb]
            self.refresh_color()
            self.pick_mode = False
            self.status.set('Target color selected. Adjust tolerance if needed.')
        elif self.custom_draw_enabled.get():
            self.drag_start = point

    def on_release(self, event):
        if not self.custom_draw_enabled.get() or self.drag_start is None:
            return
        end, start = self.xy(event), self.drag_start
        self.drag_start = None
        if end is None or self.frame is None:
            return
        h, w = self.frame.shape[:2]
        x1, x2 = sorted((start[0] / w, end[0] / w))
        y1, y2 = sorted((start[1] / h, end[1] / h))
        if (x2 - x1) * (y2 - y1) > .002:
            self.cfg['zones'][self.zone_name.get()] = [x1, y1, x2, y2]

    def refresh_settings(self):
        self.tolerance.set(self.cfg['tolerance'])
        self.min_area.set(self.cfg['min_area'])
        self.hold_frames.set(self.cfg['hold_frames'])
        self.cooldown.set(self.cfg['cooldown_ms'])
        self.mirror.set(self.cfg['mirror'])
        self.cfg = normalize(self.system_key.get(), self.cfg, DEFAULT)
        for name, var in self.mapping_vars.items():
            var.set(self.cfg.get('mapping', {}).get(name, name))
        self.zone_font_size.set(max(8, min(160, self.cfg.get('zone_font_size', 44))))
        self.zone_opacity.set(max(75, min(100, self.cfg.get('zone_opacity', 85))))
        self.zone_style.set(self.cfg.get('zone_style', 'Outline'))
        self.cfg = normalize(self.system_key.get(), self.cfg, DEFAULT)
        self.shuffle_enabled.set(self.cfg.get('shuffle_enabled', True))
        self.zone_image_path.set(self.cfg.get('zone_image', ''))
        self.load_zone_art(silent=True)
        self.refresh_color()

    def read_settings(self):
        self.cfg['tolerance'] = max(1, min(90, int(self.tolerance.get())))
        self.cfg['min_area'] = max(5, int(self.min_area.get()))
        self.cfg['hold_frames'] = max(1, min(60, int(self.hold_frames.get())))
        self.cfg['cooldown_ms'] = max(50, int(self.cooldown.get()))
        self.cfg['mirror'] = self.mirror.get()
        self.cfg['zone_font_size'] = max(8, min(160, int(self.zone_font_size.get())))
        self.cfg['zone_opacity'] = max(75, min(100, int(self.zone_opacity.get())))
        self.cfg['zone_style'] = self.zone_style.get()
        self.cfg['shuffle_enabled'] = bool(self.shuffle_enabled.get())
        self.cfg['zone_image'] = self.zone_image_path.get()
        self.cfg['mapping'] = {name: var.get() for name, var in self.mapping_vars.items()}

    def toggle(self):
        if self.armed:
            self.stop_controls()
            return
        if self.cap is None or not self.cap.isOpened():
            messagebox.showinfo('Camera required', 'Choose and start a webcam first.')
            return
        if not self.emu.running:
            messagebox.showinfo('Emulator required', 'Open a compatible ROM first. No system-wide keyboard fallback is available.')
            return
        try:
            self.read_settings()
        except (ValueError, tk.TclError):
            messagebox.showerror('Settings', 'Please correct the numeric settings.')
            return
        self.armed = True
        self.emu.armed = True
        self.last_action = time.monotonic()
        self.arm_button.config(text='Pause object controls')
        self.action.set('ACTIVE — object controls embedded emulator only')

    def stop_controls(self):
        self.armed = False
        self.emu.disarm()
        if hasattr(self, 'arm_button'):
            self.arm_button.config(text='Enable object controls')
        if hasattr(self, 'action'):
            self.action.set('PREVIEW ONLY — no keyboard events are sent')

    def tick(self):
        try:
            if self.cap is not None and self.cap.isOpened():
                ok, frame = self.cap.read()
                if ok:
                    self.frame = cv2.flip(frame, 1) if self.mirror.get() else frame
                else:
                    self.stop_camera()
                    self.status.set('Camera disconnected. Refresh and select another.')
            if self.frame is not None:
                self.draw_camera()
            self.draw_game()
            if self.emu.error:
                self.game_status.set('Emulator error: ' + self.emu.error)
                self.stop_controls()
                self.emu.error = None
            elif self.emu.running:
                self.game_status.set('Emulator running independently of desktop keyboard focus')
        except Exception as exc:
            self.stop_controls()
            self.status.set('Tracking error: ' + str(exc)[:120])
        finally:
            self.root.after(45, self.tick)

    def choose_zone_art(self):
        path = filedialog.askopenfilename(title='Choose zone artwork',
                                          filetypes=[('PNG images', '*.png')])
        if path:
            self.zone_image_path.set(path)
            self.load_zone_art()

    def ask_zone_url(self):
        from tkinter import simpledialog
        url = simpledialog.askstring('Zone image URL',
                                    'Paste a direct HTTPS link to a PNG image:')
        if not url:
            return
        if not url.startswith('https://'):
            messagebox.showerror('Image URL', 'Use a direct HTTPS PNG image URL.')
            return
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'AnythingPlays/1.6'})
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
        # Render translucent zones and readable labels at native camera
        # resolution; scaling to the preview happens afterward.
        height, width = frame.shape[:2]
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
        overlay = Image.new('RGBA', (width, height))
        draw = ImageDraw.Draw(overlay)
        opacity = max(75, min(100, int(self.zone_opacity.get())))
        # The previous opacity*1.5 calculation exceeded 255 and saturated.
        # Map the user-facing 75–100 range to visibly distinct alpha levels.
        tint_alpha = round(25 + (opacity - 75) / 25 * 170)
        size = max(8, min(160, int(self.zone_font_size.get())))
        font = None
        for font_name in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                          '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                          'C:/Windows/Fonts/arialbd.ttf'):
            try:
                font = ImageFont.truetype(font_name, size)
                break
            except OSError:
                continue
        if font is None:
            font = ImageFont.load_default()
        for name, (x1, y1, x2, y2) in self.cfg['zones'].items():
            if name == 'Shuffle' and not self.shuffle_enabled.get():
                continue
            if name != 'Shuffle' and self.mapping_vars.get(name) is not None and self.mapping_vars[name].get() == DISABLED_MAPPING:
                continue
            box = (int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            chosen = name == active
            color = (75, 240, 150) if chosen else (90, 220, 245)
            if self.zone_style.get() == 'High contrast':
                # Only high contrast tints the camera image; Outline leaves it clear.
                draw.rectangle(box, fill=(*color, tint_alpha))
            if self._zone_art is not None:
                art = self._zone_art.copy()
                art.thumbnail((max(1, box[2]-box[0]-12), max(1, box[3]-box[1]-12)))
                px = box[0] + (box[2]-box[0]-art.width)//2
                py = box[1] + (box[3]-box[1]-art.height)//2
                # Keep imported artwork's own alpha; tint opacity controls zone fills.
                overlay.alpha_composite(art, (px, py))
            label_box = draw.textbbox((0, 0), name, font=font, stroke_width=1)
            tw = label_box[2] - label_box[0]
            th = label_box[3] - label_box[1]
            lx = min(max(0, box[0]+5), max(0, width-tw-12))
            ly = min(max(0, box[1]+5), max(0, height-th-12))
            if self.zone_style.get() != 'Minimal':
                draw.rounded_rectangle((lx, ly, lx+tw+12, ly+th+12), radius=5,
                                       fill=(3, 21, 30, 235))
            draw.text((lx+6, ly+6-label_box[1]), name, font=font,
                      fill=(255, 255, 255, 255), stroke_width=1,
                      stroke_fill=(0, 0, 0, 255))
            # Draw the four-sided border LAST, on top of artwork and labels.
            # Keep the entire stroke inside the image, even for edge zones.
            stroke = 7 if chosen else (3 if self.zone_style.get() != 'Minimal' else 0)
            inset = (stroke + 1) // 2 + 1
            left = max(inset, min(width - inset - 1, box[0] + inset))
            top = max(inset, min(height - inset - 1, box[1] + inset))
            right = min(width - inset - 1, max(left + 1, box[2] - inset - 1))
            bottom = min(height - inset - 1, max(top + 1, box[3] - inset - 1))
            if stroke and right > left and bottom > top:
                draw.rectangle((left, top, right, bottom),
                               outline=(40, 255, 105, 255) if chosen else (90, 220, 245, 255),
                               width=stroke)
        rgba = Image.alpha_composite(rgba, overlay)
        return cv2.cvtColor(np.asarray(rgba.convert('RGB')), cv2.COLOR_RGB2BGR)

    def draw_camera(self):
        frame = self.frame.copy()
        h, w = frame.shape[:2]
        tol = max(1, min(90, int(self.tolerance.get())))
        area = max(5, int(self.min_area.get()))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        target = cv2.cvtColor(np.uint8([[self.cfg['rgb']]]), cv2.COLOR_RGB2HSV)[0, 0]
        hh, ss, vv = (int(x) for x in target)
        hue = hsv[:, :, 0].astype(np.int16)
        hue_distance = np.minimum(abs(hue - hh), 180 - abs(hue - hh))
        sat_distance = abs(hsv[:, :, 1].astype(np.int16) - ss)
        val_distance = abs(hsv[:, :, 2].astype(np.int16) - vv)
        mask = ((hue_distance <= tol // 2 + 1) & (sat_distance <= max(35, tol * 3)) & (val_distance <= max(45, tol * 4))).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [c for c in contours if cv2.contourArea(c) >= area]
        center = None
        if contours:
            contour = max(contours, key=cv2.contourArea)
            moment = cv2.moments(contour)
            if moment['m00']:
                center = (int(moment['m10'] / moment['m00']), int(moment['m01'] / moment['m00']))
                cv2.circle(frame, center, 8, (0, 255, 0), -1)
                cv2.drawContours(frame, [contour], -1, (0, 255, 255), 2)
        active = None
        if center:
            for name, (x1, y1, x2, y2) in self.cfg['zones'].items():
                if name == 'Shuffle' and not self.shuffle_enabled.get():
                    continue
                if name != 'Shuffle' and self.mapping_vars[name].get() == DISABLED_MAPPING:
                    continue
                if x1 <= center[0] / w <= x2 and y1 <= center[1] / h <= y2:
                    active = name
                    break
        frame = self.render_zones(frame, active)
        if active != 'Shuffle':
            self._shuffle_latched = False
        if active == 'Shuffle':
            if self.armed and self.shuffle_enabled.get() and not self._shuffle_latched:
                self._shuffle_latched = True
                self.shuffle_zones()
                self.action.set('Object activated Shuffle — controls rearranged')
        elif active and self.armed and time.monotonic() - self.last_action >= max(.05, int(self.cooldown.get()) / 1000):
            button = self.mapping_vars[active].get()
            if button != DISABLED_MAPPING:
                self.emu.press(button, self.hold_frames.get())
                self.last_action = time.monotonic()
                self.action.set(f'Object zone: {active} → game button: {button} (isolated)')
        geom = self.geometry()
        if geom:
            x, y, dw, dh, _, _ = geom
            rgb = cv2.cvtColor(cv2.resize(frame, (dw, dh)), cv2.COLOR_BGR2RGB)
            self.camera_photo = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.canvas.delete('all')
            self.canvas.create_image(x, y, anchor='nw', image=self.camera_photo)

    def draw_game(self):
        with self.emu.lock:
            frame = None if self.emu.frame is None else self.emu.frame.copy()
        if frame is None:
            return
        cw, ch = max(1, self.game_canvas.winfo_width()), max(1, self.game_canvas.winfo_height())
        scale = min(cw / frame.shape[1], ch / frame.shape[0])
        dw, dh = max(1, int(frame.shape[1] * scale)), max(1, int(frame.shape[0] * scale))
        image = Image.fromarray(frame[:, :, :3]).resize((dw, dh), Image.Resampling.NEAREST)
        self.game_photo = ImageTk.PhotoImage(image)
        self.game_canvas.delete('all')
        self.game_canvas.create_image((cw - dw) // 2, (ch - dh) // 2, image=self.game_photo, anchor='nw')

    def save_profile(self):
        try:
            self.read_settings()
        except Exception:
            messagebox.showerror('Profile', 'Correct the settings first.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON profile', '*.json')])
        if path:
            Path(path).write_text(json.dumps(self.cfg, indent=2), encoding='utf-8')
            self.profile_store.put(self.system_key.get(), self.cfg)

    def load_profile(self):
        path = filedialog.askopenfilename(filetypes=[('JSON profile', '*.json')])
        if not path:
            return
        try:
            cfg = json.loads(Path(path).read_text(encoding='utf-8'))
            if not isinstance(cfg, dict) or not isinstance(cfg.get('zones'), dict):
                raise ValueError('Invalid profile: missing zones')
            self.stop_controls()
            self.cfg = normalize(self.system_key.get(), cfg, DEFAULT)
            self.profile_store.put(self.system_key.get(), self.cfg)
            self.refresh_settings()
        except Exception as exc:
            messagebox.showerror('Profile', str(exc))

    def reset_profile(self):
        self.stop_controls()
        self.cfg = default_for(self.system_key.get(), DEFAULT)
        self.refresh_settings()
        self.profile_store.put(self.system_key.get(), self.cfg)

    def close(self):
        try:
            self.persist_system_profile()
        except (OSError, ValueError, tk.TclError):
            pass
        self.deactivate_manual()
        self.stop_controls()
        if self.cap is not None:
            self.cap.release()
        self.emu.stop()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
