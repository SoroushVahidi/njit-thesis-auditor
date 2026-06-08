"""Tests for shared PDF audit backend parity (CLI and web)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import fitz
from typer.testing import CliRunner

from njit_auditor.audit_runner import (
    PDF_AUDIT_POST_P054_CALLABLE_NAMES,
    PDF_AUDIT_POST_P054_RULE_IDS,
    collect_pdf_layout_findings,
    run_pdf_audit_full,
)
from njit_auditor.cli import app
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict


def _make_minimal_pdf(path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(path)
    doc.close()


def test_post_p054_rule_ids_include_p062() -> None:
    assert "P061" in PDF_AUDIT_POST_P054_RULE_IDS
    assert "P062" in PDF_AUDIT_POST_P054_RULE_IDS
    assert "P063" in PDF_AUDIT_POST_P054_RULE_IDS
    assert "P064" in PDF_AUDIT_POST_P054_RULE_IDS
    assert "check_pdf_toc_cross_page_entry_ordering" in PDF_AUDIT_POST_P054_CALLABLE_NAMES
    assert "check_pdf_appendix_body_headings" in PDF_AUDIT_POST_P054_CALLABLE_NAMES
    assert PDF_AUDIT_POST_P054_CALLABLE_NAMES[-1] == "check_pdf_references_citations_structural"


def test_run_pdf_audit_full_calls_post_p054_rules(tmp_path: Path) -> None:
    """Regression: web/CLI shared path must invoke P055–P062, not stop at P054."""
    pdf_path = tmp_path / "thesis.pdf"
    _make_minimal_pdf(pdf_path)

    called: list[str] = []

    def _spy(name: str, original: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> list[AuditFinding]:
            called.append(name)
            return original(*args, **kwargs)

        return wrapper

    import njit_auditor.audit_runner as ar

    patches = [
        patch.object(ar, name, _spy(name, getattr(ar, name)))
        for name in PDF_AUDIT_POST_P054_CALLABLE_NAMES
    ]
    for p in patches:
        p.start()
    try:
        run_pdf_audit_full(pdf_path)
    finally:
        for p in reversed(patches):
            p.stop()

    assert called == list(PDF_AUDIT_POST_P054_CALLABLE_NAMES)
    assert "check_pdf_lot_lof_cross_page_entry_ordering" in called
    assert "check_pdf_toc_cross_page_entry_ordering" in called


def test_cli_and_shared_backend_use_same_collect_function(tmp_path: Path) -> None:
    """CLI pdf command must call collect_pdf_layout_findings (shared rule sequence)."""
    pdf_path = tmp_path / "thesis.pdf"
    _make_minimal_pdf(pdf_path)

    with patch(
        "njit_auditor.cli.collect_pdf_layout_findings",
        return_value=[],
    ) as mock_collect:
        runner = CliRunner()
        result = runner.invoke(app, ["pdf", str(pdf_path)])

    assert result.exit_code == 0
    mock_collect.assert_called_once()
    args = mock_collect.call_args[0]
    assert args[1] == pdf_path


def test_web_audit_uses_run_audit_for_uploaded_file(tmp_path: Path) -> None:
    """Web background task must call run_audit_for_uploaded_file (PDF dispatch)."""
    import importlib
    import os

    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)

    from datetime import datetime, timezone

    pdf_path = tmp_path / "input.pdf"
    _make_minimal_pdf(pdf_path)

    job_id = "parity_test_job"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(pdf_path.read_bytes())

    job = wa.JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    from njit_auditor.audit_runner import UploadedAuditResult
    from njit_auditor.upload_handling import UploadKind

    empty_result = UploadedAuditResult(
        upload_kind=UploadKind.PDF,
        audit_type="pdf",
        findings=[],
    )
    with patch.object(
        wa, "run_audit_for_uploaded_file", return_value=empty_result
    ) as mock_dispatch:
        wa._run_audit_task(job_id)

    mock_dispatch.assert_called_once()
    assert mock_dispatch.call_args[0][0] == jdir / "upload.pdf"


def test_web_report_includes_triage_keys(tmp_path: Path) -> None:
    """Web JSON report path preserves grouped_summary triage rollups."""
    import importlib
    import os

    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)

    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
            },
        )
        for i in range(6)
    ] + [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=i + 1,
            message="Page number candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "confidence": "medium",
            },
        )
        for i in range(6)
    ] + [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=i + 1,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "confidence": "medium",
            },
        )
        for i in range(6)
    ]

    job_id = "triage_test_job"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(b"%PDF-1.4\n")

    from datetime import datetime, timezone

    job = wa.JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    from njit_auditor.audit_runner import UploadedAuditResult
    from njit_auditor.upload_handling import UploadKind

    dispatch_result = UploadedAuditResult(
        upload_kind=UploadKind.PDF,
        audit_type="pdf",
        findings=findings,
    )
    with patch.object(wa, "run_audit_for_uploaded_file", return_value=dispatch_result):
        wa._run_audit_task(job_id)

    report_path = jdir / "report.json"
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    grouped = payload["grouped_summary"]
    assert "p011_margin_triage" in grouped
    assert "p013_triage" in grouped
    assert "p026_font_triage" in grouped
    assert payload["metadata"]["total_findings"] == 18


def test_collect_pdf_layout_findings_matches_run_pdf_audit_full(tmp_path: Path) -> None:
    """Direct collect and full runner return the same findings on a fixture PDF."""
    pdf_path = tmp_path / "thesis.pdf"
    _make_minimal_pdf(pdf_path)

    from njit_auditor.pdf_layout import load_pdf_layout

    pdf_doc = load_pdf_layout(str(pdf_path))
    direct = collect_pdf_layout_findings(pdf_doc, pdf_path)
    via_runner = run_pdf_audit_full(pdf_path)

    assert [f.model_dump() for f in direct] == [f.model_dump() for f in via_runner]


def test_audit_findings_json_schema_unchanged() -> None:
    findings = [
        AuditFinding(
            rule_id="P061",
            severity=Severity.WARNING,
            page=2,
            message="Cross-page ordering issue.",
            details={"issue_type": "lof_cross_page_entry_numbers_not_nondecreasing"},
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    assert "grouped_summary" in payload
    assert "findings" in payload
    assert payload["findings"][0]["rule_id"] == "P061"
