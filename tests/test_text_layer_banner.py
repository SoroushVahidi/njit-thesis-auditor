"""Tests for the scanned-PDF text-layer warning banner."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers shared across this module
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent / "fixtures" / "web_demo"
_REAL_PDF = _FIXTURES / "clean_minimal.pdf"


def _make_app(tmp_path: Path) -> tuple[Any, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return wa.app, wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    app, wa = _make_app(tmp_path)
    return TestClient(app, raise_server_exceptions=False), wa


def _image_only_pdf(path: Path) -> None:
    """Write a valid PDF with pages but no text content."""
    with pymupdf.open() as doc:
        for _ in range(3):
            doc.new_page()
        doc.save(str(path))


def _low_text_pdf(path: Path) -> None:
    """Write a PDF with a tiny amount of text (well under 100 chars/page)."""
    with pymupdf.open() as doc:
        for _ in range(3):
            page = doc.new_page()
            page.insert_text((72, 72), "Hi")  # 2 chars per page → 6 total < 300
        doc.save(str(path))


def _normal_pdf(path: Path) -> None:
    """Write a PDF with a normal amount of text (>= 100 chars per sampled page)."""
    lorem = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."
    )
    with pymupdf.open() as doc:
        for _ in range(3):
            page = doc.new_page()
            page.insert_text((72, 72), lorem)
        doc.save(str(path))


def _inject_job(
    wa: Any,
    tmp_path: Path,
    *,
    text_layer_quality: str = "",
    audit_type: str = "pdf",
) -> str:
    """Insert a complete JobState directly into the job store."""
    import secrets

    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    # Write minimal placeholder files the route expects
    (jdir / "upload.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (jdir / "report.json").write_text("{}", encoding="utf-8")
    (jdir / "report.md").write_text("# Report\n", encoding="utf-8")

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type=audit_type,
        finding_count=0,
        warn_count=0,
        fail_count=0,
        text_layer_quality=text_layer_quality,
    )
    wa._set_job(job)
    return job_id


# ---------------------------------------------------------------------------
# Unit tests for classify_pdf_text_layer
# ---------------------------------------------------------------------------


def test_classify_real_pdf_returns_text_layer_ok(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import classify_pdf_text_layer

    assert _REAL_PDF.exists(), f"Fixture missing: {_REAL_PDF}"
    result = classify_pdf_text_layer(_REAL_PDF)
    assert result == "text_layer_ok"


def test_classify_image_only_pdf(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import classify_pdf_text_layer

    pdf_path = tmp_path / "image_only.pdf"
    _image_only_pdf(pdf_path)
    assert classify_pdf_text_layer(pdf_path) == "image_only"


def test_classify_low_text_pdf(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import classify_pdf_text_layer

    pdf_path = tmp_path / "low_text.pdf"
    _low_text_pdf(pdf_path)
    assert classify_pdf_text_layer(pdf_path) == "low_text"


def test_classify_normal_synthetic_pdf(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import classify_pdf_text_layer

    pdf_path = tmp_path / "normal.pdf"
    _normal_pdf(pdf_path)
    assert classify_pdf_text_layer(pdf_path) == "text_layer_ok"


def test_classify_nonexistent_file_returns_empty(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import classify_pdf_text_layer

    result = classify_pdf_text_layer(tmp_path / "no_such_file.pdf")
    assert result == ""


def test_classify_non_pdf_file_returns_empty(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import classify_pdf_text_layer

    bad = tmp_path / "not_a_pdf.pdf"
    bad.write_bytes(b"This is not a PDF")
    result = classify_pdf_text_layer(bad)
    assert result == ""


def test_classify_issues_pdf_fixture_returns_ok(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import classify_pdf_text_layer

    issues_pdf = _FIXTURES / "issues_pdf.pdf"
    assert issues_pdf.exists(), f"Fixture missing: {issues_pdf}"
    assert classify_pdf_text_layer(issues_pdf) == "text_layer_ok"


# ---------------------------------------------------------------------------
# Banner rendering tests (via web client)
# ---------------------------------------------------------------------------


def test_no_banner_for_text_layer_ok(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="text_layer_ok")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Limited text layer" not in resp.content
    assert b"Very limited extractable text" not in resp.content


def test_no_banner_when_quality_is_empty(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Limited text layer" not in resp.content
    assert b"Very limited extractable text" not in resp.content


def test_image_only_banner_shown(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="image_only")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"no selectable text" in resp.content
    assert b"alert-warn" in resp.content


def test_low_text_banner_shown(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="low_text")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"very little selectable text" in resp.content
    assert b"alert-info" in resp.content


def test_image_only_banner_not_shown_for_low_text(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="low_text")
    resp = c.get(f"/audits/{job_id}")
    assert b"no selectable text" not in resp.content


def test_low_text_banner_not_shown_for_image_only(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="image_only")
    resp = c.get(f"/audits/{job_id}")
    assert b"Very limited extractable text" not in resp.content


def test_banner_absent_for_tex_audit(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="", audit_type="tex")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Limited text layer" not in resp.content


def test_audit_still_completes_with_image_only_quality(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="image_only")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"complete" in resp.content.lower()


def test_finding_count_unchanged_by_banner(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Banner is presentation-only: finding_count should remain 0 in the injected job."""
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="image_only")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    # The injected job has finding_count=0 — the banner should not inflate this
    job = wa._get_job(job_id)
    assert job is not None
    assert job.finding_count == 0


def test_banner_does_not_expose_pdf_content(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Banner text must not include any extracted PDF text."""
    c, wa = client
    job_id = _inject_job(wa, tmp_path, text_layer_quality="image_only")
    resp = c.get(f"/audits/{job_id}")
    # The banner does not include file content, raw text, or paths
    content = resp.content
    assert b"Lorem ipsum" not in content
    assert b"/home/" not in content
    assert b"upload.pdf" not in content
