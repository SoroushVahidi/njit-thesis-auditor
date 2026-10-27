import json
import re
from pathlib import Path

from njit_auditor.coverage_disclosure import STUDENT_LIMITATION_DISCLOSURE
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import (
    P011_ISSUE_TYPE,
    P012_ISSUE_TYPE,
    P013_DOC_ISSUE_TYPE,
    P013_PAGE_ISSUE_TYPE,
    P026_FAMILY_ISSUE_TYPE,
    P026_SIZE_ISSUE_TYPE,
    audit_findings_to_json_dict,
    build_grouped_findings,
    build_grouped_summary,
    build_p011_margin_triage_summary,
    build_p012_annotation_triage_summary,
    build_p013_triage_summary,
    build_p019_page_numbering_triage_summary,
    build_p026_font_triage_summary,
    build_p036_toc_list_spacing_triage_summary,
    build_p038_frontmatter_heading_triage_summary,
    build_p044_abstract_indentation_triage_summary,
    compact_page_list,
    convert_pxxx_tokens_to_public_display,
    public_display_rule_id,
    write_json_report,
    write_markdown_report,
)
from njit_auditor.report_view import build_report_view


def _sample_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Possible text outside margin.",
            details={"side": "left_margin", "suggested_fix": "Adjust margins."},
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=2,
            message="Candidate page number found.",
            details={"location": "bottom"},
        ),
        AuditFinding(
            rule_id="P014",
            severity=Severity.WARNING,
            page=1,
            message="Heading not centered.",
            details={"centered": "False"},
        ),
    ]


def _metadata() -> dict[str, str]:
    return {
        "input_file_path": "example/thesis.pdf",
        "input_file_name": "thesis.pdf",
        "audit_type": "pdf",
    }


def _p026_findings(count: int = 10) -> list[AuditFinding]:
    """Synthetic P026 family warnings across multiple pages."""
    return [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=i + 1,
            message=f"Body text on page {i + 1} may not use Times New Roman.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "observed_summary": "CMR12, CMBX12",
                "confidence": "medium",
                "affected_span_count": "8",
                "candidate_count": "10",
            },
        )
        for i in range(count)
    ]


def _p011_mixed_findings() -> list[AuditFinding]:
    """P011 warnings on consecutive pages grouped by margin side."""
    findings: list[AuditFinding] = []
    for page in range(1, 6):
        findings.append(
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=page,
                message="Possible text crossing left_margin.",
                details={
                    "side": "left_margin",
                    "issue_type": P011_ISSUE_TYPE,
                    "worst_overflow_pt": "12.5",
                    "affected_line_count": "3",
                    "confidence": "high",
                    "triage_tier": "informational",
                },
            )
        )
    for page in range(6, 9):
        findings.append(
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=page,
                message="Possible text crossing right_margin.",
                details={
                    "side": "right_margin",
                    "issue_type": P011_ISSUE_TYPE,
                    "worst_overflow_pt": "8.2",
                    "affected_line_count": "2",
                    "confidence": "medium",
                    "triage_tier": "informational",
                },
            )
        )
    findings.append(
        AuditFinding(
            rule_id="P011",
            severity=Severity.PASS,
            message="No obvious margin-boundary text violations detected.",
        )
    )
    return findings


def _p026_mixed_findings() -> list[AuditFinding]:
    """P026 findings with two font-label bands and a size-issue band for range tests."""
    findings: list[AuditFinding] = []
    for page in range(1, 6):
        findings.append(
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=page,
                message=f"Body text on page {page} may not use Times New Roman.",
                details={
                    "issue_type": P026_FAMILY_ISSUE_TYPE,
                    "observed_summary": "CMR12",
                    "confidence": "medium",
                    "triage_tier": "informational",
                },
            )
        )
    for page in range(6, 9):
        findings.append(
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=page,
                message=f"Body text on page {page} may not use Times New Roman.",
                details={
                    "issue_type": P026_FAMILY_ISSUE_TYPE,
                    "observed_summary": "CMBX12, CMR12",
                    "confidence": "medium",
                    "triage_tier": "informational",
                },
            )
        )
    for page in (9, 10):
        findings.append(
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=page,
                message=f"Body text on page {page} may not use 12pt font size.",
                details={
                    "issue_type": P026_SIZE_ISSUE_TYPE,
                    "observed_summary": "11.0pt",
                    "confidence": "medium",
                    "triage_tier": "informational",
                },
            )
        )
    return findings


def _p013_findings(count: int = 8) -> list[AuditFinding]:
    """Synthetic P013 candidate findings mirroring production detail fields."""
    findings: list[AuditFinding] = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            message="Detected possible page-number candidates.",
            details={
                "issue_type": P013_DOC_ISSUE_TYPE,
                "candidate_count": str(count),
                "triage_tier": "informational",
            },
        )
    ]
    for i in range(count):
        page = i + 1
        multi = page == 3
        findings.append(
            AuditFinding(
                rule_id="P013",
                severity=Severity.WARNING,
                page=page,
                message=f"Page has {2 if multi else 1} page-number-like candidate(s).",
                details={
                    "issue_type": P013_PAGE_ISSUE_TYPE,
                    "location": "bottom",
                    "position_type": "bottom_center",
                    "number_style": "arabic" if page <= 5 else "roman_lower",
                    "candidate_count_on_page": "2" if multi else "1",
                    "observed_summary": (
                        "bottom_center/arabic" if page <= 5 else "bottom_center/roman_lower"
                    ),
                    "confidence": "medium",
                    "triage_tier": "informational",
                },
            )
        )
    return findings


def _repeated_margin_findings(
    pages: list[int],
    *,
    severity: Severity = Severity.WARNING,
    side: str = "left_margin",
    suggested_fix: str = "Adjust the affected margin in the PDF export.",
    confidence: str = "medium",
) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P011",
            severity=severity,
            page=page,
            message=f"Possible text crossing {side}.",
            details={
                "issue_type": P011_ISSUE_TYPE,
                "side": side,
                "confidence": confidence,
                "suggested_fix": suggested_fix,
            },
        )
        for page in pages
    ]


def _repeated_tex_findings(
    lines: list[int],
    *,
    file_name: str = "/tmp/private/thesis.tex",
) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P001",
            severity=Severity.WARNING,
            message="Avoid shell escape commands in TeX source.",
            details={
                "file": file_name,
                "line": str(line),
                "issue_type": "risky_command",
                "command": "\\write18",
                "suggested_fix": "Remove the shell-escape command from the source.",
            },
        )
        for line in lines
    ]


# ---- compact_page_list unit tests ----


def test_compact_page_list_empty() -> None:
    assert compact_page_list([]) == ""


def test_compact_page_list_single() -> None:
    assert compact_page_list([5]) == "5"


def test_compact_page_list_range() -> None:
    assert compact_page_list([1, 2, 3]) == "1-3"


def test_compact_page_list_mixed() -> None:
    assert compact_page_list([1, 2, 3, 5, 7, 8]) == "1-3, 5, 7-8"


def test_compact_page_list_deduplicates() -> None:
    assert compact_page_list([3, 3, 5, 5]) == "3, 5"


def test_compact_page_list_truncates_long() -> None:
    pages = list(range(1, 100, 2))  # 1,3,5,... — 50 isolated pages, >8 ranges
    result = compact_page_list(pages, max_ranges=3)
    assert "..." in result
    assert "50 pages total" in result


# ---- build_grouped_findings tests ----


def test_build_grouped_findings_groups_identical_pdf_findings_across_pages() -> None:
    findings = _repeated_margin_findings([7, 3, 4, 5, 5])
    grouped = build_grouped_findings(findings, "pdf")

    assert len(grouped) == 1
    entry = grouped[0]
    assert entry["rule_id"] == "P011"
    assert entry["occurrence_count"] == 5
    assert entry["pages"] == [3, 4, 5, 7]
    assert entry["page_ranges"] == ["3–5", "7"]
    assert entry["affected_label"] == "Pages"
    assert entry["affected_compact"] == "3–5, 7"
    assert entry["individual_indexes"] == [0, 1, 2, 3, 4]


def test_build_grouped_findings_uses_roman_page_labels_when_available() -> None:
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=page,
            message="Page has one page-number-like candidate.",
            details={
                "issue_type": P013_PAGE_ISSUE_TYPE,
                "position_type": "bottom_center",
                "number_style": "roman_lower",
                "page_label": label,
                "confidence": "medium",
            },
        )
        for page, label in ((1, "vii"), (2, "viii"), (3, "ix"))
    ]

    grouped = build_grouped_findings(findings, "pdf")

    assert len(grouped) == 1
    assert grouped[0]["page_label_ranges"] == ["vii–ix"]
    assert grouped[0]["affected_compact"] == "vii–ix"


def test_build_grouped_findings_keeps_meaningful_pdf_differences_separate() -> None:
    findings = (
        _repeated_margin_findings([3, 4], side="left_margin")
        + _repeated_margin_findings([5], side="right_margin")
        + _repeated_margin_findings([6], severity=Severity.FAIL)
        + _repeated_margin_findings(
            [7],
            suggested_fix="Regenerate the PDF with the correct left margin setting.",
        )
    )

    grouped = build_grouped_findings(findings, "pdf")

    assert len(grouped) == 4
    counts = sorted(entry["occurrence_count"] for entry in grouped)
    assert counts == [1, 1, 1, 2]
    assert {entry["severity"] for entry in grouped} == {"WARNING", "FAIL"}


def test_build_grouped_findings_merges_same_problem_across_confidence_levels() -> None:
    """Confidence must not split an otherwise-identical problem into separate cards.

    Per-occurrence confidence is preserved via confidence_levels for display layers
    (report_view.py) to aggregate; only the grouping key itself ignores confidence.
    """
    findings = _repeated_margin_findings([3, 4], confidence="high") + _repeated_margin_findings(
        [5], confidence="low"
    )

    grouped = build_grouped_findings(findings, "pdf")

    assert len(grouped) == 1
    entry = grouped[0]
    assert entry["occurrence_count"] == 3
    assert entry["confidence_levels"] == ["high", "low"]
    assert entry["confidence"] == "mixed"


