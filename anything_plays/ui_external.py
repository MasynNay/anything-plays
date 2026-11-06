"""Optional external 3D emulator setup and lifecycle.

RetroArch and Dolphin each run in their own window. Webcam button presses
cannot be sent to a separate process by this release's safe Libretro bridge.
"""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from anything_plays.external_emulators import ExternalLaunchError, launch
from anything_plays.remote_retropad import N64RemoteController, write_retroarch_config
from anything_plays.systems import SYSTEMS


class ExternalBackendMixin:
    def update_external_setup(self):
        backend = SYSTEMS[self.system_key.get()].backend
        if backend != "libretro":
            # N64 has an app-local camera / keyboard RetroPad bridge. Dolphin
            # does not yet have equivalent gamepad injection.
            available = backend == "retroarch"
            self.arm_button.configure(
                state="normal" if available else "disabled",
                text="Enable object controls" if available else
                     "Camera controls unavailable for Dolphin",
            )
            self.shortcuts_button.configure(
                state="normal" if available else "disabled"
            )
            self.external_setup.pack(fill="x", pady=(0, 7))
            if backend == "retroarch":
                self.external_executable_button.configure(text="Locate RetroArch executable")
                self.external_core_button.pack(side="right", padx=(5, 0))
                self.external_setup_label.configure(
                    text="N64 graphics run in RetroArch. Anything Plays sends camera and "
                         "keyboard controls through a local RetroPad bridge; "
                         "the game video remains in RetroArch's window."
                )
            else:
                self.external_executable_button.configure(text="Locate Dolphin executable")
                self.external_core_button.pack_forget()
                self.external_setup_label.configure(
                    text="GameCube launches in Dolphin's own 3D window. "
                         "Configure keyboard or a controller in Dolphin."
                )
        else:
            self.arm_button.configure(state="normal", text="Enable object controls")
            self.shortcuts_button.configure(state="normal")
            self.external_setup.pack_forget()

    def choose_external_executable(self):
        system = self.system_key.get()
        if SYSTEMS[system].backend == "libretro":
            return
        file = filedialog.askopenfilename(
            parent=self.root,
            title="Select " + ("RetroArch" if system == "n64" else "Dolphin") + " executable"
        )
        if file:
            self.external_emulators[system] = file
            self.save_preferences()
            self.game_status.set("Configured " + Path(file).name)

    def choose_external_core(self):
        if self.system_key.get() != "n64":
            return
        file = filedialog.askopenfilename(
            parent=self.root, title="Select your RetroArch Mupen64Plus-Next core",
            filetypes=[("Libretro cores", "*.so *.dll *.dylib"), ("All files", "*")]
        )
        if file:
            self.n64_core_override = file
            self.save_preferences()
            self.game_status.set("Selected N64 graphics core: " + Path(file).name)

    def start_external_rom(self, rom):
        system = self.system_key.get()
        self.stop_external_emulator()
        self.emu.stop()
        try:
            network_config = None
            if system == "n64":
                network_config = write_retroarch_config(
                    self.preferences_path.with_name("n64-retropad.cfg")
                )
            self.external_process = launch(
                system, rom,
                executable=self.external_emulators.get(system) or None,
                n64_core=self.n64_core_override or None,
                fullscreen=self.view_mode.get() in ("Fullscreen", "Game only"),
                borderless=self.view_mode.get() == "Borderless",
                network_config=network_config,
            )
            if system == "n64":
                self.external_input = N64RemoteController()
                self.external_input.start()
        except ExternalLaunchError as exc:
            self.game_status.set(str(exc))
            messagebox.showerror("External emulator setup", str(exc), parent=self.root)
            return False
        self.game_status.set(
            f"Launched {Path(rom).stem} in an external emulator. "
            + ("Camera/keyboard controls are available in Anything Plays; "
               "RetroArch displays the N64 game in its own GPU window."
               if system == "n64" else
               "Configure keyboard/controller input in Dolphin.")
        )
        return True

    def stop_external_emulator(self):
        input_bridge = getattr(self, "external_input", None)
        self.external_input = None
        if input_bridge is not None:
            input_bridge.close()
        process = getattr(self, "external_process", None)
        self.external_process = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
        except OSError:
            pass
