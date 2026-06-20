"""Tests for Phase 1 result-location clarity using already-captured finding details.

Covers metadata-only enrichment (no document-text quoting, no new bbox/
highlighting, no detector changes, no canonical rule/export schema changes)
for:

1. P020 — card-title differentiation by source/reason metadata
2. P024 — entry_level/reason metadata in toc_level_capitalization and
   list_of_tables_title_case comments
3. P011 — margin overflow magnitude (side, points, line count)
4. P036 — TOC/LoT/LoF inter-entry spacing (gap metrics, entry-pair index)
5. P035 — caption/body placement (float_number)
6. P040 — List of Figures terminal punctuation (entry index)
7. P018 — TOC/LoT/LoF alignment (affected entry count, worst offset)
8. Privacy invariants hold for every newly bespoke rule/issue_type
9. Grouped/problem-group rendering stays schema-compatible and findings
   become distinguishable when expanded
"""

from __future__ import annotations

import json
from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import (
    build_polished_comment,
    contains_blocked_detail_text,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view

# ---------------------------------------------------------------------------
# 1. P020 — card-title differentiation
# ---------------------------------------------------------------------------


def test_p020_card_title_differs_by_reason_and_source() -> None:
    findings = [
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=7,
            message="Title case issue.",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "source": "heading",
                "expected_or_reason": "first_word_requires_capital",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=7,
            message="Title case issue.",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "source": "caption",
                "expected_or_reason": "major_word_requires_capital",
                "confidence": "medium",
            },
        ),
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    labels = {fv.issue_type_label for fv in view.findings if fv.rule_id == "P020"}
    assert labels == {
        "Possible title-case issue (heading, first word)",
        "Possible title-case issue (table title, major word)",
    }


def test_p020_card_title_never_quotes_flagged_word() -> None:
    findings = [
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=7,
            message="Title case issue.",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "source": "heading",
                "expected_or_reason": "first_word_requires_capital",
                "line_preview": "an unforgettable confidential dissertation phrase",
                "confidence": "medium",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P020")
    assert "unforgettable confidential dissertation phrase" not in fv.issue_type_label
    assert "unforgettable confidential dissertation phrase" not in fv.polished_comment


# ---------------------------------------------------------------------------
# 2. P024 — entry_level/reason metadata
# ---------------------------------------------------------------------------


def test_p024_toc_level1_and_level2_comments_differ() -> None:
    level1 = build_polished_comment(
        rule_id="P024",
        issue_type="toc_level_capitalization",
        page=5,
        details={"entry_level": "1", "expected_or_reason": "Level 1 TOC entries expected ALL CAPS"},
    )
    level2 = build_polished_comment(
        rule_id="P024",
        issue_type="toc_level_capitalization",
        page=5,
        details={"entry_level": "2", "expected_or_reason": "major_word_requires_capital"},
    )
    assert level1 != level2
    assert "ALL CAPS" in level1
    assert "Title Case" in level2
    assert "Table of Contents" in level1 and "Table of Contents" in level2


def test_p024_lot_title_case_uses_reason_code() -> None:
    comment = build_polished_comment(
        rule_id="P024",
        issue_type="list_of_tables_title_case",
        page=9,
        details={"expected_or_reason": "first_word_requires_capital"},
    )
    assert "List of Tables" in comment
    assert "first word is not capitalized" in comment


# ---------------------------------------------------------------------------
# 3. P011 — margin overflow magnitude
# ---------------------------------------------------------------------------


def test_p011_comment_includes_overflow_and_line_count() -> None:
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Margin overflow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "worst_overflow_pt": "67.3",
                "affected_line_count": "4",
                "confidence": "high",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P011")
    assert "page 2 appears to cross the required left margin boundary" in fv.polished_comment
    assert "67.3pt beyond the boundary" in fv.polished_comment
    assert "across 4 text lines" in fv.polished_comment


def test_p011_comment_without_overflow_metadata_is_unchanged_shape() -> None:
    comment = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=2,
        details={"side": "left_margin", "confidence": "high"},
    )
    assert "page 2 appears to cross the required left margin boundary" in comment
    assert "beyond the boundary" not in comment


