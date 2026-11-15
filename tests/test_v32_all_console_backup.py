"""3.2 complete control-layout backup: strict privacy and atomic restore."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.portable_profile_library import (
    FORMAT, MAX_ARCHIVE_BYTES, make_library_archive, parse_library_archive,
    load_library_archive, save_library_archive,
)
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import (
    BUTTONS_BY_SYSTEM, ProfileStore, default_for,
)


def all_profiles():
    return {
        key: default_for(key, DEFAULT)
        for key in BUTTONS_BY_SYSTEM
    }


class AllConsoleBackupTests(unittest.TestCase):
    def test_all_18_console_profiles_round_trip_without_private_fields(self):
        source = all_profiles()
        self.assertEqual(len(source), 18)
        source["gamecube"]["zone_image"] = "/Users/private/photo.png"
        source["gba"]["rom_directory"] = "/home/secret/roms"
        source["gba"]["rgb"] = [9, 31, 117]
        source["snes"]["mapping"]["A"] = "B"
        original = copy.deepcopy(source)
        doc = make_library_archive(source)
        text = json.dumps(doc)
        self.assertEqual(doc["format"], FORMAT)
        self.assertNotIn("photo.png", text)
        self.assertNotIn("/home/secret", text)
        self.assertEqual(source, original)
        result = parse_library_archive(text)
        self.assertEqual(set(result), set(BUTTONS_BY_SYSTEM))
        self.assertEqual(result["gba"]["rgb"], [9, 31, 117])
        self.assertEqual(result["snes"]["mapping"]["A"], "B")

    def test_missing_extra_and_forged_console_rejected_before_apply(self):
        doc = make_library_archive(all_profiles())
        for key in ("gb", "gamecube"):
            altered = copy.deepcopy(doc)
            altered["profiles"].pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_library_archive(json.dumps(altered))
        altered = copy.deepcopy(doc)
        altered["profiles"]["../../../evil"] = altered["profiles"]["gb"]
        with self.assertRaises(ValueError):
            parse_library_archive(json.dumps(altered))
        altered = copy.deepcopy(doc)
        altered["profiles"]["gba"]["rom_directory"] = "/private/location"
        with self.assertRaises(ValueError):
            parse_library_archive(json.dumps(altered))
        with self.assertRaises(ValueError):
            make_library_archive({"gb": all_profiles()["gb"]})

    def test_rejects_unsafe_json_payloads_and_tampered_version(self):
        doc = make_library_archive(all_profiles())
        for bad in (
            "{\"format\":1,\"format\":2}",  # duplicate keys
            json.dumps(dict(doc, version=True)),
            json.dumps(dict(doc, version=99)),
            json.dumps(dict(doc, theme="private")),
            json.dumps(dict(doc, system_count=17)),
            json.dumps(doc).replace('"tolerance": 20', '"tolerance": NaN'),
            "[]" , "{",
        ):
            with self.subTest(payload=bad[:30]), self.assertRaises(ValueError):
                parse_library_archive(bad)
        with self.assertRaises(ValueError):
            parse_library_archive(b"x" * (MAX_ARCHIVE_BYTES + 1))

    def test_atomic_save_load_and_store_bulk_commit(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            target = base / "controls.json"
            profiles = all_profiles()
            save_library_archive(target, profiles)
            self.assertEqual(set(load_library_archive(target)), set(profiles))
            stored = ProfileStore(base / "state.json", DEFAULT)
            original = stored.get("gb")
            edited = copy.deepcopy(original)
            edited["tolerance"] = 41
            changes = {"gb": edited, "gamecube": profiles["gamecube"]}
            stored.put_many(changes)
            self.assertEqual(stored.get("gb")["tolerance"], 41)
            before = stored.path.read_bytes()
            with patch(
                "anything_plays.system_profiles.write_json_atomically",
                side_effect=OSError("disk disconnected"),
            ), self.assertRaises(OSError):
                stored.put_many({"gb": original})
            self.assertEqual(stored.get("gb")["tolerance"], 41)
            self.assertEqual(stored.path.read_bytes(), before)
            with self.assertRaises(ValueError):
                stored.put_many({"forged": edited})
            with self.assertRaises(ValueError):
                stored.put_many({"gb": None})
            self.assertEqual(stored.path.read_bytes(), before)

    def test_single_console_disk_failure_does_not_poison_later_profile_save(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "profiles.json"
            store = ProfileStore(path, DEFAULT)
            original_gba = store.get("gba")
            original_gb = store.get("gb")
            gba_changed = copy.deepcopy(original_gba)
            gba_changed["tolerance"] = 77
            with patch(
                "anything_plays.system_profiles.write_json_atomically",
                side_effect=OSError("disk full"),
            ), self.assertRaises(OSError):
                store.put("gba", gba_changed)
            self.assertEqual(store.get("gba"), original_gba)
            self.assertFalse(path.exists())
            gb_changed = copy.deepcopy(original_gb)
            gb_changed["tolerance"] = 31
            store.put("gb", gb_changed)
            fresh = ProfileStore(path, DEFAULT)
            self.assertEqual(fresh.get("gb")["tolerance"], 31)
            self.assertEqual(fresh.get("gba"), original_gba)
            self.assertEqual(store.get("gba"), original_gba)

    def test_single_console_rejects_unknown_key_without_creating_state(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "profiles.json"
            store = ProfileStore(path, DEFAULT)
            with self.assertRaises(ValueError):
                store.put("../unexpected", default_for("gb", DEFAULT))
            self.assertFalse(path.exists())
            self.assertEqual(store.profiles, {})

    def test_failed_mapping_save_rolls_back_control_and_visible_selection(self):
        from anything_plays.ui_profiles import ProfilesMixin

        class Value:
            def __init__(self, val):
                self.val = val
            def get(self):
                return self.val
            def set(self, val):
                self.val = val

        class BrokenStore:
            def put(self, _system, _profile):
                raise OSError("private disk path is unavailable")

        class Host:
            system_key = Value("gba")
            status = Value("")
            mapping_vars = {"A": Value("B")}
            cfg = {"mapping": {"A": "A"}}
            profile_store = BrokenStore()

        host = Host()
        self.assertFalse(ProfilesMixin.update_button_mapping(host, "A"))
        self.assertEqual(host.cfg["mapping"]["A"], "A")
        self.assertEqual(host.mapping_vars["A"].get(), "A")
        self.assertIn("not saved", host.status.get())
        self.assertNotIn("private disk path", host.status.get())

    def test_successful_mapping_save_persists_selected_control(self):
        from anything_plays.ui_profiles import ProfilesMixin

        class Value:
            def __init__(self, val):
                self.val = val
            def get(self):
                return self.val
            def set(self, val):
                self.val = val

        with TemporaryDirectory() as td:
            class Host:
                system_key = Value("gb")
                status = Value("")
                mapping_vars = {"A": Value("B")}
                cfg = default_for("gb", DEFAULT)
                profile_store = ProfileStore(Path(td) / "profiles.json", DEFAULT)
            host = Host()
            self.assertTrue(ProfilesMixin.update_button_mapping(host, "A"))
            self.assertEqual(host.profile_store.get("gb")["mapping"]["A"], "B")
            self.assertIn("mapping updated", host.status.get())
            self.assertEqual(
                ProfileStore(host.profile_store.path, DEFAULT).get("gb")["mapping"]["A"],
                "B",
            )

    def test_change_preview_identifies_only_changed_portable_console_settings(self):
        from anything_plays.portable_profile_library import changed_systems
        baseline = all_profiles()
        identical = parse_library_archive(
            json.dumps(make_library_archive(baseline))
        )
        self.assertEqual(changed_systems(baseline, identical), ())
        altered = copy.deepcopy(identical)
        altered["gba"]["tolerance"] = 33
        altered["gamecube"]["mapping"]["A"] = "B"
        self.assertEqual(
            changed_systems(baseline, altered), ("gba", "gamecube")
        )
        baseline["snes"]["rom_directory"] = "/private/roms"
        baseline["snes"]["zone_image"] = "/private/camera.jpg"
        self.assertEqual(
            changed_systems(baseline, altered), ("gba", "gamecube")
        )

    def test_change_preview_rejects_incomplete_profiles_without_side_effects(self):
        from anything_plays.portable_profile_library import changed_systems
        baseline = all_profiles()
        incoming = parse_library_archive(
            json.dumps(make_library_archive(baseline))
        )
        original = copy.deepcopy(incoming)
        with self.assertRaises(ValueError):
            changed_systems({"gba": baseline["gba"]}, incoming)
        tampered = copy.deepcopy(incoming)
        del tampered["gb"]
        with self.assertRaises(ValueError):
            changed_systems(baseline, tampered)
        self.assertEqual(incoming, original)

    def test_actual_installed_preview_smoke_exercises_backup_restore_undo(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "anything_plays/preview_setup_smoke.py"
        ).read_text("utf-8")
        required = (
            "_exercise_installed_control_archive(app, root)",
            '_click_button(root, "Back up all 18")',
            '_click_button(root, "Restore all 18")',
            '_click_button(root, "Undo all restore")',
            'return_value=False',
            'return_value=True',
            'rejected.call_count != 1',
            '"v32_control_archive_roundtrip_verified"',
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, source)
        from tools.verify_v32_installed_gui import REQUIRED_TRUE
        self.assertIn("v32_control_archive_roundtrip_verified", REQUIRED_TRUE)

    def test_frozen_ttk_undo_control_uses_native_state_instead_of_string_equality(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "anything_plays/preview_setup_smoke.py"
        ).read_text("utf-8")
        # Restrict the assertion to calls on this specific Undo widget:
        # the nearby explanatory comment legitimately mentions cget().
        self.assertNotIn(
            '_undo_all_profile_restore_button.cget("state")', source,
        )
        self.assertIn(
            '_undo_all_profile_restore_button.instate(["disabled"])',
            source,
        )
        self.assertIn(
            '_undo_all_profile_restore_button.instate(["!disabled"])',
            source,
        )

    def test_backup_ui_uses_atomic_full_set_and_disarms_controls(self):
        source = (Path(__file__).resolve().parents[1]
                  / "anything_plays/ui_profiles.py").read_text("utf-8")
        from ast import parse, FunctionDef, ClassDef, walk, Call, Attribute
        tree = parse(source)
        cls = next(item for item in tree.body
                   if isinstance(item, ClassDef) and item.name == "ProfilesMixin")
        methods = {item.name: item for item in cls.body
                   if isinstance(item, FunctionDef)}
        for method in ("restore_all_profiles", "undo_all_profile_restore"):
            fn = methods[method]
            calls = [node.func.attr for node in walk(fn)
                     if isinstance(node, Call) and isinstance(node.func, Attribute)]
            self.assertIn("stop_controls", calls)
            self.assertIn("put_many", calls)
        self.assertIn("askyesno", source)
        self.assertIn("_last_profile_archive_import", source)


if __name__ == "__main__":
    unittest.main()
