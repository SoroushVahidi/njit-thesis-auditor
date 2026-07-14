"""Tests for report-view DTOs and polished comments."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from njit_auditor.high_volume_student_preview import margin_location_label
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import (
    REVIEW_PREFIX,
    build_polished_comment,
    contains_blocked_detail_text,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import (
    build_report_view,
    normalize_sort_mode,
    report_view_to_dict,
    sort_findings,
    sort_grouped_problems,
)


def _p011_findings(count: int = 6) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
            },
        )
        for i in range(count)
    ]


def _p013_findings(count: int = 6) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=i + 1,
            message="Page number candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "confidence": "medium",
            },
        )
        for i in range(count)
    ]


def _p026_findings(count: int = 6) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=i + 1,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "confidence": "medium",
            },
        )
        for i in range(count)
    ]


def _sample_report() -> dict[str, Any]:
    findings = (
        _p011_findings(2)
        + _p013_findings(2)
        + _p026_findings(2)
        + [
            AuditFinding(
                rule_id="P030",
                severity=Severity.WARNING,
                page=12,
                message="Missing continued heading.",
                details={"issue_type": "missing_continued_heading"},
            )
        ]
    )
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def _sample_source_report() -> dict[str, Any]:
    findings = [
        AuditFinding(
            rule_id="P001",
            severity=Severity.WARNING,
            message="Avoid shell escape commands in TeX source.",
            details={
                "file": "/tmp/private/thesis.tex",
                "line": str(line),
                "issue_type": "risky_command",
                "command": "\\write18",
                "suggested_fix": "Remove the shell-escape command from the source.",
            },
        )
        for line in (12, 18, 19, 20, 21)
    ]
    return audit_findings_to_json_dict(findings, {"audit_type": "tex"})


def test_build_report_view_counts() -> None:
    report = _sample_report()
    view = build_report_view(report)
    assert view.total_findings == 5
    assert view.counts_by_severity["WARNING"] == 5
    assert view.counts_by_rule["P011"] == 2
    assert "margin_or_overflow" in view.counts_by_category
    assert len(view.summary_cards) >= 4
    assert view.pages == [1, 2, 12]
    assert len(view.inventory_findings) == 2


def test_build_report_view_triage_panels() -> None:
    report = _sample_report()
    view = build_report_view(report)
    rule_ids = {p.rule_id for p in view.triage_panels}
    assert "P011" in rule_ids
    assert "P026" in rule_ids
    assert "P013" in rule_ids
    p011 = next(p for p in view.triage_panels if p.rule_id == "P011")
    assert p011.raw_finding_count >= 2
    assert "triage" in p011.triage_note.lower() or "heuristic" in p011.triage_note.lower()


def test_p013_triage_panel_all_informational_when_no_visible_problems() -> None:
    """The sample's 2 P013 candidates are routine (bottom_center, single, medium) —
    none are visible problems, so the panel should show 0 problems / 2 informational,
    mirroring web's inventory split with no "Examples for this rule" affordance."""
    report = _sample_report()
    view = build_report_view(report)
    p013 = next(p for p in view.triage_panels if p.rule_id == "P013")
    assert p013.raw_finding_count == 2
    assert p013.problem_count == 0
    assert p013.informational_count == 2
    assert len(view.inventory_findings) == 2
    assert not any(f.rule_id == "P013" for f in view.findings)


def test_p013_triage_panel_splits_real_problems_from_candidates() -> None:
    """A P013 finding with candidate_count_on_page > 1 is a real visible problem;
    the triage panel must count it separately from the routine candidates."""
    findings = _p013_findings(4) + [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=9,
            message="Multiple page-number-like tokens detected.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "candidate_count_on_page": "2",
                "confidence": "medium",
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)
    p013 = next(p for p in view.triage_panels if p.rule_id == "P013")
    assert p013.raw_finding_count == 5
    assert p013.problem_count == 1
    assert p013.informational_count == 4
    assert sum(1 for f in view.findings if f.rule_id == "P013") == 1
    assert sum(1 for f in view.inventory_findings if f.rule_id == "P013") == 4


def test_p013_triage_panel_informational_count_excludes_document_overview() -> None:
    """The document-overview entry is a per-document summary note, not a per-page
    candidate; it must not inflate the triage panel's informational-candidate
    badge beyond what the "Detected candidates" inventory section actually lists
    (this previously diverged: the badge counted it, the inventory list did not)."""
    findings = _p013_findings(4) + [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=None,
            message="Page-number candidate overview.",
            details={"issue_type": "p013_document_overview"},
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)
    p013 = next(p for p in view.triage_panels if p.rule_id == "P013")
    assert p013.raw_finding_count == 5
    assert p013.problem_count == 0
    assert p013.informational_count == 4
    assert len(view.inventory_findings) == p013.informational_count
    assert not any(f.rule_id == "P013" for f in view.findings)


def test_finding_views_include_polished_comments() -> None:
    view = build_report_view(_sample_report())
    assert all(fv.polished_comment for fv in view.findings)
    assert all(
        fv.polished_comment.startswith((REVIEW_PREFIX, "Likely problem:", "Problem:"))
        for fv in view.findings
    )


