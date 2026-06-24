"""Tests for duplicate-looking warning distinctness and P020 presentation clarity."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, enriched_pdf_location_label
from njit_auditor.title_case_student_preview import (
    consume_p020_display_slot,
    p020_display_dedup_key,
    sanitize_title_case_line_preview,
)


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def _p020_finding(
    *,
    page: int = 1,
    flagged_word: str = "study",
    corrected_word: str = "Study",
    line_preview: str = "",
    bbox: str = "108.0,100.0,500.0,120.0",
    source: str = "heading",
    expected_or_reason: str = "major_word_requires_capital",
) -> AuditFinding:
    details: dict[str, str] = {
        "issue_type": "possible_title_capitalization_issue",
        "source": source,
        "expected_or_reason": expected_or_reason,
        "confidence": "medium",
        "flagged_word": flagged_word,
        "corrected_word": corrected_word,
        "bbox": bbox,
    }
    if line_preview:
        details["line_preview"] = line_preview
    return AuditFinding(
        rule_id="P020",
        severity=Severity.WARNING,
        page=page,
        message="Title case issue.",
        details=details,
    )


def test_sanitize_title_case_line_preview_collapses_and_caps_length() -> None:
    long_text = "A" * 100
    assert sanitize_title_case_line_preview("  Exoskeleton   Study   Design  ") == (
        "Exoskeleton Study Design"
    )
    assert len(sanitize_title_case_line_preview(long_text)) <= 72
    assert sanitize_title_case_line_preview(long_text).endswith("...")


def test_exact_duplicate_p020_findings_produce_one_visible_card() -> None:
    duplicate = _p020_finding(
        line_preview="Synthetic Exoskeleton Study Marker ABC",
    )
    findings = [duplicate, duplicate]
    view = build_report_view(_payload(findings))
    p020_cards = [f for f in view.findings if f.rule_id == "P020"]
    assert len(p020_cards) == 1


def test_distinct_p020_same_word_different_headings_remain_separate() -> None:
    findings = [
        _p020_finding(
            line_preview="Synthetic Exoskeleton Study Marker ABC",
            bbox="108.0,100.0,500.0,120.0",
        ),
        _p020_finding(
            line_preview="Synthetic Exoskeleton Study Marker DEF",
            bbox="108.0,200.0,500.0,220.0",
        ),
    ]
    view = build_report_view(_payload(findings))
    p020_cards = [f for f in view.findings if f.rule_id == "P020"]
    assert len(p020_cards) == 2
    locations = {card.location_label for card in p020_cards}
    assert len(locations) == 2
    assert all("Synthetic Exoskeleton Study Marker" in loc for loc in locations)
    assert locations != {
        "Page 1 — heading \"Synthetic Exoskeleton Study Marker ABC\"",
        "Page 1 — heading \"Synthetic Exoskeleton Study Marker ABC\"",
    }


def test_p020_location_label_names_affected_heading() -> None:
    label = enriched_pdf_location_label(
        "P020",
        "possible_title_capitalization_issue",
        {
            "line_preview": "Synthetic Exoskeleton Study Marker ABC",
            "source": "heading",
        },
        1,
    )
    assert label == 'Page 1 — heading "Synthetic Exoskeleton Study Marker ABC"'


def test_p020_comment_names_heading_and_flagged_word() -> None:
    view = build_report_view(
        _payload(
            [
                _p020_finding(
                    line_preview="Synthetic Exoskeleton Study Marker ABC",
                )
            ]
        )
    )
    card = view.findings[0]
    assert "Synthetic Exoskeleton Study Marker ABC" in card.polished_comment
    assert "'study'" in card.polished_comment
    assert "'Study'" in card.polished_comment


def test_p020_dedup_key_uses_rounded_bbox() -> None:
    details = {
        "issue_type": "possible_title_capitalization_issue",
        "flagged_word": "study",
        "corrected_word": "Study",
        "expected_or_reason": "major_word_requires_capital",
        "source": "heading",
        "bbox": "108.04,100.02,500.01,120.08",
    }
    key_a = p020_display_dedup_key(details, page=1)
    details["bbox"] = "108.01,100.01,500.01,120.06"
    key_b = p020_display_dedup_key(details, page=1)
    assert key_a == key_b

    details["bbox"] = "108.0,100.0,500.0,220.0"
    key_other = p020_display_dedup_key(details, page=1)
    assert key_a != key_other


def test_consume_p020_display_slot_suppresses_second_exact_duplicate() -> None:
    seen: set[tuple] = set()
    details = {
        "issue_type": "possible_title_capitalization_issue",
        "flagged_word": "study",
        "corrected_word": "Study",
        "expected_or_reason": "major_word_requires_capital",
        "source": "heading",
        "bbox": "108.0,100.0,500.0,120.0",
    }
    assert consume_p020_display_slot(details, seen, page=1) is True
    assert consume_p020_display_slot(details, seen, page=1) is False


def test_markdown_report_suppresses_exact_duplicate_p020_problems(tmp_path) -> None:
    duplicate = _p020_finding(line_preview="Synthetic Exoskeleton Study Marker ABC")
    output_path = tmp_path / "report.md"
    write_markdown_report([duplicate, duplicate], {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert text.count("### Problem") == 1
    assert "Synthetic Exoskeleton Study Marker ABC" in text


def test_markdown_report_keeps_distinct_p020_occurrences(tmp_path) -> None:
    findings = [
        _p020_finding(
            line_preview="Synthetic Exoskeleton Study Marker ABC",
            bbox="108.0,100.0,500.0,120.0",
        ),
        _p020_finding(
            line_preview="Synthetic Exoskeleton Study Marker DEF",
            bbox="108.0,200.0,500.0,220.0",
        ),
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert text.count("### Problem") == 2
    assert "Marker ABC" in text
    assert "Marker DEF" in text


def test_p020_student_facing_text_has_no_raw_coordinates() -> None:
    findings = [
        _p020_finding(
            line_preview="Synthetic Exoskeleton Study Marker ABC",
            bbox="108.0,100.0,500.0,120.0",
        )
    ]
    view = build_report_view(_payload(findings))
    card = view.findings[0]
    assert "108.0" not in card.polished_comment
    assert "108.0" not in card.location_label
    assert "500.0" not in card.detailed_explanation
