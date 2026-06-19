"""Regression tests for actionable margin/font wording in the PDF web UI."""

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
    assert resp.status_code == 200
    return html.unescape(resp.text)


def _pdf_links(text: str) -> set[str]:
    return set(re.findall(r'href="(/audits/[^"]*?/pdf[^"]*)"', text))


def _inject_job(
    wa: Any,
    findings: list[Any],
    *,
    file_name: str = "margin-font-thesis.pdf",
    page_count: int = 6,
) -> str:
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
    return job_id


def test_margin_side_specific_wording(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Right margin overflow.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "right_margin",
                    "worst_overflow_pt": "6.4",
                    "affected_line_count": "3",
                    "confidence": "medium",
                },
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}")
    assert "Likely problem:" in text
    assert "page 2 appears to cross the required right margin boundary" in text
    assert "inside the required page margins" in text
    assert "tables, figures, long lines, indentation, headers, and footers" in text
    assert "No exact highlight is available" in text
    assert "Open the original PDF page" in text
    assert "Open PDF page" not in text
    assert "Open original PDF page" in text
    assert "Open highlighted PDF page" not in text


def test_margin_unknown_side_wording(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=3,
                message="Margin overflow.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "confidence": "medium",
                },
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}/problems/rule/P011")
    assert "could not determine the exact margin side" in text
    assert "too close to or beyond a required page margin" in text
    assert "tables, figures, long lines, indentation, headers, and footers" in text
    assert "flagged issue type" not in text


def test_font_family_wording(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=4,
                message="Font family issue.",
                details={
                    "issue_type": "possible_body_font_family_issue",
                    "observed_summary": "CMR12",
                    "expected": "Times New Roman or accepted equivalent",
                    "affected_span_count": "8",
                    "candidate_count": "10",
                    "confidence": "medium",
                },
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}")
    assert "Likely problem:" in text
    assert "font family CMR12" in text
    assert "Times New Roman or accepted equivalent" in text
    assert (
        "body-text font settings" in text
        or "body-text style" in text
        or "source document's body text style" in text
    )
    assert (
        "caption, heading, table entry, or footnote" in text
        or "a caption, a heading, table text, a footnote" in text
    )


def test_font_size_wording(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=5,
                message="Font size issue.",
                details={
                    "issue_type": "possible_body_font_size_issue",
                    "observed_summary": "11.0pt",
                    "expected": "12pt (±1pt tolerance: 11.0–13.0pt)",
                    "affected_span_count": "7",
                    "candidate_count": "9",
                    "confidence": "medium",
                },
            )
        ],
    )
    text = _get_html(client, f"/audits/{job_id}/problems/rule/P026")
    assert "font size 11.0pt" in text
    assert "12pt" in text
    assert "font size" in text
    assert "permitted exception" in text


def test_font_missing_observed_metadata_stays_honest(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=2,
                message="Font family issue.",
                details={
                    "issue_type": "possible_body_font_family_issue",
                    "confidence": "medium",
                },
            )
        ],
    )
    text = _get_html(
        client,
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    )
    assert "could not extract a precise observed font value" in text
    assert "precise observed value was unavailable" in text
    assert "font family" in text


def test_no_vague_margin_font_fallback_for_known_issue_types(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
            ),
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=3,
                message="Font issue.",
                details={
                    "issue_type": "possible_body_font_family_issue",
                    "observed_summary": "ComputerModern",
                },
            ),
        ],
    )
    for path in (
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/margin-or-overflow",
        f"/audits/{job_id}/problems/category/font-format",
        f"/audits/{job_id}/problems/rule/P011",
        f"/audits/{job_id}/problems/rule/P026",
    ):
        text = _get_html(client, path)
        lower = text.lower()
        assert "flagged issue type" not in lower
        assert "verify against njit requirements" not in lower
        assert "possible font compliance issue on page" not in lower
        assert "possible margin or overflow issue on page" not in lower


