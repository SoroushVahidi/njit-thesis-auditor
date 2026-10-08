"""A crashing PDF check is isolated on the web path and loud everywhere else."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient

from njit_auditor import audit_runner
from njit_auditor.audit_runner import (
    collect_pdf_layout_findings,
    run_audit_for_uploaded_file,
)
from njit_auditor.pdf_layout import load_pdf_layout


def _pdf_with_margin_overflow(path: Path) -> Path:
    """One synthetic page whose text starts inside the 1.5-inch left margin."""
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((20, 300), "Synthetic body text placed in the left margin.")
        doc.save(path)
    return path


def _boom(*_args: object, **_kwargs: object) -> list[Any]:
    raise RuntimeError("synthetic check failure")


@pytest.fixture()
def crashing_spacing_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit_runner, "check_pdf_spacing", _boom)


def test_default_run_still_raises(tmp_path: Path, crashing_spacing_check: None) -> None:
    pdf = _pdf_with_margin_overflow(tmp_path / "t.pdf")
    with pytest.raises(RuntimeError, match="synthetic check failure"):
        collect_pdf_layout_findings(load_pdf_layout(str(pdf)), pdf)
    with pytest.raises(RuntimeError, match="synthetic check failure"):
        run_audit_for_uploaded_file(pdf)


def test_isolated_run_logs_records_and_keeps_other_findings(
    tmp_path: Path, crashing_spacing_check: None, caplog: pytest.LogCaptureFixture
) -> None:
    pdf = _pdf_with_margin_overflow(tmp_path / "t.pdf")
    failures: list[str] = []
    with caplog.at_level(logging.ERROR, logger="njit_auditor.audit_runner"):
        findings = collect_pdf_layout_findings(
            load_pdf_layout(str(pdf)), pdf, check_failures=failures
        )
    assert failures == ["_boom"]
    assert any(f.rule_id == "P011" for f in findings)
    records = [r for r in caplog.records if "_boom" in r.getMessage()]
    assert records and records[0].exc_info is not None


def test_isolated_findings_match_strict_findings_when_nothing_fails(tmp_path: Path) -> None:
    pdf = _pdf_with_margin_overflow(tmp_path / "t.pdf")
    strict = collect_pdf_layout_findings(load_pdf_layout(str(pdf)), pdf)
    failures: list[str] = []
    isolated = collect_pdf_layout_findings(
        load_pdf_layout(str(pdf)), pdf, check_failures=failures
    )
    assert failures == []
    assert [f.model_dump() for f in isolated] == [f.model_dump() for f in strict]


def test_upload_runner_reports_failed_checks(
    tmp_path: Path, crashing_spacing_check: None
) -> None:
    pdf = _pdf_with_margin_overflow(tmp_path / "t.pdf")
    result = run_audit_for_uploaded_file(pdf, isolate_check_failures=True)
    assert result.failed_checks == ("_boom",)
    assert any(f.rule_id == "P011" for f in result.findings)


def _client(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


def _upload(c: TestClient, pdf: Path) -> str:
    resp = c.post(
        "/audits",
        files={"file": ("thesis.pdf", pdf.read_bytes(), "application/pdf")},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    return resp.headers["location"].rsplit("/", 1)[-1]


def test_web_job_completes_with_notice_when_a_check_fails(
    tmp_path: Path, crashing_spacing_check: None
) -> None:
    c, wa = _client(tmp_path)
    job_id = _upload(c, _pdf_with_margin_overflow(tmp_path / "t.pdf"))
    job = wa._get_job(job_id)
    assert job.state == "complete"
    assert job.failed_check_count == 1
    html = c.get(f"/audits/{job_id}").text
    assert "Some checks could not run on this file." in html
    assert "1 automated check stopped" in html
    # Student-safe: no exception text or internal function name.
    assert "synthetic check failure" not in html
    assert "_boom" not in html


def test_web_job_without_failures_shows_no_notice(tmp_path: Path) -> None:
    c, wa = _client(tmp_path)
    job_id = _upload(c, _pdf_with_margin_overflow(tmp_path / "t.pdf"))
    assert wa._get_job(job_id).failed_check_count == 0
    assert "Some checks could not run" not in c.get(f"/audits/{job_id}").text
