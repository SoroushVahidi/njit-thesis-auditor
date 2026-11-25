"""Regression tests for student-facing highlighted/original PDF page routes.

Covers the production failure where iPhone Safari downloaded a 25-byte JSON file
named ``highlighted-page.json`` containing ``{"error":"not available"}`` instead
of a valid single-page PDF.
"""
from __future__ import annotations

import html
import json
import os
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from pdf_link_helpers import extract_audit_pdf_links

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_highlight import get_pdf_page_sizes
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict
from njit_auditor.rules.pdf_toc_terminal_period import check_pdf_toc_terminal_period
from njit_auditor.web_samples import get_builtin_sample

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


def _bbox_finding(*, page: int, x0: float = 100.0) -> AuditFinding:
    return AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message=f"Margin overflow on page {page}.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "worst_overflow_pt": "6.0",
            "affected_line_count": "1",
            "confidence": "medium",
            "bbox": f"{x0},200.0,{x0 + 50.0},230.0",
        },
    )


def _page_only_finding(page: int) -> AuditFinding:
    return AuditFinding(
        rule_id="P013",
        severity=Severity.WARNING,
        page=page,
        message=f"Page number issue on page {page}.",
        details={
            "issue_type": "page_number_candidate",
            "position_type": "bottom_center",
            "confidence": "medium",
        },
    )


def _document_level_finding() -> AuditFinding:
    return AuditFinding(
        rule_id="P013",
        severity=Severity.WARNING,
        page=None,
        message="Document-level page numbering overview.",
        details={
            "issue_type": "p013_document_overview",
            "confidence": "medium",
        },
    )


def _inject_job(
    wa: Any, findings: list[AuditFinding], *, page_count: int = 10, source: Path | None = None
) -> str:
    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    if source is None:
        _write_real_pdf(jdir / "upload.pdf", page_count=page_count)
    else:
        shutil.copyfile(source, jdir / "upload.pdf")

    metadata = {"input_file_name": "route-check.pdf", "audit_type": "pdf", "job_id": job_id}
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
        file_name="route-check.pdf",
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
                "problem_number": fv.problem_number,
                "problem_anchor": fv.problem_anchor,
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
        grouped_summary=[],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
    )
    wa._set_job(job)
    return job_id


def _assert_valid_pdf_response(resp: Any) -> None:
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert "inline" in resp.headers.get("content-disposition", "").lower()
    assert resp.content[:4] == b"%PDF"


def _assert_not_json_error(resp: Any) -> None:
    assert "json" not in resp.headers.get("content-type", "").lower()
    assert b'"error":"not available"' not in resp.content


def test_highlighted_finding_returns_application_pdf(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_bbox_finding(page=2)])
    text = html.unescape(c.get(f"/audits/{job_id}").text)
    link = next(link for link in extract_audit_pdf_links(text) if "highlighted-page" in link)
    resp = c.get(link, headers=_MOBILE_HEADERS)
    _assert_not_json_error(resp)
    _assert_valid_pdf_response(resp)


