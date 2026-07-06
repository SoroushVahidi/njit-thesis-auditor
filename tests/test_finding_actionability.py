"""Tests for clickable actionable findings with PDF highlights and explanations.

Covers:
1. Highlightable finding renders highlighted action
2. Page-known/no-bbox finding renders explanation action, no PDF button at all
3. Document-level finding renders explanation action
4. Abstract length explanation is detailed
5. Font explanation is detailed
6. Page-numbering explanation is detailed
7. PDF annotation explanation is detailed
8. Main/category/rule parity
9. Mobile/desktop parity
10. No 500 PDF route crawl
11. P013 wording precision (candidate vs. confirmed defect)
12. Page-numbering rules: main/category/rule/issue-type wording consistency
13. Page-numbering rules: mobile/desktop parity
14. Page-numbering rules: no 500 PDF route crawl
15. P063 single-appendix-letter-label exact explanation
16. P063 main/category/rule/issue-type explanation consistency
17. Category title is not misleadingly vague for P063
18. No misleading group-level PDF button when nothing is highlightable
19. P063 page-known/no-highlight action wording
20. Document-level/no-page finding has no PDF button, explanation only
21. Existing highlightable findings unaffected by the PDF-action policy
22. Mobile/desktop parity for P063 and the PDF-action policy
23. No-500 route crawl across category/rule/issue-type pages for P063
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

from njit_auditor.finding_explanations import (
    build_detailed_explanation,
    build_group_explanation,
    get_action_kind,
    get_action_label,
    get_no_highlight_reason,
)
from njit_auditor.issue_type_explanations import explain_issue_type
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_highlight import get_pdf_page_sizes
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.polished_comments import build_polished_comment
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict
from njit_auditor.rules.pdf_abstract_indentation import check_pdf_abstract_indentation
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    check_pdf_lot_lof_entry_number_alignment,
)
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting

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
                "issue_type_label": f.issue_type_label,
                "issue_type_explanation": f.issue_type_explanation,
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
    return extract_audit_pdf_links(text)



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
    original_bytes = (
        Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "upload.pdf"
    ).read_bytes()
    page_html = _get_html(c, f"/audits/{job_id}")

    # Action label
    assert "Open highlighted PDF page" in page_html
    # URL must point to highlighted endpoint
    assert "/highlighted-page.pdf" in page_html
    # Route must return a PDF, not 500, with at least one real visible annotation.
    highlighted_links = [
        link for link in _pdf_links(page_html) if "highlighted" in link
    ]
    assert highlighted_links, "No highlighted PDF link found"
    for link in highlighted_links:
        resp = c.get(link)
        assert resp.status_code != 500, f"{link} returned 500"
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content != original_bytes
        with fitz.open(stream=resp.content, filetype="pdf") as doc:
            total_annots = sum(len(list(page.annots() or [])) for page in doc)
        assert total_annots >= 1


def test_highlightable_finding_action_kind_and_label() -> None:
    assert get_action_kind(has_highlight=True, page=2) == "highlight"
    assert get_action_label(has_highlight=True, page=2) == "Open highlighted PDF page"
    assert get_no_highlight_reason(has_highlight=True, page=2) == ""


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


def test_page_known_no_bbox_finding_renders_original_page_action(
    app: tuple[TestClient, Any],
) -> None:
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

    assert "Open highlighted PDF page" not in page_html
    assert "Open original PDF page" in page_html
    # "original_page" now resolves through the same true single-page endpoint as
    # "highlight" (falls back to a plain, unhighlighted single-page extract when
    # no bbox exists) rather than a #page=N fragment into the full PDF, which
    # mobile PDF viewers do not reliably honor.
    assert (
        f"/audits/{job_id}/highlighted-page.pdf?page=3"
        "&rule_id=P026&issue_type=possible_body_font_family_issue" in page_html
    )
    assert f"/audits/{job_id}/pdf#page=3" not in page_html
    assert "/pdf/highlighted" not in page_html
    assert (
        "No exact highlight is available" in page_html
        and "page 3" in page_html
    )


def test_page_only_action_kind_and_label() -> None:
    assert get_action_kind(has_highlight=False, page=5) == "original_page"
    assert get_action_label(has_highlight=False, page=5) == "Open original PDF page"
    reason = get_no_highlight_reason(has_highlight=False, page=5)
    assert "Open the original PDF page" in reason
    assert "page 5" in reason


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
    assert fv.action_kind == "original_page"
    assert fv.action_label == "Open original PDF page"
    assert "Open the original PDF page" in fv.no_highlight_reason
    assert "left margin" in fv.no_highlight_reason
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
    assert get_action_kind(has_highlight=False, page=None) == "explanation"
    assert get_action_label(has_highlight=False, page=None) == "Read explanation"
    reason = get_no_highlight_reason(has_highlight=False, page=None)
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
    assert not view.findings
    assert not view.inventory_findings


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
    # No bbox available: original-page action only, never a fake highlight.
    assert fv.action_kind == "original_page"
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
    assert "/pdf/highlighted" not in page_html
    assert "Open original PDF page" in page_html
    assert "Page 5" in page_html


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
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}/problems/rule/P013")
    assert "Open original PDF page" in page_html
    assert "Page 2" in page_html
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
    assert "/highlighted-page.pdf" in rule_html
    # Route must not 500
    for link in _pdf_links(rule_html):
        resp = c.get(link)
        assert resp.status_code != 500


@pytest.mark.parametrize(
    ("case_name", "rect"),
    [
        ("zero_area", "0.0,0.0,0.0,0.0"),
        ("inverted", "300.0,260.0,100.0,200.0"),
        ("nan", "nan,nan,nan,nan"),
        ("infinity", "inf,inf,inf,inf"),
        ("outside_page_bounds", "2000.0,2000.0,2100.0,2100.0"),
        ("too_tiny", "100.0,200.0,100.5,200.5"),
        ("malformed_string", "not-a-number,200.0,300.0,260.0"),
        # 0-1 normalized fractions mistaken for PDF points: technically a
        # valid, positive-area rectangle, but vanishingly thin once placed on
        # a real (612x792pt) page -- must not be treated as a real highlight.
        ("normalized_coordinates", "0.1,0.1,0.5,0.5"),
    ],
)
def test_annotation_invalid_bbox_falls_back(
    app: tuple[TestClient, Any], case_name: str, rect: str
) -> None:
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
                "rect": rect,
                "triage_tier": "informational",
            },
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}")
    # Invalid/unusable bbox → no highlight → original-page fallback only.
    assert "Open original PDF page" in page_html, case_name
    assert "Open highlighted PDF page" not in page_html, case_name
    assert "/pdf/highlighted" not in page_html, case_name
    assert "No exact highlight is available" in page_html, case_name
    # No 500, regardless of which malformed bbox shape produced this state.
    for link in _pdf_links(page_html):
        resp = c.get(link)
        assert resp.status_code != 500


def test_annotation_page_out_of_pdf_range_falls_back(app: tuple[TestClient, Any]) -> None:
    """A finding whose page number exceeds the PDF's actual page count must not highlight."""
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=99,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",  # otherwise-valid bbox
                "triage_tier": "informational",
            },
        )
    ]
    job_id = _inject_job(wa, findings, page_count=5)  # PDF only has 5 pages
    page_html = _get_html(c, f"/audits/{job_id}")
    assert "Open highlighted PDF page" not in page_html
    assert "Open original PDF page" in page_html
    assert "No exact highlight is available" in page_html

    resp = c.get(f"/audits/{job_id}/pdf/highlighted", params={"page": 99, "rule_id": "P012"})
    assert resp.status_code != 500
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


