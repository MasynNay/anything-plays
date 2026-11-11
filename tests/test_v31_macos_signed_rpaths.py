"""Regression checks for original signed macOS 3.1 SDL runpath triage."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import probe_v31_macos_signed_rpaths as probe


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command_stdout(*rpaths):
    lines = ["file:", "Load command 0", "          cmd LC_ID_DYLIB",
             "      cmdsize 32", "Load command 1"]
    for index, item in enumerate(rpaths):
        lines += [f"Load command {index + 2}",
                  "          cmd LC_RPATH", "      cmdsize 48",
                  f"         path {item} (offset 12)"]
    return "\n".join(lines) + "\n"


def fake_report(root, target):
    count = probe.TARGET_COUNTS[target]
    library = root / "Contents/Frameworks/pygame/base.so"
    library.parent.mkdir(parents=True, exist_ok=True)
    library.write_bytes(b"original signed binary fixture")
    target_sdl = library.parent / "__dot__dylibs/libSDL2-2.0.0.dylib"
    target_sdl.parent.mkdir(parents=True, exist_ok=True)
    target_sdl.write_bytes(b"signed pygame SDL2 fixture")
    files = [{
        "path": library.relative_to(root).as_posix(),
        "sha256": probe.sha256(library),
        "size_bytes": library.stat().st_size,
        "otool_dependencies": [{"name": probe.SDL_REFERENCE}],
    }]
    for index in range(count - 1):
        files.append({
            "path": f"Contents/Frameworks/pygame/other{index}.so",
            "sha256": "e" * 64, "size_bytes": 1,
            "otool_dependencies": [{"name": "/usr/lib/libSystem.B.dylib"}],
        })
    report = {
        "schema_version": 1,
        "target": target,
        "status": probe.REPORT_STATUS,
        "source_app_commit": probe.SOURCE_SHA,
        "native_file_count": count,
        "redistribution_approved": False,
        "lgpl_relinking_reviewed": False,
        "native_files": files,
    }
    signed = {
        "pygame": {
            "path": str(target_sdl),
            "audited_sha256": probe.sha256(target_sdl),
            "expected_runtime_version": "2.32.10",
        }
    }
    if target == "macos-arm64":
        signed["cv2"] = {
            "path": str(root / "Contents/Frameworks/cv2/libSDL2-2.0.0.dylib"),
            "audited_sha256": "b" * 64,
            "expected_runtime_version": "2.32.8",
        }
    return report, signed, library, target_sdl


def runner_with_output(output):
    def runner(args, **kwargs):
        if args[:2] != ["otool", "-l"]:
            raise AssertionError("Unexpected native command")
        return subprocess.CompletedProcess(args, 0, output, "")
    return runner


class SignedMacRpathTests(unittest.TestCase):
    def test_parse_only_rpath_commands(self):
        output = command_stdout("@loader_path/../__dot__dylibs",
                                "@executable_path/../Frameworks",
                                "@loader_path/../__dot__dylibs")
        self.assertEqual(probe.parse_local_rpaths(output), [
            "@loader_path/../__dot__dylibs",
            "@executable_path/../Frameworks",
        ])
        self.assertEqual(probe.parse_local_rpaths("cmd LC_LOAD_DYLIB\n"), [])
        with self.assertRaises(ValueError):
            probe.parse_local_rpaths("cmd LC_RPATH\ncmdsize 24\n")

    def test_original_signed_both_arches_have_one_authenticated_direct_match(self):
        for target in probe.TARGET_COUNTS:
            with self.subTest(target=target), TemporaryDirectory() as folder:
                root = Path(folder)
                report, signed, _, _ = fake_report(root, target)
                with patch.object(probe, "select_libs", return_value=signed):
                    result = probe.inspect(
                        root, report, target,
                        runner=runner_with_output(
                            command_stdout("@loader_path/__dot__dylibs")
                        ),
                    )
                self.assertEqual(result["sdl2_referencing_images"], 1)
                self.assertEqual(result["native_images_with_direct_pinned_hash_candidate"], 1)
                self.assertEqual(result["native_consumers_without_direct_pinned_hash_candidate"], [])
                self.assertTrue(result["all_consumer_images_have_direct_hash_candidate"])
                entry = result["linking"][0]["direct_candidates"][0]
                self.assertEqual(entry["status"],
                                 "signed_sdl_binary_hash_match")
                self.assertEqual(entry["matching_pinned_sdl_slots"],
                                 ["pygame"])
                self.assertFalse(result["live_loaded_sdl_image_proven"])
                self.assertFalse(result["full_dyld_loader_chain_resolved"])
                self.assertFalse(result["stable_3_1_release_approved"])

    def test_actual_consumer_without_direct_signed_hash_remains_blocked(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report, signed, library, _ = fake_report(root, "macos-x64")
            with patch.object(probe, "select_libs", return_value=signed):
                result = probe.inspect(
                    root, report, "macos-x64",
                    runner=runner_with_output(command_stdout()),
                )
            self.assertFalse(result["all_consumer_images_have_direct_hash_candidate"])
            self.assertEqual(
                result["native_consumers_without_direct_pinned_hash_candidate"],
                [library.relative_to(root).as_posix()],
            )
            self.assertEqual(result["native_images_with_direct_pinned_hash_candidate"], 0)
            self.assertEqual(result["sdl2_self_library_or_alias_entries"], [])

    def test_absent_unexpanded_and_external_rpath_never_claim_matches(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report, signed, _, _ = fake_report(root, "macos-arm64")
            output = command_stdout(
                "@loader_path/does_not_exist", "@rpath/nested",
                "/opt/Homebrew/lib", "@loader_path/__dot__dylibs"
            )
            with patch.object(probe, "select_libs", return_value=signed):
                result = probe.inspect(root, report, "macos-arm64",
                                       runner=runner_with_output(output))
            statuses = [x["status"] for x in
                        result["linking"][0]["direct_candidates"]]
            self.assertEqual(statuses, [
                "not_present_at_direct_runpath",
                "unexpanded_or_inherited_runpath",
                "absolute_runpath_not_assumed_bundled",
                "signed_sdl_binary_hash_match",
            ])

    def test_unreviewed_bundled_binary_not_mistaken_for_pinned_sdl(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report, signed, _, target_sdl = fake_report(root, "macos-x64")
            target_sdl.write_bytes(b"unreviewed changed library")
            with patch.object(probe, "select_libs", return_value=signed):
                result = probe.inspect(
                    root, report, "macos-x64",
                    runner=runner_with_output(
                        command_stdout("@loader_path/__dot__dylibs")
                    ),
                )
            self.assertEqual(
                result["linking"][0]["direct_candidates"][0]["status"],
                "other_bundled_binary_requires_review",
            )

    def test_rejects_unpinned_source_tampered_library_and_bad_counts(self):
        for field, changed in (
            ("source_app_commit", "0" * 40),
            ("status", "APPROVED"),
            ("redistribution_approved", True),
            ("lgpl_relinking_reviewed", True),
            ("native_file_count", 1),
        ):
            with self.subTest(field=field), TemporaryDirectory() as folder:
                root = Path(folder)
                report, signed, _, _ = fake_report(root, "macos-x64")
                report[field] = changed
                with patch.object(probe, "select_libs", return_value=signed):
                    with self.assertRaises(ValueError):
                        probe.inspect(root, report, "macos-x64",
                                      runner=runner_with_output(""))
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report, signed, library, _ = fake_report(root, "macos-x64")
            library.write_bytes(b"altered signed binary")
            with patch.object(probe, "select_libs", return_value=signed):
                with self.assertRaises(ValueError):
                    probe.inspect(root, report, "macos-x64",
                                  runner=runner_with_output(""))

    def test_rejects_duplicate_paths_missing_otool_and_forged_hashes(self):
        for mode in ("duplicate", "missing-deps", "bad-sha", "bad-path"):
            with self.subTest(mode=mode), TemporaryDirectory() as folder:
                root = Path(folder)
                report, signed, _, _ = fake_report(root, "macos-x64")
                if mode == "duplicate":
                    report["native_files"][1]["path"] = report["native_files"][0]["path"]
                elif mode == "missing-deps":
                    report["native_files"][0]["otool_dependencies"] = []
                elif mode == "bad-sha":
                    report["native_files"][0]["sha256"] = "bogus"
                else:
                    report["native_files"][0]["path"] = "../../secret.so"
                with patch.object(probe, "select_libs", return_value=signed):
                    with self.assertRaises(ValueError):
                        probe.inspect(root, report, "macos-x64",
                                      runner=runner_with_output(""))

    def test_rejects_failed_otool_execution(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report, signed, _, _ = fake_report(root, "macos-x64")
            def runner(args, **kwargs):
                return subprocess.CompletedProcess(args, 1, "", "failure")
            with patch.object(probe, "select_libs", return_value=signed):
                with self.assertRaises(ValueError):
                    probe.inspect(root, report, "macos-x64", runner=runner)

    def test_signed_relative_native_symlink_with_same_original_hash_is_allowed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report, signed, library, _ = fake_report(root, "macos-x64")
            real = library.with_name("base_real.so")
            real.write_bytes(library.read_bytes())
            library.unlink()
            try:
                library.symlink_to(real.name)
            except (NotImplementedError, OSError):
                self.skipTest("Symlink support unavailable")
            with patch.object(probe, "select_libs", return_value=signed):
                result = probe.inspect(
                    root, report, "macos-x64",
                    runner=runner_with_output(
                        command_stdout("@loader_path/__dot__dylibs")
                    ),
                )
            self.assertEqual(result["sdl2_referencing_images"], 1)
            self.assertFalse(result["live_loaded_sdl_image_proven"])

    def test_original_native_link_escaping_app_is_rejected(self):
        with TemporaryDirectory() as folder, TemporaryDirectory() as external:
            root = Path(folder)
            report, signed, library, _ = fake_report(root, "macos-x64")
            outside = Path(external) / "base_real.so"
            outside.write_bytes(library.read_bytes())
            library.unlink()
            try:
                library.symlink_to(outside)
            except (NotImplementedError, OSError):
                self.skipTest("Symlink support unavailable")
            with patch.object(probe, "select_libs", return_value=signed):
                with self.assertRaises(ValueError):
                    probe.inspect(root, report, "macos-x64",
                                  runner=runner_with_output(
                                      command_stdout("@loader_path/__dot__dylibs")
                                  ))

    def test_symlink_escaping_original_app_cannot_be_read(self):
        with TemporaryDirectory() as folder, TemporaryDirectory() as external:
            root = Path(folder)
            report, signed, library, target_sdl = fake_report(root, "macos-x64")
            external_file = Path(external) / "fake_sdl.dylib"
            external_file.write_bytes(b"malicious external library")
            target_sdl.unlink()
            try:
                target_sdl.symlink_to(external_file)
            except (NotImplementedError, OSError):
                self.skipTest("Symlink support unavailable")
            with patch.object(probe, "select_libs", return_value=signed):
                with self.assertRaises(ValueError):
                    probe.inspect(root, report, "macos-x64",
                                  runner=runner_with_output(
                                      command_stdout("@loader_path/__dot__dylibs")
                                  ))


if __name__ == "__main__":
    unittest.main()
