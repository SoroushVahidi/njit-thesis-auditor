"""Tests for live-review warning fixes: P018/P020/P036 brevity and dedup."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, enriched_pdf_location_label
from njit_auditor.title_case_student_preview import (
    consume_p020_display_slot,
    p020_display_dedup_key,
    p020_short_likely_problem,
    p020_short_suggested_fix,
)
from njit_auditor.toc_list_student_preview import (
    is_toc_structural_column_label,
    p018_short_likely_problem,
    p036_short_likely_problem,
    p036_short_suggested_fix,
    sanitize_toc_list_entry_preview,
)


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def _p020_finding(
    *,
    page: int = 1,
    flagged_word: str = "study",
    corrected_word: str = "Study",
    line_preview: str = "A study of perceptions, readiness, benefits, and barriers related to",
    bbox: str = "108.0,100.0,500.0,120.0",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P020",
        severity=Severity.WARNING,
        page=page,
        message="Title case issue.",
        details={
            "issue_type": "possible_title_capitalization_issue",
            "source": "heading",
            "expected_or_reason": "major_word_requires_capital",
            "confidence": "medium",
            "flagged_word": flagged_word,
            "corrected_word": corrected_word,
            "line_preview": line_preview,
            "bbox": bbox,
        },
    )


def _p036_finding(
    *,
    page: int = 12,
    previous: str = "1 INTRODUCTION ............................",
    next_entry: str = "Background and Context ....................",
    bbox: str = "72.0,500.0,540.0,512.0",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P036",
        severity=Severity.WARNING,
        page=page,
        message="Spacing issue.",
        details={
            "issue_type": "toc_inter_entry_spacing_too_tight",
            "section_type": "table_of_contents",
            "previous_entry_preview": previous,
            "next_entry_preview": next_entry,
            "gap_points": "2.4",
            "required_gap_points": "16.8",
            "gap_ratio": "0.20",
            "entry_pair_index": "1",
            "bbox": bbox,
        },
    )


def _p018_finding(
    *,
    issue_type: str = "inconsistent_hierarchy_indent",
    preview: str = "Background and Context",
    bbox: str = "108.0,620.0,420.0,632.0",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P018",
        severity=Severity.WARNING,
        page=12,
        message="TOC alignment issue.",
        details={
            "issue_type": issue_type,
            "page_type": "table_of_contents",
            "affected_entry_preview": preview,
            "affected_entry_count": "3",
            "worst_delta_pt": "12.5",
            "bbox": bbox,
        },
    )


def test_sanitize_toc_list_entry_preview_strips_leader_dots() -> None:
    assert sanitize_toc_list_entry_preview("1 INTRODUCTION ..........................") == (
        "1 INTRODUCTION"
    )
    assert sanitize_toc_list_entry_preview("Problem Statement ..........................") == (
        "Problem Statement"
    )


def test_p036_short_comment_does_not_repeat_suggested_fix() -> None:
    comment = p036_short_likely_problem(
        "1 INTRODUCTION ..........................",
        "Background and Context ....................",
    )
    fix = p036_short_suggested_fix()
    assert "Add visible double spacing" in fix
    assert "Add visible double spacing" not in comment
    assert "2.4pt" not in comment
    assert "Background and Context" in comment
    assert "................" not in comment


def test_p020_duplicate_same_heading_word_suppressed() -> None:
    findings = [
        _p020_finding(bbox="108.0,100.0,500.0,120.0"),
        _p020_finding(bbox="108.0,105.0,500.0,125.0"),
    ]
    view = build_report_view(_payload(findings))
    p020_cards = [card for card in view.findings if card.rule_id == "P020"]
    assert len(p020_cards) == 1


def test_p020_distinct_headings_remain_separate() -> None:
    findings = [
        _p020_finding(
            line_preview="A study of perceptions, readiness, benefits, and barriers related to",
            flagged_word="study",
            corrected_word="Study",
        ),
        _p020_finding(
            line_preview="exoskeleton adoption in new jersey's warehousing sector",
            flagged_word="exoskeleton",
            corrected_word="Exoskeleton",
        ),
    ]
    view = build_report_view(_payload(findings))
    p020_cards = [card for card in view.findings if card.rule_id == "P020"]
    assert len(p020_cards) == 2


def test_p020_dedup_key_uses_heading_preview_not_bbox() -> None:
    details = {
        "issue_type": "possible_title_capitalization_issue",
        "flagged_word": "study",
        "corrected_word": "Study",
        "expected_or_reason": "major_word_requires_capital",
        "source": "heading",
        "line_preview": "A study of perceptions",
        "bbox": "108.0,100.0,500.0,120.0",
    }
    key_a = p020_display_dedup_key(details, page=1)
    details["bbox"] = "108.0,200.0,500.0,220.0"
    key_b = p020_display_dedup_key(details, page=1)
    assert key_a == key_b

    details["line_preview"] = "Different heading line"
    key_other = p020_display_dedup_key(details, page=1)
    assert key_a != key_other


def test_p020_short_main_card_wording() -> None:
    comment = p020_short_likely_problem("study", "Study")
    fix = p020_short_suggested_fix(
        "study",
        "Study",
        "A study of perceptions, readiness, benefits, and barriers related to",
    )
    assert comment == "Likely problem: In this heading, 'study' should be capitalized as 'Study'."
    assert "Title Case" not in comment
    assert fix == 'Change "study" to "Study" in this heading.'


def test_p020_short_main_card_wording_table_title_source() -> None:
    """Regression (Ester Sample B page 80): a table-title P020 finding must say
    "table title", not "heading" — the two follow different NJIT formatting rules
    and must never be described with each other's wording."""
    comment = p020_short_likely_problem("study", "Study", source="caption")
    fix = p020_short_suggested_fix(
        "study",
        "Study",
        "A study of perceptions, readiness, benefits, and barriers related to",
        source="caption",
    )
    assert comment == (
        "Likely problem: In this table title, 'study' should be capitalized as 'Study'."
    )
    assert "heading" not in comment
    assert "A Study of perceptions" in fix


