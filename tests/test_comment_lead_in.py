"""Student-facing comments carry one lead-in label, never a stacked pair."""

from __future__ import annotations

import pytest

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import (
    collapse_stacked_lead_in,
    finalize_student_facing_comment_and_fix,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view

_STACKED = ("Review needed: Problem:", "Review needed: Likely problem:")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Review needed: Problem: The entry lacks a label.",
            "Review needed: The entry lacks a label.",
        ),
        ("Review needed: Likely problem: A title.", "Review needed: A title."),
        ("Review needed: Review needed: Problem: X.", "Review needed: X."),
        ("Problem: High-confidence text.", "Problem: High-confidence text."),
        ("Likely problem: Medium text.", "Likely problem: Medium text."),
        ("Review needed: Problems with leaders.", "Review needed: Problems with leaders."),
        ("Review needed: The problem: in text.", "Review needed: The problem: in text."),
        ("", ""),
    ],
)
def test_collapse_stacked_lead_in(raw: str, expected: str) -> None:
    assert collapse_stacked_lead_in(raw) == expected


def test_finalize_collapses_before_other_cleanup() -> None:
    comment, _fix = finalize_student_facing_comment_and_fix(
        "P055",
        "lof_entry_missing_figure_prefix",
        "Review needed: Problem: This List of Figures entry does not begin with 'Figure'.",
        "",
    )
    assert comment.startswith("Review needed: This List of Figures entry")
    assert not comment.startswith(_STACKED)


def _finding(rule_id: str, issue_type: str, page: int, **details: str) -> AuditFinding:
    return AuditFinding(
        rule_id=rule_id,
        severity=Severity.WARNING,
        page=page,
        message="Synthetic finding.",
        details={"issue_type": issue_type, **details},
    )


def test_report_view_cards_have_single_lead_in_and_keep_numbering() -> None:
    findings = [
        _finding("P055", "lof_entry_missing_figure_prefix", 9, confidence="low", entry_index="1"),
        _finding("P055", "lof_entry_missing_figure_prefix", 9, confidence="low", entry_index="2"),
        _finding(
            "P024",
            "list_of_figures_title_case",
            10,
            confidence="medium",
            page_type="list_of_figures",
        ),
        _finding("P086", "bold_heading_without_section_number", 30, confidence="medium"),
    ]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    cards = [f for f in view.findings if f.problem_number > 0]
    assert len(cards) == len(findings)
    assert sorted(f.problem_number for f in cards) == list(range(1, len(findings) + 1))
    for card in cards:
        assert card.polished_comment.startswith("Review needed: "), card.polished_comment
        assert not card.polished_comment.startswith(_STACKED), card.polished_comment
