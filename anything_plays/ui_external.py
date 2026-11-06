"""Optional external 3D emulator setup and lifecycle.

RetroArch and Dolphin each run in their own window. Webcam button presses
cannot be sent to a separate process by this release's safe Libretro bridge.
"""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from anything_plays.external_emulators import ExternalLaunchError, launch
from anything_plays.systems import SYSTEMS


class ExternalBackendMixin:
    def update_external_setup(self):
        backend = SYSTEMS[self.system_key.get()].backend
        if backend != "libretro":
            # Do not present an enabled action that cannot control the game.
            self.arm_button.configure(state="disabled", text="Camera controls unavailable for external emulator")
            self.external_setup.pack(fill="x", pady=(0, 7))
            if backend == "retroarch":
                self.external_executable_button.configure(text="Locate RetroArch executable")
                self.external_core_button.pack(side="right", padx=(5, 0))
                self.external_setup_label.configure(
                    text="N64 uses RetroArch + Mupen64Plus-Next (external GPU window). "
                         "Configure controls and analog stick in RetroArch."
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
            self.external_process = launch(
                system, rom,
                executable=self.external_emulators.get(system) or None,
                n64_core=self.n64_core_override or None,
                fullscreen=self.view_mode.get() in ("Fullscreen", "Game only"),
                borderless=self.view_mode.get() == "Borderless",
            )
        except ExternalLaunchError as exc:
            self.game_status.set(str(exc))
            messagebox.showerror("External emulator setup", str(exc), parent=self.root)
            return False
        self.game_status.set(
            f"Launched {Path(rom).stem} in an external emulator. "
            "Use that emulator's keyboard/controller settings; "
            "Anything Plays does not send camera presses to another process."
        )
        return True

    def stop_external_emulator(self):
        process = getattr(self, "external_process", None)
        self.external_process = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
        except OSError:
            pass
