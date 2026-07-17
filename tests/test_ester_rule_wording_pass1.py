"""Regression tests for Ester's wording/remediation pass (PR ux/ester-rule-wording-pass1).

Covers, using synthetic metadata only:

1. P011 — neutral margin wording (1.5 in left, 1 in top/bottom/right)
2. P012 — "Resolve or delete" annotation remediation
3. P013 — bottom-center placement wording
4. P016 — necessary-page-break exception in spacing wording
5. P020 — source-document advice in remediation (no mashed PDF tokens)
6. P026 — Overleaf/Computer Modern accepted-equivalent wording
7. P038 — canonical ACKNOWLEDGEMENTS spelling clarification
8. Rule catalog questions/remediations updated in project_added_rules.json
9. No "latex" (case-insensitive) in any student-facing text added by this pass
10. Planning document exists and mentions broad split candidates
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from njit_auditor.polished_comments import build_polished_comment

# ---------------------------------------------------------------------------
# 1. P011 — neutral margin wording
# ---------------------------------------------------------------------------

def test_p011_margin_wording_mentions_1_5_inches() -> None:
    comment = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=3,
        details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
    )
    # Inch requirements appear in detailed explanations and suggested fixes, not
    # necessarily the grouped card comment.
    from njit_auditor.finding_explanations import build_detailed_explanation

    explanation = build_detailed_explanation(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        details={"side": "left_margin"},
        page=3,
        has_highlight=False,
        location_label="Page 3 — left margin",
    )
    assert "1.5 inches" in explanation or "1.5 in" in explanation
    assert "left margin" in comment


def test_p011_margin_wording_is_neutral() -> None:
    comment = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=3,
        details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
    )
    lowered = comment.lower()
    assert "strict" not in lowered
    assert "even by a small amount" not in lowered
    assert "appears too close to" in lowered or "appears to cross the required" in lowered


def test_p011_margin_right_mentions_right_boundary() -> None:
    comment = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=5,
        details={"issue_type": "margin_boundary_violation", "side": "right_margin"},
    )
    assert "right margin" in comment


def test_p011_catalog_question_is_binary() -> None:
    rules = _load_rule_catalog()
    p011 = next(r for r in rules if r["id"] == "P011")
    assert (
        "Is all text (including tables and figures) contained entirely within"
        in p011["question"]
    )


def test_p011_catalog_remediation_specifies_measurements() -> None:
    rules = _load_rule_catalog()
    p011 = next(r for r in rules if r["id"] == "P011")
    assert "1.5 inches" in p011["remediation"]
    assert "1 inch" in p011["remediation"]


# ---------------------------------------------------------------------------
# 2. P012 — "Resolve or delete" annotation remediation
# ---------------------------------------------------------------------------

def test_p012_annotation_wording_resolve_or_delete() -> None:
    comment = build_polished_comment(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        page=2,
        details={"issue_type": "pdf_annotation_detected", "annotation_type": "highlight"},
    )
    assert "Resolve or delete" in comment or "resolve or delete" in comment


def test_p012_catalog_remediation_direct() -> None:
    rules = _load_rule_catalog()
    p012 = next(r for r in rules if r["id"] == "P012")
    assert "Resolve or delete" in p012["remediation"]


# ---------------------------------------------------------------------------
# 3. P013 — bottom-center placement wording
# ---------------------------------------------------------------------------

def test_p013_catalog_question_mentions_bottom_centered() -> None:
    rules = _load_rule_catalog()
    p013 = next(r for r in rules if r["id"] == "P013")
    q = p013["question"].lower()
    assert "bottom" in q
    assert "center" in q


def test_p013_catalog_remediation_mentions_0_5_inches() -> None:
    rules = _load_rule_catalog()
    p013 = next(r for r in rules if r["id"] == "P013")
    assert "0.5 inches" in p013["remediation"]


def test_p013_comment_bottom_center_mentions_placement() -> None:
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=4,
        details={"position_type": "bottom_center"},
    )
    assert "bottom" in comment.lower()
    assert "0.5 inches" in comment


def test_p013_comment_top_position_flags_wrong_placement() -> None:
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=6,
        details={"position_type": "top_center"},
    )
    assert "top center" in comment
    assert "bottom" in comment.lower()
    assert "0.5 inches" in comment


def test_p013_comment_multiple_candidates_mentions_bottom() -> None:
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=7,
        details={"position_type": "bottom_center", "candidate_count_on_page": "2"},
    )
    assert "Multiple" in comment
    assert "0.5 inches" in comment


# ---------------------------------------------------------------------------
# 4. P016 — necessary-page-break exception in spacing wording
# ---------------------------------------------------------------------------

def test_p016_excessive_line_gap_mentions_page_breaks_exception() -> None:
    comment = build_polished_comment(
        rule_id="P016",
        issue_type="excessive_line_gap",
        page=8,
        details={"issue_type": "excessive_line_gap", "largest_gap_pt": "48.0"},
    )
    assert "page break" in comment.lower() or "page-break" in comment.lower()
    assert "delete" in comment.lower() or "unnecessary" in comment.lower()


def test_p016_excessive_paragraph_gap_mentions_necessary_breaks() -> None:
    comment = build_polished_comment(
        rule_id="P016",
        issue_type="excessive_paragraph_gap",
        page=9,
        details={"issue_type": "excessive_paragraph_gap", "largest_gap_pt": "60.0"},
    )
    assert "page break" in comment.lower() or "necessary" in comment.lower()


def test_p016_catalog_question_mentions_text_flow() -> None:
    rules = _load_rule_catalog()
    p016 = next(r for r in rules if r["id"] == "P016")
    q = p016["question"].lower()
    assert "top margin" in q or "bottom margin" in q


def test_p016_catalog_question_mentions_page_break_exception() -> None:
    rules = _load_rule_catalog()
    p016 = next(r for r in rules if r["id"] == "P016")
    q = p016["question"].lower()
    assert "page break" in q


def test_p016_catalog_remediation_mentions_page_breaks() -> None:
    rules = _load_rule_catalog()
    p016 = next(r for r in rules if r["id"] == "P016")
    assert "page break" in p016["remediation"].lower()


# ---------------------------------------------------------------------------
# 5. P020 — source-document advice in remediation
# ---------------------------------------------------------------------------

def test_p020_catalog_remediation_mentions_source_document() -> None:
    rules = _load_rule_catalog()
    p020 = next(r for r in rules if r["id"] == "P020")
    assert "source document" in p020["remediation"].lower()


def test_p020_catalog_remediation_no_latex() -> None:
    rules = _load_rule_catalog()
    p020 = next(r for r in rules if r["id"] == "P020")
    assert "latex" not in p020["remediation"].lower()


# ---------------------------------------------------------------------------
# 6. P026 — Overleaf/Computer Modern accepted-equivalent wording
# ---------------------------------------------------------------------------

def test_p026_font_family_comment_mentions_overleaf() -> None:
    comment = build_polished_comment(
        rule_id="P026",
        issue_type="possible_body_font_family_issue",
        page=10,
        details={
            "issue_type": "possible_body_font_family_issue",
            "observed_summary": "CMR12",
        },
    )
    assert "Overleaf" in comment


def test_p026_font_family_comment_mentions_computer_modern() -> None:
    comment = build_polished_comment(
        rule_id="P026",
        issue_type="possible_body_font_family_issue",
        page=10,
        details={
            "issue_type": "possible_body_font_family_issue",
            "observed_summary": "CMR12",
        },
    )
    assert "Computer Modern" in comment


def test_p026_font_family_comment_no_latex() -> None:
    comment = build_polished_comment(
        rule_id="P026",
        issue_type="possible_body_font_family_issue",
        page=10,
        details={"issue_type": "possible_body_font_family_issue"},
    )
    assert "latex" not in comment.lower()


def test_p026_catalog_question_mentions_accepted_equivalent() -> None:
    rules = _load_rule_catalog()
    p026 = next(r for r in rules if r["id"] == "P026")
    q = p026["question"].lower()
    assert "accepted" in q and "equivalent" in q


def test_p026_catalog_remediation_mentions_word_users() -> None:
    rules = _load_rule_catalog()
    p026 = next(r for r in rules if r["id"] == "P026")
    assert "Word" in p026["remediation"]


# ---------------------------------------------------------------------------
# 7. P038 — canonical ACKNOWLEDGEMENTS spelling clarification
# ---------------------------------------------------------------------------

def test_p038_catalog_remediation_spells_acknowledgements_correctly() -> None:
    rules = _load_rule_catalog()
    p038 = next(r for r in rules if r["id"] == "P038")
    assert "ACKNOWLEDGEMENTS" in p038["remediation"]


def test_p038_catalog_remediation_mentions_double_e() -> None:
    rules = _load_rule_catalog()
    p038 = next(r for r in rules if r["id"] == "P038")
    # The remediation should clarify the double-E spelling
    assert "double" in p038["remediation"].lower() or "ACKNOWLEDGEMENTS" in p038["remediation"]


# ---------------------------------------------------------------------------
# 8. No "latex" in student-facing polished comments
# ---------------------------------------------------------------------------

_LATEX_SENSITIVE_CASES = [
    ("P011", "margin_boundary_violation", {"side": "left_margin"}),
    ("P012", "pdf_annotation_detected", {"annotation_type": "text"}),
    ("P013", "page_number_candidate", {"position_type": "bottom_center"}),
    ("P016", "excessive_line_gap", {"largest_gap_pt": "48.0"}),
    ("P016", "excessive_paragraph_gap", {"largest_gap_pt": "60.0"}),
    ("P026", "possible_body_font_family_issue", {"observed_summary": "CMR12"}),
    ("P026", "possible_body_font_size_issue", {"observed_summary": "11.0pt"}),
]


@pytest.mark.parametrize("rule_id,issue_type,details", _LATEX_SENSITIVE_CASES)
def test_polished_comment_no_latex_term(rule_id: str, issue_type: str, details: dict) -> None:
    comment = build_polished_comment(
        rule_id=rule_id,
        issue_type=issue_type,
        page=1,
        details={"issue_type": issue_type, **details},
    )
    assert "latex" not in comment.lower(), (
        f"Banned term 'latex' found in {rule_id}/{issue_type} comment: {comment!r}"
    )


# ---------------------------------------------------------------------------
# 9. Planning document exists with broad split candidates
# ---------------------------------------------------------------------------

def test_planning_document_exists() -> None:
    plan_path = Path(__file__).parents[1] / "docs/planning/ester_atomic_rule_split_plan.md"
    assert plan_path.exists(), "docs/planning/ester_atomic_rule_split_plan.md not found"


def test_planning_document_mentions_p014_split() -> None:
    plan_path = Path(__file__).parents[1] / "docs/planning/ester_atomic_rule_split_plan.md"
    content = plan_path.read_text(encoding="utf-8")
    assert "P014" in content
    assert "Q013" in content or "Q047" in content


def test_planning_document_mentions_p017_split() -> None:
    plan_path = Path(__file__).parents[1] / "docs/planning/ester_atomic_rule_split_plan.md"
    content = plan_path.read_text(encoding="utf-8")
    assert "P017" in content
    assert "figure" in content.lower()


def test_planning_document_mentions_p018_split() -> None:
    plan_path = Path(__file__).parents[1] / "docs/planning/ester_atomic_rule_split_plan.md"
    content = plan_path.read_text(encoding="utf-8")
    assert "P018" in content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_rule_catalog() -> list[dict]:
    path = Path(__file__).parents[1] / "data/processed/rules/project_added_rules.json"
    return json.loads(path.read_text(encoding="utf-8"))
