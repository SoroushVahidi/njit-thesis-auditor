"""Tests for grouped high-volume warning location clarity and deduplication."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.high_volume_student_preview import (
    abstract_indent_location_label,
    consume_grouped_finding_display_slot,
    font_location_label,
    grouped_finding_display_dedup_key,
    margin_location_label,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, enriched_pdf_location_label


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def test_margin_location_label_names_page_and_side() -> None:
    label = margin_location_label(
        {"side": "right_margin"},
        11,
        bbox_label="Right margin area",
    )
    assert label == "Page 11 — right margin"


def test_font_location_label_names_page_area_and_issue_kind() -> None:
    label = font_location_label(
        "possible_body_font_family_issue",
        {},
        7,
        bbox_label="Body area",
    )
    assert label == "Page 7 — body text, possible font family issue"


def test_abstract_indent_location_label_names_paragraph() -> None:
    label = abstract_indent_location_label(
        "abstract_subsequent_paragraph_not_indented",
        {"paragraph_index": "1"},
        1,
    )
    assert label == "Page 1 — Abstract, paragraph 2"


def test_enriched_location_p011_uses_margin_side_not_body_area_alone() -> None:
    label = enriched_pdf_location_label(
        "P011",
        "margin_boundary_violation",
        {"side": "left_margin"},
        4,
        bbox_label="Body area",
    )
    assert label == "Page 4 — left margin"


def test_distinct_p044_paragraphs_have_distinct_locations() -> None:
    findings = [
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=1,
            message="Abstract indent issue.",
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "paragraph_index": "1",
                "bbox": "108.0,200.0,540.0,212.0",
            },
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=1,
            message="Abstract indent issue.",
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "paragraph_index": "2",
                "bbox": "108.0,500.0,540.0,512.0",
            },
        ),
    ]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P044"]
    assert len(cards) == 2
    locations = {card.location_label for card in cards}
    assert locations == {
        "Page 1 — Abstract, paragraph 2",
        "Page 1 — Abstract, paragraph 3",
    }


def test_exact_duplicate_p011_findings_produce_one_visible_card() -> None:
    duplicate = AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=11,
        message="Margin issue.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "bbox": "151.7,717.2,175.7,729.2",
        },
    )
    view = build_report_view(_payload([duplicate, duplicate]))
    cards = [f for f in view.findings if f.rule_id == "P011"]
    assert len(cards) == 1
    assert cards[0].location_label == "Page 11 — right margin"


def test_p011_and_p044_on_same_page_have_distinguishable_locations() -> None:
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "right_margin",
                "bbox": "500.0,400.0,540.0,412.0",
            },
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=1,
            message="Abstract indent issue.",
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "paragraph_index": "1",
                "bbox": "108.0,200.0,540.0,212.0",
            },
        ),
    ]
    view = build_report_view(_payload(findings))
    p011 = next(f for f in view.findings if f.rule_id == "P011")
    p044 = next(f for f in view.findings if f.rule_id == "P044")
    assert p011.location_label == "Page 1 — right margin"
    assert p044.location_label == "Page 1 — Abstract, paragraph 2"
    assert p011.location_label != p044.location_label


def test_grouped_dedup_key_distinguishes_paragraph_index() -> None:
    base = {
        "issue_type": "abstract_subsequent_paragraph_not_indented",
        "bbox": "108.0,200.0,540.0,212.0",
    }
    key_a = grouped_finding_display_dedup_key(
        "P044",
        "abstract_subsequent_paragraph_not_indented",
        {**base, "paragraph_index": "1"},
        page=1,
    )
    key_b = grouped_finding_display_dedup_key(
        "P044",
        "abstract_subsequent_paragraph_not_indented",
        {**base, "paragraph_index": "2"},
        page=1,
    )
    assert key_a != key_b


def test_consume_grouped_display_slot_suppresses_second_exact_duplicate() -> None:
    seen: set[tuple] = set()
    details = {
        "issue_type": "abstract_subsequent_paragraph_not_indented",
        "paragraph_index": "1",
        "bbox": "151.7,717.2,175.7,729.2",
    }
    assert (
        consume_grouped_finding_display_slot(
            "P044",
            "abstract_subsequent_paragraph_not_indented",
            details,
            seen,
            page=11,
        )
        is True
    )
    assert (
        consume_grouped_finding_display_slot(
            "P044",
            "abstract_subsequent_paragraph_not_indented",
            details,
            seen,
            page=11,
        )
        is False
    )


def test_markdown_report_suppresses_exact_duplicate_p011_problems(tmp_path: Path) -> None:
    duplicate = AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=11,
        message="Margin issue.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "bbox": "151.7,717.2,175.7,729.2",
        },
    )
    output_path = tmp_path / "report.md"
    write_markdown_report([duplicate, duplicate], {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert text.count("### Problem") == 1


def test_grouped_warning_student_facing_text_has_no_raw_coordinates() -> None:
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "bbox": "108.4,129.0,540.4,140.9",
            },
        )
    ]
    view = build_report_view(_payload(findings))
    card = view.findings[0]
    assert "108.4" not in card.location_label
    assert "108.4" not in card.polished_comment
