"""Synthetic wrapped folios whose leader evidence is stronger than a page median."""

from __future__ import annotations

import pytest

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_alignment import (
    _logical_page_column_edge,
    check_pdf_toc_alignment,
    detect_toc_like_pages,
    extract_toc_entry_lines,
    extract_toc_logical_entry_lines,
)


def _line(text: str, x0: float, x1: float, y0: float, *, y1: float | None = None) -> PdfTextLine:
    box = BBox(x0=x0, y0=y0, x1=x1, y1=y1 if y1 is not None else y0 + 13.4)
    baseline = box.y1 - 2.6
    return PdfTextLine(
        text=text,
        bbox=box,
        baseline_y=baseline,
        spans=[PdfTextSpan(text=text, bbox=box, baseline_y=baseline, size=12)],
    )


def _doc(heading: str, rows: list[PdfTextLine]) -> PdfDocument:
    lines = [_line(heading, 210, 405, 80), *rows]
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=550, y1=max(row.bbox.y1 for row in lines)),
        text="\n".join(row.text for row in lines),
    )
    return PdfDocument(
        path="synthetic.pdf",
        pages=[PdfPage(page_number=26, width=612, height=792, text_blocks=[block])],
    )


def _findings(doc: PdfDocument, issue: str) -> list:
    return [
        finding
        for finding in check_pdf_toc_alignment(doc)
        if finding.rule_id == "P018" and finding.details.get("issue_type") == issue
    ]


def _target(doc: PdfDocument, prefix: str, *, presence_recovery: bool = False):
    context = detect_toc_like_pages(doc)[0]
    entries = extract_toc_logical_entry_lines(
        context, recover_displaced_leader_folio=presence_recovery
    )
    return next(entry for entry in entries if entry.cleaned_text.startswith(prefix))


def _oscar_geometry_rows(
    *, terminal: str = "= measured quantity ........ 185"
) -> list[PdfTextLine]:
    # Neutral text with the observed page-26 geometry. Four apparent page
    # numbers pull the ordinary median to 502.3; leader-backed folios at
    # 540.5 remain a separate mode. The last hanging row is 12.9 pt below
    # the previous row and starts at the same 137.4 pt indent.
    return [
        _line(f"8.{index} Synthetic peer item .... {index + 10}", 110.5, 502.3, 140 + 30 * index)
        for index in range(1, 5)
    ] + [
        _line("9.1 Earlier figure description .... 183", 110.5, 540.5, 464.1),
        _line("9.2 A synthetic figure description wraps", 110.5, 514.0, 541.3),
        _line("a continued description of the figure", 137.4, 512.6, 555.1),
        _line(terminal, 137.4, 540.5, 568.0, y1=582.1),
        _line("9.3 Following figure description .... 187", 110.5, 540.5, 590.7),
    ]


def test_page26_geometry_recovers_terminal_leader_folio_without_column_vote() -> None:
    doc = _doc("LIST OF FIGURES", _oscar_geometry_rows())
    context = detect_toc_like_pages(doc)[0]
    assert _logical_page_column_edge(extract_toc_entry_lines(context)) == pytest.approx(502.3)
    assert _target(doc, "9.2").page_number_token is None
    target = _target(doc, "9.2", presence_recovery=True)
    assert target.page_number_token == "185"
    assert target.page_number_right_x == pytest.approx(540.5)
    assert target.page_number_line is not None
    assert target.page_number_line.bbox.y0 == pytest.approx(568.0)
    assert target.line.bbox.y1 == pytest.approx(582.1)
    assert not _findings(doc, "missing_page_number")


def test_displaced_terminal_leader_folio_in_wrapped_toc_entry() -> None:
    doc = _doc(
        "TABLE OF CONTENTS",
        [
            _line("1 Earlier chapter .... 1", 108, 502.3, 140),
            _line("1.1 Earlier section .... 2", 126, 502.3, 165),
            _line("1.2 Another section .... 3", 126, 502.3, 190),
            _line("2 A long synthetic chapter title", 108, 420, 240),
            _line("continuing below the first line", 132, 430, 254),
            _line("= terminal expression ........ 9", 132, 540.5, 268),
            _line("2.1 Next section .... 10", 126, 502.3, 320),
        ],
    )
    assert _target(doc, "2 A long", presence_recovery=True).page_number_token == "9"
    assert not _findings(doc, "missing_page_number")


