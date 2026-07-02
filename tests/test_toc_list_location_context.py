"""Tests for TOC/list location labels, entry previews, and P036 gap highlights."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_highlight import is_drawable_bbox
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.polished_comments import build_polished_comment, contains_blocked_detail_text
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, enriched_pdf_location_label
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    check_pdf_lot_lof_entry_number_alignment,
)
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.toc_list_student_preview import (
    gap_bbox_between_boxes,
    sanitize_toc_list_entry_preview,
)

_BBOX_STRING_RE = re.compile(r"^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$")


def _make_tight_toc_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 140), "Chapter 3 Literature Review and Background ....", fontsize=12)
    page.insert_text((500, 140), "10", fontsize=12)
    page.insert_text((108, 170), "Chapter 4 Extended Dissertation Topic Title ....", fontsize=12)
    page.insert_text((500, 170), "12", fontsize=12)
    doc.save(path)
    doc.close()


def _make_misaligned_toc_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    entries = [
        ("CHAPTER 1 INTRODUCTION TO THE STUDY AND ITS SCOPE ....", 108, 500),
        ("CHAPTER 2 BACKGROUND AND RELATED WORK OVERVIEW ....", 108, 500),
        ("CHAPTER 3 METHODOLOGY AND RESEARCH DESIGN OVERVIEW ....", 130, 500),
        ("CHAPTER 4 RESULTS AND DISCUSSION OVERVIEW SECTION ....", 108, 500),
    ]
    for idx, (label, x, page_x) in enumerate(entries):
        y = 130 + idx * 24
        page.insert_text((x, y), label)
        page.insert_text((page_x, y), "12")
    doc.save(path)
    doc.close()


def _parse_bbox(bbox_str: str) -> tuple[float, float, float, float]:
    parts = [float(part) for part in bbox_str.split(",")]
    assert len(parts) == 4
    return (parts[0], parts[1], parts[2], parts[3])


def test_p036_gap_bbox_is_drawable_and_between_entry_lines(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_gap_bbox.pdf"
    _make_tight_toc_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    finding = next(f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036")

    bbox_str = finding.details.get("bbox")
    assert bbox_str is not None
    assert _BBOX_STRING_RE.match(bbox_str)
    bbox = _parse_bbox(bbox_str)
    assert is_drawable_bbox(bbox)

    assert finding.details.get("previous_entry_preview")
    assert finding.details.get("next_entry_preview")
    assert "Chapter 3" in finding.details["previous_entry_preview"]
    assert "Chapter 4" in finding.details["next_entry_preview"]


def test_p036_finding_view_highlights_gap_with_entry_snippets(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_gap_actionability.pdf"
    _make_tight_toc_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    finding = next(f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036")
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    fv = view.findings[0]

    assert fv.has_highlight is True
    assert fv.action_kind == "highlight"
    assert fv.action_label == "Open highlighted PDF page"
    assert "between 'Chapter 3" in fv.location_label
    assert "Chapter 4" in fv.location_label
    assert "entries 1-2" not in fv.location_label.lower()

    assert "Chapter 3" in fv.location_label
    assert "Chapter 4" in fv.location_label
    assert "visible double spacing" in fv.polished_comment.lower()
    assert "Add visible double spacing" in fv.suggested_fix
    assert "entries 1-2" not in fv.polished_comment.lower()

    comment = build_polished_comment(
        rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
        page=finding.page,
        details=finding.details,
    )
    assert "Chapter 3 Literature Review" not in comment
    assert contains_blocked_detail_text(comment, finding.details) is False


def test_p036_fallback_wording_without_previews() -> None:
    finding = AuditFinding(
        rule_id="P036",
        severity=Severity.WARNING,
        page=12,
        message="Tight spacing.",
        details={
            "issue_type": "toc_inter_entry_spacing_too_tight",
            "section_type": "table_of_contents",
            "entry_pair_index": "4",
            "gap_points": "3.0",
            "required_gap_points": "9.0",
        },
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    fv = view.findings[0]
    assert "visible double spacing" in fv.polished_comment.lower()
    assert fv.location_label == "Page 12 — Table of Contents, spacing between entries 5-6"


def test_p018_location_uses_affected_entry_preview() -> None:
    finding = AuditFinding(
        rule_id="P018",
        severity=Severity.WARNING,
        page=12,
        message="Indent outlier.",
        details={
            "page_type": "table_of_contents",
            "issue_type": "inconsistent_hierarchy_indent",
            "worst_entry_index": "2",
            "affected_entry_count": "1",
            "affected_entry_preview": "Chapter 3 Methodology Overview",
        },
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    fv = view.findings[0]
    assert 'entry "chapter 3 methodology overview"' in fv.location_label.lower()
    assert "Chapter 3 Methodology Overview" in fv.location_label
    assert "same level" in fv.suggested_fix.lower()


def test_p046_location_uses_affected_entry_preview(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p046_preview.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 115), "Table")
    page.insert_text((500, 115), "Page")
    entries = [
        ("Table 1 Synthetic experimental setup overview entry text here.", 108.0),
        ("Table 2 Synthetic model performance comparison entry text here.", 130.0),
        ("Table 3 Synthetic regression coefficients overview entry text.", 108.0),
    ]
    for idx, (label, x) in enumerate(entries):
        y = 140 + idx * 20
        page.insert_text((x, y), label)
        page.insert_text((500, y), "12")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    finding = next(
        f for f in check_pdf_lot_lof_entry_number_alignment(model) if f.rule_id == "P046"
    )
    assert finding.details.get("affected_entry_preview")
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    fv = view.findings[0]
    assert "Table 2 Synthetic" in fv.location_label
    assert "entry 2" not in fv.location_label.lower()


def test_sanitize_preview_truncates_long_text() -> None:
    long_text = "Chapter 9 " + ("Extended dissertation topic wording " * 8)
    preview = sanitize_toc_list_entry_preview(long_text)
    assert len(preview) <= 72
    assert preview.endswith("...")


def test_gap_bbox_helper_requires_positive_vertical_gap() -> None:
    from njit_auditor.pdf_models import BBox

    last = BBox(x0=108.0, y0=140.0, x1=400.0, y1=152.0)
    first = BBox(x0=108.0, y0=152.0, x1=420.0, y1=164.0)
    assert gap_bbox_between_boxes(last, first) is None


def test_markdown_p036_uses_entry_snippets_not_index_only(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_markdown_snippets.pdf"
    _make_tight_toc_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    finding = next(f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036")
    md_path = tmp_path / "report.md"
    write_markdown_report([finding], {"audit_type": "pdf"}, md_path)
    text = md_path.read_text(encoding="utf-8")
    assert "Chapter 3" in text
    assert "Chapter 4" in text
    assert "entries 1-2" not in text.lower()


def test_enriched_location_p024_uses_line_preview_safely() -> None:
    secret = "Synthetic private toc entry marker phrase XYZ"
    label = enriched_pdf_location_label(
        "P024",
        "toc_level_capitalization",
        {
            "page_type": "table_of_contents",
            "entry_index": "1",
            "line_preview": secret,
        },
        8,
    )
    assert secret in label
    assert "affected entry:" in label.lower()
