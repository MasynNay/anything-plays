"""Map actual ELF direct-library dependencies inside a frozen Linux app.

The output is metadata only. It does not determine full legal obligations or
authorize deleting dependencies; it identifies consumers before repackaging.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

NEEDED = re.compile(r"\(NEEDED\).*Shared library: \[([^]]+)\]")
TARGETS = ("libreadline", "libdb-", "libjack", "libasound", "libportaudio")


def audit(bundle):
    root = Path(bundle).resolve(strict=True)
    report = {"target": "linux-x86_64", "scope": "ELF dynamic NEEDED metadata",
              "redistribution_approved": False, "native_files_scanned": 0,
              "library_references": [], "direct_consumers": {}}
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.is_symlink():
            continue
        with f.open("rb") as fd:
            if fd.read(4) != b"\x7fELF":
                continue
        result = subprocess.run(["readelf", "-d", str(f)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError(f"readelf failed for {f.relative_to(root)}: {result.stderr}")
        report["native_files_scanned"] += 1
        deps = NEEDED.findall(result.stdout)
        if deps:
            report["library_references"].append({
                "path": f.relative_to(root).as_posix(), "needed": deps
            })
        for lib in TARGETS:
            matches = [x for x in deps if x.startswith(lib)]
            if matches:
                report["direct_consumers"].setdefault(lib, []).append({
                    "path": f.relative_to(root).as_posix(), "needed": matches
                })
    if report["native_files_scanned"] < 100:
        raise ValueError("Native binary audit incomplete")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    p.add_argument("output", type=Path)
    args=p.parse_args()
    x=audit(args.bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(x, indent=2)+"\n", encoding="utf-8")
    print("Audited",x["native_files_scanned"],"frozen ELF objects")
    for name, consumers in x["direct_consumers"].items():
        print(name, len(consumers), "consumers")
        for row in consumers:
            print("  ",row["path"],"->",", ".join(row["needed"]))


if __name__=="__main__":
    main()