# ---------------------------------------------------------------------------
# 7b. P012 wording distinguishes uploaded-PDF annotations from auditor highlights
# ---------------------------------------------------------------------------


def test_annotation_comment_mentions_uploaded_pdf_and_disclaims_auditor_highlight() -> None:
    comment = build_polished_comment(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        page=4,
        details={"annotation_type": "Highlight", "rect": "10.0,20.0,30.0,40.0"},
    )
    assert "uploaded PDF" in comment
    assert "highlight annotation" in comment
    assert "not a highlight added by this auditor" in comment
    # Raw bbox coordinates must never leak into student-facing text.
    for raw in ("10.0", "20.0", "30.0", "40.0"):
        assert raw not in comment


def test_annotation_comment_safely_labels_known_annotation_types() -> None:
    cases = {
        "Text": "sticky note",
        "FreeText": "comment annotation",
        "Popup": "comment annotation",
        "Highlight": "highlight annotation",
        "Square": "markup annotation",
        "Unknown": "PDF annotation",
        "": "PDF annotation",
    }
    for annotation_type, expected_label in cases.items():
        comment = build_polished_comment(
            rule_id="P012",
            issue_type="pdf_annotation_detected",
            page=2,
            details={"annotation_type": annotation_type},
        )
        assert expected_label in comment, (annotation_type, comment)


def test_annotation_comment_never_exposes_raw_annotation_content() -> None:
    private_text = "Please rewrite this paragraph before your defense"
    comment = build_polished_comment(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        page=4,
        details={"annotation_type": "FreeText", "content": private_text},
    )
    assert private_text not in comment


def test_annotation_explanation_distinguishes_from_auditor_highlight() -> None:
    explanation = build_detailed_explanation(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        details={"annotation_type": "Text"},
        page=5,
        has_highlight=True,
    )
    assert "uploaded PDF" in explanation
    assert "not a highlight added by this auditor" in explanation
    assert "sticky note" in explanation


def test_annotation_explanation_never_exposes_raw_annotation_content() -> None:
    private_text = "Reviewer wrote a private note about this section"
    explanation = build_detailed_explanation(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        details={"annotation_type": "Popup", "content": private_text},
        page=2,
        has_highlight=True,
    )
    assert private_text not in explanation
    assert "comment annotation" in explanation


def test_annotation_no_highlight_fallback_names_annotation_area() -> None:
    explanation = build_detailed_explanation(
        rule_id="P012",
        issue_type="pdf_annotation_detected",
        details={"annotation_type": "Highlight"},
        page=5,
        has_highlight=False,
    )
    assert "the annotation area" in explanation


def test_annotation_issue_type_help_distinguishes_from_auditor_highlight() -> None:
    expl = explain_issue_type("P012", "pdf_annotation_detected")
    assert "uploaded PDF" in expl
    assert "not a highlight added by this auditor" in expl


def test_annotation_highlight_action_label_unchanged_with_bbox(
    app: tuple[TestClient, Any],
) -> None:
    """Real bbox data must still yield the standard, rule-agnostic highlight action."""
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=3,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Highlight",
                "rect": "100.0,200.0,300.0,260.0",
            },
        )
    ]
    job_id = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")
    assert "Open highlighted PDF page" in text
    assert "uploaded PDF" in text


