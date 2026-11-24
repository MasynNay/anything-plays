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


# These messages are generated from exact internal GameCube error categories;
# never trust a fuzzy prefix or arbitrary native text to be "safe".
_SAFE_GAMECUBE_WORKER_ERRORS = frozenset((
    "GameCube GPU hardware context negotiation failed.",
    "GameCube needs a GPU driver with OpenGL 3.3 or newer. "
    "Install or update the graphics driver and restart Anything Plays.",
    "GameCube could not initialize the accelerated GPU context.",
))
_SAFE_WORKER_CATEGORIES = frozenset((
    "RuntimeError", "OSError", "ValueError", "TypeError",
    "MemoryError", "ImportError", "FileNotFoundError",
    "AttributeError", "OverflowError", "IndexError",
    "KeyError", "AssertionError", "UnexpectedError",
))


def safe_worker_failure(error, *, starting=False):
    """Render only approved native error classes and fixed GPU guidance.

    Other consoles retain legacy internal exception details for compatibility,
    but GUI status, screenshots and dialogs must never expose those details.
    No native exception text, ROM location or device string is echoed.
    """
    import re

    prefix = "Emulator launch failed: " if starting else "Emulator stopped: "
    if type(error) is str:
        if error in _SAFE_GAMECUBE_WORKER_ERRORS:
            detail = error
        elif re.fullmatch(
            r"GameCube GPU readback failed \("
            r"(RuntimeError|ValueError|OSError|TypeError|OverflowError|"
            r"MemoryError|AttributeError|IndexError|KeyError|"
            r"AssertionError|UnexpectedError)\)\.",
            error,
        ):
            detail = error
        elif re.fullmatch(
            r"GameCube native playback failed \("
            r"(RuntimeError|OSError|ValueError|TypeError|MemoryError|"
            r"ImportError|FileNotFoundError|AttributeError|"
            r"OverflowError|UnexpectedError)\)\.",
            error,
        ):
            detail = error
        else:
            # Native _run may retain f"{type(exc).__name__}: {exc}" for
            # internal compatibility, but the second half is untrusted.
            category = error.partition(":")[0]
            if category in _SAFE_WORKER_CATEGORIES:
                detail = "Native emulator error (" + category + ")."
            else:
                detail = "Native emulator error (UnexpectedError)."
    else:
        detail = "Native emulator error (UnexpectedError)."
    return prefix + detail + " Select Restart game to recover."
