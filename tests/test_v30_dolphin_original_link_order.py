"""Prove the exact CMake-only Dolphin Libretro static linker order repair.

Pinned upstream has GNU ld dependency-order defect: GLContextLR.cpp consumes
Common::DynamicLibrary after libcommon.a was visited. This tiny real native
linker fixture first reproduces that failure, then verifies the deferred
CMake build-only amendment fixes it WITHOUT editing upstream source files.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tools/v30_dolphin_original_link_order.cmake"


@unittest.skipUnless(sys.platform.startswith("linux")
                     and shutil.which("cmake") and shutil.which("ninja"),
                     "Source-preserving GNU linker fixture needs Linux CMake/Ninja")
class DolphinOriginalCMakeLinkOrderTests(unittest.TestCase):
    def test_real_static_undefined_symbol_fixed_without_editing_sources(self):
        self.assertTrue(FIX.is_file())
        with TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"CMakeLists.txt").write_text(r"""
cmake_minimum_required(VERSION 3.25)
project(source_order_repro CXX)
file(WRITE "${CMAKE_BINARY_DIR}/common.cpp" "int helper(){return 42;}\n")
file(WRITE "${CMAKE_BINARY_DIR}/video.cpp" "extern int helper(); int video(){return helper();}\n")
file(WRITE "${CMAKE_BINARY_DIR}/main.cpp" "extern int video(); extern \"C\" int value(){return video();}\n")
add_library(common STATIC "${CMAKE_BINARY_DIR}/common.cpp")
add_library(dolphin_libretro_videocontexts STATIC "${CMAKE_BINARY_DIR}/video.cpp")
add_library(dolphin_libretro SHARED "${CMAKE_BINARY_DIR}/main.cpp")
target_link_options(dolphin_libretro PRIVATE "-Wl,--no-undefined")
target_link_libraries(dolphin_libretro PRIVATE
  common dolphin_libretro_videocontexts)
""", encoding="utf-8")
            for label,fix,expect_pass in (
                ("broken_without_fix",False,False),
                ("source_preserved_link_fix",True,True),
            ):
                target=root/label
                args=["cmake","-S",str(root),"-B",str(target),"-G","Ninja"]
                if fix:
                    args.append(f"-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={FIX}")
                config=subprocess.run(args,capture_output=True,text=True,timeout=35)
                self.assertEqual(config.returncode,0,config.stderr)
                built=subprocess.run(["cmake","--build",str(target)],
                                     capture_output=True,text=True,timeout=35)
                self.assertEqual(built.returncode == 0,expect_pass,
                                 built.stdout[-2500:]+built.stderr[-2500:])
                if fix:
                    self.assertIn("Original Dolphin source preserved",
                                  config.stdout)
                    self.assertTrue((target/"libdolphin_libretro.so").is_file())
                    link_command = (target/"build.ninja").read_text("utf-8")
                    self.assertIn("--start-group", link_command)
                    self.assertIn("--end-group", link_command)
                    # A start marker in LINK_OPTIONS and an end marker before
                    # transitive common.a is NOT sufficient (real CI failure).
                    # Require BOTH original source archives INSIDE THE SAME
                    # late CMake RESCAN group, in their exact cyclic order.
                    import re
                    self.assertRegex(
                        link_command,
                        r"-Wl,--start-group\s+libcommon\.a\s+"
                        r"libdolphin_libretro_videocontexts\.a\s+-Wl,--end-group",
                    )
                else:
                    self.assertIn("undefined reference",built.stdout+built.stderr)


    def test_missing_original_archive_target_fails_closed(self):
        """Never silently produce a candidate when the pinned source target layout changes."""
        self.assertTrue(FIX.is_file())
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "CMakeLists.txt").write_text(r"""
cmake_minimum_required(VERSION 3.25)
project(missing_original_dolphin_target CXX)
file(WRITE "${CMAKE_BINARY_DIR}/stub.cpp" "extern \"C\" int stub(){return 1;}\\n")
add_library(common STATIC "${CMAKE_BINARY_DIR}/stub.cpp")
add_library(dolphin_libretro SHARED "${CMAKE_BINARY_DIR}/stub.cpp")
# Deliberately omit dolphin_libretro_videocontexts.
""", encoding="utf-8")
            result = subprocess.run(
                ["cmake", "-S", str(root), "-B", str(root / "build"),
                 "-G", "Ninja", f"-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={FIX}"],
                capture_output=True, text=True, timeout=35,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("Original Dolphin source-linked native targets absent",
                          result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
