"""Fail-closed tests for the exact pinned original Dolphin headless patch.

No emulator binaries, ROMs, or source downloads are used. These tests check
that a three-file original-source edit cannot silently become partial or
be applied twice to a different upstream revision.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.patch_v30_dolphin_headless_source import _FILES, patch_source


class OriginalDolphinHeadlessPatchTests(unittest.TestCase):
    def prepare(self, root: Path):
        before = {}
        for relative, replacements in _FILES.items():
            file = root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            # Preserve each exact anchor once and in the same order. This is
            # a synthetic contract, not a claim to compile original Dolphin.
            original = "\n".join(pair[0] for pair in replacements)
            file.write_text(original, encoding="utf-8")
            before[relative] = original
        return before

    def test_all_exact_original_anchors_apply_and_reapplication_fails(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            original = self.prepare(root)
            changed = patch_source(root)
            self.assertEqual(set(changed), set(_FILES))
            for relative, replacements in _FILES.items():
                output = (root / relative).read_text("utf-8")
                self.assertNotEqual(output, original[relative])
                for before, after in replacements:
                    self.assertIn(after, output)
            snapshot = {p: (root / p).read_bytes() for p in _FILES}
            with self.assertRaisesRegex(RuntimeError, "anchor count=0"):
                patch_source(root)
            self.assertEqual(snapshot, {p: (root / p).read_bytes() for p in _FILES})

    def test_modified_upstream_anchor_fails_before_any_file_is_written(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            last = list(_FILES)[-1]
            changed = root / last
            changed.write_text(changed.read_text("utf-8").replace(
                _FILES[last][-1][0], "unrecognized upstream implementation"), "utf-8")
            snapshot = {p: (root / p).read_bytes() for p in _FILES}
            with self.assertRaisesRegex(RuntimeError, "anchor count=0"):
                patch_source(root)
            self.assertEqual(snapshot, {p: (root / p).read_bytes() for p in _FILES})

    def test_ambiguous_duplicate_anchor_rejected_without_partial_edits(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            first = list(_FILES)[0]
            changed = root / first
            changed.write_text(changed.read_text("utf-8") + "\n" +
                               _FILES[first][0][0], "utf-8")
            snapshot = {p: (root / p).read_bytes() for p in _FILES}
            with self.assertRaisesRegex(RuntimeError, "anchor count=2"):
                patch_source(root)
            self.assertEqual(snapshot, {p: (root / p).read_bytes() for p in _FILES})


if __name__ == "__main__":
    unittest.main()
