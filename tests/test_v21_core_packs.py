"""Approved in-app emulator-pack downloader, integrity and rollback tests.

No network calls or runnable native libraries are needed for these tests.
"""
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from anything_plays import core_packs as packs


class DummyResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, limit):
        return self.data[:limit]


def synthetic_pack(name="mgba", *, content=None, tag="v3.0.0-alpha.2-cores"):
    target, ext = packs.target_identity()
    binary = content if content is not None else (
        {".so": b"\x7fELF", ".dll": b"MZaa", ".dylib": b"\xcf\xfa\xed\xfe"}[ext]
        + b"\x01" * 15000
    )
    filename = f"{name}_libretro{ext}"
    meta = {
        "schema": 1, "name": name, "target": target, "release": tag,
        "file": filename, "sha256": hashlib.sha256(binary).hexdigest(),
        "source_repository": "https://github.com/" + packs.UPSTREAM_REPOS[name],
        "third_party_license_reviewed": True,
        "packaged_runtime_tested": True,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("core-pack.json", json.dumps(meta))
        archive.writestr(filename, binary)
    data = output.getvalue()
    asset = {
        "name": name, "target": target, "release": tag, "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "url": (packs.RELEASE_PREFIX + tag + "/"
                + packs._release_asset(name, target)),
    }
    return asset, data


class ApprovedCorePackTests(unittest.TestCase):
    def test_all_supported_platform_names_are_unambiguous(self):
        self.assertEqual(packs.target_identity("win32", "AMD64"),
                         ("windows-x64", ".dll"))
        self.assertEqual(packs.target_identity("darwin", "arm64"),
                         ("macos-arm64", ".dylib"))
        self.assertEqual(packs.target_identity("darwin", "x86_64"),
                         ("macos-x64", ".dylib"))
        self.assertEqual(packs.target_identity("linux", "x86_64"),
                         ("linux-x64", ".so"))
        with self.assertRaises(ValueError):
            packs.target_identity("linux", "arm64")

    def test_latest_official_release_asset_and_sha_required(self):
        asset, data = synthetic_pack()
        target = asset["target"]
        name = packs._release_asset("mgba", target)
        releases = [
            {
                "tag_name": "v3.0.0-alpha.2-cores", "draft": False,
                "assets": [{
                    "name": name, "digest": "sha256:" + asset["sha256"],
                    "size": len(data), "browser_download_url": asset["url"],
                }],
            },
            {
                "tag_name": "v3.0.0-alpha.3-cores", "draft": True,
                "assets": [{
                    "name": name, "digest": "sha256:" + asset["sha256"],
                    "size": len(data), "browser_download_url": asset["url"],
                }],
            },
        ]
        result = packs.discover_core_packs(
            opener=lambda request, timeout: DummyResponse(
                json.dumps(releases).encode()
            )
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "mgba")
        self.assertEqual(result[0]["sha256"], asset["sha256"])
        releases[0]["assets"][0].pop("digest")
        self.assertEqual(packs.discover_core_packs(
            opener=lambda req, timeout: DummyResponse(json.dumps(releases).encode())
        ), [])

    def test_install_switch_restore_and_unmodified_objects(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, data1 = synthetic_pack()
            install = lambda asset, data: packs.install_core_pack(
                asset, root=root, opener=lambda req, timeout: DummyResponse(data)
            )
            with self.assertRaisesRegex(RuntimeError, "Stop the running game"):
                packs.install_core_pack(first, root=root, emulator_busy=True)
            path1 = Path(install(first, data1))
            self.assertEqual(packs.managed_core_path("mgba", root=root), str(path1))
            # Native header of synthetic_pack has to match the current target.
            _, extension = packs.target_identity()
            magic = {".so": b"\x7fELF", ".dll": b"MZaa",
                     ".dylib": b"\xcf\xfa\xed\xfe"}[extension]
            second, data2 = synthetic_pack(
                content=magic + b"\x02" * 15000, tag="v3.0.0-alpha.3-cores"
            )
            path2 = Path(install(second, data2))
            self.assertNotEqual(path1, path2)
            self.assertEqual(packs.managed_core_path("mgba", root=root), str(path2))
            self.assertTrue(path1.exists())
            self.assertTrue(packs.rollback_core("mgba", root=root))
            self.assertEqual(packs.managed_core_path("mgba", root=root), str(path1))
            self.assertTrue(packs.rollback_core("mgba", root=root))
            self.assertIsNone(packs.managed_core_path("mgba", root=root))
            self.assertTrue(path1.exists())
            self.assertTrue(path2.exists())

    def test_tamper_never_overrides_original_bundle(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset, data = synthetic_pack()
            path = Path(packs.install_core_pack(
                asset, root=root, opener=lambda req, timeout: DummyResponse(data)
            ))
            path.write_bytes(b"malicious altered file")
            self.assertIsNone(packs.managed_core_path("mgba", root=root))
            self.assertIsNone(packs.installed_pack_revision("mgba", root=root))

    def test_reject_wrong_github_and_modified_asset(self):
        asset, data = synthetic_pack()
        bad = dict(asset, url="https://example.com/untrusted.zip")
        with self.assertRaisesRegex(ValueError, "official release"):
            packs.install_core_pack(
                bad, opener=lambda req, timeout: DummyResponse(data)
            )
        with TemporaryDirectory() as folder:
            bad = dict(asset, sha256="0"*64)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                packs.install_core_pack(
                    bad, root=folder,
                    opener=lambda req, timeout: DummyResponse(data),
                )
            self.assertFalse((Path(folder) / "active.json").exists())

    def test_zip_path_traversal_or_other_core_rejected(self):
        asset, _ = synthetic_pack()
        injected = io.BytesIO()
        with zipfile.ZipFile(injected, "w") as z:
            z.writestr("../untrusted.so", b"bad")
            z.writestr("core-pack.json", "{}")
        data = injected.getvalue()
        item = dict(asset, size=len(data), sha256=hashlib.sha256(data).hexdigest())
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "Invalid core pack files"):
                packs.install_core_pack(
                    item, root=folder,
                    opener=lambda req, timeout: DummyResponse(data)
                )
            self.assertFalse((Path(folder) / "active.json").exists())


if __name__ == "__main__":
    unittest.main()
