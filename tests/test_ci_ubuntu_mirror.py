"""Regression tests for signed Ubuntu archive selection in CI."""
import unittest
from tools.ci_use_official_ubuntu_mirror import rewrite_sources


class UbuntuMirrorTests(unittest.TestCase):
    def test_deb822_preserves_signed_by_and_suites(self):
        source = ("Types: deb\\nURIs: http://azure.archive.ubuntu.com/ubuntu\\n"
                  "Suites: noble noble-updates\\nComponents: main universe\\n"
                  "Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\\n")
        actual = rewrite_sources(source)
        self.assertIn("URIs: http://archive.ubuntu.com/ubuntu", actual)
        self.assertIn("Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg", actual)
        self.assertIn("Suites: noble noble-updates", actual)

    def test_security_and_other_hosts_unchanged(self):
        source = "http://security.ubuntu.com/ubuntu http://example.org/repo"
        self.assertEqual(rewrite_sources(source), source)

    def test_legacy_source_entry(self):
        self.assertEqual(
            rewrite_sources("deb http://azure.archive.ubuntu.com/ubuntu noble main"),
            "deb http://archive.ubuntu.com/ubuntu noble main",
        )

    def test_idempotent(self):
        source = "URIs: http://azure.archive.ubuntu.com/ubuntu"
        self.assertEqual(rewrite_sources(rewrite_sources(source)), rewrite_sources(source))


if __name__ == "__main__":
    unittest.main()
