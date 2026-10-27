"""Release preparation checks. Mocked Windows data is not native verification."""

from __future__ import annotations

import hashlib
import io
import json
import runpy
import struct
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from njit_auditor import desktop_download, web_app
from njit_auditor.desktop_download import desktop_release, parse_release
from njit_auditor.desktop_metadata import DESKTOP_VERSION
from njit_auditor.offline_app import create_offline_app, prepare_local_storage

ROOT = Path(__file__).parents[1]


def _record() -> dict:
    version = DESKTOP_VERSION
    filename = f"NJIT-Thesis-Auditor-{version}-windows-x64.zip"
    return {
        "enabled": True,
        "preview": False,
        "version": version,
        "url": "https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/"
        f"releases/download/desktop-v{version}/{filename}",
        "sha256": "a" * 64,
        "size_bytes": 123456,
        "windows_versions": ["Windows 10", "Windows 11"],
        "native_tested_windows_versions": ["Windows 10", "Windows 11"],
        "native_windows_build_verified": True,
        "public_download_verified": True,
        "verified_at": "2026-10-26T00:00:00Z",
        "approved_for_distribution": True,
        "licensing_reviewed": True,
        "license_basis": "commercial",
    }


def test_download_is_unpublished_by_default() -> None:
    desktop_release.cache_clear()
    release = desktop_release()
    assert not release.available and not release.preview and not release.url
    client = TestClient(web_app.app)
    assert "Download Desktop App" not in client.get("/").text
    response = client.get("/desktop")
    assert response.status_code == 404
    assert "releases/download" not in response.text


@pytest.mark.parametrize(
    "key,value",
    [
        ("enabled", False),
        ("approved_for_distribution", False),
        ("licensing_reviewed", False),
        ("license_basis", ""),
        ("license_basis", ["commercial"]),
        ("native_windows_build_verified", False),
        ("public_download_verified", False),
        ("native_tested_windows_versions", ["Windows 11"]),
        ("verified_at", ""),
        ("size_bytes", 0),
        ("sha256", ""),
        ("url", "https://example.com/missing.zip"),
        ("url", "http://github.com/private.zip"),
        ("url", "https://github.com:443/private.zip"),
        ("url", "https://user:password@github.com/private.zip"),
    ],
)
def test_incomplete_release_cannot_enable_download(key: str, value: object) -> None:
    record = {**_record(), key: value, "preview": True}
    release = parse_release(record)
    assert release.preview and not release.available and not release.url


def test_preview_has_disabled_button_and_no_installer_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        desktop_download, "desktop_release", lambda: parse_release({"preview": True})
    )
    body = TestClient(web_app.app).get("/").text
    assert "Audit your thesis locally, even without internet access." in body
    assert 'disabled aria-describedby="desktop-pending"' in body
    assert "releases/download" not in body


def test_verified_release_renders_metadata_instructions_and_checksum(monkeypatch) -> None:
    release = parse_release(_record())
    assert release.available
    monkeypatch.setattr(desktop_download, "desktop_release", lambda: release)
    client = TestClient(web_app.app)
    assert release.url in client.get("/").text
    body = client.get("/desktop").text
    for value in (
        release.url,
        release.sha256,
        release.version,
        release.filename,
        "Extract all",
        "NJIT Thesis Auditor.exe",
        "Updates are manual",
    ):
        assert value in body


def test_offline_about_and_routes_are_local(tmp_path: Path) -> None:
    prepare_local_storage(tmp_path)
    app = create_offline_app(port=17391, data_root=tmp_path, launch_ticket="ticket")
    with TestClient(app, base_url="http://127.0.0.1:17391") as client:
        assert client.get("/app-icon.ico").status_code == 403
        start = client.get("/_session/start?ticket=ticket", follow_redirects=False)
        assert start.headers["Referrer-Policy"] == "no-referrer"
        assert client.get("/").headers["Referrer-Policy"] == "same-origin"
        assert (
            client.post(
                "/quit", data={"csrf_token": app.state.csrf_token}, headers={"Origin": "null"}
            ).status_code
            == 403
        )
        body = client.get("/about").text
        assert "audited on this computer" in body and DESKTOP_VERSION in body
        for text in (
            "configured server",
            'href="/version"',
            "Result links do not require",
            "Why won't my public PDF link work?",
        ):
            assert text not in body
        assert client.get("/desktop").status_code == 404
        assert client.get("/app-icon.ico").status_code == 200
        home = client.get("/").text
        assert "Download Desktop App" not in home and "/audits/url" not in home
        assert 'action="/quit"' in home and 'href="/about"' in home


