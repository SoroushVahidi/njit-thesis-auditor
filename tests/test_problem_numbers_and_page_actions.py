"""Regression tests for problem numbering and original-page PDF actions."""

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

_P017_BBOX = "120.0,220.0,360.0,270.0"
_P012_RECT = "100.0,180.0,260.0,240.0"
_PRIVATE_CAPTION_SNIPPET = "VERY PRIVATE BODY SNIPPET 12345"


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


def _pdf_page_rgb_bytes_from_bytes(pdf_bytes: bytes, page_index: int) -> bytes:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        pixmap = doc[page_index].get_pixmap(alpha=False)
        return bytes(pixmap.samples)


def _pdf_page_rgb_bytes_from_path(pdf_path: Path, page_index: int) -> bytes:
    with fitz.open(pdf_path) as doc:
        pixmap = doc[page_index].get_pixmap(alpha=False)
        return bytes(pixmap.samples)


def _base_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": _P012_RECT,
            },
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=4,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P022",
            severity=Severity.WARNING,
            page=5,
            message="Visible page number on no-number page.",
            details={
                "issue_type": "visible_page_number_on_no_number_page",
                "page_type": "list_of_figures",
            },
        ),
        AuditFinding(
            rule_id="P025",
            severity=Severity.WARNING,
            page=None,
            message="Front matter ordering may be incorrect.",
            details={"issue_type": "possible_frontmatter_order_issue"},
        ),
        AuditFinding(
            rule_id="P017",
            severity=Severity.WARNING,
            page=6,
            message="Figure caption appears to be missing terminal punctuation.",
            details={
                "page_number": "6",
                "caption_type": "figure",
                "issue_type": "missing_terminal_punctuation",
                "line_preview": f"Figure 6 { _PRIVATE_CAPTION_SNIPPET }",
                "confidence": "high",
                "bbox": _P017_BBOX,
            },
        ),
    ]


def _inject_job(
    wa: Any,
    findings: list[AuditFinding] | None = None,
    *,
    file_name: str = "problem-numbering.pdf",
    page_count: int = 8,
) -> tuple[str, Any]:
    findings = findings or _base_findings()
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
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "page": finding.page,
                "problem_number": finding.problem_number,
                "problem_anchor": finding.problem_anchor,
                "issue_type": finding.issue_type,
                "category": finding.category,
                "polished_comment": finding.polished_comment,
                "suggested_fix": finding.suggested_fix,
                "triage_tier": finding.triage_tier,
                "confidence": finding.confidence,
                "source_file": finding.source_file,
                "source_line": finding.source_line,
                "location_label": finding.location_label,
                "bbox": list(finding.bbox) if finding.bbox else None,
                "action_kind": finding.action_kind,
                "action_label": finding.action_label,
                "has_highlight": finding.has_highlight,
                "no_highlight_reason": finding.no_highlight_reason,
                "detailed_explanation": finding.detailed_explanation,
                "issue_type_label": finding.issue_type_label,
                "issue_type_explanation": finding.issue_type_explanation,
            }
            for finding in view.findings
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
) -> str:
    resp = client.get(path, headers=headers or _DESKTOP_HEADERS)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return html.unescape(resp.text)


def _problem_numbers(text: str) -> list[int]:
    return [int(number) for number in re.findall(r"Problem (\d+)", text)]


def _pdf_links(text: str) -> set[str]:
    links = set(
        re.findall(
            r'href="(/audits/[^"]*?(?:/highlighted-page\.pdf|/highlighted\.pdf|/pdf)(?:[/?#][^"]*)?)"',
            text,
        )
    )
    return {html.unescape(link) for link in links}


