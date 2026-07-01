"""Regression tests for P014 front-matter heading centering evidence and thresholds."""

from __future__ import annotations

import tempfile
from pathlib import Path

import fitz

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_headings import (
    CENTER_MEDIUM_MAX_THRESHOLD_PT,
    CENTER_REVIEW_MAX_THRESHOLD_PT,
    CENTER_SUPPRESS_THRESHOLD_PT,
    check_named_frontmatter_headings,
)


def _insert_heading_at_center_offset(
    page: fitz.Page,
    *,
    text: str,
    center_offset_pt: float,
) -> None:
    """Place a heading whose center is offset from the text-area center by *center_offset_pt*."""
    text_area_x0 = 108.0
    text_area_x1 = 540.0
    text_area_center = (text_area_x0 + text_area_x1) / 2.0
    doc = fitz.open()
    probe_page = doc.new_page(width=612, height=792)
    probe_page.insert_text((text_area_x0, 70), text, fontsize=16, fontname="Times-Bold")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        probe_path = Path(tmp.name)
    doc.save(probe_path)
    doc.close()
    probe = load_pdf_layout(str(probe_path))
    line = probe.pages[0].text_blocks[0].lines[0]
    width = line.bbox.x1 - line.bbox.x0
    desired_center = text_area_center + center_offset_pt
    x0 = desired_center - (width / 2.0)
    page.insert_text((x0, 70), text, fontsize=16, fontname="Times-Bold")
    probe_path.unlink(missing_ok=True)


def _make_heading_pdf(
    path: Path,
    *,
    text: str = "BIOGRAPHICAL SKETCH",
    center_offset_pt: float = 0.0,
    centered_textbox: bool = False,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if centered_textbox:
        page.insert_textbox(
            fitz.Rect(108, 70, 540, 110),
            text,
            fontsize=16,
            fontname="Times-Bold",
            align=fitz.TEXT_ALIGN_CENTER,
        )
    else:
        _insert_heading_at_center_offset(
            page,
            text=text,
            center_offset_pt=center_offset_pt,
        )
    doc.save(path)
    doc.close()


def _centering_findings(model) -> list:
    return [
        f
        for f in check_named_frontmatter_headings(model)
        if f.rule_id == "P014"
        and f.details.get("issue_type") == "frontmatter_heading_not_centered"
    ]


def test_centered_biographical_sketch_produces_no_p014_centering_warning(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "biosketch_centered.pdf"
    _make_heading_pdf(pdf_path, centered_textbox=True)
    model = load_pdf_layout(str(pdf_path))
    assert not _centering_findings(model)


def test_tiny_center_offset_suppresses_p014_centering_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "biosketch_tiny_offset.pdf"
    _make_heading_pdf(pdf_path, center_offset_pt=4.0)
    model = load_pdf_layout(str(pdf_path))
    assert not _centering_findings(model)


def test_borderline_center_offset_emits_needs_review_with_evidence(tmp_path: Path) -> None:
    pdf_path = tmp_path / "biosketch_borderline.pdf"
    _make_heading_pdf(pdf_path, center_offset_pt=10.0)
    model = load_pdf_layout(str(pdf_path))
    findings = _centering_findings(model)
    assert len(findings) == 1
    details = findings[0].details
    assert float(details["center_offset_pt"]) > CENTER_SUPPRESS_THRESHOLD_PT
    assert float(details["center_offset_pt"]) <= CENTER_REVIEW_MAX_THRESHOLD_PT
    assert details.get("confidence") == "review needed"
    assert details.get("center_offset_direction") in {"left", "right"}
    assert details.get("heading_center_x")
    assert details.get("text_area_center_x")
    assert details.get("centering_threshold_points") == f"{CENTER_SUPPRESS_THRESHOLD_PT:.1f}"


def test_clear_center_offset_emits_medium_confidence_with_evidence(tmp_path: Path) -> None:
    pdf_path = tmp_path / "biosketch_clear_offset.pdf"
    _make_heading_pdf(pdf_path, center_offset_pt=20.0)
    model = load_pdf_layout(str(pdf_path))
    findings = _centering_findings(model)
    assert len(findings) == 1
    details = findings[0].details
    assert float(details["center_offset_pt"]) > CENTER_REVIEW_MAX_THRESHOLD_PT
    assert float(details["center_offset_pt"]) <= CENTER_MEDIUM_MAX_THRESHOLD_PT
    assert details.get("confidence") == "medium"


def test_p014_centering_comment_includes_offset_direction_and_points() -> None:
    finding = AuditFinding(
        rule_id="P014",
        severity=Severity.WARNING,
        page=9,
        message="Named heading formatting issue.",
        details={
            "heading": "BIOGRAPHICAL SKETCH",
            "centered": "False",
            "near_top": "True",
            "bold": "True",
            "all_caps": "True",
            "issue_type": "frontmatter_heading_not_centered",
            "centering_confidence": "medium",
            "confidence": "medium",
            "center_offset_pt": "18.5",
            "center_offset_direction": "left",
            "heading_center_x": "305.5",
            "text_area_center_x": "324.0",
            "centering_threshold_points": "6.0",
            "bbox": "216.0,70.5,367.3,87.2",
            "suggested_fix": "Center the front-matter heading within the text area.",
        },
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    card = next(f for f in view.findings if f.rule_id == "P014")
    assert "18.5 pt left" in card.polished_comment
    assert "BIOGRAPHICAL SKETCH" in card.polished_comment
    assert card.suggested_fix == "Center the front-matter heading within the text area."
    assert card.confidence_level == "medium"


def test_p014_borderline_centering_does_not_use_high_confidence(tmp_path: Path) -> None:
    pdf_path = tmp_path / "biosketch_borderline_conf.pdf"
    _make_heading_pdf(pdf_path, center_offset_pt=9.0)
    model = load_pdf_layout(str(pdf_path))
    finding = _centering_findings(model)[0]
    assert finding.details.get("confidence") == "review needed"
    view = build_report_view(
        audit_findings_to_json_dict([finding], {"audit_type": "pdf"}),
    )
    card = next(f for f in view.findings if f.rule_id == "P014")
    assert card.confidence_level != "high"


def test_non_centering_p014_checks_still_emit_for_non_bold_heading(tmp_path: Path) -> None:
    pdf_path = tmp_path / "biosketch_non_bold.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(
        fitz.Rect(108, 70, 540, 110),
        "BIOGRAPHICAL SKETCH",
        fontsize=16,
        fontname="Times-Roman",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f for f in check_named_frontmatter_headings(model) if f.rule_id == "P014"
    ]
    assert findings
    assert findings[0].details.get("bold") == "False"
    assert findings[0].details.get("issue_type") == "frontmatter_heading_layout_issue"
