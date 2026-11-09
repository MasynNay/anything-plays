"""Original 6507/TIA cartridge contract; no external game or firmware."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.atari_homebrew_fixture import (
    ROM_BYTES, build_atari_2600_probe_rom, write_atari_probe
)


class AtariVideoAudioProbeTests(unittest.TestCase):
    def test_pinned_4k_rom_has_valid_6507_reset_vector(self):
        data = build_atari_2600_probe_rom()
        self.assertEqual(len(data), ROM_BYTES)
        self.assertEqual(data[:2], bytes((0x78, 0xD8)))
        self.assertEqual(data[-4:], bytes((0, 0xF0, 0, 0xF0)))
        self.assertEqual(data, build_atari_2600_probe_rom())

    def test_original_content_written_to_temp_path(self):
        with TemporaryDirectory() as root:
            target = Path(root) / "test.a26"
            meta = write_atari_probe(target)
            self.assertEqual(target.read_bytes(), build_atari_2600_probe_rom())
            self.assertEqual(meta["bytes"], 4096)


if __name__ == "__main__":
    unittest.main()
