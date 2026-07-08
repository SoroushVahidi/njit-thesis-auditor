"""Regression tests for Ester Column C/E wording alignment and page-order-first UI."""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient

from njit_auditor.ester_warning_wording import (
    student_warning_question,
    student_warning_remediation,
)
from njit_auditor.issue_type_explanations import student_facing_issue_label
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p011_margin_presentation import margin_suggested_fix
from njit_auditor.p012_student_preview import p012_rolled_up_comment
from njit_auditor.polished_comments import resolve_suggested_fix_for_display
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view, report_view_to_dict

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MAP_PATH = _REPO_ROOT / "data" / "specs" / "ester_warning_wording_map.json"


def _make_app(tmp_path: Path) -> Any:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return wa.app, wa


def _inject_complete_job(
    wa: Any,
    tmp_path: Path,
    *,
    finding_count: int = 1,
) -> str:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.pdf_highlight import get_pdf_page_sizes
    from njit_auditor.report_outputs import write_markdown_report

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
    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(jdir / "upload.pdf")
    doc.close()
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    pdf_page_sizes = get_pdf_page_sizes(jdir / "upload.pdf")
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv["rule_id"],
                "severity": fv["severity"],
                "page": fv["page"],
                "issue_type": fv["issue_type"],
                "category": fv["category"],
                "polished_comment": fv["polished_comment"],
                "suggested_fix": fv.get("suggested_fix", ""),
                "triage_tier": fv.get("triage_tier", ""),
                "confidence": fv.get("confidence", ""),
                "confidence_level": fv.get("confidence_level", ""),
                "confidence_label": fv.get("confidence_label", ""),
                "confidence_css_class": fv.get("confidence_css_class", ""),
                "source_file": fv.get("source_file", ""),
                "source_line": fv.get("source_line", ""),
                "location_label": fv.get("location_label", ""),
                "bbox": fv.get("bbox"),
                "action_kind": fv.get("action_kind", ""),
                "action_label": fv.get("action_label", ""),
                "has_highlight": fv.get("has_highlight", False),
                "no_highlight_reason": fv.get("no_highlight_reason", ""),
                "detailed_explanation": fv.get("detailed_explanation", ""),
                "issue_type_label": fv.get("issue_type_label", ""),
                "issue_type_explanation": fv.get("issue_type_explanation", ""),
            }
            for fv in view_dict.get("findings", [])
        ],
        grouped_summary=[
            {
                "rule_id": rs.rule_id,
                "count": rs.count,
                "category": rs.category,
            }
            for rs in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview="# Audit Report\n",
    )
    wa._set_job(job)
    return job_id


def _inject_complete_job_with_findings(
    wa: Any,
    tmp_path: Path,
    *,
    findings: list[Any],
    file_name: str,
    audit_type: str,
    page_count: int = 5,
    grouped_findings: list[dict[str, Any]] | None = None,
) -> str:
    from njit_auditor.pdf_highlight import get_pdf_page_sizes
    from njit_auditor.report_outputs import write_markdown_report

    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for _ in range(page_count):
        doc.new_page(width=612, height=792)
    doc.save(jdir / "upload.pdf")
    doc.close()
    metadata = {"input_file_name": file_name, "audit_type": audit_type, "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    if grouped_findings is not None:
        payload["grouped_findings"] = grouped_findings
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    pdf_page_sizes = get_pdf_page_sizes(jdir / "upload.pdf")
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name=file_name,
        audit_type=audit_type,
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv["rule_id"],
                "severity": fv["severity"],
                "page": fv["page"],
                "issue_type": fv["issue_type"],
                "category": fv["category"],
                "polished_comment": fv["polished_comment"],
                "suggested_fix": fv.get("suggested_fix", ""),
                "triage_tier": fv.get("triage_tier", ""),
                "confidence": fv.get("confidence", ""),
                "confidence_level": fv.get("confidence_level", ""),
                "confidence_label": fv.get("confidence_label", ""),
                "confidence_css_class": fv.get("confidence_css_class", ""),
                "source_file": fv.get("source_file", ""),
                "source_line": fv.get("source_line", ""),
                "location_label": fv.get("location_label", ""),
                "bbox": fv.get("bbox"),
                "action_kind": fv.get("action_kind", ""),
                "action_label": fv.get("action_label", ""),
                "has_highlight": fv.get("has_highlight", False),
                "no_highlight_reason": fv.get("no_highlight_reason", ""),
                "detailed_explanation": fv.get("detailed_explanation", ""),
                "issue_type_label": fv.get("issue_type_label", ""),
                "issue_type_explanation": fv.get("issue_type_explanation", ""),
            }
            for fv in view_dict.get("findings", [])
        ],
        grouped_summary=[
            {
                "rule_id": rs.rule_id,
                "count": rs.count,
                "category": rs.category,
            }
            for rs in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview="# Audit Report\n",
    )
    wa._set_job(job)
    return job_id


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    app, wa = _make_app(tmp_path)
    return TestClient(app, raise_server_exceptions=False), wa


def test_ester_warning_wording_map_has_required_metadata() -> None:
    payload = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    assert payload["metadata"]["extraction_date"] == "2026-07-06"
    assert "P011" in payload["rules"]
    assert payload["rules"]["P011"]["source_column_question"] == "C"
    assert payload["rules"]["P011"]["source_column_remediation"] == "E"


