"""Regression test: main findings list highlight links must target the finding
the card actually displays, even when the default page-order display sort
reorders findings relative to their storage order in ``job.findings``.

Root cause (found during the 2026-07 highlight-quality audit): PR #459 made
page-order the default display sort for the main individual-findings list
(``report_view.sort_findings``) but the template still built each finding's
"Open highlighted PDF page" / "Open original PDF page" link with
``finding_index=loop.index0`` -- the position in the *post-sort displayed*
list. The server resolved that index against ``job.findings`` in its
*pre-sort storage* order (``_matching_findings_for_highlight`` in
web_app.py), which is not page-ordered. Whenever those two orders differ
(the common case), a card's link silently resolved to a *different*
finding's page/rule_id/issue_type, so the served "highlighted" PDF either
showed no highlight at all (page mismatch, safe fallback) or -- when two
findings coincidentally shared a page -- could show the wrong finding's box
under the right finding's card.

The fix drops ``finding_index`` from the two links in job.html's main
findings list, matching the pattern already used (and already correct) on
every drill-down page (problem_group.html) and in job.html's own grouped
"individual occurrences" table, which resolve highlights by
page/rule_id/issue_type alone.
"""
from __future__ import annotations

import html
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from pdf_link_helpers import extract_audit_pdf_links

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_highlight import get_pdf_page_sizes
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict

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


def _write_real_pdf(path: Path, *, page_count: int = 10) -> None:
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 96), f"Synthetic thesis page {index + 1}.")
    doc.save(path)
    doc.close()


def _inject_job(wa: Any, findings: list[AuditFinding], *, page_count: int = 10) -> str:
    """Mirror web_app._run_audit_task's job.findings construction exactly.

    Deliberately does NOT reorder findings into page order before storing
    them as job.findings, matching production: build_report_view's output
    order is preserved as storage order, and only the *display* layer
    (report_view.sort_findings, applied per-request in job_page()) reorders
    for the page-order default view.
    """
    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf", page_count=page_count)

    metadata = {"input_file_name": "order-check.pdf", "audit_type": "pdf", "job_id": job_id}
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
        file_name="order-check.pdf",
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for finding in view.findings if finding.severity == "WARNING"),
        fail_count=sum(1 for finding in view.findings if finding.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "finding_id": fv.finding_id,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
                "bbox": list(fv.bbox) if fv.bbox else None,
                "action_kind": fv.action_kind,
                "action_label": fv.action_label,
                "has_highlight": fv.has_highlight,
                "no_highlight_reason": fv.no_highlight_reason,
                "detailed_explanation": fv.detailed_explanation,
                "issue_type_label": fv.issue_type_label,
                "issue_type_explanation": fv.issue_type_explanation,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": row.rule_id, "count": row.count, "category": row.category}
            for row in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
    )
    wa._set_job(job)
    return job_id


def _make_p011(page: int, *, x0: float) -> AuditFinding:
    """A distinct, valid, on-page bbox per finding so boxes are distinguishable."""
    return AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message=f"Right margin overflow on page {page}.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "worst_overflow_pt": "6.0",
            "affected_line_count": "1",
            "confidence": "medium",
            "bbox": f"{x0},200.0,{x0 + 50.0},230.0",
        },
    )


def test_highlight_link_omits_finding_index(app: tuple[TestClient, Any]) -> None:
    """Main findings list must not embed a position-dependent finding_index."""
    c, wa = app
    # Storage order deliberately reverse of page order: page 9 stored first,
    # page 1 stored second. The default display sort is page order, so the
    # displayed order is the reverse of storage order.
    findings = [_make_p011(9, x0=100.0), _make_p011(1, x0=300.0)]
    job_id = _inject_job(wa, findings)

    resp = c.get(f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200
    text = html.unescape(resp.text)

    assert "finding_index=" not in text


def test_highlighted_link_matches_displayed_card_under_page_order_sort(
    app: tuple[TestClient, Any],
) -> None:
    """Each card's highlight link must open a highlight on *that card's* page.

    Regression for the finding_index/display-order mismatch: before the fix,
    requesting the link rendered for the page-9 card (stored first, displayed
    second under default page-order sort) resolved server-side against the
    wrong stored finding and produced no visible annotation at all.
    """
    c, wa = app
    findings = [_make_p011(9, x0=100.0), _make_p011(1, x0=300.0)]
    job_id = _inject_job(wa, findings)

    text, status = html.unescape(c.get(f"/audits/{job_id}").text), c.get(
        f"/audits/{job_id}"
    ).status_code
    assert status == 200

    highlighted_links = sorted(
        link for link in extract_audit_pdf_links(text) if "highlighted" in link
    )
    assert len(highlighted_links) == 2

    seen_pages = set()
    for link in highlighted_links:
        query = link.split("?", 1)[1]
        params = dict(p.split("=") for p in query.split("&"))
        requested_page = int(params["page"])
        seen_pages.add(requested_page)

        resp = c.get(link)
        assert resp.status_code == 200
        with fitz.open(stream=resp.content, filetype="pdf") as doc:
            # /highlighted-page.pdf serves a single-page extract (always doc[0]).
            page = doc[0]
            annots = list(page.annots() or [])
            assert annots, (
                f"Expected a real highlight annotation on page {requested_page}, "
                "found none -- the highlight link resolved to the wrong finding."
            )

    assert seen_pages == {1, 9}
