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
from njit_auditor.polished_comments import build_polished_comment
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
    original_bytes = (
        Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id / "upload.pdf"
    ).read_bytes()
    page_html = _get_html(c, f"/audits/{job_id}")

    # Action label
    assert "Open highlighted PDF page" in page_html
    # URL must point to highlighted endpoint
    assert "/pdf/highlighted" in page_html
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


def test_page_known_no_bbox_finding_renders_explanation_only(
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

    # No PDF button at all for a known-page-but-no-highlight finding.
    assert "Open PDF page" not in page_html
    assert "Open highlighted PDF page" not in page_html
    assert f"/audits/{job_id}/pdf#page=3" not in page_html
    assert "/pdf/highlighted" not in page_html
    # No-highlight note must be present instead.
    assert "Exact highlight is not available" in page_html


def test_page_only_action_kind_and_label() -> None:
    assert get_action_kind(has_highlight=False, page=5) == "explanation"
    assert get_action_label(has_highlight=False, page=5) == "Read explanation"
    reason = get_no_highlight_reason(has_highlight=False, page=5)
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
    assert fv.action_kind == "explanation"
    assert fv.action_label == "Read explanation"
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
    # No bbox available: explanation only, no PDF button.
    assert fv.action_kind == "explanation"
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
    # No highlight available for this font finding, and the drill-down
    # page's strict highlight-only PDF-action policy means no PDF button is
    # shown at all — the page number and explanation carry the location.
    assert "/pdf/highlighted" not in page_html
    assert "Open PDF page" not in page_html
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
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
        )
    ]
    job_id = _inject_job(wa, findings)
    page_html = _get_html(c, f"/audits/{job_id}/problems/rule/P013")
    # No highlight available, so the drill-down page's strict highlight-only
    # PDF-action policy shows no PDF button at all.
    assert "Open PDF page" not in page_html
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
    assert "/pdf/highlighted" in rule_html
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
    # Invalid/unusable bbox → no highlight → no PDF button at all, explanation only.
    assert "Open PDF page" not in page_html, case_name
    assert "Open highlighted PDF page" not in page_html, case_name
    assert "/pdf/highlighted" not in page_html, case_name
    assert "Exact highlight is not available" in page_html, case_name
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
    assert "Open PDF page" not in page_html
    assert "Exact highlight is not available" in page_html

    resp = c.get(f"/audits/{job_id}/pdf/highlighted", params={"page": 99, "rule_id": "P012"})
    assert resp.status_code != 500
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


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

    # P026 has no bbox: every page (main results, category, and rule
    # drill-down) applies the same strict highlight-only PDF-action policy
    # and shows no PDF button at all for it.
    assert "Open PDF page" not in main_html
    assert "Open PDF page" not in rule_p026_html
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
    # No highlight available — drill-down page shows no PDF button at all.
    assert "Open PDF page" not in rule_html
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
    assert "manual verification" in comment
    assert "does not by itself confirm a formatting defect" in comment
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
    assert "outside the expected bottom page-number area" in comment
    assert "required bottom position" in comment
    assert _OLD_VAGUE_P013_PHRASE not in comment


