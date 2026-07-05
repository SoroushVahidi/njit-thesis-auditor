"""Tests for results-page wording, metadata humanization, and mobile layout polish."""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inject_job(
    wa: Any,
    tmp_path: Path,
    *,
    rule_id: str = "P011",
    issue_type: str = "margin_boundary_violation",
    finding_count: int = 1,
    extra_grouped_summary: dict[str, Any] | None = None,
) -> str:
    """Inject a complete job into the in-memory store and return job_id."""
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    findings = [
        AuditFinding(
            rule_id=rule_id,
            severity=Severity.WARNING,
            page=i + 1,
            message="Test finding.",
            details={"issue_type": issue_type, "side": "left"},
        )
        for i in range(finding_count)
    ]
    job_id = secrets.token_urlsafe(16)
    runtime = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    if extra_grouped_summary:
        if "grouped_summary" not in payload or not isinstance(payload["grouped_summary"], dict):
            payload["grouped_summary"] = {}
        payload["grouped_summary"].update(extra_grouped_summary)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
            for rs in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview="# Audit\n",
    )
    wa._set_job(job)
    return job_id


def _inject_job_with_triage(wa: Any, tmp_path: Path) -> str:
    """Inject a job that includes a populated triage panel for P011."""
    triage_data = {
        "p011_margin_triage": {
            "triage_note": "Multiple pages have margin issues.",
            "triage_tier": "informational",
            "raw_finding_count": 4,
            "affected_pages_compact": "1-4",
            "side_counts": {"left_margin": 2, "right_margin": 2},
            "dominant_margin_side": "left_margin",
        }
    }
    return _inject_job(
        wa,
        tmp_path,
        rule_id="P011",
        issue_type="margin_boundary_violation",
        finding_count=4,
        extra_grouped_summary=triage_data,
    )


# ---------------------------------------------------------------------------
# 1. No "Heuristic counts" in results page
# ---------------------------------------------------------------------------

