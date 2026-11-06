"""Exercise the native Libretro lifecycle with a tiny synthetic test core.

The fixture implements only the ABI used by Anything Plays. It is compiled
on demand on Linux and contains no game code, proprietary ROM, or real core.
Other platforms skip this test but run the same pure-Python boundary tests.
"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from anything_plays.gba_emulator import Emulator


SYNTHETIC_CORE = r'''
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef bool (*environment_fn)(unsigned, void *);
typedef void (*video_fn)(const void *, unsigned, unsigned, size_t);
typedef void (*audio_fn)(int16_t, int16_t);
typedef size_t (*batch_fn)(const int16_t *, size_t);
typedef void (*poll_fn)(void);
typedef int16_t (*input_fn)(unsigned, unsigned, unsigned, unsigned);

struct game_info { const char *path; const void *data; size_t size; const char *meta; };
struct system_info {
    const char *library_name, *library_version, *valid_extensions;
    bool need_fullpath, block_extract;
};
struct geometry {
    unsigned base_width, base_height, max_width, max_height;
    float aspect_ratio;
};
struct timing { double fps, sample_rate; };
struct av_info { struct geometry geometry; struct timing timing; };

static environment_fn environment;
static video_fn video;
static audio_fn audio;
static batch_fn audio_batch;
static poll_fn input_poll;
static input_fn input_state;
static uint8_t save_ram[4];

void retro_set_environment(environment_fn callback) { environment = callback; }
void retro_set_video_refresh(video_fn callback) { video = callback; }
void retro_set_audio_sample(audio_fn callback) { audio = callback; }
void retro_set_audio_sample_batch(batch_fn callback) { audio_batch = callback; }
void retro_set_input_poll(poll_fn callback) { input_poll = callback; }
void retro_set_input_state(input_fn callback) { input_state = callback; }
void retro_init(void) { int pixel_format = 2; environment(10, &pixel_format); }
void retro_deinit(void) {}
void retro_get_system_info(struct system_info *info) {
    info->library_name = "SyntheticCore";
    info->library_version = "test";
    info->valid_extensions = "gba|gbc";
    info->need_fullpath = false;
    info->block_extract = false;
}
void retro_get_system_av_info(struct av_info *info) {
    info->geometry = (struct geometry){2, 2, 2, 2, 1.0f};
    info->timing = (struct timing){60.0, 0.0};
}
bool retro_load_game(const struct game_info *game) {
    return game != NULL && game->data != NULL && game->size > 0;
}
void retro_unload_game(void) {}
void retro_run(void) {
    static const uint16_t pixels[] = {0xF800, 0x07E0, 0x001F, 0xFFFF};
    input_poll();
    if (input_state(0, 1, 0, 8)) save_ram[0] = 42;
    video(pixels, 2, 2, 4);
}
void *retro_get_memory_data(unsigned type) { return type == 0 ? save_ram : NULL; }
size_t retro_get_memory_size(unsigned type) { return type == 0 ? sizeof(save_ram) : 0; }
'''


@unittest.skipUnless(sys.platform.startswith("linux") and shutil.which("gcc"),
                     "A Linux C compiler is required for this optional ABI test")
class NativeIntegrationTests(unittest.TestCase):
    def test_core_callbacks_manual_input_and_sram_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "synthetic.c"
            core = root / "synthetic.so"
            rom = root / "test.gba"
            source.write_text(SYNTHETIC_CORE, encoding="utf-8")
            rom.write_bytes(b"test-only-data")
            subprocess.run(
                ["gcc", "-shared", "-fPIC", "-O2", str(source), "-o", str(core)],
                check=True, capture_output=True,
            )
            emulator = Emulator()
            emulator.core_path = str(core)
            emulator.start(rom)
            try:
                deadline = time.monotonic() + 3
                while not emulator.running and time.monotonic() < deadline:
                    if emulator.error:
                        self.fail(emulator.error)
                    time.sleep(.02)
                self.assertTrue(emulator.running, emulator.error)
                emulator.set_manual("A", True)
                time.sleep(.15)
                with emulator.lock:
                    frame = emulator.frame.copy() if emulator.frame is not None else None
                self.assertIsNotNone(frame)
                self.assertEqual(frame.shape, (2, 2, 3))
                self.assertEqual(frame[0, 0].tolist(), [255, 0, 0])
            finally:
                emulator.stop()
            self.assertIsNone(emulator.error)
            self.assertEqual(rom.with_suffix(".sav").read_bytes()[0], 42)


if __name__ == "__main__":
    unittest.main()
