from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import (
    audit_findings_to_json_dict,
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


def test_audit_findings_to_json_dict_has_summary_counts() -> None:
    payload = audit_findings_to_json_dict(_sample_findings(), _metadata())
    assert payload["metadata"]["total_findings"] == 3
    assert payload["metadata"]["counts_by_severity"]["WARNING"] == 3
    assert payload["metadata"]["counts_by_rule_id"]["P011"] == 1
    assert payload["metadata"]["counts_by_category"]["margin_or_overflow"] == 1


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


def test_json_report_is_written_and_parent_created(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "report.json"
    write_json_report(_sample_findings(), _metadata(), output_path)
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert '"counts_by_rule_id"' in text
    assert '"P011"' in text


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
