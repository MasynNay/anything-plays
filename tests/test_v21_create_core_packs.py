"""Core-pack builder cannot turn unreviewed CI nightlies into live updates."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import unittest
import zipfile

from anything_plays.core_packs import (
    _validate_asset_metadata, _verify_core_pack, RELEASE_PREFIX,
    _release_asset, target_identity,
)
from tools.create_core_packs import create_candidate_packs


class CorePackBuilderTests(unittest.TestCase):
    def test_builder_provenance_and_review_gates(self):
        target, ext = target_identity()
        name = "mgba"
        filename = name + "_libretro" + ext
        magic = {".so": b"\x7fELF", ".dll": b"MZaa",
                 ".dylib": b"\xcf\xfa\xed\xfe"}[ext]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cores = root / "cores"
            cores.mkdir()
            binary = magic + b"\x04" * 14000
            (cores / filename).write_bytes(binary)
            (cores / "CORE_PROVENANCE.json").write_text(json.dumps({
                "cores": [{"name": name, "file": filename,
                           "sha256": hashlib.sha256(binary).hexdigest()}]
            }))
            output = root / "candidates"
            tag = "v2.1.0-alpha.2"
            packages = create_candidate_packs(
                cores, output, tag, selected=[name]
            )
            self.assertEqual(len(packages), 1)
            archive = Path(packages[0]["file"])
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as zipped:
                manifest = json.loads(zipped.read("core-pack.json"))
                self.assertIs(manifest["third_party_license_reviewed"], False)
                self.assertIs(manifest["packaged_runtime_tested"], False)
            item = {
                "name": name, "target": target, "release": tag,
                "url": RELEASE_PREFIX + tag + "/" + _release_asset(name, target),
                "sha256": packages[0]["sha256"],
                "size": archive.stat().st_size,
            }
            _validate_asset_metadata(item)
            with self.assertRaisesRegex(ValueError, "license and runtime review"):
                _verify_core_pack(archive.read_bytes(), item)

            reviewed = create_candidate_packs(
                cores, root / "reviewed", tag,
                selected=[name], license_reviewed=True, runtime_tested=True,
            )
            result = _verify_core_pack(Path(reviewed[0]["file"]).read_bytes(), {
                **item,
                "sha256": reviewed[0]["sha256"],
                "size": Path(reviewed[0]["file"]).stat().st_size,
            })
            self.assertEqual(result[0], hashlib.sha256(binary).hexdigest())
            self.assertEqual(result[1], filename)

    def test_wrong_provenance_never_publishes(self):
        _, ext = target_identity()
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            name = "mgba"
            filename = name + "_libretro" + ext
            (folder / filename).write_bytes(b"invalid binary data" * 800)
            (folder / "CORE_PROVENANCE.json").write_text(json.dumps({
                "cores": [{"name": name, "file": filename, "sha256": "0" * 64}]
            }))
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                create_candidate_packs(
                    folder, folder / "output", "v2.1.0-alpha.3",
                    selected=[name], license_reviewed=True, runtime_tested=True,
                )


if __name__ == "__main__":
    unittest.main()