def test_grouped_problem_views_default_to_grouped_problems_for_repeats() -> None:
    view = build_report_view(_sample_report())

    assert len(view.grouped_problems) == 3
    p011 = next(problem for problem in view.grouped_problems if problem.rule_id == "P011")
    assert p011.is_grouped is True
    assert p011.occurrence_count == 2
    assert p011.affected_label == "Pages"
    assert p011.affected_compact == "1–2"
    assert p011.page_tokens == ["1", "2"]
    assert len(p011.individual_findings) == 2
    assert all(f.rule_id == "P011" for f in p011.individual_findings)


def test_grouped_problem_views_keep_single_findings_simple() -> None:
    view = build_report_view(_sample_report())

    p030 = next(problem for problem in view.grouped_problems if problem.rule_id == "P030")
    assert p030.is_grouped is False
    assert p030.occurrence_count == 1
    assert p030.affected_compact == "12"
    assert len(p030.individual_findings) == 1


def test_report_view_adds_confidence_display_metadata() -> None:
    view = build_report_view(_sample_report())

    finding = next(f for f in view.findings if f.rule_id == "P011")
    assert finding.confidence == "medium"
    assert finding.confidence_level == "medium"
    assert finding.confidence_label == "Medium confidence"
    assert finding.confidence_css_class == "confidence-badge--medium"

    group = next(problem for problem in view.grouped_problems if problem.rule_id == "P011")
    assert group.confidence_levels == ["medium"]
    assert group.confidence_level == "medium"
    assert group.confidence_label == "Medium confidence"
    assert group.confidence_css_class == "confidence-badge--medium"


def test_finding_with_missing_confidence_shows_low_confidence_badge() -> None:
    """Missing confidence must render the public Low confidence badge, never blank
    and never a separate "Needs review" category -- public display supports exactly
    three confidence values (High/Medium/Low), so an uncertain/missing case is the
    conservative Low bucket rather than a fourth category."""
    view = build_report_view(_sample_report())

    finding = next(f for f in view.findings if f.rule_id == "P030")
    assert finding.confidence == ""
    assert finding.confidence_level == ""
    assert finding.confidence_label == "Low confidence"
    assert finding.confidence_css_class == "confidence-badge--low"

    group = next(problem for problem in view.grouped_problems if problem.rule_id == "P030")
    assert group.confidence_label == "Low confidence"
    assert group.confidence_css_class == "confidence-badge--low"


def test_grouped_problem_views_track_mixed_confidence_levels() -> None:
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "low",
            },
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    report["grouped_findings"] = [
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "individual_indexes": [0, 1],
        }
    ]

    view = build_report_view(report)

    group = next(problem for problem in view.grouped_problems if problem.rule_id == "P011")
    assert group.is_grouped is True
    # Internal tracking of which levels are present is preserved exactly (still drives
    # confidence-based sorting); only the public display label/class is normalized.
    assert group.confidence_levels == ["high", "low"]
    assert group.confidence_level == "mixed"
    assert group.confidence_label == "Low confidence"
    assert group.confidence_css_class == "confidence-badge--low"


def test_mixed_high_medium_confidence_displays_as_low() -> None:
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
            },
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    report["grouped_findings"] = [
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "individual_indexes": [0, 1],
        }
    ]

    view = build_report_view(report)
    group = next(problem for problem in view.grouped_problems if problem.rule_id == "P011")
    assert group.confidence_levels == ["high", "medium"]
    assert group.confidence_label == "Low confidence"
    assert group.confidence_css_class == "confidence-badge--low"


def test_mixed_medium_low_confidence_displays_as_low() -> None:
    findings = [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=1,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=2,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "low"},
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    report["grouped_findings"] = [
        {
            "rule_id": "P037",
            "issue_type": "wrong_page_number_sequence",
            "individual_indexes": [0, 1],
        }
    ]

    view = build_report_view(report)
    group = next(problem for problem in view.grouped_problems if problem.rule_id == "P037")
    assert group.confidence_levels == ["medium", "low"]
    assert group.confidence_label == "Low confidence"
    assert group.confidence_css_class == "confidence-badge--low"


def _confidence_sort_fixture_grouped_problems() -> list[dict[str, Any]]:
    """Five singleton cards in a deliberately non-confidence-ordered default order.

    Default order (by rule_id): P037 (low), P011 (high), P026 (medium), P030 (missing),
    P044 (high). Two "high" cards (P011, P044) are included non-adjacently so sorting
    tests can also confirm stability within a confidence bucket.
    """
    findings = [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=2,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "low"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=4,
            message="Missing continued heading.",
            details={"issue_type": "missing_continued_heading"},
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=5,
            message="Table centering issue.",
            details={"issue_type": "table_not_centered", "confidence": "high"},
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)
    return report_view_to_dict(view)["grouped_problems"]


def test_normalize_sort_mode_accepts_known_values_and_falls_back_for_unknown() -> None:
    assert normalize_sort_mode("default") == "default"
    assert normalize_sort_mode("confidence_desc") == "confidence_desc"
    assert normalize_sort_mode("confidence_asc") == "confidence_asc"
    assert normalize_sort_mode("CONFIDENCE_DESC") == "confidence_desc"
    assert normalize_sort_mode("  confidence_asc  ") == "confidence_asc"
    # Unrecognized, empty, or tampered values safely fall back to default order.
    assert normalize_sort_mode("") == "default"
    assert normalize_sort_mode("bogus") == "default"
    assert normalize_sort_mode("newest") == "default"


