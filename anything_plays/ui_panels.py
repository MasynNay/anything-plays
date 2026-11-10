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
        cameras = ttk.LabelFrame(left, text='01   CAMERA  ·  Live tracking preview', padding=8)
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
        # Frequently used label sizing belongs beside the preview, not inside
        # the collapsed advanced appearance controls on the opposite pane.
        label_row = ttk.Frame(left)
        label_row.pack(fill='x', pady=(4, 2))
        ttk.Label(label_row, text='Control label size').pack(side='left', padx=(0, 8))
        self.quick_label_size = ttk.Scale(
            label_row, from_=8, to=160, variable=self.zone_font_size,
            orient='horizontal', command=self.schedule_zone_label_size_save,
        )
        self.quick_label_size.pack(side='left', fill='x', expand=True)
        ttk.Label(label_row, textvariable=self.zone_font_size, width=4).pack(
            side='left', padx=(8, 2)
        )
        ttk.Button(
            label_row, text='Reset', command=lambda: self.set_zone_label_size(28),
            style='Compact.TButton',
        ).pack(side='left', padx=(5, 0))
        self.shuffle_enabled.trace_add('write', lambda *_: self.update_shuffle_visibility())
        # Keep the manual Shuffle action visible even when the right-hand
        # advanced appearance panel is collapsed. This moves existing zones
        # only; it never starts an emulator or injects keyboard input.
        quick_row = ttk.Frame(left)
        quick_row.pack(fill='x', pady=(6, 3))
        self.quick_shuffle_button = ttk.Button(
            quick_row, text='Shuffle control zones now',
            command=self.shuffle_zones, style='Accent.TButton',
        )
        self.quick_shuffle_button.pack(side='left', fill='x', expand=True)
        ttk.Label(
            quick_row, text='Manual shuffle · no camera needed',
            style='Helper.TLabel',
        ).pack(side='left', padx=(9, 2))
        ttk.Label(left, textvariable=self.status).pack(anchor='w')
        ttk.Label(left, textvariable=self.action, font=('DejaVu Sans', 11, 'bold')).pack(anchor='w', pady=4)


    def _build_tracking_panel(self, right):
        """Delegate to the spaced, accessible object-tracking panel."""
        from anything_plays.ui_tracking_panel import build_tracking_panel
        build_tracking_panel(self, right)

    def _build_safety_panel(self, right):
        """Emergency stop controls and profile actions."""
        controls = ttk.LabelFrame(right, text='08   SAFETY & PROFILES', padding=10)
        controls.pack(fill='x', padx=(12, 2), pady=(0, 12))
        self.arm_button = ttk.Button(controls, text='Enable object controls', command=self.toggle, style='Accent.TButton')
        self.arm_button.pack(fill='x')
        ttk.Button(controls, text='STOP ALL OBJECT CONTROLS  (Esc)', command=self.stop_controls, style='Danger.TButton').pack(fill='x', pady=5)
        ttk.Label(controls, text='F11 fullscreen · F10 borderless · Esc exit fullscreen and stop controls · Ctrl+Alt+F11 start/stop camera controls. No global keyboard injection.', wraplength=315).pack(anchor='w')
        ttk.Button(controls, text='Keyboard Shortcuts', command=self.configure_shortcuts).pack(fill='x', pady=(8, 2))
        profiles = ttk.Frame(right)
        profiles.pack(fill='x', padx=(12, 2), pady=(0, 16))
        ttk.Button(profiles, text='Save profile', command=self.save_profile).pack(side='left')
        ttk.Button(profiles, text='Load profile', command=self.load_profile).pack(side='left', padx=5)
        ttk.Button(profiles, text='Reset', command=self.reset_profile).pack(side='left')

