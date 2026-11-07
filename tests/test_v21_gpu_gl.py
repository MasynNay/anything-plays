"""EGL/GPU bridge ABI tests; no display, firmware, or game is needed."""
import ctypes as C
import sys
import threading
import unittest
from unittest.mock import patch

from tools.libretro_gpu_egl import (
    EGLFrameHost, HardwareRenderCallback, bounded_dimensions,
)


class OffscreenGpuFrontendTests(unittest.TestCase):
    def test_libretro_hw_render_callback_layout_64_bit(self):
        self.assertEqual(C.sizeof(C.c_void_p), 8)
        self.assertEqual(C.sizeof(HardwareRenderCallback), 64)
        self.assertEqual(HardwareRenderCallback.context_type.offset, 0)
        self.assertEqual(HardwareRenderCallback.context_reset.offset, 8)
        self.assertEqual(HardwareRenderCallback.get_current_framebuffer.offset, 16)
        self.assertEqual(HardwareRenderCallback.get_proc_address.offset, 24)
        self.assertEqual(HardwareRenderCallback.context_destroy.offset, 48)

    def test_bad_dimensions_never_reach_driver_memory(self):
        for w, h in ((0, 480), (640, 0), (641, 480),
                     (640, 577), (-1, 10), (4096, 4096)):
            with self.subTest(w=w, h=h):
                with self.assertRaises(ValueError):
                    bounded_dimensions(w, h)
        self.assertEqual(bounded_dimensions(640, 576), (640, 576))
        self.assertEqual(bounded_dimensions(1, 1), (1, 1))

    def test_gpu_context_must_be_thread_owned(self):
        context = EGLFrameHost.__new__(EGLFrameHost)
        context.owner = threading.get_ident() + 1
        with self.assertRaisesRegex(RuntimeError, "different thread"):
            context._check_thread()

    def test_requires_real_render_context_and_explicit_open_gl_core(self):
        context = EGLFrameHost.__new__(EGLFrameHost)
        context.owner = threading.get_ident()
        context.fbo = 17
        context.core_reset = None
        context.core_destroy = None
        # Reject an invalid/null GL callback, never pretend the GPU exists.
        self.assertFalse(context.accept_core_render(None))
        req = HardwareRenderCallback()
        req.context_type = 3
        req.version_major = 3
        req.version_minor = 3
        self.assertFalse(context.accept_core_render(C.addressof(req)))
        # A core's callback pointer may be retained only after a real context.
        req.context_reset = 1234  # Never invoke; ABI validation only.
        req.context_type = 7  # D3D11, unsupported by this Linux backend.
        self.assertFalse(context.accept_core_render(C.addressof(req)))
        req.context_type = 3
        req.version_major, req.version_minor = 9, 0
        self.assertFalse(context.accept_core_render(C.addressof(req)))

    def test_nonlinux_fails_closed_without_loading_native_libraries(self):
        with patch("tools.libretro_gpu_egl.sys.platform", "darwin"):
            with self.assertRaisesRegex(RuntimeError, "Linux-only"):
                EGLFrameHost()

    def test_single_core_override_changes_only_diagnostic_session(self):
        from tools.probe_gamecube_gl import GLCoreSession
        from unittest.mock import patch
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from anything_plays.gba_emulator import Emulator

        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"placeholder")
            sysdir = root / "dolphin-emu" / "Sys"
            sysdir.mkdir(parents=True)
            (sysdir / "codehandler.bin").write_bytes(b"placeholder")
            rom = root / "homebrew.dol"
            rom.write_bytes(b"placeholder")
            with patch("pathlib.Path.home", return_value=root):
                session = GLCoreSession(
                    Emulator(), rom, core, cpu_core=None, single_core=True
                )
                self.assertEqual(
                    session._software_options.values[b"dolphin_main_cpu_thread"],
                    b"disabled"
                )
                self.assertEqual(
                    session._software_options.values[b"dolphin_renderer"],
                    b"Hardware"
                )
                standard = GLCoreSession(
                    Emulator(), rom, core, cpu_core=None, single_core=False
                )
                self.assertNotIn(
                    b"dolphin_main_cpu_thread", standard._software_options.values
                )

    def test_gpu_experiment_explicitly_selects_x86_jit_not_safe_software_fallback(self):
        from tools.probe_gamecube_gl import GLCoreSession
        from anything_plays.gba_emulator import Emulator
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"placeholder")
            sysdir = root / "dolphin-emu" / "Sys"
            sysdir.mkdir(parents=True)
            (sysdir / "codehandler.bin").write_bytes(b"placeholder")
            rom = root / "owned.dol"
            rom.write_bytes(b"placeholder")
            with patch("pathlib.Path.home", return_value=root):
                jit = GLCoreSession(Emulator(), rom, core, cpu_core=None)
                cached = GLCoreSession(Emulator(), rom, core, cpu_core="5")
            self.assertEqual(jit._software_options.values[b"dolphin_cpu_core"], b"1")
            self.assertEqual(cached._software_options.values[b"dolphin_cpu_core"], b"5")

    def test_original_homebrew_gpu_probe_forwards_input_stimulus(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from subprocess import CompletedProcess
        from tools.probe_gamecube_gl import _parent
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"placeholder")
            report = root / "result.json"
            def inspect(args, **kwargs):
                self.assertIn("--exercise-controls", args)
                return CompletedProcess(args, -11, stdout="native failure")
            def fixture(path):
                path.write_bytes(b"synthetic")
                return path
            with patch("tools.probe_gamecube_gl.verified_homebrew",
                       side_effect=fixture), patch(
                           "tools.probe_gamecube_gl.subprocess.run",
                           side_effect=inspect):
                self.assertEqual(
                    _parent(core, 2, report, cpu_core="5", exercise_controls=True),
                    1
                )
            saved = json.loads(report.read_text())
            self.assertTrue(saved["controller_stimulus"])
            self.assertFalse(saved["passed"])

    def test_audio_and_ram_diagnostic_detects_actual_emulation_progress(self):
        import ctypes as C
        from tools.probe_gamecube_gl import RamProgress, SilentAudio

        audio = SilentAudio()
        audio.start(48000)
        audio.sample(10, 20)
        self.assertEqual(audio.batch(None, 33), 33)
        self.assertEqual(audio.sample_frames, 34)
        self.assertEqual(audio.batch_calls, 1)
        self.assertEqual(audio.sample_rate, 48000)

        memory = C.create_string_buffer(4096)
        address = C.addressof(memory)

        class Native:
            def memory_data(self, area):
                self.assertEqual(area, 2)
                return address

            def memory_size(self, area):
                return 4096

        native = Native()
        native.assertEqual = self.assertEqual
        sampler = RamProgress()
        sampler.sample(native)
        self.assertEqual(sampler.samples, 1)
        self.assertFalse(sampler.changed)
        memory[100] = b"X"
        sampler.sample(native)
        self.assertEqual(sampler.samples, 2)
        self.assertTrue(sampler.changed)

    def test_gl_probe_disables_duplicate_frame_suppression_and_counts_nulls(self):
        from tools.probe_gamecube_gl import GLCoreSession
        from anything_plays.gba_emulator import Emulator
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"placeholder")
            sysdir = root / "dolphin-emu" / "Sys"
            sysdir.mkdir(parents=True)
            (sysdir / "codehandler.bin").write_bytes(b"placeholder")
            rom = root / "homebrew.dol"
            rom.write_bytes(b"placeholder")
            with patch("pathlib.Path.home", return_value=root):
                session = GLCoreSession(Emulator(), rom, core, cpu_core=None)
                self.assertEqual(
                    session._software_options.values[b"dolphin_skip_dupe_frames"],
                    b"disabled"
                )
                session.video(None, 640, 528, 0)
                self.assertEqual(session.null_video_callbacks, 1)
                self.assertEqual(session.raw_video_callbacks, 1)

    def test_production_gamecube_session_owns_gpu_and_reuses_native_audio_sink(self):
        from anything_plays.gamecube_gpu import GameCubeHardwareSession
        from anything_plays.gba_emulator import Emulator
        from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock, patch
        import numpy as np

        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"placeholder")
            sysdir = root / "dolphin-emu" / "Sys"
            sysdir.mkdir(parents=True)
            (sysdir / "codehandler.bin").write_bytes(b"placeholder")
            rom = root / "owned.dol"
            rom.write_bytes(b"placeholder")
            fake_host = Mock()
            fake_host.core_reset = 123
            fake_host.read_frame.return_value = np.ones((2, 2, 3), dtype=np.uint8)
            emu = Emulator()
            with patch("pathlib.Path.home", return_value=root):
                session = GameCubeHardwareSession(
                    emu, rom, core, host_factory=Mock()
                )
            self.assertEqual(
                session._software_options.values[b"dolphin_renderer"], b"Hardware"
            )
            self.assertEqual(
                session._software_options.values[b"dolphin_cpu_core"], b"1"
            )
            from anything_plays.libretro_audio import AudioSink
            self.assertIsInstance(session.audio, AudioSink)
            session.host = fake_host
            self.assertTrue(session.environment(14, 333))
            fake_host.accept_core_render.assert_called_once_with(333)
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 2, 2, 0)
            self.assertEqual(session.hardware_frames, 1)
            self.assertEqual(emu.frame_serial, 1)
            self.assertEqual(emu.frame.shape, (2, 2, 3))
            session.video(None, 2, 2, 0)
            self.assertEqual(session.null_video_callbacks, 1)

    def test_gpu_failure_stops_emulation_instead_of_hiding_blank_frames(self):
        from anything_plays.gamecube_gpu import GameCubeHardwareSession
        from anything_plays.gba_emulator import Emulator
        from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock, patch
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"placeholder")
            folder_sys = root / "dolphin-emu" / "Sys"
            folder_sys.mkdir(parents=True)
            (folder_sys / "codehandler.bin").write_bytes(b"placeholder")
            rom = root / "owned.dol"
            rom.write_bytes(b"placeholder")
            with patch("pathlib.Path.home", return_value=root):
                emu = Emulator()
                session = GameCubeHardwareSession(emu, rom, core)
            session.host = Mock()
            session.host.read_frame.side_effect = RuntimeError("FBO unavailable")
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 640, 480, 0)
            self.assertTrue(emu.stop_event.is_set())
            self.assertIn("FBO unavailable", session.opengl_error)

    def test_hardware_core_session_never_uses_an_external_emulator(self):
        from tools.probe_gamecube_gl import GLCoreSession
        import inspect
        source = inspect.getsource(GLCoreSession)
        self.assertIn("CoreSession", source)
        self.assertIn("self.hardware.reset_core()", source)
        self.assertIn("self.hardware.read_frame", source)
        self.assertNotIn("RetroArch", source)
        self.assertNotIn("subprocess", source)


if __name__ == "__main__":
    unittest.main()
