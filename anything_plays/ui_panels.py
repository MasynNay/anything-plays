"""Focused camera, control-zone and safety panels for the 2.1 desktop UI.

Keep gameplay / library layout in ui_layout.py and the supporting panel
construction here. Both classes are composed into App, avoiding circular
dependencies and preserving all existing widget fields and callbacks.
"""

import tkinter as tk
from tkinter import ttk

from anything_plays.system_profiles import DISABLED_MAPPING, BUTTONS_BY_SYSTEM

ALL_BUTTONS = tuple(dict.fromkeys(
    button for buttons in BUTTONS_BY_SYSTEM.values() for button in buttons
))


class AuxiliaryPanelsMixin:
    def _build_camera_panel(self, left):
        """Camera selector, feed, and tracking status."""
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


    def _build_tracking_panel(self, right):
        """Color detection settings and per-console button mapping."""
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
        ttk.Label(appearance, text='Bold: bright thick borders + centered labels. High contrast: tinted zones. Outline: clear camera. Minimal: labels only.', wraplength=380).pack(anchor='w', pady=(4, 2))
        ttk.Combobox(appearance, textvariable=self.zone_style, state='readonly',
                     values=['Bold', 'High contrast', 'Outline', 'Minimal'], width=18).pack(fill='x', pady=4)
        ttk.Label(appearance, text='Border thickness (2–16 px)').pack(anchor='w', pady=(3, 0))
        border_row = ttk.Frame(appearance)
        border_row.pack(fill='x')
        ttk.Scale(border_row, from_=2, to=16, variable=self.zone_border_width,
                  orient='horizontal').pack(side='left', fill='x', expand=True)
        ttk.Spinbox(border_row, from_=2, to=16, increment=1, width=5,
                    textvariable=self.zone_border_width).pack(side='right', padx=(8, 0))
        ttk.Label(appearance, text='Zone label position').pack(anchor='w', pady=(4, 0))
        ttk.Combobox(appearance, textvariable=self.zone_label_position, state='readonly',
                     values=['Center', 'Top-left'], width=17).pack(fill='x')
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
        self.zone_combo = ttk.Combobox(fish, textvariable=self.zone_name, values=list(ALL_BUTTONS) + ['Shuffle'], state='readonly')
        self.zone_combo.pack(fill='x')
        mapping = ttk.Frame(fish)
        self.mapping_widgets = {}
        mapping.pack(fill='x', pady=5)
        for i, name in enumerate(ALL_BUTTONS):
            label = ttk.Label(mapping, text=name)
            label.grid(row=i // 2, column=(i % 2) * 2, sticky='w', padx=(0, 4), pady=2)
            var = tk.StringVar()
            self.mapping_vars[name] = var
            combo = ttk.Combobox(mapping, textvariable=var, values=[DISABLED_MAPPING, *ALL_BUTTONS], state='readonly', width=9)
            combo.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky='w', padx=(0, 12))
            self.mapping_widgets[name] = (label, combo)
            combo.bind('<<ComboboxSelected>>', lambda _event, n=name: self.update_button_mapping(n))


    def _build_safety_panel(self, right):
        """Emergency stop controls and profile actions."""
        controls = ttk.LabelFrame(right, text='4  Safe controls', padding=10)
        controls.pack(fill='x', padx=(12, 0), pady=(0, 8))
        self.arm_button = ttk.Button(controls, text='Enable object controls', command=self.toggle, style='Accent.TButton')
        self.arm_button.pack(fill='x')
        ttk.Button(controls, text='STOP ALL OBJECT CONTROLS  (Esc)', command=self.stop_controls, style='Danger.TButton').pack(fill='x', pady=5)
        ttk.Label(controls, text='F11 fullscreen · F10 borderless · Esc exit fullscreen and stop controls · Ctrl+Alt+F11 start/stop camera controls. No global keyboard injection.', wraplength=315).pack(anchor='w')
        profiles = ttk.Frame(right)
        profiles.pack(fill='x', padx=(12, 0))
        ttk.Button(profiles, text='Save profile', command=self.save_profile).pack(side='left')
        ttk.Button(profiles, text='Load profile', command=self.load_profile).pack(side='left', padx=5)
        ttk.Button(profiles, text='Reset', command=self.reset_profile).pack(side='left')

