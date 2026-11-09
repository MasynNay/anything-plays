"""Apply one precisely-reviewed research-only Supafaust macOS semaphore fix.

At upstream commit 642d1d1..., mednafen/config.h defines
HAVE_SEM_TIMEDWAIT for macOS, but Darwin does not supply that function.
Mednafen already provides a pthread-condition-variable semaphore fallback.
Disable the feature macro on macOS only; no other code is modified.

THIS MODIFIES ONE FILE IN THE EPHEMERAL SOURCE CHECKOUT; capture requires
and preserves the resulting exact Git patch. It is NOT an approval to
redistribute this candidate as part of Anything Plays.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

REPO = "https://github.com/libretro/supafaust"
COMMIT = "642d1d1b6684aa7e306a02a89885f3f5456a5157"
TARGET = "mednafen/config.h"
BEFORE = "#if !defined(__SWITCH__) && !defined(HAVE_LIBNX)"
AFTER = "#if !defined(__SWITCH__) && !defined(HAVE_LIBNX) && !defined(__APPLE__)"


def git(root, *args):
    p=subprocess.run(["git","-C",str(root),*args],check=True,
                     capture_output=True,text=True,timeout=30)
    return p.stdout.strip()


def apply_exact_macos_fix(source):
    source=Path(source).expanduser()
    if not source.is_dir() or source.is_symlink():
        raise ValueError("Expected original non-symlink upstream checkout")
    source=source.resolve()
    if git(source,"rev-parse","HEAD") != COMMIT:
        raise ValueError("Original upstream Supafaust commit changed")
    if git(source,"remote","get-url","origin").rstrip("/").removesuffix(".git")!=REPO:
        raise ValueError("Original upstream Supafaust repository changed")
    if git(source,"status","--porcelain","--untracked-files=no"):
        raise ValueError("Original tracked source must be pristine before patch")
    path=source/TARGET
    if not path.is_file() or path.is_symlink():
        raise ValueError("Cannot find original upstream config.h")
    original=path.read_text("utf-8")
    if original.count(BEFORE)!=1 or AFTER in original:
        raise ValueError("Cannot apply exact known macOS semaphore fix")
    original_git=subprocess.run(["git","-C",str(source),"show",f"HEAD:{TARGET}"],
                                capture_output=True,text=True,check=True,
                                timeout=30).stdout
    if original_git!=original:
        raise ValueError("Original license/source Git config does not match file")
    path.write_text(original.replace(BEFORE,AFTER,1),"utf-8")
    if git(source,"status","--porcelain","--untracked-files=no") != "M mednafen/config.h":
        raise ValueError("Unexpected files changed by research-only source patch")
    return {
        "status":"UNAPPROVED-SUPAFAUST-MACOS-REPRODUCIBLE-SOURCE-PATCH",
        "source_commit":COMMIT,
        "source_path_modified":TARGET,
        "changed_line_before":BEFORE,
        "changed_line_after":AFTER,
        "license_redistribution_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        result=apply_exact_macos_fix(args.source)
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        p.exit(1,f"MACOS SUPAFAUST PATCH REJECTED: {e}\n")
    print("Applied exact upstream macOS semaphore compile-compatibility fix: "
          +result["source_path_modified"]+"; native rights NOT approved")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
