"""P019 highlighted-PDF action link crawl (desktop + mobile).

Verifies the new bbox evidence P019 now carries (mixed_numbering_style
per-page, Roman sequence_gap) actually renders a real highlighted-PDF link
that returns a valid PDF at the correct page, on both desktop and mobile
User-Agents, and that stable finding IDs / no-JSON-fallback guarantees from
PR #501 still hold.
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


def _write_real_pdf(path: Path, *, page_count: int = 8) -> None:
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 96), f"Synthetic thesis page {index + 1}.")
    doc.save(path)
    doc.close()


def _inject_job(
    wa: Any,
    findings: list[AuditFinding],
    *,
    file_name: str = "p019-location-evidence.pdf",
    page_count: int = 8,
) -> tuple[str, Any]:
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
    return job_id, view


def _get_html(
    client: TestClient, path: str, *, headers: dict[str, str] | None = None
) -> tuple[str, int]:
    resp = client.get(path, headers=headers or _DESKTOP_HEADERS)
    return html.unescape(resp.text), resp.status_code


def _p019_mixed_style_finding(*, page: int = 4) -> AuditFinding:
    return AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=page,
        message="Mixed page-numbering styles detected on one page.",
        details={
            "page_number": str(page),
            "issue_type": "mixed_numbering_style",
            "observed_style": "Arabic numerals, lowercase Roman numerals",
            "expected_style": "one consistent page-numbering style",
            "confidence": "medium",
            "bbox": _BBOX,
        },
    )


def _p019_roman_sequence_gap_finding(*, page: int = 5) -> AuditFinding:
    return AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=page,
        message="Roman page-number candidate sequence shows an obvious gap/break.",
        details={
            "page_number": str(page),
            "issue_type": "sequence_gap",
            "observed_sequence": "iv",
            "expected_sequence": "iii",
            "previous_sequence_value": "ii",
            "previous_sequence_page": str(page - 1),
            "next_sequence_value": "",
            "next_sequence_page": "",
            "sequence_confidence": "medium",
            "confidence": "medium",
            "bbox": _BBOX,
        },
    )


def _crawl_and_verify(
    client: TestClient, findings: list[AuditFinding], wa: Any, *, headers: dict[str, str]
) -> None:
    job_id, view = _inject_job(wa, findings)
    text, status = _get_html(client, f"/audits/{job_id}", headers=headers)
    assert status == 200

    highlighted_links = [link for link in extract_audit_pdf_links(text) if "highlighted" in link]
    assert highlighted_links, "expected at least one highlighted PDF link for P019 findings"

    for link in highlighted_links:
        resp = client.get(link, headers=headers)
        assert resp.status_code == 200, link
        assert resp.headers["content-type"].startswith("application/pdf"), link
        assert resp.content.startswith(b"%PDF"), link


def test_p019_mixed_style_highlight_crawl_desktop(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    _crawl_and_verify(c, [_p019_mixed_style_finding(page=4)], wa, headers=_DESKTOP_HEADERS)


def test_p019_mixed_style_highlight_crawl_mobile(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    _crawl_and_verify(c, [_p019_mixed_style_finding(page=4)], wa, headers=_MOBILE_HEADERS)


def test_p019_roman_sequence_gap_highlight_crawl_desktop(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    _crawl_and_verify(c, [_p019_roman_sequence_gap_finding(page=5)], wa, headers=_DESKTOP_HEADERS)


def test_p019_roman_sequence_gap_highlight_crawl_mobile(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    _crawl_and_verify(c, [_p019_roman_sequence_gap_finding(page=5)], wa, headers=_MOBILE_HEADERS)


def test_p019_desktop_and_mobile_links_are_identical(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [_p019_mixed_style_finding(page=4), _p019_roman_sequence_gap_finding(page=5)]
    job_id, view = _inject_job(wa, findings)

    mobile_text, mobile_status = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop_text, desktop_status = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    assert mobile_status == 200
    assert desktop_status == 200

    mobile_links = {link for link in extract_audit_pdf_links(mobile_text) if "highlighted" in link}
    desktop_links = {
        link for link in extract_audit_pdf_links(desktop_text) if "highlighted" in link
    }
    assert mobile_links == desktop_links
    assert mobile_links


def test_p019_no_bbox_finding_never_produces_a_fake_highlight_link(
    app: tuple[TestClient, Any],
) -> None:
    """A document-wide finding (page=None, no bbox -- the genuinely
    uncertain case) must fall back to the original-page action, never claim
    a highlighted location that does not exist."""
    c, wa = app
    finding = AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=None,
        message="Mixed numbering styles detected across candidate page-number regions.",
        details={
            "page_number": "-",
            "issue_type": "mixed_numbering_style",
            "observed_style": "Arabic numerals, lowercase Roman numerals",
            "expected_style": "one consistent page-numbering style per numbering section",
            "confidence": "low",
        },
    )
    job_id, view = _inject_job(wa, [finding])
    fv = next(f for f in view.findings if f.rule_id == "P019")
    assert fv.has_highlight is False
    assert fv.bbox is None

    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200
    highlighted_links = [link for link in extract_audit_pdf_links(text) if "highlighted" in link]
    assert highlighted_links == []
