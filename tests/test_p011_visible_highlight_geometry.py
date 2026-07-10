"""Every visible Sample A/B P011 finding must expose valid highlight geometry."""

from __future__ import annotations

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.web_samples import get_builtin_sample


def _visible_p011(sample_id: str) -> list:
    sample = get_builtin_sample(sample_id)
    if not sample.abs_path.exists():
        return []
    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    return [f for f in view.findings if f.rule_id == "P011"]


def test_sample_a_visible_p011_all_have_highlight_bboxes() -> None:
    for finding in _visible_p011("ester_sample_a"):
        assert finding.has_highlight is True, f"page {finding.page}: missing highlight"
        assert finding.bbox is not None, f"page {finding.page}: no bbox"
        x0, y0, x1, y1 = finding.bbox
        assert x1 > x0 and y1 > y0, f"page {finding.page}: degenerate bbox"


def test_sample_b_visible_p011_all_have_highlight_bboxes() -> None:
    for finding in _visible_p011("ester_sample_b"):
        assert finding.has_highlight is True, f"page {finding.page}: missing highlight"
        assert finding.bbox is not None, f"page {finding.page}: no bbox"
        x0, y0, x1, y1 = finding.bbox
        assert x1 > x0 and y1 > y0, f"page {finding.page}: degenerate bbox"
