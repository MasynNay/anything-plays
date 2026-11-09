"""Full original-source companion must match pinned GPL2+ Tia eleven-core set."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from anything_plays.v30_approved_core_map import (
    ELEVEN_TIA_EXPECTED, ELEVEN_TIA_REPOSITORIES,
)
from tools.archive_v30_corresponding_sources import archive_all
from tools.prepare_v30_source_companion import (
    validate_captured_sources, prepare_source_companion,
)

class SameProfileTiaSources(unittest.TestCase):
    def make_fake_original_checkout(self, root: Path):
        path=root/"originals"
        for name in ELEVEN_TIA_EXPECTED:
            folder=path/name
            folder.mkdir(parents=True)
            for index in range(6):
                (folder/f"original-source-{index}.c").write_text(
                    f"License terms and source header {name} file {index}\n"*200,
                    encoding="utf-8",
                )
        return path

    def test_eleven_source_tarballs_replace_only_stella_with_tia(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            checkouts=self.make_fake_original_checkout(root)
            package=archive_all(checkouts,root/"sources",verify_git=False,tia=True)
            self.assertEqual(package["core_count"],11)
            self.assertEqual(package["source_set_id"],"original-eleven-gpl2plus-tia")
            self.assertEqual(set(package["sources"]),set(ELEVEN_TIA_EXPECTED))
            self.assertNotIn("stella2014",package["sources"])
            self.assertEqual(package["sources"]["tia"]["source_commit"],
                             ELEVEN_TIA_EXPECTED["tia"])
            self.assertEqual(package["sources"]["tia"]["source_repository"],
                             ELEVEN_TIA_REPOSITORIES["tia"])
            self.assertFalse(package["public_binary_distribution_approved"])
            # Synthetic test checkouts lack Git metadata: this verifies only
            # source packaging and identity logic, not actual git correspondence.
            with self.assertRaisesRegex(ValueError,"Gitlinks"):
                validate_captured_sources(root/"sources")

    def test_unexpected_license_identity_or_stella_in_tia_packet_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            src=self.make_fake_original_checkout(root)
            archive_all(src,root/"sources",verify_git=False,tia=True)
            path=root/"sources"/"SOURCE_ACCESS_CANDIDATE_UNAPPROVED.json"
            manifest=json.loads(path.read_text())
            manifest["sources"]["stella2014"]=manifest["sources"]["tia"]
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"exact"):
                validate_captured_sources(root/"sources")

    def test_unknown_source_variant_does_not_trick_source_publisher(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            src=self.make_fake_original_checkout(root)
            archive_all(src,root/"sources",verify_git=False,tia=True)
            path=root/"sources"/"SOURCE_ACCESS_CANDIDATE_UNAPPROVED.json"
            manifest=json.loads(path.read_text())
            manifest["source_set_id"]="unreviewed-other-core-list"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"Unrecognized"):
                prepare_source_companion(root/"sources",root/"release","3.0.0")
            self.assertFalse((root/"release").exists())


if __name__=="__main__":
    unittest.main()
