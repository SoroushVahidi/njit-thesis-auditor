import json
from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import (
    audit_findings_to_json_dict,
    build_grouped_summary,
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


def _p013_findings(count: int = 8) -> list[AuditFinding]:
    """Synthetic P013 candidate findings."""
    findings: list[AuditFinding] = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            message="Detected possible page-number candidates.",
            details={"candidate_count": str(count)},
        )
    ]
    findings.extend(
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=i + 1,
            message="Candidate page number near bottom margin.",
            details={"location": "bottom"},
        )
        for i in range(count)
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
