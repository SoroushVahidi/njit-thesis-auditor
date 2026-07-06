"""Narrow regression tests for minor UI wording consistency."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from njit_auditor.report_outputs import _MARKDOWN_GROUPED_SUMMARIES_HEADING


def _make_app(tmp_path: Path):
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path):
    return _make_app(tmp_path)


def test_jump_chip_uses_recommended_review_order_label(
    client, tmp_path: Path
) -> None:
    from tests.test_help_rules import _inject_complete_job

    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.text
    assert '>Recommended review order<' in html
    assert 'href="#section-review-order"' in html
    assert ">Review order<" not in html


def test_main_report_nav_avoids_legacy_toggle_labels(client, tmp_path: Path) -> None:
    from tests.test_help_rules import _inject_complete_job

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
