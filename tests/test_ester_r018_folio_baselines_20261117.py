"""Synthetic P018 folio association when PDF glyph boxes differ on one baseline."""

from __future__ import annotations

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_alignment import (
    check_pdf_toc_alignment,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)


def _line(text: str, x0: float, x1: float, y0: float, y1: float, baseline: float) -> PdfTextLine:
    box = BBox(x0=x0, y0=y0, x1=x1, y1=y1)
    return PdfTextLine(
        text=text,
        bbox=box,
        baseline_y=baseline,
        spans=[PdfTextSpan(text=text, bbox=box, baseline_y=baseline, size=12)],
    )


def _doc(heading: str, rows: list[PdfTextLine]) -> PdfDocument:
    lines = [_line(heading, 210, 405, 80, 98, 94), *rows]
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=550, y1=max(line.bbox.y1 for line in lines)),
        text="\n".join(line.text for line in lines),
    )
    return PdfDocument(
        path="synthetic.pdf",
        pages=[PdfPage(page_number=7, width=612, height=792, text_blocks=[block])],
    )


def _missing(doc: PdfDocument) -> list:
    return [
        finding
        for finding in check_pdf_toc_alignment(doc)
        if finding.rule_id == "P018" and finding.details.get("issue_type") == "missing_page_number"
    ]


def test_single_line_toc_folio_uses_shared_baseline_despite_box_offset() -> None:
    doc = _doc(
        "TABLE OF CONTENTS",
        [
            _line("4.8.2 Earlier entry .... 103", 108, 540, 120, 139, 137),
            _line("4.8.3 Another entry .... 104", 108, 540, 150, 169, 167),
            _line("4.8.4 A synthetic entry", 108, 390, 180, 206, 204),
            _line("............. 105", 445, 540, 202, 216, 204),
            _line("4.8.5 Later entry .... 106", 108, 540, 230, 249, 247),
        ],
    )
    entries = extract_toc_logical_entry_lines(detect_toc_like_pages(doc)[0])
    target = next(entry for entry in entries if entry.cleaned_text.startswith("4.8.4"))
    assert target.page_number_token == "105"
    assert target.page_number_right_x == 540
    assert not _missing(doc)


def test_wrapped_toc_folio_on_final_title_baseline() -> None:
    doc = _doc(
        "TABLE OF CONTENTS",
        [
            _line("1 Earlier entry .... 1", 108, 540, 110, 129, 127),
            _line("2 A synthetic chapter title that wraps", 108, 480, 140, 160, 158),
            _line("after the first title row", 132, 420, 161, 187, 185),
            _line("............. 9", 445, 540, 183, 197, 185),
            _line("2.1 Next section .... 10", 126, 540, 215, 234, 232),
            _line("2.2 Following section .... 11", 126, 540, 245, 264, 262),
        ],
    )
    entries = extract_toc_logical_entry_lines(detect_toc_like_pages(doc)[0])
    target = next(entry for entry in entries if entry.cleaned_text.startswith("2 A synthetic"))
    assert target.page_number_token == "9"
    assert target.page_number_right_x == 540
    assert not _missing(doc)


def test_lof_separate_folio_on_shared_baseline() -> None:
    doc = _doc(
        "LIST OF FIGURES",
        [
            _line("5.1 First synthetic figure description.", 108, 390, 140, 166, 164),
            _line("............. 87", 445, 540, 162, 176, 164),
            _line("5.2 Second figure description. .... 88", 108, 540, 180, 199, 197),
            _line("5.3 Third figure description. .... 89", 108, 540, 210, 229, 227),
        ],
    )
    entries = extract_toc_logical_entry_lines(detect_toc_like_pages(doc)[0])
    assert entries[0].page_number_token == "87"
    assert not _missing(doc)


def test_genuinely_missing_folio_and_neighbor_row_are_not_paired() -> None:
    doc = _doc(
        "TABLE OF CONTENTS",
        [
            _line("1 Earlier entry .... 1", 108, 540, 110, 129, 127),
            _line("2 An entry without a page number", 108, 420, 140, 160, 158),
            _line("3 Next chapter .... 3", 108, 540, 170, 189, 187),
            _line("4 Later chapter .... 4", 108, 540, 200, 219, 217),
        ],
    )
    missing = _missing(doc)
    assert len(missing) == 1
    assert missing[0].details["worst_entry_index"] == "1"
    assert missing[0].details["bbox"] == "108.0,140.0,420.0,160.0"
