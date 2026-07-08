"""Sample A correctness regression tests (privacy-safe, no PDF body text in assertions)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import fitz

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_frontmatter_headings import check_pdf_frontmatter_headings
from njit_auditor.web_samples import get_builtin_sample


def _make_concatenated_heading_pdf(tmp_path: Path, heading_line: str) -> Path:
    """Minimal PDF whose text layer has a concatenated front-matter heading line."""
    pdf_path = tmp_path / "concat_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 90), heading_line, fontsize=12)
    page.insert_text((108, 120), "Placeholder synthetic body line.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_p038_concatenated_approval_page_not_reported_missing(tmp_path: Path) -> None:
    pdf_path = _make_concatenated_heading_pdf(tmp_path, "APPROVALPAGE")
    model = load_pdf_layout(str(pdf_path))
    missing = [
        f
        for f in check_pdf_frontmatter_headings(model)
        if f.details.get("issue_type") == "required_heading_missing"
        and f.details.get("expected_heading") == "APPROVAL PAGE"
    ]
    assert missing == []


def test_p038_concatenated_table_of_contents_not_reported_missing(tmp_path: Path) -> None:
    pdf_path = _make_concatenated_heading_pdf(tmp_path, "TABLEOFCONTENTS")
    model = load_pdf_layout(str(pdf_path))
    missing = [
        f
        for f in check_pdf_frontmatter_headings(model)
        if f.details.get("issue_type") == "required_heading_missing"
        and f.details.get("expected_heading") == "TABLE OF CONTENTS"
    ]
    assert missing == []


def test_p038_concatenated_variant_does_not_emit_phrase_not_exact(tmp_path: Path) -> None:
    pdf_path = _make_concatenated_heading_pdf(tmp_path, "BIOGRAPHICALSKETCH")
    model = load_pdf_layout(str(pdf_path))
    phrase = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    assert phrase == []


def test_ester_sample_a_problem_finding_baseline() -> None:
    """Regression guard for the reproducible Sample A correctness fixes."""
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    problem = view.findings
    by_rule = Counter(f.rule_id for f in problem)

    assert len(problem) == 25
    assert by_rule["P038"] == 0
    assert by_rule["P011"] == 19
    assert by_rule["P013"] == 0
    assert by_rule["P028"] == 0
    assert by_rule["P044"] == 0
    assert by_rule["P027"] == 0
    assert by_rule["P015"] == 1


def test_ester_sample_a_p012_rollup_lists_affected_pages() -> None:
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    p012 = next(f for f in view.findings if f.rule_id == "P012")
    assert "Affected pages include:" in p012.polished_comment
    assert "42 pages total" in p012.polished_comment


def test_p038_required_heading_missing_remains_student_visible() -> None:
    finding = AuditFinding(
        rule_id="P038",
        severity=Severity.WARNING,
        message="Missing required heading.",
        details={
            "issue_type": "required_heading_missing",
            "expected_heading": "TABLE OF CONTENTS",
            "section_key": "table_of_contents",
        },
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    assert len(view.findings) == 1
    assert view.findings[0].rule_id == "P038"
    assert view.findings[0].location_label == (
        "Front matter — required heading missing: TABLE OF CONTENTS"
    )
    assert view.findings[0].has_highlight is False
    assert "document-level" in view.findings[0].no_highlight_reason.lower()


def test_ester_sample_a_json_export_schema_unchanged() -> None:
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    assert set(payload.keys()) == {"findings", "grouped_findings", "grouped_summary", "metadata"}
    if payload["findings"]:
        assert set(payload["findings"][0].keys()) >= {
            "rule_id",
            "severity",
            "page",
            "message",
            "details",
        }
