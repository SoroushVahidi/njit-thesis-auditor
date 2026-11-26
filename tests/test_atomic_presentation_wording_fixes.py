"""Regression tests for the Ester atomic-presentation wording/metadata cleanup pass.

Covers concrete, independently-verified presentation bugs closed in this pass:

- P014 ("frontmatter_heading_layout_issue" / "frontmatter_heading_not_centered")
  had zero entry anywhere in polished_comments.py and fell to the deepest
  generic fallback, which doubled the word "issue" (the machine issue_type
  string already ends in "_issue", and the fallback sentence appends another
  "issue" after it) — e.g. "...frontmatter heading layout issue issue on page
  5." This also proved that a rule can be invisible to the existing
  `_KNOWN_WORDING_GAPS` ratchet in test_rule_registry_consistency.py when its
  catalog entry has no populated `issue_types` field.
- P061's two cross-page templates referenced `{page_range}`, but neither
  detector (pdf_lot_lof_cross_page_entry_ordering.py) ever populates the
  `run_start_page`/`run_end_page` detail keys `_safe_page_range()` reads —
  so the template always rendered the literal fallback text "listed pages"
  ("...across pages listed pages.").
- P057/P059/P062/P065/P078/P034 issue types fell through to generic,
  cross-issue-type-identical wording (comment and/or explanation) instead of
  a specific message, per docs/RULE_ARCHITECTURE.md's documented wording debt.
- Three orphaned dict entries (`("P030", "toc_missing_continued_heading")`,
  `("P033", "title_page_mismatch")`, `("P033", "title_consistency_mismatch")`)
  existed in three separate files but are never emitted by any detector —
  confirmed dead by grepping every detector module for the literal strings.

None of these changes touch detector logic, thresholds, confidence, or rule
IDs — they are wording/dict-entry additions and deletions only.
"""

from __future__ import annotations

import pytest

from njit_auditor.finding_explanations import _EXPLANATION_TEMPLATES
from njit_auditor.issue_type_explanations import _RULE_ISSUE_EXPLANATIONS, explain_issue_type
from njit_auditor.polished_comments import (
    _ISSUE_TEMPLATES,
    _remediation_by_rule,
    build_polished_comment,
    resolve_suggested_fix_for_display,
)


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "expected"),
    [
        (
            "P063",
            "single_appendix_uses_letter_label",
            "For a sole appendix, remove the letter after APPENDIX in the heading.",
        ),
        (
            "P063",
            "multiple_appendix_missing_letter",
            "Add the missing letter to the appendix heading in alphabetical order.",
        ),
        (
            "P063",
            "appendix_letter_sequence_gap",
            "Correct the appendix labels so their letters are consecutive.",
        ),
        (
            "P063",
            "appendix_letter_sequence_repeat",
            "Give each appendix a distinct letter in alphabetical order.",
        ),
        (
            "P064",
            "references_entry_indentation_inconsistent",
            "Use either hanging indent or flush-left consistently for all reference entries, "
            "following the style agreed with your advisor.",
        ),
        (
            "P064",
            "references_entry_spacing_inconsistent",
            "Use consistent double spacing between consecutive reference entries.",
        ),
    ],
)
def test_appendix_heading_and_reference_fixes_are_specific(
    rule_id: str, issue_type: str, expected: str
) -> None:
    assert resolve_suggested_fix_for_display(rule_id, issue_type) == expected
    generic_fix = _remediation_by_rule()[rule_id]
    assert resolve_suggested_fix_for_display(rule_id, issue_type, existing=generic_fix) == expected


def test_appendix_and_references_keep_other_recorded_advice() -> None:
    fix = "Apply the same indentation to the continuation lines on this page."
    assert resolve_suggested_fix_for_display(
        "P064", "references_entry_indentation_inconsistent", existing=fix
    ) == fix
    assert resolve_suggested_fix_for_display(
        "P064", "references_section_heading_not_detected"
    ) == _remediation_by_rule()["P064"]
    assert resolve_suggested_fix_for_display(
        "P063", "appendix_subsection_missing_letter_prefix"
    ) == "Add the owning appendix's letter before the leading dot in the subsection number."

