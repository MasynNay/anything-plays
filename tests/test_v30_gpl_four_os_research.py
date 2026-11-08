"""All eight GPLv3 source-built native candidate jobs remain strictly unapproved."""
from __future__ import annotations

from pathlib import Path
import unittest

from tools.capture_v30_gpl_alternative_source_build import SOURCE, EXT


class FourPlatformGPLSourceContracts(unittest.TestCase):
    def test_complete_eight_native_build_matrix_and_source_pins(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/".github/workflows/v30-gpl-four-os-source-build.yml").read_text("utf-8")
        self.assertIn("pull_request:",text)
        for candidate,source in SOURCE.items():
            self.assertIn(source["repository"].removeprefix("https://github.com/"),text)
            self.assertIn(source["commit"],text)
            for target,suffix in EXT.items():
                self.assertIn("target: "+target+", candidate: "+candidate,text)
                self.assertIn("native: "+source["binary"]+suffix,text)
        self.assertEqual(len(EXT)*len(SOURCE),8)
        self.assertEqual(text.count("- {runner:"),8)
        self.assertIn("msys2/setup-msys2@v2",text)
        self.assertIn("macos-15-intel",text)
        self.assertIn("macos-15",text)
        self.assertIn("windows-2025",text)
        self.assertIn("ubuntu-24.04",text)

    def test_all_five_real_a_v_probes_are_required_and_no_runtime_substitution(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/".github/workflows/v30-gpl-four-os-source-build.yml").read_text("utf-8")
        self.assertIn("probe_snes_homebrew.py",text)
        self.assertIn("probe_v30_blastem_genesis_variant.py",text)
        self.assertIn("probe_sega8_homebrew.py",text)
        self.assertIn("mastersystem gamegear sg1000",text)
        self.assertIn("assert len(reports)==expect",text)
        self.assertIn("source_to_binary_independently_reproducible",text)
        self.assertIn("combined_gpl_2_and_gpl_3_license_reviewed",text)
        self.assertIn("public_binary_distribution_approved",text)
        self.assertIn("if: always()",text)
        self.assertIn("retention-days:",text)
        self.assertNotIn("continue-on-error: true",text)
        self.assertNotIn("gh release create",text)
        self.assertNotIn("APPROVED-3.0-DISTRIBUTION",text)
        self.assertNotIn("AP_V30_APPROVED_RELEASE: '1'",text)

    def test_cross_platform_build_compatibility_does_not_edit_pinned_upstream_tree(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/".github/workflows/v30-gpl-four-os-source-build.yml").read_text("utf-8")
        header=(root/"tools/bsnes_mingw_vasprintf_compat.h").read_text("utf-8")
        self.assertIn("mingw-w64-x86_64-python",workflow)
        self.assertIn("C:/msys64/mingw64/bin",workflow)
        self.assertIn("AP_V30_MINGW_CI_DLL_DIR",workflow)
        self.assertIn("tools/v30_windows_gpl_lab/sitecustomize.py",workflow)
        self.assertIn("PYTHONPATH=$GITHUB_WORKSPACE/tools/v30_windows_gpl_lab",workflow)
        bootstrap=(root/"tools/v30_windows_gpl_lab/sitecustomize.py").read_text("utf-8")
        self.assertIn('os.add_dll_directory(str(_folder))',bootstrap)
        self.assertIn('DLL_RESEARCH_HANDLES.append',bootstrap)
        self.assertIn('if os.name == "nt"',bootstrap)
        self.assertIn("AP_V30_MINGW_CI_DLL_DIR",bootstrap)
        self.assertNotIn("subprocess.Popen",bootstrap)
        self.assertIn('LDFLAGS="-fPIC -dynamiclib -Wl,-ld_classic"',workflow)
        self.assertIn('EXTRA_INCLUDES="-include $(pwd)/tools/bsnes_mingw_vasprintf_compat.h"',workflow)
        self.assertIn('EXTRA_INCLUDES="-mmacosx-version-min=10.15 -D_DARWIN_C_SOURCE"',workflow)
        self.assertIn("#if defined(_WIN32) && !defined(__cplusplus)",header)
        self.assertIn("#define vasprintf ap_v30_bsnes_mingw_vasprintf",header)
        self.assertIn("va_copy(render, original)",header)
        self.assertIn("va_end(render)",header)
        self.assertNotIn("git apply",workflow)
        self.assertNotIn("sed -i",workflow)
        self.assertNotIn("continue-on-error: true",workflow)
        self.assertNotIn("AP_V30_APPROVED_RELEASE",workflow)

    def test_all_four_original_sega_results_must_be_reconciled(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/".github/workflows/v30-gpl-four-os-source-build.yml").read_text("utf-8")
        for name in (
            "GENESIS_AV_UNAPPROVED.json",
            "mastersystem-AV_UNAPPROVED.json",
            "gamegear-AV_UNAPPROVED.json",
            "sg1000-AV_UNAPPROVED.json",
        ):
            self.assertIn(name,workflow)
        self.assertIn("all(p.is_file() for p in reports)",workflow)
        self.assertNotIn("where.glob('*_AV_UNAPPROVED.json')",workflow)

    def test_genesis_variant_must_be_platform_native_not_elf_on_windows(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/"tools/probe_v30_blastem_genesis_variant.py").read_text("utf-8")
        self.assertIn('".dll" if sys.platform == "win32"',text)
        self.assertIn('".dylib" if sys.platform == "darwin"',text)
        self.assertIn('else ".so"',text)
        self.assertIn("Expected ephemeral platform-native BlastEm core",text)
        self.assertIn("original_without_unconditional_tmss",text)


if __name__=="__main__":
    unittest.main()
