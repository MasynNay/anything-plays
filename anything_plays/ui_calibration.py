"""Non-modal, local camera calibration guide for Anything Plays 3.2.

The guide reuses the main preview and its existing color tracking results.
It does not create another VideoCapture, store any video, or arm game inputs.
"""

import copy
from collections import deque
import tkinter as tk
from tkinter import messagebox, ttk

from anything_plays.calibration_metrics import (
    calibration_advice, calibration_summary, stationary_tracking_summary,
)
from anything_plays.tracking import zone_at


# At ~30 camera FPS, collect about 1.5 seconds of position-only samples.
# This is intentionally NOT a timed frame-rate or device performance claim.
STATIONARY_SAMPLE_FRAMES = 45

_STEPS = (
    (
        "1 of 4  ·  CHOOSE YOUR CAMERA",
        "Select a webcam from the main Camera panel. Use camera there, "
        "or click the action below. Keep the target in even lighting.",
        "Use selected camera",
    ),
    (
        "2 of 4  ·  SAMPLE THE TARGET",
        "Click Pick target color, then click the actual fish, toy or hand "
        "in the main camera preview. Choose a distinctive color that "
        "contrasts with the background.",
        "Pick target color",
    ),
    (
        "3 of 4  ·  VERIFY LIVE TRACKING",
        "Move the object through several control zones in the main preview. "
        "This guide reports observed detection and zone hits without "
        "starting gameplay. Adjust tolerance or minimum area only if needed.",
        "Show advanced tuning",
    ),
    (
        "4 of 4  ·  SAVE YOUR CALIBRATION",
        "Review the observations, then save this console's color and "
        "detection settings. Start gameplay separately when you are ready.",
        "Review in preview",
    ),
)


