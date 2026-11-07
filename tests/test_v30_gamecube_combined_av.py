"""The original GX 3D homebrew must exercise native DSP in the same game."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GameCubeCombinedAVContractTests(unittest.TestCase):
    def test_original_gx_fixture_produces_native_stereo_audio(self):
        source = (ROOT / "tools/gamecube-3d-homebrew/source/main.c").read_text("utf-8")
        makefile = (ROOT / "tools/gamecube-3d-homebrew/Makefile").read_text("utf-8")
        self.assertIn("#include <asndlib.h>", source)
        self.assertIn("ASND_Init();", source)
        self.assertIn("ASND_SetInfiniteVoice(", source)
        self.assertIn("ASND_Pause(0);", source)
        self.assertIn("DCFlushRange(audio_tone", source)
        self.assertLess(source.index("init_video_and_gx();"),
                        source.index("init_audio();"))
        self.assertIn("-lasnd", makefile)
        self.assertIn("GX_Begin(GX_QUADS", source)

    def test_linux_and_both_macs_require_3d_and_audio_together(self):
        workflow = (ROOT / ".github/workflows/v30-lab.yml").read_text("utf-8")
        linux = workflow.split("  gamecube-original-gx3d-gpu-playback:", 1)[1]
        mac = linux.split("  gamecube-original-gx3d-macos:", 1)[1]
        linux = linux.split("  gamecube-original-gx3d-macos:", 1)[0]
        for name, job in (("Linux", linux), ("macOS", mac)):
            with self.subTest(platform=name):
                self.assertIn("--require-animated --require-audio", job)
                self.assertIn("probe_gamecube_app.py", job)
                self.assertIn("anythingplays-gc-gx-gamecube.dol", job)
        self.assertIn("macos-arm64", mac)
        self.assertIn("macos-x64", mac)


if __name__ == "__main__":
    unittest.main()
