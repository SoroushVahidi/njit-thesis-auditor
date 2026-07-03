"""Regression tests for bespoke long-tail remediation wording."""

from __future__ import annotations

import re

import pytest

from njit_auditor.finding_explanations import (
    build_detailed_explanation,
    get_action_label,
)
from njit_auditor.issue_type_explanations import explain_issue_type
from njit_auditor.polished_comments import build_polished_comment

_GENERIC_COMMENT_MARKERS = (
    "This check (",
    "found a possible",
    "flagged issue type",
    "Formatting check",
)

_BANNED_FALLBACK_PHRASE = "flagged issue type"

# High-impact long-tail issue types upgraded in this PR (30 pairs).
UPGRADED_ISSUE_TYPES: tuple[tuple[str, str], ...] = (
    ("P015", "missing_later_indent"),
    ("P017", "unexpected_terminal_period"),
    ("P017", "missing_terminal_punctuation"),
    ("P017", "possible_sentence_case_issue"),
    ("P017", "possible_title_case_issue"),
    ("P018", "misaligned_page_number_column"),
    ("P018", "missing_page_number"),
    ("P018", "inconsistent_leader_dots"),
    ("P018", "inconsistent_hierarchy_indent"),
    ("P021", "abstract_word_count_exceeded"),
    ("P024", "toc_level_capitalization"),
    ("P024", "list_of_tables_title_case"),
    ("P024", "list_of_figures_sentence_case"),
    ("P024", "unexpected_terminal_punctuation"),
    ("P074", "title_page_graduation_month_invalid"),
    ("P035", "table_caption_not_above_body"),
    ("P035", "figure_caption_not_below_body"),
    ("P035", "table_body_not_centered"),
    ("P035", "figure_body_not_centered"),
    ("P039", "toc_l2_not_indented_relative_to_l1"),
    ("P039", "toc_l3_not_indented_relative_to_l2"),
    ("P040", "lof_entry_missing_terminal_punctuation"),
    ("P041", "dedication_top_margin_header_text"),
    ("P043", "acknowledgements_first_paragraph_indented"),
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"),
    ("P044", "abstract_first_paragraph_indented"),
    ("P044", "abstract_subsequent_paragraph_not_indented"),
    ("P053", "lot_entry_has_terminal_period"),
    ("P054", "toc_entry_has_terminal_period"),
    ("P055", "lot_entry_is_figure"),
    ("P055", "lof_entry_is_table"),
    ("P058", "toc_page_numbers_not_nondecreasing"),
    ("P060", "toc_entry_numbers_not_nondecreasing"),
    ("P064", "references_section_heading_not_detected"),
    ("P064", "references_entry_indentation_inconsistent"),
    ("P064", "references_entry_spacing_inconsistent"),
    ("P068", "approval_page_advisor_role_label_missing"),
    ("P068", "approval_page_signature_blocks_sparse"),
)

# Minimum bespoke signal each upgraded pair must include in its polished comment.
_EXPECTED_COMMENT_SIGNALS: dict[tuple[str, str], tuple[str, ...]] = {
    ("P015", "missing_later_indent"): ("first-line indent",),
    ("P017", "unexpected_terminal_period"): ("terminal period",),
    ("P017", "missing_terminal_punctuation"): ("terminal punctuation",),
    ("P017", "possible_sentence_case_issue"): ("sentence case",),
    ("P017", "possible_title_case_issue"): ("title-case",),
    ("P018", "misaligned_page_number_column"): ("page-number column",),
    ("P018", "missing_page_number"): ("missing", "page number"),
    ("P018", "inconsistent_leader_dots"): ("leader dots",),
    ("P018", "inconsistent_hierarchy_indent"): ("hierarchy", "indent"),
    ("P021", "abstract_word_count_exceeded"): ("words", "limit"),
    ("P024", "toc_level_capitalization"): ("Table of Contents", "capitalization"),
    ("P024", "list_of_tables_title_case"): ("List of Tables", "Title Case"),
    ("P024", "list_of_figures_sentence_case"): ("List of Figures", "sentence case"),
    ("P024", "unexpected_terminal_punctuation"): ("terminal punctuation",),
    ("P074", "title_page_graduation_month_invalid"): ("graduation month",),
    ("P035", "table_caption_not_above_body"): ("table caption", "above"),
    ("P035", "figure_caption_not_below_body"): ("figure caption", "below"),
    ("P035", "table_body_not_centered"): ("table", "centered"),
    ("P035", "figure_body_not_centered"): ("figure", "centered"),
    ("P039", "toc_l2_not_indented_relative_to_l1"): ("level-2", "level-1"),
    ("P039", "toc_l3_not_indented_relative_to_l2"): ("level-3", "level-2"),
    ("P040", "lof_entry_missing_terminal_punctuation"): ("List of Figures", "terminal"),
    ("P041", "dedication_top_margin_header_text"): ("dedication", "top margin"),
    ("P043", "acknowledgements_first_paragraph_indented"): ("Acknowledgements", "first paragraph"),
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): ("Acknowledgements", "indent"),
    ("P044", "abstract_first_paragraph_indented"): ("Abstract", "first paragraph"),
    ("P044", "abstract_subsequent_paragraph_not_indented"): ("Abstract", "indent"),
    ("P053", "lot_entry_has_terminal_period"): ("List of Tables", "period"),
    ("P054", "toc_entry_has_terminal_period"): ("Table of Contents", "period"),
    ("P055", "lot_entry_is_figure"): ("List of Tables", "figure"),
    ("P055", "lof_entry_is_table"): ("List of Figures", "table"),
    ("P058", "toc_page_numbers_not_nondecreasing"): ("ascending", "page numbers"),
    ("P060", "toc_entry_numbers_not_nondecreasing"): ("section numbers",),
    ("P064", "references_section_heading_not_detected"): ("REFERENCES",),
    ("P064", "references_entry_indentation_inconsistent"): ("indentation",),
    ("P064", "references_entry_spacing_inconsistent"): ("spacing",),
    ("P068", "approval_page_advisor_role_label_missing"): ("advisor role label",),
    ("P068", "approval_page_signature_blocks_sparse"): ("signature", "date"),
}