def test_annotation_fallback_guidance_honest_without_bbox(
    app: tuple[TestClient, Any],
) -> None:
    """No parseable bbox must still fall back to the honest original-page guidance."""
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=3,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Highlight",
            },
        )
    ]
    job_id = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")
    assert "Open original PDF page" in text
    assert "Open highlighted PDF page" not in text
    assert "No exact highlight is available" in text
    assert "the annotation area" in text


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
        assert "/highlighted-page.pdf" in page_html

    assert "Open original PDF page" in main_html
    assert "Open original PDF page" in rule_p026_html
    assert "Open highlighted PDF page" not in rule_p026_html
    assert "/pdf/highlighted" not in rule_p026_html

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
    assert "Open original PDF page" in rule_html
    assert "/pdf/highlighted" not in rule_html
    assert "Page 5" in rule_html


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
    pdf_page_sizes = get_pdf_page_sizes(jdir / "upload.pdf")
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name="parity-thesis.pdf",
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
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
                "issue_type_label": f.issue_type_label,
                "issue_type_explanation": f.issue_type_explanation,
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
    return extract_audit_pdf_links(text)



def test_mobile_desktop_parity_job_page(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _build_parity_job(wa)

    mobile = html.unescape(c.get(f"/audits/{job_id}", headers=_MOBILE_HEADERS).text)
    desktop = html.unescape(c.get(f"/audits/{job_id}", headers=_DESKTOP_HEADERS).text)

    # Same action labels on both viewports
    for label in ("Open highlighted PDF page", "Open original PDF page", "What does this mean?"):
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
        issue_type="possible_body_text_not_double_spaced",
        details={},
        page=5,
    )
    assert "double-spaced" in expl.lower()


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


# ---------------------------------------------------------------------------
# 11. P013 wording precision — candidate vs. confirmed defect
# ---------------------------------------------------------------------------

# The exact phrase the old (vague) P013 remediation implied: that this rule
# alone confirms placement/style compliance. The fix must never present this
# as the sole explanation for a P013 finding.
_OLD_VAGUE_P013_PHRASE = "Verify page numbering placement and style match NJIT requirements"


def test_p013_bottom_center_wording_is_verification_signal() -> None:
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=4,
        details={"position_type": "bottom_center"},
    )
    assert "bottom center" in comment
    assert "verification signal" in comment
    assert "0.5 inches" in comment
    assert "near top/bottom zones" not in comment
    assert _OLD_VAGUE_P013_PHRASE not in comment


def test_p013_multiple_candidates_wording_flags_duplicates() -> None:
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=6,
        details={"position_type": "bottom_center", "candidate_count_on_page": "2"},
    )
    assert "Multiple page-number-like tokens were detected on page 6" in comment
    assert "duplicate" in comment.lower()
    assert _OLD_VAGUE_P013_PHRASE not in comment


def test_p013_outside_bottom_area_wording_flags_placement() -> None:
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=8,
        details={"position_type": "top_center"},
    )
    assert "appears at top center" in comment
    assert "bottom" in comment
    assert "0.5 inches" in comment
    assert _OLD_VAGUE_P013_PHRASE not in comment


def test_p013_undetermined_position_wording_is_neutral() -> None:
    # Mirrors the test_problem_drilldown.py fixture, which has no position_type.
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=9,
        details={},
    )
    assert "verification signal" in comment or "verify" in comment.lower()
    assert "bottom center" in comment
    assert _OLD_VAGUE_P013_PHRASE not in comment


def test_p013_issue_type_explanation_says_verification_signal() -> None:
    explanation = explain_issue_type("P013", "page_number_candidate")
    assert "verification signal" in explanation.lower()
    assert "roman" in explanation.lower() or "arabic" in explanation.lower()
    assert "does not by itself confirm" not in explanation or "defect" in explanation.lower()


# ---------------------------------------------------------------------------
# 12. Page-numbering rules: main/category/rule/issue-type wording consistency
# ---------------------------------------------------------------------------


def _build_page_numbering_job(wa: Any) -> str:
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=2,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=5,
            message="Missing page number.",
            details={"issue_type": "missing_page_number", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P022",
            severity=Severity.WARNING,
            page=3,
            message="Visible page number on no-number page.",
            details={
                "issue_type": "visible_page_number_on_no_number_page",
                "page_type": "abstract",
                "candidate_text": "iii",
            },
        ),
        AuditFinding(
            rule_id="P028",
            severity=Severity.WARNING,
            page=4,
            message="Wrong numbering style for region.",
            details={
                "issue_type": "arabic_number_on_frontmatter_page",
                "candidate_text": "4",
            },
        ),
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=6,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
            },
        ),
    ]
    return _inject_job(wa, findings, file_name="page-numbering-thesis.pdf", page_count=10)


