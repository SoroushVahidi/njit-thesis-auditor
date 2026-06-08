"""Synthetic tests for P065 — Dedication page centering and italic style checks.

All PDFs are built from scratch using PyMuPDF (fitz) with placeholder text only.
No real dissertation content, dedication text, author names, or private data is
used anywhere in this test file.  Where text strings are needed to construct the
synthetic PDF, clearly fake placeholder values are used and must not appear in
any finding detail field.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_dedication_centering_italic import (
    _ITALIC_RATIO_THRESHOLD,
    _MIN_SPANS,
    check_pdf_dedication_centering_italic,
)

# ---------------------------------------------------------------------------
# PDF construction helpers
# ---------------------------------------------------------------------------

_PAGE_W = 612.0
_PAGE_H = 792.0
# Matches LEFT_MARGIN_PT = 1.5 * 72 = 108 pt, RIGHT_MARGIN_PT = 1.0 * 72 = 72 pt
_TEXT_AREA_X0 = 108.0
_TEXT_AREA_X1 = 612.0 - 72.0  # = 540.0
_TEXT_AREA_CENTER = (_TEXT_AREA_X0 + _TEXT_AREA_X1) / 2.0  # = 324.0

_HEADING_FONT_SIZE = 14
_BODY_FONT_SIZE = 12

# Placeholder strings for synthetic test PDFs — must NOT appear in findings.
_PLACEHOLDER_1 = "Placeholder dedication line one synthetic text"
_PLACEHOLDER_2 = "Placeholder dedication line two synthetic text"
_PLACEHOLDER_3 = "Placeholder dedication line three synthetic text"


def _make_dedication_page(
    *,
    dedic_text_lines: list[tuple[float, str, str]] | None = None,
    page_number_text: str | None = None,
) -> fitz.Document:
    """Return a single-page fitz.Document with a DEDICATION heading.

    dedic_text_lines: list of (x_start, text, fontname) tuples inserted below heading.
    page_number_text: if set, inserted near the bottom as a page-number candidate.
    """
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text(
        (_TEXT_AREA_CENTER - 30, 100.0), "DEDICATION", fontsize=_HEADING_FONT_SIZE
    )
    if dedic_text_lines:
        y = 250.0
        for x, text, fname in dedic_text_lines:
            page.insert_text((x, y), text, fontname=fname, fontsize=_BODY_FONT_SIZE)
            y += 30.0
    if page_number_text is not None:
        page.insert_text(
            (_TEXT_AREA_CENTER, _PAGE_H - 40.0), page_number_text, fontsize=10
        )
    return doc


def _load(doc: fitz.Document, tmp_path: Path) -> PdfDocument:
    p = tmp_path / "test.pdf"
    doc.save(str(p))
    doc.close()
    return load_pdf_layout(str(p))


# ---------------------------------------------------------------------------
# Direct model construction helpers for fine-grained span/italic tests
# ---------------------------------------------------------------------------


def _make_span(italic: bool, font: str | None = "Helvetica") -> PdfTextSpan:
    return PdfTextSpan(
        text="placeholder span text",
        bbox=BBox(x0=200.0, y0=300.0, x1=400.0, y1=316.0),
        font=font,
        italic=italic,
    )


def _make_line_from_spans(spans: list[PdfTextSpan], y: float = 300.0) -> PdfTextLine:
    return PdfTextLine(
        spans=spans,
        bbox=BBox(x0=200.0, y0=y, x1=400.0, y1=y + 16.0),
        text=" ".join(s.text for s in spans),
    )


def _centered_bbox(y0: float, y1: float) -> BBox:
    return BBox(x0=_TEXT_AREA_CENTER - 50, y0=y0, x1=_TEXT_AREA_CENTER + 50, y1=y1)


def _make_doc_with_dedication_and_lines(
    heading_y: float,
    lines: list[PdfTextLine],
    page_w: float = _PAGE_W,
    page_h: float = _PAGE_H,
) -> PdfDocument:
    """Build a PdfDocument directly from model objects for fine-grained span control."""
    heading_span = PdfTextSpan(
        text="DEDICATION",
        bbox=BBox(x0=280.0, y0=heading_y - 16.0, x1=360.0, y1=heading_y),
        font="Helvetica",
        italic=False,
    )
    heading_line = PdfTextLine(
        spans=[heading_span],
        bbox=BBox(x0=280.0, y0=heading_y - 16.0, x1=360.0, y1=heading_y),
        text="DEDICATION",
    )
    heading_block = PdfTextBlock(
        lines=[heading_line],
        bbox=BBox(x0=280.0, y0=heading_y - 16.0, x1=360.0, y1=heading_y),
        text="DEDICATION",
    )
    text_block = PdfTextBlock(
        lines=lines,
        bbox=BBox(
            x0=min(ln.bbox.x0 for ln in lines),
            y0=min(ln.bbox.y0 for ln in lines),
            x1=max(ln.bbox.x1 for ln in lines),
            y1=max(ln.bbox.y1 for ln in lines),
        ),
        text=" ".join(ln.text for ln in lines),
    )
    page = PdfPage(
        page_number=1,
        width=page_w,
        height=page_h,
        text_blocks=[heading_block, text_block],
    )
    return PdfDocument(path="synthetic_test.pdf", pages=[page])


def _set_bbox(line: PdfTextLine, bbox: BBox) -> PdfTextLine:
    """Return a copy of line with the given bbox (Pydantic v2 model_copy)."""
    return line.model_copy(update={"bbox": bbox})


# ---------------------------------------------------------------------------
# Test 1 — No dedication page → no findings
# ---------------------------------------------------------------------------


def test_no_dedication_page_no_findings(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((200.0, 400.0), "ABSTRACT", fontsize=_HEADING_FONT_SIZE)
    page.insert_text(
        (200.0, 450.0), "Placeholder abstract content here.", fontsize=_BODY_FONT_SIZE
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 2 — Centered and italic dedication → no findings
# ---------------------------------------------------------------------------


def test_centered_italic_dedication_no_findings() -> None:
    heading_y = 120.0
    spans = [_make_span(italic=True) for _ in range(3)]
    lines = [
        _set_bbox(
            _make_line_from_spans([spans[i]], y=250.0 + i * 30.0),
            _centered_bbox(250.0 + i * 30.0, 266.0 + i * 30.0),
        )
        for i in range(3)
    ]
    pdf_doc = _make_doc_with_dedication_and_lines(heading_y, lines)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 3 — Off-center dedication → dedication_text_not_centered
# ---------------------------------------------------------------------------


def test_off_center_dedication_emits_centering_finding(tmp_path: Path) -> None:
    off_center_x = _TEXT_AREA_X0  # flush left = maximally off-center
    doc = _make_dedication_page(
        dedic_text_lines=[
            (off_center_x, _PLACEHOLDER_1, "helv"),
            (off_center_x, _PLACEHOLDER_2, "helv"),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    centering = [
        f for f in findings
        if f.details.get("issue_type") == "dedication_text_not_centered"
    ]
    assert len(centering) == 1
    d = centering[0].details
    assert d["issue_type"] == "dedication_text_not_centered"
    # Privacy: placeholder text must not appear in any finding detail value.
    for v in d.values():
        assert _PLACEHOLDER_1 not in v
        assert _PLACEHOLDER_2 not in v


# ---------------------------------------------------------------------------
# Test 4 — Non-italic (roman) dedication → dedication_text_not_italic
# ---------------------------------------------------------------------------


def test_non_italic_dedication_emits_italic_finding() -> None:
    heading_y = 120.0
    spans = [_make_span(italic=False) for _ in range(3)]
    lines = [
        _set_bbox(
            _make_line_from_spans([spans[i]], y=250.0 + i * 30.0),
            _centered_bbox(250.0 + i * 30.0, 266.0 + i * 30.0),
        )
        for i in range(3)
    ]
    pdf_doc = _make_doc_with_dedication_and_lines(heading_y, lines)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    italic_findings = [
        f for f in findings
        if f.details.get("issue_type") == "dedication_text_not_italic"
    ]
    assert len(italic_findings) == 1
    d = italic_findings[0].details
    assert float(d["italic_span_ratio"]) < _ITALIC_RATIO_THRESHOLD


# ---------------------------------------------------------------------------
# Test 5 — Both off-center and non-italic → two findings
# ---------------------------------------------------------------------------


def test_both_off_center_and_non_italic_emits_two_findings() -> None:
    heading_y = 120.0
    spans = [_make_span(italic=False) for _ in range(3)]
    lines = [
        _set_bbox(
            _make_line_from_spans([spans[i]], y=250.0 + i * 30.0),
            BBox(
                x0=_TEXT_AREA_X0,
                y0=250.0 + i * 30.0,
                x1=_TEXT_AREA_X0 + 100.0,
                y1=266.0 + i * 30.0,
            ),
        )
        for i in range(3)
    ]
    pdf_doc = _make_doc_with_dedication_and_lines(heading_y, lines)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    issue_types = {f.details.get("issue_type") for f in findings}
    assert "dedication_text_not_centered" in issue_types
    assert "dedication_text_not_italic" in issue_types


# ---------------------------------------------------------------------------
# Test 6 — Too few lines → centering skipped
# ---------------------------------------------------------------------------


def test_too_few_lines_skips_centering() -> None:
    heading_y = 120.0
    span = _make_span(italic=False)
    line = _set_bbox(
        _make_line_from_spans([span], y=250.0),
        BBox(x0=_TEXT_AREA_X0, y0=250.0, x1=_TEXT_AREA_X0 + 50.0, y1=266.0),
    )
    pdf_doc = _make_doc_with_dedication_and_lines(heading_y, [line])
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    centering = [
        f for f in findings
        if f.details.get("issue_type") == "dedication_text_not_centered"
    ]
    assert len(centering) == 0


# ---------------------------------------------------------------------------
# Test 7 — Too few spans → italic check skipped
# ---------------------------------------------------------------------------


def test_too_few_spans_skips_italic() -> None:
    heading_y = 120.0
    span_count = _MIN_SPANS - 1
    spans = [_make_span(italic=False) for _ in range(span_count)]
    lines = [
        _set_bbox(
            _make_line_from_spans([spans[i]], y=250.0 + i * 30.0),
            _centered_bbox(250.0 + i * 30.0, 266.0 + i * 30.0),
        )
        for i in range(span_count)
    ]
    pdf_doc = _make_doc_with_dedication_and_lines(heading_y, lines)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    italic_findings = [
        f for f in findings
        if f.details.get("issue_type") == "dedication_text_not_italic"
    ]
    assert len(italic_findings) == 0


# ---------------------------------------------------------------------------
# Test 8 — All spans have font=None → italic check skipped
# ---------------------------------------------------------------------------


def test_all_none_font_skips_italic() -> None:
    heading_y = 120.0
    spans = [_make_span(italic=False, font=None) for _ in range(4)]
    lines = [
        _set_bbox(
            _make_line_from_spans([spans[i]], y=250.0 + i * 30.0),
            _centered_bbox(250.0 + i * 30.0, 266.0 + i * 30.0),
        )
        for i in range(4)
    ]
    pdf_doc = _make_doc_with_dedication_and_lines(heading_y, lines)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    italic_findings = [
        f for f in findings
        if f.details.get("issue_type") == "dedication_text_not_italic"
    ]
    assert len(italic_findings) == 0


# ---------------------------------------------------------------------------
# Test 9 — Image-only page (no text blocks) → no findings
# ---------------------------------------------------------------------------


def test_image_only_page_no_findings(tmp_path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=_PAGE_W, height=_PAGE_H)
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 10 — Multiple DEDICATION headings → skip (ambiguous)
# ---------------------------------------------------------------------------


def test_multiple_dedication_headings_skips(tmp_path: Path) -> None:
    doc = fitz.open()
    p1 = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    p1.insert_text((_TEXT_AREA_CENTER - 30, 100.0), "DEDICATION", fontsize=14)
    p1.insert_text((_TEXT_AREA_X0, 250.0), _PLACEHOLDER_1, fontsize=12)
    p2 = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    p2.insert_text((_TEXT_AREA_CENTER - 30, 100.0), "DEDICATION", fontsize=14)
    p2.insert_text((_TEXT_AREA_X0, 250.0), _PLACEHOLDER_2, fontsize=12)
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 11 — DEDICATION heading excluded from text block metrics
# ---------------------------------------------------------------------------


def test_dedication_heading_excluded_from_metrics() -> None:
    """The DEDICATION heading line must not count toward dedication text lines."""
    heading_y = 120.0
    heading_span = PdfTextSpan(
        text="DEDICATION",
        bbox=BBox(x0=280.0, y0=heading_y - 16.0, x1=360.0, y1=heading_y),
        font="Helvetica",
        italic=False,
    )
    heading_line = PdfTextLine(
        spans=[heading_span],
        bbox=BBox(x0=280.0, y0=heading_y - 16.0, x1=360.0, y1=heading_y),
        text="DEDICATION",
    )
    heading_block = PdfTextBlock(
        lines=[heading_line],
        bbox=BBox(x0=280.0, y0=heading_y - 16.0, x1=360.0, y1=heading_y),
        text="DEDICATION",
    )
    # Only 1 real text line — centering check should skip (< _MIN_TEXT_LINES).
    text_span = _make_span(italic=False)
    text_line = _set_bbox(
        _make_line_from_spans([text_span], y=250.0),
        BBox(x0=_TEXT_AREA_X0, y0=250.0, x1=_TEXT_AREA_X0 + 100.0, y1=266.0),
    )
    text_block = PdfTextBlock(
        lines=[text_line],
        bbox=text_line.bbox,
        text=text_line.text,
    )
    page = PdfPage(
        page_number=1,
        width=_PAGE_W,
        height=_PAGE_H,
        text_blocks=[heading_block, text_block],
    )
    pdf_doc = PdfDocument(path="synthetic_test.pdf", pages=[page])
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    centering = [
        f for f in findings
        if f.details.get("issue_type") == "dedication_text_not_centered"
    ]
    assert len(centering) == 0


# ---------------------------------------------------------------------------
# Test 12 — Page number/footer excluded from metrics
# ---------------------------------------------------------------------------


def test_page_number_footer_excluded_from_metrics(tmp_path: Path) -> None:
    """Page-number candidates near the bottom must not count as dedication text."""
    doc = _make_dedication_page(
        dedic_text_lines=[
            (_TEXT_AREA_X0, _PLACEHOLDER_1, "helv"),
            (_TEXT_AREA_X0, _PLACEHOLDER_2, "helv"),
        ],
        page_number_text="iv",
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    for f in findings:
        for v in f.details.values():
            # "iv" as a raw page-number string must not appear in metric fields.
            assert v != "iv"


# ---------------------------------------------------------------------------
# Test 13 — Privacy: no placeholder text in findings
# ---------------------------------------------------------------------------


def test_no_dedication_text_in_findings(tmp_path: Path) -> None:
    """Finding detail values must not contain dedication text content."""
    doc = _make_dedication_page(
        dedic_text_lines=[
            (_TEXT_AREA_X0, _PLACEHOLDER_1, "helv"),
            (_TEXT_AREA_X0, _PLACEHOLDER_2, "helv"),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    for f in findings:
        for v in f.details.values():
            assert _PLACEHOLDER_1 not in v
            assert _PLACEHOLDER_2 not in v
            assert "synthetic" not in v.lower()
            assert "placeholder" not in v.lower()


# ---------------------------------------------------------------------------
# Test 14 — Italic font (oblique) recognized → no italic finding
# ---------------------------------------------------------------------------


def test_italic_font_recognized_no_italic_finding(tmp_path: Path) -> None:
    """Text using Helvetica-Oblique (heit) must be detected as italic."""
    doc = _make_dedication_page(
        dedic_text_lines=[
            (_TEXT_AREA_CENTER - 50, _PLACEHOLDER_1, "heit"),
            (_TEXT_AREA_CENTER - 50, _PLACEHOLDER_2, "heit"),
            (_TEXT_AREA_CENTER - 50, _PLACEHOLDER_3, "heit"),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    italic_findings = [
        f for f in findings
        if f.details.get("issue_type") == "dedication_text_not_italic"
    ]
    assert len(italic_findings) == 0


# ---------------------------------------------------------------------------
# Test 15 — Rule ID is P065 on all findings
# ---------------------------------------------------------------------------


def test_finding_rule_id_is_p065(tmp_path: Path) -> None:
    doc = _make_dedication_page(
        dedic_text_lines=[
            (_TEXT_AREA_X0, _PLACEHOLDER_1, "helv"),
            (_TEXT_AREA_X0, _PLACEHOLDER_2, "helv"),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    for f in findings:
        assert f.rule_id == "P065"
