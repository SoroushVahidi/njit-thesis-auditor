import json
from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import (
    P011_ISSUE_TYPE,
    P012_ISSUE_TYPE,
    P013_DOC_ISSUE_TYPE,
    P013_PAGE_ISSUE_TYPE,
    P026_FAMILY_ISSUE_TYPE,
    P026_SIZE_ISSUE_TYPE,
    audit_findings_to_json_dict,
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
    write_json_report,
    write_markdown_report,
)


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


def test_markdown_report_includes_p013_triage_section(tmp_path: Path) -> None:
    output_path = tmp_path / "report_p013.md"
    write_markdown_report(_p013_findings(8), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "P013 Page-Number Candidate Triage" in text
    assert "bottom_center/arabic" in text
    assert "Issue type counts" in text
    triage_pos = text.index("P013 Page-Number Candidate Triage")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos


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
    assert "P026 Body Font Compliance Triage" in text
    assert "CMR12" in text
    assert "Issue type counts" in text
    triage_pos = text.index("P026 Body Font Compliance Triage")
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
    assert "P011 Margin/Overflow Triage" in text
    assert "left_margin" in text
    assert "Overflow distance by side" in text
    triage_pos = text.index("P011 Margin/Overflow Triage")
    p013_pos = text.find("P013 Page-Number Candidate Triage")
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
    assert "P012 Annotation/Comment Triage" in text
    assert "Annotation type counts" in text
    triage_pos = text.index("P012 Annotation/Comment Triage")
    findings_pos = text.index("Findings by Rule")
    assert triage_pos < findings_pos
    triage_section = text[triage_pos:findings_pos]
    assert "Text" in triage_section
    assert "Private reviewer note" not in triage_section
    assert "secret comment" not in triage_section


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


def test_json_dict_raw_findings_preserved_with_grouped_summary() -> None:
    findings = _p026_findings(10)
    payload = audit_findings_to_json_dict(findings, _metadata())
    # Raw findings still present and count is correct.
    assert len(payload["findings"]) == 10
    assert all(f["rule_id"] == "P026" for f in payload["findings"])
    # AND grouped summary also present.
    assert payload["grouped_summary"]["high_volume_rules"][0]["count"] == 10


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


def test_markdown_report_is_written_and_parent_created(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "report.md"
    write_markdown_report(_sample_findings(), _metadata(), output_path)
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert "# NJIT PDF Audit Report" in text
    assert "## Summary" in text
    assert "### P011" in text
    assert "### P013" in text
    assert "### P014" in text


def test_markdown_report_includes_grouped_summary_section(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(_p026_findings(10), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "Repeated Findings Summary" in text
    assert "P026" in text


def test_markdown_report_grouped_summary_before_findings_by_rule(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(_p026_findings(10), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    summary_pos = text.index("Repeated Findings Summary")
    findings_pos = text.index("Findings by Rule")
    assert summary_pos < findings_pos


def test_markdown_report_no_grouped_section_when_all_low_volume(tmp_path: Path) -> None:
    # Only 3 findings per rule — below HIGH_VOLUME_THRESHOLD (5)
    output_path = tmp_path / "report_low.md"
    write_markdown_report(_p026_findings(3), _metadata(), output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "Repeated Findings Summary" not in text


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
    assert "P019 Page-Numbering Triage Summary" in text
    assert "High-priority" in text
    assert "Medium-priority" in text
    assert "Low-priority" in text
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
    assert "P036 TOC/List Spacing Triage" in text
    assert "Spacing gap bucket counts" in text
    assert "Raw per-page P036 findings are listed under **Findings by Rule → P036** below." in text
    triage_pos = text.index("P036 TOC/List Spacing Triage")
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
    assert "P038 Front-Matter Heading Triage" in text
    assert "Missing heading counts" in text
    assert (
        "Raw per-page P038 findings are listed under **Findings by Rule → P038** below."
        in text
    )
    triage_pos = text.index("P038 Front-Matter Heading Triage")
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


def test_p044_triage_source_q_rule_counts() -> None:
    triage = build_p044_abstract_indentation_triage_summary(_p044_mixed_findings())
    assert triage is not None
    assert triage["source_q_rule_counts"]["Q002"] == 1
    assert triage["source_q_rule_counts"]["Q003"] == 2


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
    assert "## P044 Abstract Indentation Triage" in text
    assert "Source Q-rule counts" in text
    assert (
        "Raw per-page P044 findings are listed under **Findings by Rule → P044** below."
        in text
    )
    triage_pos = text.index("P044 Abstract Indentation Triage")
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