def test_sort_grouped_problems_default_mode_orders_by_page() -> None:
    """"default" is the "Page order" option shown in the UI and the order applied on
    first page load, so it must sort by earliest affected page, not preserve
    insertion order (P037 is inserted first but is on page 2, after P011's page 1)."""
    problems = _confidence_sort_fixture_grouped_problems()
    insertion_order = [p["rule_id"] for p in problems]
    assert insertion_order == ["P037", "P011", "P026", "P030", "P044"]

    # Pages: P037=2, P011=1, P026=3, P030=4, P044=5.
    expected_page_order = ["P011", "P037", "P026", "P030", "P044"]
    sorted_problems = sort_grouped_problems(problems, "default")
    assert [p["rule_id"] for p in sorted_problems] == expected_page_order
    # "default" and the explicit "page_order" value must produce identical output.
    assert sort_grouped_problems(problems, "page_order") == sorted_problems


def test_sort_grouped_problems_high_first_orders_high_before_medium_before_low() -> None:
    problems = _confidence_sort_fixture_grouped_problems()
    sorted_problems = sort_grouped_problems(problems, "confidence_desc")
    # High-confidence cards (P011, P044) keep their original relative order (stability),
    # followed by medium (P026), then low (P037), then missing confidence (P030) last.
    assert [p["rule_id"] for p in sorted_problems] == [
        "P011",
        "P044",
        "P026",
        "P037",
        "P030",
    ]


def test_sort_grouped_problems_low_first_orders_low_before_medium_before_high() -> None:
    problems = _confidence_sort_fixture_grouped_problems()
    sorted_problems = sort_grouped_problems(problems, "confidence_asc")
    # Low first (P037), then medium (P026), then the high-confidence cards in their
    # original relative order (P011, P044), with missing confidence (P030) last in
    # this direction too.
    assert [p["rule_id"] for p in sorted_problems] == [
        "P037",
        "P026",
        "P011",
        "P044",
        "P030",
    ]


def test_sort_grouped_problems_invalid_mode_falls_back_to_default_order() -> None:
    problems = _confidence_sort_fixture_grouped_problems()
    mode = normalize_sort_mode("not-a-real-mode")
    assert mode == "default"
    sorted_problems = sort_grouped_problems(problems, mode)
    # Falls back to "default", i.e. page order: P011(1), P037(2), P026(3), P030(4), P044(5).
    assert [p["rule_id"] for p in sorted_problems] == [
        "P011",
        "P037",
        "P026",
        "P030",
        "P044",
    ]


def test_sort_grouped_problems_does_not_change_problem_numbers_or_card_contents() -> None:
    """Sorting only reorders the list; it must never renumber or rewrite cards."""
    problems = _confidence_sort_fixture_grouped_problems()
    before_by_rule = {p["rule_id"]: p for p in problems}

    for mode in ("confidence_desc", "confidence_asc"):
        sorted_problems = sort_grouped_problems(problems, mode)
        assert len(sorted_problems) == len(problems)
        for problem in sorted_problems:
            original = before_by_rule[problem["rule_id"]]
            assert problem["problem_numbers"] == original["problem_numbers"]
            assert problem["problem_number_label"] == original["problem_number_label"]
            assert problem["problem_anchor"] == original["problem_anchor"]
            assert problem["individual_findings"] == original["individual_findings"]


def test_sort_grouped_problems_ranks_mixed_confidence_card_by_extreme_present() -> None:
    """A grouped card spanning high+low confidence occurrences should surface with the
    high-confidence cards in high-first mode, and with the low-confidence cards in
    low-first mode, so a reviewer never misses a low-confidence occurrence hidden
    inside a card that also happens to contain a high-confidence one."""
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "low",
            },
        ),
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=3,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "medium"},
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    report["grouped_findings"] = [
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "individual_indexes": [0, 1],
        },
        {
            "rule_id": "P037",
            "issue_type": "wrong_page_number_sequence",
            "individual_indexes": [2],
        },
    ]
    view = build_report_view(report)
    problems = report_view_to_dict(view)["grouped_problems"]
    assert next(p for p in problems if p["rule_id"] == "P011")["confidence_level"] == "mixed"

    desc_order = [p["rule_id"] for p in sort_grouped_problems(problems, "confidence_desc")]
    assert desc_order == ["P011", "P037"]

    asc_order = [p["rule_id"] for p in sort_grouped_problems(problems, "confidence_asc")]
    assert asc_order == ["P011", "P037"]


def test_sort_grouped_problems_preserves_grouping_and_occurrence_details() -> None:
    """Sorting must not split or flatten a grouped card's individual occurrences."""
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
            },
        )
        for i in range(3)
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    report["grouped_findings"] = [
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "individual_indexes": [0, 1, 2],
        }
    ]
    view = build_report_view(report)
    problems = report_view_to_dict(view)["grouped_problems"]
    assert len(problems) == 1
    assert problems[0]["is_grouped"] is True
    assert problems[0]["occurrence_count"] == 3

    for mode in ("default", "confidence_desc", "confidence_asc"):
        sorted_problems = sort_grouped_problems(problems, mode)
        assert len(sorted_problems) == 1
        assert sorted_problems[0]["is_grouped"] is True
        assert sorted_problems[0]["occurrence_count"] == 3
        assert len(sorted_problems[0]["individual_findings"]) == 3