def test_p013_undetermined_position_wording_is_neutral() -> None:
    # Mirrors the test_problem_drilldown.py fixture, which has no position_type.
    comment = build_polished_comment(
        rule_id="P013",
        issue_type="page_number_candidate",
        page=9,
        details={},
    )
    assert "No specific page-numbering defect is confirmed" in comment
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
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
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
        c, f"/audits/{job_id}/problems/rule/P013/issue-type/page-number-candidate"
    )

    # P013 must never look like a confirmed defect on any page it appears on.
    for page_html in (main_html, cat_html, rule_p013_html, issue_p013_html):
        assert "near top/bottom zones" not in page_html
        assert _OLD_VAGUE_P013_PHRASE not in page_html

    # The P013 rule page title reflects the verification framing.
    assert "Page-number candidates detected for verification" in rule_p013_html

    # The bottom-center candidate is described as a manual-verification signal
    # everywhere it is rendered.
    for page_html in (main_html, cat_html, rule_p013_html, issue_p013_html):
        assert "bottom center" in page_html
        assert "manual verification" in page_html

    # The issue-type page's explanation is the full verification-signal text.
    assert "verification signal" in issue_p013_html.lower()

    # Confirmed defects from the other page-numbering rules explain the exact
    # problem, consistently on main/category/rule pages.
    rule_p019_html = _get_html(c, f"/audits/{job_id}/problems/rule/P019")
    rule_p022_html = _get_html(c, f"/audits/{job_id}/problems/rule/P022")
    rule_p028_html = _get_html(c, f"/audits/{job_id}/problems/rule/P028")

    for page_html in (main_html, cat_html, rule_p019_html):
        assert "missing a visible page number" in page_html

    for page_html in (main_html, cat_html, rule_p022_html):
        assert "abstract" in page_html.lower()
        assert "no visible page number" in page_html.lower()

    for page_html in (main_html, cat_html, rule_p028_html):
        assert "Roman numerals" in page_html
        assert "front matter" in page_html.lower() or "front-matter" in page_html.lower()


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
        assert "/pdf/highlighted" in page_html
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
        f"/audits/{job_id}/problems/rule/P013/issue-type/page-number-candidate",
    ]
    for path in paths:
        mobile = _get_html(c, path, headers=_MOBILE_HEADERS)
        desktop = _get_html(c, path, headers=_DESKTOP_HEADERS)
        assert _pdf_links(mobile) == _pdf_links(desktop), f"PDF links differ on {path}"
        for phrase in (
            "bottom center",
            "manual verification",
            "missing a visible page number",
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
        f"/audits/{job_id}/problems/rule/P013/issue-type/page-number-candidate",
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
    cat_html = _get_html(c, f"/audits/{job_id}/problems/category/page-numbering")

    # No destination-less hero "Open PDF" button.
    assert f'href="/audits/{job_id}/pdf"' not in cat_html
    # An honest substitute action is shown instead (in-page jump, not a fake PDF link).
    assert "Read explanation" in cat_html
    assert 'href="#examples"' in cat_html


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
    rule_html = _get_html(c, f"/audits/{job_id}/problems/rule/P013")

    assert f'href="/audits/{job_id}/pdf"' not in rule_html
    assert "Read explanation" in rule_html


# ---------------------------------------------------------------------------
# 19. P063 page-known/no-highlight action wording
# ---------------------------------------------------------------------------


def test_p063_page_known_no_highlight_wording(app: tuple[TestClient, Any]) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_p063_single_appendix_finding()], page_count=80)
    page_html = _get_html(c, f"/audits/{job_id}")

    # No bbox available for this finding: no PDF button at all, explanation only.
    assert "Open PDF page" not in page_html
    assert "Open highlighted PDF page" not in page_html
    assert "/pdf/highlighted" not in page_html
    assert "Exact highlight is not available" in page_html
    assert "relevant page is known" in page_html


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

    # Scope the check to this finding's own grouped-problem card — the page
    # legitimately has one whole-document "Open PDF" download button
    # elsewhere (#open-pdf-btn), which is not the misleading per-finding
    # button this policy targets.
    card_start = main_html.index('data-rule="P025"')
    actions_end = main_html.index("Examples of this problem", card_start)
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
        assert "/pdf/highlighted" in page_html

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
            page=None,
            message="Document overview.",
            details={"issue_type": "p013_document_overview"},
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
            "Open PDF page",
            "Open highlighted PDF page",
            "Exact highlight is not available",
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
    comment = build_polished_comment(
        rule_id="P025", issue_type="missing_abstract_body", page=2, details={}
    )
    assert "Add the abstract body text directly below the ABSTRACT heading" in comment
    for unrelated in ("degree phrase", "institution", "Approval Page", "Table of Contents"):
        assert unrelated not in comment
    assert _OLD_COMBINED_P025_REMEDIATION not in comment


def test_p025_frontmatter_order_remediation_matches_only_that_issue() -> None:
    comment = build_polished_comment(
        rule_id="P025",
        issue_type="possible_frontmatter_order_issue",
        page=4,
        details={"toc_page": "6"},
    )
    assert "before the Table of Contents" in comment
    assert "Move the Abstract" in comment
    for unrelated in ("degree phrase", "institution name", "Approval Page", "abstract body text"):
        assert unrelated not in comment
    assert _OLD_COMBINED_P025_REMEDIATION not in comment


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
    # P029 (Roman-numeral sequence) has no bespoke polished_comments template,
    # so it exercises the absolute generic fallback branch. Known issue types
    # must never fall through to the old "Formatting check PXXX flagged issue
    # type ..." phrase, and the rule's catalog remediation must still be the
    # appended fix, not just a bare verify-manually instruction.
    comment = build_polished_comment(
        rule_id="P029", issue_type="roman_sequence_gap", page=5, details={}
    )
    assert _OLD_BANNED_FALLBACK_PHRASE not in comment
    assert "Formatting check" not in comment
    assert "roman numeral sequence gap" in comment.lower()
    assert "ascending sequence" in comment


def test_unhandled_issue_type_fallback_document_level_has_no_banned_phrase() -> None:
    comment = build_polished_comment(
        rule_id="P029", issue_type="roman_sequence_decrease", page=None, details={}
    )
    assert _OLD_BANNED_FALLBACK_PHRASE not in comment
    assert "document level" in comment
