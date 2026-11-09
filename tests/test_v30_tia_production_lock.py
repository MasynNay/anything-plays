"""GPLv2-or-later Tia release identity is conditional, never auto-approved."""
import unittest

from tools.v30_release_lock import (
    ALTERNATIVE_CORE_NAMES, ALTERNATIVE_TIA_CORE_ORDER,
    ALTERNATIVE_TIA_CORE_NAMES, SOURCE_BUILT_ELEVEN_TIA,
    ordered_core_names_for_lock, selected_core_set, selected_source_families,
)


class TiaProductionCoreLockTests(unittest.TestCase):
    def tia_lock(self):
        return {
            "core_set_id": "gpl-source-built-eleven-tia",
            "legacy_noncommercial_native_binaries_excluded": True,
            "source_built_alternative_binary_rights_reviewed": True,
            "eleven_source_built_families_reviewed": True,
            "zero_unchanged_native_families_reviewed": True,
            "gpl2plus_atari_source_replacement_reviewed": True,
            "original_gpl2_only_stella_excluded": True,
            # Synthetic lock NEVER has global distribution approval.
            "approved_for_binary_distribution": False,
        }

    def test_new_alternative_keeps_exact_same_11_core_slots(self):
        lock=self.tia_lock()
        names=selected_core_set(lock)
        self.assertEqual(names, ALTERNATIVE_TIA_CORE_NAMES)
        self.assertEqual(len(names), 11)
        self.assertEqual(len(ALTERNATIVE_TIA_CORE_ORDER), 11)
        self.assertEqual(names, SOURCE_BUILT_ELEVEN_TIA)
        self.assertEqual(len(set(ALTERNATIVE_TIA_CORE_ORDER)), 11)
        self.assertIn("tia", names)
        self.assertNotIn("stella2014", names)
        self.assertEqual(names - ALTERNATIVE_CORE_NAMES, {"tia"})
        self.assertEqual(ALTERNATIVE_CORE_NAMES - names, {"stella2014"})
        self.assertEqual(ordered_core_names_for_lock(lock), ALTERNATIVE_TIA_CORE_ORDER)
        self.assertEqual(selected_source_families(lock), SOURCE_BUILT_ELEVEN_TIA)

    def test_excluded_gpl2_only_core_must_be_reviewed(self):
        for flag in ("gpl2plus_atari_source_replacement_reviewed",
                     "original_gpl2_only_stella_excluded"):
            with self.subTest(flag=flag):
                lock=self.tia_lock()
                lock[flag]=False
                with self.assertRaisesRegex(ValueError, "Atari native"):
                    selected_core_set(lock)

    def test_unapproved_mode_never_grants_rights(self):
        from tools.v30_release_lock import load_approved_lock
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            lock=self.tia_lock()
            lock.update(schema_version=1, native_core_count=11, system_profile_count=18,
                        license_compatibility_reviewed=False,
                        corresponding_source_inventory_verified=False,
                        targets={})
            name=Path(tmp)/"immutable-review.json"
            name.write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError, "approved_for_binary_distribution"):
                load_approved_lock(name)

    def test_other_lineups_still_have_identical_names(self):
        lock=self.tia_lock()
        lock.pop("gpl2plus_atari_source_replacement_reviewed")
        lock.pop("original_gpl2_only_stella_excluded")
        lock["core_set_id"]="gpl-source-built-eleven"
        self.assertEqual(selected_core_set(lock), ALTERNATIVE_CORE_NAMES)
        self.assertIn("stella2014", selected_core_set(lock))


if __name__=="__main__":
    unittest.main()
