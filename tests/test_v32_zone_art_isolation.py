"""3.2 zone-art cache isolation and safe camera-grid persistence.

All tests use temporary local files and synthetic image/profile data.
No webcam, ROM, controller or internet connection is opened.
"""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from anything_plays.build_identity import make_identity
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import ProfileStore, default_for
from anything_plays.ui_zones import ZonesMixin
from anything_plays.zone_art_storage import (
    save_cached_zone_art, zone_art_cache_path,
)


class Value:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class ZoneStorageTests(unittest.TestCase):
    def test_preview_image_stays_private_and_legacy_cache_untouched(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            prefs = base / ".config" / "anything-plays-32-preview" / "preferences.json"
            legacy = base / ".config" / "anything-plays" / "zone-art.png"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"original stable artwork")
            identity = make_identity("v32_preview")
            image = Image.new("RGB", (4, 3), (12, 43, 76))
            path = save_cached_zone_art(image, prefs, identity=identity)
            self.assertEqual(path, prefs.with_name("zone-art.png"))
            self.assertEqual(legacy.read_bytes(), b"original stable artwork")
            with Image.open(path) as written:
                self.assertEqual(written.size, (4, 3))
                self.assertEqual(written.getpixel((0, 0)), (12, 43, 76))
            self.assertEqual(list(path.parent.glob(".zone-art-*.tmp")), [])

    def test_preview_rejects_bad_namespace_symlinks_and_hardlinks(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            root = base / ".config"
            scope = root / "anything-plays-32-preview"
            scope.mkdir(parents=True)
            prefs = scope / "preferences.json"
            identity = make_identity("v32_preview")
            image = Image.new("RGB", (2, 2), (4, 5, 6))
            with self.assertRaises(ValueError):
                zone_art_cache_path(root / "anything-plays-31" / "preferences.json",
                                    identity=identity)
            stable = root / "stable-art.png"
            stable.write_bytes(b"stable image")
            cache = prefs.with_name("zone-art.png")
            try:
                cache.symlink_to(stable)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ValueError):
                    save_cached_zone_art(image, prefs, identity=identity)
                self.assertEqual(stable.read_bytes(), b"stable image")
                cache.unlink()
            try:
                cache.hardlink_to(stable)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ValueError):
                    save_cached_zone_art(image, prefs, identity=identity)
                self.assertEqual(stable.read_bytes(), b"stable image")
                cache.unlink()

    def test_failed_replacement_keeps_original_png(self):
        with TemporaryDirectory() as td:
            prefs = Path(td) / "anything-plays-32-preview" / "preferences.json"
            identity = make_identity("v32_preview")
            previous = Image.new("RGB", (2, 2), (200, 0, 0))
            changed = Image.new("RGB", (2, 2), (0, 0, 200))
            target = save_cached_zone_art(previous, prefs, identity=identity)
            before = target.read_bytes()
            with patch("anything_plays.zone_art_storage.os.replace",
                       side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    save_cached_zone_art(changed, prefs, identity=identity)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(list(target.parent.glob(".zone-art-*.tmp")), [])

    def test_non_preview_path_retained_for_compatibility(self):
        with TemporaryDirectory() as td:
            path = zone_art_cache_path(
                "ignored", identity=make_identity("preview1"), home=td
            )
            self.assertEqual(
                path, Path(td) / ".config" / "anything-plays" / "zone-art.png"
            )

    def test_grid_disk_failure_preserves_geometry_and_latched_state(self):
        class FailingStore:
            def put(self, _system, _profile):
                raise OSError("drive offline")

        class Host:
            system_key = Value("gba")
            shuffle_enabled = Value(True)
            status = Value("")
            _shuffle_latched = True
            profile_store = FailingStore()
            cfg = default_for("gba", DEFAULT)

            def read_settings(self):
                self.cfg["tolerance"] = 24

        host = Host()
        host.cfg = copy.deepcopy(host.cfg)
        host.cfg["zones"]["Shuffle"] = [0.1, 0.2, 0.3, 0.4]
        before = copy.deepcopy(host.cfg)
        self.assertFalse(ZonesMixin.make_symmetric_grid(host))
        self.assertEqual(host.cfg, before)
        self.assertTrue(host._shuffle_latched)
        self.assertIn("not saved", host.status.get())
        self.assertNotIn("drive offline", host.status.get())

    def test_grid_success_persists_valid_geometry(self):
        with TemporaryDirectory() as td:
            class Host:
                system_key = Value("gba")
                shuffle_enabled = Value(True)
                status = Value("")
                _shuffle_latched = True
                profile_store = ProfileStore(Path(td) / "profiles.json", DEFAULT)
                cfg = default_for("gba", DEFAULT)
                def read_settings(self):
                    pass

            host = Host()
            host.cfg = copy.deepcopy(host.cfg)
            host.cfg["zones"]["Shuffle"] = [0.1, 0.2, 0.3, 0.4]
            self.assertTrue(ZonesMixin.make_symmetric_grid(host))
            self.assertFalse(host._shuffle_latched)
            self.assertEqual(
                host.profile_store.get("gba")["zones"], host.cfg["zones"]
            )

    def test_debounced_slider_save_handles_disk_error(self):
        class Host:
            _closing = False
            _zone_label_save_job = 123
            system_key = Value("gb")
            status = Value("")
            cfg = default_for("gb", DEFAULT)
            def read_settings(self):
                pass
            class profile_store:
                @staticmethod
                def put(*_args):
                    raise OSError("disk full")
        host = Host()
        ZonesMixin.save_zone_label_size(host)
        self.assertIsNone(host._zone_label_save_job)
        self.assertIn("not saved", host.status.get())


if __name__ == "__main__":
    unittest.main()
