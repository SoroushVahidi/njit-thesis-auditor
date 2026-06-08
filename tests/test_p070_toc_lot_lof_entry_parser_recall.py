"""Synthetic tests for P070 — TOC/LoT/LoF entry parser recall refinement.

All fixtures use clearly fake placeholder text only. No real dissertation content.
"""

from __future__ import annotations

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type
from njit_auditor.rules.pdf_toc_alignment import (
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
    group_toc_page_runs,
)
from njit_auditor.rules.pdf_toc_cross_page_entry_ordering import (
    check_pdf_toc_cross_page_entry_ordering,
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


def _make_page(page_number: int, lines: list[PdfTextLine]) -> PdfPage:
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(
            x0=min(line.bbox.x0 for line in lines),
            y0=min(line.bbox.y0 for line in lines),
            x1=max(line.bbox.x1 for line in lines),
            y1=max(line.bbox.y1 for line in lines),
        ),
        text=" ".join(line.text for line in lines),
    )
    return PdfPage(
        page_number=page_number,
        width=_PAGE_W,
        height=_PAGE_H,
        text_blocks=[block],
    )


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(path="synthetic_test.pdf", pages=list(pages))


def _toc_context(page: PdfPage, heading_y: float = 90.0) -> TocPageContext:
    return TocPageContext(page=page, page_type="table_of_contents", heading_bottom_y=heading_y)


