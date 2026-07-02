"""Regression tests for P017 caption highlight support.

Covers wiring ``CaptionLine.bbox`` (already populated since PR #327) into
``AuditFinding.details["bbox"]`` for P017 figure/table caption findings, via the
existing generic, rule-agnostic highlight pipeline (no rule-specific code added).

1. P017 with valid caption bbox: real highlight, explanation still visible
2. P017 without bbox: stays explanation-only, no fake/page-only action
3. Invalid/degenerate bbox is handled safely (no crash, no fake highlight)
4. Caption privacy: no raw bbox coordinates or caption body text leaked
5. Regression: PR #327 highlight coverage (P011/P026) remains intact
6. Regression: forbidden actions never reappear
7. Mobile/desktop parity for P017 highlight and no-highlight cases
8. No-500 route crawl across main/category/rule/issue-type/highlighted-PDF routes
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

# A safely on-page, clearly-visible box for a 612x792pt synthetic page.
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
    file_name: str = "p017-caption-highlight.pdf",
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


def _pdf_links(text: str) -> set[str]:
    return extract_audit_pdf_links(text)



def _category_slug(category: str) -> str:
    return str(category).strip().replace("_", "-")


def _issue_type_slug(issue_type: str) -> str:
    return str(issue_type).strip().replace("_", "-")


def _p017_finding(
    *,
    issue_type: str = "missing_terminal_punctuation",
    caption_type: str = "figure",
    page: int = 4,
    bbox: str | None = _BBOX,
) -> AuditFinding:
    """Build a P017 finding matching real check_pdf_captions() details shape."""
    details = {
        "page_number": str(page),
        "caption_type": caption_type,
        "issue_type": issue_type,
        "line_preview": "Figure 4 some caption text without terminal punctuation",
        "confidence": "high",
    }
    if bbox is not None:
        details["bbox"] = bbox
    return AuditFinding(
        rule_id="P017",
        severity=Severity.WARNING,
        page=page,
        message="Figure caption appears to be missing terminal punctuation.",
        details=details,
    )


# ---------------------------------------------------------------------------
# 1. P017 with valid caption bbox
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("issue_type", "caption_type"),
    [
        ("missing_terminal_punctuation", "figure"),
        ("possible_sentence_case_issue", "figure"),
        ("unexpected_terminal_period", "table"),
        ("possible_title_case_issue", "table"),
    ],
)
def test_p017_with_bbox_renders_real_highlight_and_keeps_explanation(
    app: tuple[TestClient, Any], issue_type: str, caption_type: str
) -> None:
    c, wa = app
    finding = _p017_finding(issue_type=issue_type, caption_type=caption_type, page=4)
    job_id, view = _inject_job(wa, [finding])
    fv = next(f for f in view.findings if f.rule_id == "P017")
    assert fv.has_highlight is True
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.detailed_explanation, "P017 explanation must remain non-empty"

    original_bytes = (
        Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "upload.pdf"
    ).read_bytes()
    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200
    assert "Open highlighted PDF page" in text
    # Explanation text is still rendered alongside the highlight action.
    assert fv.detailed_explanation in text

    highlighted_links = [link for link in _pdf_links(text) if "highlighted" in link]
    assert highlighted_links, "No highlighted PDF link found"
    resp = c.get(highlighted_links[0])
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content != original_bytes
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        total_annots = sum(len(list(page_obj.annots() or [])) for page_obj in doc)
    assert total_annots >= 1


# ---------------------------------------------------------------------------
# 2. P017 without bbox stays explanation-only
# ---------------------------------------------------------------------------


def test_p017_without_bbox_stays_explanation_only(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    finding = _p017_finding(bbox=None, page=4)
    job_id, view = _inject_job(wa, [finding])
    fv = next(f for f in view.findings if f.rule_id == "P017")
    assert fv.has_highlight is False
    assert fv.action_kind == "original_page"
    assert fv.action_label == "Open original PDF page"
    assert fv.bbox is None

    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200
    assert "Open highlighted PDF page" not in text
    assert "Open original PDF page" in text
    assert f"/audits/{job_id}/pdf#page=4" in text
    assert "Open first example page" not in text
    # Explanation is still present and correct.
    assert fv.detailed_explanation in text


# ---------------------------------------------------------------------------
# 3. Invalid/degenerate bbox is handled safely
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_bbox", ["0,0,0,0", "300.0,260.0,100.0,200.0", "nan,nan,nan,nan"])
def test_p017_invalid_bbox_never_produces_fake_highlight_or_crash(
    app: tuple[TestClient, Any], bad_bbox: str
) -> None:
    c, wa = app
    finding = _p017_finding(bbox=bad_bbox, page=4)
    job_id, view = _inject_job(wa, [finding])
    fv = view.findings[0]
    assert fv.has_highlight is False
    assert fv.bbox is None

    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200
    assert "Open highlighted PDF page" not in text

    # Even a manually-constructed highlight request for this job/rule must not 500.
    resp = c.get(
        f"/audits/{job_id}/pdf/highlighted", params={"page": 4, "rule_id": "P017"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


# ---------------------------------------------------------------------------
# 4. Caption privacy: no raw bbox or caption body text leaked
# ---------------------------------------------------------------------------


def test_p017_caption_privacy_no_bbox_or_body_text_leak(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    finding = _p017_finding(
        issue_type="possible_sentence_case_issue", caption_type="figure", page=4
    )
    job_id, view = _inject_job(wa, [finding])
    fv = next(f for f in view.findings if f.rule_id == "P017")
    assert fv.has_highlight is True

    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200
    # Raw stored coordinates must never reach student-facing HTML.
    assert _BBOX not in text
    assert "100.0,200.0" not in text
    assert "300.0,260.0" not in text
    # The raw line_preview (verbatim caption text) is not rendered as a distinct
    # field; only the polished/explanation text derived from it may appear.
    assert "Figure 4 some caption text without terminal punctuation" not in text
    # Location label must not contain raw coordinates.
    assert fv.location_label is None or all(
        ch not in fv.location_label for ch in ("100.0", "200.0", "300.0", "260.0")
    )


# ---------------------------------------------------------------------------
# 5. Regression: PR #327 highlight coverage (P011/P026) remains intact
# ---------------------------------------------------------------------------


def test_p011_regression_highlight_still_works_alongside_p017(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Right margin overflow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "right_margin",
                "confidence": "medium",
                "bbox": _BBOX,
            },
        ),
        _p017_finding(page=4),
    ]
    job_id, view = _inject_job(wa, findings)
    p011_fv = next(f for f in view.findings if f.rule_id == "P011")
    assert p011_fv.has_highlight is True
    assert p011_fv.action_label == "Open highlighted PDF page"

    original_bytes = (
        Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "upload.pdf"
    ).read_bytes()
    rule_html, status = _get_html(c, f"/audits/{job_id}/problems/rule/P011")
    assert status == 200
    assert "Open highlighted PDF page" in rule_html

    links = [link for link in _pdf_links(rule_html) if "highlighted" in link]
    assert links
    resp = c.get(links[0])
    assert resp.status_code == 200
    assert resp.content != original_bytes


# ---------------------------------------------------------------------------
# 6. Regression: forbidden actions never reappear
# ---------------------------------------------------------------------------


def test_forbidden_actions_never_reappear_with_p017(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        _p017_finding(page=4, bbox=_BBOX),
        _p017_finding(
            issue_type="possible_title_case_issue", caption_type="table", page=7, bbox=None
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    main_text, _ = _get_html(c, f"/audits/{job_id}")
    assert "Open PDF page" not in main_text
    assert "Open first example page" not in main_text

    for fv in view.findings:
        rule_text, status = _get_html(c, f"/audits/{job_id}/problems/rule/{fv.rule_id}")
        assert status == 200
        assert "Open PDF page" not in rule_text
        assert "Open first example page" not in rule_text


# ---------------------------------------------------------------------------
# 7. Mobile/desktop parity
# ---------------------------------------------------------------------------


def test_mobile_desktop_parity_for_p017(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        _p017_finding(page=4, bbox=_BBOX),
        _p017_finding(
            issue_type="unexpected_terminal_period", caption_type="table", page=7, bbox=None
        ),
    ]
    job_id, view = _inject_job(wa, findings)

    mobile_text, mobile_status = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop_text, desktop_status = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    assert mobile_status == 200
    assert desktop_status == 200

    assert mobile_text.count("Open highlighted PDF page") == desktop_text.count(
        "Open highlighted PDF page"
    )
    mobile_links = {link for link in _pdf_links(mobile_text) if "highlighted" in link}
    desktop_links = {link for link in _pdf_links(desktop_text) if "highlighted" in link}
    assert mobile_links == desktop_links
    assert mobile_links

    for fv in view.findings:
        assert fv.detailed_explanation in mobile_text
        assert fv.detailed_explanation in desktop_text
        if fv.location_label:
            assert fv.location_label in mobile_text
            assert fv.location_label in desktop_text


# ---------------------------------------------------------------------------
# 8. No-500 route crawl
# ---------------------------------------------------------------------------


def test_no_500_route_crawl_for_p017(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        _p017_finding(issue_type="missing_terminal_punctuation", caption_type="figure", page=4),
        _p017_finding(
            issue_type="possible_sentence_case_issue", caption_type="figure", page=5
        ),
        _p017_finding(
            issue_type="unexpected_terminal_period", caption_type="table", page=6, bbox=_BBOX
        ),
        _p017_finding(
            issue_type="possible_title_case_issue", caption_type="table", page=7, bbox=None
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "right_margin",
                "confidence": "medium",
                "bbox": _BBOX,
            },
        ),
    ]
    job_id, view = _inject_job(wa, findings)

    routes = [f"/audits/{job_id}"]
    seen_rules: set[str] = set()
    seen_categories: set[str] = set()
    seen_issue_types: set[tuple[str, str]] = set()
    for fv in view.findings:
        if fv.rule_id not in seen_rules:
            seen_rules.add(fv.rule_id)
            routes.append(f"/audits/{job_id}/problems/rule/{fv.rule_id}")
        if fv.category and fv.category not in seen_categories:
            seen_categories.add(fv.category)
            routes.append(f"/audits/{job_id}/problems/category/{_category_slug(fv.category)}")
        key = (fv.rule_id, fv.issue_type)
        if fv.issue_type and key not in seen_issue_types:
            seen_issue_types.add(key)
            routes.append(
                f"/audits/{job_id}/problems/rule/{fv.rule_id}"
                f"/issue-type/{_issue_type_slug(fv.issue_type)}"
            )
        if fv.has_highlight:
            routes.append(
                f"/audits/{job_id}/highlighted-page.pdf?page={fv.page}&rule_id={fv.rule_id}"
            )

    for route in routes:
        resp = c.get(route, headers=_DESKTOP_HEADERS)
        assert resp.status_code != 500, f"{route} returned 500"
        assert resp.status_code in (200, 404), f"{route} returned {resp.status_code}"
