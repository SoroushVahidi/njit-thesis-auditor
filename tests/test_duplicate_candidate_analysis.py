"""Tests for the offline duplicate-candidate cluster analysis (Part 5).

All fixtures are synthetic finding dicts -- no real dissertation content,
no sample/document-specific values.
"""

from __future__ import annotations

from pathlib import Path

from njit_auditor.duplicate_candidate_analysis import (
    bbox_iou,
    find_geometric_duplicate_candidates,
    find_same_page_normalized_wording_candidates,
)


def test_bbox_iou_identical_boxes_is_one() -> None:
    box = (10.0, 10.0, 50.0, 50.0)
    assert bbox_iou(box, box) == 1.0


def test_bbox_iou_disjoint_boxes_is_zero() -> None:
    a = (0.0, 0.0, 10.0, 10.0)
    b = (100.0, 100.0, 110.0, 110.0)
    assert bbox_iou(a, b) == 0.0


def test_bbox_iou_missing_box_is_zero() -> None:
    assert bbox_iou(None, (0.0, 0.0, 10.0, 10.0)) == 0.0
    assert bbox_iou((0.0, 0.0, 10.0, 10.0), None) == 0.0


def test_bbox_iou_partial_overlap_between_zero_and_one() -> None:
    a = (0.0, 0.0, 10.0, 10.0)
    b = (5.0, 5.0, 15.0, 15.0)
    iou = bbox_iou(a, b)
    assert 0.0 < iou < 1.0