def _page_sort_fixture_grouped_problems() -> list[dict[str, Any]]:
    """Five cards in a deliberately non-page-ordered default order.

    Default order (by rule_id): P037 (page 8), P011 (page 3), P026 (page 3),
    P030 (no page), P044 (grouped occurrences on pages 10 and 1 -- earliest page 1).
    P011/P026 share page 3 so page-order tests can also confirm stability within a
    page bucket. P044's earliest page (1) is lower than every singleton card's page,
    confirming a multi-page grouped card sorts by its minimum affected page even
    though it is listed last by default and has a higher page among its occurrences.
    """
    findings = [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=8,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "low"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=None,
            message="Missing continued heading.",
            details={"issue_type": "missing_continued_heading"},
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=10,
            message="Abstract indentation issue.",
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=1,
            message="Abstract indentation issue.",
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "confidence": "high",
            },
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)
    return report_view_to_dict(view)["grouped_problems"]


def test_page_order_sort_orders_grouped_problems_by_earliest_page() -> None:
    problems = _page_sort_fixture_grouped_problems()
    default_order = [p["rule_id"] for p in problems]
    assert default_order == ["P037", "P011", "P026", "P030", "P044"]

    sorted_problems = sort_grouped_problems(problems, "page_order")
    # P044's earliest occurrence (page 1) sorts first even though it is a multi-page
    # grouped card also touching page 10 and is listed last by default. P011 and P026
    # share page 3 and keep their original relative order (stability). P037 (page 8)
    # comes next, and P030 (no page at all) sorts last.
    assert [p["rule_id"] for p in sorted_problems] == ["P044", "P011", "P026", "P037", "P030"]


def test_page_order_sort_same_page_findings_preserve_stable_order() -> None:
    problems = _page_sort_fixture_grouped_problems()
    sorted_problems = sort_grouped_problems(problems, "page_order")
    same_page_ids = [p["rule_id"] for p in sorted_problems if p["rule_id"] in ("P011", "P026")]
    # Both share earliest page 3; P011 preceded P026 in the original default order.
    assert same_page_ids == ["P011", "P026"]


def test_page_order_sort_no_page_findings_appear_after_page_specific_findings() -> None:
    problems = _page_sort_fixture_grouped_problems()
    sorted_problems = sort_grouped_problems(problems, "page_order")
    assert sorted_problems[-1]["rule_id"] == "P030"


def test_page_order_sort_multipage_card_uses_earliest_affected_page() -> None:
    problems = _page_sort_fixture_grouped_problems()
    p044 = next(p for p in problems if p["rule_id"] == "P044")
    assert p044["occurrence_count"] == 2
    pages = sorted(int(f["page"]) for f in p044["individual_findings"])
    assert pages == [1, 10]

    sorted_problems = sort_grouped_problems(problems, "page_order")
    assert sorted_problems[0]["rule_id"] == "P044"


def test_page_order_sort_does_not_change_problem_numbers_or_card_contents() -> None:
    """Sorting only reorders the list; it must never renumber or rewrite cards."""
    problems = _page_sort_fixture_grouped_problems()
    before_by_rule = {p["rule_id"]: p for p in problems}

    sorted_problems = sort_grouped_problems(problems, "page_order")
    assert len(sorted_problems) == len(problems)
    for problem in sorted_problems:
        original = before_by_rule[problem["rule_id"]]
        assert problem["problem_numbers"] == original["problem_numbers"]
        assert problem["problem_number_label"] == original["problem_number_label"]
        assert problem["problem_anchor"] == original["problem_anchor"]
        assert problem["individual_findings"] == original["individual_findings"]


def test_normalize_sort_mode_accepts_page_order() -> None:
    assert normalize_sort_mode("page_order") == "page_order"
    assert normalize_sort_mode("PAGE_ORDER") == "page_order"
    assert normalize_sort_mode("  page_order  ") == "page_order"


# ---------------------------------------------------------------------------
# sort_findings: the flat individual-findings list is now the primary,
# student-facing Findings table, so it gets the exact same sort-mode behavior
# as sort_grouped_problems (page order default, confidence asc/desc, stable
# tie-breaking, never touching problem_number/problem_anchor).
# ---------------------------------------------------------------------------


def _confidence_sort_fixture_findings() -> list[dict[str, Any]]:
    """Five findings in a deliberately non-confidence-ordered default order.

    Default order (by rule_id): P037 (low), P011 (high), P026 (medium), P030 (missing),
    P044 (high). Two "high" findings (P011, P044) are included non-adjacently so sorting
    tests can also confirm stability within a confidence bucket.
    """
    findings = [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=2,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "low"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=4,
            message="Missing continued heading.",
            details={"issue_type": "missing_continued_heading"},
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=5,
            message="Table centering issue.",
            details={"issue_type": "table_not_centered", "confidence": "high"},
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)
    return report_view_to_dict(view)["findings"]


def test_sort_findings_default_mode_orders_by_page() -> None:
    findings = _confidence_sort_fixture_findings()
    insertion_order = [f["rule_id"] for f in findings]
    assert insertion_order == ["P037", "P011", "P026", "P030", "P044"]

    # Pages: P037=2, P011=1, P026=3, P030=4, P044=5.
    expected_page_order = ["P011", "P037", "P026", "P030", "P044"]
    sorted_findings = sort_findings(findings, "default")
    assert [f["rule_id"] for f in sorted_findings] == expected_page_order
    # "default" and the explicit "page_order" value must produce identical output.
    assert sort_findings(findings, "page_order") == sorted_findings


def test_sort_findings_high_first_orders_high_before_medium_before_low() -> None:
    findings = _confidence_sort_fixture_findings()
    sorted_findings = sort_findings(findings, "confidence_desc")
    assert [f["rule_id"] for f in sorted_findings] == [
        "P011",
        "P044",
        "P026",
        "P037",
        "P030",
    ]


