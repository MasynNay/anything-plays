"""Eleventh pristine original Dolphin source/native staging must fail closed.

All fixtures are synthetic. No third-party core, commercial ROM, GPU, network,
Dolphin installation, or distribution approval is involved.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from anything_plays.v30_gpl_trial import MARKER
from tools.stage_v30_eleven_source_inputs import (
    NOTICE_PATHS, REV, sha, stage_eleven,
)
from tools.stage_v30_gpl_trial_inputs import package_native_zip


class ElevenOriginalSourceDolphinStages(unittest.TestCase):
    def fixture(self, root):
        root=Path(root)
        ten=root/'ten'
        source=root/'dolphin-upstream'
        ten.mkdir()
        source.mkdir()
        native=root/'dolphin_libretro.so'
        native.write_bytes(b'ELF-synthetic-research-only' * 12000)
        old=b'old-unknown-source-archive'
        (ten/'dolphin_libretro.so.zip').write_bytes(package_native_zip('dolphin','.so',old))
        (ten/'Dolphin.zip').write_bytes(b'exact pinned Dolphin Sys archive placeholder')
        (ten/'SENTINEL.txt').write_text('preserve authentic original ten-core data')
        data={
            'schema_version':1,
            'target':'linux-x64',
            'native_core_count':11,
            'all_console_profiles':18,
            'total_source_built_core_families':10,
            'original_unchanged_core_archives':1,
            'public_binary_distribution_approved':False,
            'combined_gpl_license_reviewed':False,
            'physical_qa_approved':False,
            'production_core_substitution_approved':False,
            'source_built_n64':{'real':True},
            'source_exact_original_dolphin_sys':{'public_distribution_approved':False},
        }
        (ten/MARKER).write_text(json.dumps(data)+'\n')
        for original in NOTICE_PATHS:
            p=source/original
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((b'The original Dolphin source contains GPL, MIT, CC0 and BSD licensing records.\n')*3)
        build_proof=root/'compiler-emitted-dolphin-source.json'
        build_proof.write_text(json.dumps({
            'parent_commit':REV,
            'direct_gitlinks_verified':34,
            'nested_gitlinks_verified':3,
            'original_unmodified_dolphin_source_compiled':True,
            'built_from_original_pinned_git_tree':True,
            'source_build_target':'linux-x64',
            'native_sha256':sha(native.read_bytes()),
            'native_size_bytes':native.stat().st_size,
            'old_buildbot_binary_equivalence_claimed':False,
            'public_binary_distribution_approved':False,
        }))
        return ten,source,native,build_proof

    @staticmethod
    def verified_source(_source):
        return {'parent_commit':REV,'direct_gitlinks_verified':34,'nested_gitlinks_verified':3}

    @staticmethod
    def verified_native(path, target):
        assert target=='linux-x64'
        return {'native_sha256':sha(Path(path).read_bytes()),
                'native_size_bytes':Path(path).stat().st_size}

    def run_stage(self,root,**changes):
        ten,source,native,build_report=self.fixture(root)
        row={
            'ten_dir':ten,'original_source':source,'native':native,
            'source_build_report':build_report,
            'target':'linux-x64','output':Path(root)/'eleven',
            'evidence':Path(root)/'report.json',
            'inspect_source':self.verified_source,
            'inspect_native':self.verified_native,
        }
        row.update(changes)
        env={
            'AP_V30_GPL_TRIAL':'1',
            'AP_V30_TEST_CORES':'1',
            'AP_RELEASE_BUILD':'0',
            'AP_V30_APPROVED_RELEASE':'0',
        }
        with patch.dict(os.environ,env):
            return row,stage_eleven(**row)

    def test_replaces_only_last_buildbot_core_using_original_native_and_source_notices(self):
        with TemporaryDirectory() as td:
            args,marker=self.run_stage(td)
            out=args['output']
            self.assertEqual(marker['total_source_built_core_families'],11)
            self.assertEqual(marker['original_unchanged_core_archives'],0)
            row=marker['source_built_dolphin']
            self.assertEqual(row['source_commit'],REV)
            self.assertEqual((out/'SENTINEL.txt').read_text(),
                             'preserve authentic original ten-core data')
            self.assertEqual((out/'Dolphin.zip').read_bytes(),
                             (args['ten_dir']/'Dolphin.zip').read_bytes())
            with ZipFile(out/'dolphin_libretro.so.zip') as z:
                self.assertEqual(z.namelist(),['dolphin_libretro.so'])
                self.assertEqual(z.read('dolphin_libretro.so'),args['native'].read_bytes())
            self.assertNotEqual(
                (out/'dolphin_libretro.so.zip').read_bytes(),
                (args['ten_dir']/'dolphin_libretro.so.zip').read_bytes())
            self.assertEqual(sha((out/'dolphin_libretro.so.zip').read_bytes()),
                             row['native_archive_sha256'])
            for original, copied in NOTICE_PATHS.items():
                self.assertEqual((out/copied).read_bytes(),
                                 (args['original_source']/original).read_bytes())
                self.assertEqual(row['original_source_notices'][copied]['sha256'],
                                 sha((out/copied).read_bytes()))
            for flag in ('public_binary_distribution_approved','combined_gpl_license_reviewed',
                         'physical_qa_approved','production_core_substitution_approved'):
                self.assertIs(marker[flag],False)
            self.assertIs(row['public_binary_distribution_approved'],False)
            report=json.loads(args['evidence'].read_text())
            self.assertEqual(report['source_built_families'],11)
            self.assertFalse(report['public_binary_distribution_approved'])

    def test_new_unapproved_native_is_not_staged_without_correct_source_identity(self):
        with TemporaryDirectory() as td:
            args = {}
            def wrong_source(_):
                return {'parent_commit':'0'*40,'direct_gitlinks_verified':34,
                        'nested_gitlinks_verified':3}
            with self.assertRaisesRegex(ValueError,'pinned Dolphin'):
                args,_=self.run_stage(td,inspect_source=wrong_source)
            self.assertFalse((Path(td)/'eleven').exists())

    def test_fake_native_checksum_is_rejected_before_any_output(self):
        with TemporaryDirectory() as td:
            def fake_native(_native,_target):
                return {'native_sha256':'f'*64,'native_size_bytes':400000}
            with self.assertRaisesRegex(ValueError,'compiled source proof'):
                self.run_stage(td,inspect_native=fake_native)
            self.assertFalse((Path(td)/'eleven').exists())

    def test_license_notice_missing_refuses_to_stage(self):
        with TemporaryDirectory() as td:
            # Use one already-built fixture, not the standard helper that
            # creates a new file layout on each call.
            ten,source,native,build_report=self.fixture(td)
            (source/'COPYING').unlink()
            with patch.dict(os.environ,{
                'AP_V30_GPL_TRIAL':'1','AP_V30_TEST_CORES':'1',
                'AP_RELEASE_BUILD':'0','AP_V30_APPROVED_RELEASE':'0'}):
                with self.assertRaisesRegex(ValueError,'license'):
                    stage_eleven(
                        ten_dir=ten,original_source=source,native=native,
                        source_build_report=build_report,
                        target='linux-x64',output=Path(td)/'eleven',
                        evidence=Path(td)/'report.json',
                        inspect_source=self.verified_source,
                        inspect_native=self.verified_native,
                    )
            self.assertFalse((Path(td)/'eleven').exists())

    def test_approval_flag_in_existing_archive_does_not_allow_relabeling(self):
        with TemporaryDirectory() as td:
            ten,source,native,build_report=self.fixture(td)
            marker=ten/MARKER
            data=json.loads(marker.read_text())
            data['public_binary_distribution_approved']=True
            marker.write_text(json.dumps(data))
            with patch.dict(os.environ,{
                'AP_V30_GPL_TRIAL':'1','AP_V30_TEST_CORES':'1',
                'AP_RELEASE_BUILD':'0','AP_V30_APPROVED_RELEASE':'0'}):
                with self.assertRaisesRegex(ValueError,'authentic ten-original'):
                    stage_eleven(
                        ten_dir=ten,original_source=source,native=native,
                        source_build_report=build_report,
                        target='linux-x64',output=Path(td)/'eleven',
                        evidence=Path(td)/'report.json',
                        inspect_source=self.verified_source,
                        inspect_native=self.verified_native,
                    )
            self.assertFalse((Path(td)/'eleven').exists())

    def test_forged_compiler_report_does_not_convert_unknown_native_to_original(self):
        with TemporaryDirectory() as td:
            ten,source,native,build_report=self.fixture(td)
            record=json.loads(build_report.read_text())
            record['native_sha256']='0'*64
            build_report.write_text(json.dumps(record))
            with patch.dict(os.environ,{
                'AP_V30_GPL_TRIAL':'1','AP_V30_TEST_CORES':'1',
                'AP_RELEASE_BUILD':'0','AP_V30_APPROVED_RELEASE':'0'}):
                with self.assertRaisesRegex(ValueError,'independently emitted build report'):
                    stage_eleven(
                        ten_dir=ten,original_source=source,native=native,
                        source_build_report=build_report,
                        target='linux-x64',output=Path(td)/'eleven',
                        evidence=Path(td)/'report.json',
                        inspect_source=self.verified_source,
                        inspect_native=self.verified_native,
                    )
            self.assertFalse((Path(td)/'eleven').exists())

    def test_no_production_build_can_call_unapproved_stager(self):
        with TemporaryDirectory() as td:
            ten,source,native,build_report=self.fixture(td)
            with patch.dict(os.environ,{
                'AP_V30_GPL_TRIAL':'1','AP_V30_TEST_CORES':'1',
                'AP_RELEASE_BUILD':'1','AP_V30_APPROVED_RELEASE':'1'}):
                with self.assertRaisesRegex(ValueError,'Unapproved research only'):
                    stage_eleven(
                        ten_dir=ten,original_source=source,native=native,
                        source_build_report=build_report,
                        target='linux-x64',output=Path(td)/'eleven',
                        evidence=Path(td)/'report.json',
                        inspect_source=self.verified_source,
                        inspect_native=self.verified_native,
                    )
            self.assertFalse((Path(td)/'eleven').exists())


if __name__=='__main__':
    unittest.main()