def test_page_numbering_main_category_rule_issue_type_parity(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id = _build_page_numbering_job(wa)

    main_html = _get_html(c, f"/audits/{job_id}")
    cat_html = _get_html(c, f"/audits/{job_id}/problems/category/page-numbering")
    rule_p013_html = _get_html(c, f"/audits/{job_id}/problems/rule/P013")
    issue_p013_html = _get_html(
        c, f"/audits/{job_id}/problems/rule/P013/issue-type/wrong-page-number-location"
    )

    # P013 must never look like a confirmed defect on any page it appears on.
    for page_html in (main_html, cat_html, rule_p013_html, issue_p013_html):
        assert "near top/bottom zones" not in page_html
        assert _OLD_VAGUE_P013_PHRASE not in page_html

    # The P013 finding is now shown only because it states an exact location suspicion.
    for page_html in (main_html, cat_html, rule_p013_html, issue_p013_html):
        assert "appears at top center" in page_html
        assert "required bottom position" in page_html
        assert "Page number candidate" not in page_html

    assert "Wrong page-number location" in issue_p013_html

    # Confirmed defects from the other page-numbering rules explain the exact
    # problem, consistently on main/category/rule pages.
    rule_p019_html = _get_html(c, f"/audits/{job_id}/problems/rule/P019")
    rule_p022_html = _get_html(c, f"/audits/{job_id}/problems/rule/P022")
    rule_p028_html = _get_html(c, f"/audits/{job_id}/problems/rule/P028")

    for page_html in (main_html, cat_html, rule_p019_html):
        assert "did not find a clear page number" in page_html

    assert "abstract" in rule_p022_html.lower()
    for page_html in (main_html, cat_html, rule_p022_html):
        assert "suppressed or hidden" in page_html.lower()

    assert "expected to use" in rule_p028_html
    assert "Roman numerals" in rule_p028_html or "Arabic numerals" in rule_p028_html
    assert "front matter" in rule_p028_html.lower() or "front-matter" in rule_p028_html.lower()


def test_highlight_action_consistent_across_main_category_rule_issue_type_pages(
    app: tuple[TestClient, Any],
) -> None:
    """A highlightable finding's action must appear identically on every page that lists it."""
    c, wa = app
    job_id = _build_page_numbering_job(wa)  # includes a P012 finding with a valid bbox on page 6

    main_html = _get_html(c, f"/audits/{job_id}")
    cat_html = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    rule_html = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    issue_html = _get_html(
        c, f"/audits/{job_id}/problems/rule/P012/issue-type/pdf-annotation-detected"
    )

    for page_html in (main_html, cat_html, rule_html, issue_html):
        assert "Open highlighted PDF page" in page_html
        assert "/highlighted-page.pdf" in page_html
        for link in _pdf_links(page_html):
            if "highlighted" not in link:
                continue
            resp = c.get(link)
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("application/pdf")


# ---------------------------------------------------------------------------
# 13. Page-numbering rules: mobile/desktop parity
# ---------------------------------------------------------------------------


def test_page_numbering_mobile_desktop_parity(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _build_page_numbering_job(wa)

    paths = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/rule/P013",
        f"/audits/{job_id}/problems/rule/P019",
        f"/audits/{job_id}/problems/rule/P022",
        f"/audits/{job_id}/problems/rule/P028",
        f"/audits/{job_id}/problems/rule/P013/issue-type/wrong-page-number-location",
    ]
    for path in paths:
        mobile = _get_html(c, path, headers=_MOBILE_HEADERS)
        desktop = _get_html(c, path, headers=_DESKTOP_HEADERS)
        assert _pdf_links(mobile) == _pdf_links(desktop), f"PDF links differ on {path}"
        for phrase in (
            "top center",
            "required bottom position",
            "did not find a clear page number",
            "Roman numerals",
        ):
            if phrase in desktop:
                assert phrase in mobile, f"Mobile missing {phrase!r} on {path}"
            if phrase in mobile:
                assert phrase in desktop, f"Desktop missing {phrase!r} on {path}"


# ---------------------------------------------------------------------------
# 14. Page-numbering rules: no 500 PDF route crawl
# ---------------------------------------------------------------------------


def test_page_numbering_no_500_route_crawl(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _build_page_numbering_job(wa)

    pages_to_crawl = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/rule/P013",
        f"/audits/{job_id}/problems/rule/P019",
        f"/audits/{job_id}/problems/rule/P022",
        f"/audits/{job_id}/problems/rule/P028",
        f"/audits/{job_id}/problems/rule/P013/issue-type/wrong-page-number-location",
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
        assert resp.headers["content-type"].startswith("application/pdf"), f"{link} not a PDF"


# ---------------------------------------------------------------------------
# 15. P063 single-appendix-letter-label exact explanation
# ---------------------------------------------------------------------------


def _p063_single_appendix_finding(page: int = 76) -> AuditFinding:
    return AuditFinding(
        rule_id="P063",
        severity=Severity.WARNING,
        page=page,
        message=f"Single appendix body heading on page {page} uses a letter identifier ('A').",
        details={
            "issue_type": "single_appendix_uses_letter_label",
            "appendix_count": "1",
            "letter_found": "A",
            "triage_tier": "medium",
            "source_q_rule_id": "Q058",
        },
    )


def test_p063_single_appendix_exact_explanation(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_p063_single_appendix_finding()], page_count=80)
    page_html = _get_html(c, f"/audits/{job_id}")

    assert "single appendix" in page_html.lower()
    assert "APPENDIX A" in page_html
    assert "only when the document has multiple appendices" in page_html
    assert "What to fix" in page_html

    # Must not fall through to the generic, vague text.
    assert "Formatting check P063 flagged" not in page_html
    assert "This automated check flagged an issue of type" not in page_html
    assert "Front matter structure" not in page_html


# ---------------------------------------------------------------------------
# 16. P063 main/category/rule/issue-type explanation consistency
# ---------------------------------------------------------------------------


def test_p063_main_category_rule_issue_type_consistency(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_p063_single_appendix_finding()], page_count=80)

    main_html = _get_html(c, f"/audits/{job_id}")
    cat_html = _get_html(c, f"/audits/{job_id}/problems/category/frontmatter-structure")
    rule_html = _get_html(c, f"/audits/{job_id}/problems/rule/P063")
    issue_html = _get_html(
        c, f"/audits/{job_id}/problems/rule/P063/issue-type/single-appendix-uses-letter-label"
    )

    for page_html in (main_html, cat_html, rule_html, issue_html):
        assert "APPENDIX A" in page_html, page_html
        assert "only when the document has multiple appendices" in page_html
        assert "What to fix" in page_html


# ---------------------------------------------------------------------------
# 17. Category title is not misleadingly vague for P063
# ---------------------------------------------------------------------------