def test_windows_packager_rejects_linux_host(tmp_path) -> None:
    package = runpy.run_path(str(ROOT / "scripts/package_offline_desktop.py"))["package_windows"]
    with (
        patch("platform.system", return_value="Linux"),
        pytest.raises(RuntimeError, match="native"),
    ):
        package(tmp_path / "missing", tmp_path)


def test_zip_manifest_checksum_and_disabled_state_using_mocked_pe(tmp_path) -> None:
    package = runpy.run_path(str(ROOT / "scripts/package_offline_desktop.py"))["package_windows"]
    bundle = tmp_path / "bundle"
    (bundle / "_internal").mkdir(parents=True)
    header = bytearray(128)
    header[:2] = b"MZ"
    struct.pack_into("<I", header, 0x3C, 64)
    header[64:68] = b"PE\0\0"
    struct.pack_into("<H", header, 68, 0x8664)
    (bundle / "NJIT Thesis Auditor.exe").write_bytes(header)
    required = runpy.run_path(str(ROOT / "scripts/package_offline_desktop.py"))["REQUIRED_FILES"]
    for name in (*required, "_internal/python312.dll"):
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Synthetic placeholder for presence checks, not native verification")
    (bundle / "_internal/desktop-build-info.json").write_text(
        json.dumps(
            {
                "system": "Windows",
                "version": DESKTOP_VERSION,
                "commit": "b" * 40,
            }
        )
    )
    with (
        patch("platform.system", return_value="Windows"),
        patch("platform.machine", return_value="AMD64"),
    ):
        record = package(bundle, tmp_path / "packages")
    archive = tmp_path / "packages" / str(record["filename"])
    assert record["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert record["size_bytes"] == archive.stat().st_size
    assert not record["enabled"] and not record["approved_for_distribution"]
    assert not parse_release(record).available
    (bundle / "_internal/src/njit_auditor/templates/about.html").unlink()
    with (
        patch("platform.system", return_value="Windows"),
        patch("platform.machine", return_value="AMD64"),
        pytest.raises(ValueError, match="Required application assets"),
    ):
        package(bundle, tmp_path / "incomplete")


def test_public_verifier_checks_bytes_without_enabling_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = runpy.run_path(str(ROOT / "scripts/verify_desktop_download.py"))
    verify = module["verify_public_download"]
    payload = b"synthetic-public-package"
    record = {
        **_record(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    response = io.BytesIO(payload)
    response.status = 200
    opened = []

    class Opener:
        def open(self, url, timeout):
            opened.append((url, timeout))
            return response

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    receipt = verify(record)
    assert opened == [(record["url"], 30)]
    assert receipt["public_download_verified"]
    assert not receipt["enabled"] and not receipt["approved_for_distribution"]
    with pytest.raises(ValueError):
        verify({**record, "url": "http://localhost/private.zip"})


def test_license_collection_includes_nested_dependency_notices_only(tmp_path, monkeypatch):
    from types import SimpleNamespace

    collect = runpy.run_path(str(ROOT / "scripts/collect_desktop_licenses.py"))["collect"]
    (tmp_path / "fake.dist-info/licenses/LICENSES").mkdir(parents=True)
    (tmp_path / "fake.dist-info/licenses/LICENSES/BSD-3-Clause.txt").write_text("Synthetic notice")
    (tmp_path / "fake.dist-info/direct_url.json").write_text("private-checkout-path")
    dist = SimpleNamespace(
        metadata={"Name": "synthetic", "License": "BSD-3-Clause"},
        version="1.0",
        files=[
            "fake.dist-info/licenses/LICENSES/BSD-3-Clause.txt",
            "fake.dist-info/direct_url.json",
        ],
        locate_file=lambda name: tmp_path / name,
    )

    class Meta(dict):
        def get_all(self, key, default):
            return default

    dist.metadata = Meta(dist.metadata)
    monkeypatch.setattr("importlib.metadata.distributions", lambda: [dist])
    records = collect(tmp_path / "out")
    assert records[0]["notices"] == ["synthetic/00-BSD-3-Clause.txt"]
    assert "private-checkout-path" not in (tmp_path / "out/DEPENDENCIES.json").read_text()
