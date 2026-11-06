"""Construct the desktop layout and route scroll wheel events by pane."""

import sys
import tkinter as tk
from tkinter import ttk

from anything_plays.systems import SYSTEMS
from anything_plays.system_profiles import DISABLED_MAPPING, BUTTONS_BY_SYSTEM

ALL_BUTTONS = tuple(dict.fromkeys(
    button for buttons in BUTTONS_BY_SYSTEM.values() for button in buttons
))


class LayoutMixin:
    """Tkinter behavior shared with the main application controller.

    These methods use widgets and state initialized by ``App.__init__``
    and ``LayoutMixin.build``. They are not standalone widgets.
    """

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
        ttk.Label(main, text='A little world where movement becomes play  •  Camera tracking  •  Classic consoles and 3D launcher', style='Subtitle.TLabel').pack(anchor='w', pady=(2, 16))
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

        self._build_camera_panel(left)
        self._build_game_panel(right)
        self._build_tracking_panel(right)
        self._build_safety_panel(right)

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


    def _build_game_panel(self, right):
        """Console selector, embedded display, and interactive ROM shelf."""
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
        self.external_setup = ttk.Frame(game)
        self.external_setup_label = ttk.Label(self.external_setup, text='', wraplength=430)
        self.external_setup_label.pack(fill='x', pady=(2, 4))
        external_actions = ttk.Frame(self.external_setup)
        external_actions.pack(fill='x')
        self.external_executable_button = ttk.Button(
            external_actions, text='Locate emulator executable',
            command=self.choose_external_executable)
        self.external_executable_button.pack(side='left', fill='x', expand=True)
        self.external_core_button = ttk.Button(
            external_actions, text='Locate N64 graphics core',
            command=self.choose_external_core)
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
        view_row = ttk.Frame(game)
        view_row.pack(fill='x', pady=(7, 0))
        ttk.Label(view_row, text='View mode:').pack(side='left', padx=(0, 6))
        view_combo = ttk.Combobox(view_row, textvariable=self.view_mode, state='readonly',
                                  values=['Windowed', 'Borderless', 'Fullscreen', 'Game only'],
                                  width=15)
        view_combo.pack(side='left', padx=(0, 8))
        view_combo.bind('<<ComboboxSelected>>', lambda _: self.set_view_mode())
        ttk.Button(view_row, text='Keyboard shortcuts',
                   command=self.configure_shortcuts).pack(side='right')
        # Embedded emulators use the existing on-canvas software-video renderer.
        self.game_canvas = tk.Canvas(game, bg='#0a1a30', height=350, highlightthickness=0)
        self.game_canvas.pack(fill='both', expand=True, pady=10)
        self.game_canvas.configure(takefocus=1, highlightthickness=2, highlightbackground='#23456f', highlightcolor='#5aa9ff')
        self.game_canvas.bind('<Button-1>', self.activate_manual)
        self.game_canvas.bind('<KeyPress>', self.manual_key_down)
        self.game_canvas.bind('<KeyRelease>', self.manual_key_up)
        self.game_canvas.bind('<FocusOut>', self.deactivate_manual)
        self.root.bind_all('<Button-1>', self.deactivate_on_outside_click, add='+')
        self.manual_label = tk.StringVar(value='Click game screen for manual controls · Open Keyboard shortcuts to customize')
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
