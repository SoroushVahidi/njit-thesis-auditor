"""The student default cannot fetch URLs; deliberate server configuration can restore it."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from test_offline_desktop import _pdf

from njit_auditor import web_app
from njit_auditor.feature_flags import pdf_url_auditing_enabled
from njit_auditor.offline_app import create_offline_app, prepare_local_storage

FLAG = "NJIT_AUDITOR_ENABLE_PDF_URL_AUDITING"


@pytest.mark.parametrize("setting", [None, "", "0", "false", "true", "yes", "1 "])
def test_url_auditing_fails_closed(setting, monkeypatch, tmp_path):
    if setting is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, setting)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "audits")
    monkeypatch.setattr(web_app, "_jobs", {})
    fetch = Mock(side_effect=AssertionError("URL transport must not run"))
    allocate = Mock(side_effect=AssertionError("Disabled route must not allocate jobs"))
    monkeypatch.setattr(web_app, "fetch_pdf_url", fetch)
    monkeypatch.setattr(web_app, "_new_job_id", allocate)
    assert not pdf_url_auditing_enabled()
    with TestClient(web_app.app) as client:
        for url in ("https://invalid.example/test.pdf", "http://127.0.0.1/a", "", "file:///tmp/x"):
            response = client.post("/audits/url?enabled=1", data={"pdf_url": url, FLAG: "1"})
            assert response.status_code == 404
            assert "Upload a local PDF" in response.text
            assert 'name="pdf_url"' not in response.text
        index = client.get("/").text
        assert 'action="/audits/url"' not in index
        assert 'action="/audits"' in index
        assert 'type="file"' in index
        assert client.get("/audits/url", follow_redirects=False).status_code == 302
        for path in ("/about", "/help"):
            page = client.get(path)
            assert page.status_code == 200
            assert "public PDF link" not in page.text
            assert "audit a public PDF URL" not in page.text
    fetch.assert_not_called()
    allocate.assert_not_called()
    assert not list(tmp_path.rglob("upload.pdf"))
    assert not web_app._jobs


def test_local_upload_still_audits_when_url_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(web_app, "_jobs", {})
    with TestClient(web_app.app) as client:
        response = client.post(
            "/audits",
            files={"file": ("synthetic.pdf", _pdf("normal"), "application/pdf")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        job = response.headers["location"]
        assert client.get(job + "/status").json()["state"] == "complete"
        assert client.get(job + "/download/json").status_code == 200


def test_deliberate_reactivation_retains_implementation(monkeypatch, tmp_path):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(web_app, "_jobs", {})

    def fetch(url, destination: Path, max_bytes):
        assert url == "https://synthetic.invalid/test.pdf"
        destination.write_bytes(_pdf("normal"))

    monkeypatch.setattr(web_app, "fetch_pdf_url", fetch)
    with TestClient(web_app.app) as client:
        assert 'name="pdf_url"' in client.get("/").text
        response = client.post(
            "/audits/url",
            data={"pdf_url": "https://synthetic.invalid/test.pdf"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert client.get(response.headers["location"] + "/status").json()["state"] == "complete"


@pytest.mark.parametrize("setting", ["0", "1"])
def test_desktop_never_exposes_url_import(monkeypatch, tmp_path, setting):
    monkeypatch.setenv(FLAG, setting)
    prepare_local_storage(tmp_path)
    app = create_offline_app(port=17391, data_root=tmp_path, launch_ticket="synthetic")
    with TestClient(app, base_url="http://127.0.0.1:17391") as client:
        client.get("/_session/start?ticket=synthetic")
        assert 'name="pdf_url"' not in client.get("/").text
        assert "/audits/url" not in {route.path for route in app.routes}
        response = client.post(
            "/audits/url",
            data={"csrf_token": app.state.csrf_token, "pdf_url": "https://invalid.example/x.pdf"},
            headers={"Origin": "http://127.0.0.1:17391"},
        )
        assert response.status_code in {404, 405}
