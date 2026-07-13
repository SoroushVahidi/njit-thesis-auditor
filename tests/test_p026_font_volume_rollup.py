"""Tests for P026 pattern-level font warning rollups in student-facing reports."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p026_student_preview import (
    P026_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES,
    P026_FAMILY_ISSUE_TYPE,
    should_use_p026_document_summary,
    student_facing_observed_font_phrase,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view


def _p026_family_finding(
    *,
    page: int,
    observed_summary: str = "CMR12",
    expected: str = "Times New Roman or accepted equivalent",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P026",
        severity=Severity.WARNING,
        page=page,
        message=f"Body text on page {page} may not use Times New Roman.",
        details={
            "issue_type": P026_FAMILY_ISSUE_TYPE,
            "observed_summary": observed_summary,
            "expected": expected,
            "bbox": "72.0,100.0,200.0,120.0",
            "content": "Private paragraph text must never appear.",
        },
    )


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def test_should_use_p026_document_summary_thresholds() -> None:
    assert should_use_p026_document_summary(10, 20) is False
    assert should_use_p026_document_summary(11, 5) is True
    assert should_use_p026_document_summary(5, 21) is True


def test_student_facing_font_phrase_explains_computer_modern_codes() -> None:
    phrase = student_facing_observed_font_phrase("CMR12")
    assert "Computer Modern / LaTeX" in phrase
    assert '"CMR12"' in phrase


def test_low_volume_p026_keeps_page_level_cards() -> None:
    findings = [_p026_family_finding(page=i) for i in range(1, 6)]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P026"]
    assert len(cards) == 5
    assert all("Document-wide" not in card.location_label for card in cards)
    assert "Computer Modern / LaTeX" in cards[0].location_label
    assert '"CMR12"' in cards[0].location_label


def test_high_volume_same_pattern_collapses_to_one_document_card() -> None:
    findings = [
        _p026_family_finding(page=i)
        for i in range(1, P026_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES + 1)
    ]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P026"]
    assert len(cards) == 1
    assert cards[0].location_label.startswith("Document-wide —")
    assert "Computer Modern / LaTeX" in cards[0].location_label
    assert '"CMR12"' in cards[0].location_label
    assert f"on {P026_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES} pages" in cards[0].location_label
    assert "Affected pages include:" in cards[0].polished_comment
    assert cards[0].has_highlight is False


def test_high_volume_no_highlight_reason_lists_affected_pages() -> None:
    """The no-highlight text must not tell a student to "review every affected
    page" without actually naming them -- same wording defect Ester flagged
    on the P012 document-wide summary, present here in the parallel P026
    document-wide summary too.
    """
    findings = [
        _p026_family_finding(page=i)
        for i in range(1, P026_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES + 1)
    ]
    view = build_report_view(_payload(findings))
    card = [f for f in view.findings if f.rule_id == "P026"][0]
    reason = card.no_highlight_reason or ""
    assert "listed in the summary" not in reason.lower()

    from njit_auditor.report_outputs import compact_page_list

    pages = sorted({f.page for f in findings if f.page is not None})
    assert compact_page_list(pages) in reason


def test_distinct_font_patterns_remain_separate() -> None:
    findings = [
        _p026_family_finding(page=1, observed_summary="CMR12"),
        _p026_family_finding(page=2, observed_summary="ArialMT"),
    ]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P026"]
    assert len(cards) == 2
    labels = {card.location_label for card in cards}
    assert any("Computer Modern / LaTeX" in label and '"CMR12"' in label for label in labels)
    assert any("Arial" in label for label in labels)


def test_p026_rollup_has_no_private_leaks() -> None:
    findings = [_p026_family_finding(page=i) for i in range(1, 12)]
    view = build_report_view(_payload(findings))
    card = [f for f in view.findings if f.rule_id == "P026"][0]
    for forbidden in (
        "Private paragraph",
        "72.0",
        "100.0",
        "Reviewer:",
    ):
        assert forbidden not in card.location_label
        assert forbidden not in card.polished_comment
        assert forbidden not in card.detailed_explanation


def test_markdown_and_web_align_on_document_summary(tmp_path: Path) -> None:
    findings = [_p026_family_finding(page=i) for i in range(1, 12)]
    payload = _payload(findings)
    view = build_report_view(payload)
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert text.count("### Problem") == len(view.findings)
    problems_section = text.split("## Findings by Rule")[0]
    assert "- Location: `Document-wide —" in problems_section
    assert len([f for f in view.findings if f.rule_id == "P026"]) == 1


def test_raw_p026_findings_unchanged_in_payload() -> None:
    findings = [_p026_family_finding(page=i) for i in range(1, 12)]
    payload = _payload(findings)
    raw_count = len(payload["findings"])
    build_report_view(payload)
    assert len(payload["findings"]) == raw_count
