"""Fail closed on source assets before creating a public source companion."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from anything_plays.v30_approved_core_map import ELEVEN_EXPECTED, ELEVEN_REPOSITORIES
from tools.prepare_v30_source_companion import (
    CHECKSUMS, MANIFEST, STATUS, prepare_source_companion, validate_captured_sources,
)


def prepare_fixture(root):
    src = root / "source"
    src.mkdir()
    sources, lines = {}, []
    for name, revision in sorted(ELEVEN_EXPECTED.items()):
        filename = f"source-{name}-{revision}.tar.gz"
        data = (f"TEST ONLY source archive for {name} {revision}\n" * 15).encode()
        (src / filename).write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        lines.append(f"{sha}  {filename}")
        sources[name] = {
            "source_commit": revision,
            "source_repository": ELEVEN_REPOSITORIES[name],
            "archive_file": filename,
            "sha256": sha,
            "size_bytes": len(data),
            "source_files": 5,
            "nested_gitlink_source_count": 37 if name == "dolphin" else 0,
        }
    (src / CHECKSUMS).write_text("\n".join(lines) + "\n", "ascii")
    report = {
        "schema_version": 1, "status": STATUS, "core_count": 11,
        "all_source_revisions_pinned": True,
        "newly_compiled_libretro_core_outputs_included": False,
        "source_to_bundled_binary_review_complete": False,
        "transitive_build_dependencies_review_complete": False,
        "combined_gpl_distribution_reviewed": False,
        "public_binary_distribution_approved": False,
        "sources": sources,
    }
    (src / MANIFEST).write_text(json.dumps(report), "utf-8")
    return src


class SourceCompanionTests(unittest.TestCase):
    def test_source_companion_has_all_eleven_no_fake_approvals(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            src = prepare_fixture(root)
            result = prepare_source_companion(src, root / "published", "3.0.0")
            self.assertEqual(result["upstream_core_count"], 11)
            self.assertFalse(result["binary_distribution_approval_auto_granted"])
            archive = root / "published" / result["filename"]
            with ZipFile(archive) as packed:
                self.assertEqual(len(packed.namelist()), 14)
                self.assertIn("SOURCE_ACCESS_README.txt", packed.namelist())
            self.assertEqual(len(result["sha256"]), 64)
            self.assertEqual(len((root/"published"/CHECKSUMS).read_text().splitlines()), 1)

    def test_false_rights_flag_is_mandatory(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            src = prepare_fixture(root)
            path = src / MANIFEST
            data = json.loads(path.read_text())
            data["public_binary_distribution_approved"] = True
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "fabricated approval"):
                validate_captured_sources(src)

    def test_source_file_tamper_fails_before_output_created(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            src = prepare_fixture(root)
            filename = next(p.name for p in src.iterdir() if p.name.endswith(".tar.gz"))
            (src / filename).write_bytes(b"malicious contents")
            with self.assertRaisesRegex(ValueError, "checksum"):
                prepare_source_companion(src, root / "out", "3.0.0")
            self.assertFalse((root / "out").exists())

    def test_source_archive_cannot_overwrite_existing_package(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            src = prepare_fixture(root)
            with self.assertRaisesRegex(ValueError, "separate"):
                prepare_source_companion(src, src, "3.0.0")

    def test_dolphin_gitlink_identity_cannot_be_forged(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            src = prepare_fixture(root)
            path = src / MANIFEST
            data = json.loads(path.read_text())
            data["sources"]["dolphin"]["nested_gitlink_source_count"] = 34
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "Gitlinks"):
                validate_captured_sources(src)


    def test_publisher_creates_source_draft_before_binary_release(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/v30-publish-approved.yml").read_text("utf-8")
        self.assertIn("source_run_id:", workflow)
        self.assertIn("python -m tools.prepare_v30_source_companion", workflow)
        self.assertIn("SOURCE_RUN_ID", workflow)
        self.assertIn('gh release create "v$VERSION-sources"', workflow)
        self.assertIn('gh release create "v$VERSION" public-release/*', workflow)
        self.assertLess(
            workflow.index('gh release create "v$VERSION-sources"'),
            workflow.index('gh release create "v$VERSION" public-release/*'),
        )
        self.assertLess(
            workflow.index('gh release edit "v$VERSION-sources" --draft=false'),
            workflow.index('gh release edit "v$VERSION" --draft=false'),
        )
        self.assertIn("test \"$(find . -maxdepth 1 -type f | wc -l)\" -eq 5", workflow)
        self.assertNotIn("\n  push:", workflow)

    def test_companion_zip_byte_identical_across_distinct_output_directories(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            src = prepare_fixture(root)
            first = prepare_source_companion(src, root / "first", "3.0.0")
            second = prepare_source_companion(src, root / "second", "3.0.0")
            self.assertEqual(first["sha256"], second["sha256"])


if __name__ == "__main__":
    unittest.main()