# ---------------------------------------------------------------------------
# P014 double-"issue" bug
# ---------------------------------------------------------------------------


def test_p014_layout_issue_comment_has_no_doubled_issue_word() -> None:
    comment = build_polished_comment(
        rule_id="P014",
        issue_type="frontmatter_heading_layout_issue",
        page=5,
        details={
            "heading": "DEDICATION",
            "centered": "False",
            "near_top": "True",
            "bold": "True",
            "all_caps": "True",
        },
    )
    assert "issue issue" not in comment
    assert "not centered" in comment


def test_p014_not_centered_comment_has_no_doubled_issue_word() -> None:
    comment = build_polished_comment(
        rule_id="P014",
        issue_type="frontmatter_heading_not_centered",
        page=5,
        details={
            "heading": "APPROVAL PAGE",
            "centered": "False",
            "near_top": "True",
            "bold": "True",
            "all_caps": "True",
        },
    )
    assert "issue issue" not in comment
    assert "not centered" in comment


def test_p014_comment_never_echoes_extracted_heading_text() -> None:
    """The comment must be stable regardless of which named heading was
    flagged — it must never embed details["heading"] verbatim."""
    for heading in ("ABSTRACT", "DEDICATION", "APPROVAL PAGE", "ACKNOWLEDGEMENTS"):
        comment = build_polished_comment(
            rule_id="P014",
            issue_type="frontmatter_heading_layout_issue",
            page=1,
            details={
                "heading": heading,
                "centered": "False",
                "near_top": "True",
                "bold": "True",
                "all_caps": "True",
            },
        )
        assert heading not in comment


def test_p014_both_issue_types_never_hit_generic_fallback() -> None:
    """P014 is handled via a build_polished_comment() dispatch branch (like
    P011/P012/P026), not an _ISSUE_TEMPLATES dict entry — so the coverage
    check here is behavioral (no generic-fallback sentence), matching the
    same convention documented for P066/P067 in test_rule_registry_consistency.py."""
    for issue_type in (
        "frontmatter_heading_layout_issue",
        "frontmatter_heading_not_centered",
    ):
        comment = build_polished_comment(
            rule_id="P014",
            issue_type=issue_type,
            page=1,
            details={"centered": "False", "near_top": "True", "bold": "True", "all_caps": "True"},
        )
        assert "This automated check found a possible" not in comment


# ---------------------------------------------------------------------------
# P061 {page_range} -> {page} wording fix
# ---------------------------------------------------------------------------


def test_p061_lot_comment_never_says_listed_pages() -> None:
    comment = build_polished_comment(
        rule_id="P061",
        issue_type="lot_cross_page_entry_numbers_not_nondecreasing",
        page=12,
        details={"page_count": "3", "entry_count": "5"},
    )
    assert "listed pages" not in comment
    assert "page 12" in comment


def test_p061_lof_comment_never_says_listed_pages() -> None:
    comment = build_polished_comment(
        rule_id="P061",
        issue_type="lof_cross_page_entry_numbers_not_nondecreasing",
        page=8,
        details={"page_count": "2", "entry_count": "4"},
    )
    assert "listed pages" not in comment
    assert "page 8" in comment


# ---------------------------------------------------------------------------
# Newly closed comment-template gaps: specific, non-generic, no raw leak
# ---------------------------------------------------------------------------

_NEWLY_TEMPLATED_PAIRS = [
    ("P057", "lot_page_numbers_not_nondecreasing"),
    ("P057", "lof_page_numbers_not_nondecreasing"),
    ("P059", "lot_entry_numbers_not_nondecreasing"),
    ("P059", "lof_entry_numbers_not_nondecreasing"),
    ("P062", "toc_cross_page_entry_numbers_not_nondecreasing"),
    ("P065", "dedication_text_not_centered"),
    ("P065", "dedication_text_not_italic"),
    ("P078", "abstract_pdf_forbidden_term"),
    ("P078", "abstract_pdf_first_person_pronoun"),
    ("P034", "copyright_top_margin_header_text"),
    ("P034", "copyright_author_mismatch"),
]


