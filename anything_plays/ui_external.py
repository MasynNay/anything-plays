"""3D emulator launch and experimental camera gamepad bridges.

Hardware GPU games still render in their own windows; only controller input
is relayed from Anything Plays via RetroPad or the Dolphin POSIX pipe.
"""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

from anything_plays.external_emulators import ExternalLaunchError, launch
from anything_plays.remote_retropad import N64RemoteController, write_retroarch_config
from anything_plays.dolphin_pipe import DolphinPipeController
from anything_plays.systems import SYSTEMS


class ExternalBackendMixin:
    """3D software-video modes with optional developer GPU fallbacks."""

    def _switch_3d_backend(self, system):
        """Select a 3D renderer without disturbing other console settings."""
        if self.system_key.get() != system:
            return
        if not getattr(self, "external_fallback_enabled", False):
            # External launchers are not an acceptable user-facing fallback:
            # select the packaged core even if old test preferences said no.
            self.n64_embedded.set(True)
            self.gamecube_embedded.set(True)
        self.stop_controls()
        self.unload_rom()
        if not self.uses_embedded_emulator() and self.view_mode.get() == "Game only":
            self.set_view_mode("Windowed")
        self.save_preferences()
        self.update_external_setup()
        self.game_canvas.delete("all")
        self.show_external_placeholder()
        name = "GameCube" if system == "gamecube" else "N64"
        if self.uses_embedded_emulator():
            self.game_status.set(
                (
                    "GameCube accelerated graphics selected. Choose a ROM "
                    "to play inside the game panel."
                    if system == "gamecube" else
                    f"{name} software graphics selected. Choose a ROM "
                    "to try it inside the game panel."
                )
            )
        else:
            program = "Dolphin" if system == "gamecube" else "RetroArch"
            self.game_status.set(
                f"{name} external developer fallback selected; "
                f"{program} must be installed separately."
            )

    def switch_n64_backend(self):
        self._switch_3d_backend("n64")

    def switch_gamecube_backend(self):
        self._switch_3d_backend("gamecube")

    def update_external_setup(self):
        # Keep the GPU preview tradeoff visible only while GameCube is the
        # active embedded console. Other emulators retain their own display
        # timing and settings.
        preview_row = getattr(self, "gamecube_preview_row", None)
        if preview_row is not None:
            if (self.system_key.get() == "gamecube"
                    and self.uses_embedded_emulator()):
                preview_row.pack(fill="x", pady=(11, 0))
            else:
                preview_row.pack_forget()
        backend = SYSTEMS[self.system_key.get()].backend
        if (self.system_key.get() == "n64" and
                getattr(self, "external_fallback_enabled", False)):
            self.n64_mode_row.pack(fill="x", pady=(0, 6))
            self.system_description.configure(
                text="Nintendo 64 · Built-in test"
                if self.uses_embedded_emulator() else
                "Nintendo 64 · RetroArch fallback"
            )
        else:
            self.n64_mode_row.pack_forget()
        if (self.system_key.get() == "gamecube" and
                getattr(self, "external_fallback_enabled", False)):
            self.gamecube_mode_row.pack(fill="x", pady=(0, 6))
            self.system_description.configure(
                text="Nintendo GameCube · Embedded accelerated graphics"
                if self.uses_embedded_emulator() else
                "Nintendo GameCube · Dolphin fallback"
            )
        else:
            self.gamecube_mode_row.pack_forget()
        if (not getattr(self, "external_fallback_enabled", False)
                and backend in ("retroarch", "dolphin")):
            # This can only happen with a corrupt test preference or a
            # developer forcibly changing a Tk value. Never ask a regular
            # player to locate another executable.
            self.n64_embedded.set(True)
            self.gamecube_embedded.set(True)
            self.external_setup.pack_forget()
            self.arm_button.configure(state="normal", text="Enable object controls")
            self.shortcuts_button.configure(state="normal")
            return
        if self.uses_embedded_emulator():
            self.arm_button.configure(state="normal", text="Enable object controls")
            self.shortcuts_button.configure(state="normal")
            self.external_setup.pack_forget()
            return
        if backend != "libretro":
            # N64 uses Remote RetroPad; Dolphin uses an isolated named pipe.
            # Dolphin's pipe backend is only supported on Unix-like systems.
            available = backend == "retroarch" or (
                backend == "dolphin" and sys.platform != "win32"
            )
            self.arm_button.configure(
                state="normal" if available else "disabled",
                text="Enable object controls" if available else
                     "Camera controls unavailable on this platform",
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
                    text=(
                        "GameCube graphics run in Dolphin. Anything Plays sends "
                        "camera and keyboard controls through a private controller "
                        "pipe; Dolphin displays the game in its own window."
                        if sys.platform != "win32" else
                        "GameCube runs in Dolphin's window. Windows pipe input "
                        "integration is not currently supported."
                    )
                )
        else:
            self.arm_button.configure(state="normal", text="Enable object controls")
            self.shortcuts_button.configure(state="normal")
            self.external_setup.pack_forget()

    def show_external_placeholder(self):
        """Make clear why the native game canvas has no video for 3D consoles."""
        backend = SYSTEMS[self.system_key.get()].backend
        if self.uses_embedded_emulator():
            return
        canvas = self.game_canvas
        canvas.delete("all")
        width = max(340, canvas.winfo_width())
        height = max(180, canvas.winfo_height())
        label = "NINTENDO 64" if backend == "retroarch" else "NINTENDO GAMECUBE"
        canvas.create_text(
            width // 2, height // 2 - 20,
            text=label, fill="#eef4ff", font=("Arial", 17, "bold"),
            anchor="center",
        )
        canvas.create_text(
            width // 2, height // 2 + 26,
            text=("Game video uses a separate GPU window.\n"
                  "The camera zones and keyboard controls remain in Anything Plays.\n"
                  "Launch a cartridge below to start playing."),
            fill="#afc6e3", font=("Arial", 12),
            justify="center", width=max(200, width - 40),
        )

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
            dolphin_user = None
            if system == "n64":
                network_config = write_retroarch_config(
                    self.preferences_path.with_name("n64-retropad.cfg")
                )
            elif system == "gamecube" and sys.platform != "win32":
                dolphin_user = self.preferences_path.parent / "dolphin-user"
                self.external_input = DolphinPipeController(dolphin_user)
            self.external_process = launch(
                system, rom,
                executable=self.external_emulators.get(system) or None,
                n64_core=self.n64_core_override or None,
                fullscreen=self.view_mode.get() in ("Fullscreen", "Game only"),
                borderless=self.view_mode.get() == "Borderless",
                network_config=network_config,
                dolphin_user=dolphin_user,
            )
            if system == "n64":
                self.external_input = N64RemoteController()
            if self.external_input is not None:
                self.external_input.start()
        except (ExternalLaunchError, OSError, RuntimeError) as exc:
            if self.external_input is not None:
                self.external_input.close()
                self.external_input = None
            process = self.external_process
            self.external_process = None
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
            self.game_status.set(str(exc))
            messagebox.showerror("External emulator setup", str(exc), parent=self.root)
            return False
        self.show_external_placeholder()
        self.game_status.set(
            f"Launched {Path(rom).stem} in an external emulator. "
            + ("Camera/keyboard controls are available in Anything Plays; "
               "the game is displayed in the external GPU window."
               if self.external_input is not None else
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
