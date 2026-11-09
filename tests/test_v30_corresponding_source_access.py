"""Original-source access packaging must never add binaries or fake approvals."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import tarfile
import unittest

from anything_plays.v30_approved_core_map import ELEVEN_EXPECTED
from tools.archive_v30_corresponding_sources import archive_all, archive_checkout


class OriginalSourceArchiveTests(unittest.TestCase):
    def make_checkouts(self, root):
        folder = root / "checkouts"
        for name in ELEVEN_EXPECTED:
            checkout = folder / name
            checkout.mkdir(parents=True)
            (checkout / "COPYING").write_text("Original license text " * 100, "utf-8")
            (checkout / "README.md").write_text("Verified source tree " * 100, "utf-8")
            (checkout / "a.c").write_text("int main(void) {return 0;}\n" * 100, "utf-8")
            (checkout / "b.h").write_text("#define X 1\n" * 100, "utf-8")
            (checkout / "Makefile").write_text("all:\n\t@echo built\n" * 100, "utf-8")
            (checkout / ".git").mkdir()
            (checkout / ".git" / "config").write_text("SECRET TOKEN MUST NOT BE IN ARCHIVE")
        return folder

    def test_complete_11_pinned_source_archive_no_git_secrets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = self.make_checkouts(root)
            packet = archive_all(checkout, root / "out", verify_git=False)
            self.assertEqual(packet["core_count"], 11)
            self.assertFalse(packet["newly_compiled_libretro_core_outputs_included"])
            self.assertFalse(packet["public_binary_distribution_approved"])
            self.assertEqual(set(packet["sources"]), set(ELEVEN_EXPECTED))
            for row in packet["sources"].values():
                self.assertEqual(len(row["sha256"]), 64)
                with tarfile.open(root / "out" / row["archive_file"], "r:gz") as tar:
                    names = tar.getnames()
                    self.assertEqual(len(names), 5)
                    self.assertFalse(any("/.git/" in name for name in names))
                    self.assertFalse(any(name.endswith(".dll") for name in names))

    def test_same_source_gives_same_sha_even_after_stat_changes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = self.make_checkouts(root)
            name = "dolphin"
            sha = ELEVEN_EXPECTED[name]
            first = archive_checkout(checkout / name, root / "one.tar.gz", name, sha)
            os.utime(checkout / name / "a.c", (1234567, 1234567))
            second = archive_checkout(checkout / name, root / "two.tar.gz", name, sha)
            self.assertEqual(first["sha256"], second["sha256"])

    def test_cannot_overwrite_existing_source_packet(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = self.make_checkouts(root)
            (root / "out").mkdir()
            with self.assertRaisesRegex(ValueError, "new"):
                archive_all(checkout, root / "out", verify_git=False)

    def test_symlink_escape_is_rejected_and_incomplete_archive_removed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = self.make_checkouts(root)
            (checkout / "dolphin" / "bad").symlink_to(root / "outside")
            with self.assertRaisesRegex(ValueError, "External source symlink"):
                archive_checkout(checkout / "dolphin", root / "bad.tar.gz",
                                 "dolphin", ELEVEN_EXPECTED["dolphin"])
            self.assertFalse((root / "bad.tar.gz").exists())


if __name__ == "__main__":
    unittest.main()
