"""Synthetic P019 folio evidence when PDF extraction groups body and footer."""

from __future__ import annotations

import pytest

from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextLine
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    detect_page_number_candidates,
)


def _line(text: str, x0: float, x1: float, y0: float) -> PdfTextLine:
    return PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y0 + 12))


def _page(number: int, folio: str | None, *, mixed: bool = False,
          unreadable: bool = False) -> PdfPage:
    body = _line("A synthetic paragraph.", 108, 490, 180)
    lines = [body]
    if folio is not None:
        lines.append(_line(folio, 298, 314, 745))
    if mixed:
        blocks = [PdfTextBlock(lines=lines, bbox=BBox(x0=108, y0=180, x1=490, y1=757), text="")]
    else:
        blocks = [PdfTextBlock(lines=[line], bbox=line.bbox, text=line.text) for line in lines]
    return PdfPage(page_number=number, width=612, height=792,
                   text_blocks=blocks, text_extraction_unavailable=unreadable)


def _missing(doc: PdfDocument) -> list[int | None]:
    return [finding.page for finding in check_pdf_page_number_sequence(doc)
            if finding.details.get("issue_type") == "missing_page_number"]


@pytest.mark.parametrize("folios", [("1", "2", "3"), ("i", "ii", "iii")])
def test_visible_expected_folio_inside_body_block_is_not_missing(
    folios: tuple[str, str, str],
) -> None:
    doc = PdfDocument(path="synthetic.pdf", pages=[
        _page(1, folios[0]), _page(2, folios[1], mixed=True), _page(3, folios[2])
    ])
    assert not [c for c in detect_page_number_candidates(doc) if c.page_number == 2]
    assert _missing(doc) == []


def test_genuinely_absent_folio_still_warns() -> None:
    doc = PdfDocument(path="synthetic.pdf", pages=[
        _page(1, "1"), _page(2, None, mixed=True), _page(3, "3")
    ])
    assert _missing(doc) == [2]


def test_unreadable_folio_page_is_ambiguous_and_does_not_warn() -> None:
    doc = PdfDocument(path="synthetic.pdf", pages=[
        _page(1, "1"), _page(2, None, mixed=True, unreadable=True), _page(3, "3")
    ])
    assert _missing(doc) == []


def test_roman_to_arabic_boundary_does_not_claim_a_missing_folio() -> None:
    doc = PdfDocument(path="synthetic.pdf", pages=[
        _page(1, "ii"), _page(2, None), _page(3, "1")
    ])
    assert _missing(doc) == []


def test_wrong_folio_value_inside_body_block_does_not_hide_missing_number() -> None:
    doc = PdfDocument(path="synthetic.pdf", pages=[
        _page(1, "1"), _page(2, "9", mixed=True), _page(3, "3")
    ])
    assert _missing(doc) == [2]
