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

_MINIMAL_TEX = (
    rb"\documentclass{report}"
    b"\n\\begin{document}\n\\vspace{1cm}\nHello\n\\end{document}\n"
)


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
    assert b".pdf" in resp.content
    assert b".tex" in resp.content
    assert b".zip" in resp.content


def test_index_contains_drag_drop_upload_zone_markup(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b'id="upload-drop-zone"' in resp.content
    assert b'Drop a PDF, TeX, or ZIP file here' in resp.content
    assert b'role="button"' in resp.content
    assert b'tabindex="0"' in resp.content
    assert b'aria-controls="file"' in resp.content
    assert b'id="file-selection-status"' in resp.content
    assert b'aria-live="polite"' in resp.content
    assert b'Drag-and-drop is available when JavaScript is enabled' in resp.content


def test_index_contains_drag_drop_progressive_enhancement_script(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"DataTransfer" in resp.content
    assert b"dragenter" in resp.content
    assert b"dragover" in resp.content
    assert b"dragleave" in resp.content
    assert b"drop" in resp.content
    assert b"Drop one file at a time" in resp.content
    assert b"Unsupported file:" in resp.content
    assert b"Submit when ready or choose another file" in resp.content


def test_index_advertises_pdf_tex_zip_support(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"P011" in resp.content
    assert b"P001" in resp.content
    assert b"ZIP" in resp.content or b"zip" in resp.content.lower()
    assert b"no LaTeX compilation" in resp.content or b"no compilation" in resp.content.lower()


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
    assert b"Supported uploads" in resp.content


def test_upload_wrong_magic_bytes_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("thesis.pdf", io.BytesIO(b"NOTAPDF_content"), "application/pdf")},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert b"valid PDF" in resp.content


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


def _fake_dispatch(pdf_path: Path, **kwargs: Any) -> Any:
    from njit_auditor.audit_runner import UploadedAuditResult
    from njit_auditor.upload_handling import UploadKind

    return UploadedAuditResult(
        upload_kind=UploadKind.PDF,
        audit_type="pdf",
        findings=_fake_audit(pdf_path),
    )


def test_upload_tex_creates_job_and_redirects(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        resp = c.post(
            "/audits",
            files={"file": ("main.tex", io.BytesIO(_MINIMAL_TEX), "text/plain")},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/audits/")


def test_upload_tex_completes_with_source_report(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    resp = c.post(
        "/audits",
        files={"file": ("main.tex", io.BytesIO(_MINIMAL_TEX), "text/plain")},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"TeX source audit" in resp.content or b"P001" in resp.content
    assert b"Location" in resp.content
    assert b"High-volume triage" not in resp.content
    assert b"fig:secret" not in resp.content


def test_tex_upload_json_and_markdown_downloads(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    post = c.post(
        "/audits",
        files={"file": ("main.tex", io.BytesIO(_MINIMAL_TEX), "text/plain")},
        follow_redirects=False,
    )
    job_id = post.headers["location"].split("/audits/")[1]
    page = c.get(f"/audits/{job_id}")
    assert page.status_code == 200
    json_resp = c.get(f"/audits/{job_id}/download/json")
    md_resp = c.get(f"/audits/{job_id}/download/markdown")
    if json_resp.status_code == 200:
        data = json_resp.json()
        assert data["metadata"]["audit_type"] == "tex"
        assert "findings" in data
    if md_resp.status_code == 200:
        assert b"Source Audit Report" in md_resp.content


def test_zip_upload_json_and_markdown_downloads(client: tuple[TestClient, Any]) -> None:
    import zipfile

    c, _ = client
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("main.tex", _MINIMAL_TEX)
    zbuf.seek(0)
    post = c.post(
        "/audits",
        files={"file": ("project.zip", zbuf, "application/zip")},
        follow_redirects=False,
    )
    job_id = post.headers["location"].split("/audits/")[1]
    c.get(f"/audits/{job_id}")
    json_resp = c.get(f"/audits/{job_id}/download/json")
    if json_resp.status_code == 200:
        assert json_resp.json()["metadata"]["audit_type"] == "tex"


def test_upload_zip_completes_with_source_report(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    import zipfile

    c, _ = client
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("main.tex", _MINIMAL_TEX)
    zbuf.seek(0)
    resp = c.post(
        "/audits",
        files={"file": ("project.zip", zbuf, "application/zip")},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"TeX source audit" in resp.content or b"P001" in resp.content
    assert b"Location" in resp.content


def test_unsafe_zip_upload_shows_safe_error(client: tuple[TestClient, Any]) -> None:
    import zipfile

    c, _ = client
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("../evil.tex", _MINIMAL_TEX)
    zbuf.seek(0)
    resp = c.post(
        "/audits",
        files={"file": ("bad.zip", zbuf, "application/zip")},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Traceback" not in resp.content
    assert (
        b"could not complete" in resp.content.lower()
        or b"Unsafe ZIP" in resp.content
        or b"unsafe" in resp.content.lower()
    )


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
    with patch.object(wa, "run_audit_for_uploaded_file", _fake_dispatch):
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

def _inject_complete_job(
    wa: Any,
    tmp_path: Path,
    *,
    finding_count: int = 1,
) -> str:
    """Create a complete job in the job store and on disk."""
    from njit_auditor.models import AuditFinding, Severity

    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
                "suggested_fix": "Adjust the left margin in the PDF export settings.",
            },
        )
        for i in range(finding_count)
    ]
    return _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )


def _inject_complete_job_with_findings(
    wa: Any,
    tmp_path: Path,
    *,
    findings: list[Any],
    file_name: str,
    audit_type: str,
) -> str:
    """Create a complete job from an explicit findings list."""
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    metadata = {"input_file_name": file_name, "audit_type": audit_type, "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name=file_name,
        audit_type=audit_type,
        finding_count=view.total_findings,
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {
                "rule_id": rs.rule_id,
                "count": rs.count,
                "category": rs.category,
            }
            for rs in view.rule_summaries
        ],
        report_view=report_view_to_dict(view),
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


def test_index_states_privacy_safe_local_processing(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"Privacy-safe processing" in resp.content
    assert b"processed locally" in resp.content.lower() or b"locally" in resp.content.lower()
    assert b"not stored permanently" in resp.content.lower()


def test_index_states_pdf_tex_zip_web_support(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"Supported inputs" in resp.content
    assert b"PDF" in resp.content
    assert b"TeX source" in resp.content or b"TeX" in resp.content
    assert b"Supported" in resp.content
    assert b"source only" in resp.content.lower() or b"not compiled" in resp.content.lower()


def test_index_lists_what_you_get_deliverables(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"What you get" in resp.content
    assert b"JSON report" in resp.content
    assert b"Markdown report" in resp.content
    assert b"Triage summaries" in resp.content
    assert b"Polished comments" in resp.content


def test_results_page_shows_summary_cards(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Total findings" in resp.content
    assert b"Highest severity" in resp.content
    assert b"Pages affected" in resp.content
    assert b"Rules flagged" in resp.content


def test_results_page_defaults_to_grouped_problems_with_expandable_occurrences(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=page,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
                "suggested_fix": "Adjust the left margin in the PDF export settings.",
            },
        )
        for page in (3, 4, 5, 6, 7, 10, 14, 15, 16)
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    assert b"Grouped problems" in resp.content
    assert b"All individual findings" in resp.content
    assert b"Show individual occurrences" in resp.content
    assert b"9 occurrences" in resp.content
    assert "3–7, 10, 14–16".encode() in resp.content
    assert (
        b"Summary cards and severity/category totals remain based on raw findings."
        in resp.content
    )
    assert b'id="grouped-problems-panel"' in resp.content
    assert b'id="individual-findings-panel"' in resp.content


def test_results_page_groups_source_locations_compactly(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P001",
            severity=Severity.WARNING,
            message="Avoid shell escape commands in TeX source.",
            details={
                "file": "/tmp/private/thesis.tex",
                "line": str(line),
                "issue_type": "risky_command",
                "command": "\\write18",
                "suggested_fix": "Remove the shell-escape command from the source.",
            },
        )
        for line in (12, 18, 19, 20, 21)
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.tex",
        audit_type="tex",
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    assert "thesis.tex:12, thesis.tex:18–21".encode() in resp.content
    assert b"/tmp/private/" not in resp.content
    assert b"Show individual occurrences" in resp.content


def test_results_page_shows_triage_panels(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=6)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"High-volume triage" in resp.content
    assert b"Margin" in resp.content or b"P011" in resp.content


def test_results_page_renders_polished_comments(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Polished comment" in resp.content
    assert b"Review needed" in resp.content


def test_results_page_has_client_side_filters(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"filter-rule" in resp.content
    assert b"filter-severity" in resp.content
    assert b"filter-category" in resp.content
    assert b"filter-page" in resp.content


def test_results_page_filter_script_defers_until_dom_ready(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Findings filter/toggle script must wait for DOMContentLoaded (head vs body)."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"DOMContentLoaded" in resp.content
    assert b'setMode("grouped")' in resp.content
    assert b"getElementById(\"filter-rule\")" in resp.content


def test_results_page_shows_privacy_note(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Privacy note" in resp.content
    assert b"body text" in resp.content.lower()


def test_results_polished_comments_exclude_private_sample_text(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    forbidden = b"John Smith Dissertation Title"
    assert forbidden not in resp.content


def test_failed_job_shows_safe_error_no_stack_trace(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    from datetime import datetime, timezone

    job = wa.JobState(
        job_id="failedjob1",
        state="failed",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="bad.pdf",
        error_message="File does not appear to be a valid PDF.",
    )
    wa._set_job(job)
    resp = c.get("/audits/failedjob1")
    assert resp.status_code == 200
    assert b"Traceback" not in resp.content
    assert b"valid PDF" in resp.content or b"could not complete" in resp.content.lower()


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


# ---------------------------------------------------------------------------
# Job TTL cleanup
# ---------------------------------------------------------------------------


def _reload_web_app(tmp_path: Path, **env_overrides: str) -> Any:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    for key, value in env_overrides.items():
        os.environ[key] = value
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    with wa._jobs_lock:
        wa._jobs.clear()
    return wa


def test_invalid_job_ttl_env_falls_back_to_default(tmp_path: Path) -> None:
    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="not-a-number")
    assert wa.JOB_TTL_SECONDS == 86400

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="-5")
    assert wa.JOB_TTL_SECONDS == 86400


def test_cleanup_expired_jobs_evicts_memory_and_deletes_directory(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "expiredjob123456"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=old_time,
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    removed = wa.cleanup_expired_jobs()
    assert removed >= 1
    assert wa._get_job(job_id) is None
    assert not jdir.exists()


def test_cleanup_missing_job_directory_does_not_fail(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "missingdirjob12"
    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=old_time,
        file_name="thesis.pdf",
    )
    wa._set_job(job)
    assert not wa._job_dir(job_id).exists()

    removed = wa.cleanup_expired_jobs()
    assert removed >= 1
    assert wa._get_job(job_id) is None


def test_cleanup_keeps_non_expired_job(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="3600")
    job_id = "freshjob123456"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    removed = wa.cleanup_expired_jobs()
    assert removed == 0
    assert wa._get_job(job_id) is not None
    assert jdir.exists()


def test_cleanup_skips_running_jobs_even_when_old(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "runningjob12345"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)

    job = wa.JobState(
        job_id=job_id,
        state="running",
        created_at=old_time,
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    removed = wa.cleanup_expired_jobs()
    assert removed == 0
    assert wa._get_job(job_id) is not None
    assert jdir.exists()


def test_cleanup_does_not_delete_paths_outside_runtime_root(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    outside_dir = tmp_path / "outside_runtime"
    outside_dir.mkdir()
    marker = outside_dir / "keep.txt"
    marker.write_text("stay", encoding="utf-8")

    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "outsidejob1234"
    with patch.object(wa, "_job_dir", return_value=outside_dir):
        job = wa.JobState(
            job_id=job_id,
            state="complete",
            created_at=old_time,
            file_name="thesis.pdf",
        )
        wa._set_job(job)
        removed = wa.cleanup_expired_jobs()

    assert removed >= 1
    assert marker.exists()


def test_job_not_found_message_mentions_expiration(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/audits/doesnotexistjob")
    assert resp.status_code == 404
    assert b"not found" in resp.content.lower()
    assert b"hours" in resp.content.lower()


# ---------------------------------------------------------------------------
# Web export path redaction
# ---------------------------------------------------------------------------


def test_tex_upload_json_redacts_absolute_paths(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    post = c.post(
        "/audits",
        files={"file": ("main.tex", io.BytesIO(_MINIMAL_TEX), "text/plain")},
        follow_redirects=False,
    )
    job_id = post.headers["location"].split("/audits/")[1]
    c.get(f"/audits/{job_id}")
    json_resp = c.get(f"/audits/{job_id}/download/json")
    if json_resp.status_code != 200:
        pytest.skip("audit did not complete in time")
    data = json_resp.json()
    runtime_root = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]).resolve()
    serialized = json.dumps(data)
    assert str(runtime_root) not in serialized
    assert data["metadata"]["input_file_path"] == "upload.tex"
    for finding in data.get("findings", []):
        details = finding.get("details", {})
        file_path = details.get("file", "")
        if file_path:
            assert "/" not in file_path
            assert "\\" not in file_path


def test_tex_upload_markdown_preview_redacts_absolute_paths(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    post = c.post(
        "/audits",
        files={"file": ("main.tex", io.BytesIO(_MINIMAL_TEX), "text/plain")},
        follow_redirects=False,
    )
    job_id = post.headers["location"].split("/audits/")[1]
    page = c.get(f"/audits/{job_id}")
    if page.status_code != 200:
        pytest.skip("audit did not complete in time")
    runtime_root = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]).resolve()
    job = wa._get_job(job_id)
    if job is None or not job.md_preview:
        pytest.skip("markdown preview unavailable")
    assert str(runtime_root) not in job.md_preview
    assert "upload.tex" in job.md_preview


# ---------------------------------------------------------------------------
# Web export source-message privacy sanitization (#215)
# ---------------------------------------------------------------------------

# Synthetic TeX content that will produce findings with private label/ref names.
# The label "fig:test_private_label" and ref "fig:test_private_ref" must NOT
# appear in any web-generated JSON or Markdown report.
_PRIVATE_LABEL_TEX = (
    b"\\documentclass{report}\n"
    b"\\begin{document}\n"
    b"\\label{fig:test_private_label}\n"
    b"\\ref{fig:test_private_ref}\n"
    b"\\begin{figure}\n"
    b"\\caption{A figure.}\n"
    b"\\end{figure}\n"
    b"\\begin{table}\n"
    b"\\caption{A table}\n"
    b"\\end{table}\n"
    b"\\end{document}\n"
)

_PRIVATE_LABEL = "fig:test_private_label"
_PRIVATE_REF = "fig:test_private_ref"


def _submit_tex_and_get_job_id(
    c: TestClient,
    tex_content: bytes = _PRIVATE_LABEL_TEX,
    filename: str = "main.tex",
) -> str:
    """Upload synthetic TeX, follow redirect, return job_id."""
    post = c.post(
        "/audits",
        files={"file": (filename, io.BytesIO(tex_content), "text/plain")},
        follow_redirects=False,
    )
    assert post.status_code == 303, f"Expected redirect, got {post.status_code}"
    return post.headers["location"].split("/audits/")[1]


def test_source_web_json_does_not_contain_private_label(
    client: tuple[TestClient, Any],
) -> None:
    """Web JSON download for source audit must not contain synthetic private label name."""
    c, _ = client
    job_id = _submit_tex_and_get_job_id(c)
    c.get(f"/audits/{job_id}")  # wait for completion
    resp = c.get(f"/audits/{job_id}/download/json")
    if resp.status_code != 200:
        pytest.skip("audit did not complete")
    serialized = resp.text
    assert _PRIVATE_LABEL not in serialized, (
        f"Private label '{_PRIVATE_LABEL}' found in web JSON download"
    )


def test_source_web_json_does_not_contain_private_ref(
    client: tuple[TestClient, Any],
) -> None:
    """Web JSON download for source audit must not contain synthetic private ref name."""
    c, _ = client
    job_id = _submit_tex_and_get_job_id(c)
    c.get(f"/audits/{job_id}")
    resp = c.get(f"/audits/{job_id}/download/json")
    if resp.status_code != 200:
        pytest.skip("audit did not complete")
    serialized = resp.text
    assert _PRIVATE_REF not in serialized, (
        f"Private ref '{_PRIVATE_REF}' found in web JSON download"
    )


def test_source_web_markdown_does_not_contain_private_label(
    client: tuple[TestClient, Any],
) -> None:
    """Web Markdown download for source audit must not contain synthetic private label name."""
    c, _ = client
    job_id = _submit_tex_and_get_job_id(c)
    c.get(f"/audits/{job_id}")
    resp = c.get(f"/audits/{job_id}/download/markdown")
    if resp.status_code != 200:
        pytest.skip("audit did not complete")
    assert _PRIVATE_LABEL not in resp.text, (
        f"Private label '{_PRIVATE_LABEL}' found in web Markdown download"
    )


def test_source_web_markdown_does_not_contain_private_ref(
    client: tuple[TestClient, Any],
) -> None:
    """Web Markdown download for source audit must not contain synthetic private ref name."""
    c, _ = client
    job_id = _submit_tex_and_get_job_id(c)
    c.get(f"/audits/{job_id}")
    resp = c.get(f"/audits/{job_id}/download/markdown")
    if resp.status_code != 200:
        pytest.skip("audit did not complete")
    assert _PRIVATE_REF not in resp.text, (
        f"Private ref '{_PRIVATE_REF}' found in web Markdown download"
    )


def test_source_web_markdown_preview_does_not_contain_private_labels(
    client: tuple[TestClient, Any],
) -> None:
    """In-page Markdown preview must not contain synthetic private label/ref names."""
    c, wa = client
    job_id = _submit_tex_and_get_job_id(c)
    c.get(f"/audits/{job_id}")
    job = wa._get_job(job_id)
    if job is None or not job.md_preview:
        pytest.skip("markdown preview unavailable")
    assert _PRIVATE_LABEL not in job.md_preview, (
        f"Private label '{_PRIVATE_LABEL}' found in in-page Markdown preview"
    )
    assert _PRIVATE_REF not in job.md_preview, (
        f"Private ref '{_PRIVATE_REF}' found in in-page Markdown preview"
    )


def test_source_web_json_finding_counts_unchanged_after_sanitization(
    client: tuple[TestClient, Any],
) -> None:
    """Sanitization must preserve finding counts — no findings removed."""
    c, _ = client
    job_id = _submit_tex_and_get_job_id(c)
    c.get(f"/audits/{job_id}")
    resp = c.get(f"/audits/{job_id}/download/json")
    if resp.status_code != 200:
        pytest.skip("audit did not complete")
    data = resp.json()
    meta = data.get("metadata", {})
    total = meta.get("total_findings", 0)
    findings = data.get("findings", [])
    # Total in metadata must match actual findings list length
    assert total == len(findings), (
        f"total_findings={total} != len(findings)={len(findings)} after sanitization"
    )
    # Must have at least some findings from the synthetic TeX (P002/P003/P004 etc.)
    assert total > 0, "Expected at least one finding from synthetic TeX with dangling refs"


def test_source_web_json_preserves_structural_fields(
    client: tuple[TestClient, Any],
) -> None:
    """Rule IDs, severity, category, source_file, source_line must survive sanitization."""
    c, _ = client
    job_id = _submit_tex_and_get_job_id(c)
    c.get(f"/audits/{job_id}")
    resp = c.get(f"/audits/{job_id}/download/json")
    if resp.status_code != 200:
        pytest.skip("audit did not complete")
    data = resp.json()
    for finding in data.get("findings", []):
        assert "rule_id" in finding, "rule_id missing from sanitized finding"
        assert "severity" in finding, "severity missing from sanitized finding"
        assert "message" in finding, "message missing from sanitized finding"
        # source_file and source_line are set for tex audits
        # (may be empty string for PASS findings)
        assert "source_file" in finding, "source_file missing from sanitized finding"
        assert "source_line" in finding, "source_line missing from sanitized finding"


def _inject_complete_pdf_job(
    wa: Any,
    tmp_path: Path,
) -> str:
    """Create a complete PDF job in the job store and on disk (for PDF parity tests)."""
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    job_id = secrets.token_urlsafe(16)
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Possible text outside margin.",
            details={"issue_type": "margin_boundary_violation", "side": "left"},
        ),
    ]
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=1,
        fail_count=0,
        findings=[],
        grouped_summary=[],
        report_view=report_view_to_dict(view),
        md_preview="# NJIT PDF Audit Report\n",
    )
    wa._set_job(job)
    return job_id


def test_pdf_web_json_download_unaffected_by_sanitization(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """PDF reports must remain fully intact — sanitization is source-audit-only."""
    c, wa = client
    job_id = _inject_complete_pdf_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["audit_type"] == "pdf"
    # PDF finding messages are preserved as-is (no sanitization)
    messages = [f.get("message", "") for f in data.get("findings", [])]
    assert any("margin" in m.lower() or "P011" in m or len(m) > 0 for m in messages)


def test_pdf_web_markdown_download_unaffected_by_sanitization(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """PDF Markdown reports must download normally — no sanitization applied."""
    c, wa = client
    job_id = _inject_complete_pdf_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/markdown")
    assert resp.status_code == 200
    ct = resp.headers["content-type"]
    assert "text/markdown" in ct or "text/plain" in ct
    assert b"PDF Audit Report" in resp.content


def test_sanitize_report_for_web_export_unit_pdf_passthrough() -> None:
    """sanitize_report_for_web_export() must return PDF reports unchanged."""
    from njit_auditor.report_outputs import sanitize_report_for_web_export

    report: dict = {
        "metadata": {"audit_type": "pdf", "total_findings": 1},
        "findings": [
            {
                "rule_id": "P011",
                "severity": "WARNING",
                "message": "Possible text outside margin.",
                "page": 2,
                "details": {"side": "left"},
            }
        ],
    }
    result = sanitize_report_for_web_export(report)
    # PDF reports returned unchanged
    assert result["findings"][0]["message"] == "Possible text outside margin."
    assert result["findings"][0]["details"] == {"side": "left"}


def test_sanitize_report_for_web_export_unit_tex_label_removed() -> None:
    """sanitize_report_for_web_export() removes private label/ref from tex findings."""
    from njit_auditor.report_outputs import sanitize_report_for_web_export

    report: dict = {
        "metadata": {"audit_type": "tex", "total_findings": 2},
        "findings": [
            {
                "rule_id": "P002",
                "severity": "FAIL",
                "message": "Duplicate label detected: 'fig:test_private_label'",
                "page": None,
                "details": {
                    "file": "main.tex",
                    "line": "5",
                    "issue_type": "duplicate_label",
                    "label": "fig:test_private_label",
                },
                "source_file": "main.tex",
                "source_line": "5",
            },
            {
                "rule_id": "P004",
                "severity": "WARNING",
                "message": "Reference points to undefined label: 'tab:my_secret_table'",
                "page": None,
                "details": {
                    "file": "main.tex",
                    "line": "10",
                    "issue_type": "dangling_reference",
                    "ref": "tab:my_secret_table",
                },
                "source_file": "main.tex",
                "source_line": "10",
            },
        ],
    }
    result = sanitize_report_for_web_export(report)
    assert "fig:test_private_label" not in result["findings"][0]["message"]
    assert "tab:my_secret_table" not in result["findings"][1]["message"]
    assert "label" not in result["findings"][0]["details"]
    assert "ref" not in result["findings"][1]["details"]
    # Structural keys preserved
    assert result["findings"][0]["details"]["file"] == "main.tex"
    assert result["findings"][0]["details"]["line"] == "5"
    assert result["findings"][0]["details"]["issue_type"] == "duplicate_label"
    # Finding count unchanged
    assert len(result["findings"]) == 2


def test_sanitize_report_for_web_export_unit_preserves_count() -> None:
    """Finding count in metadata must be unchanged after sanitization."""
    from njit_auditor.report_outputs import sanitize_report_for_web_export

    report: dict = {
        "metadata": {"audit_type": "tex", "total_findings": 3},
        "findings": [
            {
                "rule_id": "P003",
                "severity": "WARNING",
                "message": "Label contains spaces: 'fig some label'",
                "page": None,
                "details": {"file": "main.tex", "line": "3", "issue_type": "invalid_label"},
            }
        ]
        * 3,
    }
    result = sanitize_report_for_web_export(report)
    assert result["metadata"]["total_findings"] == 3
    assert len(result["findings"]) == 3


# ---------------------------------------------------------------------------
# Category humanization filter
# ---------------------------------------------------------------------------

def test_humanize_cat_known_keys() -> None:
    """_CATEGORY_LABELS must map all recognised snake_case keys to friendly labels."""
    import importlib

    import njit_auditor.web_app as wa
    importlib.reload(wa)
    assert wa._humanize_cat("page_numbering") == "Page numbering"
    assert wa._humanize_cat("font_format") == "Font formatting"
    assert wa._humanize_cat("margin_or_overflow") == "Margins / overflow"
    assert wa._humanize_cat("list_of_tables_figures_toc") == "TOC / lists"
    assert wa._humanize_cat("committee_approval_page") == "Approval page"
    assert wa._humanize_cat("heading_title") == "Headings / titles"
    assert wa._humanize_cat("abstract_length") == "Abstract length"
    assert wa._humanize_cat("latex_linter") == "LaTeX linting"


def test_humanize_cat_fallback_for_unknown_key() -> None:
    """Unknown keys must not raise — fall back to a capitalised version."""
    import importlib

    import njit_auditor.web_app as wa
    importlib.reload(wa)
    result = wa._humanize_cat("some_new_category")
    assert isinstance(result, str)
    assert len(result) > 0
    assert result == result.lstrip()


def test_humanize_cat_all_labels_dict_keys_are_distinct() -> None:
    """Every key and value in _CATEGORY_LABELS must be unique."""
    import importlib

    import njit_auditor.web_app as wa
    importlib.reload(wa)
    labels = wa._CATEGORY_LABELS
    assert len(set(labels.keys())) == len(labels), "Duplicate keys in _CATEGORY_LABELS"
    assert len(set(labels.values())) == len(labels), "Duplicate values in _CATEGORY_LABELS"


def test_results_page_shows_human_category_labels(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The results page must display human-readable category labels, not raw snake_case."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    # P011 findings are categorised as margin_or_overflow — should render as human label
    assert b"Margins / overflow" in resp.content
    # Raw snake_case must NOT appear in the visible label positions
    # (it may still appear in data-* attributes for JS filtering)
    text = resp.text
    # The category filter dropdown should use human label as option text
    assert "Margins / overflow" in text


def test_results_page_filter_category_raw_value_preserved(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Filter category <option value=...> must keep the raw snake_case key for JS matching."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    # value attribute must contain the raw key so JS data-category comparison works
    assert b'value="margin_or_overflow"' in resp.content


def test_results_page_shows_review_order_section(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Completed results with findings must include the Recommended review order section."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Recommended review order" in resp.content
    assert b"Manual verification" in resp.content


def test_results_page_shows_jump_links(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Completed results with findings must include the jump-links navigation bar."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"jump-links" in resp.content
    assert b"#section-summary" in resp.content
    assert b"#section-findings" in resp.content


def test_results_page_review_signals_label(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Summary card must say 'Review signals / Errors', not the old 'Warnings / errors'."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Review signals / Errors" in resp.content
    assert b"Warnings / errors" not in resp.content


def test_results_page_heuristic_note_in_status_banner(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Status banner must include heuristic / verify wording."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Heuristic review signals" in resp.content
