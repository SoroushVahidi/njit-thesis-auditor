"""Regression tests for P015 equation-continuation indent suppression."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfTextLine
from njit_auditor.rules.pdf_indentation import (
    _is_displayed_equation_line,
    _paragraph_highlight_bbox,
    check_pdf_indentation,
    group_lines_into_paragraphs,
)


def _draw_indented_paragraph(page: fitz.Page, y: float, lines: int = 3) -> None:
    page.insert_text((190, y), "This is a synthetic paragraph line for indentation checks.")
    for idx in range(1, lines):
        page.insert_text((108, y + (idx * 14)), "Continuation synthetic paragraph line text.")


def _draw_flush_paragraph(page: fitz.Page, y: float, first_line: str, lines: int = 4) -> None:
    page.insert_text((108, y), first_line)
    for idx in range(1, lines):
        page.insert_text(
            (108, y + (idx * 14)),
            "Continuation synthetic paragraph line text for indentation checks.",
        )


def _make_equation_continuation_pdf(path: Path, *, first_line: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_indented_paragraph(page, y=120)
    _draw_indented_paragraph(page, y=190)
    _draw_indented_paragraph(page, y=260)
    page.insert_text((220, 330), "fθ(x): R³ → R,", fontsize=11)
    _draw_flush_paragraph(page, y=360, first_line=first_line)
    doc.save(path)
    doc.close()


def test_displayed_equation_line_detected() -> None:
    line = PdfTextLine(
        text="fθ(x): R³ → R,",
        bbox=BBox(x0=220, y0=330, x1=360, y1=345),
        spans=[],
    )
    assert _is_displayed_equation_line(line)


def test_equation_followed_by_where_suppresses_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "equation_where.pdf"
    _make_equation_continuation_pdf(
        pdf_path,
        first_line="where the underlying surface is defined as the zero level set f(x) = 0.",
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_equation_followed_by_with_suppresses_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "equation_with.pdf"
    _make_equation_continuation_pdf(
        pdf_path,
        first_line="with the underlying surface defined as the zero level set f(x) = 0.",
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_equation_followed_by_such_that_suppresses_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "equation_such_that.pdf"
    _make_equation_continuation_pdf(
        pdf_path,
        first_line="such that the underlying surface is defined as the zero level set.",
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_equation_followed_by_normal_paragraph_may_still_warn(tmp_path: Path) -> None:
    pdf_path = tmp_path / "equation_normal_para.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_indented_paragraph(page, y=120)
    _draw_indented_paragraph(page, y=190)
    _draw_indented_paragraph(page, y=260)
    page.insert_text((220, 330), "fθ(x): R³ → R,", fontsize=11)
    _draw_flush_paragraph(
        page,
        y=360,
        first_line="This paragraph begins a new topic after the displayed equation above.",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert findings
    assert findings[0].details.get("issue_type") == "missing_later_indent"
    assert findings[0].details.get("confidence") == "high"


def test_where_without_preceding_equation_still_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "where_no_equation.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_indented_paragraph(page, y=120)
    _draw_indented_paragraph(page, y=190)
    _draw_indented_paragraph(page, y=260)
    _draw_flush_paragraph(
        page,
        y=330,
        first_line="where the underlying surface is defined as the zero level set f(x) = 0.",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert findings


def test_paragraph_highlight_bbox_includes_wrapped_first_line() -> None:
    first = PdfTextLine(
        text="where",
        bbox=BBox(x0=108, y0=360, x1=140, y1=374),
        spans=[],
    )
    second = PdfTextLine(
        text="the underlying surface is defined as the zero level set.",
        bbox=BBox(x0=108, y0=378, x1=500, y1=392),
        spans=[],
    )
    bbox = _paragraph_highlight_bbox([first, second])
    assert bbox[2] - bbox[0] > 140


def test_grouped_equation_continuation_paragraph_is_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "equation_grouping.pdf"
    _make_equation_continuation_pdf(
        pdf_path,
        first_line="where the underlying surface is defined as the zero level set f(x) = 0.",
    )
    model = load_pdf_layout(str(pdf_path))
    page = model.pages[0]
    paragraphs = group_lines_into_paragraphs(page)
    assert paragraphs
    assert any(
        line.text.lower().startswith("where")
        for paragraph in paragraphs
        for line in paragraph
    )
