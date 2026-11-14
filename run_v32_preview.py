"""Start the unreleased 3.2 source preview with isolated local preferences.

Usage (after installing the repository's normal Python requirements):
    python run_v32_preview.py

This source-only entrypoint does not change 3.1/3.1.1 installers, public tags,
release update channels, or system-wide input. The preview never imports
settings from an installed stable version.
"""

import os


def main():
    # Set before importing App: it loads the embedded/source identity and
    # selects the matching per-channel settings folder during construction.
    os.environ["AP_V32_PREVIEW"] = "1"
    from app import main as start_app
    return start_app()


if __name__ == "__main__":
    raise SystemExit(main())
