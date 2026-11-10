"""Fail closed when generated binaries or unrelated files enter the source tree.

Run with: python tools/check_repository_hygiene.py
CI checks the tracked Git index, not the developer's ignored local files.
The allowlist intentionally preserves conventional repository entry points
and keeps native emulator binaries in reproducible build artifacts only.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = frozenset({
    ".gitattributes", ".gitignore",
    "LICENSE", "README.md", "app.py", "fetch_mgba_core.py",
    "requirements-build.txt", "requirements.txt", "verify_bundle.py",
})
ROOT_DIRECTORIES = frozenset({
    ".github", "anything_plays", "assets", "config", "cores",
    "docs", "licenses", "packaging", "site", "tests", "tools",
})
FORBIDDEN_SUFFIXES = frozenset({
    ".deb", ".dmg", ".exe", ".msi", ".pkg", ".whl", ".zip", ".7z",
    ".rar", ".iso", ".rom", ".gba", ".gbc", ".gb", ".nes", ".sfc",
    ".smc", ".n64", ".z64", ".v64", ".gcm", ".gcz", ".ngp", ".ngc",
    ".dll", ".dylib", ".so", ".pyc", ".pyo",
})
GENERATED_PARTS = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".build-venv", ".venv", "node_modules",
})
# Core libraries are downloaded at build time. The source tree must NEVER
# contain native binaries or copied system data.
CORE_TRACKED_ALLOWLIST = frozenset({"cores/.gitkeep"})


def scan_tracked_paths(paths: list[str]) -> list[str]:
    """Return deterministic violations without scanning ignored work files."""
    violations: list[str] = []
    for name in sorted(set(paths)):
        if not name or name.startswith("/") or "\\" in name:
            violations.append(f"Invalid repository path: {name!r}")
            continue
        pieces = name.split("/")
        if any(part in ("", ".", "..") for part in pieces):
            violations.append(f"Invalid repository path: {name!r}")
            continue
        if len(pieces) == 1:
            if name not in ROOT_FILES:
                violations.append(f"Unexpected root file: {name}")
        elif pieces[0] not in ROOT_DIRECTORIES:
            violations.append(f"Unexpected root directory: {pieces[0]}/")
        if any(part in GENERATED_PARTS for part in pieces):
            violations.append(f"Generated cache checked in: {name}")
        if name.startswith("cores/") and name not in CORE_TRACKED_ALLOWLIST:
            violations.append(f"Downloaded core data checked in: {name}")
        if Path(name).suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(f"Installer, emulator, or ROM binary checked in: {name}")
    return violations


def tracked_files(root: Path = ROOT) -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z", "--cached"],
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Repository hygiene requires a Git checkout") from exc
    return [value.decode("utf-8", "surrogateescape")
            for value in output.split(b"\0") if value]


def main() -> int:
    try:
        paths = tracked_files()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    violations = scan_tracked_paths(paths)
    if violations:
        for violation in violations:
            print(f"Repository hygiene: {violation}", file=sys.stderr)
        return 1
    print(f"Repository hygiene passed: {len(paths)} tracked files in approved locations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