def test_p063_category_title_not_misleadingly_vague(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_p063_single_appendix_finding()], page_count=80)
    cat_html = _get_html(c, f"/audits/{job_id}/problems/category/frontmatter-structure")

    # Only one issue type is present, so the page must use a precise,
    # issue-specific title instead of the broad category umbrella label.
    assert "Appendix heading label convention" in cat_html
    assert "Front matter structure" not in cat_html
    assert "Front matter / appendix structure" not in cat_html
    assert "appendix" in cat_html.lower()
    # The exact issue is visible above the findings, not hidden.
    assert "APPENDIX A" in cat_html


# ---------------------------------------------------------------------------
# 18. No misleading group-level PDF button when nothing is highlightable
# ---------------------------------------------------------------------------


def test_no_misleading_group_level_pdf_button_when_doc_level_only(
    app: tuple[TestClient, Any],
) -> None:
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
    resp = c.get(f"/audits/{job_id}/problems/category/page-numbering", headers=_DESKTOP_HEADERS)
    assert resp.status_code in (400, 404)


def test_no_misleading_group_level_pdf_button_on_rule_page(
    app: tuple[TestClient, Any],
) -> None:
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
    resp = c.get(f"/audits/{job_id}/problems/rule/P013", headers=_DESKTOP_HEADERS)
    assert resp.status_code in (400, 404)


# ---------------------------------------------------------------------------
# 19. P063 page-known/no-highlight action wording
# ---------------------------------------------------------------------------


def test_p063_page_known_no_highlight_wording(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_p063_single_appendix_finding()], page_count=80)
    page_html = _get_html(c, f"/audits/{job_id}")

    assert "Open original PDF page" in page_html
    assert "Open highlighted PDF page" not in page_html
    assert "/pdf/highlighted" not in page_html
    assert "No exact highlight is available" in page_html
    assert "Open the original PDF page" in page_html


# ---------------------------------------------------------------------------
# 20. Document-level/no-page finding has no PDF button, explanation only
# ---------------------------------------------------------------------------


def test_document_level_structure_finding_no_pdf_button_explanation_only(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P025",
            severity=Severity.WARNING,
            page=None,
            message="Front matter ordering may be incorrect.",
            details={"issue_type": "possible_frontmatter_order_issue"},
        )
    ]
    job_id = _inject_job(wa, findings)
    main_html = _get_html(c, f"/audits/{job_id}")

    # Scope the check to this finding's own grouped-problem card (in the
    # collapsed Advanced: grouped problem summaries section, which comes after
    # the primary individual-findings row's own `data-rule="P025"` attribute --
    # hence rindex, not index) — the page legitimately has one whole-document
    # "Open PDF" download button elsewhere (#open-pdf-btn), which is not the
    # misleading per-finding button this policy targets.
    card_start = main_html.rindex('data-rule="P025"')
    actions_end = main_html.index("Examples of this exact problem", card_start)
    card_section = main_html[card_start:actions_end]
    assert f'href="/audits/{job_id}/pdf"' not in card_section
    assert "/pdf/highlighted" not in card_section
    assert "document-level" in card_section.lower()
    assert "What does this mean?" in main_html

    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = view.findings[0]
    assert fv.action_kind == "explanation"
    assert fv.page is None
    assert fv.detailed_explanation


# ---------------------------------------------------------------------------
# 21. Existing highlightable findings unaffected by the PDF-action policy
# ---------------------------------------------------------------------------


def test_highlightable_finding_unaffected_by_pdf_action_policy(
    app: tuple[TestClient, Any],
) -> None:
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
        )
    ]
    job_id = _inject_job(wa, findings)

    main_html = _get_html(c, f"/audits/{job_id}")
    cat_html = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    rule_html = _get_html(c, f"/audits/{job_id}/problems/rule/P012")

    for page_html in (main_html, cat_html, rule_html):
        assert "Open highlighted PDF page" in page_html
        assert "/highlighted-page.pdf" in page_html

    for page_html in (cat_html, rule_html):
        links = [link for link in _pdf_links(page_html) if "highlighted" in link]
        assert links, "No highlighted PDF link found"
        for link in links:
            resp = c.get(link)
            assert resp.status_code != 500
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 22. Mobile/desktop parity for P063 and the PDF-action policy
# ---------------------------------------------------------------------------


def _build_p063_policy_parity_job(wa: Any) -> str:
    findings = [
        _p063_single_appendix_finding(),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=7,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        ),
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
    ]
    return _inject_job(wa, findings, file_name="p063-policy-parity.pdf", page_count=80)


def test_p063_and_policy_mobile_desktop_parity(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _build_p063_policy_parity_job(wa)

    paths = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/frontmatter-structure",
        f"/audits/{job_id}/problems/rule/P063",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/category/annotations",
        f"/audits/{job_id}/problems/rule/P012",
    ]
    for path in paths:
        mobile = _get_html(c, path, headers=_MOBILE_HEADERS)
        desktop = _get_html(c, path, headers=_DESKTOP_HEADERS)
        assert _pdf_links(mobile) == _pdf_links(desktop), f"PDF links differ on {path}"
        for phrase in (
            "APPENDIX A",
            "Open original PDF page",
            "Open highlighted PDF page",
            "No exact highlight is available",
            "Read explanation",
        ):
            if phrase in desktop:
                assert phrase in mobile, f"Mobile missing {phrase!r} on {path}"
            if phrase in mobile:
                assert phrase in desktop, f"Desktop missing {phrase!r} on {path}"


# ---------------------------------------------------------------------------
# 23. No-500 route crawl across category/rule/issue-type pages for P063
# ---------------------------------------------------------------------------