def test_geometric_candidates_flag_overlapping_bboxes_from_different_rules() -> None:
    findings = [
        {
            "rule_id": "P018",
            "issue_type": "missing_page_number",
            "page": 5,
            "bbox": [10, 10, 100, 30],
        },
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 5,
            "bbox": [12, 11, 98, 29],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    assert len(report.candidates) == 1
    c = report.candidates[0]
    assert {c.rule_id_a, c.rule_id_b} == {"P018", "P024"}
    assert c.page == 5


def test_geometric_candidates_ignore_same_rule_pairs() -> None:
    """Same (rule_id, issue_type) overlap is exact/near-exact duplication,
    already handled by each rule's own dedup key -- not a cross-rule
    semantic-duplicate candidate this tool should surface."""
    findings = [
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "page": 3,
            "bbox": [0, 0, 50, 50],
        },
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "page": 3,
            "bbox": [1, 1, 51, 51],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    assert report.candidates == ()


def test_geometric_candidates_ignore_different_pages() -> None:
    findings = [
        {
            "rule_id": "P018",
            "issue_type": "missing_page_number",
            "page": 5,
            "bbox": [10, 10, 100, 30],
        },
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 6,
            "bbox": [10, 10, 100, 30],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    assert report.candidates == ()


def test_geometric_candidates_ignore_findings_without_bbox() -> None:
    findings = [
        {"rule_id": "P019", "issue_type": "wrong_page_numbering_style", "page": 5, "bbox": None},
        {
            "rule_id": "P028",
            "issue_type": "wrong_page_numbering_style",
            "page": 5,
            "bbox": [10, 10, 100, 30],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    assert report.candidates == ()


def test_geometric_candidates_below_threshold_are_excluded() -> None:
    findings = [
        {"rule_id": "P018", "issue_type": "missing_page_number", "page": 5, "bbox": [0, 0, 10, 10]},
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 5,
            "bbox": [9, 9, 30, 30],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.9)
    assert report.candidates == ()


def test_by_rule_pair_groups_and_counts_candidates() -> None:
    findings = [
        {"rule_id": "P018", "issue_type": "missing_page_number", "page": 5, "bbox": [0, 0, 10, 10]},
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 5,
            "bbox": [0, 0, 10, 10],
        },
        {"rule_id": "P018", "issue_type": "missing_page_number", "page": 9, "bbox": [0, 0, 10, 10]},
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 9,
            "bbox": [0, 0, 10, 10],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    grouped = report.by_rule_pair()
    assert len(grouped) == 1
    (only_pair, items) = next(iter(grouped.items()))
    assert len(items) == 2
    assert only_pair == ("P018:missing_page_number", "P024:list_of_tables_title_case")


def test_wording_candidates_flag_shared_student_facing_issue_type_across_rules() -> None:
    """Mirrors the real P019/P028 pattern: two different rule_ids that both
    normalize to the same student-facing issue_type on the same page, where
    one of the two has no bbox at all (so geometric IoU alone would miss it)."""
    findings = [
        {"rule_id": "P019", "issue_type": "wrong_page_numbering_style", "page": 15, "bbox": None},
        {
            "rule_id": "P028",
            "issue_type": "wrong_page_numbering_style",
            "page": 15,
            "bbox": [10, 10, 100, 30],
        },
    ]
    report = find_same_page_normalized_wording_candidates(findings)
    assert len(report.candidates) == 1
    c = report.candidates[0]
    assert {c.rule_id_a, c.rule_id_b} == {"P019", "P028"}
    assert "same_normalized_issue_type" in c.reasons
    assert "same_page" in c.reasons


def test_wording_candidates_ignore_same_rule() -> None:
    findings = [
        {"rule_id": "P019", "issue_type": "wrong_page_numbering_style", "page": 15, "bbox": None},
        {"rule_id": "P019", "issue_type": "wrong_page_numbering_style", "page": 15, "bbox": None},
    ]
    report = find_same_page_normalized_wording_candidates(findings)
    assert report.candidates == ()


def test_wording_candidates_ignore_different_issue_types() -> None:
    findings = [
        {"rule_id": "P019", "issue_type": "missing_page_number", "page": 15, "bbox": None},
        {"rule_id": "P028", "issue_type": "wrong_page_numbering_style", "page": 15, "bbox": None},
    ]
    report = find_same_page_normalized_wording_candidates(findings)
    assert report.candidates == ()


def test_wording_candidates_ignore_missing_issue_type() -> None:
    findings = [
        {"rule_id": "P019", "issue_type": "", "page": 15, "bbox": None},
        {"rule_id": "P028", "issue_type": "", "page": 15, "bbox": None},
    ]
    report = find_same_page_normalized_wording_candidates(findings)
    assert report.candidates == ()


def test_candidates_use_stable_problem_anchor_not_raw_list_index() -> None:
    """finding_id must come from the report's own stable identifier
    (problem_anchor/problem_number), never a bare list position -- list
    position is not a stable identifier across requests or views."""
    findings = [
        {
            "rule_id": "P018",
            "issue_type": "missing_page_number",
            "page": 5,
            "bbox": [0, 0, 10, 10],
            "problem_number": 7,
            "problem_anchor": "problem-7",
        },
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 5,
            "bbox": [0, 0, 10, 10],
            "problem_number": 12,
            "problem_anchor": "problem-12",
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    c = report.candidates[0]
    assert {c.finding_id_a, c.finding_id_b} == {"problem-7", "problem-12"}


def test_candidates_fall_back_to_index_when_no_stable_id_present() -> None:
    findings = [
        {"rule_id": "P018", "issue_type": "missing_page_number", "page": 5, "bbox": [0, 0, 10, 10]},
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 5,
            "bbox": [0, 0, 10, 10],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    c = report.candidates[0]
    assert {c.finding_id_a, c.finding_id_b} == {"index-0", "index-1"}


def test_geometric_candidates_carry_explicit_machine_readable_reasons() -> None:
    findings = [
        {
            "rule_id": "P018",
            "issue_type": "missing_page_number",
            "page": 5,
            "bbox": [10, 10, 100, 30],
        },
        {
            "rule_id": "P024",
            "issue_type": "list_of_tables_title_case",
            "page": 5,
            "bbox": [12, 11, 98, 29],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    c = report.candidates[0]
    assert "same_page" in c.reasons
    assert any(r.startswith("bbox_overlap:") for r in c.reasons)


def test_candidates_are_never_labeled_confirmed_or_duplicate_alone() -> None:
    """Every result type and field name must read as a candidate requiring
    human review -- never as a confirmed/auto-actionable duplicate."""
    import njit_auditor.duplicate_candidate_analysis as mod

    assert hasattr(mod, "DuplicateCandidate")
    assert not hasattr(mod, "ConfirmedDuplicate")
    assert "candidate" in mod.__doc__.lower()
    assert "human review" in mod.__doc__.lower()


def test_legitimately_distinct_same_object_findings_stay_candidates_only() -> None:
    """P024 (sentence case) and P040 (terminal punctuation) can both fire on
    the same List of Figures entry -- different edits are required for
    each, so this tool must surface them as a *candidate* (for a human to
    judge), never as anything auto-suppressed or merged. This module has no
    suppression mechanism at all, so this is really asserting the analysis
    doesn't crash or misclassify overlapping-but-independent findings."""
    findings = [
        {
            "rule_id": "P024",
            "issue_type": "list_of_figures_sentence_case",
            "page": 8,
            "bbox": [50, 400, 300, 415],
        },
        {
            "rule_id": "P040",
            "issue_type": "lof_entry_missing_terminal_punctuation",
            "page": 8,
            "bbox": [50, 400, 300, 415],
        },
    ]
    report = find_geometric_duplicate_candidates(findings, iou_threshold=0.3)
    assert len(report.candidates) == 1
    c = report.candidates[0]
    assert {c.rule_id_a, c.rule_id_b} == {"P024", "P040"}
    assert "same_page" in c.reasons


def test_duplicate_candidate_cli_help_mentions_human_review(tmp_path: Path) -> None:
    """The CLI must document that candidates need human review and fail clearly
    on a missing PDF path without writing private filenames into Tracebacks as
    success output.
    """
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "warning_duplicate_candidate_analysis.py"
    help_proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert help_proc.returncode == 0
    assert "human review" in help_proc.stdout.lower()

    missing = tmp_path / "does-not-exist.pdf"
    missing_proc = subprocess.run(
        [sys.executable, str(script), str(missing)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert missing_proc.returncode == 2
    assert "PDF not found" in missing_proc.stderr