@pytest.mark.parametrize("has_period", [False, True])
def test_p054_renders_only_the_period_before_a_corroborated_leader_grid(
    app: tuple[TestClient, Any], tmp_path: Path, has_period: bool
) -> None:
    client, wa = app
    source = tmp_path / "synthetic-toc.pdf"
    title = "1 RESULTS FROM EXPERIMENTAL MEASUREMENTS" + ("." if has_period else "")
    title_size, clearance = (8, 0.88) if has_period else (12, 0.04)
    first_dot_x = 108 + fitz.get_text_length(title, fontname="tiro", fontsize=title_size)
    first_dot_x += clearance
    with fitz.open() as doc:
        doc.new_page()
        page = doc.new_page(width=612, height=792)
        page.insert_text((220, 85), "TABLE OF CONTENTS", fontname="tibo", fontsize=14)
        for row in range(5):
            y = 132 + row * 24
            label = f"{row + 1} Study of sample {row}" if row else title
            size = 12 if row else title_size
            page.insert_text((108, y), label, fontname="tiro", fontsize=size)
            for cell in range(4):
                page.insert_text((first_dot_x + 12 * cell, y), ".", fontname="tiro", fontsize=size)
            page.insert_text((528, y), str(11 * (row + 1)), fontname="tiro", fontsize=12)
        doc.save(source)
        row_dots = sorted(
            tuple(char["bbox"])
            for block in page.get_text("rawdict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
            for char in span["chars"]
            if char["c"] == "." and char["origin"][1] == 132
        )
    assert len(row_dots) == (5 if has_period else 4)

    findings = check_pdf_toc_terminal_period(load_pdf_layout(str(source)))
    assert len(findings) == int(has_period)
    job_id = _inject_job(wa, findings, source=source)
    audit = f"/audits/{job_id}"
    result = client.get(audit)
    assert result.status_code == 200
    finding_links = extract_audit_pdf_links(html.unescape(result.text))
    complete = client.get(f"{audit}/download/student-report.pdf")
    assert complete.status_code == 200
    assert complete.headers["content-type"].startswith("application/pdf")
    with fitz.open(stream=complete.content, filetype="pdf") as doc:
        assert doc.page_count > 2
        complete_marks = [tuple(mark.rect) for mark in doc[1].annots()]
        assert len(complete_marks) == int(has_period)
        assert not list(doc[0].annots())
    if not has_period:
        assert not any("P054" in link for link in finding_links)
        return

    period, first_leader = row_dots[:2]
    bbox = tuple(float(v) for v in findings[0].details["bbox"].split(","))
    assert 0 < first_leader[0] - bbox[2] < 1
    assert bbox[0] == pytest.approx(period[0], abs=0.05)
    assert bbox[2] == pytest.approx(period[2], abs=0.05)
    link = next(link for link in finding_links if "highlighted-page.pdf" in link and "P054" in link)
    focused = client.get(link)
    legacy = client.get(f"{audit}/pdf/highlighted", params={"page": 2, "rule_id": "P054"})
    for response, page_index, page_count in ((focused, 0, 1), (legacy, 1, 2)):
        _assert_valid_pdf_response(response)
        with fitz.open(stream=response.content, filetype="pdf") as doc:
            assert doc.page_count == page_count
            assert [tuple(mark.rect) for mark in doc[page_index].annots()] == complete_marks
    mark, = complete_marks
    assert mark == pytest.approx((bbox[0] - 1, bbox[1] - 1, bbox[2], bbox[3] + 1), abs=0.01)
    assert mark[2] < first_leader[0]


def test_page_only_finding_returns_original_single_page_pdf(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    finding = AuditFinding(
        rule_id="P026",
        severity=Severity.WARNING,
        page=3,
        message="Font issue on page 3.",
        details={
            "issue_type": "possible_body_font_family_issue",
            "confidence": "medium",
        },
    )
    job_id = _inject_job(wa, [finding])
    text = html.unescape(c.get(f"/audits/{job_id}").text)
    links = list(
        dict.fromkeys(
            link for link in extract_audit_pdf_links(text) if "highlighted-page" in link
        )
    )
    assert len(links) == 1
    resp = c.get(links[0])
    _assert_valid_pdf_response(resp)
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        assert doc.page_count == 1
        assert len(list(doc[0].annots() or [])) == 0


def test_p046_highlight_uses_continued_figure_list_page_in_both_pdf_routes(
    app: tuple[TestClient, Any],
) -> None:
    client, web = app
    target_text = "Figure 4 Synthetic layout comparison."
    with fitz.open() as source:
        for number in (1, 2):
            page = source.new_page(width=612, height=792)
            heading = "LIST OF FIGURES" if number == 1 else "LIST OF FIGURES (continued)"
            page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
            page.insert_text((108, 115), "Figure")
            page.insert_text((500, 115), "Page")
            page.insert_text((108, 140), f"Figure {number * 2 - 1} Synthetic example.")
            page.insert_text((503, 140), "12")
            page.insert_text(
                (145 if number == 2 else 108, 207),
                target_text if number == 2 else "Figure 2 Synthetic example.",
            )
            page.insert_text((503, 207), "13")
        target_row, = source[1].search_for(target_text)
        pdf = source.tobytes()

    response = client.post(
        "/audits", files={"file": ("synthetic.pdf", pdf, "application/pdf")}, follow_redirects=False
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert client.get(location + "/status").json()["state"] == "complete"
    job = web._get_job(location.rsplit("/", 1)[1])
    card, = [card for card in job.findings if card["rule_id"] == "P046"]
    assert card["issue_type"] == "lof_entry_number_column_misaligned"
    assert card["page"] == 2
    assert card["has_highlight"]
    assert "List of Figures entry 2" in card["location_label"]
    row_index = int(card["finding_id"][1:])
    rows = client.get(location + "/download/json").json()["findings"]
    row = rows[row_index]
    assert (row["rule_id"], row["page"], row["problem_number"]) == (
        "P046", 2, card["problem_number"]
    )
    source_bbox = tuple(float(part) for part in row["details"]["bbox"].split(","))
    assert source_bbox[0] == pytest.approx(target_row.x0, abs=0.06)
    assert source_bbox[1::2] == pytest.approx((target_row.y0, target_row.y1), abs=0.06)

    job_html = html.unescape(client.get(location).text)
    link = next(
        href for href in extract_audit_pdf_links(job_html)
        if f"finding_id={card['finding_id']}" in href
    )
    assert "page=2" in link
    single = client.get(link)
    complete = client.get(location + "/download/student-report.pdf")
    _assert_valid_pdf_response(single)
    assert complete.status_code == 200
    with fitz.open(stream=single.content) as doc:
        assert doc.page_count == 1
        source_page = doc[0]
        assert target_text in source_page.get_text()
        mark, = source_page.annots()
        rect = tuple(mark.rect)
        assert fitz.Rect(target_row) in fitz.Rect(*rect)
    with fitz.open(stream=complete.content) as doc:
        assert doc.page_count > 2
        first_page, continued_page = doc[0], doc[1]
        assert rect in [tuple(mark.rect) for mark in continued_page.annots()]
        assert rect not in [tuple(mark.rect) for mark in first_page.annots()]


@pytest.mark.parametrize("bbox", [None, "0,0,0,0", "900,900,910,910"])
def test_p046_without_drawable_location_keeps_both_pdfs_unmarked(
    app: tuple[TestClient, Any], bbox: str | None
) -> None:
    client, web = app
    details = {"issue_type": "lof_entry_number_column_misaligned"}
    if bbox is not None:
        details["bbox"] = bbox
    finding = AuditFinding(
        rule_id="P046", severity=Severity.WARNING, page=2, message="Synthetic list alignment.",
        details=details,
    )
    job_id = _inject_job(web, [finding], page_count=3)
    card, = web._get_job(job_id).findings
    assert not card["has_highlight"]
    location = f"/audits/{job_id}"
    single = client.get(location + "/highlighted-page.pdf", params={"page": 2, "finding_id": "f0"})
    complete = client.get(location + "/download/student-report.pdf")
    _assert_valid_pdf_response(single)
    assert complete.status_code == 200
    with fitz.open(stream=single.content) as doc:
        assert doc.page_count == 1
        assert "Synthetic thesis page 2" in doc[0].get_text()
        assert not list(doc[0].annots())
    with fitz.open(stream=complete.content) as doc:
        assert doc.page_count > 3
        assert not any(list(page.annots()) for page in doc)


def test_p046_relocation_preserves_json_indexes_and_page_ordered_problem_numbers(
    tmp_path: Path,
) -> None:
    legacy = AuditFinding(
        rule_id="P046", severity=Severity.WARNING, page=1, message="Synthetic list alignment.",
        details={"issue_type": "lof_entry_number_column_misaligned"},
    )
    relocated = legacy.model_copy(update={
        "page": 3,
        "details": {**legacy.details, "list_start_page": "1", "bbox": "120,150,300,162"},
    })
    unrelated = _bbox_finding(page=2)
    metadata = {"audit_type": "pdf"}
    before = audit_findings_to_json_dict([legacy, unrelated], metadata)["findings"]
    after = audit_findings_to_json_dict([relocated, unrelated], metadata)["findings"]
    assert [row["rule_id"] for row in after] == [row["rule_id"] for row in before]
    assert [(row["page"], row["problem_number"]) for row in after] == [(3, 2), (2, 1)]
    view = build_report_view({"findings": after, "metadata": metadata})
    assert [(f.finding_id, f.page, f.problem_number) for f in view.findings] == [
        ("f1", 2, 1), ("f0", 3, 2)
    ]
    md = tmp_path / "report.md"
    write_markdown_report([relocated, unrelated], metadata, md)
    assert re.findall(r"^### Problem (\d+)", md.read_text(), flags=re.M) == ["1", "2"]


def test_document_level_finding_renders_no_highlight_button(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_document_level_finding()])
    text = html.unescape(c.get(f"/audits/{job_id}").text)
    assert "Open highlighted PDF page" not in text
    assert "Open original PDF page" not in text
    assert "highlighted-page.pdf" not in text


def test_expired_job_returns_html_not_json(app: tuple[TestClient, Any]) -> None:
    c, _wa = app
    resp = c.get(
        "/audits/missing-job-id/highlighted-page.pdf",
        params={"page": 1, "rule_id": "P011"},
        headers=_MOBILE_HEADERS,
    )
    assert resp.status_code == 404
    assert "text/html" in resp.headers.get("content-type", "")
    _assert_not_json_error(resp)
    assert b"expired" in resp.content.lower() or b"upload" in resp.content.lower()


def test_exact_production_json_failure_shape_never_returned(app: tuple[TestClient, Any]) -> None:
    """Regression for the 25-byte ``highlighted-page.json`` Safari download."""
    c, _wa = app
    for path in (
        "/audits/expired-job/highlighted-page.pdf?page=1",
        "/audits/expired-job/highlighted-page.pdf",
    ):
        resp = c.get(path, headers=_MOBILE_HEADERS)
        assert resp.content != b'{"error":"not available"}'
        assert "application/json" not in resp.headers.get("content-type", "")


def test_stale_finding_id_falls_back_to_page_pdf(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_bbox_finding(page=4)])
    resp = c.get(
        f"/audits/{job_id}/highlighted-page.pdf",
        params={
            "page": 4,
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "finding_id": "f99999",
        },
        headers=_MOBILE_HEADERS,
    )
    _assert_not_json_error(resp)
    _assert_valid_pdf_response(resp)


def test_page_order_and_topic_links_share_finding_id(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_bbox_finding(page=2, x0=120.0), _bbox_finding(page=7, x0=220.0)])
    page_text = html.unescape(c.get(f"/audits/{job_id}?sort=page").text)
    topic_text = html.unescape(c.get(f"/audits/{job_id}?sort=topic").text)
    page_ids = re.findall(r"finding_id=(f\d+)", page_text)
    topic_ids = re.findall(r"finding_id=(f\d+)", topic_text)
    assert page_ids
    assert set(page_ids) == set(topic_ids)