@pytest.mark.parametrize("rule_id,issue_type", UPGRADED_ISSUE_TYPES)
def test_upgraded_issue_type_avoids_generic_polished_comment(
    rule_id: str, issue_type: str
) -> None:
    details: dict[str, str] = {"caption_type": "table"}
    if issue_type == "abstract_word_count_exceeded":
        details = {"word_count": "400", "limit": "350", "inferred_degree_type": "phd"}
    comment = build_polished_comment(
        rule_id=rule_id,
        issue_type=issue_type,
        page=5,
        details=details,
    )
    lowered = comment.lower()
    for marker in _GENERIC_COMMENT_MARKERS:
        assert marker.lower() not in lowered, f"{rule_id}/{issue_type}: found {marker!r}"
    assert _BANNED_FALLBACK_PHRASE not in lowered
    for signal in _EXPECTED_COMMENT_SIGNALS[(rule_id, issue_type)]:
        assert signal.lower() in lowered, f"{rule_id}/{issue_type}: missing {signal!r}"


@pytest.mark.parametrize("rule_id,issue_type", UPGRADED_ISSUE_TYPES)
def test_upgraded_issue_type_has_specific_explanation(
    rule_id: str, issue_type: str
) -> None:
    explanation = build_detailed_explanation(
        rule_id=rule_id,
        issue_type=issue_type,
        page=5,
        details={"caption_type": "table"},
    )
    assert explanation.strip()
    assert "flagged an issue of type" not in explanation
    assert "automated formatting check" not in explanation.lower()


@pytest.mark.parametrize("rule_id,issue_type", UPGRADED_ISSUE_TYPES)
def test_upgraded_issue_type_has_rule_specific_issue_explanation(
    rule_id: str, issue_type: str
) -> None:
    text = explain_issue_type(rule_id, issue_type)
    assert text.strip()
    assert "was flagged by an automated check" not in text
    assert _BANNED_FALLBACK_PHRASE not in text


def test_upgraded_comments_do_not_expose_bbox_coordinates() -> None:
    bbox_pattern = re.compile(r"\b\d+\.?\d*\s*,\s*\d+\.?\d*\s*,\s*\d+\.?\d*\s*,\s*\d+\.?\d*\b")
    for rule_id, issue_type in UPGRADED_ISSUE_TYPES:
        comment = build_polished_comment(
            rule_id=rule_id,
            issue_type=issue_type,
            page=3,
            details={"bbox": "72.0,100.0,540.0,720.0", "caption_type": "figure"},
        )
        assert not bbox_pattern.search(comment)


def test_pdf_action_labels_unchanged() -> None:
    assert get_action_label(has_highlight=True, page=1) == "Open highlighted PDF page"
    assert get_action_label(has_highlight=False, page=1) == "Open original PDF page"
    assert get_action_label(has_highlight=False, page=None) == "Read explanation"


def test_p068_advisor_and_signature_remediations_are_distinct() -> None:
    advisor = build_polished_comment(
        rule_id="P068",
        issue_type="approval_page_advisor_role_label_missing",
        page=2,
        details={},
    )
    sparse = build_polished_comment(
        rule_id="P068",
        issue_type="approval_page_signature_blocks_sparse",
        page=2,
        details={},
    )
    assert "advisor role label" in advisor.lower()
    assert "signature" in sparse.lower() and "date" in sparse.lower()
    assert advisor != sparse
