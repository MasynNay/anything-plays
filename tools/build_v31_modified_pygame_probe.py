"""Create an explicit, observable GNU LGPL pygame-ce 2.5.8 source change.

Only modifies an isolated clone of EXACT upstream commit
c8200a9eaa530f884a0a4c3384cefc48006e58be, never the bundled RC
binary. Adds an intentionally new Python-callable native C method to
pygame.base; a successful import & method invocation proves the *changed*
source code (not identical official wheel bytes) is actually running.

This is a test patch, not a production feature or a legal opinion.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess

PYGAME_COMMIT = "c8200a9eaa530f884a0a4c3384cefc48006e58be"
VERSION = "2.5.8"
TAG_LGPL_SHA256 = "a190dc9c8043755d90f8b0a75fa66b9e42d4af4c980bf5ddc633f0124db3cee7"
PROBE_VALUE = "anything-plays-3.1-ce-2.5.8-compiled-modified-native"
NATIVE_FILENAME = Path("src_c/base.c")
PROBE_FUNCTION = """
/* Owner-only LGPL code modification, explicitly NOT in pygame-ce 2.5.8. */
static PyObject *
pg_ap31_relink_probe(PyObject *self, PyObject *unused)
{
    return PyUnicode_FromString("anything-plays-3.1-ce-2.5.8-compiled-modified-native");
}
"""
C_ANCHOR = "/* bind functions to python */\n\nstatic PyMethodDef _base_methods[] = {"
C_REPLACEMENT = (
    PROBE_FUNCTION + "\n" + C_ANCHOR
)
METHOD_ANCHOR = '    {"get_init", (PyCFunction)pg_base_get_init, METH_NOARGS, DOC_GETINIT},'
METHOD_REPLACEMENT = (
    METHOD_ANCHOR + "\n"
    '    {"_ap31_relink_probe", (PyCFunction)pg_ap31_relink_probe, METH_NOARGS,\n'
    '     "Verify this pygame native extension was compiled from modified LGPL source"},'
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def patch_source(root, *, runner=subprocess.run):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Missing independent, unlinked pygame source clone")
    completed = runner(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True, capture_output=True, check=True,
    )
    if completed.stdout.strip() != PYGAME_COMMIT:
        raise ValueError("Wrong upstream pygame-ce source commit")
    license_path = root / "docs/LGPL.txt"
    if (license_path.is_symlink() or not license_path.is_file()
            or sha256(license_path) != TAG_LGPL_SHA256):
        raise ValueError("Exact original upstream LGPL source/license unverified")
    native = root / NATIVE_FILENAME
    if native.is_symlink() or not native.is_file():
        raise ValueError("Refusing to modify linked or missing source")
    before = native.read_text("utf-8")
    if (before.count(C_ANCHOR) != 1 or before.count(METHOD_ANCHOR) != 1
            or "pg_ap31_relink_probe" in before or "_ap31_relink_probe" in before):
        raise ValueError("Unexpected upstream C code; refusing ambiguous patch")
    native.write_text(
        before.replace(C_ANCHOR, C_REPLACEMENT, 1)
              .replace(METHOD_ANCHOR, METHOD_REPLACEMENT, 1),
        "utf-8",
    )
    after = native.read_text("utf-8")
    if (PROBE_VALUE not in after
            or after.count("_ap31_relink_probe") != 3
            or sha256(native) == hashlib.sha256(before.encode()).hexdigest()):
        raise ValueError("Genuine observable C modification not applied")
    return {
        "original_source_revision": PYGAME_COMMIT,
        "original_tag": VERSION,
        "original_lgpl_sha256": TAG_LGPL_SHA256,
        "modified_source_file": NATIVE_FILENAME.as_posix(),
        "original_base_c_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "patched_base_c_sha256": sha256(native),
        "expected_modified_native_method": "_ap31_relink_probe",
        "expected_modified_native_result": PROBE_VALUE,
        "not_official_unmodified_pygame_wheel": True,
        "full_lgpl_compliance_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args()
    r = patch_source(a.root)
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    import json
    a.receipt.write_text(json.dumps(r, indent=2) + "\n", "utf-8")
    print("Modified pygame-ce source:", r["patched_base_c_sha256"],
          "; native method:", r["expected_modified_native_method"])


if __name__ == "__main__":
    main()
