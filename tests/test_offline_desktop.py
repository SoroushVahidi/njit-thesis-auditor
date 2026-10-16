"""Synthetic-only offline security, lifecycle, and online parity checks."""

from __future__ import annotations

import inspect
import re
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import fitz
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from njit_auditor import offline_app, web_app
from njit_auditor.offline_app import create_offline_app, prepare_local_storage

HOST = "http://127.0.0.1:17391"


def _pdf(kind: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if kind == "rotated":
        page.set_rotation(90)
    elif kind == "unicode":
        page.insert_text((60, 80), "Synthetic résumé — naïve study", fontsize=12)
    elif kind == "normal":
        page.insert_text((60, 80), "Synthetic dissertation chapter", fontsize=12)
    result = doc.tobytes()
    doc.close()
    return result


def _upload(client: TestClient, data: bytes, *, csrf: str | None = None) -> str:
    fields = {"csrf_token": csrf} if csrf else {}
    headers = {"Origin": HOST} if csrf else {}
    response = client.post(
        "/audits",
        files={"file": ("synthetic.pdf", data, "application/pdf")},
        data=fields,
        headers=headers,
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return response.headers["location"]


def _report(client: TestClient, url: str) -> dict:
    response = client.get(url + "/download/json")
    assert response.status_code == 200
    return response.json()


def _normalize(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _normalize(item)
            for key, item in value.items()
            if key not in {"job_id", "created_at", "finished_at", "generated_at", "input_file_path"}
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _report_pdf_content(payload: bytes) -> list[tuple[str, list[dict]]]:
    with fitz.open(stream=payload, filetype="pdf") as doc:
        return [(page.get_text(), page.get_drawings()) for page in doc]


def _normalize_markdown(payload: bytes) -> str:
    text = payload.decode("utf-8")
    return re.sub(r"(?m)^- Generated at: .+$", "- Generated at: <time>", text)


def _finding_order(page_html: str) -> list[tuple[str, str, str]]:
    return re.findall(
        r'<article[^>]*data-rule="([^"]*)"[^>]*data-category="([^"]*)"[^>]*data-page="([^"]*)"',
        page_html,
        flags=re.S,
    )


def _filter_script(page_html: str) -> str:
    return next(
        (
            script
            for script in re.findall(r"<script>(.*?)</script>", page_html, re.S)
            if "applyFiltersToRaw" in script
        ),
        "",
    )


@pytest.mark.parametrize("kind", ["normal", "unicode", "rotated", "low_text"])
def test_online_offline_parity(kind: str) -> None:
    data = _pdf(kind)
    with TemporaryDirectory() as online_dir, TemporaryDirectory() as offline_dir:
        web_app.RUNTIME_DIR = Path(online_dir)
        with web_app._jobs_lock:
            web_app._jobs.clear()
        with TestClient(web_app.app, base_url=HOST) as online:
            online_url = _upload(online, data)
            online_report = _report(online, online_url)
            online_status = online.get(online_url + "/status").json()
            online_findings = web_app._get_job(online_url.rsplit("/", 1)[-1]).findings
            online_page = online.get(online_url).text
            online_sorted = online.get(online_url + "?sort=confidence_desc").text
            online_pdf = online.get(online_url + "/pdf")
            online_combined = online.get(online_url + "/download/student-report.pdf")
            online_text = online.get(online_url + "/download/text").content
            online_md = online.get(online_url + "/download/markdown").content
            online_highlight = online.get(online_url + "/highlighted-page.pdf?page=1")
            assert online_pdf.status_code == online_combined.status_code == 200

        root = Path(offline_dir)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as offline:
            offline.get("/_session/start?ticket=ticket")
            offline_url = _upload(offline, data, csrf=app.state.csrf_token)
            offline_report = _report(offline, offline_url)
            offline_status = offline.get(offline_url + "/status").json()
            offline_findings = web_app._get_job(offline_url.rsplit("/", 1)[-1]).findings
            offline_page = offline.get(offline_url).text
            offline_sorted = offline.get(offline_url + "?sort=confidence_desc").text
            offline_pdf = offline.get(offline_url + "/pdf")
            offline_combined = offline.get(offline_url + "/download/student-report.pdf")
            offline_text = offline.get(offline_url + "/download/text").content
            offline_md = offline.get(offline_url + "/download/markdown").content
            offline_highlight = offline.get(offline_url + "/highlighted-page.pdf?page=1")
            assert offline_pdf.status_code == offline_combined.status_code == 200
            assert online_pdf.content == offline_pdf.content
            assert online_text == offline_text
            assert _normalize_markdown(online_md) == _normalize_markdown(offline_md)
            assert _report_pdf_content(online_combined.content) == _report_pdf_content(
                offline_combined.content
            )
            assert online_highlight.status_code == offline_highlight.status_code == 200
            assert _report_pdf_content(online_highlight.content) == _report_pdf_content(
                offline_highlight.content
            )
            assert ("Filter" in online_page) == ("Filter" in offline_page)
            assert _finding_order(online_page) == _finding_order(offline_page)
            assert _finding_order(online_sorted) == _finding_order(offline_sorted)
            if online_status["finding_count"]:
                assert _finding_order(online_page)
                assert _filter_script(online_page) == _filter_script(offline_page)
            if 'id="sort-problems"' in online_sorted:
                assert 'value="confidence_desc" selected' in online_sorted
                assert 'value="confidence_desc" selected' in offline_sorted
            assert ('id="filter-rule"' in online_page) == ('id="filter-rule"' in offline_page)
            assert ("highlighted-page.pdf" in online_page) == (
                "highlighted-page.pdf" in offline_page
            )

        assert online_status["finding_count"] == offline_status["finding_count"]
        assert _normalize(online_report) == _normalize(offline_report)
        assert _normalize(online_findings) == _normalize(offline_findings)


def test_offline_auth_routes_csrf_deletion_and_recovery() -> None:
    with TemporaryDirectory() as d:
        root = Path(d)
        audits = prepare_local_storage(root)
        abandoned = audits / "abandoned"
        abandoned.mkdir()
        (abandoned / "upload.pdf").write_bytes(_pdf("normal"))
        (root / "tmp" / "abandoned-upload").write_bytes(b"synthetic temporary data")
        prepare_local_storage(root)
        assert not abandoned.exists()
        assert not (root / "tmp" / "abandoned-upload").exists()
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        routes = {r.path for r in app.routes}
        assert "/audits/url" not in routes
        assert "/audits/sample" not in routes
        assert "/version" not in routes
        with TestClient(app, base_url=HOST) as client:
            assert client.get("/").status_code == 403
            assert client.get("/audits/x/pdf").status_code == 403
            assert client.get("/audits/x/download/json").status_code == 403
            assert client.get("/_session/start?ticket=wrong").status_code == 403
            assert (
                client.get("/_session/start?ticket=ticket", follow_redirects=False).status_code
                == 303
            )
            assert client.get("/", headers={"Host": "evil.example"}).status_code == 403
            assert client.get("/", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
            assert (
                client.post("/local-data/delete-all", headers={"Origin": HOST}).status_code == 403
            )
            assert (
                client.post(
                    "/local-data/delete-all", data={"csrf_token": "wrong"}, headers={"Origin": HOST}
                ).status_code
                == 403
            )
            assert (
                client.post(
                    "/local-data/delete-all",
                    data={"csrf_token": app.state.csrf_token},
                    headers={"Origin": "http://evil.example"},
                ).status_code
                == 403
            )
            url = _upload(client, _pdf("normal"), csrf=app.state.csrf_token)
            job_id = urlparse(url).path.rsplit("/", 1)[-1]
            assert (audits / job_id / "upload.pdf").exists()
            report_bytes = client.get(url + "/download/json").content
            assert app.state.csrf_token.encode() not in report_bytes
            assert client.cookies["njit_offline_session"].encode() not in report_bytes
            assert client.get(url + "/highlighted-page.pdf?page=1").status_code == 200
            assert (
                client.post(
                    url + "/delete",
                    data={"csrf_token": app.state.csrf_token},
                    headers={"Origin": HOST},
                    follow_redirects=False,
                ).status_code
                == 303
            )
            assert not (audits / job_id).exists()
            assert client.get(url + "/download/json").status_code == 404
            url2 = _upload(client, _pdf("normal"), csrf=app.state.csrf_token)
            assert (
                client.post(
                    "/local-data/delete-all",
                    data={"csrf_token": app.state.csrf_token},
                    headers={"Origin": HOST},
                    follow_redirects=False,
                ).status_code
                == 303
            )
            assert client.get(url2 + "/status").status_code == 404
        assert not any(audits.iterdir())


def test_audit_with_connections_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """A synthetic audit completes when application socket connects are disabled."""
    attempts: list[object] = []

    def deny_connect(self: socket.socket, address: object) -> None:
        attempts.append(address)
        raise AssertionError("outbound socket connect attempted")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    with TemporaryDirectory() as d:
        root = Path(d)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            url = _upload(client, _pdf("normal"), csrf=app.state.csrf_token)
            assert client.get(url + "/status").json()["state"] == "complete"
    assert attempts == []


def test_fastapi_telemetry_stays_disabled_with_export_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FASTAPI_OTEL_AUTO_CONFIGURE", "true")
    with TemporaryDirectory() as d:
        root = Path(d)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        if hasattr(app, "_telemetry"):
            assert app._telemetry["auto_configure"] is False
            assert app._telemetry["tracing"] is False
            assert app._telemetry["metrics"] is False
            assert app._telemetry["logs"] is False
        else:
            assert "telemetry" not in inspect.signature(FastAPI).parameters


def test_deleting_running_audit_waits_for_completion() -> None:
    with TemporaryDirectory() as d:
        root = Path(d)
        audits = prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        job_id = "synthetic-running-job"
        workspace = audits / job_id
        workspace.mkdir()
        (workspace / "upload.pdf").write_bytes(_pdf("normal"))
        job = web_app.JobState(
            job_id=job_id,
            state="running",
            created_at="2026-10-16T00:00:00Z",
            file_name="synthetic.pdf",
        )
        web_app._set_job(job)
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            response = client.post(
                f"/audits/{job_id}/delete",
                data={"csrf_token": app.state.csrf_token},
                headers={"Origin": HOST},
                follow_redirects=False,
            )
            assert response.headers["location"] == "/?deletion=pending"
            assert "queued for deletion" in client.get(response.headers["location"]).text
        assert workspace.exists()
        job.state = "complete"
        web_app._set_job(job)
        offline_app._after_audit(job_id)
        assert not workspace.exists()
        assert web_app._get_job(job_id) is None


def test_failed_deletion_is_visible_and_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    with TemporaryDirectory() as d:
        root = Path(d)
        audits = prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            url = _upload(client, _pdf("normal"), csrf=app.state.csrf_token)
            job_id = url.rsplit("/", 1)[-1]
            original_remove = web_app._delete_job_workspace
            monkeypatch.setattr(web_app, "_delete_job_workspace", lambda _job_id: False)
            response = client.post(
                url + "/delete",
                data={"csrf_token": app.state.csrf_token},
                headers={"Origin": HOST},
                follow_redirects=False,
            )
            assert response.headers["location"] == "/?deletion=failed"
            assert "could not be deleted" in client.get(response.headers["location"]).text
            assert (audits / job_id / "upload.pdf").exists()
            monkeypatch.setattr(web_app, "_delete_job_workspace", original_remove)
            retry = client.post(
                "/local-data/delete-all",
                data={"csrf_token": app.state.csrf_token},
                headers={"Origin": HOST},
                follow_redirects=False,
            )
            assert retry.headers["location"] == "/?deletion=deleted"
            assert not (audits / job_id).exists()


def test_invalid_pdf_failure_page_parity() -> None:
    with TemporaryDirectory() as online_dir, TemporaryDirectory() as offline_dir:
        web_app.RUNTIME_DIR = Path(online_dir)
        with TestClient(web_app.app, base_url=HOST) as online:
            response_online = online.post(
                "/audits",
                files={"file": ("bad.pdf", b"not a PDF", "application/pdf")},
            )
        root = Path(offline_dir)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as offline:
            offline.get("/_session/start?ticket=ticket")
            response_offline = offline.post(
                "/audits",
                files={"file": ("bad.pdf", b"not a PDF", "application/pdf")},
                data={"csrf_token": app.state.csrf_token},
                headers={"Origin": HOST},
            )
        assert response_online.status_code == response_offline.status_code == 400
        assert "Could not start audit" in response_online.text
        assert "Could not start audit" in response_offline.text