class CalibrationMixin:
    """Tk helpers compatible with App's existing CameraMixin and Tk state."""

    def open_calibration_wizard(self):
        previous = getattr(self, "_calibration_window", None)
        if previous is not None:
            try:
                if previous.winfo_exists():
                    previous.lift()
                    previous.focus_set()
                    return
            except tk.TclError:
                pass

        self.stop_controls()
        try:
            # Capture the *visible* editor, including controls that have not
            # yet been written to disk. The guide is a temporary transaction,
            # not a request to throw away pre-existing unsaved edits.
            self._calibration_capture_original()
        except (OSError, ValueError, TypeError, tk.TclError):
            messagebox.showerror(
                "Camera calibration",
                "Correct the current console settings or profile storage "
                "before starting calibration. No changes were saved.",
                parent=self.root,
            )
            return
        self._calibration_history = deque(maxlen=90)
        self._calibration_stability_history = deque(
            maxlen=STATIONARY_SAMPLE_FRAMES
        )
        self._calibration_stability_running = False
        self._calibration_stability_result = None
        self._calibration_sampled = False
        self._calibration_step = 0
        self._calibration_after = None

        window = tk.Toplevel(self.root)
        self._calibration_window = window
        window.title("Guided camera calibration · Anything Plays 3.2")
        window.geometry("560x520")
        window.minsize(460, 430)
        window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self.close_camera_calibration(restore=True),
        )
        # Deliberately NOT modal / grabbed / always-on-top. The user must be
        # able to click a target color on the existing main preview.
        content = ttk.Frame(window, padding=18)
        content.pack(fill="both", expand=True)

        ttk.Label(
            content, text="Camera calibration", font=("TkDefaultFont", 17, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            content,
            text="Local preview only. Camera input is paused during setup.",
            style="Helper.TLabel", wraplength=500,
        ).pack(anchor="w", pady=(3, 14))

        self._calibration_heading = tk.StringVar(master=window)
        self._calibration_guidance = tk.StringVar(master=window)
        ttk.Label(
            content, textvariable=self._calibration_heading,
            style="Value.TLabel",
        ).pack(anchor="w", pady=(1, 7))
        ttk.Label(
            content, textvariable=self._calibration_guidance,
            wraplength=500, justify="left",
        ).pack(fill="x", anchor="w", pady=(0, 10))

        self._calibration_action_button = ttk.Button(
            content, command=self._calibration_action,
            style="Compact.TButton",
        )
        self._calibration_action_button.pack(fill="x", pady=(3, 12))

        diagnostics = ttk.LabelFrame(
            content, text="LIVE OBSERVATIONS · LAST 90 FRAMES", padding=12,
        )
        diagnostics.pack(fill="both", expand=True)
        self._calibration_diagnostics = tk.StringVar(
            master=window, value="Choose and start a webcam to see live results."
        )
        ttk.Label(
            diagnostics, textvariable=self._calibration_diagnostics,
            wraplength=480, justify="left",
        ).pack(anchor="w")
        self._calibration_advice = tk.StringVar(
            master=window, value="Sample a target color to begin."
        )
        ttk.Label(
            diagnostics, textvariable=self._calibration_advice,
            style="Value.TLabel", wraplength=475, justify="left",
        ).pack(anchor="w", pady=(9, 0))
        ttk.Label(
            diagnostics,
            text="Detection means a color match, not verified identification. "
                 "Motion per frame is not a measurement of tracking accuracy.",
            style="Helper.TLabel", wraplength=480, justify="left",
        ).pack(anchor="w", pady=(9, 0))
        ttk.Button(
            diagnostics, text="Check stationary jitter",
            command=self._calibration_begin_stability,
            style="Compact.TButton",
        ).pack(anchor="w", pady=(9, 0))
        self._calibration_stability_status = tk.StringVar(
            master=window,
            value="Optional: hold your sampled target still to measure "
                  "observed pixel variation. No camera images are stored.",
        )
        ttk.Label(
            diagnostics, textvariable=self._calibration_stability_status,
            style="Helper.TLabel", wraplength=480, justify="left",
        ).pack(anchor="w", pady=(4, 0))

        footer = ttk.Frame(content)
        footer.pack(fill="x", pady=(15, 0))
        ttk.Button(
            footer, text="Cancel", command=lambda:
            self.close_camera_calibration(restore=True),
        ).pack(side="left")
        self._calibration_back = ttk.Button(
            footer, text="Back",
            command=lambda: self._calibration_advance(-1),
        )
        self._calibration_back.pack(side="right", padx=(8, 0))
        self._calibration_next = ttk.Button(
            footer, text="Next",
            command=lambda: self._calibration_advance(1),
            style="Accent.TButton",
        )
        self._calibration_next.pack(side="right")
        self._calibration_render_step()
        self._calibration_refresh()

    def _calibration_capture_original(self):
        """Snapshot both the live editor and disk prior to camera calibration."""
        system = self.system_key.get()
        saved_profile = self.profile_store.get(system)
        self.read_settings()
        self._calibration_original = {
            "system": system,
            "profile": copy.deepcopy(self.cfg),
            "stored_profile": saved_profile,
            "rgb": list(self.cfg["rgb"]),
            "tolerance": int(self.tolerance.get()),
            "min_area": int(self.min_area.get()),
        }

    def _calibration_render_step(self):
        step = self._calibration_step
        heading, guidance, button = _STEPS[step]
        self._calibration_heading.set(heading)
        self._calibration_guidance.set(guidance)
        self._calibration_action_button.configure(text=button)
        self._calibration_back.configure(
            state="disabled" if step == 0 else "normal"
        )
        self._calibration_next.configure(
            text="Save & finish" if step == len(_STEPS) - 1 else "Next"
        )

    def _calibration_action(self):
        step = self._calibration_step
        if step == 0:
            self.start_camera()
        elif step == 1:
            self.pick_color()
            if self.frame is not None:
                self._calibration_diagnostics.set(
                    "Click your object in the MAIN camera preview, "
                    "then return here to continue."
                )
        elif step == 2:
            advanced = getattr(self, "advanced_tracking_controls", None)
            toggle = getattr(self, "advanced_tracking_expanded", None)
            if advanced is not None and toggle is not None:
                toggle.set(True)
                advanced.pack(fill="x", pady=(8, 0))
                self.status.set(
                    "Advanced detection settings expanded. "
                    "Changes are not committed until you finish calibration."
                )
        else:
            self.root.lift()

    def _calibration_advance(self, direction):
        if direction < 0:
            self._calibration_step = max(0, self._calibration_step - 1)
            self._calibration_render_step()
            return

        step = self._calibration_step
        if step == len(_STEPS) - 1:
            self._calibration_finish()
            return
        if step == 0 and self.cap is None:
            messagebox.showinfo(
                "Camera calibration",
                "Start the selected camera in the main window first.",
                parent=self._calibration_window,
            )
            return
        if step == 1 and not self._calibration_sampled:
            messagebox.showinfo(
                "Camera calibration",
                "Pick a target color from the live camera preview first.",
                parent=self._calibration_window,
            )
            return
        if step == 2:
            report = calibration_summary(self._calibration_history)
            if report["frames"] < 8 or report["seen"] == 0:
                messagebox.showinfo(
                    "Camera calibration",
                    "The guide needs eight live frames and at least one "
                    "target detection before you can save. Keep the target "
                    "in view, or sample its color again.",
                    parent=self._calibration_window,
                )
                return
        self._calibration_step += 1
        self._calibration_render_step()

    def _calibration_reset_stability(self, message=None):
        """Discard unfinished/old still-target measurements on device changes."""
        self._calibration_stability_running = False
        self._calibration_stability_result = None
        history = getattr(self, "_calibration_stability_history", None)
        if history is not None:
            history.clear()
        status = getattr(self, "_calibration_stability_status", None)
        if status is not None and message:
            status.set(message)

    def _calibration_begin_stability(self):
        """Start a new, explicitly requested live stationary-target probe."""
        if getattr(self, "_calibration_window", None) is None:
            return
        status = self._calibration_stability_status
        if self.cap is None:
            status.set("Start the webcam first; no stationary check is running.")
            return
        if not self._calibration_sampled:
            status.set("Sample the target color first, then keep it still.")
            return
        self._calibration_reset_stability()
        self._calibration_stability_running = True
        status.set(
            f"Keep the target still for {STATIONARY_SAMPLE_FRAMES} live frames. "
            "The app observes positions only; it does not record video."
        )

    def calibration_camera_changed(self):
        """Drop stale observations after camera stop, switch or reconnect."""
        if getattr(self, "_calibration_window", None) is None:
            return
        self._calibration_sampled = False
        self._calibration_history.clear()
        CalibrationMixin._calibration_reset_stability(
            self, "Camera changed. Restart the still-target check after sampling.",
        )
        self._calibration_step = min(self._calibration_step, 1)
        self._calibration_render_step()
        self._calibration_diagnostics.set(
            "Camera changed. Pick your target color again before continuing."
        )

    def calibration_color_sampled(self):
        """Invoked by the primary-color click handler, never by a thread."""
        if getattr(self, "_calibration_window", None) is None:
            return
        self._calibration_sampled = True
        self._calibration_history.clear()
        CalibrationMixin._calibration_reset_stability(
            self, "Color sampled. Keep it still and choose Check stationary jitter.",
        )
        self._calibration_diagnostics.set(
            "Target sampled. Watch the green tracking outline in the main "
            "preview, then move the object across the zones."
        )

    def calibration_note_frame(self, matches, mapping, size):
        """Record a tiny observation from the already completed tracking pass."""
        if getattr(self, "_calibration_window", None) is None or self.cap is None:
            return
        center = matches[0][0] if matches else None
        zone = (
            zone_at(center, size, self.cfg["zones"], mapping,
                    self.shuffle_enabled.get())
            if center is not None else None
        )
        self._calibration_history.append((center, zone))
        if getattr(self, "_calibration_stability_running", False):
            samples = self._calibration_stability_history
            samples.append(center)
            if len(samples) >= STATIONARY_SAMPLE_FRAMES:
                self._calibration_stability_running = False
                result = stationary_tracking_summary(samples)
                self._calibration_stability_result = result
                if result["median_deviation_px"] is None:
                    self._calibration_stability_status.set(
                        f"Only {result['seen']}/{result['frames']} frames had a "
                        "target match. Check lighting and contrast, then retry."
                    )
                else:
                    self._calibration_stability_status.set(
                        f"Still-target observation: {result['seen']}/"
                        f"{result['frames']} matched frames. Median position "
                        f"variation {result['median_deviation_px']} px; "
                        f"95th percentile {result['p95_deviation_px']} px. "
                        "Movement during the hold also affects these numbers; "
                        "this is not a tracking accuracy score."
                    )

    def _calibration_refresh(self):
        window = getattr(self, "_calibration_window", None)
        if window is None or getattr(self, "_closing", False):
            return
        if self.cap is None:
            self._calibration_diagnostics.set(
                "No live camera connected. Select a webcam in the main window."
            )
            self._calibration_advice.set(
                "Reconnect a camera and sample the target color again."
            )
        else:
            report = calibration_summary(self._calibration_history)
            self._calibration_advice.set(
                calibration_advice(report, sampled=self._calibration_sampled)
            )
            if not report["frames"]:
                text = "Waiting for live frames from the main preview…"
            else:
                zones = report["zone_hits"]
                strongest = ", ".join(
                    f"{name}: {hits}" for name, hits in
                    sorted(zones.items(), key=lambda item: -item[1])[:5]
                ) or "none yet"
                motion = report["average_motion_px"]
                text = (
                    f'Target observed: {report["seen"]}/{report["frames"]} '
                    f'frames ({report["detection_percent"]}%)\n'
                    f'Frames without target: {report["lost"]}\n'
                    f'Observed zone hits: {strongest}\n'
                    'Motion between detected frames: '
                    f'{motion if motion is not None else "not enough data"}'
                    + (' px/frame' if motion is not None else '')
                )
            self._calibration_diagnostics.set(text)
        self._calibration_after = self.root.after(
            300, self._calibration_refresh
        )

    def _calibration_finish(self):
        if self.cap is None:
            messagebox.showinfo(
                "Camera calibration",
                "Your camera is disconnected. Reconnect it and check "
                "tracking before saving.", parent=self._calibration_window,
            )
            return
        try:
            self.persist_system_profile()
        except (ValueError, OSError, tk.TclError) as exc:
            messagebox.showerror(
                "Camera calibration",
                f"Unable to save calibration settings: {exc}",
                parent=self._calibration_window,
            )
            return
        self.close_camera_calibration(restore=False)
        self.status.set(
            "Calibration saved for this console. Object controls remain paused."
        )

    def close_camera_calibration(self, *, restore=False):
        window = getattr(self, "_calibration_window", None)
        if window is None:
            return
        self._calibration_window = None
        job = getattr(self, "_calibration_after", None)
        self._calibration_after = None
        if job is not None:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass
        # The main UI can independently arm buttons while the non-modal
        # guide is visible. A close must always leave gameplay disarmed.
        if not getattr(self, "_closing", False):
            self.stop_controls()
        if restore:
            saved = self._calibration_original
            # Do not rebuild the prior profile from the newly selected
            # combobox or from half-finished calibration spinbox values.
            self.cfg = copy.deepcopy(saved["profile"])
            if self.system_key.get() == saved["system"]:
                self.refresh_settings()
            else:
                self.tolerance.set(saved["tolerance"])
                self.min_area.set(saved["min_area"])
                self.refresh_color()
            if self.pick_mode is True:
                self.pick_mode = False
            # Canceling a guide that made no durable changes must not write
            # to profile storage. If a separately bound advanced control
            # auto-saved during calibration, restore the exact pre-guide
            # on-disk profile rather than committing unsaved editor values.
            try:
                saved_disk = saved["stored_profile"]
                if self.profile_store.get(saved["system"]) != saved_disk:
                    self.profile_store.put(saved["system"], saved_disk)
            except (ValueError, TypeError, OSError, tk.TclError):
                self.status.set(
                    "Calibration canceled, but a temporary saved change "
                    "could not be rolled back. Check profile storage."
                )
            else:
                self.status.set(
                    "Calibration canceled. Pre-guide controls restored; "
                    "unsaved editor changes were kept."
                )
        self._calibration_history.clear()
        CalibrationMixin._calibration_reset_stability(self)
        try:
            window.destroy()
        except tk.TclError:
            pass
