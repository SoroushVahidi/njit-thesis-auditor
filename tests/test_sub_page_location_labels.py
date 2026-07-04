"""Regression tests for sub-page location labels in the PDF web UI.

Covers the salvaged, geometry-driven replacement for PR #311's sub-page
location-label concept: labels are derived purely from (bbox, page_size)
quadrant geometry, never from rule-specific text snippets, and never replace
or weaken existing problem explanations or the strict highlight policy.
"""
from __future__ import annotations

import html
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from pdf_link_helpers import extract_audit_pdf_links

_MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Viewport-Width": "390",
}

_DESKTOP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Viewport-Width": "1440",
}


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def app(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _write_real_pdf(path: Path, *, page_count: int = 6) -> None:
    doc = fitz.open()
    for page_index in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 96), f"Synthetic thesis page {page_index + 1}.")
    doc.save(path)
    doc.close()


def _get_html(client: TestClient, path: str, *, headers: dict[str, str] | None = None) -> str:
    resp = client.get(path, headers=headers or _DESKTOP_HEADERS)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return html.unescape(resp.text)


def _pdf_links(text: str) -> set[str]:
    return extract_audit_pdf_links(text)



def _summary_value(text: str, label: str) -> str:
    pattern = re.compile(
        rf'<div class="summary-card__label">{re.escape(label)}</div>\s*'
        r'<div class="summary-card__value">([^<]+)</div>'
    )
    match = pattern.search(text)
    assert match, f"Could not find summary card {label!r}"
    return match.group(1).strip()


def _inject_job(
    wa: Any,
    findings: list[Any],
    *,
    file_name: str = "sub-page-location-labels.pdf",
    page_count: int = 6,
) -> tuple[str, Any]:
    from njit_auditor.pdf_highlight import get_pdf_page_sizes
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf", page_count=page_count)

    metadata = {"input_file_name": file_name, "audit_type": "pdf", "job_id": job_id}
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
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name=file_name,
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=int(view.counts_by_severity.get("WARNING", 0)),
        fail_count=int(view.counts_by_severity.get("FAIL", 0)),
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
            {"rule_id": row.rule_id, "count": row.count, "category": row.category}
            for row in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
        text_layer_quality="good",
    )
    wa._set_job(job)
    return job_id, view


# ---------------------------------------------------------------------------
# 1. Location label from a valid bbox
# ---------------------------------------------------------------------------


def test_location_label_from_valid_bbox_top_of_page(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P012",
                severity=Severity.WARNING,
                page=2,
                message="Annotation detected.",
                details={
                    "issue_type": "pdf_annotation_detected",
                    "rect": "250.0,80.0,360.0,100.0",
                },
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}")
    assert "Page 2 — PDF annotations/comments detected" in text
    assert "uploaded PDF" in text
    assert "page 2" in text
    assert "not a highlight added by this auditor" in text
    # No raw bbox coordinates leak into the student-facing page.
    for raw in ("250.0", "80.0", "360.0", "100.0"):
        assert raw not in text


# ---------------------------------------------------------------------------
# 2. Location label for a margin-side finding
# ---------------------------------------------------------------------------


def test_location_label_for_margin_side_finding(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=4,
                message="Right margin overflow.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "right_margin",
                    "rect": "545.0,400.0,580.0,420.0",
                },
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}")
    assert "cross the required right margin boundary" in text
    assert "Page 4 — right margin" in text
    # The highlight is geometrically valid here, so the strict policy must
    # allow the highlight action -- but no forbidden page-only phrasing.
    assert "Open highlighted PDF page" in text
    assert "Open PDF page" not in text
    assert "Open first example page" not in text


# ---------------------------------------------------------------------------
# 3. Missing/invalid bbox never produces a misleading label
# ---------------------------------------------------------------------------


def test_missing_bbox_shows_no_misleading_location_label(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
            )
        ],
    )
    resp = client.get(f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200
    text = html.unescape(resp.text)
    assert "Page 2 — left margin" in text
    for forbidden in (
        "Top of page",
        "Bottom of page",
        "Left margin area",
        "Right margin area",
        "Header area",
        "Footer area",
        "Near page center",
        "Body area",
    ):
        assert forbidden not in text
    assert "Open highlighted PDF page" not in text


def test_invalid_degenerate_bbox_shows_no_misleading_location_label(
    app: tuple[TestClient, Any],
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P012",
                severity=Severity.WARNING,
                page=3,
                message="Annotation detected.",
                details={
                    "issue_type": "pdf_annotation_detected",
                    "rect": "100.0,100.0,100.0,100.0",
                },
            )
        ],
    )
    resp = client.get(f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200
    text = html.unescape(resp.text)
    assert "Page 3" in text
    for forbidden in (
        "Top of page",
        "Bottom of page",
        "Body area",
        "Near page center",
    ):
        assert forbidden not in text
    assert "Open highlighted PDF page" not in text


# ---------------------------------------------------------------------------
# 4. Highlight policy regression
# ---------------------------------------------------------------------------


def test_highlight_policy_unaffected_by_location_labels(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    no_highlight_job, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
            )
        ],
    )
    text = _get_html(client, f"/audits/{no_highlight_job}")
    assert "Open PDF page" not in text
    assert "Open first example page" not in text
    assert "Open highlighted PDF page" not in text
    assert "/pdf/highlighted" not in text

    highlight_job, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "left_margin",
                    "rect": "20.0,380.0,90.0,420.0",
                },
            )
        ],
        file_name="highlight-job.pdf",
    )
    highlighted_text = _get_html(client, f"/audits/{highlight_job}")
    assert "Open highlighted PDF page" in highlighted_text
    assert "Page 2 — left margin" in highlighted_text
    links = _pdf_links(highlighted_text)
    assert links
    for link in links:
        resp = client.get(link)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")


