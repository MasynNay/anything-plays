"""Synthetic N64 control bridge tests (no games or network needed)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
import struct
import unittest

from anything_plays.external_emulators import command_for
from anything_plays.remote_retropad import (
    ANALOG, JOY, PACKET, N64RemoteController, desired_state,
    encode_message, write_retroarch_config,
)


class N64BridgeTests(unittest.TestCase):
    def test_packet_layout_matches_retroarch_remote_message_abi(self):
        self.assertEqual(PACKET.size, 20)
        self.assertEqual(
            struct.unpack("<iiiiH2x", encode_message(JOY, 0, 8, 1)),
            (0, 1, 0, 8, 1),
        )
        self.assertEqual(
            struct.unpack("<iiiiH2x", encode_message(ANALOG, 0, 1, -28000))[-1],
            (-28000 & 0xFFFF),
        )
        with self.assertRaises(ValueError):
            encode_message(JOY, 0, 1, 50000)

    def test_camera_axes_and_n64_c_buttons(self):
        state = desired_state(("Up", "Right", "C Up", "Z", "A"))
        self.assertEqual(state[(ANALOG, 0, 1)], -28000)
        self.assertEqual(state[(ANALOG, 0, 0)], 28000)
        self.assertEqual(state[(ANALOG, 1, 1)], -28000)
        self.assertEqual(state[(JOY, 0, 12)], 1)
        self.assertEqual(state[(JOY, 0, 8)], 1)
        neutral = desired_state(("Up", "Down", "C Left", "C Right"))
        self.assertFalse(neutral)

    def test_camera_press_latches_and_releases_without_os_keys(self):
        socket = Mock()
        instant = [10.0]
        bridge = N64RemoteController(sock=socket, clock=lambda: instant[0])
        bridge.press("A", frames=6)
        bridge.flush()
        packet, address = socket.sendto.call_args.args
        self.assertEqual(address, ("127.0.0.1", 55400))
        self.assertEqual(struct.unpack("<iiiiH2x", packet), (0, JOY, 0, 8, 1))
        instant[0] += 0.2
        bridge.flush()
        packet, _ = socket.sendto.call_args.args
        self.assertEqual(struct.unpack("<iiiiH2x", packet), (0, JOY, 0, 8, 0))
        bridge.close()

    def test_disarming_camera_preserves_manual_buttons(self):
        socket = Mock()
        bridge = N64RemoteController(sock=socket)
        bridge.press("A", 8)
        bridge.set_manual("B", True)
        bridge.flush()
        self.assertEqual(socket.sendto.call_count, 1)
        bridge.flush()  # Receiver accepts at most one event per frame.
        self.assertEqual(len(bridge._sent), 2)
        bridge.release_camera()
        bridge.flush()  # Release A before any pending presses.
        self.assertEqual(bridge._sent, {(JOY, 0, 0): 1})
        bridge.release_manual()
        bridge.flush()
        self.assertEqual(bridge._sent, {})
        bridge.close()

    def test_app_test_config_uses_appendconfig_not_user_preferences(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = write_retroarch_config(root / "alpha" / "n64.cfg")
            content = config.read_text(encoding="utf-8")
            self.assertIn('network_remote_enable = "true"\n', content)
            self.assertIn('network_remote_enable_user_p1 = "true"\n', content)
            self.assertIn('config_save_on_exit = "false"\n', content)
            rom = root / "game.n64"
            exe = root / "RetroArch"
            core = root / "mupen64plus_next_libretro.dylib"
            for path in (rom, exe, core):
                path.write_bytes(b"test fixture")
            args = command_for(
                "n64", rom, executable=exe, n64_core=core,
                network_config=config,
            )
            self.assertEqual(args[-1], str(rom))
            self.assertEqual(args[1:3], ["--appendconfig", str(config)])
            self.assertEqual(args[0], str(exe))


if __name__ == "__main__":
    unittest.main()