def test_p063_no_500_route_crawl(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_p063_single_appendix_finding()], page_count=80)

    pages_to_crawl = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/frontmatter-structure",
        f"/audits/{job_id}/problems/rule/P063",
        f"/audits/{job_id}/problems/rule/P063/issue-type/single-appendix-uses-letter-label",
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
        assert resp.headers["content-type"].startswith("application/pdf"), f"{link} not a PDF"


# ---------------------------------------------------------------------------
# 24. Ester YES/NO matrix alignment — one check, one matching remediation
#
# See docs/planning/ester_yesno_matrix_alignment_audit.md. P027 is the rule
# that actually spans heading Levels 1-5 (Ester's "P020 mixes levels"
# complaint, as literally reproducible, maps onto P027); P020 mixes two
# subjects (Level 2 headings vs. table titles) under one issue_type. Both
# used to append one combined, rule-level remediation regardless of which
# level/subject actually applied — the exact failure mode being fixed here.
# ---------------------------------------------------------------------------

_OLD_COMBINED_P027_REMEDIATION = "Level 2 (1.x): Title Case; Level 3 (1.x.x): Sentence case"
_OLD_COMBINED_P025_REMEDIATION = "the title page includes the degree and institution name"
_OLD_BANNED_FALLBACK_PHRASE = "flagged issue type"


def test_p027_level1_remediation_is_level_specific() -> None:
    comment = build_polished_comment(
        rule_id="P027", issue_type="level1_not_all_caps", page=3, details={}
    )
    assert "Level 1" in comment
    assert "ALL CAPS" in comment
    for other_level in ("Level 2", "Level 3", "Level 4", "Level 5"):
        assert other_level not in comment
    assert _OLD_COMBINED_P027_REMEDIATION not in comment


def test_p027_level3_remediation_is_level_specific() -> None:
    comment = build_polished_comment(
        rule_id="P027", issue_type="level3_sentence_case_issue", page=12, details={}
    )
    assert "Level 3" in comment
    assert "Sentence case" in comment
    for other_level in ("Level 1", "Level 2", "Level 4", "Level 5"):
        assert other_level not in comment
    assert "ALL CAPS" not in comment
    assert _OLD_COMBINED_P027_REMEDIATION not in comment


def test_p027_all_issue_types_avoid_old_combined_remediation() -> None:
    for issue_type in (
        "level1_not_all_caps",
        "level2_title_case_issue",
        "level3_sentence_case_issue",
        "level4_sentence_case_issue",
        "level4_sentence_case_or_punctuation_issue",
        "level5_sentence_case_issue",
        "level5_sentence_case_or_punctuation_issue",
    ):
        comment = build_polished_comment(
            rule_id="P027", issue_type=issue_type, page=3, details={}
        )
        assert _OLD_COMBINED_P027_REMEDIATION not in comment
        assert _OLD_BANNED_FALLBACK_PHRASE not in comment


def test_p027_explanation_templates_are_level_specific() -> None:
    level1 = build_detailed_explanation(
        rule_id="P027", issue_type="level1_not_all_caps", page=3, details={}
    )
    level3 = build_detailed_explanation(
        rule_id="P027", issue_type="level3_sentence_case_issue", page=12, details={}
    )
    assert "Level 1" in level1 and "Level 3" not in level1
    assert "Level 3" in level3 and "Level 1" not in level3


def test_p020_heading_source_comment_is_title_case_specific_not_mixed_with_caption() -> None:
    comment = build_polished_comment(
        rule_id="P020",
        issue_type="possible_title_capitalization_issue",
        page=5,
        details={"source": "heading", "expected_or_reason": "first_word_requires_capital"},
    )
    assert "Level 2 heading" in comment
    assert "table title" not in comment
    assert "the first word is not capitalized" in comment


def test_p020_caption_source_comment_is_title_case_specific_not_mixed_with_heading() -> None:
    comment = build_polished_comment(
        rule_id="P020",
        issue_type="possible_title_capitalization_issue",
        page=7,
        details={"source": "caption", "expected_or_reason": "major_word_requires_capital"},
    )
    assert "table title" in comment
    assert "Level 2 heading" not in comment
    assert "a major word (4+ letters) is not capitalized" in comment


def test_p020_comment_never_quotes_flagged_word() -> None:
    # The actual flagged word is dissertation body text and must never appear,
    # even if accidentally passed through in details.
    comment = build_polished_comment(
        rule_id="P020",
        issue_type="possible_title_capitalization_issue",
        page=5,
        details={
            "source": "heading",
            "expected_or_reason": "first_word_requires_capital",
            "word": "the",
        },
    )
    assert "'the'" not in comment


def test_p025_missing_abstract_body_remediation_matches_only_that_issue() -> None:
    from njit_auditor.polished_comments import resolve_suggested_fix_for_display

    fix = resolve_suggested_fix_for_display("P025", "missing_abstract_body")
    assert "Add the abstract body text directly below the ABSTRACT heading" in fix
    for unrelated in ("degree phrase", "institution", "Approval Page", "Table of Contents"):
        assert unrelated not in fix
    assert _OLD_COMBINED_P025_REMEDIATION not in fix


def test_p025_frontmatter_order_remediation_matches_only_that_issue() -> None:
    from njit_auditor.polished_comments import resolve_suggested_fix_for_display

    fix = resolve_suggested_fix_for_display("P025", "possible_frontmatter_order_issue")
    assert "before the Table of Contents" in fix
    assert "Move the Abstract" in fix
    for unrelated in ("degree phrase", "institution name", "Approval Page", "abstract body text"):
        assert unrelated not in fix
    assert _OLD_COMBINED_P025_REMEDIATION not in fix