# ---------------------------------------------------------------------------
# 5. Page-number regression
# ---------------------------------------------------------------------------


def test_routine_page_number_candidate_remains_suppressed(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, view = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P013",
                severity=Severity.WARNING,
                page=2,
                message="Page number candidate.",
                details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}")
    assert view.total_findings == 0
    assert len(view.inventory_findings) == 1
    assert _summary_value(text, "Items to review") == "0"


def test_real_page_number_defect_keeps_exact_wording(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                page=5,
                message="Missing page number.",
                details={"issue_type": "missing_page_number"},
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}")
    assert "The auditor did not find a clear page number on page 5" in text


# ---------------------------------------------------------------------------
# 6. Margin/font wording regression
# ---------------------------------------------------------------------------


def test_margin_and_font_wording_not_replaced_by_location_label_alone(
    app: tuple[TestClient, Any],
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "right_margin",
                    "rect": "545.0,400.0,580.0,420.0",
                },
            ),
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=3,
                message="Font issue.",
                details={
                    "issue_type": "possible_body_font_family_issue",
                    "observed_summary": "CMR12",
                },
            ),
        ],
    )
    text = _get_html(client, f"/audits/{job_id}")
    assert "cross the required right margin boundary" in text
    assert "Page 2 — right margin" in text
    assert (
        "Page 3 — body text uses Computer Modern / LaTeX font (pattern \"CMR12\") where "
        "Times New Roman or an accepted equivalent is expected"
    ) in text
    assert "font family CMR12" in text
    assert "Times New Roman" in text


# ---------------------------------------------------------------------------
# 7. Main/category/rule/issue-type consistency
# ---------------------------------------------------------------------------


def test_location_label_consistent_across_drilldown_pages(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=4,
                message="Right margin overflow.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "right_margin",
                    "rect": "545.0,400.0,580.0,420.0",
                },
            )
        ],
    )
    for path in (
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/margin-or-overflow",
        f"/audits/{job_id}/problems/rule/P011",
        f"/audits/{job_id}/problems/rule/P011/issue-type/margin-boundary-violation",
    ):
        text = _get_html(client, path)
        assert "Page 4 — right margin" in text, f"missing location label on {path}"


# ---------------------------------------------------------------------------
# 8. Mobile/desktop parity
# ---------------------------------------------------------------------------


def test_location_label_mobile_desktop_parity(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=4,
                message="Right margin overflow.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "right_margin",
                    "rect": "545.0,400.0,580.0,420.0",
                },
            ),
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
            ),
        ],
    )
    mobile = _get_html(client, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop = _get_html(client, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    for fragment in (
        "Page 4 — right margin",
        "cross the required right margin boundary",
        "Open highlighted PDF page",
    ):
        assert fragment in mobile
        assert fragment in desktop
    assert _pdf_links(mobile) == _pdf_links(desktop)


# ---------------------------------------------------------------------------
# 9. No-500 crawl
# ---------------------------------------------------------------------------


def test_location_label_route_crawl_has_no_500s(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id, _ = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=4,
                message="Right margin overflow.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "right_margin",
                    "rect": "545.0,400.0,580.0,420.0",
                },
            ),
            AuditFinding(
                rule_id="P012",
                severity=Severity.WARNING,
                page=2,
                message="Annotation detected.",
                details={
                    "issue_type": "pdf_annotation_detected",
                    "rect": "100.0,100.0,100.0,100.0",
                },
            ),
        ],
        file_name="crawl-sub-page-location.pdf",
    )
    routes = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/margin-or-overflow",
        f"/audits/{job_id}/problems/rule/P011",
        f"/audits/{job_id}/problems/rule/P011/issue-type/margin-boundary-violation",
        f"/audits/{job_id}/problems/rule/P012",
    ]
    pdf_links: set[str] = set()
    for route in routes:
        text = _get_html(client, route)
        pdf_links.update(_pdf_links(text))
    for route in routes:
        resp = client.get(route, headers=_DESKTOP_HEADERS)
        assert resp.status_code == 200
    assert pdf_links
    for link in pdf_links:
        resp = client.get(link, headers=_DESKTOP_HEADERS)
        assert resp.status_code == 200