def test_p020_suggested_fix_never_edits_inside_larger_word() -> None:
    # Regression: replacing the flagged token "n" -> "N" must never alter the
    # "n" inside "Linear" (which previously produced "LiNear").
    fix = p020_short_suggested_fix(
        "n",
        "N",
        "Multiple Linear Regression Predicting Readiness (n = 97)",
    )
    assert "LiNear" not in fix
    assert "Linear" in fix


def test_p020_suggested_fix_replaces_only_whole_word_token() -> None:
    # Whole-token replacement must not edit a flagged stem inside a larger word.
    fix = p020_short_suggested_fix(
        "form",
        "Form",
        "Comparison form Prior Studies within Formulas",
    )
    assert fix == (
        'Change "Comparison form Prior Studies within Formulas" to '
        '"Comparison Form Prior Studies within Formulas".'
    )
    assert "Formulas" in fix
    assert "within Formulas" in fix


def test_p018_short_main_card_and_location_label() -> None:
    label = enriched_pdf_location_label(
        "P018",
        "inconsistent_hierarchy_indent",
        {
            "page_type": "table_of_contents",
            "affected_entry_preview": "Background and Context",
        },
        12,
    )
    assert label == 'Page 12 — Table of Contents entry "Background and Context"'
    assert p018_short_likely_problem("inconsistent_hierarchy_indent").startswith(
        "Likely problem: This entry is indented differently"
    )


def test_p018_highlight_when_bbox_present() -> None:
    view = build_report_view(_payload([_p018_finding()]))
    card = view.findings[0]
    assert card.has_highlight is True
    assert card.action_label == "Open highlighted PDF page"


def test_p018_structural_chapter_missing_page_number_suppressed() -> None:
    assert is_toc_structural_column_label("CHAPTER")
    assert is_toc_structural_column_label("Chapter")
    finding = _p018_finding(issue_type="missing_page_number", preview="Chapter", bbox="")
    view = build_report_view(_payload([finding]))
    assert not any(card.rule_id == "P018" for card in view.findings)


def test_p036_visible_card_uses_short_wording(tmp_path) -> None:
    view = build_report_view(_payload([_p036_finding()]))
    card = view.findings[0]
    assert "visible double spacing" in card.polished_comment.lower()
    assert card.suggested_fix == p036_short_suggested_fix()
    assert "................" not in card.location_label

    md_path = tmp_path / "report.md"
    write_markdown_report([_p036_finding()], {"audit_type": "pdf"}, md_path)
    text = md_path.read_text(encoding="utf-8")
    assert "visible double spacing" in text
    assert "................" not in text


def test_consume_p020_display_slot_still_suppresses_exact_duplicate() -> None:
    seen: set[tuple] = set()
    details = {
        "issue_type": "possible_title_capitalization_issue",
        "flagged_word": "study",
        "corrected_word": "Study",
        "expected_or_reason": "major_word_requires_capital",
        "source": "heading",
        "line_preview": "A study of perceptions",
    }
    assert consume_p020_display_slot(details, seen, page=1) is True
    assert consume_p020_display_slot(details, seen, page=1) is False
