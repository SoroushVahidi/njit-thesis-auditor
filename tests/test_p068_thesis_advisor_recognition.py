"""Regression tests for P068 advisor-role recognition and atomic wording."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import (
    build_polished_comment,
    resolve_suggested_fix_for_display,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view


def _advisor_finding(**details: str) -> AuditFinding:
    return AuditFinding(
        rule_id="P068",
        severity=Severity.WARNING,
        page=8,
        message="Advisor role label missing.",
        details={
            "issue_type": "approval_page_advisor_role_label_missing",
            "role_label_count": "2",
            **details,
        },
    )


def test_p068_advisor_fix_is_atomic() -> None:
    fix = resolve_suggested_fix_for_display(
        "P068",
        "approval_page_advisor_role_label_missing",
    )
    lower = fix.lower()
    assert "thesis advisor" in lower or "dissertation advisor" in lower
    assert "signature" not in lower
    assert "date" not in lower
    assert "honorific" not in lower
    assert "rank order" not in lower


def test_p068_advisor_comment_does_not_mention_signature_blocks() -> None:
    comment = build_polished_comment(
        rule_id="P068",
        issue_type="approval_page_advisor_role_label_missing",
        page=8,
        details={"role_label_count": "2"},
    )
    lower = comment.lower()
    assert "thesis/dissertation advisor" in lower or "thesis or dissertation advisor" in lower
    assert "signature/date structural blocks" not in lower


def test_p068_advisor_finding_with_bbox_enables_highlight() -> None:
    finding = _advisor_finding(bbox="108.0,200.0,504.0,500.0")
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P068")
    assert fv.has_highlight is True
    assert "Thesis Advisor" in fv.suggested_fix or "thesis advisor" in fv.suggested_fix.lower()
