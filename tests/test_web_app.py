"""Tests for the NJIT Thesis Auditor web upload UI."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Minimal synthetic PDF header — enough to pass the magic-byte check
_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


def _make_app(tmp_path: Path) -> Any:
    """Import the web app with RUNTIME_DIR pointed at a temp directory."""
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    # Re-import so RUNTIME_DIR picks up the env var
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return wa.app, wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    app, wa = _make_app(tmp_path)
    return TestClient(app, raise_server_exceptions=False), wa


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

def test_index_get_returns_200(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"<form" in resp.content
    assert b"NJIT Thesis Auditor" in resp.content


def test_index_contains_file_input(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert b'type="file"' in resp.content
    assert b'accept=".pdf"' in resp.content


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------

def test_upload_no_file_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post("/audits", data={})
    assert resp.status_code in (400, 422)


def test_upload_non_pdf_extension_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("thesis.docx", io.BytesIO(b"PK\x03\x04fake"), "application/octet-stream")},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert b"Only PDF files" in resp.content


def test_upload_wrong_magic_bytes_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("thesis.pdf", io.BytesIO(b"NOTAPDF_content"), "application/pdf")},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert b"does not appear to be a PDF" in resp.content


def test_upload_too_small_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("tiny.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        follow_redirects=False,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Successful upload (monkeypatched audit runner)
# ---------------------------------------------------------------------------

def _fake_audit(pdf_path: Path) -> list[Any]:
    from njit_auditor.models import AuditFinding, Severity

    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Margin violation detected.",
            details={"issue_type": "margin_boundary_violation", "side": "left"},
        )
    ]


def test_upload_pdf_creates_job_and_redirects(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        resp = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    location = resp.headers["location"]
    assert location.startswith("/audits/")


def test_job_page_pending_shows_processing(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        resp_post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=False,
        )
    job_url = resp_post.headers["location"]
    resp = c.get(job_url)
    assert resp.status_code == 200
    # Either "Processing" or already moved past pending (background may have run)
    body = resp.content
    assert b"Processing" in body or b"complete" in body.lower() or b"Audit" in body


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

def test_status_endpoint_unknown_job(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/audits/nonexistent_job_id/status")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data


def test_status_endpoint_returns_pending(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=False,
        )
    job_id = post.headers["location"].split("/audits/")[1]
    resp = c.get(f"/audits/{job_id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["state"] in ("pending", "running", "complete", "failed")


def test_status_endpoint_complete_after_audit(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "run_pdf_audit_full", _fake_audit):
        post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=True,
        )
    # follow_redirects=True should load the job page; extract job_id from URL
    job_id_url = post.url
    assert "/audits/" in str(job_id_url)
    job_id = str(job_id_url).split("/audits/")[1].rstrip("/")
    resp = c.get(f"/audits/{job_id}/status")
    data = resp.json()
    assert data["state"] in ("complete", "running", "failed")


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _inject_complete_job(wa: Any, tmp_path: Path) -> str:
    """Create a complete job in the job store and on disk."""
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report

    job_id = secrets.token_urlsafe(16)
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation"},
        )
    ]
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        finding_count=1,
        warn_count=1,
        fail_count=0,
        findings=[
            {
                "rule_id": "P011",
                "severity": "WARNING",
                "page": 2,
                "issue_type": "margin_boundary_violation",
                "message": "Left margin too narrow.",
            }
        ],
        grouped_summary=[],
        md_preview="# Audit Report\n",
    )
    wa._set_job(job)
    return job_id


def test_results_page_shows_findings(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"P011" in resp.content
    assert b"complete" in resp.content.lower() or b"finding" in resp.content.lower()


# ---------------------------------------------------------------------------
# Download endpoints
# ---------------------------------------------------------------------------

def test_download_json_returns_json(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert "findings" in data
    assert "metadata" in data


def test_download_markdown_returns_text(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/markdown")
    assert resp.status_code == 200
    ct = resp.headers["content-type"]
    assert "text/markdown" in ct or "text/plain" in ct


def test_download_missing_job_returns_404(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    assert c.get("/audits/badid/download/json").status_code == 404
    assert c.get("/audits/badid/download/markdown").status_code == 404


# ---------------------------------------------------------------------------
# Runtime files are not tracked by git
# ---------------------------------------------------------------------------

def test_runtime_dir_is_gitignored(tmp_path: Path) -> None:
    repo_root = Path(__file__).parent.parent
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert ".runtime/" in gitignore or ".runtime" in gitignore


# ---------------------------------------------------------------------------
# URL fetch module — SSRF / scheme / host unit tests (no web client needed)
# ---------------------------------------------------------------------------


def test_url_fetch_rejects_file_scheme() -> None:
    from njit_auditor.web_url_fetch import FetchError, _validate_url

    with pytest.raises(FetchError, match="http"):
        _validate_url("file:///etc/passwd")


def test_url_fetch_rejects_ftp_scheme() -> None:
    from njit_auditor.web_url_fetch import FetchError, _validate_url

    with pytest.raises(FetchError, match="http"):
        _validate_url("ftp://example.com/thesis.pdf")


def test_url_fetch_rejects_empty_host() -> None:
    from njit_auditor.web_url_fetch import FetchError, _validate_url

    with pytest.raises(FetchError):
        _validate_url("http:///x.pdf")


def test_url_fetch_rejects_localhost() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError, match="localhost"):
        _check_host("localhost")


def test_url_fetch_rejects_loopback_ip() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("127.0.0.1")


def test_url_fetch_rejects_private_class_a() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("10.0.0.1")


def test_url_fetch_rejects_private_class_c() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("192.168.1.100")


def test_url_fetch_rejects_link_local() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("169.254.0.1")


def test_url_fetch_rejects_private_via_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    from njit_auditor.web_url_fetch import FetchError, _check_host

    original = socket.getaddrinfo

    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> Any:
        if "evil" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.10.10", 0))]
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(FetchError, match="private"):
        _check_host("evil.internal.example.com")


def test_url_fetch_ip_is_private_v4() -> None:
    from njit_auditor.web_url_fetch import _ip_is_private

    assert _ip_is_private("10.10.10.10") is True
    assert _ip_is_private("172.20.0.1") is True
    assert _ip_is_private("192.168.0.1") is True
    assert _ip_is_private("127.0.0.1") is True
    assert _ip_is_private("169.254.1.1") is True


def test_url_fetch_ip_is_private_v6() -> None:
    from njit_auditor.web_url_fetch import _ip_is_private

    assert _ip_is_private("::1") is True
    assert _ip_is_private("fe80::1") is True
    assert _ip_is_private("fc00::1") is True


def test_url_fetch_public_ip_not_private() -> None:
    from njit_auditor.web_url_fetch import _ip_is_private

    assert _ip_is_private("8.8.8.8") is False
    assert _ip_is_private("1.1.1.1") is False


# ---------------------------------------------------------------------------
# /audits/url route tests
# ---------------------------------------------------------------------------


def test_index_contains_url_form(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert b"pdf_url" in resp.content
    assert b"/audits/url" in resp.content


def test_url_audit_missing_url_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post("/audits/url", data={}, follow_redirects=False)
    assert resp.status_code == 400
    assert b"PDF URL" in resp.content or b"provide" in resp.content.lower()


def test_url_audit_whitespace_url_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post("/audits/url", data={"pdf_url": "   "}, follow_redirects=False)
    assert resp.status_code == 400


def test_url_audit_non_http_scheme_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits/url",
        data={"pdf_url": "file:///etc/passwd"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert b"http" in resp.content.lower()


def test_url_audit_localhost_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits/url",
        data={"pdf_url": "http://localhost/thesis.pdf"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_url_audit_loopback_ip_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits/url",
        data={"pdf_url": "http://127.0.0.1/thesis.pdf"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_url_audit_private_ip_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits/url",
        data={"pdf_url": "http://10.0.0.1/thesis.pdf"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_url_audit_resolves_to_private_rejected(
    client: tuple[TestClient, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    import socket

    original = socket.getaddrinfo

    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> Any:
        if "evil" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.99.1", 0))]
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    c, _ = client
    resp = c.post(
        "/audits/url",
        data={"pdf_url": "http://evil.internal.corp/thesis.pdf"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_url_audit_valid_public_url_creates_job(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client

    def _fake_fetch(url: str, dest: Path, max_bytes: int) -> None:
        dest.write_bytes(_MINIMAL_PDF)

    with patch.object(wa, "fetch_pdf_url", _fake_fetch):
        with patch.object(wa, "_run_audit_task", lambda job_id: None):
            resp = c.post(
                "/audits/url",
                data={"pdf_url": "https://example.com/thesis.pdf"},
                follow_redirects=False,
            )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/audits/")


def test_url_audit_fetch_error_shows_error(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    from njit_auditor.web_url_fetch import FetchError

    def _raise(url: str, dest: Path, max_bytes: int) -> None:
        raise FetchError("The URL does not point to a valid PDF file.")

    with patch.object(wa, "fetch_pdf_url", _raise):
        resp = c.post(
            "/audits/url",
            data={"pdf_url": "https://example.com/fake.bin"},
            follow_redirects=False,
        )
    assert resp.status_code == 400
    assert b"does not point to a valid PDF" in resp.content


def test_url_audit_oversized_shows_error(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    from njit_auditor.web_url_fetch import FetchError

    def _raise(url: str, dest: Path, max_bytes: int) -> None:
        raise FetchError("Download exceeds the maximum allowed size.")

    with patch.object(wa, "fetch_pdf_url", _raise):
        resp = c.post(
            "/audits/url",
            data={"pdf_url": "https://example.com/huge.pdf"},
            follow_redirects=False,
        )
    assert resp.status_code == 400
    assert b"exceeds" in resp.content.lower()


def test_url_audit_job_download_json(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """URL-created job uses same download endpoints as file-upload jobs."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/json")
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data


