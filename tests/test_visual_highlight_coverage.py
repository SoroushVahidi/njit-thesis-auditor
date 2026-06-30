"""Regression tests for expanded real-highlight coverage on visual/layout findings.

Covers the rules that gained ``details["bbox"]`` propagation beyond P012:
P011 (margins), P026 (fonts), P027 (heading levels), P020 (title capitalization),
P063 (appendix labels), P028 (page-numbering regime), P019 (inconsistent_position),
P022 (no-number page), P038 (heading_phrase_not_exact).

1. P011 margin propagation: real highlight + unchanged wording, no contradiction
2. P026 font propagation: real highlight, no body-text/coordinate leak
3. P020 / P027 / P063 propagation: real highlight, no raw bbox shown to student
4. No-geometry findings stay explanation-only (no regression for unmodified issue types)
5. Invalid/degenerate bbox is handled safely (no crash, no fake highlight)
6. P012 regression: existing highlight behavior still works alongside new rules
7. Forbidden-action regression: no "Open PDF page" / "Open first example page"
8. Actionability-wording regression: page-number exact phrases unchanged
9. Mobile/desktop parity for newly-highlightable findings
10. No-500 route crawl across main/category/rule/issue-type/highlighted-PDF routes
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
    file_name: str = "visual-highlight-coverage.pdf",
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
    links = set(re.findall(r'href="(/audits/[^"]*?/pdf(?:[/?#][^"]*)?)"', text))
    return {link.split("#")[0] for link in links}


def _category_slug(category: str) -> str:
    return str(category).strip().replace("_", "-")


def _issue_type_slug(issue_type: str) -> str:
    return str(issue_type).strip().replace("_", "-")


# ---------------------------------------------------------------------------
# 1. P011 margin propagation
# ---------------------------------------------------------------------------


def test_p011_margin_with_bbox_renders_real_highlight_and_keeps_wording(
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
                "worst_overflow_pt": "6.4",
                "affected_line_count": "3",
                "confidence": "medium",
                "bbox": _BBOX,
                "affected_line_bboxes": _BBOX,
            },
        )
    ]
    job_id, _ = _inject_job(wa, findings)
    original_bytes = (
        Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "upload.pdf"
    ).read_bytes()
    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200

    assert "page 2 appears to cross the required right margin boundary" in text
    assert "Adjust the paragraph, text wrapping, or line spacing" in text
    assert "tables, figures, long lines, indentation, headers, and footers" not in text

    # A real highlight is now offered, and it must not contradict itself.
    assert "Open highlighted PDF page" in text
    assert "No exact highlight is available for this finding." not in text

    highlighted_links = [link for link in _pdf_links(text) if "highlighted" in link]
    assert highlighted_links, "No highlighted PDF link found"
    for link in highlighted_links:
        resp = c.get(link)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content != original_bytes
        with fitz.open(stream=resp.content, filetype="pdf") as doc:
            total_annots = sum(len(list(page.annots() or [])) for page in doc)
        assert total_annots >= 1


# ---------------------------------------------------------------------------
# 2. P026 font propagation, no text/coordinate leak
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "issue_type",
    ["possible_body_font_family_issue", "possible_body_font_size_issue"],
)
def test_p026_font_with_bbox_no_text_leak(
    app: tuple[TestClient, Any], issue_type: str
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=4,
            message="Font issue.",
            details={
                "issue_type": issue_type,
                "observed_summary": "11.0pt" if "size" in issue_type else "CMR12",
                "expected": "12pt (±1pt tolerance: 11.0–13.0pt)"
                if "size" in issue_type
                else "Times New Roman or accepted equivalent",
                "affected_span_count": "7",
                "candidate_count": "9",
                "confidence": "medium",
                "bbox": _BBOX,
            },
        )
    ]
    job_id, _ = _inject_job(wa, findings)
    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200

    assert "Open highlighted PDF page" in text
    assert "No exact highlight is available for this finding." not in text
    # Raw stored coordinates must never reach student-facing HTML.
    assert _BBOX not in text
    assert "100.0,200.0" not in text

    highlighted_links = [link for link in _pdf_links(text) if "highlighted" in link]
    assert highlighted_links
    resp = c.get(highlighted_links[0])
    assert resp.status_code == 200
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        total_annots = sum(len(list(page.annots() or [])) for page in doc)
    assert total_annots >= 1


# ---------------------------------------------------------------------------
# 3. P020 / P027 / P063 propagation, no raw bbox shown
# ---------------------------------------------------------------------------


def _p027_finding() -> AuditFinding:
    return AuditFinding(
        rule_id="P027",
        severity=Severity.WARNING,
        page=5,
        message="Heading case issue.",
        details={
            "issue_type": "level2_title_case_issue",
            "inferred_level": "2",
            "heading_pattern": "2.1",
            "expected_or_reason": "Title Case; lowercase word found",
            "line_preview": "2.1 background and related work",
            "confidence": "medium",
            "bbox": _BBOX,
        },
    )


def _p020_finding() -> AuditFinding:
    return AuditFinding(
        rule_id="P020",
        severity=Severity.WARNING,
        page=6,
        message="Title capitalization issue.",
        details={
            "issue_type": "possible_title_capitalization_issue",
            "line_preview": "table 1: summary of results",
            "expected_or_reason": "first letter of 'summary' should be capitalized",
            "confidence": "medium",
            "source": "caption",
            "detection_reason": "table_caption_pattern",
            "bbox": _BBOX,
        },
    )


def _p063_finding() -> AuditFinding:
    return AuditFinding(
        rule_id="P063",
        severity=Severity.WARNING,
        page=7,
        message="Appendix letter label issue.",
        details={
            "issue_type": "single_appendix_uses_letter_label",
            "letter_found": "A",
            "appendix_count": "1",
            "source_q_rule_id": "Q058",
            "triage_tier": "medium",
            "bbox": _BBOX,
        },
    )


@pytest.mark.parametrize(
    ("build_finding", "rule_id"),
    [
        (_p027_finding, "P027"),
        (_p020_finding, "P020"),
        (_p063_finding, "P063"),
    ],
)
def test_propagated_rules_render_highlight_without_raw_bbox(
    app: tuple[TestClient, Any], build_finding: Any, rule_id: str
) -> None:
    c, wa = app
    job_id, view = _inject_job(wa, [build_finding()])
    fv = next(f for f in view.findings if f.rule_id == rule_id)
    assert fv.has_highlight is True, f"{rule_id} finding did not get a real highlight"

    main_text, main_status = _get_html(c, f"/audits/{job_id}")
    rule_text, rule_status = _get_html(c, f"/audits/{job_id}/problems/rule/{rule_id}")
    assert main_status == 200
    assert rule_status == 200

    for text in (main_text, rule_text):
        assert "Open highlighted PDF page" in text
        assert _BBOX not in text
        assert "100.0,200.0" not in text
        assert "300.0,260.0" not in text

    highlighted_links = [link for link in _pdf_links(main_text) if "highlighted" in link]
    assert highlighted_links
    resp = c.get(highlighted_links[0])
    assert resp.status_code == 200
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        total_annots = sum(len(list(page.annots() or [])) for page in doc)
    assert total_annots >= 1


# ---------------------------------------------------------------------------
# 4. No-geometry findings stay explanation-only
# ---------------------------------------------------------------------------


def test_no_geometry_findings_stay_explanation_only(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=3,
            message="Missing page number.",
            details={"issue_type": "missing_page_number"},
        ),
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            message="Required heading missing.",
            details={
                "issue_type": "required_heading_missing",
                "section_key": "acknowledgements",
                "expected_heading": "ACKNOWLEDGEMENTS",
            },
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    page_known = [fv for fv in view.findings if fv.page is not None]
    doc_level = [fv for fv in view.findings if fv.page is None]
    for fv in page_known:
        assert fv.has_highlight is False
        assert fv.action_kind == "original_page"
        assert fv.action_label == "Open original PDF page"
    for fv in doc_level:
        assert fv.has_highlight is False
        assert fv.action_kind == "explanation"
        assert fv.action_label == "Read explanation"

    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200
    assert "Open highlighted PDF page" not in text
    assert "Open original PDF page" in text
    assert "/pdf/highlighted" not in text


# ---------------------------------------------------------------------------
# 5. Invalid/degenerate bbox is handled safely
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_bbox", ["0,0,0,0", "300.0,260.0,100.0,200.0", "nan,nan,nan,nan"])
def test_invalid_bbox_never_produces_fake_highlight_or_crash(
    app: tuple[TestClient, Any], bad_bbox: str
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
                "bbox": bad_bbox,
            },
        )
    ]
    job_id, view = _inject_job(wa, findings)
    fv = view.findings[0]
    assert fv.has_highlight is False
    assert fv.bbox is None

    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200
    assert "Open highlighted PDF page" not in text
    assert "Open original PDF page" in text
    assert "No exact highlight is available" in text

    # Even a manually-constructed highlight request for this job/rule must not 500.
    resp = c.get(
        f"/audits/{job_id}/pdf/highlighted", params={"page": 2, "rule_id": "P011"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


# ---------------------------------------------------------------------------
# 6. P012 regression
# ---------------------------------------------------------------------------


def test_p012_highlight_unaffected_when_mixed_with_new_rules(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=1,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
            },
        ),
        _p027_finding(),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    p012_fv = next(f for f in view.findings if f.rule_id == "P012")
    assert p012_fv.has_highlight is True
    assert p012_fv.action_label == "Open highlighted PDF page"

    rule_html, status = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert status == 200
    assert "Open highlighted PDF page" in rule_html


# ---------------------------------------------------------------------------
# 7. Forbidden-action regression
# ---------------------------------------------------------------------------


def test_forbidden_actions_never_reappear(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        _p027_finding(),
        _p020_finding(),
        _p063_finding(),
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
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=3,
            message="Missing page number.",
            details={"issue_type": "missing_page_number"},
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
# 8. Actionability-wording regression for page-number rules with bbox
# ---------------------------------------------------------------------------


def test_page_number_wording_unchanged_when_bbox_present(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P028",
            severity=Severity.WARNING,
            page=6,
            message="Wrong style.",
            details={
                "issue_type": "arabic_number_on_frontmatter_page",
                "observed_style": "Arabic numerals",
                "expected_style": "lowercase Roman numerals",
                "bbox": _BBOX,
            },
        ),
        AuditFinding(
            rule_id="P022",
            severity=Severity.WARNING,
            page=2,
            message="Visible page number on no-number page.",
            details={
                "issue_type": "visible_page_number_on_no_number_page",
                "page_type": "abstract",
                "bbox": _BBOX,
            },
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    text, status = _get_html(c, f"/audits/{job_id}")
    assert status == 200

    # Exact phrases preserved from the pre-bbox baseline (test_page_number_actionability.py).
    assert "appears to use Arabic numerals" in text
    assert "expected to use lowercase Roman numerals" in text
    assert "suppressed or hidden" in text

    for fv in view.findings:
        assert fv.has_highlight is True
        assert fv.action_label == "Open highlighted PDF page"
    assert "Open highlighted PDF page" in text
    assert _BBOX not in text


# ---------------------------------------------------------------------------
# 9. Mobile/desktop parity
# ---------------------------------------------------------------------------


def test_mobile_desktop_parity_for_new_highlight_rules(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [_p027_finding(), _p020_finding(), _p063_finding()]
    job_id, _ = _inject_job(wa, findings)

    mobile_text, mobile_status = _get_html(
        c, f"/audits/{job_id}", headers=_MOBILE_HEADERS
    )
    desktop_text, desktop_status = _get_html(
        c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS
    )
    assert mobile_status == 200
    assert desktop_status == 200

    assert mobile_text.count("Open highlighted PDF page") == desktop_text.count(
        "Open highlighted PDF page"
    )
    mobile_links = {link for link in _pdf_links(mobile_text) if "highlighted" in link}
    desktop_links = {link for link in _pdf_links(desktop_text) if "highlighted" in link}
    assert mobile_links == desktop_links
    assert mobile_links


# ---------------------------------------------------------------------------
# 10. No-500 route crawl
# ---------------------------------------------------------------------------


def test_no_500_route_crawl_for_all_newly_highlightable_rules(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=1,
            message="Annotation.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": _BBOX,
            },
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
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "observed_summary": "CMR12",
                "confidence": "medium",
                "bbox": _BBOX,
            },
        ),
        _p027_finding(),
        _p020_finding(),
        _p063_finding(),
        AuditFinding(
            rule_id="P028",
            severity=Severity.WARNING,
            page=6,
            message="Wrong style.",
            details={
                "issue_type": "arabic_number_on_frontmatter_page",
                "observed_style": "Arabic numerals",
                "expected_style": "lowercase Roman numerals",
                "bbox": _BBOX,
            },
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=4,
            message="Inconsistent position.",
            details={
                "issue_type": "inconsistent_position",
                "expected_or_context": "dominant=bottom_center",
                "observed_location": "top center",
                "expected_position": "bottom center",
                "confidence": "medium",
                "bbox": _BBOX,
            },
        ),
        AuditFinding(
            rule_id="P022",
            severity=Severity.WARNING,
            page=2,
            message="Visible page number on no-number page.",
            details={
                "issue_type": "visible_page_number_on_no_number_page",
                "page_type": "abstract",
                "bbox": _BBOX,
            },
        ),
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            page=2,
            message="Heading phrase variant.",
            details={
                "issue_type": "heading_phrase_not_exact",
                "section_key": "acknowledgements",
                "expected_heading": "ACKNOWLEDGEMENTS",
                "observed_heading_normalized": "ACKNOWLEDGEMENT",
                "bbox": _BBOX,
            },
        ),
        # A no-geometry control finding mixed in, to confirm it never 500s either.
        AuditFinding(
            rule_id="P023",
            severity=Severity.WARNING,
            page=5,
            message="Spacing issue.",
            details={"issue_type": "possible_blank_line_issue", "confidence": "low"},
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
            routes.append(
                f"/audits/{job_id}/problems/category/{_category_slug(fv.category)}"
            )
        key = (fv.rule_id, fv.issue_type)
        if fv.issue_type and key not in seen_issue_types:
            seen_issue_types.add(key)
            routes.append(
                f"/audits/{job_id}/problems/rule/{fv.rule_id}"
                f"/issue-type/{_issue_type_slug(fv.issue_type)}"
            )
        if fv.has_highlight:
            routes.append(
                f"/audits/{job_id}/pdf/highlighted?page={fv.page}&rule_id={fv.rule_id}"
            )

    for route in routes:
        resp = c.get(route, headers=_DESKTOP_HEADERS)
        assert resp.status_code != 500, f"{route} returned 500"
        assert resp.status_code in (200, 404), f"{route} returned {resp.status_code}"
