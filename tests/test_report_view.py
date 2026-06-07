"""Tests for report-view DTOs and polished comments."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import (
    REVIEW_PREFIX,
    build_polished_comment,
    contains_blocked_detail_text,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view, report_view_to_dict


def _p011_findings(count: int = 6) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
            },
        )
        for i in range(count)
    ]


def _p013_findings(count: int = 6) -> list[AuditFinding]:
    return [
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
        for i in range(count)
    ]


def _p026_findings(count: int = 6) -> list[AuditFinding]:
    return [
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
        for i in range(count)
    ]


def _sample_report() -> dict[str, Any]:
    findings = (
        _p011_findings(2)
        + _p013_findings(2)
        + _p026_findings(2)
        + [
            AuditFinding(
                rule_id="P030",
                severity=Severity.WARNING,
                page=12,
                message="Missing continued heading.",
                details={"issue_type": "missing_continued_heading"},
            )
        ]
    )
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def test_build_report_view_counts() -> None:
    report = _sample_report()
    view = build_report_view(report)
    assert view.total_findings == 7
    assert view.counts_by_severity["WARNING"] == 7
    assert view.counts_by_rule["P011"] == 2
    assert "margin_or_overflow" in view.counts_by_category
    assert len(view.summary_cards) >= 4
    assert view.pages == [1, 2, 12]


def test_build_report_view_triage_panels() -> None:
    report = _sample_report()
    view = build_report_view(report)
    rule_ids = {p.rule_id for p in view.triage_panels}
    assert "P011" in rule_ids
    assert "P013" in rule_ids
    assert "P026" in rule_ids
    p011 = next(p for p in view.triage_panels if p.rule_id == "P011")
    assert p011.raw_finding_count >= 2
    assert "triage" in p011.triage_note.lower() or "heuristic" in p011.triage_note.lower()


def test_finding_views_include_polished_comments() -> None:
    view = build_report_view(_sample_report())
    assert all(fv.polished_comment for fv in view.findings)
    assert all(fv.polished_comment.startswith(REVIEW_PREFIX) for fv in view.findings)


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "forbidden"),
    [
        ("P011", "margin_boundary_violation", "John Smith Dissertation Title"),
        ("P013", "page_number_candidate", "Figure 3.1 Neural network diagram"),
        ("P026", "possible_body_font_family_issue", "Chapter One Introduction text"),
        ("P030", "missing_continued_heading", "TABLE OF CONTENTS continued heading"),
        ("P033", "title_page_mismatch", "Yin Haotian"),
        ("P034", "copyright_author_not_found", "Committee Chair Name"),
        ("P061", "lof_cross_page_entry_numbers_not_nondecreasing", "Figure 2.4 Caption text"),
    ],
)
def test_polished_comments_are_privacy_safe(
    rule_id: str, issue_type: str, forbidden: str
) -> None:
    details = {
        "issue_type": issue_type,
        "observed_summary": forbidden,
        "caption": forbidden,
        "title": forbidden,
        "author": forbidden,
        "side": "left_margin",
        "position_type": "bottom_center",
        "run_start_page": "17",
        "run_end_page": "18",
        "confidence": "medium",
    }
    comment = build_polished_comment(
        rule_id=rule_id,
        issue_type=issue_type,
        page=5,
        details=details,
    )
    assert forbidden not in comment
    assert contains_blocked_detail_text(comment, details) is False
    assert "Review needed" in comment or "review" in comment.lower()


def test_polished_comment_templates_for_key_rules() -> None:
    p011 = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=3,
        details={"side": "left_margin"},
    )
    assert "margin" in p011.lower()
    p013 = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=4,
        details={"position_type": "bottom_center"},
    )
    assert "page-number" in p013.lower() or "page number" in p013.lower()
    p061 = build_polished_comment(
        rule_id="P061",
        issue_type="lof_cross_page_entry_numbers_not_nondecreasing",
        page=None,
        details={"run_start_page": "17", "run_end_page": "18"},
    )
    assert "figures" in p061.lower() or "lof" in p061.lower()


def test_polished_comment_fallback_unknown_rule() -> None:
    comment = build_polished_comment(
        rule_id="P999",
        issue_type="unknown_issue",
        page=1,
        details={},
    )
    assert "P999" in comment
    assert "Review needed" in comment


def test_web_results_render_polished_comments(tmp_path: Path) -> None:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)

    findings = _p011_findings(1)
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf", "job_id": "rv1"})
    view = build_report_view(payload)

    job = wa.JobState(
        job_id="rv1",
        state="complete",
        created_at="2026-01-01T00:00:00Z",
        file_name="thesis.pdf",
        finding_count=view.total_findings,
        warn_count=1,
        fail_count=0,
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
            for rs in view.rule_summaries
        ],
        report_view=report_view_to_dict(view),
        md_preview="# report",
    )
    wa._set_job(job)

    client = TestClient(wa.app)
    resp = client.get("/audits/rv1")
    assert resp.status_code == 200
    assert b"Polished comment" in resp.content
    assert b"Review needed" in resp.content
    assert b"High-volume triage" in resp.content


def test_json_download_unchanged_by_report_view(tmp_path: Path) -> None:
    findings = _p011_findings(1)
    metadata = {"audit_type": "pdf", "job_id": "dl1"}
    payload = audit_findings_to_json_dict(findings, metadata)
    build_report_view(payload)

    out = tmp_path / "report.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "grouped_summary" in loaded
    assert "findings" in loaded
    assert loaded["findings"][0]["rule_id"] == "P011"
