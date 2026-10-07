"""R011 references context across page breaks (synthetic PDFs only).

A page that cannot establish the outdented "[n]" label column on its own (no
heading and a single entry, e.g. the last page of a bibliography) continues
the previous page's column only when every structural signal agrees: same
label and text columns, the "[n]" sequence continues without a gap or
restart, and no new section heading. See
docs/status/r011_outdented_reference_labels_20261006.md.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_margins import _reference_label_columns, run_pdf_margin_rule

FONT_SIZE = 11.0
LABEL_RIGHT_EDGE = 102.5
TEXT_X = 108.4
ENTRY = "A. Author and B. Author, A synthetic article title, Journal, 2020."
CONTINUATION = "vol. 12, no. 3, pp. 45-67, a continuation line of the entry."
BODY = "Ordinary body paragraph text that starts inside the margin."

Row = tuple[float, str | None, float, str]


def _entries(first: int, count: int) -> list[Row]:
    rows: list[Row] = []
    y = 130.0
    for number in range(first, first + count):
        rows.append((y, f"[{number}]", TEXT_X, ENTRY))
        rows.append((y + 15, None, TEXT_X + 36, CONTINUATION))
        y += 40
    return rows


def _pdf(
    tmp_path: Path,
    pages: list[tuple[str | None, list[Row]]],
    *,
    label_edges: dict[int, float] | None = None,
) -> Path:
    """Each page is (heading or None, rows); rows are (y, label or None, text
    x, text). A label and its entry text share one text object so they
    extract as one line with two spans, the way LaTeX output does."""
    doc = fitz.open()
    font = fitz.Font("tiro")
    for index, (heading, rows) in enumerate(pages):
        page = doc.new_page(width=612, height=792)
        writer = fitz.TextWriter(page.rect)
        if heading:
            writer.append((240, 90), heading, font=font, fontsize=FONT_SIZE)
        edge = (label_edges or {}).get(index, LABEL_RIGHT_EDGE)
        for y, label, x, text in rows:
            if label is not None:
                label_x = edge - font.text_length(label, fontsize=FONT_SIZE)
                writer.append((label_x, y), label, font=font, fontsize=FONT_SIZE)
            writer.append((x, y), text, font=font, fontsize=FONT_SIZE)
        writer.write_text(page)
    path = tmp_path / "refs.pdf"
    doc.save(path)
    doc.close()
    return path


def _left_pages(path: Path) -> set[int]:
    model = load_pdf_layout(str(path))
    return {
        finding.page
        for finding in run_pdf_margin_rule(model)
        if finding.severity.value == "WARNING"
        and finding.details["side"] == "left_margin"
        and finding.page is not None
    }


def _column_pages(path: Path) -> set[int]:
    return set(_reference_label_columns(load_pdf_layout(str(path))))


def test_heading_page_with_several_entries_establishes_its_own_column(tmp_path: Path) -> None:
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4))])
    assert _column_pages(path) == {1}
    assert _left_pages(path) == set()


def test_next_page_continuing_the_sequence_is_exempt(tmp_path: Path) -> None:
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), (None, _entries(5, 4))])
    assert _column_pages(path) == {1, 2}
    assert _left_pages(path) == set()


def test_final_page_with_a_single_entry_continues_the_column(tmp_path: Path) -> None:
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), (None, _entries(5, 1))])
    assert _column_pages(path) == {1, 2}
    assert _left_pages(path) == set()


def test_page_opening_with_a_wrapped_entry_still_continues(tmp_path: Path) -> None:
    rows: list[Row] = [(100.0, None, TEXT_X + 36, CONTINUATION), *_entries(5, 1)]
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), (None, rows)])
    assert _left_pages(path) == set()


def test_single_entry_page_after_a_new_section_heading_is_reported(tmp_path: Path) -> None:
    for heading in ("APPENDIX A", "CHAPTER 7", "BIOGRAPHICAL SKETCH"):
        path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), (heading, _entries(5, 1))])
        assert _left_pages(path) == {2}, heading


def test_unrelated_restarted_item_after_references_is_reported(tmp_path: Path) -> None:
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), (None, _entries(1, 1))])
    assert _left_pages(path) == {2}


def test_numbering_gap_is_reported(tmp_path: Path) -> None:
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), (None, _entries(7, 1))])
    assert _left_pages(path) == {2}


def test_label_column_shift_is_reported(tmp_path: Path) -> None:
    path = _pdf(
        tmp_path,
        [("REFERENCES", _entries(1, 4)), (None, _entries(5, 1))],
        label_edges={1: LABEL_RIGHT_EDGE - 2.5},
    )
    assert _column_pages(path) == {1}
    assert _left_pages(path) == {2}


def test_entry_text_column_shift_does_not_continue(tmp_path: Path) -> None:
    # Label column unchanged, entry text 2.5pt further right: a different layout.
    y, label, _, text = _entries(5, 1)[0]
    path = _pdf(
        tmp_path, [("REFERENCES", _entries(1, 4)), (None, [(y, label, TEXT_X + 2.5, text)])]
    )
    assert _column_pages(path) == {1}
    assert _left_pages(path) == {2}


def test_geometry_alone_without_a_references_page_before_is_reported(tmp_path: Path) -> None:
    path = _pdf(tmp_path, [("CHAPTER 2", [(130.0, None, TEXT_X, BODY)]), (None, _entries(5, 1))])
    assert _column_pages(path) == set()
    assert _left_pages(path) == {2}


def test_several_continuation_pages_chain_until_the_section_ends(tmp_path: Path) -> None:
    path = _pdf(
        tmp_path,
        [
            ("REFERENCES", _entries(1, 4)),
            (None, _entries(5, 1)),
            (None, _entries(6, 1)),
            ("APPENDIX A", [(130.0, None, TEXT_X, BODY)]),
            (None, _entries(7, 1)),
        ],
    )
    assert _column_pages(path) == {1, 2, 3}
    assert _left_pages(path) == {5}


def test_chain_does_not_skip_a_page_without_labels(tmp_path: Path) -> None:
    path = _pdf(
        tmp_path,
        [
            ("REFERENCES", _entries(1, 4)),
            (None, [(130.0, None, TEXT_X, BODY)]),
            (None, _entries(5, 1)),
        ],
    )
    assert _left_pages(path) == {3}


def test_contents_page_never_inherits_the_column(tmp_path: Path) -> None:
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), ("TABLE OF CONTENTS", _entries(5, 1))])
    assert _column_pages(path) == {1}
    assert _left_pages(path) == {2}


def test_entry_text_crossing_on_a_continuation_page_is_reported(tmp_path: Path) -> None:
    y, label, _, text = _entries(5, 1)[0]
    rows: list[Row] = [(y, label, 90.0, text)]
    path = _pdf(tmp_path, [("REFERENCES", _entries(1, 4)), (None, rows)])
    assert _left_pages(path) == {2}
