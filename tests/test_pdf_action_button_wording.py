"""Regression tests for "Open highlighted/original PDF page" button honesty.

Investigated as a follow-up to the 2026-07 highlight-quality audit: a mobile
report showed a "Open highlighted PDF page" button that (for a no-highlight
finding) actually opened the full multi-page PDF via a ``#page=N`` fragment,
which mobile PDF viewers do not reliably honor -- so the button silently
opened what looked like "the whole document" instead of the single page its
label implied.

Root cause: ``action_kind == "highlight"`` findings already resolved through
``/audits/{job_id}/highlighted-page.pdf`` -- a route that always extracts a
true single page (drawing a highlight box when one is available, or a plain
single-page copy otherwise; see ``pdf_highlight.build_highlighted_single_page_pdf``
/ ``build_single_page_pdf``). But ``action_kind == "original_page"`` findings
(page known, no bbox) instead resolved through ``/audits/{job_id}/pdf#page=N``
-- the full original PDF with a fragment anchor.

Fix: route both action kinds through the same true single-page endpoint
(``_pdf_action_url`` in web_app.py), and append the finding's page number to
the visible button text (not just the ``title`` tooltip, which mobile
browsers never surface) so it's unambiguous which single page will open.

This file covers:
1. Both "highlight" and "original_page" buttons render the page number in
   visible text.
2. Both action kinds resolve to the same single-page endpoint pattern, never
   a ``#page=N`` fragment into the full document.
3. Fetching either link returns a genuinely single-page PDF.
4. No-highlight (page-less, explanation-only) findings render no PDF action
   at all.
5. Mobile vs. desktop parity for the button text.
6. No ``finding_index`` in any rendered link (regression coverage for the
   prior finding_index/display-order fix, exercised in this new context).
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

_MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
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

_BBOX = "100.0,200.0,300.0,260.0"


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


def _inject_job(
    wa: Any, findings: list[AuditFinding], *, page_count: int = 10
) -> str:
    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf", page_count=page_count)

    metadata = {"input_file_name": "button-wording.pdf", "audit_type": "pdf", "job_id": job_id}
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
        file_name="button-wording.pdf",
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


def _get_html(client: TestClient, path: str, *, headers: dict[str, str] | None = None) -> str:
    resp = client.get(path, headers=headers or _DESKTOP_HEADERS)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return html.unescape(resp.text)


def _highlight_finding(page: int) -> AuditFinding:
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
            "bbox": _BBOX,
        },
    )


def _original_page_finding(page: int) -> AuditFinding:
    """A P026 font finding with a known page but no bbox (no-highlight case)."""
    return AuditFinding(
        rule_id="P026",
        severity=Severity.WARNING,
        page=page,
        message=f"Font issue on page {page}.",
        details={
            "issue_type": "possible_body_font_family_issue",
            "confidence": "medium",
        },
    )


def _explanation_only_finding() -> AuditFinding:
    """A document-level finding with no page at all."""
    return AuditFinding(
        rule_id="P021",
        severity=Severity.WARNING,
        page=None,
        message="Abstract word count exceeded.",
        details={"word_count": "420", "limit": "350"},
    )


# ---------------------------------------------------------------------------
# 1 & 2. Visible button text includes the page number; URL is a true
# single-page endpoint for both action kinds, never a #page=N fragment.
# ---------------------------------------------------------------------------


def test_highlight_button_shows_page_number_and_single_page_url(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_highlight_finding(4)])
    text = _get_html(c, f"/audits/{job_id}")

    assert "Open highlighted PDF page 4" in text
    assert f"/audits/{job_id}/highlighted-page.pdf?page=4" in text
    assert f"/audits/{job_id}/pdf#page=4" not in text


def test_original_page_button_shows_page_number_and_single_page_url(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_original_page_finding(4)])
    text = _get_html(c, f"/audits/{job_id}")

    assert "Open highlighted PDF page" not in text
    assert "Open original PDF page 4" in text
    assert (
        f"/audits/{job_id}/highlighted-page.pdf?page=4"
        "&rule_id=P026&issue_type=possible_body_font_family_issue" in text
    )
    assert f"/audits/{job_id}/pdf#page=4" not in text


# ---------------------------------------------------------------------------
# 3. Both links actually serve a true single-page PDF.
# ---------------------------------------------------------------------------


def test_highlight_link_serves_true_single_page_pdf(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_highlight_finding(4)])
    text = _get_html(c, f"/audits/{job_id}")
    links = [link for link in extract_audit_pdf_links(text) if "highlighted-page" in link]
    assert len(links) == 1

    resp = c.get(links[0])
    assert resp.status_code == 200
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        assert doc.page_count == 1
        assert list(doc[0].annots() or [])


def test_original_page_link_serves_true_single_page_pdf(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_original_page_finding(4)])
    text = _get_html(c, f"/audits/{job_id}")
    links = [link for link in extract_audit_pdf_links(text) if "highlighted-page" in link]
    assert len(links) == 1

    resp = c.get(links[0])
    assert resp.status_code == 200
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        # No bbox exists for this finding, so no annotation is drawn -- but
        # it must still be a real, single-page extract, not the full PDF
        # (originally written with page_count=10) and not a 404/error.
        assert doc.page_count == 1
        assert not list(doc[0].annots() or [])


# ---------------------------------------------------------------------------
# 4. No-highlight, page-less findings render no PDF action at all.
# ---------------------------------------------------------------------------


def test_explanation_only_finding_has_no_pdf_action(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_explanation_only_finding()])
    text = _get_html(c, f"/audits/{job_id}")

    assert "Open highlighted PDF page" not in text
    assert "Open original PDF page" not in text
    assert "highlighted-page.pdf" not in text
    assert "document-level and does not correspond to a specific page" in text


# ---------------------------------------------------------------------------
# 5. Mobile vs. desktop parity for the (now page-numbered) button text.
# ---------------------------------------------------------------------------


def test_mobile_desktop_parity_for_page_numbered_button_text(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_highlight_finding(4), _original_page_finding(6)])

    desktop_text = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    mobile_text = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)

    assert "Open highlighted PDF page 4" in desktop_text
    assert "Open highlighted PDF page 4" in mobile_text
    assert "Open original PDF page 6" in desktop_text
    assert "Open original PDF page 6" in mobile_text
    assert desktop_text.count("Open highlighted PDF page 4") == mobile_text.count(
        "Open highlighted PDF page 4"
    )
    assert desktop_text.count("Open original PDF page 6") == mobile_text.count(
        "Open original PDF page 6"
    )


# ---------------------------------------------------------------------------
# 6. No finding_index in any rendered link (regression coverage in this
# new highlight/original-page-unified context).
# ---------------------------------------------------------------------------


def test_no_finding_index_in_rendered_links(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    # Storage order deliberately reverse of page order, matching the prior
    # finding_index/display-order regression scenario.
    job_id = _inject_job(wa, [_highlight_finding(9), _original_page_finding(1)])
    text = _get_html(c, f"/audits/{job_id}")

    assert "finding_index=" not in text
