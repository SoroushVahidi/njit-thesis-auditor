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
    build_p026_font_triage_summary,
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
