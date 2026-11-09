"""Nonblocking core updates for the 3.0 preview application.

An ordinary upstream commit is NOT an approved binary update. The check UI
lists installed provenance, then separately looks for vetted core-pack assets
on Anything Plays' own GitHub releases. Installation is user-confirmed,
hash-verified, off the Tk thread and forbidden during native emulation.
"""
from __future__ import annotations

import json
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import time
from tkinter import messagebox

from anything_plays.core_locator import _search_directories
from anything_plays.core_packs import (
    discover_core_packs, install_core_pack, installed_pack_revision,
    rollback_core, managed_core_path,
)
from anything_plays.emulator_updates import (
    check_emulator_updates, summary_text,
)

CHECK_INTERVAL_SECONDS = 24 * 60 * 60
class UpdatesMixin:
    """Never stall the Tk event loop or swap a loaded native emulator."""

    def schedule_emulator_update_checks(self):
        if self._closing:
            return
        try:
            self.check_emulator_updates(automatic=True)
        finally:
            if not self._closing:
                self._updates_repeat_job = self.root.after(
                    CHECK_INTERVAL_SECONDS * 1000,
                    self.schedule_emulator_update_checks,
                )

    def _can_update_emulators(self):
        native = getattr(self, "emu", None)
        if native is not None and (
            getattr(native, "running", False)
            or (getattr(native, "thread", None) is not None
                and native.thread.is_alive())
        ):
            return False
        if getattr(self, "current_rom", None):
            return False
        if getattr(self, "external_process", None) is not None:
            return False
        return True

    def check_emulator_updates(self, automatic=False):
        if self._closing or getattr(self, "_updates_busy", False):
            return
        cache_path = self.preferences_path.with_name("emulator_updates.json")
        if automatic and cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                checked = float(cached.get("checked_at_unix", 0))
                if 0 <= time.time() - checked < CHECK_INTERVAL_SECONDS:
                    self._emulator_update_status.set(
                        "Emulator sources checked recently · Check updates for details"
                    )
                    return
            except (OSError, ValueError, TypeError):
                pass

        self._updates_busy = True
        self._emulator_update_status.set("Checking installed cores and approved updates…")
        results = Queue(maxsize=1)
        self._updates_result = results

        def worker():
            try:
                report = check_emulator_updates(_search_directories(), online=True)
                approved_error = None
                try:
                    available = [
                        item for item in discover_core_packs()
                        if item["name"] not in FULL_APP_ONLY
                        and installed_pack_revision(item["name"]) != item["sha256"]
                    ]
                except (OSError, ValueError, TimeoutError) as exc:
                    available = []
                    approved_error = str(exc)
                cache = {"checked_at_unix": time.time(), "report": report}
                temporary = cache_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(cache, indent=2), encoding="utf-8")
                temporary.replace(cache_path)
                results.put((report, available, approved_error, None))
            except Exception as exc:
                results.put((None, [], None, str(exc)))

        Thread(target=worker, daemon=True, name="emulator-update-check").start()
        self.root.after(100, lambda: self._poll_emulator_updates(results, automatic))

    def _poll_emulator_updates(self, results, automatic):
        if self._closing:
            return
        try:
            report, approved, approved_error, error = results.get_nowait()
        except Empty:
            self.root.after(120, lambda: self._poll_emulator_updates(results, automatic))
            return
        self._updates_busy = False
        if error is not None:
            self._emulator_update_status.set("Update check unavailable")
            if not automatic:
                messagebox.showwarning("Emulator updates",
                                       "Could not check updates: " + error,
                                       parent=self.root)
            return

        self._available_core_packs = approved
        changed = sum(x["status"] == "review-upstream" for x in report["cores"])
        self._emulator_update_status.set(
            f"Emulators · {len(approved)} approved in-app update(s)"
            + (f" · {changed} upstream source(s) changed" if changed else "")
            + (" · GitHub release check unavailable" if approved_error else "")
        )
        if not automatic:
            detail = summary_text(report)
            detail += f"\n\nInstallable approved core packs: {len(approved)}."
            if approved:
                detail += "\n" + "\n".join(
                    f"• {item['name']} ({item['release']})" for item in approved
                )
            else:
                detail += "\nNo separately vetted update packs are published for this platform."
            detail += (
                "\nGameCube core and Sys assets update together in a complete "
                "vetted application release."
            )
            if approved_error:
                detail += "\nCouldn't check released core packs: " + approved_error
            messagebox.showinfo("Emulator update status", detail, parent=self.root)

    def install_emulator_updates(self):
        if self._closing or getattr(self, "_updates_busy", False):
            return
        if not self._can_update_emulators():
            messagebox.showwarning(
                "Emulator updates",
                "Unload the running game before installing emulator updates.",
                parent=self.root,
            )
            return
        packages = list(getattr(self, "_available_core_packs", []))
        if not packages:
            messagebox.showinfo(
                "Emulator updates",
                "No approved core packs are available yet. Choose "
                "'Check emulator updates' to look for newly published packs.",
                parent=self.root,
            )
            return
        if not messagebox.askyesno(
            "Install approved emulator updates",
            f"Install {len(packages)} verified emulator update(s) inside Anything Plays?\n\n"
            "No separate emulator installation is needed. The updates take "
            "effect the next time you load a game, and the bundled originals "
            "are preserved for rollback.",
            parent=self.root,
        ):
            return

        self._updates_busy = True
        self._core_install_busy = True
        self._emulator_update_status.set(
            f"Installing {len(packages)} approved core pack(s)…"
        )
        results = Queue(maxsize=1)

        def worker():
            success, failures = [], []
            for pack in packages:
                try:
                    # Use a versioned user-owned install. Never replace a
                    # library currently loaded in the Tk process.
                    installed = install_core_pack(pack)
                    success.append((pack["name"], installed))
                except Exception as exc:
                    failures.append((pack["name"], str(exc)))
            results.put((success, failures))

        Thread(target=worker, daemon=True, name="emulator-core-install").start()
        self.root.after(150, lambda: self._poll_core_install(results))

    def _poll_core_install(self, results):
        if self._closing:
            return
        try:
            installed, failures = results.get_nowait()
        except Empty:
            self.root.after(150, lambda: self._poll_core_install(results))
            return
        self._updates_busy = False
        self._core_install_busy = False
        successful = {name for name, _ in installed}
        self._available_core_packs = [
            p for p in getattr(self, "_available_core_packs", [])
            if p["name"] not in successful
        ]
        # Switching the pointer in core_locator is enough; next ROM launch
        # re-evaluates it. The Tk app and game library stay open and intact.
        if installed and hasattr(self, "emu"):
            self.emu.core_path = self.emu.find_system_core()
        self.refresh_selected_emulator_state()
        self._emulator_update_status.set(
            f"Installed {len(installed)} core update(s)"
            + (f" · {len(failures)} failed" if failures else " · Ready for next game")
        )
        body = "\n".join(name for name, _ in installed)
        if failures:
            body += "\n\nErrors:\n" + "\n".join(
                f"{name}: {error}" for name, error in failures
            )
            messagebox.showwarning("Emulator update results", body, parent=self.root)
        else:
            messagebox.showinfo(
                "Emulator updates installed",
                "Updated cores:\n" + body + "\n\nLoad a game to use the new core.",
                parent=self.root,
            )

    def restore_bundled_emulator(self):
        if self._closing or getattr(self, "_updates_busy", False):
            return
        if not self._can_update_emulators():
            messagebox.showwarning(
                "Restore emulator",
                "Unload the game before restoring the bundled emulator.",
                parent=self.root,
            )
            return
        from anything_plays.systems import SYSTEMS
        key = self.system_key.get()
        name = "parallel_n64" if key == "n64" else SYSTEMS[key].core
        if not managed_core_path(name):
            messagebox.showinfo(
                "Restore emulator", "This console is already using its bundled core.",
                parent=self.root,
            )
            return
        if not messagebox.askyesno(
            "Restore emulator",
            f"Restore {name} to its previous verified version or the bundled original?",
            parent=self.root,
        ):
            return
        try:
            rollback_core(name)
            self.emu.core_path = self.emu.find_system_core()
            self._emulator_update_status.set(
                f"{name} restored · Ready for next game"
            )
            self.refresh_selected_emulator_state()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Restore emulator", str(exc), parent=self.root)

    def _selected_core_name(self):
        """Resolve every console shelf to its embedded native core."""
        from anything_plays.systems import SYSTEMS
        system = self.system_key.get()
        return "parallel_n64" if system == "n64" else SYSTEMS[system].core

    def refresh_selected_emulator_state(self):
        """Show offline emulator health, never offer mandatory first-run downloads."""
        status = getattr(self, "_selected_emulator_status", None)
        if status is None:
            return
        system = self.system_key.get()
        core = self._selected_core_name()
        from anything_plays.core_locator import find_core
        from anything_plays.n64_software import find_parallel_n64_core
        installed = (find_parallel_n64_core() if system == "n64"
                     else find_core(system))
        if installed:
            status.set("Ready inside Anything Plays · " + core)
        elif getattr(self, "_core_install_busy", False):
            status.set("Installing an approved emulator update…")
        else:
            # The full 3.0 installer has ALL 11 cores. Missing binaries
            # indicate corruption/packaging failure, not an optional feature.
            status.set("Emulator files missing · repair or reinstall Anything Plays")

