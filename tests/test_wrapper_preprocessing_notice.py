"""Regression tests for Digital Commons wrapper preprocessing notices."""

from __future__ import annotations

import re
from pathlib import Path

import fitz
from starlette.testclient import TestClient

from njit_auditor.audit_runner import collect_pdf_layout_findings
from njit_auditor.confidence_presentation import apply_results_presentation
from njit_auditor.digital_commons_student_preview import (
    digital_commons_advisory_suggested_fix,
    is_wrapper_preprocessing_notice,
)
from njit_auditor.digital_commons_wrapper import detect_digital_commons_wrapper_pages
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from tests.test_web_app import _inject_complete_job_with_findings, _make_app


def _make_repository_wrapper_then_thesis_pdf(path: Path) -> None:
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Digital Commons @ NJIT", fontsize=14)
    page.insert_text((72, 100), "Electronic Theses and Dissertations", fontsize=11)
    page.insert_text((72, 130), "Recommended Citation", fontsize=11)
    page.insert_text(
        (108, 210),
        "machine learning repository cover title",
        fontsize=16,
        fontname="Times-Bold",
    )
    page.insert_text((292, 760), "1", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 90),
        "This work is protected by copyright and/or related rights.",
        fontsize=11,
    )
    page.insert_text(
        (72, 118),
        "For other uses you need to obtain permission from the rights-holder(s) directly.",
        fontsize=11,
    )
    page.insert_text((292, 760), "2", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 180), "Actual Thesis Title", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 210), "Author Name", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text(
        (108, 140),
        "This abstract contains enough body text to count as the real manuscript front matter.",
        fontsize=12,
    )

    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 180),
        "Machine learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )

    doc.save(path)
    doc.close()


def _wrapper_finding(*, confidence: str = "") -> AuditFinding:
    return AuditFinding(
        rule_id="P025",
        severity=Severity.WARNING,
        page=1,
        message="Repository-generated Digital Commons wrapper pages were detected.",
        details={
            "issue_type": "digital_commons_wrapper_pages_detected",
            "presentation_kind": "preprocessing_notice",
            "digital_commons_wrapper_pages": "1,2",
            "digital_commons_wrapper_page_count": "2",
            "digital_commons_wrapper_pages_compact": "1, 2",
            "triage_tier": "informational",
            "confidence": confidence,
            "suggested_fix": digital_commons_advisory_suggested_fix(),
        },
    )


def _margin_finding() -> AuditFinding:
    return AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=5,
        message="Left margin too narrow.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "left_margin",
            "confidence": "high",
            "suggested_fix": "Adjust the left margin in the PDF export settings.",
        },
    )


def test_is_wrapper_preprocessing_notice_helper() -> None:
    assert is_wrapper_preprocessing_notice(
        rule_id="P025",
        issue_type="digital_commons_wrapper_pages_detected",
    )
    assert not is_wrapper_preprocessing_notice(
        rule_id="P025",
        issue_type="other_issue",
    )