def test_sorting_does_not_change_highlight_target(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [_bbox_finding(page=9, x0=100.0), _bbox_finding(page=1, x0=300.0)]
    job_id = _inject_job(wa, findings)
    text = html.unescape(c.get(f"/audits/{job_id}?sort=page").text)
    page_one_link = next(
        link
        for link in extract_audit_pdf_links(text)
        if "page=1" in link and "highlighted-page" in link
    )
    resp = c.get(page_one_link)
    _assert_valid_pdf_response(resp)
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        assert list(doc[0].annots() or []), "Page 1 card must highlight page 1, not page 9"


def test_grouped_display_preserves_finding_id(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_bbox_finding(page=5, x0=100.0), _bbox_finding(page=5, x0=200.0)])
    text = html.unescape(c.get(f"/audits/{job_id}").text)
    ids = re.findall(r"finding_id=(f\d+)", text)
    assert len(set(ids)) >= 1
    for link in extract_audit_pdf_links(text):
        if "highlighted-page" not in link:
            continue
        resp = c.get(link)
        _assert_not_json_error(resp)
        _assert_valid_pdf_response(resp)


def test_invalid_bbox_triggers_fallback_not_json(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    finding = AuditFinding(
        rule_id="P012",
        severity=Severity.WARNING,
        page=2,
        message="Annotation detected.",
        details={
            "issue_type": "pdf_annotation_detected",
            "annotation_type": "Text",
            "bbox": "0,0,0,0",
        },
    )
    job_id = _inject_job(wa, [finding])
    resp = c.get(
        f"/audits/{job_id}/highlighted-page.pdf",
        params={"page": 2, "rule_id": "P012", "issue_type": "pdf_annotation_detected"},
    )
    _assert_not_json_error(resp)
    _assert_valid_pdf_response(resp)


def test_mobile_user_agent_receives_same_pdf(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_bbox_finding(page=3)])
    url = (
        f"/audits/{job_id}/highlighted-page.pdf"
        "?page=3&rule_id=P011&issue_type=margin_boundary_violation"
    )
    desktop = c.get(url, headers=_DESKTOP_HEADERS)
    mobile = c.get(url, headers=_MOBILE_HEADERS)
    _assert_valid_pdf_response(desktop)
    _assert_valid_pdf_response(mobile)
    assert desktop.content[:32] == mobile.content[:32]


