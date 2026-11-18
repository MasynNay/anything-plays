"""3.3 private QA nightly core retry never loosens the release lock."""
import io
import os
import socket
import unittest
from unittest.mock import Mock, patch
from urllib import error as url_error

from fetch_mgba_core import _read_core_archive, BUILD_BOT, MAX_ARCHIVE_SIZE


URL = BUILD_BOT + "/apple/osx/x86_64/latest/mgba_libretro.dylib.zip"
NAME = "mgba_libretro.dylib"


def response(content):
    handle = io.BytesIO(content)
    return handle


class V33PrivateCoreFetchRetryTests(unittest.TestCase):
    def test_transient_dns_recovers_on_same_url_with_bounded_wait(self):
        data = b"original, unmodified downloaded ZIP input"
        dns = url_error.URLError(socket.gaierror(8, "no address"))
        with (
            patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "0",
                "AP_CORE_ARCHIVE_DIR": "",
                "AP_V33_CANDIDATE": "1",
                "AP_V30_MINIMAL_CORE_BUILD": "1",
            }),
            patch("fetch_mgba_core.request.urlopen",
                  side_effect=[dns, dns, response(data)]) as open_url,
            patch("fetch_mgba_core.time.sleep") as sleep,
        ):
            self.assertEqual(_read_core_archive(URL, NAME), data)
        self.assertEqual(open_url.call_count, 3)
        self.assertEqual(
            [call.args[0].full_url for call in open_url.call_args_list],
            [URL] * 3,
        )
        self.assertEqual([call.kwargs["timeout"] for call in
                          open_url.call_args_list], [45] * 3)
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list], [2, 4],
        )

    def test_repeated_dns_failure_is_bounded_and_never_returns_empty_zip(self):
        dns = url_error.URLError(socket.gaierror(8, "no address"))
        with (
            patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "0",
                "AP_CORE_ARCHIVE_DIR": "",
                "AP_V33_CANDIDATE": "1",
                "AP_V30_MINIMAL_CORE_BUILD": "1",
            }),
            patch("fetch_mgba_core.request.urlopen",
                  side_effect=dns) as open_url,
            patch("fetch_mgba_core.time.sleep") as sleep,
        ):
            with self.assertRaises(url_error.URLError):
                _read_core_archive(URL, NAME)
        self.assertEqual(open_url.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_no_retries_for_other_builds_or_non_buildbot_sources(self):
        for env, url in (
            ({"AP_V33_CANDIDATE": "0", "AP_V30_MINIMAL_CORE_BUILD": "1"},
             URL),
            ({"AP_V33_CANDIDATE": "1", "AP_V30_MINIMAL_CORE_BUILD": "0"},
             URL),
            ({"AP_V33_CANDIDATE": "1", "AP_V30_MINIMAL_CORE_BUILD": "1"},
             "https://example.invalid/unknown.zip"),
        ):
            with self.subTest(env=env, url=url):
                with (
                    patch.dict(os.environ, {
                        **env, "AP_RELEASE_BUILD": "0",
                        "AP_CORE_ARCHIVE_DIR": "",
                    }),
                    patch("fetch_mgba_core.request.urlopen",
                          side_effect=url_error.URLError(
                              socket.gaierror(8, "no address")
                          )) as open_url,
                    patch("fetch_mgba_core.time.sleep") as sleep,
                ):
                    with self.assertRaises(url_error.URLError):
                        _read_core_archive(url, NAME)
                open_url.assert_called_once()
                sleep.assert_not_called()

    def test_http_404_and_invalid_archive_size_are_never_retried(self):
        with (
            patch.dict(os.environ, {
                "AP_V33_CANDIDATE": "1",
                "AP_V30_MINIMAL_CORE_BUILD": "1",
                "AP_RELEASE_BUILD": "0",
                "AP_CORE_ARCHIVE_DIR": "",
            }),
            patch("fetch_mgba_core.time.sleep") as sleep,
        ):
            missing = url_error.HTTPError(URL, 404, "not found", {}, None)
            with patch("fetch_mgba_core.request.urlopen",
                       side_effect=missing) as open_url:
                with self.assertRaises(url_error.HTTPError):
                    _read_core_archive(URL, NAME)
                open_url.assert_called_once()
            with patch("fetch_mgba_core.request.urlopen",
                       return_value=response(b"X" * (MAX_ARCHIVE_SIZE + 1))
                       ) as open_url:
                with self.assertRaisesRegex(ValueError, "exceeds 30 MB"):
                    _read_core_archive(URL, NAME)
                open_url.assert_called_once()
            sleep.assert_not_called()

    def test_offline_release_never_uses_retry_or_network(self):
        with (
            patch.dict(os.environ, {
                "AP_V33_CANDIDATE": "1",
                "AP_V30_MINIMAL_CORE_BUILD": "1",
                "AP_RELEASE_BUILD": "1",
                "AP_CORE_ARCHIVE_DIR": "",
            }),
            patch("fetch_mgba_core.request.urlopen") as open_url,
            patch("fetch_mgba_core.time.sleep") as sleep,
        ):
            with self.assertRaisesRegex(ValueError, "AP_CORE_ARCHIVE_DIR"):
                _read_core_archive(URL, NAME)
            open_url.assert_not_called()
            sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
