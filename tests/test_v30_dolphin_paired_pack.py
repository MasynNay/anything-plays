"""GameCube must be installable *only* as a complete verified core+Sys pack.

All ZIP bytes and fake native headers are synthetic. No commercial games,
Dolphin executable, external network, GPU, or user installation is required.
"""
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from anything_plays import core_packs
from anything_plays.dolphin_pack import (
    SYS_PREFIX, SYS_MANIFEST, make_sys_index, sha256,
)
from tools.create_core_packs import create_candidate_packs


class Response:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, maximum):
        return self.data[:maximum]


def fake_dolphin_folder(root):
    root = Path(root)
    cores = root / "cores"
    sysdir = cores / "dolphin-emu" / "Sys"
    sysdir.mkdir(parents=True)
    target, extension = core_packs.target_identity()
    filename = f"dolphin_libretro{extension}"
    magic = {".dll": b"MZaa", ".so": b"\x7fELF",
             ".dylib": b"\xcf\xfa\xed\xfe"}[extension]
    content = magic + b"D" * 18000
    (cores / filename).write_bytes(content)
    (cores / "CORE_PROVENANCE.json").write_text(json.dumps({
        "cores": [{
            "name": "dolphin", "file": filename,
            "sha256": sha256(content),
            "reported_source_revision": "3a" * 20,
        }]
    }))
    files = {
        "codehandler.bin": b"synthetic Gecko codes",
        "GC/font_western.bin": b"fake font data",
        "GC/font_japanese.bin": b"fake font data 2",
        "Resources/dsp_rom.bin": b"fake dsp",
        "Resources/gfx.dat": b"fake shader",
        "Resources/sub/folder.ini": b"fake settings",
    }
    for name, data in files.items():
        location = sysdir / name
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_bytes(data)
    (cores / "DOLPHIN_SYS_PROVENANCE.json").write_text(json.dumps({
        "archive_sha256": "f" * 64,
        "file_count": len(files),
        "files": {
            name: {"sha256": sha256(value), "size_bytes": len(value)}
            for name, value in files.items()
        },
    }))
    return cores, target, extension, files


def item_for(result):
    return {
        "name": "dolphin", "target": result["target"],
        "release": result["release"], "size": Path(result["file"]).stat().st_size,
        "sha256": result["sha256"],
        "url": (core_packs.RELEASE_PREFIX + result["release"] + "/"
                + core_packs._release_asset("dolphin", result["target"])),
    }


