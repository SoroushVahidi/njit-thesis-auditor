"""Tests for P012 document-level summary when annotation volume is high."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p012_student_preview import (
    P012_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES,
    P012_DOCUMENT_SUMMARY_MIN_RAW_FINDINGS,
    build_p012_presentation_stats,
    should_use_p012_document_summary,
)
from njit_auditor.report_outputs import (
    audit_findings_to_json_dict,
    compact_page_list,
    write_markdown_report,
)
from njit_auditor.report_view import build_report_view


def _p012_finding(
    *,
    page: int,
    rect: str = "72.0,100.0,200.0,120.0",
    annotation_type: str = "Text",
    content: str = "Private reviewer note should never appear.",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P012",
        severity=Severity.WARNING,
        page=page,
        message=f"PDF annotation/comment detected ({annotation_type}).",
        details={
            "issue_type": "pdf_annotation_detected",
            "annotation_type": annotation_type,
            "content": content,
            "rect": rect,
        },
    )


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def _high_volume_findings(
    *,
    page_count: int = P012_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES,
    per_page: int = 1,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for page in range(1, page_count + 1):
        for index in range(per_page):
            findings.append(
                _p012_finding(
                    page=page,
                    rect=f"{72 + index}.0,100.0,200.0,120.0",
                    content=f"secret note {page}-{index}",
                )
            )
    return findings


def test_should_use_p012_document_summary_thresholds() -> None:
    assert should_use_p012_document_summary(10, 20) is False
    assert should_use_p012_document_summary(11, 5) is True
    assert should_use_p012_document_summary(5, 21) is True


def test_low_volume_p012_keeps_page_level_cards() -> None:
    findings = [_p012_finding(page=3), _p012_finding(page=8), _p012_finding(page=8)]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P012"]
    assert len(cards) == 2
    assert all("Document-wide" not in card.location_label for card in cards)


def test_high_volume_p012_collapses_to_one_document_summary_card() -> None:
    findings = _high_volume_findings()
    payload = _payload(findings)
    view = build_report_view(payload)
    cards = [f for f in view.findings if f.rule_id == "P012"]
    assert len(cards) == 1
    assert cards[0].location_label.startswith("Document-wide —")
    assert f"across {P012_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES} pages" in cards[0].location_label
    assert str(P012_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES) in cards[0].location_label
    assert "Affected pages include:" in cards[0].polished_comment
    assert cards[0].has_highlight is False
    assert cards[0].bbox is None


def test_high_volume_by_raw_count_not_only_page_count() -> None:
    findings = [_p012_finding(page=1) for _ in range(P012_DOCUMENT_SUMMARY_MIN_RAW_FINDINGS)]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P012"]
    assert len(cards) == 1
    assert "Document-wide" in cards[0].location_label


def test_document_summary_includes_compact_page_ranges() -> None:
    pages = [3, 4, 7, 8, 9, 10, 12, 15, 18]
    stats = build_p012_presentation_stats({page: 1 for page in pages})
    compact = compact_page_list(pages)
    assert compact == "3-4, 7-10, 12, 15, 18"
    assert compact in stats.pages_compact


def test_document_summary_has_no_private_leaks() -> None:
    findings = _high_volume_findings(per_page=2)
    view = build_report_view(_payload(findings))
    card = [f for f in view.findings if f.rule_id == "P012"][0]
    forbidden = (
        "secret note",
        "Private reviewer",
        "Reviewer:",
        "72.0",
        "100.0",
        "Text",
    )
    for text in (
        card.location_label,
        card.polished_comment,
        card.suggested_fix,
        card.detailed_explanation,
        card.no_highlight_reason or "",
    ):
        for token in forbidden:
            assert token not in text


def test_markdown_and_web_align_on_document_summary(tmp_path: Path) -> None:
    findings = _high_volume_findings()
    payload = _payload(findings)
    view = build_report_view(payload)
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert text.count("### Problem") == len(view.findings)
    problems_section = text.split("## Findings by Rule")[0]
    assert "- Location: `Document-wide —" in problems_section
    assert problems_section.count("### Problem") == 1
    assert "Affected pages include:" in text
    assert "Remove, resolve, or flatten" in text
    assert len([f for f in view.findings if f.rule_id == "P012"]) == 1


def test_raw_p012_findings_unchanged_in_payload() -> None:
    findings = _high_volume_findings(per_page=2)
    payload = _payload(findings)
    raw_count = len(payload["findings"])
    build_report_view(payload)
    assert len(payload["findings"]) == raw_count
    assert payload["metadata"]["total_findings"] == raw_count


def test_document_summary_representative_page_action_wording() -> None:
    findings = _high_volume_findings()
    view = build_report_view(_payload(findings))
    card = [f for f in view.findings if f.rule_id == "P012"][0]
    assert card.page == 1
    assert "representative" in (card.no_highlight_reason or "").lower()
    assert card.action_label is not None