def test_no_highlight_actions_without_bbox_and_real_highlight_with_bbox(
    app: tuple[TestClient, Any],
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    no_highlight_job = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
            ),
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=3,
                message="Font issue.",
                details={"issue_type": "possible_body_font_family_issue"},
            ),
        ],
    )
    text = _get_html(client, f"/audits/{no_highlight_job}")
    assert "Open PDF page" not in text
    assert "Open highlighted PDF page" not in text
    assert "/pdf/highlighted" not in text

    highlight_job = _inject_job(
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
                    "rect": "80.0,220.0,220.0,260.0",
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
                    "rect": "110.0,260.0,280.0,300.0",
                },
            ),
        ],
        file_name="highlight-margin-font-thesis.pdf",
    )
    highlighted_text = _get_html(client, f"/audits/{highlight_job}")
    assert "Open highlighted PDF page" in highlighted_text
    links = _pdf_links(highlighted_text)
    assert links
    for link in links:
        resp = client.get(link)
        assert resp.status_code == 200
        assert resp.status_code != 500
        assert resp.headers["content-type"].startswith("application/pdf")


def test_margin_font_wording_consistent_across_pages(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={
                    "issue_type": "margin_boundary_violation",
                    "side": "bottom_margin",
                    "worst_overflow_pt": "9.1",
                },
            ),
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=4,
                message="Font issue.",
                details={
                    "issue_type": "possible_body_font_family_issue",
                    "observed_summary": "CMR12",
                },
            ),
        ],
    )
    paths = (
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/margin-or-overflow",
        f"/audits/{job_id}/problems/category/font-format",
        f"/audits/{job_id}/problems/rule/P011",
        f"/audits/{job_id}/problems/rule/P026",
        f"/audits/{job_id}/problems/rule/P011/issue-type/margin-boundary-violation",
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    )
    for path in paths:
        text = _get_html(client, path)
        if "P011" in path or "margin-or-overflow" in path or path.endswith(job_id):
            assert "bottom margin" in text
            assert "inside the required page margins" in text
        if "P026" in path or "font-format" in path or path.endswith(job_id):
            assert "font family CMR12" in text
            assert "Times New Roman" in text


def test_margin_font_mobile_desktop_parity(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
        wa,
        [
            AuditFinding(
                rule_id="P011",
                severity=Severity.WARNING,
                page=2,
                message="Margin issue.",
                details={"issue_type": "margin_boundary_violation", "side": "right_margin"},
            ),
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=3,
                message="Font issue.",
                details={
                    "issue_type": "possible_body_font_size_issue",
                    "observed_summary": "10.5pt",
                },
            ),
        ],
    )
    mobile = _get_html(client, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop = _get_html(client, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    for fragment in (
        "right margin",
        "font size 10.5pt",
        "No exact highlight is available",
        "Problems found",
    ):
        assert fragment in mobile
        assert fragment in desktop
    assert _pdf_links(mobile) == _pdf_links(desktop)


def test_margin_font_route_crawl_has_no_500s(app: tuple[TestClient, Any]) -> None:
    from njit_auditor.models import AuditFinding, Severity

    client, wa = app
    job_id = _inject_job(
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
                    "rect": "90.0,220.0,230.0,265.0",
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
                    "rect": "120.0,260.0,300.0,305.0",
                },
            ),
        ],
        file_name="crawl-margin-font-thesis.pdf",
    )
    routes = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/margin-or-overflow",
        f"/audits/{job_id}/problems/category/font-format",
        f"/audits/{job_id}/problems/rule/P011",
        f"/audits/{job_id}/problems/rule/P026",
        f"/audits/{job_id}/problems/rule/P011/issue-type/margin-boundary-violation",
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    ]
    pdf_links: set[str] = set()
    for route in routes:
        text = _get_html(client, route)
        pdf_links.update(_pdf_links(text))
    for route in routes:
        resp = client.get(route, headers=_DESKTOP_HEADERS)
        assert resp.status_code == 200
        assert resp.status_code != 500
    assert pdf_links
    for link in pdf_links:
        resp = client.get(link, headers=_DESKTOP_HEADERS)
        assert resp.status_code == 200
        assert resp.status_code != 500
