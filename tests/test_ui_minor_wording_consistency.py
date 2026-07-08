"""Narrow regression tests for minor UI wording consistency."""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from njit_auditor.report_outputs import _MARKDOWN_GROUPED_SUMMARIES_HEADING


def _make_app(tmp_path: Path):
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


def _inject_complete_job(
    wa,
    tmp_path: Path,
    rule_id: str = "P011",
    finding_count: int = 1,
) -> str:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.pdf_highlight import get_pdf_page_sizes
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    findings = [
        AuditFinding(
            rule_id=rule_id,
            severity=Severity.WARNING,
            page=i + 1,
            message="Test finding.",
            details={"issue_type": "margin_boundary_violation", "side": "left"},
        )
        for i in range(finding_count)
    ]
    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(jdir / "upload.pdf")
    doc.close()
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    pdf_page_sizes = get_pdf_page_sizes(jdir / "upload.pdf")
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv["rule_id"],
                "severity": fv["severity"],
                "page": fv["page"],
                "issue_type": fv["issue_type"],
                "category": fv["category"],
                "polished_comment": fv["polished_comment"],
                "suggested_fix": fv.get("suggested_fix", ""),
                "triage_tier": fv.get("triage_tier", ""),
                "confidence": fv.get("confidence", ""),
                "confidence_level": fv.get("confidence_level", ""),
                "confidence_label": fv.get("confidence_label", ""),
                "confidence_css_class": fv.get("confidence_css_class", ""),
                "source_file": fv.get("source_file", ""),
                "source_line": fv.get("source_line", ""),
                "location_label": fv.get("location_label", ""),
                "bbox": fv.get("bbox"),
                "action_kind": fv.get("action_kind", ""),
                "action_label": fv.get("action_label", ""),
                "has_highlight": fv.get("has_highlight", False),
                "no_highlight_reason": fv.get("no_highlight_reason", ""),
                "detailed_explanation": fv.get("detailed_explanation", ""),
                "issue_type_label": fv.get("issue_type_label", ""),
                "issue_type_explanation": fv.get("issue_type_explanation", ""),
            }
            for fv in view_dict.get("findings", [])
        ],
        grouped_summary=[
            {
                "rule_id": rs.rule_id,
                "count": rs.count,
                "category": rs.category,
            }
            for rs in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview="# Audit Report\n",
    )
    wa._set_job(job)
    return job_id


@pytest.fixture()
def client(tmp_path: Path):
    return _make_app(tmp_path)


def test_jump_chip_uses_recommended_review_order_label(
    client, tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.text
    assert '>Recommended review order<' in html
    assert 'href="#section-review-order"' in html
    assert ">Review order<" not in html


def test_main_report_nav_avoids_legacy_toggle_labels(client, tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    html = c.get(f"/audits/{job_id}").text
    assert "Grouped problems" not in html
    assert "All individual findings" not in html
    assert "Most common issues" not in html
    assert "filter-severity" not in html


def test_markdown_export_grouped_heading_matches_ui_wording(tmp_path: Path) -> None:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import write_markdown_report

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
            },
        )
        for page in (1, 2)
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(
        findings,
        {"input_file_name": "thesis.pdf", "audit_type": "pdf"},
        output_path,
    )
    text = output_path.read_text(encoding="utf-8")
    assert f"## {_MARKDOWN_GROUPED_SUMMARIES_HEADING}" in text
    assert "## Grouped Problems" not in text


def test_demo_guide_describes_recommended_review_order() -> None:
    guide = Path("docs/web_ui_demo_guide.md").read_text(encoding="utf-8")
    assert "Recommended review order" in guide
    assert "\n   - Review order\n" not in guide
    assert "Summary → Review order" not in guide
