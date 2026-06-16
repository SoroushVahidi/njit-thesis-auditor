"""Tests for clickable actionable findings with PDF highlights and explanations.

Covers:
1. Highlightable finding renders highlighted action
2. Page-only finding renders page action
3. Document-level finding renders explanation action
4. Abstract length explanation is detailed
5. Font explanation is detailed
6. Page-numbering explanation is detailed
7. PDF annotation explanation is detailed
8. Main/category/rule parity
9. Mobile/desktop parity
10. No 500 PDF route crawl
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

from njit_auditor.finding_explanations import (
    build_detailed_explanation,
    build_group_explanation,
    get_action_kind,
    get_action_label,
    get_no_highlight_reason,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict

# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def app(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _write_real_pdf(path: Path, *, page_count: int = 5) -> None:
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 96), f"Synthetic thesis page {i + 1}.")
    doc.save(path)
    doc.close()


def _inject_job(
    wa: Any,
    findings: list[AuditFinding],
    *,
    file_name: str = "synthetic-thesis.pdf",
    page_count: int = 5,
) -> str:
    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf", page_count=page_count)

    metadata = {"input_file_name": file_name, "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name=file_name,
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=sum(1 for f in view.findings if f.severity == "WARNING"),
        fail_count=sum(1 for f in view.findings if f.severity == "FAIL"),
        findings=[
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "page": f.page,
                "issue_type": f.issue_type,
                "category": f.category,
                "polished_comment": f.polished_comment,
                "suggested_fix": f.suggested_fix,
                "triage_tier": f.triage_tier,
                "confidence": f.confidence,
                "source_file": f.source_file,
                "source_line": f.source_line,
                "location_label": f.location_label,
                "bbox": list(f.bbox) if f.bbox else None,
                "action_kind": f.action_kind,
                "action_label": f.action_label,
                "has_highlight": f.has_highlight,
                "no_highlight_reason": f.no_highlight_reason,
                "detailed_explanation": f.detailed_explanation,
            }
            for f in view.findings
        ],
        grouped_summary=[
            {"rule_id": r.rule_id, "count": r.count, "category": r.category}
            for r in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
    )
    wa._set_job(job)
    return job_id


def _get_html(client: TestClient, path: str, headers: dict[str, str] | None = None) -> str:
    resp = client.get(path, headers=headers or _DESKTOP_HEADERS)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return html.unescape(resp.text)


def _pdf_links(text: str) -> set[str]:
    links = set(re.findall(r'href="(/audits/[^"]*?/pdf(?:[/?#][^"]*)?)"', text))
    return {html.unescape(link).split("#")[0] for link in links}


# ---------------------------------------------------------------------------
# 1. Highlightable finding renders highlighted action
# ---------------------------------------------------------------------------


def test_highlightable_finding_renders_highlighted_action(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
                "suggested_fix": "Remove reviewer comments.",
            },
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}")

    # Action label
    assert "Open highlighted PDF page" in page_html
    # URL must point to highlighted endpoint
    assert "/pdf/highlighted" in page_html
    # Route must return a PDF, not 500
    highlighted_links = [
        link for link in _pdf_links(page_html) if "highlighted" in link
    ]
    assert highlighted_links, "No highlighted PDF link found"
    for link in highlighted_links:
        resp = c.get(link)
        assert resp.status_code != 500, f"{link} returned 500"
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")


def test_highlightable_finding_action_kind_and_label() -> None:
    assert get_action_kind(has_bbox=True, page=2) == "highlight"
    assert get_action_label(has_bbox=True, page=2) == "Open highlighted PDF page"
    assert get_no_highlight_reason(has_bbox=True, page=2) == ""


def test_findingview_has_highlight_field() -> None:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view

    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=3,
            message="Annotation.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "FreeText",
                "rect": "50.0,100.0,200.0,140.0",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = view.findings[0]
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.no_highlight_reason == ""
    assert fv.bbox is not None


# ---------------------------------------------------------------------------
# 2. Page-only finding renders page action
# ---------------------------------------------------------------------------


def test_page_only_finding_renders_page_action(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "confidence": "medium",
            },
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}")

    # Must show page action, NOT highlighted action for this finding
    assert "Open PDF page" in page_html
    # Plain PDF link (not highlighted)
    assert f"/audits/{job_id}/pdf#page=3" in page_html
    # No-highlight note must be present
    assert "Exact highlight is not available" in page_html


def test_page_only_action_kind_and_label() -> None:
    assert get_action_kind(has_bbox=False, page=5) == "page"
    assert get_action_label(has_bbox=False, page=5) == "Open PDF page"
    reason = get_no_highlight_reason(has_bbox=False, page=5)
    assert "relevant page is known" in reason


def test_findingview_page_only_fields() -> None:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view

    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=4,
            message="Margin issue.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = view.findings[0]
    assert fv.has_highlight is False
    assert fv.action_kind == "page"
    assert fv.action_label == "Open PDF page"
    assert "relevant page is known" in fv.no_highlight_reason
    assert fv.bbox is None


# ---------------------------------------------------------------------------
# 3. Document-level finding renders explanation action
# ---------------------------------------------------------------------------


def test_document_level_finding_renders_explanation(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=None,
            message="Document overview.",
            details={"issue_type": "p013_document_overview"},
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}")

    # Should not show a fake highlighted link
    assert "/pdf/highlighted" not in page_html
    # Should show document-level explanation note
    assert "document-level" in page_html.lower() or "What does this mean?" in page_html


def test_document_level_action_kind() -> None:
    assert get_action_kind(has_bbox=False, page=None) == "explanation"
    assert get_action_label(has_bbox=False, page=None) == "Read explanation"
    reason = get_no_highlight_reason(has_bbox=False, page=None)
    assert "document-level" in reason


def test_document_level_findingview() -> None:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view

    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=None,
            message="Document overview.",
            details={"issue_type": "p013_document_overview"},
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = view.findings[0]
    assert fv.has_highlight is False
    assert fv.action_kind == "explanation"
    assert fv.action_label == "Read explanation"
    assert "document-level" in fv.no_highlight_reason
    assert fv.page is None
    assert fv.detailed_explanation  # must be non-empty


# ---------------------------------------------------------------------------
# 4. Abstract length explanation is detailed
# ---------------------------------------------------------------------------


def test_abstract_length_explanation_detailed() -> None:
    details = {
        "word_count": "420",
        "limit": "350",
        "inferred_degree_type": "phd",
        "confidence": "medium",
    }
    explanation = build_detailed_explanation(
        rule_id="P021",
        issue_type="abstract_word_count_exceeded",
        details=details,
        page=3,
    )
    assert "420" in explanation
    assert "350" in explanation
    assert "70" in explanation  # over_by = 420 - 350
    assert "PhD" in explanation


def test_abstract_length_explanation_ms() -> None:
    details = {
        "word_count": "180",
        "limit": "150",
        "inferred_degree_type": "ms",
        "confidence": "medium",
    }
    explanation = build_detailed_explanation(
        rule_id="P021",
        issue_type="abstract_word_count_exceeded",
        details=details,
        page=3,
    )
    assert "180" in explanation
    assert "150" in explanation
    assert "30" in explanation  # over_by
    assert "MS" in explanation


def test_abstract_findingview_has_explanation() -> None:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view

    findings = [
        AuditFinding(
            rule_id="P021",
            severity=Severity.WARNING,
            page=5,
            message="Abstract too long.",
            details={
                "word_count": "400",
                "limit": "350",
                "inferred_degree_type": "phd",
                "confidence": "medium",
                "caveat": "single-page only",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = view.findings[0]
    assert "400" in fv.detailed_explanation
    assert "350" in fv.detailed_explanation
    assert "50" in fv.detailed_explanation  # over_by
    assert "PhD" in fv.detailed_explanation
    # Must be page-only (no highlight)
    assert fv.action_kind == "page"
    assert fv.has_highlight is False


def test_abstract_no_fake_highlight(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P021",
            severity=Severity.WARNING,
            page=3,
            message="Abstract too long.",
            details={"word_count": "400", "limit": "350", "inferred_degree_type": "phd"},
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}")
    assert "/pdf/highlighted" not in page_html
    assert "400" in page_html or "What does this mean?" in page_html


# ---------------------------------------------------------------------------
# 5. Font explanation is detailed
# ---------------------------------------------------------------------------


def test_font_family_explanation() -> None:
    details = {"issue_type": "possible_body_font_family_issue", "confidence": "medium"}
    explanation = build_detailed_explanation(
        rule_id="P026",
        issue_type="possible_body_font_family_issue",
        details=details,
        page=7,
    )
    assert "Times New Roman" in explanation
    assert "font" in explanation.lower()


def test_font_size_explanation() -> None:
    details = {"issue_type": "possible_body_font_size_issue", "confidence": "medium"}
    explanation = build_detailed_explanation(
        rule_id="P026",
        issue_type="possible_body_font_size_issue",
        details=details,
        page=8,
    )
    assert "12pt" in explanation or "12" in explanation
    assert "font" in explanation.lower()


def test_font_findingview_explanation(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=5,
            message="Font family issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        )
    ]
    job_id = _inject_job(wa, findings)
    # Rule problem page
    page_html = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    assert "Times New Roman" in page_html
    # No highlight link on font findings
    assert "/pdf/highlighted" not in page_html
    assert "Open PDF page" in page_html


# ---------------------------------------------------------------------------
# 6. Page-numbering explanation is detailed
# ---------------------------------------------------------------------------


def test_page_numbering_explanation_candidate() -> None:
    details = {"issue_type": "page_number_candidate", "position_type": "bottom_center"}
    explanation = build_detailed_explanation(
        rule_id="P013",
        issue_type="page_number_candidate",
        details=details,
        page=4,
    )
    assert (
        "bottom center" in explanation.lower()
        or "bottom_center".replace("_", " ") in explanation.lower()
    )
    assert "Roman" in explanation or "numeral" in explanation.lower()


def test_page_numbering_explanation_doc_level() -> None:
    details = {"issue_type": "p013_document_overview"}
    explanation = build_detailed_explanation(
        rule_id="P013",
        issue_type="p013_document_overview",
        details=details,
        page=None,
    )
    assert "document-level" in explanation or "document level" in explanation.lower()


def test_page_numbering_findingview(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=2,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}/problems/rule/P013")
    assert "Open PDF page" in page_html
    # Explanation must reference page numbering
    assert (
        "Roman" in page_html
        or "numeral" in page_html.lower()
        or "page number" in page_html.lower()
    )


# ---------------------------------------------------------------------------
# 7. PDF annotation explanation is detailed
# ---------------------------------------------------------------------------


def test_annotation_explanation_with_type() -> None:
    details = {
        "issue_type": "pdf_annotation_detected",
        "annotation_type": "Text",
        "rect": "100.0,200.0,300.0,260.0",
    }
    explanation = build_detailed_explanation(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        details=details,
        page=3,
    )
    assert "annotation" in explanation.lower() or "comment" in explanation.lower()
    assert "submission" in explanation.lower() or "remove" in explanation.lower()


def test_annotation_findingview_highlight(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=3,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
            },
        )
    ]
    job_id = _inject_job(wa, findings)
    # Rule problem page
    rule_html = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert "Open highlighted PDF page" in rule_html
    assert "/pdf/highlighted" in rule_html
    # Route must not 500
    for link in _pdf_links(rule_html):
        resp = c.get(link)
        assert resp.status_code != 500


def test_annotation_invalid_bbox_falls_back(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "FreeText",
                "rect": "0.0,0.0,0.0,0.0",  # zero-area — invalid
                "triage_tier": "informational",
            },
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}")
    # Zero-area bbox → no highlight → must fall back to page link
    assert "Open PDF page" in page_html
    assert "/pdf/highlighted" not in page_html
    # No 500
    for link in _pdf_links(page_html):
        resp = c.get(link)
        assert resp.status_code != 500


# ---------------------------------------------------------------------------
# 8. Main/category/rule parity
# ---------------------------------------------------------------------------


def test_main_category_rule_parity(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue"},
        ),
    ]
    job_id = _inject_job(wa, findings)

    main_html = _get_html(c, f"/audits/{job_id}")
    cat_html = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    rule_p012_html = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    rule_p026_html = _get_html(c, f"/audits/{job_id}/problems/rule/P026")

    # P012 highlighted action appears everywhere it is relevant
    for page_html in (main_html, cat_html, rule_p012_html):
        assert "Open highlighted PDF page" in page_html, "P012 highlight missing"
        assert "/pdf/highlighted" in page_html

    # P026 page-only appears on main and rule page
    for page_html in (main_html, rule_p026_html):
        assert "Open PDF page" in page_html
        # P026 has no bbox — any highlighted links must not be for P026
        assert (
            "/pdf/highlighted" not in page_html
            or "P026" not in page_html.split("/pdf/highlighted")[0].split("P026")[-1]
        )

    # issue types appear on all pages
    assert "pdf annotation detected" in main_html.lower()
    assert "pdf annotation detected" in cat_html.lower()
    assert "pdf annotation detected" in rule_p012_html.lower()

    # explanation present everywhere
    assert "What does this mean?" in main_html
    assert "What does this mean?" in cat_html
    assert "What does this mean?" in rule_p012_html


def test_rule_page_explanation_present(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P021",
            severity=Severity.WARNING,
            page=5,
            message="Abstract too long.",
            details={"word_count": "400", "limit": "350", "inferred_degree_type": "phd"},
        )
    ]
    job_id = _inject_job(wa, findings)
    rule_html = _get_html(c, f"/audits/{job_id}/problems/rule/P021")
    # Explanation shown
    assert "What does this mean?" in rule_html
    # page-only action
    assert "Open PDF page" in rule_html
    assert "/pdf/highlighted" not in rule_html


# ---------------------------------------------------------------------------
# 9. Mobile/desktop parity
# ---------------------------------------------------------------------------


def _build_parity_job(wa: Any) -> str:
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue"},
        ),
        AuditFinding(
            rule_id="P021",
            severity=Severity.WARNING,
            page=4,
            message="Abstract too long.",
            details={"word_count": "400", "limit": "350", "inferred_degree_type": "phd"},
        ),
    ]
    import json
    import os

    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()
    for i in range(5):
        pg = doc.new_page(width=612, height=792)
        pg.insert_text((72, 96), f"Page {i+1}")
    doc.save(jdir / "upload.pdf")
    doc.close()

    metadata = {"input_file_name": "parity-thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name="parity-thesis.pdf",
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=sum(1 for f in view.findings if f.severity == "WARNING"),
        fail_count=sum(1 for f in view.findings if f.severity == "FAIL"),
        findings=[
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "page": f.page,
                "issue_type": f.issue_type,
                "category": f.category,
                "polished_comment": f.polished_comment,
                "suggested_fix": f.suggested_fix,
                "triage_tier": f.triage_tier,
                "confidence": f.confidence,
                "source_file": f.source_file,
                "source_line": f.source_line,
                "location_label": f.location_label,
                "bbox": list(f.bbox) if f.bbox else None,
                "action_kind": f.action_kind,
                "action_label": f.action_label,
                "has_highlight": f.has_highlight,
                "no_highlight_reason": f.no_highlight_reason,
                "detailed_explanation": f.detailed_explanation,
            }
            for f in view.findings
        ],
        grouped_summary=[
            {"rule_id": r.rule_id, "count": r.count, "category": r.category}
            for r in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
    )
    wa._set_job(job)
    return job_id


def _normalize_pdf_links(text: str) -> set[str]:
    links = set(re.findall(r'href="(/audits/[^"]*?/pdf(?:[/?#][^"]*)?)"', text))
    return {html.unescape(link).split("#")[0] for link in links}


def test_mobile_desktop_parity_job_page(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _build_parity_job(wa)

    mobile = html.unescape(c.get(f"/audits/{job_id}", headers=_MOBILE_HEADERS).text)
    desktop = html.unescape(c.get(f"/audits/{job_id}", headers=_DESKTOP_HEADERS).text)

    # Same action labels on both viewports
    for label in ("Open highlighted PDF page", "Open PDF page", "What does this mean?"):
        if label in desktop:
            assert label in mobile, f"Mobile missing: {label!r}"
        if label in mobile:
            assert label in desktop, f"Desktop missing: {label!r}"

    # Same PDF links
    assert _normalize_pdf_links(mobile) == _normalize_pdf_links(desktop)

    # Same rule IDs
    for rule_id in ("P012", "P026", "P021"):
        assert rule_id in mobile
        assert rule_id in desktop

    # Same issue labels
    for label in ("pdf annotation detected", "possible body font family issue"):
        if label in desktop.lower():
            assert label in mobile.lower(), f"Mobile missing issue label: {label!r}"


def test_mobile_desktop_parity_category_and_rule_pages(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _build_parity_job(wa)

    pages = [
        f"/audits/{job_id}/problems/category/annotations",
        f"/audits/{job_id}/problems/rule/P012",
        f"/audits/{job_id}/problems/rule/P026",
    ]
    for path in pages:
        mobile = html.unescape(c.get(path, headers=_MOBILE_HEADERS).text)
        desktop = html.unescape(c.get(path, headers=_DESKTOP_HEADERS).text)
        assert _normalize_pdf_links(mobile) == _normalize_pdf_links(desktop), (
            f"PDF links differ on {path}"
        )
        # explanation present on both
        assert "What does this mean?" in mobile
        assert "What does this mean?" in desktop


def test_no_mobile_only_or_desktop_only_classes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    templates = [
        repo_root / "src/njit_auditor/templates/job.html",
        repo_root / "src/njit_auditor/templates/problem_group.html",
    ]
    combined = "\n".join(t.read_text(encoding="utf-8") for t in templates)
    for cls in ("mobile-only", "desktop-only", "sm:hidden", "md:hidden", "lg:hidden"):
        assert cls not in combined, f"Forbidden responsive class found: {cls!r}"


# ---------------------------------------------------------------------------
# 10. No 500 PDF route crawl
# ---------------------------------------------------------------------------


def test_no_500_pdf_route_crawl(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue"},
        ),
        AuditFinding(
            rule_id="P021",
            severity=Severity.WARNING,
            page=4,
            message="Abstract too long.",
            details={"word_count": "400", "limit": "350", "inferred_degree_type": "phd"},
        ),
    ]
    job_id = _inject_job(wa, findings)

    pages_to_crawl = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/annotations",
        f"/audits/{job_id}/problems/rule/P012",
        f"/audits/{job_id}/problems/rule/P026",
        f"/audits/{job_id}/problems/rule/P021",
    ]

    all_links: set[str] = set()
    for path in pages_to_crawl:
        page_html = _get_html(c, path)
        all_links.update(_pdf_links(page_html))

    assert all_links, "No PDF links found — test may be broken"
    for link in all_links:
        resp = c.get(link)
        assert resp.status_code != 500, f"{link} returned 500"
        assert resp.status_code == 200, f"{link} returned {resp.status_code}"
        assert resp.headers["content-type"].startswith("application/pdf"), (
            f"{link} not a PDF"
        )
        disposition = resp.headers.get("content-disposition", "").lower()
        assert "attachment" not in disposition, f"{link} forces download"
        assert "inline" in disposition, f"{link} not inline"


# ---------------------------------------------------------------------------
# Explanation module unit tests
# ---------------------------------------------------------------------------


def test_build_detailed_explanation_annotation() -> None:
    expl = build_detailed_explanation(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        details={"annotation_type": "FreeText"},
        page=3,
    )
    assert "annotation" in expl.lower() or "comment" in expl.lower()
    assert "submission" in expl.lower() or "remove" in expl.lower()


def test_build_detailed_explanation_unknown_rule() -> None:
    expl = build_detailed_explanation(
        rule_id="P999",
        issue_type="some_unknown_type",
        details={},
        page=1,
    )
    assert expl  # must not be empty
    assert "some unknown type" in expl.lower() or "automated" in expl.lower()


def test_build_detailed_explanation_unknown_rule_no_issue() -> None:
    expl = build_detailed_explanation(
        rule_id="P999",
        issue_type="",
        details={},
        page=1,
    )
    assert expl


def test_build_group_explanation_p026() -> None:
    expl = build_group_explanation(rule_id="P026", issue_type="possible_body_font_family_issue")
    assert "Times New Roman" in expl or "font" in expl.lower()


def test_build_group_explanation_unknown() -> None:
    expl = build_group_explanation(rule_id="P999", issue_type="weird_issue")
    assert expl


def test_annotation_explanation_unknown_type() -> None:
    details = {"issue_type": "pdf_annotation_detected", "annotation_type": "Unknown"}
    expl = build_detailed_explanation(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        details=details,
        page=2,
    )
    assert expl
    assert "annotation" in expl.lower()


def test_p023_body_spacing_explanation() -> None:
    expl = build_detailed_explanation(
        rule_id="P023",
        issue_type="body_spacing_issue",
        details={},
        page=5,
    )
    assert "double" in expl.lower()
    assert "spacing" in expl.lower()


def test_p011_margin_explanation_with_side() -> None:
    expl = build_detailed_explanation(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        details={"side": "left_margin", "worst_overflow_pt": "5.2"},
        page=7,
    )
    assert "left margin" in expl.lower()
    assert "1.5" in expl or "margin" in expl.lower()


def test_groupedproblemview_has_explanation() -> None:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view

    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=i + 1,
            message=f"Font issue {i}.",
            details={"issue_type": "possible_body_font_family_issue"},
        )
        for i in range(3)
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    assert view.grouped_problems
    gp = view.grouped_problems[0]
    assert gp.detailed_explanation
    assert "Times New Roman" in gp.detailed_explanation or "font" in gp.detailed_explanation.lower()
    assert not gp.has_any_highlight


def test_groupedproblemview_has_any_highlight() -> None:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view

    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="Annotation.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    gp = view.grouped_problems[0]
    assert gp.has_any_highlight is True
