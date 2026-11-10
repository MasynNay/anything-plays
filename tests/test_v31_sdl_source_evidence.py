"""Adversarial tests for four-platform SDL source/relinking evidence.

A byte match to an official wheel is a useful lead, not an authorization to
redistribute native SDL or a proof of all corresponding compiled sources.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from tools import prepare_v31_sdl_source_review as evidence

ROOT = Path(__file__).resolve().parents[1]


def fixture(target, digest="a" * 64):
    record = {
        "status": evidence.EXPECTED_RECEIPT_STATUS[target],
        "source_preview_revision": evidence.RC_APP_COMMIT,
        "native_core_count": 11, "console_profiles": 18,
        "public_release_approved": False,
        "final_release_approved": False,
        "sdl_runtime_audit": "SDL_RUNTIME_AUDIT.json",
        "installer": "AnythingPlays-RC1-UNRELEASED.pkg",
    }
    native = {
        "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
        "target": target, "pygame_version": "2.5.8",
        "pygame_distribution": "pygame-ce",
        "redistribution_approved": False,
        "original_sources_verified": False,
        "lgpl_relinking_reviewed": False,
        "native_candidates": [{"path": "_internal/pygame/base.pyd", "sha256": digest}],
    }
    return record, native


class SDLCorrespondenceEvidenceTests(unittest.TestCase):
    def test_real_release_pins_four_platforms_and_exact_tag_sha(self):
        self.assertEqual(set(evidence.WHEELS), set(evidence.TARGETS))
        self.assertEqual(len(evidence.RC_APP_COMMIT), 40)
        self.assertEqual(evidence.PYGAME_COMMIT,
                         "c8200a9eaa530f884a0a4c3384cefc48006e58be")
        for target, (name, digest) in evidence.WHEELS.items():
            with self.subTest(target=target):
                self.assertIn("pygame_ce-2.5.8-cp313", name)
                self.assertRegex(digest, r"^[a-f0-9]{64}$")
        self.assertEqual(evidence.WHEELS["macos-arm64"],
                         evidence.WHEELS["macos-x64"])

    def test_real_native_digests_match_only_identical_official_bytes(self):
        for target in evidence.TARGETS:
            with self.subTest(target=target):
                receipt, audit = fixture(target)
                matched = evidence.match_installed_runtime(
                    target, receipt, audit, {"a" * 64: ["pygame/base.pyd"]})
                self.assertEqual(matched["wheel_match_count"], 1)
                self.assertEqual(matched["unmatched_native_candidates"], [])
                self.assertFalse(matched["sdl_native_source_correspondence_proven"])
                self.assertFalse(matched["wheel_provenance_in_installed_bundle_proven"])
                unmatched = evidence.match_installed_runtime(
                    target, receipt, audit, {"b" * 64: ["pygame/base.pyd"]})
                self.assertEqual(unmatched["wheel_match_count"], 0)
                self.assertEqual(len(unmatched["unmatched_native_candidates"]), 1)

    def test_unapproved_gate_and_source_revision_must_remain_false_and_pinned(self):
        for field, value in (
            ("public_release_approved", True),
            ("final_release_approved", True),
            ("native_core_count", 10),
            ("console_profiles", 3),
            ("source_preview_revision", "0" * 40),
            ("status", "APPROVED_PUBLIC_RELEASE"),
        ):
            with self.subTest(field=field):
                receipt, audit = fixture("linux-x64")
                receipt[field] = value
                with self.assertRaises(ValueError):
                    evidence.match_installed_runtime("linux-x64", receipt, audit, {})
        for field, value in (
            ("redistribution_approved", True),
            ("original_sources_verified", True),
            ("lgpl_relinking_reviewed", True),
            ("pygame_version", "2.5.7"),
            ("target", "windows-x64"),
            ("native_candidates", []),
        ):
            with self.subTest(field=field):
                receipt, audit = fixture("linux-x64")
                audit[field] = value
                with self.assertRaises(ValueError):
                    evidence.match_installed_runtime("linux-x64", receipt, audit, {})

    def test_path_traversal_and_digest_tampering_fail_closed(self):
        for path, digest in (
            ("../secret", "a" * 64),
            ("/system/libSDL.so", "a" * 64),
            ("pygame/base.pyd", "bad_hash"),
        ):
            with self.subTest(path=path, digest=digest):
                receipt, audit = fixture("linux-x64")
                audit["native_candidates"] = [{"path": path, "sha256": digest}]
                with self.assertRaises(ValueError):
                    evidence.match_installed_runtime("linux-x64", receipt, audit, {})

    def test_wheel_matches_pinned_content_and_rejects_modified_wheel(self):
        native = b"MZ" + b"pygame native SDL dependency"
        with TemporaryDirectory() as d:
            root = Path(d)
            name = evidence.WHEELS["windows-x64"][0]
            wheel = root / name
            with zipfile.ZipFile(wheel, "w") as z:
                z.writestr("pygame/base.pyd", native)
                z.writestr("pygame/package_data.bin", os.urandom(1_100_000))
            valid_hash = evidence.sha256(wheel)
            with patch.dict(evidence.WHEELS, {"windows-x64": (name, valid_hash)}):
                native_hashes = evidence.wheel_hashes(wheel, "windows-x64")
                self.assertEqual(native_hashes[hashlib.sha256(native).hexdigest()],
                                 ["pygame/base.pyd"])
                wheel.write_bytes(wheel.read_bytes() + b"changed")
                with self.assertRaises(ValueError):
                    evidence.wheel_hashes(wheel, "windows-x64")

    def test_actual_upstream_archive_needs_original_license_and_source(self):
        license_bytes = (ROOT / "licenses/Pygame-CE-LGPL-2.1.txt").read_bytes()
        self.assertEqual(hashlib.sha256(license_bytes).hexdigest(),
                         evidence.UPSTREAM_LGPL_HASH)
        with TemporaryDirectory() as d:
            root = Path(d)
            archive = root / evidence.SOURCE_ARCHIVE
            with tarfile.open(archive, "w:gz") as tar:
                for name, body in (
                    ("pygame-ce-2.5.8/docs/LGPL.txt", license_bytes),
                    ("pygame-ce-2.5.8/src_c/base.c", os.urandom(1_100_000)),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(body)
                    tar.addfile(info, io.BytesIO(body))
            result = evidence.validate_source_archive(archive)
            self.assertEqual(result["source_commit"], evidence.PYGAME_COMMIT)
            self.assertRegex(result["sha256"], r"^[a-f0-9]{64}$")
            with tarfile.open(archive, "w:gz") as tar:
                data = b"invalid license" + os.urandom(1_100_000)
                member = tarfile.TarInfo("pygame-ce-2.5.8/docs/LGPL.txt")
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
                entry = tarfile.TarInfo("pygame-ce-2.5.8/src_c/base.c")
                entry.size = 1
                tar.addfile(entry, io.BytesIO(b"x"))
            with self.assertRaises(ValueError):
                evidence.validate_source_archive(archive)

    def test_source_evidence_workflow_never_publishes_or_claims_license_approval(self):
        flow = (ROOT / ".github/workflows/v31-sdl-source-evidence.yml").read_text("utf-8")
        self.assertIn("42865608433", flow)
        self.assertIn("c8200a9eaa530f884a0a4c3384cefc48006e58be", flow)
        self.assertIn("actions/upload-artifact@v4", flow)
        self.assertNotIn("contents: write", flow)
        self.assertNotIn("gh release create", flow)
        self.assertNotIn("gh release edit", flow)
        self.assertNotIn("public_release_approved: '1'", flow)


if __name__ == "__main__":
    unittest.main()
