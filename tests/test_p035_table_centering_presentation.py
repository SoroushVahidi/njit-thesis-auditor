"""Regression tests for P035 table-body centering presentation."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout

_TABLE_CAPTION = "Table 4.2 Example table caption title for layout testing here."
_ATOMIC_FIX = (
    "Center the table body within the text area between the left and right margins."
)
_FORBIDDEN_FIX_TOKENS = (
    "figure caption",
    "table caption",
    "caption above",
    "caption below",
)


def _draw_table_rows(
    page: fitz.Page,
    *,
    x0: float,
    y_start: float,
    rows: int,
    row_height: float = 18.0,
) -> None:
    for idx in range(rows):
        page.insert_text(
            (x0, y_start + idx * row_height),
            f"Row {idx + 1} column alpha and column beta values",
            fontsize=11,
        )


def _make_split_table_body_pdf(path: Path) -> None:
    """Simulate a table extracted as two vertically stacked row clusters."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 4 RESULTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 200.0), _TABLE_CAPTION, fontsize=11)
    _draw_table_rows(page, x0=108.0, y_start=240.0, rows=2)
    # 30pt gap keeps clusters separate for PyMuPDF but within merge threshold.
    _draw_table_rows(page, x0=108.0, y_start=306.0, rows=3)
    doc.save(path)
    doc.close()


def _finding_view(
    issue_type: str,
    *,
    float_number: str = "4.2",
    details: dict[str, str] | None = None,
):
    payload_details = {
        "issue_type": issue_type,
        "float_type": "table",
        "float_number": float_number,
        "confidence": "medium",
        "center_delta_points": "24.0",
        "allowed_center_delta_points": "15",
        "table_center_x": "180.0",
        "text_area_center_x": "306.0",
        "body_bbox": "108.0,240.0,420.0,360.0",
        "bbox": "108.0,240.0,420.0,360.0",
    }
    if details:
        payload_details.update(details)
    finding = AuditFinding(
        rule_id="P035",
        severity=Severity.WARNING,
        page=48,
        message="Table body centering issue.",
        details=payload_details,
    )
    report = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(report)
    return next(f for f in view.findings if f.issue_type == issue_type)


def test_table_body_not_centered_suggested_fix_is_atomic() -> None:
    rendered = _finding_view("table_body_not_centered")
    assert rendered.suggested_fix == _ATOMIC_FIX
    lower = rendered.suggested_fix.lower()
    for token in _FORBIDDEN_FIX_TOKENS:
        assert token not in lower


def test_table_body_not_centered_comment_mentions_table_number() -> None:
    rendered = _finding_view("table_body_not_centered")
    assert "Table 4.2" in rendered.polished_comment
    assert "centered within the text area" in rendered.polished_comment.lower()


def test_table_caption_placement_fix_remains_separate() -> None:
    rendered = _finding_view("table_caption_not_above_body")
    assert "caption above" in rendered.suggested_fix.lower()
    assert rendered.suggested_fix != _ATOMIC_FIX


def test_centered_table_body_produces_no_p035_centering_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "centered_table.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 4 RESULTS", fontsize=14, fontname="Times-Bold")
    for idx in range(4):
        y0 = 240.0 + idx * 18.0
        page.insert_textbox(
            fitz.Rect(108, y0 - 15, 540, y0 + 5),
            f"Row {idx + 1} column alpha and column beta values",
            fontsize=11,
            align=fitz.TEXT_ALIGN_CENTER,
        )
    page.insert_text((108, 200.0), _TABLE_CAPTION, fontsize=11)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_figure_table_layout(model)
    assert not any(f.details.get("issue_type") == "table_body_not_centered" for f in findings)


def test_off_center_table_body_produces_centering_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "off_center_table.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 4 RESULTS", fontsize=14, fontname="Times-Bold")
    _draw_table_rows(page, x0=108.0, y_start=240.0, rows=4)
    page.insert_text((108, 200.0), _TABLE_CAPTION, fontsize=11)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_figure_table_layout(model)
        if f.details.get("issue_type") == "table_body_not_centered"
    ]
    assert len(findings) == 1
    assert findings[0].details.get("confidence") == "medium"
    assert findings[0].details.get("center_delta_points")
    assert findings[0].details.get("table_center_x")
    assert findings[0].details.get("text_area_center_x")


def test_split_table_body_highlight_covers_full_body(tmp_path: Path) -> None:
    pdf_path = tmp_path / "split_table_body.pdf"
    _make_split_table_body_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_figure_table_layout(model)
        if f.details.get("issue_type") == "table_body_not_centered"
    ]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details.get("body_bbox")

    body_bbox = finding.details["body_bbox"]
    parts = [float(part) for part in body_bbox.split(",")]
    y0, y1 = parts[1], parts[3]
    assert y1 - y0 >= 90.0, (
        "Highlight should cover header and data rows, not only the header cluster"
    )

    boxes = parse_highlight_bboxes_from_details(
        finding.details,
        rule_id="P035",
        issue_type="table_body_not_centered",
    )
    assert len(boxes) == 1
    assert boxes[0][3] - boxes[0][1] >= 90.0
