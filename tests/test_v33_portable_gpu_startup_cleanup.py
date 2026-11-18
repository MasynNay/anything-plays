"""3.3 portable Windows/macOS context startup must preserve primary errors.

All exercises use fake glcontext objects with no GPU, real driver,
commercial ROM, audio output or window.
"""
import unittest
from unittest.mock import patch

from anything_plays.libretro_gpu_portable import PortableGLFrameHost


class FakeContext:
    def __init__(self, *, fail_on_exit=False, fail_on_enter=False):
        self.enter_calls = 0
        self.exit_calls = 0
        self.fail_on_exit = fail_on_exit
        self.fail_on_enter = fail_on_enter

    def __enter__(self):
        self.enter_calls += 1
        if self.fail_on_enter:
            raise OSError("PRIMARY GPU context entry private /Users/a/ROMs")
        return self

    def __exit__(self, *_):
        self.exit_calls += 1
        if self.fail_on_exit:
            raise OSError("SECONDARY GPU context close private /dev/dri")


class PortableGPUStartupCleanupTests(unittest.TestCase):
    def test_native_exit_failure_never_masks_failed_gpu_version_probe(self):
        for platform in ("darwin", "win32"):
            with self.subTest(platform=platform):
                context = FakeContext(fail_on_exit=True)
                with (
                    patch("anything_plays.libretro_gpu_portable.sys.platform",
                          platform),
                    patch.object(PortableGLFrameHost, "_gl",
                                 side_effect=RuntimeError(
                                     "PRIMARY no GL version entry"
                                 )),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "PRIMARY no GL version entry"
                    ):
                        PortableGLFrameHost(backend=lambda **kwargs: context)
                self.assertEqual(context.enter_calls, 1)
                self.assertEqual(context.exit_calls, 1)

    def test_gl_deletion_oserror_does_not_skip_other_resource_deletion(self):
        context = FakeContext()
        calls = []

        def fail_fbo(host):
            host.fbo, host.color_tex, host.depth_stencil = 9, 10, 11
            raise RuntimeError("PRIMARY FBO allocation failed")

        def gl(_host, name, _restype, _args):
            if name == "glGetString":
                return lambda field: b"4.1" if field == 0x1F02 else b"test"
            def invoke(*args):
                calls.append(name)
                if name == "glDeleteFramebuffers":
                    raise OSError("SECONDARY first native GL delete failed")
            return invoke

        with (
            patch("anything_plays.libretro_gpu_portable.sys.platform",
                  "darwin"),
            patch.object(PortableGLFrameHost, "_gl", gl),
            patch.object(PortableGLFrameHost, "_init_framebuffer", fail_fbo),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "PRIMARY FBO allocation failed"
            ):
                PortableGLFrameHost(backend=lambda **kwargs: context)
        self.assertEqual(
            calls,
            ["glDeleteFramebuffers", "glDeleteTextures",
             "glDeleteRenderbuffers"],
        )
        self.assertEqual(context.exit_calls, 1)

    def test_entry_failure_does_not_call_exit_of_unentered_context(self):
        context = FakeContext(fail_on_enter=True)
        with patch("anything_plays.libretro_gpu_portable.sys.platform", "darwin"):
            with self.assertRaisesRegex(
                OSError, "PRIMARY GPU context entry"
            ):
                PortableGLFrameHost(backend=lambda **kwargs: context)
        self.assertEqual(context.enter_calls, 1)
        self.assertEqual(context.exit_calls, 0)


if __name__ == "__main__":
    unittest.main()
