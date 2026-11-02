"""Synthetic-only offline security, lifecycle, and online parity checks."""

from __future__ import annotations

import inspect
import logging
import re
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.parse import urlparse

import fitz
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from njit_auditor import offline_app, web_app
from njit_auditor.desktop_network import (
    is_loopback_address,
    loopback_connect,
    loopback_connect_ex,
)
from njit_auditor.offline_app import create_offline_app, prepare_local_storage
from njit_auditor.offline_launcher import _single_instance_lock

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
    elif kind == "uri_link":
        page.insert_text((60, 80), "Synthetic dissertation chapter", fontsize=12)
        page.insert_link(
            {
                "kind": fitz.LINK_URI,
                "from": fitz.Rect(60, 60, 220, 85),
                "uri": "https://invalid.example/audit",
            }
        )
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


def _normalize_audit_time(text: str) -> str:
    # Independent audits legitimately cross a wall-clock second. Only the
    # report header's recorded audit time is volatile; findings stay exact.
    return re.sub(
        r"(?m)^(Audit date/time \(UTC\): )\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
        r"\1<time>",
        text,
    )


def _report_pdf_content(payload: bytes) -> list[tuple[str, list[dict]]]:
    with fitz.open(stream=payload, filetype="pdf") as doc:
        return [(_normalize_audit_time(page.get_text()), page.get_drawings()) for page in doc]


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
            assert _normalize_audit_time(online_text.decode()) == _normalize_audit_time(
                offline_text.decode()
            )
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
        assert "/audits/sample" in routes  # Locally generated synthetic example only.
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


@pytest.mark.parametrize("kind", ["normal", "uri_link", "malformed"])
def test_audit_with_connections_denied(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    """Synthetic and malformed PDFs cause no outbound connects or DNS lookups."""
    attempts: list[object] = []

    def deny_connect(self: socket.socket, address: object) -> None:
        if is_loopback_address(self.family, address):
            return loopback_connect(self, address)
        attempts.append(address)
        raise AssertionError("outbound socket connect attempted")

    def deny_connect_ex(self: socket.socket, address: object) -> int:
        if is_loopback_address(self.family, address):
            return loopback_connect_ex(self, address)
        attempts.append(address)
        raise AssertionError("outbound socket connect_ex attempted")

    def deny_dns(*args: object, **kwargs: object) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("DNS lookup attempted")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", deny_dns)
    monkeypatch.setattr(socket, "gethostbyname", deny_dns)
    with TemporaryDirectory() as d:
        root = Path(d)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            if kind == "malformed":
                response = client.post(
                    "/audits",
                    files={
                        "file": ("malformed.pdf", b"%PDF-synthetic-malformed", "application/pdf")
                    },
                    data={"csrf_token": app.state.csrf_token},
                    headers={"Origin": HOST},
                    follow_redirects=False,
                )
                assert response.status_code == 303
                status = client.get(response.headers["location"] + "/status").json()
                assert status["state"] == "failed"
            else:
                url = _upload(client, _pdf(kind), csrf=app.state.csrf_token)
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


@pytest.mark.parametrize("filename", ["../odd name.pdf", "nested\\name.pdf", "é résumé.pdf"])
def test_odd_filename_stays_in_workspace(filename: str) -> None:
    with TemporaryDirectory() as d:
        root = Path(d)
        audits = prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            response = client.post(
                "/audits",
                files={"file": (filename, _pdf("normal"), "application/pdf")},
                data={"csrf_token": app.state.csrf_token},
                headers={"Origin": HOST},
                follow_redirects=False,
            )
            assert response.status_code == 303
            job_id = response.headers["location"].rsplit("/", 1)[-1]
            assert (audits / job_id / "upload.pdf").exists()
            assert len(list((audits / job_id).glob("*.pdf"))) >= 1
            assert not (root / "odd name.pdf").exists()
            assert client.get(response.headers["location"] + "/pdf").status_code == 200


def test_encrypted_pdf_error_parity() -> None:
    doc = fitz.open(stream=_pdf("normal"), filetype="pdf")
    encrypted = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="synthetic-owner", user_pw="synthetic-user"
    )
    doc.close()
    with TemporaryDirectory() as online_dir, TemporaryDirectory() as offline_dir:
        web_app.RUNTIME_DIR = Path(online_dir)
        with TestClient(web_app.app, base_url=HOST) as online:
            online_response = online.post(
                "/audits",
                files={"file": ("encrypted.pdf", encrypted, "application/pdf")},
                follow_redirects=False,
            )
            online_state = online.get(online_response.headers["location"] + "/status").json()
            online_error = web_app._get_job(online_state["job_id"]).error_message
        root = Path(offline_dir)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as offline:
            offline.get("/_session/start?ticket=ticket")
            offline_response = offline.post(
                "/audits",
                files={"file": ("encrypted.pdf", encrypted, "application/pdf")},
                data={"csrf_token": app.state.csrf_token},
                headers={"Origin": HOST},
                follow_redirects=False,
            )
            offline_state = offline.get(offline_response.headers["location"] + "/status").json()
            offline_error = web_app._get_job(offline_state["job_id"]).error_message
        assert online_response.status_code == offline_response.status_code
        assert online_response.status_code == 303
        assert online_state["state"] == offline_state["state"] == "failed"
        assert online_error == offline_error


