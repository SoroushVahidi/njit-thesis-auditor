"""Suggested fixes refer to the flagged target and never quote a partial title as complete."""

from njit_auditor.polished_comments import resolve_suggested_fix_for_display
from njit_auditor.title_case_student_preview import p020_short_suggested_fix


def test_p020_connector_ending_uses_word_correction_for_wrapped_heading() -> None:
    fix = p020_short_suggested_fix(
        "need", "Need", "1.1 Synthetic Importance of Proteins and need for Measurement and"
    )
    assert fix == 'Change "need" to "Need" in this heading.'


def test_p020_truncated_heading_uses_word_correction() -> None:
    fix = p020_short_suggested_fix(
        "need", "Need", "A Synthetic Heading That Includes need and Many More Words " * 2
    )
    assert fix == 'Change "need" to "Need" in this heading.'


def test_p020_complete_heading_can_still_show_a_full_rewrite() -> None:
    fix = p020_short_suggested_fix("need", "Need", "1.1 Why We need Measurement")
    assert fix == 'Change "1.1 Why We need Measurement" to "1.1 Why We Need Measurement".'


def test_p039_fix_only_mentions_the_affected_hierarchy_level() -> None:
    assert resolve_suggested_fix_for_display(
        "P039", "toc_l3_not_indented_relative_to_l2"
    ) == "Indent the highlighted level-3 TOC entries to the right of level-2 entries."
    assert resolve_suggested_fix_for_display(
        "P039", "toc_l2_not_indented_relative_to_l1"
    ) == "Indent the highlighted level-2 TOC entries to the right of level-1 entries."