def test_sort_findings_low_first_orders_low_before_medium_before_high() -> None:
    findings = _confidence_sort_fixture_findings()
    sorted_findings = sort_findings(findings, "confidence_asc")
    assert [f["rule_id"] for f in sorted_findings] == [
        "P037",
        "P026",
        "P011",
        "P044",
        "P030",
    ]


def test_sort_findings_invalid_mode_falls_back_to_default_order() -> None:
    findings = _confidence_sort_fixture_findings()
    mode = normalize_sort_mode("not-a-real-mode")
    assert mode == "default"
    sorted_findings = sort_findings(findings, mode)
    assert [f["rule_id"] for f in sorted_findings] == [
        "P011",
        "P037",
        "P026",
        "P030",
        "P044",
    ]


def test_sort_findings_does_not_change_problem_numbers() -> None:
    """Sorting only reorders the list; it must never renumber or rewrite findings."""
    findings = _confidence_sort_fixture_findings()
    before_by_rule = {f["rule_id"]: f for f in findings}

    for mode in ("confidence_desc", "confidence_asc"):
        sorted_findings = sort_findings(findings, mode)
        assert len(sorted_findings) == len(findings)
        for finding in sorted_findings:
            original = before_by_rule[finding["rule_id"]]
            assert finding["problem_number"] == original["problem_number"]
            assert finding["problem_anchor"] == original["problem_anchor"]


def _page_sort_fixture_findings() -> list[dict[str, Any]]:
    """Four findings in a deliberately non-page-ordered default order, with two
    sharing the same page so page-order tests can also confirm stability within a
    page bucket, and one with no page at all."""
    findings = [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=8,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "low"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=None,
            message="Missing continued heading.",
            details={"issue_type": "missing_continued_heading"},
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)
    return report_view_to_dict(view)["findings"]


def test_sort_findings_page_order_orders_by_page() -> None:
    findings = _page_sort_fixture_findings()
    default_order = [f["rule_id"] for f in findings]
    assert default_order == ["P037", "P011", "P026", "P030"]

    sorted_findings = sort_findings(findings, "page_order")
    # P011 and P026 share page 3 and keep their original relative order
    # (stability); P037 (page 8) comes next; P030 (no page) sorts last.
    assert [f["rule_id"] for f in sorted_findings] == ["P011", "P026", "P037", "P030"]


def test_sort_findings_same_page_findings_preserve_stable_order() -> None:
    findings = _page_sort_fixture_findings()
    sorted_findings = sort_findings(findings, "page_order")
    same_page_ids = [f["rule_id"] for f in sorted_findings if f["rule_id"] in ("P011", "P026")]
    assert same_page_ids == ["P011", "P026"]


def test_sort_findings_no_page_findings_appear_after_page_specific_findings() -> None:
    findings = _page_sort_fixture_findings()
    sorted_findings = sort_findings(findings, "page_order")
    assert sorted_findings[-1]["rule_id"] == "P030"


def test_same_problem_with_different_confidence_stays_on_one_card_by_default() -> None:
    """End-to-end: the default (non-overridden) grouping pipeline must not split
    an identical problem into separate cards just because confidence differs —
    see build_grouped_findings() in report_outputs.py, which excludes confidence
    from its grouping key for this reason."""
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=page,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": confidence,
            },
        )
        for page, confidence in ((1, "high"), (2, "high"), (3, "low"))
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})

    view = build_report_view(report)

    p011_groups = [problem for problem in view.grouped_problems if problem.rule_id == "P011"]
    assert len(p011_groups) == 1
    group = p011_groups[0]
    assert group.occurrence_count == 3
    assert group.confidence_levels == ["high", "low"]
    assert group.confidence_level == "mixed"
    assert len(group.individual_findings) == 3
    assert {f.confidence for f in group.individual_findings} == {"high", "low"}


def test_routine_p013_candidates_move_to_inventory() -> None:
    view = build_report_view(_sample_report())

    assert all(f.rule_id != "P013" for f in view.findings)
    assert len(view.inventory_findings) == 2
    assert all(f.issue_type == "detected_page_number_candidate" for f in view.inventory_findings)


def test_grouped_problem_views_group_source_locations_compactly() -> None:
    view = build_report_view(_sample_source_report())

    assert len(view.grouped_problems) == 1
    problem = view.grouped_problems[0]
    assert problem.is_grouped is True
    assert problem.affected_label == "Locations"
    assert problem.affected_compact == "thesis.tex:12, thesis.tex:18–21"
    assert problem.location_tokens == [
        "thesis.tex:12",
        "thesis.tex:18",
        "thesis.tex:19",
        "thesis.tex:20",
        "thesis.tex:21",
    ]
    assert all(
        finding.location_label.startswith("thesis.tex:")
        for finding in problem.individual_findings
    )


