"""Regression: Tia original-source mapping cannot silently accept Stella."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from anything_plays import v30_approved_core_map as mapping


class TiaMapTests(unittest.TestCase):
    def _manifest(self):
        rows = {
            name: {
                "native_filename": f"{name}_libretro.so",
                "source_commit": commit,
                "source_repository": mapping.ELEVEN_TIA_REPOSITORIES[name],
                "native_sha256": "a" * 64,
                "license_notice_sha256": "b" * 64,
            }
            for name, commit in mapping.ELEVEN_TIA_EXPECTED.items()
        }
        return {
            "schema_version": 1,
            "status": mapping.STATUS,
            "core_set_id": "gpl-source-built-eleven-tia",
            "all_console_profiles": 18,
            "native_core_count": 11,
            "legacy_noncommercial_native_binaries_excluded": True,
            "eleven_source_built_families_reviewed": True,
            "zero_unchanged_native_families_reviewed": True,
            "gpl2plus_atari_source_replacement_reviewed": True,
            "original_gpl2_only_stella_excluded": True,
            "runtime_dependencies": {},
            "cores": rows,
        }

    def test_tia_manifest_accepted_and_atari_routes_to_tia(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / mapping.MARKER).write_text(json.dumps(self._manifest()))
            result = mapping.validate_installed_map(root, ".so", verify_native=False)
            self.assertEqual(set(result["cores"]), set(mapping.ELEVEN_TIA_EXPECTED))
            with patch.object(mapping, "validate_installed_map", return_value=result):
                with patch.object(mapping, "enable_windows_offline_runtime"):
                    with patch.object(mapping, "Path", wraps=Path):
                        # Lookup verifies native bytes in production; this stub isolates routing.
                        found, native = mapping.find_approved_core([root], "atari2600", ".so")
            self.assertTrue(found)
            self.assertEqual(Path(native).name, "tia_libretro.so")

    def test_stella_payload_is_rejected_even_with_valid_tia_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / mapping.MARKER).write_text(json.dumps(self._manifest()))
            (root / "stella2014_libretro.so").write_bytes(b"legacy")
            with self.assertRaises(ValueError):
                mapping.validate_installed_map(root, ".so", verify_native=False)

    def test_missing_tia_review_flag_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self._manifest()
            manifest["original_gpl2_only_stella_excluded"] = False
            (root / mapping.MARKER).write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                mapping.validate_installed_map(root, ".so", verify_native=False)


if __name__ == "__main__":
    unittest.main()
