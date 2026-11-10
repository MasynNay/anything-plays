"""3.1 RC1 draft preparation rejects tampered installers and source gaps."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools import stage_v31_rc_draft as draft


def fixture(root):
    root = Path(root)
    inputs = root / "installers"
    source = root / "source"
    inputs.mkdir()
    source.mkdir()
    for target, (filename, receipt_name, status) in draft.TARGETS.items():
        folder = inputs / target
        folder.mkdir()
        binary = folder / filename
        binary.write_bytes(("VERIFIED-" + target).encode())
        (folder / receipt_name).write_text(json.dumps({
            "status": status, "target": target, "installer": filename,
            "source_preview_revision": draft.APP_SOURCE,
            "native_core_count": 11, "console_profiles": 18,
            "sdl_runtime_audit": "SDL_RUNTIME_AUDIT.json",
            "public_release_approved": False,
            "final_release_approved": False,
            "sha256": draft.digest(binary),
        }))
        (folder / "SDL_RUNTIME_AUDIT.json").write_text(json.dumps({
            "target": target, "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
            "pygame_version": "2.5.8", "redistribution_approved": False,
        }))
    (source / "SIX_SOURCE_COMPANION_READINESS.json").write_text(json.dumps({
        "status": "UNRELEASED_3_1_ORIGINAL_SOURCE_CANDIDATES_ONLY",
        "full_rc_qa_run": draft.QA_RUN, "source_app_commit": draft.APP_SOURCE,
        "original_source_archive_count": 6,
        "exact_binary_to_source_correspondence_verified": False,
        "complete_transitive_source_verified": False,
        "lgpl_relinking_reviewed": False,
        "redistribution_approved": False,
        "public_release_approved": False,
    }))
    (source / "SDL_SOURCE_REVIEW.json").write_text(json.dumps({
        "full_rc_qa_run": draft.QA_RUN, "source_app_commit": draft.APP_SOURCE,
        "corresponding_source_complete": False,
        "redistribution_approved": False,
    }))
    checked = []
    for name in draft.SDL_NAMES:
        base = source / "SDL-original-tagged-source-candidates"
        base.mkdir(exist_ok=True)
        for suffix in (".tar.gz", "-ORIGINAL-LICENSE.txt"):
            item = base / (name + suffix)
            item.write_bytes(("immutable-original-" + name + suffix).encode())
            checked.append(item)
    for suffix in ("SDL_CANDIDATE_SOURCE_MANIFEST.json", "Pygame-CE-LGPL-2.1.txt"):
        item = source / "SDL-original-tagged-source-candidates" / suffix
        item.write_bytes(("tagged-" + suffix).encode())
        checked.append(item)
    src_archive = source / draft.SOURCE_FILES[0]
    src_archive.write_bytes(b"pygame-original-tag-source")
    checked.append(src_archive)
    (source / "README_SOURCE_CANDIDATES.txt").write_text("UNAPPROVED ORIGINAL SOURCE CANDIDATES")
    (source / "SIX_ORIGINAL_SOURCE_CANDIDATE_SHA256SUMS.txt").write_text(
        "".join(draft.digest(file) + "  " + file.relative_to(source).as_posix() + "\n"
                for file in checked))
    return inputs, source


class DraftPreparationTests(unittest.TestCase):
    def setUp(self):
        ctx = TemporaryDirectory()
        self.addCleanup(ctx.cleanup)
        self.root = Path(ctx.name)
        self.installers, self.source = fixture(self.root)
        self.out = self.root / "draft"

    def test_four_original_installers_and_source_zip_with_sha_receipts(self):
        record = draft.stage(self.installers, self.source, self.out, minimum=1)
        self.assertEqual(record["status"], "UNPUBLISHED_3_1_RC1_RELEASE_DRAFT_QA_ONLY")
        self.assertEqual(len(record["installers"]), 4)
        self.assertFalse(record["redistribution_approved"])
        self.assertFalse(record["public_release_approved"])
        self.assertFalse(record["complete_native_corresponding_source_verified"])
        self.assertTrue((self.out / draft.SOURCE_ASSET).is_file())
        with zipfile.ZipFile(self.out / draft.SOURCE_ASSET) as archive:
            names = archive.namelist()
        self.assertEqual(len(names), len(draft.SOURCE_FILES) + 2 + 10)
        self.assertIn("SDL-original-tagged-source-candidates/Pygame-CE-LGPL-2.1.txt", names)
        sums = (self.out / "SHA256SUMS.txt").read_text().splitlines()
        self.assertEqual(len(sums), 6)
        for line in sums:
            sha, name = line.split("  ")
            self.assertEqual(sha, draft.digest(self.out / name))

    def test_original_linux_receipt_has_no_target_but_audit_pins_target(self):
        record_file = self.installers / "linux-x64" / draft.TARGETS["linux-x64"][1]
        receipt = json.loads(record_file.read_text())
        receipt.pop("target")
        record_file.write_text(json.dumps(receipt))
        # The actual 3.1 Linux assembler omits target in its QA receipt;
        # the unique filename/status and independent SDL audit carry it.
        valid = draft.verify_installers(self.installers, minimum=1)
        self.assertIn("linux-x64", valid)
        receipt["target"] = "windows-x64"
        record_file.write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):
            draft.verify_installers(self.installers, minimum=1)

    def test_fake_approval_or_wrong_platform_sha_is_rejected(self):
        target = "windows-x64"
        file = self.installers / target / draft.TARGETS[target][1]
        original = json.loads(file.read_text())
        for patch in (
            {"public_release_approved": True},
            {"native_core_count": 10},
            {"source_preview_revision": "0" * 40},
            {"sha256": "f" * 64},
        ):
            with self.subTest(patch=patch):
                file.write_text(json.dumps({**original, **patch}))
                with self.assertRaises(ValueError):
                    draft.stage(self.installers, self.source, self.out, minimum=1)
                self.assertFalse(self.out.exists())
        file.write_text(json.dumps(original))

    def test_missing_source_or_overstated_rights_cannot_create_draft(self):
        info = self.source / "SIX_SOURCE_COMPANION_READINESS.json"
        original = json.loads(info.read_text())
        info.write_text(json.dumps({**original, "redistribution_approved": True}))
        with self.assertRaises(ValueError):
            draft.stage(self.installers, self.source, self.out, minimum=1)
        info.write_text(json.dumps(original))
        missing = self.source / "SDL-original-tagged-source-candidates/sdl2-2.32.8.tar.gz"
        missing.unlink()
        with self.assertRaises(ValueError):
            draft.stage(self.installers, self.source, self.out, minimum=1)

    def test_source_path_traversal_and_corrupt_upstream_digests_refused(self):
        listing = self.source / "SIX_ORIGINAL_SOURCE_CANDIDATE_SHA256SUMS.txt"
        valid = listing.read_text()
        for malformed in (
            valid + "a" * 64 + "  ../outside\n",
            valid + "a" * 64 + "  /tmp/outside\n",
            valid + "a" * 64 + "  SDL-original-tagged-source-candidates/sdl2-2.32.8.tar.gz\n",
        ):
            with self.subTest(malformed=malformed[-35:]):
                listing.write_text(malformed)
                with self.assertRaises(ValueError):
                    draft.stage(self.installers, self.source, self.out, minimum=1)
        listing.write_text(valid.replace(valid[:64], "0" * 64, 1))
        with self.assertRaises(ValueError):
            draft.stage(self.installers, self.source, self.out, minimum=1)

    def test_no_overwriting_original_evidence_or_symlink_inputs(self):
        with self.assertRaises(ValueError):
            draft.stage(self.installers, self.source, self.source / "test", minimum=1)
        with self.assertRaises(ValueError):
            draft.stage(self.installers, self.source, self.installers, minimum=1)
        binary = self.installers / "windows-x64" / draft.TARGETS["windows-x64"][0]
        binary.unlink()
        binary.symlink_to(self.source / draft.SOURCE_FILES[0])
        with self.assertRaises(ValueError):
            draft.stage(self.installers, self.source, self.out, minimum=1)

    def test_workflow_preserves_full_qa_without_unapproved_release_write(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/v31-stage-rc1-release-draft.yml"
        text = path.read_text("utf-8")
        for required in ("42905694504", "42909893531",
                         "RC1_DRAFT_QA_RECEIPT.json", "GH_TOKEN",
                         "SHA256SUMS.txt", "retention-days: 90",
                         "actions/upload-artifact@v4", "contents: read"):
            self.assertIn(required, text)
        for forbidden in ("--latest", "gh release create",
                          "gh release delete", "--clobber", "contents: write"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