def test_out_of_range_page_returns_html_not_json(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_bbox_finding(page=2)], page_count=3)
    resp = c.get(
        f"/audits/{job_id}/highlighted-page.pdf",
        params={"page": 99999, "rule_id": "P011"},
        headers=_MOBILE_HEADERS,
    )
    assert resp.status_code == 404
    assert "text/html" in resp.headers.get("content-type", "")
    _assert_not_json_error(resp)


@pytest.mark.parametrize("sample_id", ["ester_sample_a", "ester_sample_b"])
def test_sample_audit_pdf_links_never_return_json(
    app: tuple[TestClient, Any], sample_id: str
) -> None:
    c, _wa = app
    sample = get_builtin_sample(sample_id)
    if not sample.abs_path.exists():
        pytest.skip(f"{sample_id} PDF not available locally")

    start = c.post("/audits",
                   files={"file": ("sample.pdf", sample.abs_path.read_bytes(), "application/pdf")},
                   follow_redirects=False)
    assert start.status_code in (302, 303)
    job_id = start.headers["location"].rstrip("/").split("/")[-1]

    for _ in range(120):
        status = c.get(f"/audits/{job_id}/status").json()
        if status["state"] == "complete":
            break

    text = html.unescape(c.get(f"/audits/{job_id}").text)
    links = list(dict.fromkeys(extract_audit_pdf_links(text)))
    pdf_links = [link for link in links if "highlighted-page" in link]
    assert pdf_links, f"No highlighted-page links rendered for {sample_id}"

    for link in pdf_links:
        for headers in (_DESKTOP_HEADERS, _MOBILE_HEADERS):
            resp = c.get(link, headers=headers)
            _assert_not_json_error(resp)
            _assert_valid_pdf_response(resp)
