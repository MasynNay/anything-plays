"""Exercise real macOS packaging mount-retry shell logic without a disk image.

This isolates only the mount/retry block and replaces hdiutil and sleep with
controlled shell functions. A false successful attach must never reach
verify_bundle. Source-CI runs on Linux; native macOS CI still tests real DMGs.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] /
          "packaging" / "build_macos_dmg.sh")


class MacOSDMGAttachRetryTests(unittest.TestCase):
    @staticmethod
    def block():
        source = SCRIPT.read_text("utf-8")
        start = source.index("MOUNT_OK=0\n")
        end = source.index('"$PYTHON" verify_bundle.py --check-native macos "$MOUNT_DIR/${BUNDLE_FILE}"', start)
        block = source[start:end]
        assert "hdiutil attach -readonly -nobrowse" in block
        assert '[[ "$MOUNT_OK" == "1" ]] || {' in block
        return block

    def run_fake(self, success_on_attempt):
        harness = (
            "set -euo pipefail\n"
            "MOUNT_DIR=/synthetic-dmg-mount\n"
            "DMG=/synthetic-3.0.dmg\n"
            f"SUCCESS_AT={success_on_attempt}\n"
            "ATTACH_CALLS=0\nDETACH_CALLS=0\n"
            "hdiutil() {\n"
            "  if [[ \"$1\" == attach ]]; then\n"
            "    ATTACH_CALLS=$((ATTACH_CALLS + 1))\n"
            "    [[ $ATTACH_CALLS -ge $SUCCESS_AT ]]\n"
            "  else\n"
            "    DETACH_CALLS=$((DETACH_CALLS + 1))\n"
            "  fi\n"
            "}\n"
            "sleep() { :; }\n"
            + self.block() +
            'printf "VERIFICATION_ALLOWED=%s ATTACH_CALLS=%s\\n" "$MOUNT_OK" "$ATTACH_CALLS"\n'
        )
        return subprocess.run(["bash", "-c", harness], capture_output=True, text=True)

    def test_healthy_and_transient_busy_attach_both_allow_real_check(self):
        for attempt in (1, 2, 4, 6):
            with self.subTest(success_at=attempt):
                proc = self.run_fake(attempt)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn(f"VERIFICATION_ALLOWED=1 ATTACH_CALLS={attempt}", proc.stdout)
                self.assertEqual(proc.stderr.count("mount refused"), attempt - 1)

    def test_permanent_attach_failure_does_not_pass_verification(self):
        proc = self.run_fake(7)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("VERIFICATION_ALLOWED=1", proc.stdout)
        self.assertEqual(proc.stderr.count("mount refused"), 6)
        self.assertIn("DMG validation BLOCKED", proc.stderr)

    def test_original_verifier_and_cleanup_are_still_mandatory(self):
        source = SCRIPT.read_text("utf-8")
        mount = source.index("MOUNT_OK=0\n")
        guard = source.index('[[ "$MOUNT_OK" == "1" ]] || {', mount)
        verify = source.index('"$PYTHON" verify_bundle.py --check-native macos "$MOUNT_DIR/${BUNDLE_FILE}"', guard)
        detach = source.index('hdiutil detach "$MOUNT_DIR"\n', verify)
        self.assertTrue(mount < guard < verify < detach)
        self.assertIn("trap 'hdiutil detach", source)
        self.assertIn("trap - EXIT", source)


if __name__ == "__main__":
    unittest.main()
