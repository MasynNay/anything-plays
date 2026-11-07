"""Third-party NGPC smoke tests require pinned MIT game content, never ship it."""
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.ngp_mit_fixtures import FIXTURES, fetch_test_fixture


class NeoGeoPocketCIContracts(unittest.TestCase):
    def test_fixture_registry_is_exactly_two_pinned_mit_roms(self):
        self.assertEqual(set(FIXTURES), {"ngp", "ngpc"})
        for system, spec in FIXTURES.items():
            with self.subTest(system=system):
                self.assertEqual(spec["license"], "MIT")
                self.assertEqual(len(spec["commit"]), 40)
                self.assertEqual(len(spec["blob_sha1"]), 40)
                self.assertGreater(spec["bytes"], 10000)
                self.assertTrue(spec["path"].endswith(spec["ext"]))
                self.assertNotIn("latest", spec["commit"].casefold())

    def test_download_is_rejected_if_source_bytes_fail_git_integrity(self):
        from tempfile import TemporaryDirectory
        from io import BytesIO
        with TemporaryDirectory() as tmp:
            fake = bytes([0x33]) * FIXTURES["ngpc"]["bytes"]
            context = BytesIO(fake)
            with patch("tools.ngp_mit_fixtures.urlopen", return_value=context):
                with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                    fetch_test_fixture("ngpc", Path(tmp) / "test.ngc")
            self.assertFalse((Path(tmp) / "test.ngc").exists())

    def test_wrong_extension_or_console_cannot_fetch_anything(self):
        with self.assertRaises(ValueError):
            fetch_test_fixture("ngpc", Path("bad.ngp"))
        with self.assertRaises(ValueError):
            fetch_test_fixture("gamecube", Path("bad.ngc"))

    def test_native_state_roundtrip_diagnostic_on_fake_core(self):
        """A state report must be based on actual serialize/unserialize calls."""
        import ctypes as C
        from types import SimpleNamespace
        from tools.probe_ngp_mit_homebrew import _native_save_state_roundtrip

        original = bytes(range(32))
        state = {"bytes": original, "writes": 0, "reads": 0}

        def state_size():
            return len(state["bytes"])

        def serialize(destination, count):
            state["writes"] += 1
            C.memmove(destination, state["bytes"], count)
            return True

        def unserialize(source, count):
            state["reads"] += 1
            state["bytes"] = C.string_at(source, count)
            return True

        # Plain callable attributes stand in for ctypes export objects;
        # the diagnostic is responsible for binding Libretro ABI types.
        native = SimpleNamespace(library=SimpleNamespace(
            retro_serialize_size=state_size,
            retro_serialize=serialize,
            retro_unserialize=unserialize,
        ))
        evidence = _native_save_state_roundtrip(native)
        self.assertTrue(evidence["supported"])
        self.assertTrue(evidence["serialized"])
        self.assertTrue(evidence["restored"])
        self.assertTrue(evidence["matching_roundtrip"])
        self.assertEqual(evidence["bytes"], len(original))
        self.assertEqual(state["writes"], 2)
        self.assertEqual(state["reads"], 1)

    def test_probe_gates_on_actual_native_manual_and_camera_callbacks(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "tools/probe_ngp_mit_homebrew.py").read_text("utf-8")
        self.assertIn("manual_a_native_positive_samples", script)
        self.assertIn("camera_b_native_positive_samples", script)
        self.assertIn("and video_ok and audio_ok and input_ok", script)
        self.assertIn("input_gate_passed", script)
        self.assertIn("cartridge_sram_persistence_verified", script)
        self.assertIn("save_state_roundtrip", script)

    def test_workflow_uses_native_core_both_video_and_audio_not_library_import(self):
        root = Path(__file__).resolve().parents[1]
        yaml = (root / ".github/workflows/v30-cores.yml").read_text("utf-8")
        script = (root / "tools/probe_ngp_mit_homebrew.py").read_text("utf-8")
        self.assertIn("ngp-mit-homebrew-video-audio", yaml)
        self.assertIn("mednafen_ngp", yaml)
        self.assertIn("native_nonzero_pcm_values", script)
        self.assertIn("video_gate_passed", script)
        self.assertIn("audio_gate_passed", script)
        self.assertIn("and audio_ok", script)
        self.assertIn("MIT", (root / "docs/V3_NGP_TEST_LICENSE.md").read_text())


if __name__ == "__main__":
    unittest.main()