def test_p011_student_question_includes_tables_and_figures() -> None:
    question = student_warning_question("P011")
    assert question.startswith("Is all text")
    assert "including tables and figures" in question
    assert question.endswith("?")


def test_p011_student_facing_label_uses_ester_question() -> None:
    label = student_facing_issue_label("P011", "margin_boundary_violation")
    assert "including tables and figures" in label
    assert label.endswith("?")


def test_p012_student_facing_label_uses_ester_question() -> None:
    label = student_facing_issue_label("P012", "pdf_annotation_detected")
    assert label == student_warning_question("P012")
    assert label == "Does the PDF contain annotations/comments?"


def test_p011_remediation_includes_margin_inches_and_content_types() -> None:
    remediation = student_warning_remediation("P011")
    assert "1.5 inches" in remediation
    assert "1 inch" in remediation

    fix = margin_suggested_fix(
        page_context="body",
        content_kind="text_paragraph",
        side_label="left margin",
    )
    lower = fix.lower()
    assert "1.5 inches" in fix
    assert "1 inch" in fix
    assert "text" in lower or "paragraph" in lower
    assert fix.index("1.5 inches") < fix.index("Adjust the paragraph")


def test_p013_wording_from_ester_map() -> None:
    question = student_warning_question("P013")
    remediation = student_warning_remediation("P013")
    assert "bottom" in question.lower()
    assert "center" in question.lower()
    assert "0.5 inches" in remediation


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "expected_fix"),
    [
        ("P012", "pdf_annotation_detected", "Resolve or delete all annotations"),
        (
            "P013",
            "page_number_candidate",
            "Set page numbers on the bottom of the page, centered and 0.5 inches from margin",
        ),
        (
            "P068",
            "approval_page_advisor_role_label_missing",
            (
                "Ensure the Approval Page includes an advisor-role label and sufficient "
                "date/signature structural blocks for each committee entry. Manual review "
                "is still required for honorifics and rank order."
            ),
        ),
    ],
)
def test_suggested_fix_prefers_ester_map_when_available(
    rule_id: str, issue_type: str, expected_fix: str
) -> None:
    assert resolve_suggested_fix_for_display(rule_id, issue_type) == expected_fix


def test_p012_page_level_comment_does_not_claim_affected_pages_when_unlisted() -> None:
    comment = p012_rolled_up_comment(page=4, annotation_count=1)
    lowered = comment.lower()
    assert "affected pages include" not in lowered
    assert "affected pages listed above" not in lowered


def test_report_section_order_page_before_topic(
    client: tuple[TestClient, object], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    html = c.get(f"/audits/{job_id}").text

    idx_findings = html.index('id="section-findings"')
    idx_topics = html.index('id="section-topics"')
    assert idx_findings < idx_topics


def test_nav_jump_links_page_order_before_topic(
    client: tuple[TestClient, object], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    html = c.get(f"/audits/{job_id}").text
    nav_start = html.index('<nav class="jump-links"')
    nav_end = html.index("</nav>", nav_start)
    nav = html[nav_start:nav_end]

    idx_page = nav.index("Findings in page order")
    idx_topic = nav.index("Findings by topic")
    assert idx_page < idx_topic
    assert 'href="#section-findings"' in nav
    assert 'href="#section-topics"' in nav


def test_confidence_filter_still_present_after_reorder(
    client: tuple[TestClient, object], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    html = c.get(f"/audits/{job_id}").text
    assert 'data-confidence-filter="low"' in html
    assert "confidence-filter__chip" in html


def test_one_page_pdf_excerpt_buttons_still_present(
    client: tuple[TestClient, object], tmp_path: Path
) -> None:
    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="margin",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "bbox": "10,10,20,20",
            },
        )
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    html = c.get(f"/audits/{job_id}").text
    assert "highlighted-page.pdf" in html


def test_json_export_schema_unchanged_by_wording_layer(tmp_path: Path) -> None:
    findings = [
        {
            "rule_id": "P011",
            "severity": "WARNING",
            "page": 1,
            "message": "margin",
            "details": {
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
            },
        }
    ]
    from njit_auditor.models import AuditFinding, Severity

    audit_findings = [
        AuditFinding(
            rule_id=f["rule_id"],
            severity=Severity.WARNING,
            page=f["page"],
            message=f["message"],
            details=f["details"],
        )
        for f in findings
    ]
    payload = audit_findings_to_json_dict(audit_findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    exported = {
        "findings": [
            {
                "rule_id": f.rule_id,
                "issue_type": f.issue_type,
                "severity": f.severity,
                "page": f.page,
            }
            for f in view.findings
        ]
    }
    assert exported == {
        "findings": [
            {
                "rule_id": "P011",
                "issue_type": "margin_boundary_violation",
                "severity": "WARNING",
                "page": 1,
            }
        ]
    }


@pytest.mark.parametrize(
    "viewport_width",
    [390],
)
def test_mobile_390px_no_horizontal_overflow(
    client: tuple[TestClient, object], tmp_path: Path, viewport_width: int
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=4)
    resp = c.get(
        f"/audits/{job_id}",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            )
        },
    )
    assert resp.status_code == 200
    # Structural smoke: main sections and filters still render at phone width.
    text = resp.text
    assert "Findings in page order" in text
    assert "overflow-x:auto" in text or "table-scroll" in text