@pytest.mark.parametrize("linked_directory", ["audits", "tmp"])
def test_startup_refuses_linked_storage_without_deleting_target(linked_directory: str) -> None:
    with TemporaryDirectory() as d:
        base = Path(d)
        root = base / "app"
        root.mkdir()
        outside = base / "outside"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_text("synthetic private data")
        try:
            (root / linked_directory).symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("directory symlinks unavailable on this platform")
        with pytest.raises(RuntimeError, match="must not be a link"):
            prepare_local_storage(root)
        assert sentinel.read_text() == "synthetic private data"


def test_launcher_refuses_linked_root_without_creating_lock_file() -> None:
    with TemporaryDirectory() as d:
        base = Path(d)
        outside = base / "outside"
        outside.mkdir()
        linked_root = base / "app"
        try:
            linked_root.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("directory symlinks unavailable on this platform")
        with pytest.raises(RuntimeError, match="must not be a link"):
            _single_instance_lock(linked_root)
        assert not (outside / "desktop.lock").exists()


def test_launcher_refuses_linked_lock_without_writing_target() -> None:
    with TemporaryDirectory() as d:
        base = Path(d)
        root = base / "app"
        root.mkdir()
        outside = base / "outside-empty.txt"
        outside.write_bytes(b"")
        try:
            (root / "desktop.lock").symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("file symlinks unavailable on this platform")
        with pytest.raises(RuntimeError, match="lock file must not be a link"):
            _single_instance_lock(root)
        assert outside.read_bytes() == b""


@pytest.mark.parametrize("parent_name", ["audits", "tmp"])
def test_startup_removes_child_link_without_following_target(parent_name: str) -> None:
    with TemporaryDirectory() as d:
        base = Path(d)
        root = base / "app"
        prepare_local_storage(root)
        outside = base / "outside"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_text("synthetic private data")
        link = root / parent_name / "abandoned-link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("directory symlinks unavailable on this platform")
        prepare_local_storage(root)
        assert not link.exists()
        assert sentinel.read_text() == "synthetic private data"


def test_reparse_point_detection_works_without_path_is_junction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = Path("synthetic-windows-junction")
    monkeypatch.setattr(Path, "is_symlink", lambda self: False)
    monkeypatch.setattr(Path, "lstat", lambda self: SimpleNamespace(st_file_attributes=0x400))
    assert offline_app.is_link_or_junction(path)


