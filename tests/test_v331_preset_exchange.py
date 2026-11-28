"""Local preset collection exchange: privacy, validation and atomic import."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.named_presets import NamedPresetStore
from anything_plays.portable_profiles import make_bundle
from anything_plays.preset_exchange import (
    FORMAT, VERSION, MAX_COLLECTION_BYTES, MAX_COLLECTION_ENTRIES,
    read_collection, write_collection, validate_collection,
)
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import default_for


class PresetExchangeTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "collection.json"
        self.store = NamedPresetStore(self.root / "library.json", ("Dark",))
        self.entries = [self.entry("gba", "Action"), self.entry("snes", "Action")]

    def entry(self, system, label, **changes):
        profile = default_for(system, DEFAULT)
        profile.update(changes)
        return {"label": label, "bundle": make_bundle(system, profile)}

    def test_multi_console_round_trip_and_atomic_import(self):
        write_collection(self.path, self.entries, ("Dark",))
        document = read_collection(self.path, ("Dark",))
        self.assertEqual(document["layouts"], self.entries)
        self.assertEqual(self.store.import_collection(document["layouts"]), (2, 0))
        self.assertEqual(self.store.list("gba"), ("Action",))
        self.assertEqual(self.store.list("snes"), ("Action",))

    def test_identical_import_is_idempotent(self):
        self.store.import_collection(self.entries)
        prior = self.store.path.read_bytes()
        with patch.object(self.store, "_write", side_effect=AssertionError("no write")):
            self.assertEqual(self.store.import_collection(self.entries), (0, 2))
        self.assertEqual(self.store.path.read_bytes(), prior)

    def test_casefold_collision_rejects_entire_batch(self):
        self.store.import_collection(self.entries)
        prior = self.store.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.import_collection([
                self.entry("gb", "New"),
                self.entry("gba", "action", tolerance=30),
            ])
        self.assertEqual(self.store.path.read_bytes(), prior)
        self.assertEqual(self.store.list("gb"), ())

    def test_capacity_conflict_does_not_import_any_console(self):
        for index in range(12):
            self.store.save("gba", str(index), default_for("gba", DEFAULT))
        prior = self.store.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.import_collection([self.entry("gb", "New"),
                                          self.entry("gba", "Overflow")])
        self.assertEqual(self.store.path.read_bytes(), prior)

    def test_local_names_not_exported_when_relabeling(self):
        self.store.save("gba", "Private local name",
                        {**default_for("gba", DEFAULT), "zone_image": "/private/art.png",
                         "rom_directory": "/secret/roms", "token": "PRIVATE_TOKEN"})
        system, name, bundle = self.store.collection_candidates()[0]
        self.assertEqual(name, "Private local name")
        write_collection(self.path, [{"label": "Layout 1", "bundle": bundle}], ("Dark",))
        text = self.path.read_text(encoding="utf-8")
        for forbidden in ("Private local name", "/private/", "/secret/", "PRIVATE_TOKEN"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(self.store.list(system), (name,))

    def test_duplicate_same_console_label_rejected(self):
        with self.assertRaises(ValueError):
            write_collection(self.path, [self.entry("gba", "Action"),
                                         self.entry("gba", "action")], ("Dark",))
        self.assertFalse(self.path.exists())

    def test_unknown_fields_and_private_bundle_values_rejected(self):
        for mutate in (
            lambda d: d.update({"owner": "Private"}),
            lambda d: d["layouts"][0].update({"path": "/private/roms"}),
            lambda d: d["layouts"][0]["bundle"]["profile"].update({"zone_image": "secret"}),
            lambda d: d["layouts"][0]["bundle"].update({"system": "unknown"}),
            lambda d: d["layouts"][0]["bundle"].update({"theme": "Unsupported"}),
        ):
            doc = {"format": FORMAT, "version": VERSION, "layouts": copy.deepcopy(self.entries)}
            mutate(doc)
            with self.assertRaises(ValueError):
                validate_collection(doc, ("Dark",))

    def test_bad_versions_duplicate_keys_and_oversize_rejected(self):
        for raw in (
            b"{broken",
            b'{"format":"anything-plays-preset-collection","version":2,"layouts":[]}',
            b'{"format":"anything-plays-preset-collection","version":1,"version":1,"layouts":[]}',
            b"x" * (MAX_COLLECTION_BYTES + 1),
        ):
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError):
                read_collection(self.path, ("Dark",))
        with self.assertRaises(ValueError):
            write_collection(self.path, [self.entry("gba", str(i))
                for i in range(MAX_COLLECTION_ENTRIES + 1)], ("Dark",))

    def test_failed_write_does_not_modify_existing_library(self):
        self.store.import_collection(self.entries)
        prior = self.store.path.read_bytes()
        with patch("anything_plays.named_presets.write_json_atomically",
                   side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.import_collection([self.entry("gb", "New")])
        self.assertEqual(self.store.path.read_bytes(), prior)

    def test_corrupt_local_library_never_overwritten(self):
        self.store.path.write_bytes(b"{broken")
        with self.assertRaises(ValueError):
            self.store.import_collection(self.entries)
        self.assertEqual(self.store.path.read_bytes(), b"{broken")

    def test_candidates_are_detached_from_persisted_data(self):
        self.store.import_collection(self.entries)
        candidates = self.store.collection_candidates()
        candidates[0][2]["profile"]["zones"].clear()
        self.assertTrue(self.store.get("gba", "Action")["profile"]["zones"])

    def test_mixed_identical_and_new_entries_commit_once(self):
        self.store.import_collection(self.entries)
        with patch.object(self.store, "_write", wraps=self.store._write) as writer:
            self.assertEqual(self.store.import_collection([
                self.entry("gba", "action"), self.entry("gb", "New"),
            ]), (1, 1))
        writer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