def test_build_grouped_findings_keeps_single_confidence_value_when_uniform() -> None:
    findings = _repeated_margin_findings([3, 4, 5], confidence="medium")

    grouped = build_grouped_findings(findings, "pdf")

    assert len(grouped) == 1
    entry = grouped[0]
    assert entry["confidence_levels"] == ["medium"]
    assert entry["confidence"] == "medium"


def test_build_grouped_findings_keeps_distinct_issue_types_separate() -> None:
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page has multiple page-number-like candidates.",
            details={
                "issue_type": "page_number_multiple_candidates",
                "position_type": "bottom_center",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=4,
            message="Page is missing a page-number candidate.",
            details={
                "issue_type": "page_number_missing_candidate",
                "position_type": "bottom_center",
                "confidence": "medium",
            },
        ),
    ]

    grouped = build_grouped_findings(findings, "pdf")

    assert len(grouped) == 2
    assert {entry["issue_type"] for entry in grouped} == {
        "page_number_missing_candidate",
        "page_number_multiple_candidates",
    }


def test_build_grouped_findings_groups_tex_locations_by_file_and_line_ranges() -> None:
    findings = _repeated_tex_findings([12, 18, 19, 20, 21])

    grouped = build_grouped_findings(findings, "tex")

    assert len(grouped) == 1
    entry = grouped[0]
    assert entry["occurrence_count"] == 5
    assert entry["locations"] == [
        "thesis.tex:12",
        "thesis.tex:18",
        "thesis.tex:19",
        "thesis.tex:20",
        "thesis.tex:21",
    ]
    assert entry["location_ranges"] == ["thesis.tex:12", "thesis.tex:18–21"]
    assert entry["locations_compact"] == "thesis.tex:12, thesis.tex:18–21"
    assert entry["affected_label"] == "Locations"
    assert entry["affected_compact"] == "thesis.tex:12, thesis.tex:18–21"
    assert "/tmp/private/" not in entry["locations_compact"]


def test_build_grouped_findings_preserves_raw_count_via_occurrence_counts() -> None:
    findings = _repeated_margin_findings([3, 4, 5]) + _repeated_margin_findings(
        [10], side="right_margin"
    )

    grouped = build_grouped_findings(findings, "pdf")

    assert sum(entry["occurrence_count"] for entry in grouped) == len(findings)
    assert all(entry["individual_indexes"] for entry in grouped)


def test_build_grouped_findings_assigns_every_raw_finding_once_with_missing_optional_metadata(
) -> None:
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Possible text crossing left_margin.",
            details={},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=4,
            message="Possible text crossing left_margin.",
            details={"side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=12,
            message="Missing continued heading.",
            details={},
        ),
    ]

    grouped = build_grouped_findings(findings, "pdf")
    all_indexes = sorted(
        index
        for entry in grouped
        for index in entry["individual_indexes"]
    )

    assert sum(entry["occurrence_count"] for entry in grouped) == len(findings)
    assert all_indexes == list(range(len(findings)))


# ---- build_grouped_summary tests ----


def test_grouped_summary_has_required_keys() -> None:
    summary = build_grouped_summary(_p026_findings(10))
    assert "high_volume_rules" in summary
    assert "by_rule_issue_type" in summary


def test_grouped_summary_high_volume_includes_p026() -> None:
    summary = build_grouped_summary(_p026_findings(10))
    hv = summary["high_volume_rules"]
    rule_ids = [e["rule_id"] for e in hv]
    assert "P026" in rule_ids


def test_grouped_summary_counts_match() -> None:
    findings = _p026_findings(10)
    summary = build_grouped_summary(findings)
    p026_entry = next(e for e in summary["high_volume_rules"] if e["rule_id"] == "P026")
    assert p026_entry["count"] == 10
    assert p026_entry["affected_page_count"] == 10


def test_grouped_summary_below_threshold_not_in_high_volume() -> None:
    # 3 findings < HIGH_VOLUME_THRESHOLD (5) → not in high_volume_rules
    findings = _p026_findings(3)
    summary = build_grouped_summary(findings)
    rule_ids = [e["rule_id"] for e in summary["high_volume_rules"]]
    assert "P026" not in rule_ids


def test_grouped_summary_by_rule_issue_type_populated() -> None:
    findings = _p026_findings(10)
    summary = build_grouped_summary(findings)
    assert "P026" in summary["by_rule_issue_type"]
    p026_breakdown = summary["by_rule_issue_type"]["P026"]
    assert "possible_body_font_family_issue" in p026_breakdown
    assert p026_breakdown["possible_body_font_family_issue"]["count"] == 10


def test_grouped_summary_page_compact_for_p026() -> None:
    findings = _p026_findings(10)
    summary = build_grouped_summary(findings)
    p026_entry = next(e for e in summary["high_volume_rules"] if e["rule_id"] == "P026")
    # Pages 1–10 should compact to "1-10"
    assert "1-10" in p026_entry["affected_pages_compact"]


def test_grouped_summary_observed_summary_sample_present() -> None:
    findings = _p026_findings(10)
    summary = build_grouped_summary(findings)
    p026_entry = next(e for e in summary["high_volume_rules"] if e["rule_id"] == "P026")
    assert "CMR12" in p026_entry.get("observed_summary_sample", "")


def test_grouped_summary_p013_included() -> None:
    findings = _p013_findings(8)
    summary = build_grouped_summary(findings)
    rule_ids = [e["rule_id"] for e in summary["high_volume_rules"]]
    assert "P013" in rule_ids


def test_p013_triage_summary_issue_type_counts() -> None:
    findings = _p013_findings(8)
    triage = build_p013_triage_summary(findings)
    assert triage is not None
    assert triage["issue_type_counts"][P013_PAGE_ISSUE_TYPE] == 8
    assert triage["issue_type_counts"][P013_DOC_ISSUE_TYPE] == 1
    assert triage["pages_with_multiple_candidates"] == 1


def test_p013_triage_consecutive_pages_compact_range() -> None:
    findings = _p013_findings(8)
    triage = build_p013_triage_summary(findings)
    assert triage is not None
    assert "1-5" in triage["pattern_page_ranges"]["bottom_center/arabic"]
    assert "6-8" in triage["pattern_page_ranges"]["bottom_center/roman_lower"]
    assert "1-8" in triage["affected_pages_compact"]


def test_p013_calibration_buckets_and_pattern_label() -> None:
    triage = build_p013_triage_summary(_p013_findings(8))
    assert triage is not None
    assert triage["document_pattern_label"] == "mostly_routine_pattern_with_outliers"
    assert triage["dominant_pattern"] == "bottom_center/arabic"
    assert triage["dominant_pattern_page_count"] == 5
    assert triage["dominant_pattern_share_pct"] == 62.5
    buckets = triage["calibration_buckets"]
    assert buckets["routine_single_candidate_dominant_pattern"]["count"] == 4
    assert buckets["routine_single_candidate_dominant_pattern"]["pages_compact"] == "1-2, 4-5"
    assert buckets["multi_candidate_pages"]["count"] == 1
    assert buckets["multi_candidate_pages"]["pages_compact"] == "3"
    assert buckets["other_pattern_or_low_confidence"]["count"] == 3
    assert buckets["other_pattern_or_low_confidence"]["pages_compact"] == "6-8"


def test_p013_triage_in_grouped_summary() -> None:
    findings = _p013_findings(8)
    summary = build_grouped_summary(findings)
    assert "p013_triage" in summary
    assert summary["p013_triage"]["affected_page_count"] == 8


def test_p013_raw_findings_preserved_in_json() -> None:
    findings = _p013_findings(8)
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 9
    assert payload["grouped_summary"]["p013_triage"]["raw_finding_count"] == 9
    routine_candidates = [
        finding
        for finding in payload["findings"]
        if finding["rule_id"] == "P013"
        and (finding["details"] or {}).get("issue_type") == P013_PAGE_ISSUE_TYPE
        and finding.get("student_facing_role") == "inventory"
    ]
    assert len(routine_candidates) == 7
    assert payload["metadata"]["inventory_finding_count"] == 7
    assert all(finding["student_visible_problem"] is False for finding in routine_candidates)


