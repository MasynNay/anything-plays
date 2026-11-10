"""Regression tests for bounded extraction of preserved native core ZIPs."""
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import create_v30_candidate_lock as lock


def archive(payload: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("mgba_libretro.so", payload)
    return out.getvalue()


class NativePayloadBoundsTests(unittest.TestCase):
    def test_normal_payload(self):
        with patch.object(lock, "MAX_NATIVE_PAYLOAD_BYTES", 32):
            self.assertEqual(lock.read_native_payload(archive(b"native"), "mgba_libretro.so", "linux-x64", "mgba"), b"native")

    def test_compressed_bomb_rejected_before_extraction(self):
        with patch.object(lock, "MAX_NATIVE_PAYLOAD_BYTES", 32):
            with self.assertRaisesRegex(ValueError, "oversized native core"):
                lock.read_native_payload(archive(b"A" * 10000), "mgba_libretro.so", "linux-x64", "mgba")

    def test_payload_at_limit_is_accepted(self):
        with patch.object(lock, "MAX_NATIVE_PAYLOAD_BYTES", 32):
            self.assertEqual(len(lock.read_native_payload(archive(b"A" * 32), "mgba_libretro.so", "linux-x64", "mgba")), 32)


if __name__ == "__main__":
    unittest.main()