def test_url_audit_job_download_markdown(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/markdown")
    assert resp.status_code == 200
    ct = resp.headers["content-type"]
    assert "text/markdown" in ct or "text/plain" in ct


def test_url_audit_fetch_error_cleans_up_dir(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Failed URL fetch removes the job directory (no orphaned dirs)."""
    c, wa = client
    from njit_auditor.web_url_fetch import FetchError

    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])

    def _raise(url: str, dest: Path, max_bytes: int) -> None:
        raise FetchError("not a PDF")

    with patch.object(wa, "fetch_pdf_url", _raise):
        c.post(
            "/audits/url",
            data={"pdf_url": "https://example.com/fake.bin"},
            follow_redirects=False,
        )

    if runtime_dir.exists():
        job_dirs = list(runtime_dir.iterdir())
        # Any dir left should have at least upload.pdf (a completed job from earlier)
        for jdir in job_dirs:
            assert (jdir / "upload.pdf").exists(), f"Orphaned dir without upload: {jdir}"


def test_runtime_files_not_in_ls_files(tmp_path: Path) -> None:
    import subprocess

    repo_root = Path(__file__).parent.parent
    result = subprocess.run(
        ["git", "ls-files", ".runtime"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.stdout.strip() == "", f"Runtime files tracked by git: {result.stdout}"


# ---------------------------------------------------------------------------
# Built-in sample registry unit tests (web_samples.py)
# ---------------------------------------------------------------------------


def test_web_samples_reject_unknown_id() -> None:
    from njit_auditor.web_samples import get_builtin_sample

    with pytest.raises(ValueError, match="Unknown sample ID"):
        get_builtin_sample("nonexistent_id_xyz")


def test_web_samples_path_traversal_rejected() -> None:
    from njit_auditor.web_samples import get_builtin_sample

    for bad_id in ["../../etc/passwd", "../secret", "..", "data/raw/ester/x.pdf"]:
        with pytest.raises(ValueError):
            get_builtin_sample(bad_id)


def test_web_samples_list_filters_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)
    (fake_dir / "exists.pdf").write_bytes(b"%PDF-1.4\n")

    fake_curated = [
        ws.SampleInfo("test_exists", "Exists", "data/raw/ester/exists.pdf"),
        ws.SampleInfo("test_missing", "Missing", "data/raw/ester/gone.pdf"),
    ]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    result = ws.list_builtin_samples()
    ids = [s.sample_id for s in result]
    assert "test_exists" in ids
    assert "test_missing" not in ids


def test_web_samples_copy_writes_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)
    src = fake_dir / "sample.pdf"
    src.write_bytes(b"%PDF-1.4\n%%EOF\n")

    fake_curated = [ws.SampleInfo("test_copy", "Copy test", "data/raw/ester/sample.pdf")]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    dest = tmp_path / "out.pdf"
    ws.copy_builtin_sample_to_job("test_copy", dest)
    assert dest.exists()
    assert dest.read_bytes().startswith(b"%PDF")


def test_web_samples_copy_rejects_bad_magic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)
    src = fake_dir / "notapdf.pdf"
    src.write_bytes(b"NOTPDF\n")

    fake_curated = [ws.SampleInfo("test_badpdf", "Bad PDF", "data/raw/ester/notapdf.pdf")]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    dest = tmp_path / "out.pdf"
    with pytest.raises(ValueError, match="valid PDF"):
        ws.copy_builtin_sample_to_job("test_badpdf", dest)


def test_web_samples_copy_raises_for_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)

    fake_curated = [ws.SampleInfo("test_gone", "Gone", "data/raw/ester/gone.pdf")]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    dest = tmp_path / "out.pdf"
    with pytest.raises(FileNotFoundError):
        ws.copy_builtin_sample_to_job("test_gone", dest)


# ---------------------------------------------------------------------------
# /audits/sample route tests
# ---------------------------------------------------------------------------


def _fake_sample_info() -> Any:
    from njit_auditor.web_samples import SampleInfo

    return SampleInfo(
        sample_id="ester_sample_a",
        label="Sample A — first review (EF-annotated)",
        rel_path="data/raw/ester/250218 Cibaku Elson First Review.pdf",
    )


def test_index_contains_sample_form(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        resp = c.get("/")
    assert b"sample_id" in resp.content
    assert b"/audits/sample" in resp.content


def test_index_shows_three_input_methods(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        resp = c.get("/")
    # File upload
    assert b'type="file"' in resp.content
    # URL input
    assert b"pdf_url" in resp.content
    # Sample dropdown
    assert b"sample_id" in resp.content


def test_sample_audit_missing_sample_id_rejected(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        resp = c.post("/audits/sample", data={}, follow_redirects=False)
    assert resp.status_code == 400
    assert b"select" in resp.content.lower() or b"sample" in resp.content.lower()


def test_sample_audit_empty_sample_id_rejected(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        resp = c.post("/audits/sample", data={"sample_id": "   "}, follow_redirects=False)
    assert resp.status_code == 400


def test_sample_audit_unknown_sample_id_rejected(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        resp = c.post("/audits/sample", data={"sample_id": "bad_id_xyz"}, follow_redirects=False)
    assert resp.status_code == 400
    assert b"Unknown" in resp.content or b"invalid" in resp.content.lower()


def test_sample_audit_path_traversal_rejected(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    for bad_id in ["../../etc/passwd", "../secret", "data/raw/ester/x.pdf"]:
        with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
            resp = c.post(
                "/audits/sample",
                data={"sample_id": bad_id},
                follow_redirects=False,
            )
        assert resp.status_code == 400, f"Expected 400 for bad_id={bad_id!r}"


def test_sample_audit_valid_sample_creates_job(client: tuple[TestClient, Any]) -> None:
    c, wa = client

    def fake_copy(sample_id: str, dest: Path) -> None:
        dest.write_bytes(_MINIMAL_PDF)

    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        with patch.object(wa, "get_builtin_sample", lambda sid: _fake_sample_info()):
            with patch.object(wa, "copy_builtin_sample_to_job", fake_copy):
                with patch.object(wa, "_run_audit_task", lambda job_id: None):
                    resp = c.post(
                        "/audits/sample",
                        data={"sample_id": "ester_sample_a"},
                        follow_redirects=False,
                    )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/audits/")


def test_sample_audit_uses_runtime_dir(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    created_dirs: list[Path] = []

    def fake_copy(sample_id: str, dest: Path) -> None:
        created_dirs.append(dest.parent)
        dest.write_bytes(_MINIMAL_PDF)

    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        with patch.object(wa, "get_builtin_sample", lambda sid: _fake_sample_info()):
            with patch.object(wa, "copy_builtin_sample_to_job", fake_copy):
                with patch.object(wa, "_run_audit_task", lambda job_id: None):
                    c.post(
                        "/audits/sample",
                        data={"sample_id": "ester_sample_a"},
                        follow_redirects=False,
                    )

    runtime_root = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    assert len(created_dirs) == 1
    assert str(created_dirs[0]).startswith(str(runtime_root))


def test_sample_audit_redirects_to_job_page(client: tuple[TestClient, Any]) -> None:
    c, wa = client

    def fake_copy(sample_id: str, dest: Path) -> None:
        dest.write_bytes(_MINIMAL_PDF)

    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        with patch.object(wa, "get_builtin_sample", lambda sid: _fake_sample_info()):
            with patch.object(wa, "copy_builtin_sample_to_job", fake_copy):
                with patch.object(wa, "_run_audit_task", lambda job_id: None):
                    resp = c.post(
                        "/audits/sample",
                        data={"sample_id": "ester_sample_a"},
                        follow_redirects=True,
                    )
    assert resp.status_code == 200
    assert b"Audit" in resp.content


def test_sample_audit_missing_file_shows_error(client: tuple[TestClient, Any]) -> None:
    c, wa = client

    def raise_fnf(sample_id: str, dest: Path) -> None:
        raise FileNotFoundError("Sample file not found on this server.")

    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        with patch.object(wa, "get_builtin_sample", lambda sid: _fake_sample_info()):
            with patch.object(wa, "copy_builtin_sample_to_job", raise_fnf):
                resp = c.post(
                    "/audits/sample",
                    data={"sample_id": "ester_sample_a"},
                    follow_redirects=False,
                )
    assert resp.status_code == 400
    assert b"not available" in resp.content or b"not found" in resp.content.lower()


def test_sample_audit_invalid_pdf_shows_error(client: tuple[TestClient, Any]) -> None:
    c, wa = client

    def raise_val(sample_id: str, dest: Path) -> None:
        raise ValueError("Sample file is not a valid PDF.")

    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        with patch.object(wa, "get_builtin_sample", lambda sid: _fake_sample_info()):
            with patch.object(wa, "copy_builtin_sample_to_job", raise_val):
                resp = c.post(
                    "/audits/sample",
                    data={"sample_id": "ester_sample_a"},
                    follow_redirects=False,
                )
    assert resp.status_code == 400
    assert b"valid PDF" in resp.content or b"PDF" in resp.content


def test_sample_job_download_json(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    """Sample-created job uses same download endpoints as file-upload jobs."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/json")
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data


def test_sample_job_download_markdown(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/markdown")
    assert resp.status_code == 200
    ct = resp.headers["content-type"]
    assert "text/markdown" in ct or "text/plain" in ct


def test_sample_audit_no_private_text_in_response(client: tuple[TestClient, Any]) -> None:
    """Error responses must not contain dissertation content — only UI text."""
    c, wa = client
    with patch.object(wa, "list_builtin_samples", lambda: [_fake_sample_info()]):
        resp = c.post("/audits/sample", data={"sample_id": "bad_id_xyz"}, follow_redirects=False)
    assert resp.status_code == 400
    # Response should be a normal HTML page with a short error message
    assert b"<html" in resp.content or b"<!DOCTYPE" in resp.content
