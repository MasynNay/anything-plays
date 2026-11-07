"""Portable GameCube OpenGL contracts without a display or commercial game."""
import ctypes as C
import threading
from unittest import TestCase
from unittest.mock import Mock, patch
from anything_plays.libretro_gpu_portable import (
    PortableGLFrameHost, choose_gamecube_gpu_host,
)
from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, HardwareRenderCallback,
)


class PortableGameCubeHostTests(TestCase):
    def test_selects_proven_egl_for_linux(self):
        with patch("anything_plays.libretro_gpu_portable.sys.platform", "linux"):
            self.assertIs(choose_gamecube_gpu_host(), EGLFrameHost)

    def test_selects_portable_for_windows_and_macos(self):
        for system in ("win32", "darwin"):
            with patch("anything_plays.libretro_gpu_portable.sys.platform",
                       system):
                self.assertIs(choose_gamecube_gpu_host(), PortableGLFrameHost)

    def test_unsupported_platform_fails_closed(self):
        with patch("anything_plays.libretro_gpu_portable.sys.platform", "other"):
            with self.assertRaises(RuntimeError):
                choose_gamecube_gpu_host()

    def test_macos_open_gl_41_rejects_45_dolphin_request(self):
        host = PortableGLFrameHost.__new__(PortableGLFrameHost)
        host.owner = threading.get_ident()
        host.opengl_version = "4.1 INTEL-17"
        req = HardwareRenderCallback()
        req.context_type = 3
        req.version_major = 4
        req.version_minor = 5
        req.context_reset = 123
        self.assertFalse(host.accept_core_render(C.addressof(req)))

    def test_no_context_procs_return_none_without_native_crash(self):
        host = PortableGLFrameHost.__new__(PortableGLFrameHost)
        host.context = None
        self.assertIsNone(host.get_proc_address(b"glGetString"))
        host.context = Mock()
        host.context.load.return_value = 123
        self.assertEqual(host.get_proc_address(b"glClear"), 123)
        host.context.load.side_effect = ValueError("missing")
        self.assertIsNone(host.get_proc_address(b"missing"))
