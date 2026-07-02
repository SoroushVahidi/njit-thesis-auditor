"""Regression tests for P018 List-of-Tables row page-number association.

Synthetic fixtures only — no private dissertation content.
"""

from __future__ import annotations

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
from njit_auditor.rules.pdf_toc_alignment import (
    TocPageContext,
    check_pdf_toc_alignment,
    extract_toc_entry_lines,
)

_PAGE_W = 612.0
_PAGE_H = 792.0
_MARGIN_L = 108.0
_RIGHT_COL = 500.0


def _make_line(
    text: str,
    y: float,
    *,
    x0: float = _MARGIN_L,
    x1: float = 420.0,
) -> PdfTextLine:
    bbox = BBox(x0=x0, y0=y, x1=x1, y1=y + 14.0)
    span = PdfTextSpan(text=text, bbox=bbox, font="Helvetica", size=12.0)
    return PdfTextLine(spans=[span], bbox=bbox, text=text)


def _make_line_from_spans(spans: list[PdfTextSpan], y: float) -> PdfTextLine:
    bbox = BBox(
        x0=min(span.bbox.x0 for span in spans),
        y0=y,
        x1=max(span.bbox.x1 for span in spans),
        y1=y + 14.0,
    )
    return PdfTextLine(spans=spans, bbox=bbox, text="".join(span.text for span in spans))


def _make_page(page_number: int, lines: list[PdfTextLine], *, heading: str) -> PdfPage:
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(
            x0=min(line.bbox.x0 for line in lines),
            y0=min(line.bbox.y0 for line in lines),
            x1=max(line.bbox.x1 for line in lines),
            y1=max(line.bbox.y1 for line in lines),
        ),
        text="\n".join(line.text for line in lines),
    )
    return PdfPage(
        page_number=page_number,
        width=_PAGE_W,
        height=_PAGE_H,
        text_blocks=[block],
    )


def _lot_context(page: PdfPage, heading_y: float = 90.0) -> TocPageContext:
    return TocPageContext(page=page, page_type="list_of_tables", heading_bottom_y=heading_y)


def _p018_missing_page_findings(doc: PdfDocument) -> list:
    return [
        finding
        for finding in check_pdf_toc_alignment(doc)
        if finding.rule_id == "P018" and finding.details.get("issue_type") == "missing_page_number"
    ]


def test_lot_entry_with_split_title_and_leader_page_fragment_on_same_row() -> None:
    y = 134.8
    page = _make_page(
        14,
        heading="LIST OF TABLES",
        lines=[
            _make_line("LIST OF TABLES", 90.0, x1=300.0),
            _make_line(
                "4.1 Alignment of Research Questions and Survey Items",
                y,
                x0=120.9,
                x1=391.2,
            ),
            _make_line("........................ 31", y, x0=300.0, x1=520.0),
            _make_line("4.2 Synthetic Table Title B .... 32", 155.0, x1=520.0),
            _make_line("4.3 Synthetic Table Title C .... 33", 175.0, x1=520.0),
            _make_line("4.4 Synthetic Table Title D .... 34", 195.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_lot_context(page))
    target = next(
        entry
        for entry in entries
        if "Alignment of Research Questions" in entry.cleaned_text
    )
    assert target.page_number_token == "31"
    assert not _p018_missing_page_findings(PdfDocument(path="synthetic.pdf", pages=[page]))


def test_lot_entry_with_right_column_page_span_on_same_line() -> None:
    y = 134.8
    title_span = PdfTextSpan(
        text="4.1 Alignment of Research Questions and Survey Items",
        bbox=BBox(x0=120.9, y0=y, x1=391.2, y1=y + 14.0),
    )
    page_span = PdfTextSpan(
        text="31",
        bbox=BBox(x0=_RIGHT_COL, y0=y, x1=520.0, y1=y + 14.0),
    )
    page = _make_page(
        14,
        heading="LIST OF TABLES",
        lines=[
            _make_line("LIST OF TABLES", 90.0, x1=300.0),
            _make_line_from_spans([title_span, page_span], y),
            _make_line("4.2 Synthetic Table Title B .... 32", 155.0, x1=520.0),
            _make_line("4.3 Synthetic Table Title C .... 33", 175.0, x1=520.0),
            _make_line("4.4 Synthetic Table Title D .... 34", 195.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_lot_context(page))
    target = next(
        entry
        for entry in entries
        if "Alignment of Research Questions" in entry.cleaned_text
    )
    assert target.page_number_token == "31"
    assert not _p018_missing_page_findings(PdfDocument(path="synthetic.pdf", pages=[page]))


def test_lot_entry_without_trailing_page_number_still_warns() -> None:
    page = _make_page(
        14,
        heading="LIST OF TABLES",
        lines=[
            _make_line("LIST OF TABLES", 90.0, x1=300.0),
            _make_line("4.1 Synthetic Table Title A .... 31", 120.0, x1=520.0),
            _make_line("4.2 Synthetic Table Title B", 140.0, x1=420.0),
            _make_line("4.3 Synthetic Table Title C .... 33", 160.0, x1=520.0),
            _make_line("4.4 Synthetic Table Title D .... 34", 180.0, x1=520.0),
        ],
    )
    findings = _p018_missing_page_findings(PdfDocument(path="synthetic.pdf", pages=[page]))
    assert findings
    assert findings[0].details.get("worst_entry_index") == "1"


def test_lot_entry_number_prefix_without_page_number_is_not_valid() -> None:
    page = _make_page(
        14,
        heading="LIST OF TABLES",
        lines=[
            _make_line("LIST OF TABLES", 90.0, x1=300.0),
            _make_line("4.1 Synthetic Table Title A", 120.0, x1=420.0),
            _make_line("4.2 Synthetic Table Title B .... 32", 140.0, x1=520.0),
            _make_line("4.3 Synthetic Table Title C .... 33", 160.0, x1=520.0),
            _make_line("4.4 Synthetic Table Title D .... 34", 180.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_lot_context(page))
    target = next(entry for entry in entries if entry.cleaned_text.startswith("4.1"))
    assert target.page_number_token is None
    assert _p018_missing_page_findings(PdfDocument(path="synthetic.pdf", pages=[page]))


def test_toc_shared_parser_accepts_leader_fragment_row(tmp_path) -> None:
    pdf_path = tmp_path / "toc_leader_fragment_row.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16)
    y = 140.0
    page.insert_text((108, y), "1 LOREM SECTION WITH LONG WRAPPED TITLE TEXT")
    page.insert_text((300, y), "........................ 12")
    page.insert_text((108, 160), "2 LOREM SECTION BETA .... 24")
    page.insert_text((108, 180), "3 LOREM SECTION GAMMA .... 36")
    page.insert_text((108, 200), "4 LOREM SECTION DELTA .... 48")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = _p018_missing_page_findings(model)
    assert not findings