def test_report_download_refuses_link_outside_runtime() -> None:
    with TemporaryDirectory() as d:
        base = Path(d)
        root = base / "app"
        audits = prepare_local_storage(root)
        outside = base / "outside.txt"
        outside.write_text("synthetic outside sentinel")
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            url = _upload(client, _pdf("normal"), csrf=app.state.csrf_token)
            job_id = url.rsplit("/", 1)[-1]
            for extension, route in (("json", "json"), ("md", "markdown"), ("txt", "text")):
                report = audits / job_id / f"report.{extension}"
                report.unlink()
                try:
                    report.symlink_to(outside)
                except (OSError, NotImplementedError):
                    pytest.skip("file symlinks unavailable on this platform")
                response = client.get(url + f"/download/{route}")
                assert response.status_code == 404
                assert outside.read_bytes() not in response.content
            report = audits / job_id / "report.json"
            report.unlink()
            report.symlink_to(report)
            assert client.get(url + "/download/json").status_code == 404


def test_combined_pdf_failure_does_not_log_job_id_or_exception_message(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with TemporaryDirectory() as d:
        root = Path(d)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            url = _upload(client, _pdf("normal"), csrf=app.state.csrf_token)
            job_id = url.rsplit("/", 1)[-1]

            def fail_report(*args: object, **kwargs: object) -> None:
                raise RuntimeError("synthetic-secret-pdf-content")

            monkeypatch.setattr(web_app, "build_combined_student_pdf_report", fail_report)
            with caplog.at_level(logging.WARNING, logger="njit_auditor.web_app"):
                response = client.get(url + "/download/student-report.pdf")
            assert response.status_code == 500
            assert "synthetic-secret-pdf-content" not in response.text
            assert "synthetic-secret-pdf-content" not in caplog.text
            assert job_id not in caplog.text
            assert "RuntimeError" in caplog.text


def test_highlight_failure_does_not_log_job_id_or_exception_message(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with TemporaryDirectory() as d:
        root = Path(d)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket="ticket")
        with TestClient(app, base_url=HOST) as client:
            client.get("/_session/start?ticket=ticket")
            url = _upload(client, _pdf("normal"), csrf=app.state.csrf_token)
            job_id = url.rsplit("/", 1)[-1]

            def fail_highlight(*args: object, **kwargs: object) -> None:
                raise RuntimeError("synthetic-secret-highlight-text")

            monkeypatch.setattr(web_app, "_matching_findings_for_highlight", fail_highlight)
            with caplog.at_level(logging.WARNING, logger="njit_auditor.web_app"):
                response = client.get(url + "/pdf/highlighted?page=1")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "synthetic-secret-highlight-text" not in caplog.text
            assert job_id not in caplog.text
            assert "RuntimeError" in caplog.text


def test_parity_normalization_changes_only_the_report_audit_time() -> None:
    first = "Audit date/time (UTC): 2026-10-26 23:59:59\nMeasured gap: 12.5 pt\n"
    second = "Audit date/time (UTC): 2026-10-27 00:00:00\nMeasured gap: 12.5 pt\n"
    assert _normalize_audit_time(first) == _normalize_audit_time(second)
    assert _normalize_audit_time(first) != _normalize_audit_time(second.replace("12.5", "13.5"))


def test_local_example_uses_only_generated_synthetic_pdf(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError('Private online samples must not be loaded')

    monkeypatch.setattr(web_app, 'get_builtin_sample', forbidden)
    monkeypatch.setattr(web_app, 'copy_builtin_sample_to_job', forbidden)
    with TemporaryDirectory() as directory:
        root = Path(directory)
        prepare_local_storage(root)
        app = create_offline_app(port=17391, data_root=root, launch_ticket='ticket')
        with TestClient(app, base_url=HOST) as client:
            client.get('/_session/start?ticket=ticket')
            response = client.post('/audits/sample',
                                   data={'csrf_token': app.state.csrf_token},
                                   headers={'Origin': HOST}, follow_redirects=False)
            assert response.status_code == 303
            job = response.headers['location']
            assert client.get(job+'/status').json()['state'] == 'complete'
            original = client.get(job+'/pdf')
            with fitz.open(stream=original.content, filetype='pdf') as pdf:
                assert 'SYNTHETIC THESIS' in pdf[0].get_text()
            assert _report(client, job)['findings']