def test_collect_pdf_layout_findings_emits_informational_wrapper_notice(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "repository_wrapper_collect.pdf"
    _make_repository_wrapper_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    assert detect_digital_commons_wrapper_pages(model) == {1, 2}

    findings = collect_pdf_layout_findings(model, pdf_path)
    wrapper_findings = [
        f
        for f in findings
        if f.details.get("issue_type") == "digital_commons_wrapper_pages_detected"
    ]
    assert len(wrapper_findings) == 1
    details = wrapper_findings[0].details
    assert details.get("triage_tier") == "informational"
    assert details.get("presentation_kind") == "preprocessing_notice"
    assert details.get("confidence") == ""
    assert "no action is needed" in str(details.get("suggested_fix", "")).lower()
    assert "remove repository-generated" in str(details.get("suggested_fix", "")).lower()


def test_build_report_view_routes_wrapper_to_preprocessing_notices() -> None:
    payload = audit_findings_to_json_dict(
        [_wrapper_finding(), _margin_finding()],
        {
            "audit_type": "pdf",
            "digital_commons_wrapper_pages": "1,2",
            "digital_commons_wrapper_page_count": "2",
            "digital_commons_wrapper_pages_compact": "1, 2",
        },
    )
    view = build_report_view(payload, pdf_page_sizes=[(612.0, 792.0)] * 6)

    assert len(view.preprocessing_notices) == 1
    notice = view.preprocessing_notices[0]
    assert notice.rule_id == "P025"
    assert notice.issue_type == "digital_commons_wrapper_pages_detected"
    assert notice.issue_type_label == "Repository wrapper pages detected"
    assert notice.triage_tier == "informational"
    assert notice.confidence == ""
    assert notice.confidence_label == ""
    assert notice.problem_number == 0
    assert "repository-generated Digital Commons pages" in notice.polished_comment
    assert "no action is needed" in notice.suggested_fix.lower()

    assert len(view.findings) == 1
    assert view.findings[0].rule_id == "P011"
    assert view.counts_by_rule.get("P025") is None
    assert view.counts_by_severity["WARNING"] == 1


def test_wrapper_notice_excluded_from_confidence_summary() -> None:
    payload = audit_findings_to_json_dict(
        [_wrapper_finding(), _margin_finding()],
        {
            "audit_type": "pdf",
            "digital_commons_wrapper_pages": "1,2",
            "digital_commons_wrapper_page_count": "2",
            "digital_commons_wrapper_pages_compact": "1, 2",
        },
    )
    view = build_report_view(payload, pdf_page_sizes=[(612.0, 792.0)] * 6)
    serialized_findings = [
        {
            "rule_id": finding.rule_id,
            "severity": finding.severity,
            "page": finding.page,
            "issue_type": finding.issue_type,
            "confidence_level": finding.confidence_level,
            "confidence": finding.confidence,
            "triage_tier": finding.triage_tier,
        }
        for finding in view.findings
    ]
    presentation = apply_results_presentation(
        findings=serialized_findings,
        grouped_problems=[],
    )
    summary = presentation["confidence_summary"]
    assert summary.get("high", 0) == 1
    assert sum(summary.values()) == 1


def test_confidence_grouping_still_works_for_real_warnings() -> None:
    findings = [
        {
            "rule_id": "P011",
            "severity": "WARNING",
            "page": 3,
            "issue_type": "margin_boundary_violation",
            "confidence_level": "high",
            "confidence": "high",
            "polished_comment": "High margin issue.",
        },
        {
            "rule_id": "P026",
            "severity": "WARNING",
            "page": 5,
            "issue_type": "possible_body_font_family_issue",
            "confidence_level": "medium",
            "confidence": "medium",
            "polished_comment": "Medium font issue.",
        },
    ]
    presentation = apply_results_presentation(
        findings=findings,
        grouped_problems=[],
        group_by_confidence=True,
    )
    sections = presentation["confidence_sections"]
    assert [section["bucket"] for section in sections] == ["high", "medium"]
    assert sections[0]["count"] == 1
    assert sections[1]["count"] == 1


def test_job_page_shows_preprocessing_notice_section(tmp_path: Path) -> None:
    app, wa = _make_app(tmp_path)
    client = TestClient(app, raise_server_exceptions=False)
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=[_wrapper_finding(), _margin_finding()],
        file_name="digital_commons_thesis.pdf",
        audit_type="pdf",
        page_count=6,
    )
    response = client.get(f"/audits/{job_id}")
    assert response.status_code == 200
    html = response.text

    assert "Document preprocessing notices" in html
    assert "Repository wrapper pages detected" in html
    assert 'badge badge-muted">Notice</span>' in html
    assert "no action is needed" in html.lower()
    assert "remove repository-generated" in html.lower()
    assert "Problem 1" in html
    assert "digital_commons_wrapper_pages_detected" not in html
    assert re.search(r"Problem\s+1[^<]*P025", html) is None
    assert "confidence-badge confidence-badge--high" not in html or html.count(
        "confidence-badge confidence-badge--high"
    ) <= html.count("P011")


def test_rules_page_unchanged_by_wrapper_notice_presentation(tmp_path: Path) -> None:
    app, _wa = _make_app(tmp_path)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/rules")
    assert response.status_code == 200
    assert "Repository wrapper pages detected" not in response.text
