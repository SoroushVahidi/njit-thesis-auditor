"""Synthetic download-byte checks under Windows default newline translation."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from njit_auditor import web_app
from njit_auditor.synthetic_sample import sample_pdf


@pytest.mark.parametrize("export", ["json", "markdown", "text"])
def test_downloads_keep_utf8_lf_under_windows_text_io(
    export: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_write_text = Path.write_text

    def windows_write_text(self, data, encoding=None, errors=None, newline=None):
        return original_write_text(
            self, data, encoding=encoding, errors=errors,
            newline="\r\n" if newline is None else newline,
        )

    monkeypatch.setattr(Path, "write_text", windows_write_text)
    # Confirm this host reproduces Windows text mode unless the writer opts out.
    control = tmp_path / "windows-default.txt"
    control.write_text("synthetic\n", encoding="utf-8")
    assert control.read_bytes() == b"synthetic\r\n"
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "audits")
    monkeypatch.setattr(web_app, "_jobs", {})
    with TestClient(web_app.app) as client:
        response = client.post(
            "/audits", files={"file": ("synthetic.pdf", sample_pdf(), "application/pdf")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        job = response.headers["location"]
        assert client.get(job + "/status").json()["state"] == "complete"
        download = client.get(job + "/download/" + export)
        assert download.status_code == 200
        payload = download.content
        assert b"\n" in payload
        assert b"\r\n" not in payload
        assert payload.decode("utf-8").encode("utf-8") == payload
