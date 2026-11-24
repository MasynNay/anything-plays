"""Privacy-safe, actionable diagnostics for synchronous game launch failures.

Native exceptions frequently contain full ROM/library paths, USB hardware
identifiers and private filesystem information. No exception text, repr() or
custom __str__ methods may reach an application status label or Tk dialog.
"""


def _failure_category(exc):
    """Bounded exception family only, never extension-defined type names."""
    if isinstance(exc, PermissionError):
        return "PermissionError"
    if isinstance(exc, FileNotFoundError):
        return "FileNotFoundError"
    if isinstance(exc, TimeoutError):
        return "TimeoutError"
    if isinstance(exc, OSError):
        return "OSError"
    if isinstance(exc, ValueError):
        return "ValueError"
    if isinstance(exc, TypeError):
        return "TypeError"
    if isinstance(exc, RuntimeError):
        return "RuntimeError"
    return "UnexpectedError"


def safe_launch_failure(exc, *, external=False):
    """Return fixed guidance with no user-provided/native exception content."""
    category = _failure_category(exc)
    if external:
        return (
            "External emulator launch failed (" + category + "). "
            "Check the configured emulator executable, game file and "
            "permissions; then try again."
        )
    if category in ("FileNotFoundError", "PermissionError"):
        advice = (
            "Check that the selected game and bundled emulator files "
            "exist and are accessible, then retry."
        )
    elif category == "TimeoutError":
        advice = (
            "The emulator did not respond during startup. "
            "Try Restart game after the previous session finishes."
        )
    else:
        advice = (
            "Check the selected game and emulator setup, then choose "
            "Restart game after correcting the issue."
        )
    return "Game could not start (" + category + "). " + advice