class GameCubePairedPackTests(unittest.TestCase):
    def test_cumulative_zip_expansion_guard_before_extracting_any_file(self):
        # All six entries are individually within MAX_SYS_SINGLE, but their
        # combined *declared uncompressed* size exceeds MAX_SYS_TOTAL.
        # None of their contents should be read by the native updater.
        from anything_plays.dolphin_pack import (
            verify_dolphin_pack, MAX_SYS_SINGLE, MAX_SYS_TOTAL
        )
        from unittest.mock import patch
        from zipfile import ZipInfo
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cores, _, _, _ = fake_dolphin_folder(root)
            result = create_candidate_packs(
                cores, root / "zip", "v3.0.0-alpha.2-cores",
                selected=["dolphin"], license_reviewed=True,
                runtime_tested=True,
            )[0]
            real_bytes = Path(result["file"]).read_bytes()
            with zipfile.ZipFile(io.BytesIO(real_bytes)) as fixture:
                entries = fixture.infolist()
                # zipfile.ZipInfo.file_size is populated from the central
                # directory. Replacing the list simulates an attack without
                # allocating an 80+ MiB test archive.
                bloated = [
                    ZipInfo(f"dolphin-emu/Sys/mock-{index}.bin")
                    for index in range(6)
                ]
                for entry in bloated:
                    entry.file_size = MAX_SYS_SINGLE
                self.assertGreater(sum(e.file_size for e in bloated),
                                   MAX_SYS_TOTAL)
                with patch.object(fixture, "infolist",
                                  return_value=entries + bloated), patch(
                                       "anything_plays.dolphin_pack.zipfile.ZipFile",
                                       return_value=fixture
                                  ), patch.object(
                                      fixture, "read",
                                      side_effect=AssertionError(
                                          "ZIP contents read before size limits"
                                      )
                                  ):
                    with self.assertRaisesRegex(ValueError, "expanded Sys"):
                        verify_dolphin_pack(
                            real_bytes, item_for(result)
                        )

    def test_unreviewed_candidate_fails_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cores, target, ext, files = fake_dolphin_folder(root)
            result = create_candidate_packs(
                cores, root / "candidate", "v3.0.0-alpha.2-cores",
                selected=["dolphin"],
            )[0]
            self.assertEqual(result["sys_file_count"], len(files))
            archive = Path(result["file"]).read_bytes()
            with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                self.assertIn(f"dolphin_libretro{ext}", zipped.namelist())
                self.assertIn("dolphin-emu/Sys/codehandler.bin", zipped.namelist())
                self.assertIn(SYS_MANIFEST, zipped.namelist())
                meta = json.loads(zipped.read("core-pack.json"))
                self.assertFalse(meta["third_party_license_reviewed"])
                self.assertFalse(meta["packaged_runtime_tested"])
                self.assertEqual(meta["schema"], 2)
            with self.assertRaisesRegex(ValueError, "Unreviewed"):
                core_packs.install_core_pack(
                    item_for(result), root=root / "managed",
                    opener=lambda req, timeout: Response(archive)
                )
            self.assertFalse((root / "managed" / "active.json").exists())

    def test_complete_reviewed_pack_installs_verifies_and_rolls_back(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cores, target, ext, files = fake_dolphin_folder(root)
            result = create_candidate_packs(
                cores, root / "candidate", "v3.0.0-alpha.2-cores",
                selected=["dolphin"], license_reviewed=True,
                runtime_tested=True,
            )[0]
            blob = Path(result["file"]).read_bytes()
            asset = item_for(result)
            installed = Path(core_packs.install_core_pack(
                asset, root=root / "managed",
                opener=lambda req, timeout: Response(blob)
            ))
            self.assertTrue(installed.is_file())
            self.assertEqual(
                core_packs.managed_core_path("dolphin", root=root / "managed"),
                str(installed),
            )
            from anything_plays.gamecube_software import (
                packaged_dolphin_system_directory,
            )
            self.assertEqual(
                packaged_dolphin_system_directory(installed), installed.parent
            )
            self.assertEqual(
                (installed.parent / SYS_PREFIX / "codehandler.bin").read_bytes(),
                files["codehandler.bin"],
            )
            self.assertTrue(
                core_packs.installed_pack_revision("dolphin", root=root / "managed")
            )
            self.assertTrue(
                core_packs.rollback_core("dolphin", root=root / "managed")
            )
            self.assertIsNone(
                core_packs.managed_core_path("dolphin", root=root / "managed")
            )
            self.assertTrue(installed.is_file())  # Immutable object retained.

    def test_changed_or_deleted_sys_never_claims_gamecube_installed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cores, _, _, _ = fake_dolphin_folder(root)
            result = create_candidate_packs(
                cores, root / "zip", "v3.0.0-alpha.2-cores",
                selected=["dolphin"], license_reviewed=True, runtime_tested=True,
            )[0]
            managed = root / "managed"
            installed = Path(core_packs.install_core_pack(
                item_for(result), root=managed,
                opener=lambda req, timeout: Response(Path(result["file"]).read_bytes())
            ))
            sysfile = installed.parent / SYS_PREFIX / "GC/font_western.bin"
            sysfile.write_bytes(b"tampered")
            self.assertIsNone(core_packs.managed_core_path("dolphin", root=managed))
            # Reusing a corrupt immutable object must not reactivate it.
            with self.assertRaisesRegex(ValueError, "installed-file verification"):
                core_packs.install_core_pack(
                    item_for(result), root=managed,
                    opener=lambda req, timeout: Response(Path(result["file"]).read_bytes())
                )
            self.assertIsNone(core_packs.managed_core_path("dolphin", root=managed))

    def test_missing_sys_or_unexpected_path_must_not_activate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cores, _, _, _ = fake_dolphin_folder(root)
            result = create_candidate_packs(
                cores, root / "zip", "v3.0.0-alpha.2-cores",
                selected=["dolphin"], license_reviewed=True, runtime_tested=True,
            )[0]
            blob = Path(result["file"]).read_bytes()
            for unwanted in ("missing", "traversal", "changed"):
                with self.subTest(unwanted=unwanted):
                    out = io.BytesIO()
                    with zipfile.ZipFile(io.BytesIO(blob)) as source:
                        with zipfile.ZipFile(out, "w") as target:
                            for entry in source.infolist():
                                if unwanted == "missing" and entry.filename.endswith("codehandler.bin"):
                                    continue
                                content = source.read(entry)
                                if unwanted == "changed" and entry.filename.endswith("codehandler.bin"):
                                    content = b"unexpected replacement"
                                target.writestr(entry, content)
                            if unwanted == "traversal":
                                target.writestr("../injected.txt", b"not allowed")
                    modified = out.getvalue()
                    item = dict(item_for(result), sha256=sha256(modified),
                                size=len(modified))
                    managed = root / ("managed-" + unwanted)
                    with self.assertRaises(ValueError):
                        core_packs.install_core_pack(
                            item, root=managed,
                            opener=lambda req, timeout: Response(modified)
                        )
                    self.assertFalse((managed / "active.json").exists())


if __name__ == "__main__":
    unittest.main()
