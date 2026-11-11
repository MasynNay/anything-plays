"""A fresh 3.1 QA assembler may use only the exact checkout's source SHA."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import assemble_v31_full_linux as linux
from tools import assemble_v31_full_windows as windows
from tools import assemble_v31_full_macos as mac
from tools.v31_current_source_qa import reviewed_source_revision


ORIGINAL = "26de1e1ad1b701d0735e085158347f8c213ce437"
FRESH = "a" * 40
SAFETY = {
    "AP_V31_NEXT_QA": "1",
    "AP_V31_QA_CHECKOUT_SHA": FRESH,
    "AP_V31_RC": "1",
    "AP_V31_FULL_TEST_CORES": "1",
    "AP_V31_PREVIEW": "0",
    "AP_RELEASE_BUILD": "0",
    "AP_V30_APPROVED_RELEASE": "0",
    "AP_V30_STABLE_CANDIDATE": "0",
}


class CurrentSourceQaTests(unittest.TestCase):
    def test_legacy_rc_source_pin_is_never_implicitly_overridden(self):
        self.assertEqual(reviewed_source_revision(ORIGINAL, rc1=True), ORIGINAL)
        self.assertEqual(reviewed_source_revision(ORIGINAL, rc1=False), ORIGINAL)
        self.assertEqual(linux.RC_SOURCE_REVISION, ORIGINAL)
        self.assertEqual(windows.RC_SOURCE_REVISION, ORIGINAL)
        self.assertEqual(mac.RC_SOURCE_REVISION, ORIGINAL)

    def test_accepts_only_exact_same_checkout_source_sha_for_nonrelease(self):
        self.assertEqual(
            reviewed_source_revision(
                ORIGINAL, rc1=True, override=FRESH,
                environ=SAFETY, checkout=FRESH,
            ),
            FRESH,
        )
        with self.assertRaises(ValueError):
            reviewed_source_revision(ORIGINAL, rc1=True, override=FRESH,
                                     environ=SAFETY, checkout="b" * 40)
        for bad in ("unknown", "a" * 39, "a" * 41, "A" * 40):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                reviewed_source_revision(ORIGINAL, rc1=True, override=bad,
                                         environ=SAFETY, checkout=FRESH)

    def test_never_allows_a_qa_override_to_approve_distribution(self):
        for key, bad in (
            ("AP_V31_NEXT_QA", "0"),
            ("AP_V31_QA_CHECKOUT_SHA", "b" * 40),
            ("AP_V31_RC", "0"),
            ("AP_V31_FULL_TEST_CORES", "0"),
            ("AP_V31_PREVIEW", "1"),
            ("AP_RELEASE_BUILD", "1"),
            ("AP_V30_APPROVED_RELEASE", "1"),
            ("AP_V30_STABLE_CANDIDATE", "1"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                reviewed_source_revision(
                    ORIGINAL, rc1=True, override=FRESH,
                    environ=dict(SAFETY, **{key: bad}), checkout=FRESH,
                )
        with self.assertRaises(ValueError):
            reviewed_source_revision(ORIGINAL, rc1=False, override=FRESH,
                                     environ=SAFETY, checkout=FRESH)

    def test_all_three_packagers_reject_tampered_fresh_receipts(self):
        cases = (
            ("linux", linux, "linux-x64", linux.STABLE,
             linux.RC_PREVIEW, linux.validate_inputs, linux.sha),
            ("windows", windows, "windows-x64", windows.STABLE,
             windows.RC_PREVIEW, windows.check_inputs, windows.hash_file),
        )
        for label, module, target, oldname, newname, check, digest in cases:
            with self.subTest(platform=label), TemporaryDirectory() as tmp:
                root = Path(tmp)
                old, new = root / oldname, root / newname
                old.write_bytes(b"trusted 3.0 native")
                new.write_bytes(b"current source QA installer")
                sums, receipt = root / "SHA256SUMS.txt", root / "RECEIPT.json"
                sums.write_text(digest(old) + "  " + oldname + "\n", "utf-8")
                report = {"target": target, "installer": newname,
                          "source_revision": FRESH, "sha256": digest(new)}
                receipt.write_text(json.dumps(report), "utf-8")
                with patch.dict(os.environ, SAFETY):
                    with patch("tools.v31_current_source_qa.subprocess.check_output",
                               return_value=FRESH + "\n"):
                        self.assertEqual(
                            check(old, new, sums, receipt, rc1=True,
                                  expected_source_revision=FRESH),
                            digest(old),
                        )
                        report["source_revision"] = ORIGINAL
                        receipt.write_text(json.dumps(report), "utf-8")
                        with self.assertRaises(ValueError):
                            check(old, new, sums, receipt, rc1=True,
                                  expected_source_revision=FRESH)

    def test_mac_receipt_checks_fresh_sha_and_both_architectures(self):
        for arch in ("arm64", "x64"):
            with self.subTest(arch=arch), TemporaryDirectory() as tmp:
                root = Path(tmp)
                old = root / ("AnythingPlays-3.0.0-macos-" + arch + ".dmg")
                new = root / ("AnythingPlays-3.1.0-rc1-macos-" + arch + ".dmg")
                old.write_bytes(b"trusted 3.0 native")
                new.write_bytes(b"fresh source 3.1 app")
                sums, receipt = root / "SHA256SUMS.txt", root / "RECEIPT.json"
                sums.write_text(mac.digest(old) + "  " + old.name + "\n", "utf-8")
                info = {"target": "macos-" + arch, "installer": new.name,
                        "source_revision": FRESH, "sha256": mac.digest(new)}
                receipt.write_text(json.dumps(info), "utf-8")
                with patch.dict(os.environ, SAFETY):
                    with patch("tools.v31_current_source_qa.subprocess.check_output",
                               return_value=FRESH + "\n"):
                        self.assertEqual(
                            mac.verify_inputs(arch, old, new, sums, receipt,
                                              rc1=True,
                                              expected_source_revision=FRESH),
                            mac.digest(old),
                        )
                        new.write_bytes(b"modified after receipt")
                        with self.assertRaises(ValueError):
                            mac.verify_inputs(arch, old, new, sums, receipt,
                                              rc1=True,
                                              expected_source_revision=FRESH)

    def test_qa_workflow_does_not_write_releases_or_claim_stable(self):
        source = (Path(__file__).resolve().parents[1] /
                  ".github/workflows/v31-current-source-full-qa.yml").read_text("utf-8")
        for text in (
            "actions/download-artifact@v4",
            "actions/upload-artifact@v4",
            "AP_V31_NEXT_QA: '1'",
            "AP_V31_FULL_TEST_CORES: '1'",
            "AP_RELEASE_BUILD: '0'",
            "--expected-source-revision",
            "retention-days: 30",
        ):
            self.assertIn(text, source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("gh release create", source)
        self.assertNotIn("softprops/action-gh-release", source)
        self.assertNotIn("release upload", source)


if __name__ == "__main__":
    unittest.main()
