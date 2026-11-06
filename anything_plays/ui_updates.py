"""Nonblocking, opt-in-visible updater status for the 2.1 testing UI.

Automatic checks run at most once per 24 hours. The updater is intentionally
read-only: installing native libraries without a verified full app rebuild
would break bundle integrity or macOS code signing.
"""

import json
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import time
from tkinter import messagebox

from anything_plays.core_locator import _search_directories
from anything_plays.emulator_updates import (
    check_emulator_updates, summary_text,
)

CHECK_INTERVAL_SECONDS = 24 * 60 * 60


class UpdatesMixin:
    """Add a safe emulator-update check without slowing Tk or opening a game."""

    def schedule_emulator_update_checks(self):
        """Check again every 24 hours while the same application stays open."""
        if self._closing:
            return
        try:
            self.check_emulator_updates(automatic=True)
        finally:
            # One scheduled check at a time; do not accumulate timers on
            # machines that remain logged in for days or weeks.
            if not self._closing:
                self._updates_repeat_job = self.root.after(
                    CHECK_INTERVAL_SECONDS * 1000,
                    self.schedule_emulator_update_checks,
                )

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
        self._emulator_update_status.set("Checking emulator source updates…")
        results = Queue(maxsize=1)
        self._updates_result = results

        def worker():
            try:
                report = check_emulator_updates(_search_directories(), online=True)
                cache = {"checked_at_unix": time.time(), "report": report}
                temporary = cache_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(cache, indent=2), encoding="utf-8")
                temporary.replace(cache_path)
                results.put((report, None))
            except Exception as exc:
                results.put((None, str(exc)))

        Thread(target=worker, daemon=True, name="emulator-update-check").start()
        self.root.after(
            100, lambda: self._poll_emulator_updates(results, automatic)
        )

    def _poll_emulator_updates(self, results, automatic):
        if self._closing:
            return
        try:
            report, error = results.get_nowait()
        except Empty:
            self.root.after(
                120, lambda: self._poll_emulator_updates(results, automatic)
            )
            return
        self._updates_busy = False
        if error is not None:
            self._emulator_update_status.set("Update check unavailable")
            if not automatic:
                messagebox.showwarning(
                    "Emulator updates", "Could not check updates: " + error,
                    parent=self.root,
                )
            return
        count = sum(
            item["status"] == "review-upstream" for item in report["cores"]
        )
        self._emulator_update_status.set(
            "Emulator updates · " +
            (f"{count} source(s) changed; review before app update"
             if count else "Source check complete")
        )
        if not automatic:
            messagebox.showinfo(
                "Emulator update status", summary_text(report), parent=self.root
            )