def test_p015_missing_later_indent_gets_precise_location_and_highlight() -> None:
    findings = [
        AuditFinding(
            rule_id="P015",
            severity=Severity.WARNING,
            page=32,
            message="Later paragraph appears to be missing expected first-line indentation.",
            details={
                "issue_type": "missing_later_indent",
                "indent_pt": "0.0",
                "expected": "first_line_indent_approx_36pt",
                "paragraph_line_count": "4",
                "paragraph_index": "2",
                "bbox": "100.0,300.0,500.0,312.0",
                "confidence": "high",
                "suggested_fix": (
                    "Apply consistent first-line indentation for non-opening paragraphs."
                ),
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report, pdf_page_sizes=[(612.0, 792.0)] * 32)

    finding = next(f for f in view.findings if f.rule_id == "P015")
    assert finding.location_label == "First line of body paragraph 2"
    assert finding.has_highlight is True
    assert finding.action_kind == "highlight"
    assert finding.action_label == "Open highlighted PDF page"
    assert "Observed" in finding.detailed_explanation
    assert "Expected" in finding.detailed_explanation
    assert "body paragraph 2" in finding.detailed_explanation
    assert "100.0" not in finding.detailed_explanation
    assert "300.0" not in finding.detailed_explanation


def test_p015_unexpected_opening_indent_gets_precise_location_and_highlight() -> None:
    findings = [
        AuditFinding(
            rule_id="P015",
            severity=Severity.WARNING,
            page=4,
            message="Opening paragraph appears unexpectedly indented.",
            details={
                "issue_type": "unexpected_opening_indent",
                "indent_pt": "82.0",
                "expected": "flush_left",
                "paragraph_line_count": "3",
                "paragraph_index": "1",
                "bbox": "190.0,140.0,540.0,152.0",
                "confidence": "high",
                "suggested_fix": "Remove first-line indent for opening front-matter paragraph.",
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report, pdf_page_sizes=[(612.0, 792.0)] * 4)

    finding = next(f for f in view.findings if f.rule_id == "P015")
    assert finding.location_label == "First line of the first paragraph after a heading"
    assert finding.has_highlight is True
    assert finding.action_kind == "highlight"
    assert finding.action_label == "Open highlighted PDF page"
    assert "flush with the left margin" in finding.polished_comment.lower()
    assert "190.0" not in finding.detailed_explanation


def test_p015_without_bbox_falls_back_to_specific_inspection_guidance() -> None:
    findings = [
        AuditFinding(
            rule_id="P015",
            severity=Severity.WARNING,
            page=10,
            message="Later paragraph appears to be missing expected first-line indentation.",
            details={
                "issue_type": "missing_later_indent",
                "indent_pt": "0.0",
                "expected": "first_line_indent_approx_36pt",
                "paragraph_line_count": "4",
                "paragraph_index": "3",
                "confidence": "high",
                "suggested_fix": (
                    "Apply consistent first-line indentation for non-opening paragraphs."
                ),
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    finding = next(f for f in view.findings if f.rule_id == "P015")
    assert finding.has_highlight is False
    assert finding.action_kind == "original_page"
    assert finding.action_label == "Open original PDF page"
    assert "body paragraph 3" in finding.no_highlight_reason


def _p024_finding(
    *, page: int, issue_type: str, entry_index: str | None, **extra: str
) -> AuditFinding:
    details: dict[str, str] = {
        "page_type": "table_of_contents",
        "issue_type": issue_type,
        "confidence": "medium",
        # Synthetic stand-in for real TOC text — must never reach rendered output.
        "line_preview": "Synthetic Sample Toc Entry Text Marker XYZ123",
        **extra,
    }
    if entry_index is not None:
        details["entry_index"] = entry_index
    return AuditFinding(
        rule_id="P024",
        severity=Severity.WARNING,
        page=page,
        message="TOC Level 2 entry may have a title-case issue.",
        details=details,
    )


def test_p024_location_label_uses_entry_index_for_toc() -> None:
    findings = [
        _p024_finding(
            page=12,
            issue_type="toc_level_capitalization",
            entry_index="0",
            entry_level="2",
            expected_or_reason="major_word_requires_capital",
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    finding = next(f for f in view.findings if f.rule_id == "P024")
    expected = (
        "Page 12 — Table of Contents, affected entry: "
        "'Synthetic Sample Toc Entry Text Marker XYZ123'"
    )
    assert finding.location_label == expected


def test_p024_location_label_falls_back_without_entry_index() -> None:
    """Without entry_index metadata, the label stays honest (section only, no index)."""
    findings = [
        _p024_finding(
            page=12,
            issue_type="toc_level_capitalization",
            entry_index=None,
            entry_level="2",
            expected_or_reason="major_word_requires_capital",
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    finding = next(f for f in view.findings if f.rule_id == "P024")
    assert finding.location_label == "Page 12 — Table of Contents"
    assert "entry" not in finding.location_label.lower()


def test_p027_location_label_names_the_actual_heading() -> None:
    """P027 findings must show the flagged heading, not a bare page number,
    so a Level 3 sentence-case warning reads as an actual heading location."""
    findings = [
        AuditFinding(
            rule_id="P027",
            severity=Severity.WARNING,
            page=62,
            message="Change this Level 3 heading to sentence case.",
            details={
                "issue_type": "level3_sentence_case_issue",
                "inferred_level": "3",
                "heading_pattern": "4.4.1",
                "line_preview": "4.4.1 Scatterplots Of Relationships With Readiness",
                "confidence": "medium",
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    finding = next(f for f in view.findings if f.rule_id == "P027")
    assert finding.location_label == (
        'Page 62 — Level 3 heading "4.4.1 Scatterplots Of Relationships With Readiness"'
    )


def test_p027_level3_card_shows_exact_sentence_case_replacement() -> None:
    """A P027 Level 3 sentence-case card must present the exact corrected
    heading as the suggested fix, not only a generic style reminder."""
    findings = [
        AuditFinding(
            rule_id="P027",
            severity=Severity.WARNING,
            page=62,
            message="(detector message)",
            details={
                "issue_type": "level3_sentence_case_issue",
                "inferred_level": "3",
                "heading_pattern": "4.4.1",
                "line_preview": "4.4.1 Scatterplots Of Relationships With Readiness",
                "corrected_from": "4.4.1 Scatterplots Of Relationships With Readiness",
                "corrected_example": "4.4.1 Scatterplots of relationships with readiness",
                "confidence": "medium",
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    finding = next(f for f in view.findings if f.rule_id == "P027")
    # The display finalizer trims the trailing period from the comment.
    assert finding.polished_comment == (
        "Likely problem: This Level-3 heading appears to use Title Case, "
        "but Level-3 headings should use sentence case"
    )
    assert finding.suggested_fix == (
        'Change "4.4.1 Scatterplots Of Relationships With Readiness" to '
        '"4.4.1 Scatterplots of relationships with readiness".'
    )


def test_p024_same_page_findings_distinguishable_via_entry_index() -> None:
    findings = [
        _p024_finding(
            page=12,
            issue_type="toc_level_capitalization",
            entry_index="0",
            entry_level="2",
            expected_or_reason="major_word_requires_capital",
            line_preview="Synthetic first toc entry marker ABC",
        ),
        _p024_finding(
            page=12,
            issue_type="toc_level_capitalization",
            entry_index="2",
            entry_level="2",
            expected_or_reason="major_word_requires_capital",
            line_preview="Synthetic third toc entry marker DEF",
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    p024_findings = [f for f in view.findings if f.rule_id == "P024"]
    assert len(p024_findings) == 2
    labels = {f.location_label for f in p024_findings}
    assert labels == {
        "Page 12 — Table of Contents, affected entry: 'Synthetic first toc entry marker ABC'",
        "Page 12 — Table of Contents, affected entry: 'Synthetic third toc entry marker DEF'",
    }


def test_p024_lof_sentence_case_display_comment_names_flagged_words() -> None:
    """The displayed comment for a List of Figures sentence-case finding must
    name the specific flagged word(s), not a generic 'multiple later words'
    message — and grouping is unaffected because the override happens after
    grouping (the underlying card-level comment stays generic)."""
    findings = [
        AuditFinding(
            rule_id="P024",
            severity=Severity.WARNING,
            page=15,
            message="List of Figures entry may not follow sentence-case style.",
            details={
                "page_type": "list_of_figures",
                "issue_type": "list_of_figures_sentence_case",
                "entry_index": "0",
                "flagged_words": "Schematic, Diagram",
                "confidence": "medium",
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    finding = next(f for f in view.findings if f.rule_id == "P024")
    assert "'Schematic'" in finding.polished_comment
    assert "'Diagram'" in finding.polished_comment
    assert "multiple later words" not in finding.polished_comment


def test_p040_entry_clause_uses_page_relative_index_not_document_global() -> None:
    """A List of Figures continuation page with 5 visible entries must not be
    labeled '(entry #6)' just because earlier pages already used indices 0-4
    — the display index must be relative to what is visible on that page."""
    findings = [
        AuditFinding(
            rule_id="P040",
            severity=Severity.WARNING,
            page=16,
            message="List of Figures entry does not end with terminal punctuation.",
            details={
                "issue_type": "lof_entry_missing_terminal_punctuation",
                # Document-global index carried over from an earlier page,
                # but this is the first (page-relative index 0) flagged entry
                # on *this* page.
                "entry_index": "5",
                "page_entry_index": "0",
            },
        )
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    finding = next(f for f in view.findings if f.rule_id == "P040")
    assert "(entry #1)" in finding.polished_comment
    assert "(entry #6)" not in finding.polished_comment


def test_p024_line_preview_never_rendered_in_comment_or_explanation() -> None:
    """line_preview may appear in the location label but not in comments or fixes."""
    secret = "Synthetic Sample Toc Entry Text Marker XYZ123"
    findings = [
        _p024_finding(
            page=12,
            issue_type="toc_level_capitalization",
            entry_index="0",
            entry_level="2",
            expected_or_reason="major_word_requires_capital",
        ),
        _p024_finding(
            page=8,
            issue_type="list_of_tables_title_case",
            entry_index="1",
            expected_or_reason="first_word_requires_capital",
        ),
        _p024_finding(
            page=9,
            issue_type="list_of_figures_sentence_case",
            entry_index="0",
        ),
        _p024_finding(
            page=8,
            issue_type="unexpected_terminal_punctuation",
            entry_index="1",
        ),
    ]
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)

    p024_findings = [f for f in view.findings if f.rule_id == "P024"]
    assert len(p024_findings) == 4
    for finding in p024_findings:
        assert secret not in finding.polished_comment
        assert secret not in finding.detailed_explanation
        assert secret in finding.location_label
        assert secret not in finding.suggested_fix


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "forbidden"),
    [
        ("P011", "margin_boundary_violation", "John Smith Dissertation Title"),
        ("P013", "page_number_candidate", "Figure 3.1 Neural network diagram"),
        ("P026", "possible_body_font_family_issue", "Chapter One Introduction text"),
        ("P030", "missing_continued_heading", "TABLE OF CONTENTS continued heading"),
        ("P033", "title_page_mismatch", "Yin Haotian"),
        ("P034", "copyright_author_not_found", "Committee Chair Name"),
        ("P061", "lof_cross_page_entry_numbers_not_nondecreasing", "Figure 2.4 Caption text"),
        ("P024", "toc_level_capitalization", "Background Of The Study And Its Implications"),
    ],
)
def test_polished_comments_are_privacy_safe(
    rule_id: str, issue_type: str, forbidden: str
) -> None:
    details = {
        "issue_type": issue_type,
        "observed_summary": forbidden,
        "caption": forbidden,
        "title": forbidden,
        "author": forbidden,
        "side": "left_margin",
        "position_type": "bottom_center",
        "run_start_page": "17",
        "run_end_page": "18",
        "confidence": "medium",
    }
    comment = build_polished_comment(
        rule_id=rule_id,
        issue_type=issue_type,
        page=5,
        details=details,
    )
    assert forbidden not in comment
    assert contains_blocked_detail_text(comment, details) is False
    assert "Review needed" in comment or "review" in comment.lower()


@pytest.mark.parametrize(
    ("issue_type", "extra_details"),
    [
        ("toc_level_capitalization", {"entry_level": "1"}),
        (
            "toc_level_capitalization",
            {"entry_level": "2", "expected_or_reason": "major_word_requires_capital"},
        ),
        ("list_of_tables_title_case", {"expected_or_reason": "first_word_requires_capital"}),
        ("list_of_figures_sentence_case", {}),
        ("unexpected_terminal_punctuation", {}),
    ],
)
def test_p024_build_polished_comment_never_quotes_line_preview(
    issue_type: str, extra_details: dict[str, str]
) -> None:
    """P024 line_preview may hold real document text; it must never reach the comment."""
    secret = "Synthetic Sample Toc Entry Text Marker XYZ123"
    details = {
        "page_type": "table_of_contents",
        "issue_type": issue_type,
        "line_preview": secret,
        "confidence": "medium",
        **extra_details,
    }
    comment = build_polished_comment(
        rule_id="P024",
        issue_type=issue_type,
        page=12,
        details=details,
    )
    assert secret not in comment
    assert contains_blocked_detail_text(comment, details) is False


def test_polished_comment_templates_for_key_rules() -> None:
    p011 = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=3,
        details={"side": "left_margin"},
    )
    assert "margin" in p011.lower()
    p013 = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=4,
        details={"position_type": "bottom_center"},
    )
    assert "page-number" in p013.lower() or "page number" in p013.lower()
    p061 = build_polished_comment(
        rule_id="P061",
        issue_type="lof_cross_page_entry_numbers_not_nondecreasing",
        page=None,
        details={"run_start_page": "17", "run_end_page": "18"},
    )
    assert "figures" in p061.lower() or "lof" in p061.lower()


def test_p011_location_label_states_measured_overrun() -> None:
    """The exact measured overrun must be visible per occurrence via
    location_label — not baked into the shared card-level comment, which
    would split identical margin problems across cards by overflow amount
    (see test_same_problem_with_different_confidence_stays_on_one_card_by_default)."""
    label = margin_location_label(
        {"side": "right_margin", "worst_overflow_pt": "3.5"}, 11
    )
    assert label == "Page 11 — right margin (~3.5 pt over)"


def test_p011_polished_comment_identical_regardless_of_overflow_or_confidence() -> None:
    """The card-level P011 comment must not vary with overflow amount or
    confidence — both feed build_grouped_findings()'s grouping key, and an
    instance-specific value there would silently break the "one card per
    problem type" grouping guarantee for a high-volume rule."""
    low_confidence = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=11,
        details={"side": "right_margin", "worst_overflow_pt": "3.5", "confidence": "low"},
    )
    high_confidence = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=11,
        details={"side": "right_margin", "worst_overflow_pt": "22.0", "confidence": "high"},
    )
    assert low_confidence == high_confidence


def test_polished_comment_fallback_unknown_rule() -> None:
    comment = build_polished_comment(
        rule_id="P999",
        issue_type="unknown_issue",
        page=1,
        details={},
    )
    # The generic fallback must never leak the raw internal rule_id into
    # student-facing text (fixed in the 2026-07-13 repository-polish audit —
    # see tests/test_rule_registry_consistency.py for the general regression
    # coverage). It previously read "This check (P999) found a possible ...".
    assert "P999" not in comment
    assert "This automated check found a possible" in comment
    assert "Review needed" in comment


def test_web_results_render_polished_comments(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)

    findings = _p011_findings(1)
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf", "job_id": "rv1"})
    view = build_report_view(payload)

    job = wa.JobState(
        job_id="rv1",
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        finding_count=view.total_findings,
        warn_count=1,
        fail_count=0,
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
            for rs in view.rule_summaries
        ],
        report_view=report_view_to_dict(view),
        md_preview="# report",
    )
    wa._set_job(job)

    client = TestClient(wa.app)
    resp = client.get("/audits/rv1")
    assert resp.status_code == 200
    assert b"Polished comment" in resp.content
    assert b"Likely problem" in resp.content
    assert b"Findings by topic" in resp.content


def test_json_download_unchanged_by_report_view(tmp_path: Path) -> None:
    findings = _p011_findings(1)
    metadata = {"audit_type": "pdf", "job_id": "dl1"}
    payload = audit_findings_to_json_dict(findings, metadata)
    build_report_view(payload)

    out = tmp_path / "report.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "grouped_summary" in loaded
    assert "grouped_findings" in loaded
    assert "findings" in loaded
    assert loaded["findings"][0]["rule_id"] == "P011"
