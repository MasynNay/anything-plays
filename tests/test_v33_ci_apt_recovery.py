"""GitHub runner apt recovery uses only signed Ubuntu 24.04 sources."""
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tools" / "ci_use_canonical_ubuntu_mirror.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "v33-private-candidate-installers.yml"


class UbuntuPackageMirrorRecoveryTests(unittest.TestCase):
    def test_source_manifest_requires_canonical_ubuntu_signatures(self):
        result = subprocess.run(
            ["bash", str(HELPER), "--print-recovery-sources"],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=5,
        )
        manifest = result.stdout
        self.assertEqual(manifest.count("Types: deb"), 2)
        self.assertIn("URIs: https://archive.ubuntu.com/ubuntu/", manifest)
        self.assertIn("URIs: https://security.ubuntu.com/ubuntu/", manifest)
        self.assertIn("Suites: noble noble-updates noble-backports", manifest)
        self.assertIn("Suites: noble-security", manifest)
        self.assertEqual(
            manifest.count(
                "Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg"
            ), 2,
        )
        self.assertNotIn("trusted=yes", manifest.lower())
        self.assertNotIn("AllowInsecureRepositories", manifest)
        self.assertNotIn("http://", manifest)

    def test_recovery_refuses_non_ci_host_and_unknown_commands(self):
        env = dict(os.environ)
        env["GITHUB_ACTIONS"] = "false"
        env["RUNNER_OS"] = "Linux"
        response = subprocess.run(
            ["bash", str(HELPER), "--repair-missing-packages"],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(response.returncode, 2)
        self.assertIn("restricted", response.stderr.lower())
        unknown = subprocess.run(
            ["bash", str(HELPER), "--disable-gpg-checks"],
            cwd=ROOT, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(unknown.returncode, 2)

    def test_unreleased_installer_checks_apt_metadata_after_update(self):
        flow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            'sudo env GITHUB_ACTIONS="$GITHUB_ACTIONS" '
            'RUNNER_OS="$RUNNER_OS" bash '
            'tools/ci_use_canonical_ubuntu_mirror.sh '
            '--repair-missing-packages', flow,
        )
        self.assertIn("sudo apt-get -o Acquire::Retries=2 update", flow)
        self.assertIn("tools/ci_use_canonical_ubuntu_mirror.sh", flow)
        self.assertIn("tests/test_v33_ci_apt_recovery.py", flow)
        self.assertIn('AP_RELEASE_BUILD: "0"', flow)
        self.assertIn("persist-credentials: false", flow)


if __name__ == "__main__":
    unittest.main()