def test_newly_templated_pairs_are_registered_in_issue_templates() -> None:
    for rule_id, issue_type in _NEWLY_TEMPLATED_PAIRS:
        assert (rule_id, issue_type) in _ISSUE_TEMPLATES, (
            f"{rule_id}/{issue_type} should have a specific _ISSUE_TEMPLATES entry"
        )


def test_newly_templated_pairs_never_hit_the_generic_fallback_sentence() -> None:
    for rule_id, issue_type in _NEWLY_TEMPLATED_PAIRS:
        comment = build_polished_comment(
            rule_id=rule_id, issue_type=issue_type, page=3, details={}
        )
        assert "This automated check found a possible" not in comment, (
            f"{rule_id}/{issue_type} fell through to the generic fallback: {comment!r}"
        )


# ---------------------------------------------------------------------------
# Newly closed explanation-side gaps: specific, no "This issue type (...)" leak
# ---------------------------------------------------------------------------

_NEWLY_EXPLAINED_PAIRS = [
    ("P057", "lot_page_numbers_not_nondecreasing"),
    ("P057", "lof_page_numbers_not_nondecreasing"),
    ("P059", "lot_entry_numbers_not_nondecreasing"),
    ("P059", "lof_entry_numbers_not_nondecreasing"),
    ("P061", "lot_cross_page_entry_numbers_not_nondecreasing"),
    ("P061", "lof_cross_page_entry_numbers_not_nondecreasing"),
    ("P062", "toc_cross_page_entry_numbers_not_nondecreasing"),
    ("P034", "copyright_top_margin_header_text"),
    ("P034", "copyright_author_mismatch"),
]


def test_newly_explained_pairs_are_registered() -> None:
    for rule_id, issue_type in _NEWLY_EXPLAINED_PAIRS:
        assert (rule_id, issue_type) in _RULE_ISSUE_EXPLANATIONS, (
            f"{rule_id}/{issue_type} should have a specific explanation entry"
        )


def test_newly_explained_pairs_never_leak_machine_issue_type_wording() -> None:
    """No student-facing explanation should use the raw-issue-type fallback
    sentence — a softer, still-real leak of internal naming (see
    docs/RULE_ARCHITECTURE.md and the audit that produced this test file)."""
    for rule_id, issue_type in _NEWLY_EXPLAINED_PAIRS:
        explanation = explain_issue_type(rule_id, issue_type)
        assert "was flagged by an automated check" not in explanation, (
            f"{rule_id}/{issue_type} fell through to the generic issue-type-naming "
            f"fallback: {explanation!r}"
        )
        assert explanation and explanation.strip()


# ---------------------------------------------------------------------------
# Orphaned/dead dict entries removed (never emitted by any detector)
# ---------------------------------------------------------------------------

_CONFIRMED_DEAD_PAIRS = [
    ("P030", "toc_missing_continued_heading"),
    ("P033", "title_page_mismatch"),
    ("P033", "title_consistency_mismatch"),
]


def test_confirmed_dead_pairs_removed_from_issue_templates() -> None:
    for pair in _CONFIRMED_DEAD_PAIRS:
        assert pair not in _ISSUE_TEMPLATES


def test_confirmed_dead_pairs_removed_from_rule_issue_explanations() -> None:
    for pair in _CONFIRMED_DEAD_PAIRS:
        assert pair not in _RULE_ISSUE_EXPLANATIONS


def test_confirmed_dead_pairs_removed_from_explanation_templates() -> None:
    for pair in _CONFIRMED_DEAD_PAIRS:
        assert pair not in _EXPLANATION_TEMPLATES


def test_p030_and_p033_real_issue_types_still_covered() -> None:
    """Guard against accidentally deleting the real (non-orphaned) sibling
    entries alongside the dead ones."""
    assert ("P030", "missing_continued_heading") in _ISSUE_TEMPLATES
    assert ("P033", "frontmatter_title_mismatch") in _EXPLANATION_TEMPLATES
