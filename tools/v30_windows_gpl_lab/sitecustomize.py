"""Private Windows GPL-source research DLL loader bootstrap, never app runtime.

Python 3.8+ ctypes uses restricted Windows DLL lookup: PATH alone does NOT
authorize dependencies of a loaded Libretro core. This sitecustomize module
lives in a unique test-only directory and is enabled ONLY for source-built
MSYS2 homebrew CI with AP_V30_MINGW_CI_DLL_DIR set by that workflow.
It is never loaded by regular Anything Plays users or final installers.
"""
import os
from pathlib import Path

DLL_RESEARCH_HANDLES = []
if os.name == "nt" and os.environ.get("AP_V30_MINGW_CI_DLL_DIR"):
    _folder = Path(os.environ["AP_V30_MINGW_CI_DLL_DIR"]).resolve()
    if not _folder.is_dir() or not (_folder / "libstdc++-6.dll").is_file():
        raise RuntimeError("Missing trusted MSYS2 native DLL research directory")
    DLL_RESEARCH_HANDLES.append(os.add_dll_directory(str(_folder)))