def test_p025_all_issue_types_avoid_old_combined_remediation() -> None:
    for issue_type in (
        "missing_abstract_body",
        "missing_title_page_degree_phrase",
        "missing_title_page_institution",
        "sparse_approval_page_content",
        "possible_frontmatter_order_issue",
    ):
        comment = build_polished_comment(
            rule_id="P025",
            issue_type=issue_type,
            page=3,
            details={"toc_page": "5", "substantial_line_count": "1"},
        )
        assert _OLD_COMBINED_P025_REMEDIATION not in comment
        assert _OLD_BANNED_FALLBACK_PHRASE not in comment


def test_p038_required_heading_missing_uses_matrix_aligned_wording() -> None:
    comment = build_polished_comment(
        rule_id="P038",
        issue_type="required_heading_missing",
        page=None,
        details={"expected_heading": "ACKNOWLEDGEMENTS"},
    )
    assert "ACKNOWLEDGEMENTS" in comment
    assert "was not found anywhere in the document" in comment
    explanation = explain_issue_type("P038", "required_heading_missing")
    assert "required front-matter section heading was not found" in explanation


def test_p038_required_heading_missing_explanation_distinct_from_phrase_not_exact() -> None:
    missing = explain_issue_type("P038", "required_heading_missing")
    not_exact = explain_issue_type("P038", "heading_phrase_not_exact")
    assert missing != not_exact
    assert "not found anywhere" in missing
    assert "not found anywhere" not in not_exact


def test_unhandled_issue_type_fallback_has_no_banned_phrase_but_keeps_rule_remediation() -> None:
    from njit_auditor.polished_comments import resolve_suggested_fix_for_display

    # P029 (Roman-numeral sequence) has no bespoke polished_comments template,
    # so it exercises the absolute generic fallback branch. Known issue types
    # must never fall through to the old "Formatting check PXXX flagged issue
    # type ..." phrase, and the rule's catalog remediation must still be
    # available as the suggested fix, not just a bare verify-manually instruction.
    comment = build_polished_comment(
        rule_id="P029", issue_type="roman_sequence_gap", page=5, details={}
    )
    fix = resolve_suggested_fix_for_display("P029", "roman_sequence_gap")
    assert _OLD_BANNED_FALLBACK_PHRASE not in comment
    assert "Formatting check" not in comment
    assert "roman numeral" in fix.lower()
    assert "increase continuously in order" in fix.lower()


def test_unhandled_issue_type_fallback_document_level_has_no_banned_phrase() -> None:
    comment = build_polished_comment(
        rule_id="P029", issue_type="roman_sequence_decrease", page=None, details={}
    )
    assert _OLD_BANNED_FALLBACK_PHRASE not in comment
    assert "document level" in comment


# ---------------------------------------------------------------------------
# 24. Batch 1 geometry passthrough: bbox added for P029, P035, P037, P044
#
# Each of these rules already computes the correct bbox locally for its
# detection logic; this batch only threads that existing geometry into
# details["bbox"] so the highlight pipeline can use it. These tests confirm,
# per rule: the bbox string is present and well-formed, the resulting
# FindingView is highlight-eligible, and the underlying detector still fires
# the same finding it always did (detection logic itself is unchanged).
# ---------------------------------------------------------------------------

_BBOX_STRING_RE = re.compile(r"^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$")


def _assert_valid_bbox_string(bbox_str: str) -> None:
    assert _BBOX_STRING_RE.match(bbox_str), f"not a valid 'x0,y0,x1,y1' bbox string: {bbox_str!r}"


def _findingview_for(finding: AuditFinding) -> Any:
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    return view.findings[0]