def test_problem_numbering_is_consecutive_and_skips_suppressed_candidates(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id, view = _inject_job(wa)
    assert [finding.problem_number for finding in view.findings] == [1, 2, 3, 4, 5]
    assert len(view.inventory_findings) == 1

    payload = json.loads(
        (
            Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "report.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["metadata"]["visible_problem_count"] == 5
    assert [finding["problem_number"] for finding in payload["findings"]] == [1, None, 2, 3, 4, 5]

    page_html = _get_html(c, f"/audits/{job_id}")
    for number in range(1, 6):
        assert f"Problem {number}" in page_html


def test_problem_number_is_consistent_across_pages_and_reports(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id, view = _inject_job(wa)
    payload = json.loads(
        (
            Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "report.json"
        ).read_text(encoding="utf-8")
    )
    p017_entry = next(
        finding
        for finding in payload["findings"]
        if finding["rule_id"] == "P017"
        and finding["details"].get("issue_type") == "missing_terminal_punctuation"
    )
    problem_number = int(p017_entry["problem_number"])
    p017_view = next(
        finding
        for finding in view.findings
        if finding.rule_id == "P017"
        and finding.issue_type == "missing_terminal_punctuation"
    )
    category_slug = p017_view.category.replace("_", "-")
    markdown = (
        Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "report.md"
    ).read_text(encoding="utf-8")

    for path in (
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/{category_slug}",
        f"/audits/{job_id}/problems/rule/P017",
        f"/audits/{job_id}/problems/rule/P017/issue-type/missing-terminal-punctuation",
    ):
        text = _get_html(c, path)
        assert f"Problem {problem_number}" in text
        assert f'problem-{problem_number}' in text

    assert f"### Problem {problem_number} —" in markdown


def test_highlighted_and_original_page_actions_are_distinct(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id, _ = _inject_job(wa)
    original_bytes = (
        Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "upload.pdf"
    ).read_bytes()

    main_html = _get_html(c, f"/audits/{job_id}")
    assert "Open highlighted PDF page" in main_html
    assert "Open original PDF page" in main_html

    highlight_resp = c.get(
        f"/audits/{job_id}/highlighted-page.pdf",
        params={"page": 2, "rule_id": "P012", "issue_type": "pdf_annotation_detected"},
    )
    assert highlight_resp.status_code == 200
    assert highlight_resp.content != original_bytes
    with fitz.open(stream=highlight_resp.content, filetype="pdf") as doc:
        assert doc.page_count == 1
        drawing_count = len(doc[0].get_drawings())
        annot_count = len(list(doc[0].annots() or []))
    assert drawing_count >= 1
    assert annot_count == 0
    upload_path = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "upload.pdf"
    assert _pdf_page_rgb_bytes_from_bytes(
        highlight_resp.content,
        0,
    ) != _pdf_page_rgb_bytes_from_path(upload_path, 1)

    p026_rule_html = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    assert "Open original PDF page" in p026_rule_html
    assert "Open highlighted PDF page" not in p026_rule_html
    assert f"/audits/{job_id}/pdf#page=4" in p026_rule_html
    assert "/highlighted-page.pdf" not in p026_rule_html
    original_resp = c.get(f"/audits/{job_id}/pdf")
    assert original_resp.status_code == 200
    assert original_resp.headers["content-type"].startswith("application/pdf")


def test_no_page_findings_have_no_pdf_action(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id, _ = _inject_job(wa)
    p025_html = _get_html(c, f"/audits/{job_id}/problems/rule/P025")
    assert "Open highlighted PDF page" not in p025_html
    assert "Open original PDF page" not in p025_html
    assert "What does this mean?" in p025_html


def test_no_highlight_explanation_is_specific_and_privacy_safe(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id, _ = _inject_job(wa)
    p022_html = _get_html(c, f"/audits/{job_id}/problems/rule/P022")
    assert "No exact highlight is available" in p022_html
    assert "page 5" in p022_html.lower()
    assert "list of figures" in p022_html.lower()
    assert "Open the original PDF page" in p022_html
    assert _P017_BBOX not in p022_html
    assert _PRIVATE_CAPTION_SNIPPET not in p022_html
    assert "\\chapter{" not in p022_html


def test_forbidden_labels_do_not_reappear(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id, _ = _inject_job(wa)
    text = _get_html(c, f"/audits/{job_id}")
    assert "Open PDF page" not in text
    assert "Open first example page" not in text
    assert ">Open PDF<" not in text


def test_mobile_desktop_parity_for_problem_numbers_and_actions(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id, _ = _inject_job(wa)

    desktop = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    mobile = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)

    assert _problem_numbers(desktop) == _problem_numbers(mobile)
    assert desktop.count("Open highlighted PDF page") == mobile.count("Open highlighted PDF page")
    assert desktop.count("Open original PDF page") == mobile.count("Open original PDF page")
    assert _pdf_links(desktop) == _pdf_links(mobile)


def test_problem_routes_and_downloads_do_not_500(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id, view = _inject_job(wa)
    p017_category = next(
        finding.category.replace("_", "-")
        for finding in view.findings
        if finding.rule_id == "P017"
    )
    routes = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/{p017_category}",
        f"/audits/{job_id}/problems/rule/P017",
        f"/audits/{job_id}/problems/rule/P017/issue-type/missing-terminal-punctuation",
        f"/audits/{job_id}/pdf",
        f"/audits/{job_id}/highlighted-page.pdf?page=2&rule_id=P012&issue_type=pdf_annotation_detected",
        f"/audits/{job_id}/download/json",
        f"/audits/{job_id}/download/markdown",
    ]
    for route in routes:
        resp = c.get(route)
        assert resp.status_code != 500, route
        assert resp.status_code == 200, route