# ---------------------------------------------------------------------------
# 4. P036 — TOC/LoT/LoF inter-entry spacing
# ---------------------------------------------------------------------------


def _p036_finding(*, entry_pair_index: str, gap_points: str, page: int = 12) -> AuditFinding:
    return AuditFinding(
        rule_id="P036",
        severity=Severity.WARNING,
        page=page,
        message="Inter-entry spacing too tight.",
        details={
            "issue_type": "toc_inter_entry_spacing_too_tight",
            "section_type": "table_of_contents",
            "entry_pair_index": entry_pair_index,
            "gap_points": gap_points,
            "required_gap_points": "9.1",
            "gap_ratio": "0.35",
            "triage_tier": "medium",
        },
    )


def test_p036_distinguishes_entry_pairs_on_same_page() -> None:
    findings = [
        _p036_finding(entry_pair_index="3", gap_points="3.2"),
        _p036_finding(entry_pair_index="7", gap_points="2.1"),
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    comments = [fv.polished_comment for fv in view.findings if fv.rule_id == "P036"]
    assert len(comments) == 2
    assert comments[0] != comments[1]
    assert "entries 4-5" in comments[0]
    assert "entries 8-9" in comments[1]
    assert "observed gap 3.2pt" in comments[0]
    assert "observed gap 2.1pt" in comments[1]
    assert "about 0.35x the expected spacing" in comments[0]


def test_p036_avoids_generic_fallback_comment() -> None:
    findings = [
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=15,
            message="Inter-entry spacing too tight.",
            details={
                "issue_type": "lof_inter_entry_spacing_too_tight",
                "section_type": "list_of_figures",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P036")
    assert "found a possible" not in fv.polished_comment.lower()
    assert "List of Figures" in fv.polished_comment
    assert "two consecutive entries" in fv.polished_comment


def test_p036_grouping_key_is_stable_across_entry_pairs() -> None:
    """The grouping-time comment (used as the grouping key) must not vary by
    entry pair, or repeated same-page occurrences would stop collapsing into
    one card. Per-occurrence detail belongs only in the post-grouping
    display override, exercised by test_grouped_p036_individual_findings_are_distinguishable.
    """
    first = build_polished_comment(
        rule_id="P036",
        issue_type="toc_inter_entry_spacing_too_tight",
        page=12,
        details={"entry_pair_index": "0", "gap_points": "1.0"},
    )
    second = build_polished_comment(
        rule_id="P036",
        issue_type="toc_inter_entry_spacing_too_tight",
        page=12,
        details={"entry_pair_index": "5", "gap_points": "3.0"},
    )
    assert first == second


# ---------------------------------------------------------------------------
# 4b. P036 — Markdown report individual-finding listings ("## Problems" /
#     "## Findings by Rule") must also distinguish same-page occurrences.
#     These sections list every finding individually by build_polished_comment
#     directly, bypassing the report_view.py override exercised above, so they
#     need their own coverage.
# ---------------------------------------------------------------------------


def test_markdown_report_distinguishes_p036_entry_pairs_on_same_page(tmp_path: Path) -> None:
    from njit_auditor.report_outputs import write_markdown_report

    findings = [
        _p036_finding(entry_pair_index="0", gap_points="4.0"),
        _p036_finding(entry_pair_index="5", gap_points="3.0"),
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")

    headings = [line for line in text.splitlines() if line.startswith("### Problem")]
    assert len(headings) == 2
    assert headings[0] != headings[1]

    problem_lines = [line for line in text.splitlines() if line.startswith("- **Problem")]
    assert len(problem_lines) >= 2
    assert problem_lines[0] != problem_lines[1]
    assert "entries 1-2" in problem_lines[0]
    assert "entries 6-7" in problem_lines[1]
    assert "observed gap 4.0pt" in problem_lines[0]
    assert "observed gap 3.0pt" in problem_lines[1]


def test_markdown_report_p036_single_finding_is_not_duplicated(tmp_path: Path) -> None:
    from njit_auditor.report_outputs import write_markdown_report

    findings = [_p036_finding(entry_pair_index="2", gap_points="5.0")]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")

    headings = [line for line in text.splitlines() if line.startswith("### Problem")]
    assert len(headings) == 1


def test_markdown_report_p036_includes_section_and_gap_metadata_when_available(
    tmp_path: Path,
) -> None:
    from njit_auditor.report_outputs import write_markdown_report

    findings = [_p036_finding(entry_pair_index="1", gap_points="2.5")]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "Table of Contents" in text
    assert "entries 2-3" in text
    assert "observed gap 2.5pt" in text
    assert "expected at least 9.1pt" in text


def test_markdown_report_p036_does_not_fall_back_to_generic_wording(
    tmp_path: Path,
) -> None:
    from njit_auditor.report_outputs import write_markdown_report

    findings = [_p036_finding(entry_pair_index="4", gap_points="1.9")]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "found a possible toc inter entry spacing too tight issue" not in text


def test_markdown_report_p036_omits_gap_clause_without_measurements(
    tmp_path: Path,
) -> None:
    from njit_auditor.report_outputs import write_markdown_report

    findings = [
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=15,
            message="Inter-entry spacing too tight.",
            details={
                "issue_type": "lof_inter_entry_spacing_too_tight",
                "section_type": "list_of_figures",
            },
        )
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "List of Figures" in text
    assert "two consecutive entries" in text
    assert "observed gap" not in text


def test_markdown_report_p036_groups_same_gap_repeats_while_listing_individually(
    tmp_path: Path,
) -> None:
    """Two same-page, same-gap P036 occurrences are legitimate separate
    findings (e.g. two distinct tight pairs sharing identical metrics by
    coincidence), not duplicates, so both must still get their own "###
    Problem N" entry even though they collapse into one "## Grouped
    Problems" card.
    """
    from njit_auditor.report_outputs import write_markdown_report

    findings = [
        _p036_finding(entry_pair_index="0", gap_points="3.0"),
        _p036_finding(entry_pair_index="1", gap_points="3.0"),
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")

    headings = [line for line in text.splitlines() if line.startswith("### Problem")]
    assert len(headings) == 2
    assert "### P036 — 2 occurrences" in text


def test_markdown_report_p036_never_quotes_blocked_detail_text(
    tmp_path: Path,
) -> None:
    from njit_auditor.report_outputs import write_markdown_report

    forbidden = "Table of Contents Chapter 3: A Confidential Study"
    findings = [
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=12,
            message="Inter-entry spacing too tight.",
            details={
                "issue_type": "toc_inter_entry_spacing_too_tight",
                "section_type": "table_of_contents",
                "entry_pair_index": "0",
                "gap_points": "3.2",
                "required_gap_points": "9.1",
                "entry_text": forbidden,
                "observed_summary": forbidden,
            },
        )
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert forbidden not in text
    assert "/home/" not in text
    assert "Traceback" not in text
    assert "\\begin" not in text


# ---------------------------------------------------------------------------
# 5. P035 — caption/body placement (float_number)
# ---------------------------------------------------------------------------


def test_p035_comment_includes_float_number_when_available() -> None:
    findings = [
        AuditFinding(
            rule_id="P035",
            severity=Severity.WARNING,
            page=31,
            message="Caption placement.",
            details={"issue_type": "table_caption_not_above_body", "float_number": "4.3"},
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P035")
    assert "for Table 4.3" in fv.polished_comment
    assert "table caption" in fv.polished_comment.lower()
    assert "above" in fv.polished_comment


def test_p035_figure_comment_includes_float_number() -> None:
    findings = [
        AuditFinding(
            rule_id="P035",
            severity=Severity.WARNING,
            page=24,
            message="Caption placement.",
            details={"issue_type": "figure_body_not_centered", "float_number": "2.1"},
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P035")
    assert "for Figure 2.1" in fv.polished_comment
    assert "centered" in fv.polished_comment


def test_p035_comment_without_float_number_is_unchanged_shape() -> None:
    comment = build_polished_comment(
        rule_id="P035",
        issue_type="table_caption_not_above_body",
        page=31,
        details={},
    )
    assert "for Table" not in comment
    assert "table caption" in comment.lower()


def test_p035_grouping_key_is_stable_across_float_numbers() -> None:
    first = build_polished_comment(
        rule_id="P035",
        issue_type="table_caption_not_above_body",
        page=31,
        details={"float_number": "2.1"},
    )
    second = build_polished_comment(
        rule_id="P035",
        issue_type="table_caption_not_above_body",
        page=31,
        details={"float_number": "9.9"},
    )
    assert first == second


# ---------------------------------------------------------------------------
# 6. P040 — List of Figures terminal punctuation (entry index)
# ---------------------------------------------------------------------------


def test_p040_distinguishes_entries_by_index() -> None:
    findings = [
        AuditFinding(
            rule_id="P040",
            severity=Severity.WARNING,
            page=15,
            message="Missing terminal punctuation.",
            details={
                "issue_type": "lof_entry_missing_terminal_punctuation",
                "entry_index": str(idx),
            },
        )
        for idx in (6, 11)
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    comments = [fv.polished_comment for fv in view.findings if fv.rule_id == "P040"]
    assert "entry #7" in comments[0]
    assert "entry #12" in comments[1]
    assert comments[0] != comments[1]


# ---------------------------------------------------------------------------
# 7. P018 — TOC/LoT/LoF alignment (affected entry count, worst offset)
# ---------------------------------------------------------------------------


def test_p018_includes_affected_entry_count_and_offset() -> None:
    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=14,
            message="Misaligned page-number column.",
            details={
                "issue_type": "misaligned_page_number_column",
                "affected_entry_count": "3",
                "worst_delta_pt": "4.2",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P018")
    assert "3 entries affected" in fv.polished_comment
    assert "worst offset about 4.2pt" in fv.polished_comment
    assert "page-number column" in fv.polished_comment


def test_p018_missing_page_number_includes_count() -> None:
    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=14,
            message="Missing page number.",
            details={"issue_type": "missing_page_number", "affected_entry_count": "1"},
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P018")
    assert "1 entry affected" in fv.polished_comment
    assert "missing" in fv.polished_comment.lower()
    assert "page number" in fv.polished_comment.lower()


def test_p018_grouping_key_is_stable_across_entry_counts() -> None:
    first = build_polished_comment(
        rule_id="P018",
        issue_type="missing_page_number",
        page=14,
        details={"affected_entry_count": "1"},
    )
    second = build_polished_comment(
        rule_id="P018",
        issue_type="missing_page_number",
        page=14,
        details={"affected_entry_count": "9"},
    )
    assert first == second


# ---------------------------------------------------------------------------
# 8. Privacy invariants for every newly bespoke rule/issue_type
# ---------------------------------------------------------------------------


_NEW_BESPOKE_CASES: tuple[tuple[str, str, dict[str, str]], ...] = (
    ("P024", "toc_level_capitalization", {"entry_level": "2"}),
    ("P024", "list_of_tables_title_case", {}),
    ("P036", "toc_inter_entry_spacing_too_tight", {"entry_pair_index": "2"}),
    ("P035", "table_caption_not_above_body", {"float_number": "2.1"}),
    ("P040", "lof_entry_missing_terminal_punctuation", {"entry_index": "4"}),
    ("P018", "inconsistent_hierarchy_indent", {"affected_entry_count": "2"}),
)


def test_new_bespoke_comments_never_quote_blocked_detail_text() -> None:
    forbidden = "a long confidential dissertation sentence nobody should see"
    for rule_id, issue_type, extra_details in _NEW_BESPOKE_CASES:
        details: dict[str, str] = {
            "line_preview": forbidden,
            "observed_summary": forbidden,
            "confidence": "medium",
            **extra_details,
        }
        comment = build_polished_comment(
            rule_id=rule_id,
            issue_type=issue_type,
            page=10,
            details=details,
        )
        assert forbidden not in comment, f"{rule_id}/{issue_type} leaked blocked text"
        assert contains_blocked_detail_text(comment, details) is False


def test_new_display_overrides_never_quote_blocked_detail_text() -> None:
    """P036/P035/P040/P018 enrichment lives in report_view.py post-grouping
    overrides rather than build_polished_comment; check the same privacy
    invariant holds for the actual rendered FindingView.polished_comment.
    """
    forbidden = "a long confidential dissertation sentence nobody should see"
    cases: tuple[tuple[str, str, dict[str, str]], ...] = (
        ("P036", "toc_inter_entry_spacing_too_tight", {"entry_pair_index": "2"}),
        ("P035", "table_caption_not_above_body", {"float_number": "2.1"}),
        ("P040", "lof_entry_missing_terminal_punctuation", {"entry_index": "4"}),
        ("P018", "inconsistent_hierarchy_indent", {"affected_entry_count": "2"}),
    )
    for rule_id, issue_type, extra_details in cases:
        details: dict[str, str] = {
            "issue_type": issue_type,
            "line_preview": forbidden,
            "observed_summary": forbidden,
            "confidence": "medium",
            **extra_details,
        }
        findings = [
            AuditFinding(
                rule_id=rule_id,
                severity=Severity.WARNING,
                page=10,
                message="Detail.",
                details=details,
            )
        ]
        payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
        view = build_report_view(payload)
        fv = next(f for f in view.findings if f.rule_id == rule_id)
        assert forbidden not in fv.polished_comment, f"{rule_id}/{issue_type} leaked blocked text"


# ---------------------------------------------------------------------------
# 9. Grouped/problem-group rendering and export-schema compatibility
# ---------------------------------------------------------------------------


def test_grouped_p036_individual_findings_are_distinguishable() -> None:
    findings = [
        _p036_finding(entry_pair_index="0", gap_points="1.0"),
        _p036_finding(entry_pair_index="1", gap_points="1.5"),
        _p036_finding(entry_pair_index="2", gap_points="2.0"),
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    assert view.grouped_problems, "expected findings to form at least one group"
    gp = next(g for g in view.grouped_problems if g.rule_id == "P036")
    assert gp.is_grouped
    comments = [f.polished_comment for f in gp.individual_findings]
    assert len(comments) == len(set(comments)) == 3


def test_grouped_p035_individual_findings_are_distinguishable() -> None:
    findings = [
        AuditFinding(
            rule_id="P035",
            severity=Severity.WARNING,
            page=8,
            message="Caption placement.",
            details={"issue_type": "table_caption_not_above_body", "float_number": num},
        )
        for num in ("1.1", "1.2")
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    gp = next(g for g in view.grouped_problems if g.rule_id == "P035")
    assert gp.is_grouped
    comments = [f.polished_comment for f in gp.individual_findings]
    assert len(comments) == len(set(comments)) == 2


def test_grouped_p040_individual_findings_are_distinguishable() -> None:
    findings = [
        AuditFinding(
            rule_id="P040",
            severity=Severity.WARNING,
            page=15,
            message="Missing terminal punctuation.",
            details={"issue_type": "lof_entry_missing_terminal_punctuation", "entry_index": idx},
        )
        for idx in ("3", "9")
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    gp = next(g for g in view.grouped_problems if g.rule_id == "P040")
    assert gp.is_grouped
    comments = [f.polished_comment for f in gp.individual_findings]
    assert len(comments) == len(set(comments)) == 2


def test_grouped_p018_individual_findings_are_distinguishable() -> None:
    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=14,
            message="Misaligned page-number column.",
            details={
                "issue_type": "misaligned_page_number_column",
                "affected_entry_count": count,
            },
        )
        for count in ("2", "5")
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    gp = next(g for g in view.grouped_problems if g.rule_id == "P018")
    assert gp.is_grouped
    comments = [f.polished_comment for f in gp.individual_findings]
    assert len(comments) == len(set(comments)) == 2


def test_raw_finding_details_unchanged_by_report_view() -> None:
    findings = [
        _p036_finding(entry_pair_index="0", gap_points="1.0"),
        AuditFinding(
            rule_id="P035",
            severity=Severity.WARNING,
            page=24,
            message="Caption placement.",
            details={"issue_type": "figure_body_not_centered", "float_number": "2.1"},
        ),
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    before = json.loads(json.dumps(payload["findings"]))
    build_report_view(payload)
    assert payload["findings"] == before