def _make_batch1_p035_pdf(path: Path) -> None:
    """Off-center table body below a table caption -> table_body_not_centered."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 1 INTRODUCTION", fontsize=14, fontname="Times-Bold")
    for idx in range(3):
        page.insert_text(
            (108.0, 240.0 + idx * 18.0),
            f"Row {idx + 1} column alpha and column beta values",
            fontsize=11,
        )
    page.insert_text(
        (108, 200.0), "Table 3.1 Example table caption title for layout testing here.", fontsize=11
    )
    doc.save(path)
    doc.close()


def test_p035_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_batch1_offcenter.pdf"
    _make_batch1_p035_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details.get("issue_type") == "table_body_not_centered"

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None


def _make_batch1_p044_pdf(path: Path, *, para1_x: float, para2_x: float) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    page.insert_text((para1_x, 130), "Synthetic abstract body paragraph first line text here.")
    page.insert_text((108.0, 144), "Continuation abstract first paragraph body text line here.")
    page.insert_text((108.0, 158), "Another line in first abstract paragraph body text here.")
    page.insert_text((para2_x, 240), "Synthetic abstract body paragraph second line here.")
    page.insert_text((108.0, 254), "Continuation abstract second paragraph body text line.")
    page.insert_text((108.0, 268), "Another line in second abstract paragraph body text.")
    doc.save(path)
    doc.close()


def test_p044_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p044_batch1_second_flush.pdf"
    _make_batch1_p044_pdf(pdf_path, para1_x=108.0, para2_x=108.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "abstract_subsequent_paragraph_not_indented" in issue_types
    finding = next(
        f
        for f in findings
        if f.details.get("issue_type") == "abstract_subsequent_paragraph_not_indented"
    )

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None


def _make_batch1_p029_pdf(path: Path) -> None:
    """Front-matter Roman sequence i, <skip>, iii -> roman_sequence_gap."""
    doc = fitz.open()
    texts: list[str | None] = ["i", None, "iii"]
    for idx, txt in enumerate(texts):
        page = doc.new_page(width=612, height=792)
        if txt is not None:
            page.insert_text((300, 770), txt, fontsize=12)
        if idx == 0:
            page.insert_textbox(
                fitz.Rect(0, 70, 612, 110),
                "TABLE OF CONTENTS",
                fontsize=16,
                fontname="Times-Bold",
                align=1,
            )
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 100), "CHAPTER 1 INTRODUCTION", fontsize=16)
    doc.save(path)
    doc.close()


def test_p029_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_batch1_gap.pdf"
    _make_batch1_p029_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_sequence(model) if f.rule_id == "P029"]
    assert any(f.details.get("issue_type") == "roman_sequence_gap" for f in findings)
    finding = next(f for f in findings if f.details.get("issue_type") == "roman_sequence_gap")

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None


def _make_batch1_p037_pdf(
    path: Path, pages: list[tuple[str | None, str | None, str | None]]
) -> None:
    doc = fitz.open()
    for heading, chapter, page_num in pages:
        page = doc.new_page(width=612, height=792)
        if heading:
            page.insert_text((180, 90), heading, fontsize=14, fontname="Times-Bold")
        if chapter:
            page.insert_text((108, 200), chapter, fontsize=14)
        if page_num:
            page.insert_text((300, 760), page_num, fontsize=12)
    doc.save(path)
    doc.close()


def test_p037_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p037_batch1_bio_wrong.pdf"
    _make_batch1_p037_pdf(
        pdf_path,
        [
            ("BIOGRAPHICAL SKETCH", None, "v"),
            (None, "CHAPTER 1 INTRODUCTION", "1"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert any(f.details.get("issue_type") == "roman_bio_sketch_not_iv" for f in findings)
    finding = next(f for f in findings if f.details.get("issue_type") == "roman_bio_sketch_not_iv")

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None


# ---------------------------------------------------------------------------
# 25. Batch 2 geometry passthrough: bbox added for P014, P024, P036, P046
# ---------------------------------------------------------------------------


def _make_batch2_p014_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((120, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    doc.save(path)
    doc.close()


def test_p014_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p014_batch2_off_center.pdf"
    _make_batch2_p014_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_named_frontmatter_headings(model) if f.rule_id == "P014"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details.get("centered") == "False"

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None

    comment = build_polished_comment(
        rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
        page=finding.page,
        details=finding.details,
    )
    assert bbox_str not in comment
    assert "ABSTRACT" not in comment


def _make_batch2_p024_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    entries = [
        "1.1 background of the study and motivation ....",
        "1.2 Statement of the Problem and Research Gap ....",
        "1.3 Review of Related Literature and Prior Work ....",
    ]
    for idx, label in enumerate(entries):
        page.insert_text((108, 130 + idx * 20), label)
        page.insert_text((500, 130 + idx * 20), "12")
    doc.save(path)
    doc.close()


def test_p024_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p024_batch2_toc_level2.pdf"
    _make_batch2_p024_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_toc_list_formatting(model)
        if f.rule_id == "P024" and f.details.get("issue_type") == "toc_level_capitalization"
    ]
    assert findings
    finding = findings[0]

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None

    line_preview = finding.details.get("line_preview", "")
    comment = build_polished_comment(
        rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
        page=finding.page,
        details=finding.details,
    )
    assert bbox_str not in comment
    if line_preview:
        assert line_preview not in comment


def _make_batch2_p036_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 140), "Chapter 3 Literature Review and Background ....", fontsize=12)
    page.insert_text((500, 140), "10", fontsize=12)
    page.insert_text((108, 170), "Chapter 4 Extended Dissertation Topic Title ....", fontsize=12)
    page.insert_text((500, 170), "12", fontsize=12)
    doc.save(path)
    doc.close()


def test_p036_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_batch2_tight_spacing.pdf"
    _make_batch2_p036_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details.get("issue_type") == "toc_inter_entry_spacing_too_tight"

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None

    comment = build_polished_comment(
        rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
        page=finding.page,
        details=finding.details,
    )
    assert bbox_str not in comment
    assert "Chapter 4 Extended Dissertation Topic Title" not in comment


_P046_BATCH2_LOT_MISALIGNED = [
    ("Table 1 Synthetic experimental setup overview entry text here.", 108.0),
    ("Table 2 Synthetic model performance comparison entry text here.", 130.0),
    ("Table 3 Synthetic regression coefficients overview entry text.", 108.0),
]


def _make_batch2_p046_pdf(path: Path, entries: list[tuple[str, float]]) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 115), "Table")
    page.insert_text((500, 115), "Page")
    for idx, (label, indent_x) in enumerate(entries):
        y = 140 + idx * 20
        page.insert_text((indent_x, y), label)
        page.insert_text((500, y), "12")
    doc.save(path)
    doc.close()


def test_p046_bbox_passthrough_present_and_valid(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p046_batch2_lot_misaligned.pdf"
    _make_batch2_p046_pdf(pdf_path, _P046_BATCH2_LOT_MISALIGNED)
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_lot_lof_entry_number_alignment(model)
        if f.rule_id == "P046"
        and f.details.get("issue_type") == "lot_entry_number_column_misaligned"
    ]
    assert len(findings) == 1
    finding = findings[0]

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    _assert_valid_bbox_string(bbox_str)

    fv = _findingview_for(finding)
    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert fv.bbox is not None

    comment = build_polished_comment(
        rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
        page=finding.page,
        details=finding.details,
    )
    assert bbox_str not in comment
    for label, _ in _P046_BATCH2_LOT_MISALIGNED:
        assert label not in comment
