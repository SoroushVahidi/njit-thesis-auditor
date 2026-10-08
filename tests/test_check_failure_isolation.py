"""A crashing PDF check is isolated on the web path and loud everywhere else."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient

from njit_auditor import audit_runner
from njit_auditor.audit_runner import (
    UploadedAuditResult,
    collect_pdf_layout_findings,
    run_audit_for_uploaded_file,
)
from njit_auditor.incomplete_audit import (
    FAILED_CHECK_COUNT_KEY,
    INCOMPLETE_AUDIT_TITLE,
    failed_check_count_from_metadata,
    incomplete_audit_notice,
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
    assert records
    message = records[0].getMessage()
    assert "RuntimeError" in message
    assert "test_check_failure_isolation.py:" in message  # where it failed


# Values a real failure could carry in its message: the upload path (whose job
# directory is the access token for the report) and extracted document text.
_PRIVATE_TOKEN = "Zk3SyntheticJobToken0000"
_PRIVATE_EXCERPT = "synthetic private dissertation sentence"


def _leaky(*_args: object, **_kwargs: object) -> list[Any]:
    try:
        raise OSError(f"cannot open /runtime/jobs/{_PRIVATE_TOKEN}/upload.pdf")
    except OSError as exc:
        raise ValueError(f"unparsed line '{_PRIVATE_EXCERPT}'") from exc


def test_failure_log_omits_exception_messages_paths_and_document_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(audit_runner, "check_pdf_spacing", _leaky)
    pdf = _pdf_with_margin_overflow(tmp_path / "t.pdf")
    failures: list[str] = []
    with caplog.at_level(logging.DEBUG):
        collect_pdf_layout_findings(load_pdf_layout(str(pdf)), pdf, check_failures=failures)
    assert failures == ["_leaky"]
    # Format every record the way a journal handler would, tracebacks included.
    formatter = logging.Formatter()
    logged = "\n".join(formatter.format(record) for record in caplog.records)
    assert "_leaky" in logged and "ValueError" in logged
    assert _PRIVATE_TOKEN not in logged
    assert _PRIVATE_EXCERPT not in logged
    assert str(tmp_path) not in logged
    assert all(record.exc_info is None for record in caplog.records)


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


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Any]:
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(tmp_path / "web_audits"))
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


def _student_pdf_text(c: TestClient, job_id: str) -> str:
    resp = c.get(f"/audits/{job_id}/download/student-report.pdf")
    assert resp.status_code == 200
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_web_job_marks_every_output_incomplete_when_a_check_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, crashing_spacing_check: None
) -> None:
    c, wa = _client(tmp_path, monkeypatch)
    job_id = _upload(c, _pdf_with_margin_overflow(tmp_path / "t.pdf"))
    job = wa._get_job(job_id)
    assert job.state == "complete"
    assert job.failed_check_count == 1

    html = c.get(f"/audits/{job_id}").text
    text = c.get(f"/audits/{job_id}/download/text").text
    markdown = c.get(f"/audits/{job_id}/download/markdown").text
    payload = c.get(f"/audits/{job_id}/download/json").json()
    student_pdf = _flat(_student_pdf_text(c, job_id))

    assert INCOMPLETE_AUDIT_TITLE in html
    assert INCOMPLETE_AUDIT_TITLE.upper() in text
    assert f"**{INCOMPLETE_AUDIT_TITLE}**" in markdown
    assert INCOMPLETE_AUDIT_TITLE in student_pdf
    for surface in (html, text, markdown, student_pdf):
        assert "1 automated check stopped" in _flat(surface)
        # Student-safe: no exception text or internal function name.
        assert "synthetic check failure" not in surface
        assert "_boom" not in surface
    # JSON: additive metadata key only.
    assert payload["metadata"][FAILED_CHECK_COUNT_KEY] == "1"
    assert "_boom" not in str(payload)


def test_web_job_without_failures_shows_no_notice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    c, wa = _client(tmp_path, monkeypatch)
    job_id = _upload(c, _pdf_with_margin_overflow(tmp_path / "t.pdf"))
    assert wa._get_job(job_id).failed_check_count == 0
    assert INCOMPLETE_AUDIT_TITLE not in c.get(f"/audits/{job_id}").text
    assert INCOMPLETE_AUDIT_TITLE.upper() not in c.get(f"/audits/{job_id}/download/text").text
    markdown = c.get(f"/audits/{job_id}/download/markdown").text
    assert INCOMPLETE_AUDIT_TITLE not in markdown
    payload = c.get(f"/audits/{job_id}/download/json").json()
    assert FAILED_CHECK_COUNT_KEY not in payload["metadata"]
    assert INCOMPLETE_AUDIT_TITLE not in _flat(_student_pdf_text(c, job_id))


def test_incomplete_audit_with_no_findings_is_not_labelled_no_problems(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    c, wa = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(
        wa,
        "run_audit_for_uploaded_file",
        lambda *_a, **_k: UploadedAuditResult(
            upload_kind=audit_runner.UploadKind.PDF,
            audit_type="pdf",
            findings=[],
            failed_checks=("check_pdf_spacing",),
        ),
    )
    job_id = _upload(c, _pdf_with_margin_overflow(tmp_path / "t.pdf"))
    html = c.get(f"/audits/{job_id}").text
    assert "Audit incomplete" in html
    assert "No problems found" not in html
    assert INCOMPLETE_AUDIT_TITLE.upper() in c.get(f"/audits/{job_id}/download/text").text


def test_notice_wording_is_pluralized_and_empty_when_complete() -> None:
    assert incomplete_audit_notice(0) == ""
    assert incomplete_audit_notice(1).startswith("1 automated check stopped")
    assert incomplete_audit_notice(3).startswith("3 automated checks stopped")
    assert failed_check_count_from_metadata({}) == 0
    assert failed_check_count_from_metadata({FAILED_CHECK_COUNT_KEY: "2"}) == 2
    assert failed_check_count_from_metadata({FAILED_CHECK_COUNT_KEY: "bad"}) == 0
