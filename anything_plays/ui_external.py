"""3D emulator launch and experimental camera gamepad bridges.

Hardware GPU games still render in their own windows; only controller input
is relayed from Anything Plays via RetroPad or the Dolphin POSIX pipe.
"""
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

from anything_plays.external_emulators import ExternalLaunchError, launch
from anything_plays.remote_retropad import N64RemoteController, write_retroarch_config
from anything_plays.dolphin_pipe import DolphinPipeController
from anything_plays.systems import SYSTEMS
from anything_plays.launch_error_messages import safe_launch_failure


class ExternalBackendMixin:
    """3D software-video modes with optional developer GPU fallbacks."""

    def _switch_3d_backend(self, system):
        """Select a 3D renderer without disturbing other console settings."""
        if self.system_key.get() != system:
            return False
        fallback = bool(getattr(self, "external_fallback_enabled", False))
        selection = (
            self.n64_embedded if system == "n64" else self.gamecube_embedded
        )
        # This callback belongs to a Tk Checkbutton: the new boolean is
        # already applied when we run. On a rejected switch roll the widget
        # back to the *previous* backend rather than leaving it pointing at
        # an external process while the embedded core is still alive.
        prior_selected = not bool(selection.get()) if fallback else True
        if not fallback:
            # External launchers are not an acceptable user-facing fallback:
            # select the packaged core even if old test preferences said no.
            self.n64_embedded.set(True)
            self.gamecube_embedded.set(True)
        self.stop_controls()
        try:
            unloaded = self.unload_rom()
        except Exception:
            unloaded = False
        if unloaded is False:
            selection.set(prior_selected)
            self.game_status.set(
                "Backend switch canceled: the previous emulator could not "
                "finish shutting down. Retry after it stops."
            )
            return False
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
        return True

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
        # Confirm the native worker has exited BEFORE retiring any existing
        # external fallback. A timed-out or failing native Stop must not
        # unexpectedly kill a healthy Dolphin/RetroArch game. Legacy idle
        # facades returning None are still treated as completed.
        try:
            stopped = self.emu.stop()
        except Exception:
            stopped = False
        if stopped is False:
            # Never copy an exception string containing ROM or device paths
            # into Tk; leave the old external process and bridge untouched.
            self.game_status.set(
                "Previous emulator is still shutting down. "
                "Existing external game retained; retry after it finishes."
            )
            return False
        self.stop_external_emulator()
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
            # Use the same independently fault-isolated IPC and process
            # teardown as Stop. A controller bridge can fail during startup
            # and then fail again during close(); never orphan the process.
            self.stop_external_emulator()
            # Launch/OS errors can embed private local paths and device IDs.
            # Do not evaluate or display exception strings, even when a
            # third-party extension provides a broken __str__ method.
            detail = safe_launch_failure(exc, external=True)
            self.game_status.set(detail)
            messagebox.showerror("External emulator setup", detail, parent=self.root)
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
        """Retire both external resources even if either native hook fails.

        A detached/closed Dolphin or RetroPad bridge can raise on close().
        That must never prevent an independent emulator process from being
        terminated. Detach both references first so repeated Stop is safe.
        No native exception strings or private device paths reach the UI.
        """
        input_bridge = getattr(self, "external_input", None)
        process = getattr(self, "external_process", None)
        self.external_input = None
        self.external_process = None
        if input_bridge is not None:
            try:
                input_bridge.close()
            except Exception:
                # A failed IPC bridge release cannot hold the emulator alive.
                pass
        if process is None:
            return
        try:
            running = process.poll() is None
        except Exception:
            # A faulty status handle must not skip the shutdown request.
            running = True
        if not running:
            return
        try:
            process.terminate()
        except Exception:
            # It might have exited between poll() and terminate(). Avoid a
            # forceful signal when a completed process can be confirmed.
            try:
                if process.poll() is not None:
                    return
            except Exception:
                pass
            try:
                process.kill()
            except Exception:
                pass
            return
        # Wait only a bounded interval inside the Tk callback. Hung GPU
        # processes must not survive indefinitely after a polite request.
        wait = getattr(process, "wait", None)
        if not callable(wait):
            return  # Legacy/custom process facades have no wait hook.
        try:
            wait(timeout=0.6)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except Exception:
                pass
            try:
                wait(timeout=0.25)
            except Exception:
                pass
        except Exception:
            # Even a broken wait wrapper may leave the original process live.
            try:
                if process.poll() is not None:
                    return
            except Exception:
                pass
            try:
                process.kill()
            except Exception:
                pass
