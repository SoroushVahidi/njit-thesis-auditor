"""Regression tests for confidence-based grouping and sorting on audit result pages."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from njit_auditor.confidence_presentation import (
    apply_results_presentation,
    normalize_confidence_bucket,
    sort_findings,
)
from njit_auditor.models import AuditFinding, Severity


def _confidence_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="High margin issue.",
            details={"issue_type": "margin_boundary_violation", "confidence": "high"},
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=5,
            message="Medium font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=7,
            message="Low heading issue.",
            details={"issue_type": "missing_continued_heading", "confidence": "low"},
        ),
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=9,
            message="Unknown confidence issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "unknown"},
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=11,
            message="Review needed issue.",
            details={"issue_type": "page_number_mismatch", "confidence": "review needed"},
        ),
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("high", "high"),
        ("Medium", "medium"),
        ("low", "low"),
        ("needs_review", "needs_review"),
        ("unknown", "needs_review"),
        ("review needed", "needs_review"),
        ("", "needs_review"),
    ],
)
def test_normalize_confidence_bucket(raw: str, expected: str) -> None:
    assert normalize_confidence_bucket(raw) == expected


def test_sort_confidence_desc_orders_high_before_needs_review() -> None:
    findings = [
        {"confidence_level": "low", "page": 1, "rule_id": "P1"},
        {"confidence_level": "high", "page": 2, "rule_id": "P2"},
        {"confidence_level": "needs_review", "page": 3, "rule_id": "P3"},
        {"confidence_level": "medium", "page": 4, "rule_id": "P4"},
    ]
    ordered = sort_findings(findings, "confidence_desc")
    assert [item["confidence_level"] for item in ordered] == [
        "high",
        "medium",
        "low",
        "needs_review",
    ]


def test_sort_confidence_asc_orders_needs_review_before_high() -> None:
    findings = [
        {"confidence_level": "high", "page": 1, "rule_id": "P1"},
        {"confidence_level": "needs_review", "page": 2, "rule_id": "P2"},
        {"confidence_level": "medium", "page": 3, "rule_id": "P3"},
        {"confidence_level": "low", "page": 4, "rule_id": "P4"},
    ]
    ordered = sort_findings(findings, "confidence_asc")
    assert [item["confidence_level"] for item in ordered] == [
        "needs_review",
        "low",
        "medium",
        "high",
    ]


def test_apply_results_presentation_keeps_default_order_without_params() -> None:
    findings = [
        {"confidence_level": "high", "page": 1, "rule_id": "P1", "issue_type": "a"},
        {"confidence_level": "low", "page": 2, "rule_id": "P2", "issue_type": "b"},
    ]
    presentation = apply_results_presentation(
        findings=findings,
        grouped_problems=[],
        confidence_filter="",
        sort_mode="default",
    )
    assert presentation["findings"][0]["rule_id"] == "P1"
    assert presentation["findings"][1]["rule_id"] == "P2"


def test_confidence_summary_and_controls_on_job_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from tests.test_web_app import _inject_complete_job_with_findings

    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")
    body = resp.text

    assert resp.status_code == 200
    assert "High confidence" in body
    assert "Medium confidence" in body
    assert "Low confidence" in body
    assert "Needs review" in body
    assert 'data-confidence-filter="high"' in body
    assert 'data-confidence-filter="needs_review"' in body
    assert "Highest confidence first" in body
    assert "Group by confidence" in body


def _grouped_problem_rules_in_findings_section(body: str) -> list[str]:
    section = body.split('id="section-findings"', 1)[1]
    return re.findall(
        r'class="card grouped-problem-card[^"]* grouped-problem"[^>]*data-rule="([^"]+)"',
        section,
    )


def test_confidence_filter_high_shows_only_high_findings(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from tests.test_web_app import _inject_complete_job_with_findings

    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}?confidence=high")
    body = resp.text

    assert resp.status_code == 200
    assert _grouped_problem_rules_in_findings_section(body) == ["P011"]


def test_confidence_filter_medium_shows_only_medium_findings(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from tests.test_web_app import _inject_complete_job_with_findings

    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}?confidence=medium")
    body = resp.text

    assert resp.status_code == 200
    assert _grouped_problem_rules_in_findings_section(body) == ["P026"]


def test_group_by_confidence_renders_separate_sections(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from tests.test_web_app import _inject_complete_job_with_findings

    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}?group=confidence")
    body = resp.text

    assert resp.status_code == 200
    assert body.index("High confidence") < body.index("Medium confidence")
    assert body.index("Medium confidence") < body.index("Low confidence")
    assert body.index("Low confidence") < body.index("Needs review")
    assert "P011" in body
    assert "P026" in body


def test_page_labels_and_pdf_links_remain_after_filtering(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from tests.test_web_app import _inject_complete_job_with_findings

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
                "manuscript_page": "2",
                "pdf_page": "3",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}?confidence=high&sort=confidence_desc")
    body = resp.text

    assert resp.status_code == 200
    assert "/audits/" in body
    assert "highlight" in body or "View highlighted page" in body or "page-link" in body


def test_rules_page_has_no_confidence_grouping_controls(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/rules")
    body = resp.text

    assert resp.status_code == 200
    assert "Group by confidence" not in body
    assert "Highest confidence first" not in body
    assert "confidence-summary" not in body
