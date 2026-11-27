"""Exercise resource discovery and privacy-safe Rule Reference failures."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from njit_auditor import offline_app, resource_paths, web_app

BAD_CATALOGS = [
    None,
    b"{broken",
    b"\xff",
    b"{}",
    b"[]",
    b"[false]",
    b'[{"id": 17}]',
    b'[{"id": "P013", "notes": ["damaged"]}]',
    b'[{"id": "P013", "severity": {"unexpected": true}}]',
    b'[{"id": "P013", "input_required": {"unexpected": true}}]',
]


@pytest.mark.parametrize("payload", BAD_CATALOGS)
@pytest.mark.parametrize("offline", [False, True])
def test_catalog_failure_and_recovery(tmp_path, monkeypatch, payload, offline):
    canonical = web_app._RULES_JSON_PATH
    catalog = tmp_path / "private-catalog.json"
    if payload is not None:
        catalog.write_bytes(payload)
    monkeypatch.setattr(web_app, "_RULES_JSON_PATH", catalog)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "web-runtime")
    if offline:
        data = tmp_path / "desktop-runtime"
        offline_app.prepare_local_storage(data)
        app = offline_app.create_offline_app(port=17391, data_root=data, launch_ticket="test")
        origin = "http://127.0.0.1:17391"
    else:
        app = web_app.app
        origin = "http://testserver"

    with TestClient(app, base_url=origin) as client:
        if offline:
            assert client.get("/_session/start", params={"ticket": "test"}).status_code == 200
        response = client.get("/rules")
        assert response.status_code == 503
        assert "The Rule Reference is unavailable." in response.text
        message = "complete copy" if offline else "Please try again later"
        assert message in response.text
        assert "private-catalog.json" not in response.text
        assert str(tmp_path) not in response.text
        assert client.get("/help").status_code == 200

        catalog.write_bytes(canonical.read_bytes())
        recovered = client.get("/rules")
        assert recovered.status_code == 200
        assert 'id="P013"' in recovered.text


def test_unreadable_catalog_returns_unavailable(monkeypatch):
    canonical = web_app._RULES_JSON_PATH
    read_text = Path.read_text

    def deny_catalog(path, *args, **kwargs):
        if path == canonical:
            raise PermissionError("private error message")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny_catalog)
    with TestClient(web_app.app) as client:
        response = client.get("/rules")
    assert response.status_code == 503
    assert "private error message" not in response.text


def test_frozen_paths_keep_bundle_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_paths.package_path("templates") == tmp_path / "src/njit_auditor/templates"
    assert resource_paths.resource_path("assets", "icons") == tmp_path / "assets/icons"


def test_public_rule_links_recover_after_a_failed_catalog_read(tmp_path, monkeypatch):
    canonical = web_app._RULES_JSON_PATH
    catalog = tmp_path / "catalog.json"
    monkeypatch.setattr(web_app, "_RULES_JSON_PATH", catalog)
    web_app._cached_public_rule_lookup.cache_clear()
    try:
        assert web_app._public_rule_lookup() == {}
        catalog.write_bytes(canonical.read_bytes())
        assert "P013" in web_app._public_rule_lookup()
    finally:
        web_app._cached_public_rule_lookup.cache_clear()
