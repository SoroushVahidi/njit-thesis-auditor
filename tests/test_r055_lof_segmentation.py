"""Regression for wrapped list entries with numbers inside their titles."""

import pytest

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
    detect_toc_like_pages,
    extract_toc_entry_lines,
    extract_toc_logical_entry_lines,
)


def _line(y: float, *pieces: tuple[str, float, float]) -> PdfTextLine:
    spans = [
        PdfTextSpan(text=text, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 12)) for text, x0, x1 in pieces
    ]
    return PdfTextLine(
        spans=spans,
        bbox=BBox(
            x0=min(s.bbox.x0 for s in spans), y0=y, x1=max(s.bbox.x1 for s in spans), y1=y + 12
        ),
        text=" ".join(text for text, _, _ in pieces),
    )


def _doc(lines: list[PdfTextLine]) -> PdfDocument:
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=108, y0=80, x1=540, y1=max(line.bbox.y1 for line in lines)),
        text="\n".join(line.text for line in lines),
    )
    return PdfDocument(
        path="synthetic.pdf",
        pages=[PdfPage(page_number=12, width=612, height=792, text_blocks=[block])],
    )


def test_wrapped_figure_entries_ignore_interior_numbers_and_count_once() -> None:
    """Interior numeric spans must not end an entry before its page column."""
    doc = _doc(
        [
            _line(80, ("LIST OF FIGURES", 190, 350)),
            _line(
                140,
                ("2.1 Sample measurements across", 108, 295),
                ("20", 305, 320),
                ("trial sites", 325, 480),
            ),
            _line(154, ("using invented equipment and labels", 150, 510)),
            _line(168, ("with a final caption and leaders. . . . 5", 150, 540)),
            _line(
                192,
                ("2.2 Another fabricated result from", 108, 350),
                ("800", 360, 385),
                ("observations", 390, 510),
            ),
            _line(206, ("in a separate setting. . . . 6", 150, 540)),
            _line(230, ("2.3 Third synthetic result with a wrapped", 108, 510)),
            _line(244, ("caption and its own page column. . . . 7", 150, 540)),
        ]
    )

    context = detect_toc_like_pages(doc)[0]
    entries = extract_toc_entry_lines(context, require_right_edge=True)
    assert len(entries) == 3
    assert [entry.page_number_token for entry in entries] == ["5", "6", "7"]

    findings = check_pdf_lot_lof_entry_type(doc)
    assert [finding.details["issue_type"] for finding in findings] == [
        "lof_entry_missing_figure_prefix"
    ] * 3
    assert [finding.details["entry_index"] for finding in findings] == ["0", "1", "2"]


def test_roman_letter_start_of_prose_is_not_a_numbered_entry() -> None:
    doc = _doc(
        [
            _line(80, ("LIST OF FIGURES", 190, 350)),
            _line(140, ("in a synthetic continuation. . . . 5", 108, 540)),
            _line(164, ("I.1 Numbered example with a real page. . . . 6", 108, 540)),
            _line(188, ("Figure I.2 Correctly prefixed entry. . . . 7", 108, 540)),
        ]
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert len(findings) == 1
    assert findings[0].details["issue_type"] == "lof_entry_missing_figure_prefix"


def test_numeric_continuation_with_page_token_keeps_owning_entry() -> None:
    doc = _doc(
        [
            _line(80, ("LIST OF FIGURES", 190, 350)),
            _line(140, ("3.1 Results from a study of", 108, 510)),
            _line(155, ("2 groups and 20 measurements 41", 149, 540)),
            _line(180, ("3.2 Independent second result 42", 108, 540)),
            _line(205, ("Figure 3.3 Compliant third result 43", 108, 540)),
        ]
    )
    entries = extract_toc_entry_lines(detect_toc_like_pages(doc)[0], require_right_edge=True)
    assert entries[0].page_number_token is None
    findings = check_pdf_lot_lof_entry_type(doc)
    assert [(f.details["entry_index"], f.details["issue_type"]) for f in findings] == [
        ("0", "lof_entry_missing_figure_prefix"),
        ("1", "lof_entry_missing_figure_prefix"),
    ]


def test_leaderless_wrapped_and_dot_leader_entries() -> None:
    doc = _doc(
        [
            _line(80, ("LIST OF FIGURES", 190, 350)),
            _line(140, ("4.1 Long title containing 100 trials", 108, 510)),
            _line(155, ("and its conclusion 51", 149, 540)),
            _line(180, ("4.2 Another independent title. . . . 52", 108, 540)),
            _line(205, ("Figure 4.3 Properly prefixed title. . . . 53", 108, 540)),
        ]
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert [f.details["entry_index"] for f in findings] == ["0", "1"]


def test_glued_numbered_title_and_near_baseline_fragments() -> None:
    doc = _doc(
        [
            _line(80, ("LIST OF FIGURES", 190, 350)),
            _line(140, ("5.4Synthetic title with a wrapped", 108, 510)),
            _line(155, ("completion with leaders. . . . 72", 149, 540)),
            _line(180, ("5.5", 108, 125)),
            _line(180.4, ("Another title split on the same baseline", 138, 510)),
            _line(195, ("with its page number. . . . 73", 149, 540)),
            _line(220, ("Figure 5.6 Compliant entry. . . . 74", 108, 540)),
        ]
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert [f.details["entry_index"] for f in findings] == ["0", "1"]


@pytest.mark.parametrize(
    ("heading", "second_prefix", "third_prefix", "expected_issue"),
    [
        ("LIST OF FIGURES", "2.2", "Figure", "lof_entry_missing_figure_prefix"),
        ("LIST OF FIGURES", "II.2", "Figure", "lof_entry_missing_figure_prefix"),
        ("LIST OF FIGURES", "Figure 2.2", "Figure", None),
        ("LIST OF FIGURES", "Table 2.2", "Figure", "lof_entry_is_table"),
        ("LIST OF TABLES", "2.2", "Table", "lot_entry_missing_table_prefix"),
        ("LIST OF TABLES", "Figure 2.2", "Table", "lot_entry_is_figure"),
    ],
)
def test_indented_numbered_row_keeps_its_own_page_number(
    heading: str, second_prefix: str, third_prefix: str, expected_issue: str | None
) -> None:
    doc = _doc(
        [
            _line(80, (heading, 190, 350)),
            _line(140, ("2.1 First synthetic item with no folio", 108, 510)),
            _line(156, (f"{second_prefix} Second synthetic item with folio 9", 149, 540)),
            _line(185, (f"{third_prefix} 2.3 Third synthetic item 10", 108, 540)),
        ]
    )
    entries = extract_toc_logical_entry_lines(
        detect_toc_like_pages(doc)[0], require_right_edge=True
    )
    assert [(entry.page_number_token, entry.line.bbox.y0) for entry in entries] == [
        (None, 140.0),
        ("9", 156.0),
        ("10", 185.0),
    ]
    findings = check_pdf_lot_lof_entry_type(doc)
    assert [
        (finding.details["entry_index"], finding.details["issue_type"], finding.page)
        for finding in findings
    ] == ([] if expected_issue is None else [("1", expected_issue, 12)])