def test_single_line_toc_entry_with_inline_page_number() -> None:
    page = _make_page(
        1,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line("1 LOREM SECTION ALPHA .... 12", 120.0, x1=520.0),
            _make_line("2 LOREM SECTION BETA .... 24", 140.0, x1=520.0),
            _make_line("3 LOREM SECTION GAMMA .... 36", 160.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_toc_context(page))
    assert len(entries) == 3
    assert all(entry.page_number_token is not None for entry in entries)


def test_wrapped_entry_pairs_following_right_column_number() -> None:
    page = _make_page(
        1,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line("1 LOREM WRAPPED TITLE LINE", 120.0, x1=420.0),
            _make_line("42", 132.0, x0=_RIGHT_COL, x1=520.0),
            _make_line("2 LOREM SECTION BETA .... 24", 160.0, x1=520.0),
            _make_line("3 LOREM SECTION GAMMA .... 36", 180.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_toc_context(page))
    assert len(entries) == 3
    wrapped = [entry for entry in entries if entry.is_wrapped]
    assert len(wrapped) == 1
    assert wrapped[0].page_number_token == "42"


def test_short_table_prefix_parsed_with_page_number() -> None:
    page = _make_page(
        1,
        [
            _make_line("LIST OF TABLES", 80.0, x1=260.0),
            _make_line("Table 1", 120.0, x1=200.0),
            _make_line("9", 120.0, x0=_RIGHT_COL, x1=520.0),
            _make_line("Table 2 .... 11", 140.0, x1=520.0),
            _make_line("Table 3 .... 13", 160.0, x1=520.0),
        ],
    )
    context = TocPageContext(page=page, page_type="list_of_tables", heading_bottom_y=80.0)
    entries = extract_toc_entry_lines(context)
    assert len(entries) >= 3
    assert any(entry.cleaned_text.upper().startswith("TABLE 1") for entry in entries)


def test_short_figure_prefix_parsed_with_inline_page_number() -> None:
    page = _make_page(
        1,
        [
            _make_line("LIST OF FIGURES", 80.0, x1=280.0),
            _make_line("Figure 1 .... 5", 120.0, x1=520.0),
            _make_line("Figure 2 .... 7", 140.0, x1=520.0),
            _make_line("Figure 3 .... 9", 160.0, x1=520.0),
        ],
    )
    context = TocPageContext(page=page, page_type="list_of_figures", heading_bottom_y=80.0)
    entries = extract_toc_entry_lines(context)
    assert len(entries) == 3
    assert entries[0].cleaned_text.upper().startswith("FIGURE 1")


def test_ambiguous_left_margin_number_not_paired() -> None:
    page = _make_page(
        1,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line("1 LOREM SECTION ALPHA", 120.0, x1=420.0),
            _make_line("99", 120.0, x0=140.0, x1=170.0),
            _make_line("2 LOREM SECTION BETA .... 24", 160.0, x1=520.0),
            _make_line("3 LOREM SECTION GAMMA .... 36", 180.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_toc_context(page))
    first = next(entry for entry in entries if "ALPHA" in entry.cleaned_text.upper())
    assert first.page_number_token is None


def test_continued_list_heading_not_parsed_as_entry() -> None:
    page = _make_page(
        1,
        [
            _make_line("LIST OF TABLES (Continued)", 80.0, x1=320.0),
            _make_line("Table 4 .... 15", 120.0, x1=520.0),
            _make_line("Table 5 .... 17", 140.0, x1=520.0),
            _make_line("Table 6 .... 19", 160.0, x1=520.0),
        ],
    )
    context = TocPageContext(page=page, page_type="list_of_tables", heading_bottom_y=80.0)
    entries = extract_toc_entry_lines(context)
    assert all("CONTINUED" not in entry.cleaned_text.upper() for entry in entries)
    assert len(entries) == 3


def test_prose_like_long_line_not_parsed_as_entry() -> None:
    prose = (
        "This is a long synthetic prose paragraph that should not be treated as a "
        "table of contents entry because it ends with a period."
    )
    page = _make_page(
        1,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line(prose, 120.0, x1=520.0),
            _make_line("1 LOREM SECTION ALPHA .... 12", 160.0, x1=520.0),
            _make_line("2 LOREM SECTION BETA .... 24", 180.0, x1=520.0),
            _make_line("3 LOREM SECTION GAMMA .... 36", 200.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_toc_context(page))
    assert all(prose not in entry.cleaned_text for entry in entries)
    assert len(entries) == 3


def test_empty_page_yields_no_entries() -> None:
    page = _make_page(1, [_make_line("TABLE OF CONTENTS", 80.0, x1=300.0)])
    entries = extract_toc_entry_lines(_toc_context(page))
    assert entries == []


def test_group_toc_page_runs_combines_consecutive_pages() -> None:
    page1 = _make_page(
        1,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line("1 LOREM ALPHA .... 3", 120.0, x1=520.0),
            _make_line("2 LOREM BETA .... 5", 140.0, x1=520.0),
        ],
    )
    page2 = _make_page(
        2,
        [
            _make_line("TABLE OF CONTENTS (Continued)", 80.0, x1=360.0),
            _make_line("3 LOREM GAMMA .... 7", 120.0, x1=520.0),
            _make_line("4 LOREM DELTA .... 9", 140.0, x1=520.0),
        ],
    )
    doc = _doc(page1, page2)
    contexts = detect_toc_like_pages(doc)
    runs = group_toc_page_runs(contexts)
    toc_runs = [run for run in runs if run.page_type == "table_of_contents"]
    assert len(toc_runs) == 1
    assert len(toc_runs[0].contexts) == 2
    assert len(toc_runs[0].iter_entries()) >= 4


def test_p055_cross_type_check_uses_parser_entries() -> None:
    page = _make_page(
        1,
        [
            _make_line("LIST OF TABLES", 80.0, x1=260.0),
            _make_line("Figure 9 .... 21", 120.0, x1=520.0),
            _make_line("Table 1 .... 11", 140.0, x1=520.0),
            _make_line("Table 2 .... 13", 160.0, x1=520.0),
        ],
    )
    findings = check_pdf_lot_lof_entry_type(_doc(page))
    assert any(f.rule_id == "P055" for f in findings)


def test_p062_still_skips_when_insufficient_comparable_entries() -> None:
    page = _make_page(
        1,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line("1 LOREM ALPHA .... 3", 120.0, x1=520.0),
        ],
    )
    findings = check_pdf_toc_cross_page_entry_ordering(_doc(page))
    assert findings == []


def test_privacy_no_entry_text_in_p055_finding_details() -> None:
    secret = "SYNTHETIC_SECRET_ENTRY_TITLE_XYZ"
    page = _make_page(
        1,
        [
            _make_line("LIST OF TABLES", 80.0, x1=260.0),
            _make_line(f"Figure 1 {secret} .... 21", 120.0, x1=520.0),
            _make_line("Table 1 .... 11", 140.0, x1=520.0),
            _make_line("Table 2 .... 13", 160.0, x1=520.0),
        ],
    )
    findings = check_pdf_lot_lof_entry_type(_doc(page))
    serialized = " ".join(
        f"{finding.message} {finding.details}" for finding in findings if finding.rule_id == "P055"
    )
    assert secret not in serialized