def test_no_heuristic_counts_in_results(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Heuristic counts" not in resp.content


# ---------------------------------------------------------------------------
# 2. No "All findings are heuristic" in results page
# ---------------------------------------------------------------------------

def test_no_all_findings_are_heuristic(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert "All findings are heuristic" not in body


# ---------------------------------------------------------------------------
# 3. Summary card / triage panel titles use "summary", not "triage"
# ---------------------------------------------------------------------------

def test_page_number_panel_title_uses_summary(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.report_view import _TRIAGE_KEYS

    titles = {t for _, _, t in _TRIAGE_KEYS}
    for title in titles:
        assert "triage" not in title.lower(), f"Panel title still contains 'triage': {title!r}"
        assert "summary" in title.lower(), f"Panel title missing 'summary': {title!r}"


# ---------------------------------------------------------------------------
# 4. "TIER: INFORMATIONAL" (or "tier: informational") no longer appears
# ---------------------------------------------------------------------------

def test_tier_informational_badge_not_in_results(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job_with_triage(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text.lower()
    assert "tier: informational" not in body
    assert "tier:informational" not in body


def test_review_priority_badge_removed_from_results(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The raw "review priority: ..." badge was removed entirely (not just
    reworded) since it leaked an internal triage concept students can't act on."""
    c, wa = client
    job_id = _inject_job_with_triage(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text.lower()
    assert "review priority:" not in body
    assert "conf:" not in body


# ---------------------------------------------------------------------------
# 5. Raw detail keys are humanized in rendered HTML
# ---------------------------------------------------------------------------

def test_humanize_detail_key_function() -> None:
    from njit_auditor.web_app import humanize_detail_key

    assert humanize_detail_key("bottom_margin") == "bottom margin"
    assert humanize_detail_key("left_margin") == "left margin"
    assert humanize_detail_key("right_margin") == "right margin"
    assert humanize_detail_key("possible_body_font_family_issue") == (
        "possible body font family issue"
    )
    assert humanize_detail_key("possible_body_font_size_issue") == "possible body font size issue"
    assert humanize_detail_key("bottom_center") == "bottom center"
    assert humanize_detail_key("margin_boundary_violation") == "margin boundary violation"


def test_issue_type_humanized_in_results_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, issue_type="margin_boundary_violation")
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    # Humanized form should appear somewhere
    assert "margin boundary violation" in body
    # Raw underscore form must not appear as a standalone rendered value
    # (it may appear in data-* attributes which is fine, but not in visible text)
    # We check it doesn't appear as a bare text token in the card title
    assert "· margin_boundary_violation" not in body


def test_triage_highlight_keys_humanized(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job_with_triage(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    # The margin side highlight should show "left margin" not "left_margin"
    assert "left margin" in body or "right margin" in body
    assert "left_margin: 2" not in body


# ---------------------------------------------------------------------------
# 6. Review-order wording no longer uses "dismiss anything"
# ---------------------------------------------------------------------------

def test_review_order_no_dismiss_wording(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert "dismiss anything" not in body


def test_review_order_uses_intentional_wording(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert "intentional" in body


# ---------------------------------------------------------------------------
# 7. Summary by rule guidance appears
# ---------------------------------------------------------------------------

def test_summary_by_rule_guidance_present(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert "Click a rule ID for rule reference" in body


# ---------------------------------------------------------------------------
# 8. Mobile CSS media rule exists for stacked section headers
# ---------------------------------------------------------------------------

def test_mobile_section_header_css_rule_exists(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "max-width: 640px" in body
    assert "flex-direction: column" in body
    assert ".section-header" in body


# ---------------------------------------------------------------------------
# 10. Nav chips wrap on mobile instead of overflowing
# ---------------------------------------------------------------------------


def test_jump_links_css_wraps_instead_of_overflowing(client: tuple[TestClient, Any]) -> None:
    """.jump-links must stay a wrapping flex row so a full chip set (up to 7
    chips across primary + advanced) wraps onto new lines on a narrow
    viewport instead of forcing horizontal scroll."""
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert ".jump-links {" in body
    start = body.index(".jump-links {")
    rule = body[start : start + 200]
    assert "flex-wrap: wrap;" in rule


def test_jump_links_advanced_chips_are_visually_demoted(client: tuple[TestClient, Any]) -> None:
    """Reviewer-facing chips (rule table, detected candidates) use a quieter
    style than the primary student-facing chips, so they read as optional."""
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert ".jump-links__advanced" in body


# ---------------------------------------------------------------------------
# 9. Findings-section grouped-problem cards are mobile-safe
# ---------------------------------------------------------------------------
#
# A grid item's default min-width: auto refuses to shrink below its widest
# descendant's intrinsic size (e.g. the collapsed "individual occurrences"
# table), which pushes the whole page wider than the viewport on mobile.
# These guard the CSS fix so it isn't silently dropped in a later edit.


def test_grouped_problem_card_can_shrink_below_content_width(
    client: tuple[TestClient, Any],
) -> None:
    """.grouped-problem-card is a CSS grid item; it must set min-width: 0 so
    it can shrink to the grid track width instead of stretching to fit a wide
    descendant (like the individual-occurrences table)."""
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert ".grouped-problem-card {" in body
    assert "min-width: 0;" in body


def test_detail_cell_wraps_long_issue_and_fix_text(client: tuple[TestClient, Any]) -> None:
    """The issue-type/suggested-fix column in the individual-occurrences
    table must wrap (not nowrap) since that text can run to a full sentence;
    reusing the short, intentionally-nowrap .meta-cell class here is what
    originally caused the table (and the whole card) to overflow on mobile."""
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert ".detail-cell {" in body
    assert "overflow-wrap: anywhere;" in body


def test_meta_cell_no_longer_forces_nowrap(client: tuple[TestClient, Any]) -> None:
    """.meta-cell (used for the "Pages: ..." line) must wrap for a long,
    non-contiguous page list instead of forcing one unbroken line."""
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    meta_cell_start = body.index(".meta-cell {")
    meta_cell_rule = body[meta_cell_start : meta_cell_start + 200]
    assert "white-space: nowrap" not in meta_cell_rule
