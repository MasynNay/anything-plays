"""Fail-closed exact pinned Dolphin Sys replacement used by full 3.0 test installers."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from tools.prepare_v30_dolphin_source_sys import (
    DOLPHIN_REV, _git_tree_sha, create_pinned_sys,
)
from tools.stage_v30_original_dolphin_sys import (
    ARCHIVE, REPORT, CHECKSUMS, exact_original_sys_artifact,
)

FILES = {
    "codehandler.bin": b"test only source codehandler",
    "GC/font_western.bin": b"test only source font",
    "GC/dsp_rom.bin": b"test only source DSP fixture",
    "GameSettings/TEST.ini": b"[Core]\nEnabled = True\n",
    "Readme.txt": b"TEST only original pinned source",
}
TREE = _git_tree_sha({key:(body, False) for key,body in FILES.items()})


def fixture_tar(path):
    with tarfile.open(path, "w:gz") as archive:
        for name, body in FILES.items():
            info = tarfile.TarInfo(f"dolphin-{DOLPHIN_REV}/Data/Sys/{name}")
            info.mode = 0o644
            info.size = len(body)
            archive.addfile(info, io.BytesIO(body))
        # Original GitHub parent TAR is large; make a realistic-sized
        # synthetic source TAR to exercise safe input budgets.
        blob = os.urandom(160000)
        info=tarfile.TarInfo(f"dolphin-{DOLPHIN_REV}/CMakeLists.txt")
        info.size=len(blob)
        archive.addfile(info,io.BytesIO(blob))


def fixture(root):
    source=root/"source.tar.gz"
    fixture_tar(source)
    folder=root/"input"
    folder.mkdir()
    create_pinned_sys(source, folder/ARCHIVE, folder/REPORT, expected_tree=TREE)
    _update_sha(folder)
    return folder


def _update_sha(folder):
    (folder/CHECKSUMS).write_text(
        f"{hashlib.sha256((folder/ARCHIVE).read_bytes()).hexdigest()}  {ARCHIVE}\n"
        f"{hashlib.sha256((folder/REPORT).read_bytes()).hexdigest()}  {REPORT}\n",
        encoding="ascii",
    )


class PinnedDolphinSysTenCoreStagingTests(unittest.TestCase):
    def test_source_proof_reconstructed_from_actual_zip_bytes(self):
        with TemporaryDirectory() as temp:
            folder=fixture(Path(temp))
            with patch("tools.stage_v30_original_dolphin_sys.PINNED_SYS_TREE_SHA1",TREE):
                raw,receipt=exact_original_sys_artifact(folder)
            self.assertEqual(raw,(folder/ARCHIVE).read_bytes())
            self.assertEqual(receipt["original_git_data_sys_tree_sha1"],TREE)
            self.assertEqual(receipt["pinned_sys_files"],5)
            for flag in (
                "source_correspondence_to_archived_buildbot_dolphin_verified",
                "source_asset_rights_independently_approved",
                "public_distribution_approved",
            ):
                self.assertIs(receipt[flag],False)

    def test_changed_zip_is_rejected_even_with_rewritten_metadata(self):
        with TemporaryDirectory() as temp:
            folder=fixture(Path(temp))
            previous=(folder/ARCHIVE).read_bytes()
            with zipfile.ZipFile(io.BytesIO(previous)) as upstream:
                entries=[(item.filename,upstream.read(item),item)
                         for item in upstream.infolist()]
            with zipfile.ZipFile(folder/ARCHIVE,"w",zipfile.ZIP_DEFLATED) as forged:
                for name,body,info in entries:
                    if name.endswith("codehandler.bin"):
                        body=b"forged core system file"
                    forged.writestr(info,body)
            m=json.loads((folder/REPORT).read_text("utf-8"))
            m["dolphin_sys_zip_sha256"]=hashlib.sha256((folder/ARCHIVE).read_bytes()).hexdigest()
            m["dolphin_sys_zip_size"]=(folder/ARCHIVE).stat().st_size
            changed=FILES["codehandler.bin"]
            m["dolphin_sys_extracted_bytes"]+=len(b"forged core system file")-len(changed)
            m["files"]["codehandler.bin"]["sha256"]=hashlib.sha256(b"forged core system file").hexdigest()
            m["files"]["codehandler.bin"]["size_bytes"]=len(b"forged core system file")
            (folder/REPORT).write_text(json.dumps(m), "utf-8")
            _update_sha(folder)
            with patch("tools.stage_v30_original_dolphin_sys.PINNED_SYS_TREE_SHA1",TREE):
                with self.assertRaisesRegex(ValueError,"Git tree"):
                    exact_original_sys_artifact(folder)

    def test_forged_rights_missing_checksum_extra_files_are_rejected(self):
        with TemporaryDirectory() as temp:
            folder=fixture(Path(temp))
            report=json.loads((folder/REPORT).read_text("utf-8"))
            report["public_binary_distribution_approved"]=True
            (folder/REPORT).write_text(json.dumps(report))
            _update_sha(folder)
            with patch("tools.stage_v30_original_dolphin_sys.PINNED_SYS_TREE_SHA1",TREE):
                with self.assertRaisesRegex(ValueError,"rights forged"):
                    exact_original_sys_artifact(folder)
        with TemporaryDirectory() as temp:
            folder=fixture(Path(temp))
            (folder/"unexpected.exe").write_bytes(b"no binary allowed")
            with self.assertRaisesRegex(ValueError,"missing/extra"):
                exact_original_sys_artifact(folder)
        with TemporaryDirectory() as temp:
            folder=fixture(Path(temp))
            (folder/CHECKSUMS).write_text("forged\n",encoding="ascii")
            with patch("tools.stage_v30_original_dolphin_sys.PINNED_SYS_TREE_SHA1",TREE):
                with self.assertRaisesRegex(ValueError,"SHA256SUMS"):
                    exact_original_sys_artifact(folder)


if __name__ == "__main__":
    unittest.main()
