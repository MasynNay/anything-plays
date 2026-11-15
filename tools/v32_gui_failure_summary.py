"""Private installed-3.2 GUI failure classification: no raw error paths.

The frozen GUI writes a local JSON receipt into a disposable QA home. CI
prints only selected exception class, a recognized source filename, and a
bounded numeric line to help fix actual installed-app regressions. Raw
tracebacks or settings never leave that disposable test environment.
"""
import json
from pathlib import Path
import re

MAX_BYTES = 64 * 1024
KNOWN_FILES = frozenset((
    "preview_setup_smoke.py", "ui_profiles.py",
    "portable_profile_library.py", "system_profiles.py",
    "ui_panels.py", "frozen_gui_smoke.py",
    "verify_v32_installed_gui.py",
))
KNOWN_EXCEPTIONS = frozenset((
    "RuntimeError", "ValueError", "AttributeError", "TypeError",
    "OSError", "TclError", "FileNotFoundError", "AssertionError",
    "KeyError",
))
TRACE_LINE = re.compile(
    r'^\s*File "[^"]*[/\\]([^/\\"]+\.py)", line (\d+), in ([a-zA-Z_][a-zA-Z_0-9]*)',
    re.MULTILINE,
)
EXCEPTION_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9]*Error):", re.MULTILINE)


def summarize(path):
    result = {
        "status": "report_missing_or_invalid",
        "exception_class": "unavailable",
        "source_file": "unavailable",
        "source_line": None,
    }
    try:
        file = Path(path)
        if not file.is_file() or file.is_symlink():
            return result
        with file.open("rb") as reader:
            raw = reader.read(MAX_BYTES + 1)
        if not raw or len(raw) > MAX_BYTES:
            return result
        report = json.loads(raw)
        if not isinstance(report, dict):
            return result
        result["status"] = (
            "failed" if report.get("passed") is False else "no_failed_report"
        )
        trace = report.get("error")
        if not isinstance(trace, str):
            return result
        types = EXCEPTION_LINE.findall(trace)
        if types and types[-1] in KNOWN_EXCEPTIONS:
            result["exception_class"] = types[-1]
        frames = TRACE_LINE.findall(trace)
        for name, number, _function in reversed(frames):
            if name in KNOWN_FILES:
                result["source_file"] = name
                result["source_line"] = min(int(number), 100000)
                break
    except (OSError, ValueError, UnicodeError, TypeError, RecursionError):
        pass
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    args = parser.parse_args()
    print(json.dumps(summarize(args.report), sort_keys=True))