def test_markdown_report_includes_p013_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "report_p013.md"
    write_markdown_report(_p013_findings(8), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "R013 Page-Number Candidate Inventory" in text
    assert "P013 Page-Number Candidate Inventory" not in text
    assert "bottom_center/arabic" in text
    assert "Calibration buckets" in text
    assert "Document pattern label" in text
    assert "detector entries are retained as inventory evidence" in text
    assert "Issue type counts" in text
    triage_pos = text.index("R013 Page-Number Candidate Inventory")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos


def _extract_findings_by_rule_subsection(text: str, rule_id: str) -> str:
    """Return the text of one rule's "### {rule_id}" block under "## Findings by Rule".

    ``rule_id`` is the internal Pxxx id (matching how test fixtures build
    AuditFinding objects); the rendered Markdown shows the Rxxx display form
    (see public_display_rule_id / convert_pxxx_tokens_to_public_display), so
    the heading searched for here is the converted form.
    """
    display_rule_id = public_display_rule_id(rule_id)
    findings_by_rule_idx = text.index("## Findings by Rule")
    section = text[findings_by_rule_idx:]
    heading = f"### {display_rule_id}"
    start = section.index(heading) + len(heading)
    rest = section[start:]
    next_heading_idx = rest.find("\n### ")
    end_idx = next_heading_idx if next_heading_idx != -1 else rest.find("\n## ")
    return rest[: end_idx if end_idx != -1 else None]


def test_markdown_findings_by_rule_summarizes_p013_informational_candidates(
    tmp_path: Path,
) -> None:
    """Routine P013 candidates must be summarized, not listed flat, like the web UI."""
    output_path = tmp_path / "report_p013.md"
    write_markdown_report(_p013_findings(8), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    section = _extract_findings_by_rule_subsection(text, "P013")

    assert section.count("- **Problem") == 1
    assert "7 additional detected page-number candidates" in section
    assert (
        "These are detected page-number candidates used by the auditor and are "
        "not counted as formatting problems unless another finding reports a "
        "specific defect."
    ) in section
    assert "informational" in section.lower()


def test_markdown_findings_by_rule_omits_routine_only_p013_candidates(
    tmp_path: Path,
) -> None:
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=1,
            message="Page has 1 page-number-like candidate(s).",
            details={
                "issue_type": P013_PAGE_ISSUE_TYPE,
                "position_type": "bottom_center",
                "number_style": "roman_lower",
                "candidate_count_on_page": "1",
                "observed_summary": "bottom_center/roman_lower",
                "confidence": "medium",
                "triage_tier": "informational",
            },
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=2,
            message="Page has 1 page-number-like candidate(s).",
            details={
                "issue_type": P013_PAGE_ISSUE_TYPE,
                "position_type": "bottom_center",
                "number_style": "arabic",
                "candidate_count_on_page": "1",
                "observed_summary": "bottom_center/arabic",
                "confidence": "medium",
                "triage_tier": "informational",
            },
        ),
    ]
    output_path = tmp_path / "report_p013_routine.md"
    write_markdown_report(findings, _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    findings_by_rule = text.split("## Findings by Rule", 1)[1]

    assert "R013 Page-Number Candidate Inventory" in text
    assert "### R013" not in findings_by_rule
    assert "### P013" not in findings_by_rule


def test_markdown_findings_by_rule_keeps_real_p013_problem_individually_listed(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "report_p013.md"
    write_markdown_report(_p013_findings(8), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    section = _extract_findings_by_rule_subsection(text, "P013")

    assert "Multiple page-number-like tokens" in section
    assert "Problem 1" in section


def test_markdown_p013_informational_summary_breaks_down_by_page_position_style(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "report_p013.md"
    write_markdown_report(_p013_findings(8), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    section = _extract_findings_by_rule_subsection(text, "P013")

    assert "Pages:" in section
    assert "Position:" in section
    assert "Number style:" in section
    assert "R013 Page-Number Candidate Inventory" in section


def test_markdown_findings_by_rule_unaffected_for_non_p013_rules(tmp_path: Path) -> None:
    """A rule with no problem/informational split still lists every finding."""
    output_path = tmp_path / "report_p026.md"
    write_markdown_report(_p026_findings(6), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    section = _extract_findings_by_rule_subsection(text, "P026")

    assert section.count("- **") == 6
    assert "informational" not in section.lower()


def test_p013_view_and_markdown_agree_on_visible_problem_count() -> None:
    """report_view.py (web) and report_outputs.py (Markdown) must draw the same line
    between real P013 problems and informational candidates for identical findings.

    The document-overview entry is excluded from both: the web inventory never
    displays it, and Markdown's informational summary only counts per-page
    candidates (the overview is already reflected in the triage section).
    """
    findings = _p013_findings(8)
    payload = audit_findings_to_json_dict(findings, _metadata())
    view = build_report_view(payload)

    p013_serialized = [f for f in payload["findings"] if f["rule_id"] == "P013"]
    markdown_visible_count = sum(
        1
        for f in p013_serialized
        if isinstance(f.get("problem_number"), int) and f["problem_number"] > 0
    )
    markdown_page_level_informational_count = sum(
        1
        for f in p013_serialized
        if not (isinstance(f.get("problem_number"), int) and f["problem_number"] > 0)
        and (f.get("details") or {}).get("issue_type") == P013_PAGE_ISSUE_TYPE
    )

    view_visible_count = sum(1 for f in view.findings if f.rule_id == "P013")
    view_informational_count = sum(1 for f in view.inventory_findings if f.rule_id == "P013")

    assert markdown_visible_count == view_visible_count == 1
    assert markdown_page_level_informational_count == view_informational_count == 7


def test_non_p013_grouped_summary_unchanged_for_p026() -> None:
    findings = _p026_findings(10)
    summary = build_grouped_summary(findings)
    assert "p013_triage" not in summary
    assert "p026_font_triage" in summary
    p026_entry = next(e for e in summary["high_volume_rules"] if e["rule_id"] == "P026")
    assert p026_entry["count"] == 10


def test_p026_triage_issue_type_counts() -> None:
    triage = build_p026_font_triage_summary(_p026_mixed_findings())
    assert triage is not None
    assert triage["issue_type_counts"][P026_FAMILY_ISSUE_TYPE] == 8
    assert triage["issue_type_counts"][P026_SIZE_ISSUE_TYPE] == 2


def test_p026_triage_font_label_counts() -> None:
    triage = build_p026_font_triage_summary(_p026_mixed_findings())
    assert triage is not None
    assert triage["font_label_counts"]["CMR12"] == 5
    assert triage["font_label_counts"]["CMBX12, CMR12"] == 3
    assert triage["size_observed_label_counts"]["11.0pt"] == 2


def test_p026_triage_consecutive_pages_compact_range() -> None:
    triage = build_p026_font_triage_summary(_p026_mixed_findings())
    assert triage is not None
    patterns = triage["pattern_page_ranges"]
    assert "1-5" in patterns[f"{P026_FAMILY_ISSUE_TYPE}/CMR12"]
    assert "6-8" in patterns[f"{P026_FAMILY_ISSUE_TYPE}/CMBX12, CMR12"]
    assert "9-10" in patterns[f"{P026_SIZE_ISSUE_TYPE}/11.0pt"]
    assert "1-10" in triage["affected_pages_compact"]


def test_p026_calibration_buckets_and_pattern_label() -> None:
    triage = build_p026_font_triage_summary(_p026_mixed_findings())
    assert triage is not None
    assert triage["document_pattern_label"] == "dominant_font_pattern_with_outliers"
    assert triage["dominant_pattern"] == f"{P026_FAMILY_ISSUE_TYPE}/CMR12"
    assert triage["dominant_pattern_page_count"] == 5
    assert triage["dominant_pattern_share_pct"] == 50.0
    buckets = triage["calibration_buckets"]
    assert buckets["routine_single_issue_dominant_pattern"]["count"] == 5
    assert buckets["routine_single_issue_dominant_pattern"]["pages_compact"] == "1-5"
    assert buckets["pages_with_both_issue_types"]["count"] == 0
    assert buckets["pages_with_both_issue_types"]["pages_compact"] == ""
    assert buckets["size_issue_only_pages"]["count"] == 2
    assert buckets["size_issue_only_pages"]["pages_compact"] == "9-10"
    assert buckets["non_dominant_family_only_pages"]["count"] == 3
    assert buckets["non_dominant_family_only_pages"]["pages_compact"] == "6-8"


def test_p026_triage_in_grouped_summary() -> None:
    summary = build_grouped_summary(_p026_mixed_findings())
    assert summary["p026_font_triage"]["affected_page_count"] == 10


def test_p026_raw_findings_preserved_in_json() -> None:
    findings = _p026_mixed_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 10
    assert payload["grouped_summary"]["p026_font_triage"]["raw_finding_count"] == 10


def test_markdown_report_includes_p026_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "report_p026.md"
    write_markdown_report(_p026_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "R026 Body Font Compliance Triage" in text
    assert "P026 Body Font Compliance Triage" not in text
    assert "CMR12" in text
    assert "Calibration buckets" in text
    assert "Document pattern label" in text
    assert "not suppressed or re-scored" in text
    assert "Issue type counts" in text
    triage_pos = text.index("R026 Body Font Compliance Triage")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos


def test_p013_and_p026_triage_coexist() -> None:
    findings = _p013_findings(8) + _p026_findings(10)
    summary = build_grouped_summary(findings)
    assert "p013_triage" in summary
    assert "p026_font_triage" in summary


def test_p011_triage_side_counts() -> None:
    triage = build_p011_margin_triage_summary(_p011_mixed_findings())
    assert triage is not None
    assert triage["side_counts"]["left_margin"] == 5
    assert triage["side_counts"]["right_margin"] == 3
    assert triage["raw_finding_count"] == 8


def test_p011_triage_consecutive_pages_compact_range() -> None:
    triage = build_p011_margin_triage_summary(_p011_mixed_findings())
    assert triage is not None
    assert "1-5" in triage["pattern_page_ranges"]["left_margin"]
    assert "6-8" in triage["pattern_page_ranges"]["right_margin"]


def test_p011_triage_overflow_summary() -> None:
    triage = build_p011_margin_triage_summary(_p011_mixed_findings())
    assert triage is not None
    assert triage["max_overflow_by_side_pt"]["left_margin"] == 12.5
    assert triage["median_overflow_by_side_pt"]["right_margin"] == 8.2


def test_p011_triage_in_grouped_summary() -> None:
    summary = build_grouped_summary(_p011_mixed_findings())
    assert "p011_margin_triage" in summary
    assert summary["p011_margin_triage"]["affected_page_count"] == 8


def test_p011_raw_findings_preserved_in_json() -> None:
    findings = _p011_mixed_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 9
    assert payload["grouped_summary"]["p011_margin_triage"]["raw_finding_count"] == 8


def test_markdown_report_includes_p011_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "report_p011.md"
    write_markdown_report(_p011_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "R011 Margin/Overflow Triage" in text
    assert "P011 Margin/Overflow Triage" not in text
    assert "left_margin" in text
    assert "Overflow distance by side" in text
    triage_pos = text.index("R011 Margin/Overflow Triage")
    p013_pos = text.find("R013 Page-Number Candidate Inventory")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos
    if p013_pos >= 0:
        assert triage_pos < p013_pos


def test_p011_p013_p026_triage_coexist() -> None:
    findings = _p011_mixed_findings() + _p013_findings(8) + _p026_findings(10)
    summary = build_grouped_summary(findings)
    assert "p011_margin_triage" in summary
    assert "p013_triage" in summary
    assert "p026_font_triage" in summary


def _p012_mixed_findings() -> list[AuditFinding]:
    """Synthetic P012 annotations across pages and types."""
    findings: list[AuditFinding] = []
    for page in range(1, 6):
        findings.append(
            AuditFinding(
                rule_id="P012",
                severity=Severity.WARNING,
                page=page,
                message="PDF annotation/comment detected (Text).",
                details={
                    "issue_type": P012_ISSUE_TYPE,
                    "annotation_type": "Text",
                    "content": "Private reviewer note should not appear in triage",
                    "rect": "100.0,120.0,200.0,140.0",
                    "triage_tier": "informational",
                },
            )
        )
    for page in range(6, 9):
        findings.append(
            AuditFinding(
                rule_id="P012",
                severity=Severity.WARNING,
                page=page,
                message="PDF annotation/comment detected (Highlight).",
                details={
                    "issue_type": P012_ISSUE_TYPE,
                    "annotation_type": "Highlight",
                    "content": "Another secret comment",
                    "rect": "50.0,60.0,150.0,80.0",
                    "triage_tier": "informational",
                },
            )
        )
    findings.append(
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=5,
            message="PDF annotation/comment detected (Text).",
            details={
                "issue_type": P012_ISSUE_TYPE,
                "annotation_type": "Text",
                "content": "Second annotation on page 5",
                "triage_tier": "informational",
            },
        )
    )
    return findings


def test_p012_triage_annotation_type_counts() -> None:
    triage = build_p012_annotation_triage_summary(_p012_mixed_findings())
    assert triage is not None
    assert triage["annotation_type_counts"]["Text"] == 6
    assert triage["annotation_type_counts"]["Highlight"] == 3


def test_p012_triage_consecutive_pages_compact_range() -> None:
    triage = build_p012_annotation_triage_summary(_p012_mixed_findings())
    assert triage is not None
    assert "1-5" in triage["type_page_ranges"]["Text"]
    assert "6-8" in triage["type_page_ranges"]["Highlight"]
    assert "1-8" in triage["affected_pages_compact"]
    assert triage["pages_with_multiple_annotations"] == 1
    assert "5" in triage["multiple_annotations_pages_compact"]


def test_p012_triage_in_grouped_summary() -> None:
    summary = build_grouped_summary(_p012_mixed_findings())
    assert summary["p012_annotation_triage"]["affected_page_count"] == 8


def test_p012_triage_absent_when_no_findings() -> None:
    assert build_p012_annotation_triage_summary([]) is None
    summary = build_grouped_summary(_p026_findings(10))
    assert "p012_annotation_triage" not in summary


def test_p012_raw_findings_preserved_in_json() -> None:
    findings = _p012_mixed_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 9
    assert payload["grouped_summary"]["p012_annotation_triage"]["raw_finding_count"] == 9


def test_p012_triage_excludes_private_annotation_content() -> None:
    triage = build_p012_annotation_triage_summary(_p012_mixed_findings())
    assert triage is not None
    triage_blob = json.dumps(triage)
    assert "Private reviewer note" not in triage_blob
    assert "secret comment" not in triage_blob


def test_markdown_report_includes_p012_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "report_p012.md"
    write_markdown_report(_p012_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "R012 Annotation/Comment Triage" in text
    assert "P012 Annotation/Comment Triage" not in text
    assert "Annotation type counts" in text
    triage_pos = text.index("R012 Annotation/Comment Triage")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos
    triage_section = text[triage_pos:findings_pos]
    assert "Text" in triage_section
    assert "Private reviewer note" not in triage_section
    assert "secret comment" not in triage_section


def test_p012_triage_note_distinguishes_from_auditor_highlight() -> None:
    triage = build_p012_annotation_triage_summary(_p012_mixed_findings())
    assert triage is not None
    assert "uploaded PDF" in triage["triage_note"]
    assert "not highlights added by this auditor" in triage["triage_note"]


def test_markdown_p012_triage_section_distinguishes_from_auditor_highlight(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "report_p012_wording.md"
    write_markdown_report(_p012_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    triage_pos = text.index("R012 Annotation/Comment Triage")
    findings_pos = text.index("Findings by Rule")
    triage_section = text[triage_pos:findings_pos]
    assert "uploaded PDF" in triage_section
    assert "not highlights added by this auditor" in triage_section


def test_all_four_triage_rollups_coexist() -> None:
    findings = (
        _p011_mixed_findings()
        + _p012_mixed_findings()
        + _p013_findings(8)
        + _p026_findings(10)
    )
    summary = build_grouped_summary(findings)
    assert "p011_margin_triage" in summary
    assert "p012_annotation_triage" in summary
    assert "p013_triage" in summary
    assert "p026_font_triage" in summary


# ---- audit_findings_to_json_dict tests (existing + new) ----


def test_audit_findings_to_json_dict_has_summary_counts() -> None:
    payload = audit_findings_to_json_dict(_sample_findings(), _metadata())
    assert payload["metadata"]["total_findings"] == 3
    assert payload["metadata"]["counts_by_severity"]["WARNING"] == 3
    assert payload["metadata"]["counts_by_rule_id"]["P011"] == 1
    assert payload["metadata"]["counts_by_category"]["margin_or_overflow"] == 1


def test_json_dict_includes_grouped_summary() -> None:
    payload = audit_findings_to_json_dict(_p026_findings(10), _metadata())
    assert "grouped_summary" in payload
    assert "high_volume_rules" in payload["grouped_summary"]


def test_json_dict_includes_grouped_findings() -> None:
    payload = audit_findings_to_json_dict(_repeated_margin_findings([3, 4, 5]), _metadata())
    assert "grouped_findings" in payload
    assert len(payload["grouped_findings"]) == 1
    assert payload["grouped_findings"][0]["occurrence_count"] == 3
    assert payload["grouped_findings"][0]["page_ranges"] == ["3–5"]


def test_json_dict_raw_findings_preserved_with_grouped_summary() -> None:
    findings = _p026_findings(10)
    payload = audit_findings_to_json_dict(findings, _metadata())
    # Raw findings still present and count is correct.
    assert len(payload["findings"]) == 10
    assert all(f["rule_id"] == "P026" for f in payload["findings"])
    # AND grouped summary also present.
    assert payload["grouped_summary"]["high_volume_rules"][0]["count"] == 10
    assert sum(entry["occurrence_count"] for entry in payload["grouped_findings"]) == 10


def test_long_preview_is_truncated() -> None:
    long_text = "X" * 200
    findings = [
        AuditFinding(
            rule_id="P017",
            severity=Severity.WARNING,
            message="Caption issue.",
            details={"line_preview": long_text},
        )
    ]
    payload = audit_findings_to_json_dict(findings, _metadata())
    value = payload["findings"][0]["details"]["line_preview"]
    assert len(value) <= 120


def test_json_export_hides_internal_source_q_details() -> None:
    findings = [
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            message="Abstract paragraph after the first appears not to be indented.",
            page=1,
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "source_q_rule_id": "Q003",
                "source_q_rule_ids": "Q002,Q003",
                "source_q_rule_basis": "internal mapping note",
                "paragraph_index": "1",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, _metadata())
    details = payload["findings"][0]["details"]
    assert "source_q_rule_id" not in details
    assert "source_q_rule_ids" not in details
    assert "source_q_rule_basis" not in details
    assert details["paragraph_index"] == "1"


def _unordered_page_findings() -> list[AuditFinding]:
    """Findings whose input order deliberately does not match page order.

    Mimics real pipeline output: each rule sweeps the whole document before the
    next rule runs, so findings from different rules interleave pages
    non-sequentially (here: 8, 2, 5, None, 2). None of these rule_id/issue_type
    pairs are subject to the P011/P012/P020/P026/P018/page-numbering "first
    occurrence wins" display dedup, so every finding stays individually visible
    and this test can assert order and count without that logic in the way.
    A source_q_rule_id is attached to the first finding to confirm the
    page-reorder does not reintroduce a Q-rule ID leak into the export.
    """
    return [
        AuditFinding(
            rule_id="P014",
            severity=Severity.WARNING,
            page=8,
            message="Heading not centered on page eight.",
            details={"issue_type": "heading_not_centered", "source_q_rule_id": "Q014"},
        ),
        AuditFinding(
            rule_id="P015",
            severity=Severity.WARNING,
            page=2,
            message="Body indentation problem on page two.",
            details={"issue_type": "body_indent_problem"},
        ),
        AuditFinding(
            rule_id="P021",
            severity=Severity.WARNING,
            page=5,
            message="Formatting problem on page five.",
            details={"issue_type": "formatting_problem"},
        ),
        AuditFinding(
            rule_id="P068",
            severity=Severity.WARNING,
            page=None,
            message="Document-wide committee block problem.",
            details={"issue_type": "committee_block_problem"},
        ),
        AuditFinding(
            rule_id="P027",
            severity=Severity.WARNING,
            page=2,
            message="Second problem also on page two.",
            details={"issue_type": "sentence_case_mismatch"},
        ),
    ]


def test_json_export_orders_findings_by_page() -> None:
    findings = _unordered_page_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    serialized = payload["findings"]

    # No finding is dropped or added by the reorder.
    assert len(serialized) == len(findings)
    assert {f["rule_id"] for f in serialized} == {"P014", "P015", "P021", "P068", "P027"}

    # Page-specific findings come first in ascending page order; the one
    # page-less finding (P068) sorts last, not wherever it fell in the input.
    pages = [f["page"] for f in serialized]
    assert pages == [2, 2, 5, 8, None]

    # A stable sort keeps same-page findings in their original relative order
    # (P015 appeared before P027 in the unsorted input, both on page 2).
    rule_order = [f["rule_id"] for f in serialized]
    assert rule_order == ["P015", "P027", "P021", "P014", "P068"]

    # Problem numbers are assigned in the new page order, 1..N, matching the
    # order a student would encounter each issue reading front-to-back.
    problem_numbers = [f["problem_number"] for f in serialized]
    assert problem_numbers == [1, 2, 3, 4, 5]

    # The page-reorder must not reintroduce a source Q-rule ID leak.
    for entry in serialized:
        assert "source_q_rule_id" not in entry["details"]
        assert "Q014" not in json.dumps(entry)


# ---- write_json_report tests ----


def test_json_report_is_written_and_parent_created(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "report.json"
    write_json_report(_sample_findings(), _metadata(), output_path)
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert '"counts_by_rule_id"' in text
    assert '"P011"' in text


def test_json_report_includes_grouped_summary_field(tmp_path: Path) -> None:
    output_path = tmp_path / "report.json"
    write_json_report(_p026_findings(10), _metadata(), output_path)
    data = json.loads(output_path.read_text())
    assert "grouped_summary" in data
    hv = data["grouped_summary"]["high_volume_rules"]
    assert any(e["rule_id"] == "P026" for e in hv)


def test_json_report_raw_findings_not_removed(tmp_path: Path) -> None:
    output_path = tmp_path / "report.json"
    findings = _p026_findings(10)
    write_json_report(findings, _metadata(), output_path)
    data = json.loads(output_path.read_text())
    assert len(data["findings"]) == 10


# ---- write_markdown_report tests ----


def test_markdown_problems_section_orders_findings_by_page(tmp_path: Path) -> None:
    """The primary "## Problems" list must read in page order, not detection order.

    Regression test for the report-download page-ordering fix: before it, this
    section listed findings in raw per-rule detection order (see
    _findings_sorted_for_export), so a student reading the downloaded report
    front-to-back would encounter problems jumping backward across pages.
    """
    output_path = tmp_path / "report.md"
    findings = _unordered_page_findings()
    write_markdown_report(findings, _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")

    problems_start = text.index("## Problems")
    findings_by_rule_start = text.index("## Findings by Rule")
    problems_section = text[problems_start:findings_by_rule_start]

    headings = re.findall(r"^### Problem (\d+) — (.+)$", problems_section, re.MULTILINE)
    # No finding is dropped: exactly one "### Problem N" heading per input finding.
    assert len(headings) == len(findings)
    assert [int(number) for number, _ in headings] == [1, 2, 3, 4, 5]

    # Rule IDs appear in the same page order asserted against the JSON export:
    # page 2, 2, 5, 8, then the page-less finding last.
    rule_id_order = []
    for number, _ in headings:
        block = problems_section[problems_section.index(f"### Problem {number} —") :]
        # The rendered Markdown shows the student-facing Rxxx form, not the
        # internal Pxxx id (see public_display_rule_id).
        match = re.search(r"- Rule: `(R\d+)`", block)
        assert match is not None
        rule_id_order.append(match.group(1))
    assert rule_id_order == ["R015", "R027", "R021", "R014", "R068"]

    # A source Q-rule ID attached to one finding must not leak into the
    # student-facing markdown export.
    assert "source_q_rule_id" not in text
    assert "Q014" not in text


def test_markdown_report_is_written_and_parent_created(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "report.md"
    write_markdown_report(_sample_findings(), _metadata(), output_path)
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert "# NJIT PDF Audit Report" in text
    assert "## Summary" in text
    assert "### R011" in text
    assert "### R013" in text
    assert "### R014" in text
    assert "### P011" not in text
    assert "### P013" not in text
    assert "### P014" not in text


def test_markdown_report_includes_grouped_summary_section(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(_p026_findings(10), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "Repeated Findings Summary" in text
    assert "R026" in text
    assert "P026" not in text


def test_markdown_report_grouped_summary_before_findings_by_rule(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(_p026_findings(10), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    summary_pos = text.index("Repeated Findings Summary")
    grouped_pos = text.index("Advanced grouped summaries")
    findings_pos = text.index("Findings by Rule")
    assert summary_pos < findings_pos
    assert grouped_pos < findings_pos


def test_markdown_report_low_volume_repeats_skip_high_volume_summary_only(tmp_path: Path) -> None:
    # Only 3 findings — below HIGH_VOLUME_THRESHOLD (5), but still a repeated problem.
    output_path = tmp_path / "report_low.md"
    write_markdown_report(_p026_findings(3), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "Repeated Findings Summary" not in text
    assert "Advanced grouped summaries" in text


# ---- "## Advanced grouped summaries" student-facing wording (no raw confidence/triage labels) ----


def _repeated_synthetic_findings(
    *, confidence: str = "medium", count: int = 2
) -> list[AuditFinding]:
    """Two+ findings sharing a grouping key, using a rule id with no curated
    explanation so build_polished_comment() exercises its generic fallback.
    """
    return [
        AuditFinding(
            rule_id="P099",
            severity=Severity.WARNING,
            page=page,
            message="Synthetic formatting issue.",
            details={
                "issue_type": "possible_synthetic_marker_issue",
                "suggested_fix": "Re-check this item against the NJIT format requirements.",
                "confidence": confidence,
                "triage_tier": "check",
            },
        )
        for page in range(1, count + 1)
    ]


def test_markdown_grouped_section_never_shows_raw_confidence_or_triage_labels(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(_repeated_synthetic_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "Confidence:" not in text
    assert "Triage tier:" not in text
    assert "Triage Tier:" not in text
    assert "conf:" not in text
    assert "review priority:" not in text.lower()


def test_markdown_grouped_section_keeps_useful_problem_info(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(_repeated_synthetic_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "### R099" in text
    assert "### P099" not in text
    assert "2 occurrences" in text
    assert "Issue type: Possible synthetic marker issue" in text
    assert "Suggested fix: Re-check this item against the NJIT format requirements." in text


def test_markdown_grouped_section_adds_manual_check_hint_for_non_high_confidence(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(
        _repeated_synthetic_findings(confidence="medium"), _metadata(), output_path
    )
    text = output_path.read_text(encoding="utf-8")
    assert STUDENT_LIMITATION_DISCLOSURE in text
    assert "verify this item against the NJIT format requirements" not in text


def test_markdown_grouped_section_omits_manual_check_hint_for_high_confidence(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(
        _repeated_synthetic_findings(confidence="high"), _metadata(), output_path
    )
    text = output_path.read_text(encoding="utf-8")
    assert STUDENT_LIMITATION_DISCLOSURE in text
    assert "verify this item against the NJIT format requirements" not in text


def test_grouped_findings_key_unaffected_by_wording_change(tmp_path: Path) -> None:
    """The Markdown wording fix must not change which findings collapse together."""
    findings = _repeated_synthetic_findings(count=3)
    grouped = build_grouped_findings(findings, "pdf")
    assert len(grouped) == 1
    assert grouped[0]["occurrence_count"] == 3


def _two_repeated_synthetic_groups() -> list[AuditFinding]:
    """Two distinct repeated-problem groups, each with its own suggested fix.

    Regression coverage for a bug where the Markdown grouped-findings loop
    only emitted ``Suggested fix`` for the last group in the list.
    """
    return [
        AuditFinding(
            rule_id="P099",
            severity=Severity.WARNING,
            page=page,
            message="Synthetic formatting issue A.",
            details={
                "issue_type": "synthetic_first_issue",
                "suggested_fix": "Fix the first synthetic issue.",
                "confidence": "medium",
                "triage_tier": "check",
            },
        )
        for page in (1, 2)
    ] + [
        AuditFinding(
            rule_id="P098",
            severity=Severity.WARNING,
            page=page,
            message="Synthetic formatting issue B.",
            details={
                "issue_type": "synthetic_second_issue",
                "suggested_fix": "Fix the second synthetic issue.",
                "confidence": "medium",
                "triage_tier": "check",
            },
        )
        for page in (3, 4)
    ]


def test_markdown_grouped_section_shows_suggested_fix_for_every_group(
    tmp_path: Path,
) -> None:
    """Every repeated-problem group must keep its own Suggested fix line.

    Previously, an indentation bug moved the ``Suggested fix`` append outside
    the per-group loop, so only the last group in ``repeated_groups`` ever
    showed a fix and earlier groups silently lost theirs.
    """
    output_path = tmp_path / "report.md"
    write_markdown_report(_two_repeated_synthetic_groups(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    section_start = text.index("## Advanced grouped summaries")
    section_end = text.index("\n## ", section_start + len("## Advanced grouped summaries"))
    grouped_section = text[section_start:section_end]

    first_heading = grouped_section.index("### R099")
    second_heading = grouped_section.index("### R098")
    assert first_heading < second_heading

    first_block = grouped_section[first_heading:second_heading]
    second_block = grouped_section[second_heading:]

    assert "Suggested fix: Fix the first synthetic issue." in first_block
    assert "Suggested fix: Fix the second synthetic issue." in second_block
    # Each group's fix must stay scoped to its own heading, not bleed into
    # the other group's block.
    assert "Suggested fix: Fix the second synthetic issue." not in first_block
    assert "Suggested fix: Fix the first synthetic issue." not in second_block
    # Headings must be separated by a blank line, not run together.
    assert "\n\n### R098" in grouped_section


def test_markdown_grouped_section_does_not_expose_blocked_detail_text(tmp_path: Path) -> None:
    forbidden = "an unforgettable confidential dissertation phrase"
    findings = [
        AuditFinding(
            rule_id="P099",
            severity=Severity.WARNING,
            page=page,
            message="Synthetic formatting issue.",
            details={
                "issue_type": "possible_synthetic_marker_issue",
                "suggested_fix": "Re-check this item against the NJIT format requirements.",
                "confidence": "medium",
                "triage_tier": "check",
                "heading_text": forbidden,
                "observed_summary": forbidden,
            },
        )
        for page in (1, 2)
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert forbidden not in text
    assert "/home/" not in text
    assert "Traceback" not in text
    assert "\\begin" not in text


def test_markdown_report_p020_and_p036_individual_clarity_unaffected_by_grouped_wording_fix(
    tmp_path: Path,
) -> None:
    """Per-occurrence P020/P036 word-level clarity (added separately) must keep working
    alongside the reworded "## Advanced grouped summaries" section."""
    findings = [
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=7,
            message="Title case issue.",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "source": "heading",
                "expected_or_reason": "major_word_requires_capital",
                "confidence": "medium",
                "flagged_word": "example",
                "corrected_word": "Example",
            },
        ),
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=7,
            message="Title case issue.",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "source": "heading",
                "expected_or_reason": "major_word_requires_capital",
                "confidence": "medium",
                "flagged_word": "another",
                "corrected_word": "Another",
            },
        ),
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "Confidence:" not in text
    assert "Triage tier:" not in text
    problem_lines = [line for line in text.splitlines() if line.startswith("- **Problem")]
    assert len(problem_lines) >= 2
    assert "'example'" in problem_lines[0]
    assert "'another'" in problem_lines[1]


# ---- P019 triage helpers ----


def _p019_finding(issue_type: str, page: int | None = 5) -> AuditFinding:
    triage_details: dict[str, str] = {
        "sequence_gap": {
            "issue_type": "sequence_gap",
            "triage_tier": "high",
            "p019_triage_category": "high_signal_sequence_gap",
            "triage_reason": "numeric page sequence gap; manual review recommended",
        },
        "missing_page_number": {
            "issue_type": "missing_page_number",
            "triage_tier": "high",
            "p019_triage_category": "high_signal_missing_page_number",
            "triage_reason": "expected page number missing; manual review recommended",
        },
        "mixed_numbering_style": {
            "issue_type": "mixed_numbering_style",
            "triage_tier": "medium",
            "p019_triage_category": "mixed_numbering_manual_review",
            "triage_reason": (
                "mixed Roman/Arabic style; boundary detection not available; "
                "manual review recommended"
            ),
        },
        "multiple_page_numbers": {
            "issue_type": "multiple_page_numbers",
            "triage_tier": "medium",
            "p019_triage_category": "multiple_page_numbers_manual_review",
            "triage_reason": (
                "multiple page-number candidates detected; "
                "may be real or artifact-driven"
            ),
        },
        "inconsistent_position": {
            "issue_type": "inconsistent_position",
            "triage_tier": "low",
            "p019_triage_category": "position_inconsistency_artifact_suspected",
            "triage_reason": (
                "page-number position inconsistency is often artifact-driven; "
                "manual spot check recommended"
            ),
        },
    }[issue_type]
    return AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=page,
        message=f"P019 test finding: {issue_type}",
        details=triage_details,
    )


def _p019_mixed_findings() -> list[AuditFinding]:
    return [
        _p019_finding("sequence_gap", page=10),
        _p019_finding("missing_page_number", page=20),
        _p019_finding("mixed_numbering_style", page=30),
        _p019_finding("multiple_page_numbers", page=40),
        _p019_finding("inconsistent_position", page=50),
    ]


def _p036_mixed_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=1,
            message="TOC entry spacing too tight.",
            details={
                "issue_type": "toc_inter_entry_spacing_too_tight",
                "section_type": "table_of_contents",
                "gap_ratio": "0.10",
                "triage_tier": "high",
            },
        ),
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=2,
            message="TOC entry spacing too tight.",
            details={
                "issue_type": "toc_inter_entry_spacing_too_tight",
                "section_type": "table_of_contents",
                "gap_ratio": "0.30",
                "triage_tier": "medium",
            },
        ),
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=4,
            message="LoT entry spacing too tight.",
            details={
                "issue_type": "lot_inter_entry_spacing_too_tight",
                "section_type": "list_of_tables",
                "gap_ratio": "0.60",
                "triage_tier": "medium",
            },
        ),
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=5,
            message="LoF entry spacing too tight.",
            details={
                "issue_type": "lof_inter_entry_spacing_too_tight",
                "section_type": "list_of_figures",
                "gap_ratio": "0.90",
                "triage_tier": "low",
            },
        ),
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=6,
            message="LoF entry spacing too tight.",
            details={
                "issue_type": "lof_inter_entry_spacing_too_tight",
                "section_type": "list_of_figures",
                "gap_ratio": "oops",
                "triage_tier": "high",
            },
        ),
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=7,
            message="TOC entry spacing too tight.",
            details={
                "issue_type": "toc_inter_entry_spacing_too_tight",
                "gap_ratio": "1.20",
                "triage_tier": "low",
            },
        ),
    ]


def _p038_mixed_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            page=None,
            message="Required front-matter heading 'APPROVAL PAGE' not detected.",
            details={
                "issue_type": "required_heading_missing",
                "section_key": "approval_page",
                "expected_heading": "APPROVAL PAGE",
                "triage_tier": "check",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            page=None,
            message="Required front-matter heading 'BIOGRAPHICAL SKETCH' not detected.",
            details={
                "issue_type": "required_heading_missing",
                "section_key": "biographical_sketch",
                "expected_heading": "BIOGRAPHICAL SKETCH",
                "triage_tier": "check",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            page=None,
            message="Required front-matter heading 'ACKNOWLEDGEMENTS' not detected.",
            details={
                "issue_type": "required_heading_missing",
                "section_key": "acknowledgements",
                "expected_heading": "ACKNOWLEDGEMENTS",
                "triage_tier": "check",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            page=3,
            message=(
                "Front-matter heading uses variant 'ACKNOWLEDGMENTS'; "
                "expected canonical 'ACKNOWLEDGEMENTS'."
            ),
            details={
                "issue_type": "heading_phrase_not_exact",
                "section_key": "acknowledgements",
                "expected_heading": "ACKNOWLEDGEMENTS",
                "observed_heading_normalized": "ACKNOWLEDGMENTS",
                "triage_tier": "check",
                "confidence": "medium",
            },
        ),
    ]


# ---- P019 triage summary tests ----


def test_p019_triage_absent_when_no_findings() -> None:
    result = build_p019_page_numbering_triage_summary([])
    assert result is None


def test_p019_triage_absent_when_no_p019_findings() -> None:
    result = build_p019_page_numbering_triage_summary(_p026_findings(3))
    assert result is None


def test_p019_sequence_gap_is_high_priority() -> None:
    findings = [_p019_finding("sequence_gap")]
    result = build_p019_page_numbering_triage_summary(findings)
    assert result is not None
    assert result["high_priority_count"] == 1
    assert result["by_triage_tier"].get("high") == 1
    assert result["by_category"].get("high_signal_sequence_gap") == 1


def test_p019_missing_page_number_is_high_priority() -> None:
    findings = [_p019_finding("missing_page_number")]
    result = build_p019_page_numbering_triage_summary(findings)
    assert result is not None
    assert result["high_priority_count"] == 1
    assert result["by_category"].get("high_signal_missing_page_number") == 1


def test_p019_multiple_page_numbers_is_medium_priority() -> None:
    findings = [_p019_finding("multiple_page_numbers")]
    result = build_p019_page_numbering_triage_summary(findings)
    assert result is not None
    assert result["medium_priority_count"] == 1
    assert result["by_category"].get("multiple_page_numbers_manual_review") == 1


def test_p019_inconsistent_position_is_low_priority() -> None:
    findings = [_p019_finding("inconsistent_position")]
    result = build_p019_page_numbering_triage_summary(findings)
    assert result is not None
    assert result["low_priority_count"] == 1
    assert result["by_category"].get("position_inconsistency_artifact_suspected") == 1


def test_p019_triage_groups_counts_correctly() -> None:
    findings = _p019_mixed_findings()
    result = build_p019_page_numbering_triage_summary(findings)
    assert result is not None
    assert result["total_findings"] == 5
    assert result["high_priority_count"] == 2
    assert result["medium_priority_count"] == 2
    assert result["low_priority_count"] == 1
    assert result["by_issue_type"]["sequence_gap"] == 1
    assert result["by_issue_type"]["inconsistent_position"] == 1


def test_p019_triage_in_grouped_summary() -> None:
    findings = _p019_mixed_findings()
    summary = build_grouped_summary(findings)
    assert "p019_page_numbering_triage" in summary
    triage = summary["p019_page_numbering_triage"]
    assert triage["total_findings"] == 5


def test_p019_triage_absent_in_grouped_summary_when_no_p019() -> None:
    summary = build_grouped_summary(_p026_findings(5))
    assert "p019_page_numbering_triage" not in summary


def test_p019_raw_findings_preserved_in_json() -> None:
    findings = _p019_mixed_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 5
    assert all(f["rule_id"] == "P019" for f in payload["findings"])
    assert "p019_page_numbering_triage" in payload["grouped_summary"]


def test_markdown_report_includes_p019_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "p019_report.md"
    write_markdown_report(_p019_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "R019 Page-Numbering Triage Summary" in text
    assert "P019 Page-Numbering Triage Summary" not in text
    assert "Check first" in text
    assert "Review carefully" in text
    assert "Spot check" in text
    assert "High-priority" not in text
    assert "Medium-priority" not in text
    assert "Low-priority" not in text
    assert "Triage tier counts" not in text
    assert "review priority" not in text.lower()
    assert "Findings by Rule" in text


def test_p019_triage_section_absent_when_no_p019(tmp_path: Path) -> None:
    output_path = tmp_path / "no_p019_report.md"
    write_markdown_report(_p026_findings(5), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "P019 Page-Numbering Triage Summary" not in text


def test_p036_triage_absent_when_no_findings() -> None:
    assert build_p036_toc_list_spacing_triage_summary([]) is None


def test_p036_triage_absent_when_no_p036_findings() -> None:
    assert build_p036_toc_list_spacing_triage_summary(_p026_findings(5)) is None
    summary = build_grouped_summary(_p026_findings(5))
    assert "p036_toc_list_spacing_triage" not in summary


def test_p036_triage_in_grouped_summary() -> None:
    summary = build_grouped_summary(_p036_mixed_findings())
    assert "p036_toc_list_spacing_triage" in summary
    assert summary["p036_toc_list_spacing_triage"]["raw_finding_count"] == 6


def test_p036_triage_issue_type_counts() -> None:
    triage = build_p036_toc_list_spacing_triage_summary(_p036_mixed_findings())
    assert triage is not None
    assert triage["issue_type_counts"]["toc_inter_entry_spacing_too_tight"] == 3
    assert triage["issue_type_counts"]["lot_inter_entry_spacing_too_tight"] == 1
    assert triage["issue_type_counts"]["lof_inter_entry_spacing_too_tight"] == 2


def test_p036_triage_section_type_counts() -> None:
    triage = build_p036_toc_list_spacing_triage_summary(_p036_mixed_findings())
    assert triage is not None
    assert triage["section_type_counts"]["table_of_contents"] == 2
    assert triage["section_type_counts"]["list_of_tables"] == 1
    assert triage["section_type_counts"]["list_of_figures"] == 2
    assert triage["section_type_counts"]["toc"] == 1


def test_p036_triage_section_page_ranges_compact() -> None:
    triage = build_p036_toc_list_spacing_triage_summary(_p036_mixed_findings())
    assert triage is not None
    assert triage["section_page_ranges"]["table_of_contents"] == "1-2"
    assert triage["section_page_ranges"]["list_of_tables"] == "4"
    assert triage["section_page_ranges"]["list_of_figures"] == "5-6"
    assert triage["section_page_ranges"]["toc"] == "7"


def test_p036_triage_tier_counts() -> None:
    triage = build_p036_toc_list_spacing_triage_summary(_p036_mixed_findings())
    assert triage is not None
    assert triage["triage_tier_counts"]["high"] == 2
    assert triage["triage_tier_counts"]["medium"] == 2
    assert triage["triage_tier_counts"]["low"] == 2


def test_p036_triage_gap_ratio_buckets() -> None:
    triage = build_p036_toc_list_spacing_triage_summary(_p036_mixed_findings())
    assert triage is not None
    assert triage["spacing_gap_bucket_counts"]["very_tight"] == 1
    assert triage["spacing_gap_bucket_counts"]["tight"] == 1
    assert triage["spacing_gap_bucket_counts"]["moderately_tight"] == 1
    assert triage["spacing_gap_bucket_counts"]["slightly_tight"] == 1
    assert triage["spacing_gap_bucket_counts"]["unexpected_non_tight"] == 1


def test_p036_triage_ignores_invalid_gap_ratio() -> None:
    triage = build_p036_toc_list_spacing_triage_summary(_p036_mixed_findings())
    assert triage is not None
    assert triage["min_gap_ratio"] == 0.1
    assert triage["max_gap_ratio"] == 1.2
    assert sum(triage["spacing_gap_bucket_counts"].values()) == 5


def test_markdown_report_includes_p036_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "p036_report.md"
    write_markdown_report(_p036_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "R036 TOC/List Spacing Triage" in text
    assert "P036 TOC/List Spacing Triage" not in text
    assert "Spacing gap bucket counts" in text
    assert "Triage tier counts" not in text
    assert "Raw per-page R036 findings are listed under **Findings by Rule → R036** below." in text
    assert "P036" not in text
    triage_pos = text.index("R036 TOC/List Spacing Triage")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos


def test_p036_raw_findings_preserved_in_json() -> None:
    findings = _p036_mixed_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 6
    assert all(f["rule_id"] == "P036" for f in payload["findings"])
    assert payload["grouped_summary"]["p036_toc_list_spacing_triage"]["raw_finding_count"] == 6


def test_all_six_triage_rollups_coexist() -> None:
    findings = (
        _p011_mixed_findings()
        + _p012_mixed_findings()
        + _p013_findings(8)
        + _p026_findings(10)
        + _p019_mixed_findings()
        + _p036_mixed_findings()
    )
    summary = build_grouped_summary(findings)
    assert "p011_margin_triage" in summary
    assert "p012_annotation_triage" in summary
    assert "p013_triage" in summary
    assert "p026_font_triage" in summary
    assert "p019_page_numbering_triage" in summary
    assert "p036_toc_list_spacing_triage" in summary


# ---- P038 frontmatter heading triage tests ----


def test_p038_triage_absent_when_no_findings() -> None:
    assert build_p038_frontmatter_heading_triage_summary([]) is None


def test_p038_triage_absent_when_no_p038_findings() -> None:
    assert build_p038_frontmatter_heading_triage_summary(_p026_findings(5)) is None
    summary = build_grouped_summary(_p026_findings(5))
    assert "p038_frontmatter_heading_triage" not in summary


def test_p038_triage_in_grouped_summary() -> None:
    summary = build_grouped_summary(_p038_mixed_findings())
    assert "p038_frontmatter_heading_triage" in summary
    assert summary["p038_frontmatter_heading_triage"]["raw_finding_count"] == 4


def test_p038_triage_issue_type_counts() -> None:
    triage = build_p038_frontmatter_heading_triage_summary(_p038_mixed_findings())
    assert triage is not None
    assert triage["issue_type_counts"]["required_heading_missing"] == 3
    assert triage["issue_type_counts"]["heading_phrase_not_exact"] == 1


def test_p038_triage_expected_heading_counts() -> None:
    triage = build_p038_frontmatter_heading_triage_summary(_p038_mixed_findings())
    assert triage is not None
    assert triage["expected_heading_counts"]["ACKNOWLEDGEMENTS"] == 2
    assert triage["expected_heading_counts"]["APPROVAL PAGE"] == 1
    assert triage["expected_heading_counts"]["BIOGRAPHICAL SKETCH"] == 1


def test_p038_triage_missing_heading_counts() -> None:
    triage = build_p038_frontmatter_heading_triage_summary(_p038_mixed_findings())
    assert triage is not None
    assert triage["missing_heading_counts"]["APPROVAL PAGE"] == 1
    assert triage["missing_heading_counts"]["BIOGRAPHICAL SKETCH"] == 1
    assert triage["missing_heading_counts"]["ACKNOWLEDGEMENTS"] == 1


def test_p038_triage_inexact_phrase_counts() -> None:
    triage = build_p038_frontmatter_heading_triage_summary(_p038_mixed_findings())
    assert triage is not None
    assert triage["inexact_phrase_counts"]["ACKNOWLEDGEMENTS"] == 1


def test_p038_triage_affected_pages() -> None:
    triage = build_p038_frontmatter_heading_triage_summary(_p038_mixed_findings())
    assert triage is not None
    # required_heading_missing findings have page=None; only the phrase-not-exact
    # finding (page=3) contributes to the page set.
    assert triage["affected_page_count"] == 1
    assert triage["affected_pages_compact"] == "3"


def test_p038_triage_tier_and_confidence_counts() -> None:
    triage = build_p038_frontmatter_heading_triage_summary(_p038_mixed_findings())
    assert triage is not None
    assert triage["triage_tier_counts"]["check"] == 4
    assert triage["confidence_counts"]["medium"] == 4


def test_markdown_report_includes_p038_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "p038_report.md"
    write_markdown_report(_p038_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "R038 Front-Matter Heading Triage" in text
    assert "P038 Front-Matter Heading Triage" not in text
    assert "Missing heading counts" in text
    assert "Triage tier counts" not in text
    assert (
        "Raw per-page R038 findings are listed under **Findings by Rule → R038** below."
        in text
    )
    assert "P038" not in text
    triage_pos = text.index("R038 Front-Matter Heading Triage")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos


def test_p038_raw_findings_preserved_in_json() -> None:
    findings = _p038_mixed_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 4
    assert all(f["rule_id"] == "P038" for f in payload["findings"])
    assert payload["grouped_summary"]["p038_frontmatter_heading_triage"]["raw_finding_count"] == 4


def test_all_seven_triage_rollups_coexist() -> None:
    findings = (
        _p011_mixed_findings()
        + _p012_mixed_findings()
        + _p013_findings(8)
        + _p026_findings(10)
        + _p019_mixed_findings()
        + _p036_mixed_findings()
        + _p038_mixed_findings()
    )
    summary = build_grouped_summary(findings)
    assert "p011_margin_triage" in summary
    assert "p012_annotation_triage" in summary
    assert "p013_triage" in summary
    assert "p026_font_triage" in summary
    assert "p019_page_numbering_triage" in summary
    assert "p036_toc_list_spacing_triage" in summary
    assert "p038_frontmatter_heading_triage" in summary


# ---- P044 abstract indentation triage tests ----


def _p044_mixed_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=1,
            message="First Abstract paragraph is indented.",
            details={
                "issue_type": "abstract_first_paragraph_indented",
                "paragraph_index": "0",
                "observed_x0": "130.4",
                "expected_left_margin": "108.4",
                "indent_delta_points": "22.0",
                "required_indent_points": "0.0",
                "triage_tier": "medium",
                "source_q_rule_id": "Q002",
            },
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=1,
            message="Subsequent Abstract paragraph is not indented.",
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "paragraph_index": "1",
                "observed_x0": "108.4",
                "expected_left_margin": "108.4",
                "indent_delta_points": "0.0",
                "required_indent_points": "18.0",
                "triage_tier": "medium",
                "source_q_rule_id": "Q003",
            },
        ),
        AuditFinding(
            rule_id="P044",
            severity=Severity.WARNING,
            page=2,
            message="Subsequent Abstract paragraph is not indented.",
            details={
                "issue_type": "abstract_subsequent_paragraph_not_indented",
                "paragraph_index": "2",
                "observed_x0": "108.4",
                "expected_left_margin": "108.4",
                "indent_delta_points": "0.0",
                "required_indent_points": "18.0",
                "triage_tier": "medium",
                "source_q_rule_id": "Q003",
            },
        ),
    ]


def test_p044_triage_absent_when_no_findings() -> None:
    assert build_p044_abstract_indentation_triage_summary([]) is None


def test_p044_triage_absent_when_no_p044_findings() -> None:
    assert build_p044_abstract_indentation_triage_summary(_p026_findings(5)) is None
    summary = build_grouped_summary(_p026_findings(5))
    assert "p044_abstract_indentation_triage" not in summary


def test_p044_triage_in_grouped_summary() -> None:
    summary = build_grouped_summary(_p044_mixed_findings())
    assert "p044_abstract_indentation_triage" in summary
    assert summary["p044_abstract_indentation_triage"]["raw_finding_count"] == 3


def test_p044_triage_issue_type_counts() -> None:
    triage = build_p044_abstract_indentation_triage_summary(_p044_mixed_findings())
    assert triage is not None
    assert triage["issue_type_counts"]["abstract_first_paragraph_indented"] == 1
    assert triage["issue_type_counts"]["abstract_subsequent_paragraph_not_indented"] == 2


def test_p044_triage_excludes_source_q_rule_counts() -> None:
    triage = build_p044_abstract_indentation_triage_summary(_p044_mixed_findings())
    assert triage is not None
    assert "source_q_rule_counts" not in triage


def test_p044_triage_paragraph_index_counts() -> None:
    triage = build_p044_abstract_indentation_triage_summary(_p044_mixed_findings())
    assert triage is not None
    assert triage["paragraph_index_counts"]["0"] == 1
    assert triage["paragraph_index_counts"]["1"] == 1
    assert triage["paragraph_index_counts"]["2"] == 1


def test_markdown_report_includes_p044_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "p044_report.md"
    write_markdown_report(_p044_mixed_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "## R044 Abstract Indentation Triage" in text
    assert "P044 Abstract Indentation Triage" not in text
    assert "Source Q-rule counts" not in text
    assert "Q002" not in text
    assert "Q003" not in text
    assert "Triage tier counts" not in text
    assert (
        "Raw per-page R044 findings are listed under **Findings by Rule → R044** below."
        in text
    )
    assert "P044" not in text
    triage_pos = text.index("R044 Abstract Indentation Triage")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos


def test_p044_raw_findings_preserved_in_json() -> None:
    findings = _p044_mixed_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    assert len(payload["findings"]) == 3
    assert all(f["rule_id"] == "P044" for f in payload["findings"])
    raw_count = payload["grouped_summary"]["p044_abstract_indentation_triage"]
    assert raw_count["raw_finding_count"] == 3


def test_all_eight_triage_rollups_coexist() -> None:
    findings = (
        _p011_mixed_findings()
        + _p012_mixed_findings()
        + _p013_findings(8)
        + _p026_findings(10)
        + _p019_mixed_findings()
        + _p036_mixed_findings()
        + _p038_mixed_findings()
        + _p044_mixed_findings()
    )
    summary = build_grouped_summary(findings)
    assert "p011_margin_triage" in summary
    assert "p012_annotation_triage" in summary
    assert "p013_triage" in summary
    assert "p026_font_triage" in summary
    assert "p019_page_numbering_triage" in summary
    assert "p036_toc_list_spacing_triage" in summary
    assert "p038_frontmatter_heading_triage" in summary
    assert "p044_abstract_indentation_triage" in summary


# ---------------------------------------------------------------------------
# P024: TOC/List entry location clarity (entry_index-based location labels)
# ---------------------------------------------------------------------------

_P024_LINE_PREVIEW_SECRET = "Synthetic Sample Toc Entry Text Marker XYZ123"


def _p024_finding(
    *, page: int, issue_type: str, entry_index: str | None, **extra: str
) -> AuditFinding:
    details: dict[str, str] = {
        "page_type": "table_of_contents",
        "issue_type": issue_type,
        "confidence": "medium",
        "line_preview": _P024_LINE_PREVIEW_SECRET,
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


def _p024_same_page_findings() -> list[AuditFinding]:
    return [
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


def test_markdown_p024_same_page_findings_get_distinct_entry_locations(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "p024_report.md"
    write_markdown_report(_p024_same_page_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert (
        "Page 12 — Table of Contents, affected entry: "
        "'Synthetic first toc entry marker ABC'"
    ) in text
    assert (
        "Page 12 — Table of Contents, affected entry: "
        "'Synthetic third toc entry marker DEF'"
    ) in text


def test_markdown_p024_never_renders_raw_line_preview_in_problem_text(tmp_path: Path) -> None:
    output_path = tmp_path / "p024_report.md"
    write_markdown_report(_p024_same_page_findings(), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    problem_lines = [
        line for line in text.splitlines() if line.startswith("- **Problem")
    ]
    assert problem_lines
    for line in problem_lines:
        assert _P024_LINE_PREVIEW_SECRET not in line


def test_markdown_p024_without_entry_index_falls_back_honestly(tmp_path: Path) -> None:
    """Findings without entry_index metadata must not claim a false entry number."""
    finding = _p024_finding(
        page=20,
        issue_type="list_of_tables_title_case",
        entry_index=None,
        page_type="list_of_tables",
        expected_or_reason="first_word_requires_capital",
    )
    output_path = tmp_path / "p024_report.md"
    write_markdown_report([finding], _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "Location: `Page 20 — List of Tables`" in text
    assert "List of Tables entry 1" not in text
    assert _P024_LINE_PREVIEW_SECRET not in text


def test_p024_suggested_fix_and_confidence_remain_visible_with_entry_index(
    tmp_path: Path,
) -> None:
    """Adding entry_index must not remove the suggested-fix line or confidence info."""
    findings = _p024_same_page_findings()
    payload = audit_findings_to_json_dict(findings, _metadata())
    view = build_report_view(payload)
    p024_findings = [f for f in view.findings if f.rule_id == "P024"]
    assert len(p024_findings) == 2
    for f in p024_findings:
        assert f.suggested_fix
        assert f.confidence_level in {"medium"}


def test_public_display_rule_id_maps_pxxx_to_rxxx() -> None:
    """Ester requested Rxxx terminology for students; Pxxx stays the internal
    catalog/test id (see public_display_rule_id's docstring for why a
    repository-wide rename was rejected in favor of a display-boundary map)."""
    assert public_display_rule_id("P019") == "R019"
    assert public_display_rule_id("P001") == "R001"
    assert public_display_rule_id("P028") == "R028"


def test_public_display_rule_id_passes_through_non_pxxx_values() -> None:
    """Anything that is not a plain Pddd id must be returned unchanged rather
    than silently mangled."""
    assert public_display_rule_id("Q019") == "Q019"
    assert public_display_rule_id("") == ""
    assert public_display_rule_id("P19") == "P19"
    assert public_display_rule_id("R019") == "R019"


def test_public_display_rule_id_preserves_atomic_sub_rule_suffix() -> None:
    """Broad parent rules such as P018 are split into lettered atomic
    sub-rules (P018A..P018Q in the current catalog; P024D/E, P032B/C are
    also live) for the public rule-reference page, and a finding can carry
    one of these directly as its rule_id/reference id. The suffix identifies
    a distinct atomic rule -- it must be preserved, never collapsed to the
    parent id, or a student would be pointed at the wrong rule reference."""
    assert public_display_rule_id("P018D") == "R018D"
    assert public_display_rule_id("P018A") == "R018A"
    assert public_display_rule_id("P018Q") == "R018Q"
    assert public_display_rule_id("P024D") == "R024D"
    assert public_display_rule_id("P032C") == "R032C"


def test_public_display_rule_id_rejects_malformed_suffix_shapes() -> None:
    """Only the established grammar (Pddd or PdddX, one trailing uppercase
    letter) converts; anything else passes through unchanged rather than
    being guessed at."""
    assert public_display_rule_id("P018DD") == "P018DD"
    assert public_display_rule_id("P018d") == "P018d"
    assert public_display_rule_id("P0181") == "P0181"
    assert public_display_rule_id("P018-D") == "P018-D"


def test_audit_findings_to_json_dict_carries_public_rule_id_without_renaming_internal() -> None:
    """The exported JSON must expose a student-facing Rxxx id alongside the
    stable internal Pxxx rule_id, not replace it (internal tooling/tests key
    off rule_id, so it must never change)."""
    finding = AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=5,
        message="Multiple plausible page-number candidates detected on one page.",
        details={"issue_type": "multiple_page_numbers"},
    )
    payload = audit_findings_to_json_dict([finding], _metadata())
    entry = payload["findings"][0]
    assert entry["rule_id"] == "P019"
    assert entry["public_rule_id"] == "R019"
    assert payload["metadata"]["counts_by_rule_id"].get("P019") == 1
    assert payload["metadata"]["counts_by_public_rule_id"].get("R019") == 1
    assert "P019" not in payload["metadata"]["counts_by_public_rule_id"]


def test_convert_pxxx_tokens_to_public_display_word_boundary() -> None:
    """The Markdown-text converter must only touch standalone Pddd tokens,
    reusing public_display_rule_id as its single mapping source -- never a
    longer digit run, and never a token that isn't P-prefixed."""
    text = "See P019 and P028. A longer id like P0191 must stay untouched. Q052 is unrelated."
    converted = convert_pxxx_tokens_to_public_display(text)
    assert converted == (
        "See R019 and R028. A longer id like P0191 must stay untouched. Q052 is unrelated."
    )


def test_convert_pxxx_tokens_to_public_display_preserves_atomic_suffix() -> None:
    """A standalone atomic-sub-rule token (e.g. P018D) embedded in free text
    must also convert with its suffix intact, not be left untouched or
    collapsed to the parent id -- the same grammar public_display_rule_id
    itself uses."""
    text = "See P018D for the leader-dot consistency requirement."
    converted = convert_pxxx_tokens_to_public_display(text)
    assert converted == "See R018D for the leader-dot consistency requirement."


def test_markdown_report_representative_multi_rule_converts_all_public_surfaces(
    tmp_path: Path,
) -> None:
    """End-to-end: a report covering several internal Pxxx rules (including
    ones with dedicated triage sections) must show only Rxxx to the reader
    everywhere -- counts, headings, triage sections, findings, and
    cross-references -- while nothing downstream that parses the report by
    key (this test's own construction of the findings, using rule_id="Pxxx")
    is affected.
    """
    findings = (
        _p013_findings(8)
        + _p026_findings(5)
        + _p011_mixed_findings()
        + _p019_mixed_findings()
    )
    output_path = tmp_path / "representative_report.md"
    write_markdown_report(findings, _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")

    # Rxxx present everywhere a rule id is shown to the reader.
    assert "- `R013`:" in text
    assert "- `R026`:" in text
    assert "- `R011`:" in text
    assert "- `R019`:" in text
    assert "### R013" in text
    assert "### R026" in text
    assert "### R011" in text
    assert "### R019" in text
    assert "R013 Page-Number Candidate Inventory" in text
    assert "R026 Body Font Compliance Triage" in text
    assert "R011 Margin/Overflow Triage" in text
    assert "R019 Page-Numbering Triage Summary" in text

    # No raw Pxxx token survives in the rendered report.
    for rule_id in ("P013", "P026", "P011", "P019"):
        assert rule_id not in text, f"found un-mapped internal id {rule_id!r} in student report"

    # The findings used to build this report keep their real internal ids --
    # this test constructed them with rule_id="P013" etc., and nothing in
    # the Markdown pipeline mutates the AuditFinding objects themselves.
    assert {f.rule_id for f in findings} == {"P013", "P026", "P011", "P019"}