def test_final_hanging_row_with_separate_spans_on_one_baseline() -> None:
    rows = _oscar_geometry_rows()
    final = rows[-2]
    baseline = final.baseline_y
    final.spans = [
        PdfTextSpan(
            text=text,
            bbox=BBox(x0=x0, y0=568.0, x1=x1, y1=582.1),
            baseline_y=baseline,
            size=12,
        )
        for text, x0, x1 in [
            ("= measured quantity", 137.4, 400.1),
            ("........", 406.1, 510.0),
            ("185", 523.0, 540.5),
        ]
    ]
    final.text = "= measured quantity........185"
    doc = _doc("LIST OF FIGURES", rows)
    target = _target(doc, "9.2", presence_recovery=True)
    assert target.page_number_token == "185"
    assert target.page_number_right_x == pytest.approx(540.5)
    assert not _findings(doc, "missing_page_number")


def test_genuinely_missing_wrapped_folio_still_warns() -> None:
    rows = _oscar_geometry_rows(terminal="= measured quantity without a terminal folio")
    doc = _doc("LIST OF FIGURES", rows)
    assert _target(doc, "9.2").page_number_token is None
    missing = _findings(doc, "missing_page_number")
    assert len(missing) == 1
    assert missing[0].details["bbox"] == "110.5,541.3,514.0,568.5"


def test_neighbor_entry_folio_is_not_borrowed() -> None:
    doc = _doc(
        "LIST OF FIGURES",
        [
            _line("9.1 Earlier figure description .... 183", 110.5, 540.5, 464),
            _line("9.2 A long synthetic figure description", 110.5, 514.0, 541.3),
            _line("continuation has no page number", 137.4, 512.6, 555.1),
            _line("9.3 Following figure description .... 187", 110.5, 540.5, 568.0),
            _line("9.4 Another figure description .... 188", 110.5, 540.5, 590.7),
        ],
    )
    assert _target(doc, "9.2").page_number_token is None
    assert _findings(doc, "missing_page_number")


def test_ordinary_aligned_entries_keep_their_folios() -> None:
    doc = _doc(
        "TABLE OF CONTENTS",
        [
            _line("1 First chapter .... 1", 108, 540.5, 140),
            _line("1.1 First section .... 2", 126, 540.5, 165),
            _line("1.2 Second section .... 3", 126, 540.5, 190),
        ],
    )
    assert not _findings(doc, "missing_page_number")
    assert [
        e.page_number_token for e in extract_toc_logical_entry_lines(detect_toc_like_pages(doc)[0])
    ] == ["1", "2", "3"]


@pytest.mark.parametrize(
    "heading,prefix",
    [
        ("TABLE OF CONTENTS", "B.1.7"),
        ("LIST OF FIGURES", "B.1"),
    ],
)
def test_existing_appendix_and_list_entry_folios(heading: str, prefix: str) -> None:
    doc = _doc(
        heading,
        [
            _line("B.1 Earlier entry .... 91", 108, 502.3, 140),
            _line("B.1.1 Another entry .... 92", 126, 502.3, 165),
            _line("B.1.2 Third entry .... 93", 126, 502.3, 190),
            _line(f"{prefix} A synthetic description .... 94", 126, 502.3, 240),
        ],
    )
    assert _target(doc, prefix + " A synthetic").page_number_token == "94"
    assert not _findings(doc, "missing_page_number")


def test_off_column_number_without_leader_evidence_is_not_assigned() -> None:
    doc = _doc("LIST OF FIGURES", _oscar_geometry_rows(terminal="= measured quantity 185"))
    assert _target(doc, "9.2").page_number_token is None
    assert _findings(doc, "missing_page_number")


def test_leader_token_outside_right_folio_region_is_insufficient() -> None:
    rows = _oscar_geometry_rows()
    rows[-2].bbox.x1 = 480.0
    rows[-2].spans[0].bbox.x1 = 480.0
    doc = _doc("LIST OF FIGURES", rows)
    assert _target(doc, "9.2", presence_recovery=True).page_number_token is None
    assert _findings(doc, "missing_page_number")
