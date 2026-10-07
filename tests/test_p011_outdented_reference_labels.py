"""R011 outdented reference-number labels (synthetic PDFs only).

On a references page, a right-aligned column of standalone "[n]" labels may
hang left of the 1.5 in edge while each entry's text starts at it (Ester's
LaTeX left-margin authority; see
docs/status/r011_outdented_reference_labels_20261006.md). Only the label is
exempt: entry text crossing any margin is still reported.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, run_pdf_margin_rule

FONT_SIZE = 11.0
LABEL_RIGHT_EDGE = 102.5
TEXT_X = 108.4
ENTRY = "A. Author and B. Author, A synthetic article title, Journal, 2020."
CONTINUATION = "vol. 12, no. 3, pp. 45-67, a continuation line of the entry."


def _pdf(
    tmp_path: Path,
    rows: list[tuple[float, str | None, float, str]],
    *,
    heading: str | None = "REFERENCES",
    name: str = "refs.pdf",
) -> Path:
    """Rows are (y, label or None, text x, text), written as one text object
    per page so a label and its entry text extract as one line with two
    spans, the way LaTeX output does."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    font = fitz.Font("tiro")
    writer = fitz.TextWriter(page.rect)
    if heading:
        writer.append((260, 90), heading, font=font, fontsize=FONT_SIZE)
    for y, label, x, text in rows:
        if label is not None:
            label_x = LABEL_RIGHT_EDGE - font.text_length(label, fontsize=FONT_SIZE)
            writer.append((label_x, y), label, font=font, fontsize=FONT_SIZE)
        writer.append((x, y), text, font=font, fontsize=FONT_SIZE)
    writer.write_text(page)
    path = tmp_path / name
    doc.save(path)
    doc.close()
    return path


def _sides(path: Path) -> list[str]:
    model = load_pdf_layout(str(path))
    return [
        finding.details["side"]
        for finding in run_pdf_margin_rule(model)
        if finding.severity.value == "WARNING"
    ]


def _labelled_rows(
    text_x: float = TEXT_X, count: int = 4
) -> list[tuple[float, str | None, float, str]]:
    rows: list[tuple[float, str | None, float, str]] = []
    y = 130.0
    for number in range(1, count + 1):
        rows.append((y, f"[{number + 8}]", text_x, ENTRY))
        rows.append((y + 15, None, text_x + 36, CONTINUATION))
        y += 40
    return rows


def test_label_only_overflow_is_not_reported(tmp_path: Path) -> None:
    path = _pdf(tmp_path, _labelled_rows())
    model = load_pdf_layout(str(path))
    first = next(
        line for block in model.pages[0].text_blocks for line in block.lines if "[9]" in line.text
    )
    assert LEFT_MARGIN_PT - first.bbox.x0 > 15  # the label really hangs into the margin
    assert _sides(path) == []


def test_continuation_page_without_heading_is_also_exempt(tmp_path: Path) -> None:
    assert _sides(_pdf(tmp_path, _labelled_rows(), heading=None)) == []


def test_label_and_entry_text_both_crossing_is_reported(tmp_path: Path) -> None:
    assert _sides(_pdf(tmp_path, _labelled_rows(text_x=88.0))) == ["left_margin"]


def test_one_entry_text_crossing_among_compliant_entries_is_reported(tmp_path: Path) -> None:
    rows = _labelled_rows()
    y, label, _, text = rows[2]
    rows[2] = (y, label, 90.0, text)
    path = _pdf(tmp_path, rows)
    model = load_pdf_layout(str(path))
    (finding,) = [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]
    assert finding.details["side"] == "left_margin"
    assert "A. Author" in finding.details["affected_line_texts"]
    assert "[9]" not in finding.details["affected_line_texts"]  # compliant entries stay exempt


def test_reference_text_alone_crossing_left_is_reported(tmp_path: Path) -> None:
    rows: list[tuple[float, str | None, float, str]] = [
        (
            130.0 + 30 * i,
            None,
            80.0,
            f"Author{i}, A. (2020). A synthetic title. Journal, 1(2), 3-4.",
        )
        for i in range(4)
    ]
    assert _sides(_pdf(tmp_path, rows)) == ["left_margin"]


def test_reference_text_crossing_right_is_still_reported(tmp_path: Path) -> None:
    rows = _labelled_rows()
    y, label, x, _ = rows[0]
    rows[0] = (y, label, x, ENTRY + " Extra unbreakable words running far past the edge")
    assert _sides(_pdf(tmp_path, rows)) == ["right_margin"]


def test_reference_text_below_the_bottom_margin_is_still_reported(tmp_path: Path) -> None:
    rows = _labelled_rows()
    rows += [(762.0, "[20]", TEXT_X, ENTRY), (777.0, None, TEXT_X + 36, CONTINUATION)]
    assert _sides(_pdf(tmp_path, rows)) == ["bottom_margin"]


def test_body_text_crossing_left_is_reported(tmp_path: Path) -> None:
    rows: list[tuple[float, str | None, float, str]] = [
        (130.0 + 25 * i, None, 80.0, "Ordinary body paragraph text that starts inside the margin.")
        for i in range(4)
    ]
    assert _sides(_pdf(tmp_path, rows, heading="CHAPTER 2")) == ["left_margin"]


def test_table_caption_crossing_left_is_reported(tmp_path: Path) -> None:
    rows: list[tuple[float, str | None, float, str]] = [
        (130.0, None, 80.0, "Table 2.1 Synthetic results for the comparison of methods"),
        (150.0, None, 80.0, "Method    Accuracy    Recall    Precision    Runtime"),
    ]
    assert _sides(_pdf(tmp_path, rows, heading="CHAPTER 2")) == ["left_margin"]


def test_numbered_list_outside_a_references_page_is_reported(tmp_path: Path) -> None:
    # A single bracketed item is not a numbered reference list.
    rows: list[tuple[float, str | None, float, str]] = [
        (130.0, "[1]", TEXT_X, "step one of the procedure described in this chapter"),
        (160.0, None, 80.0, "Ordinary body paragraph text that starts inside the margin."),
    ]
    assert _sides(_pdf(tmp_path, rows, heading="CHAPTER 2")) == ["left_margin"]


def test_contents_page_label_column_is_not_exempt(tmp_path: Path) -> None:
    path = _pdf(tmp_path, _labelled_rows(), heading="TABLE OF CONTENTS")
    assert _sides(path) == ["left_margin"]


def test_unaligned_labels_are_not_treated_as_a_label_column(tmp_path: Path) -> None:
    rows = _labelled_rows()
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    font = fitz.Font("tiro")
    writer = fitz.TextWriter(page.rect)
    writer.append((260, 90), "REFERENCES", font=font, fontsize=FONT_SIZE)
    for index, (y, label, x, text) in enumerate(rows):
        if label is not None:
            writer.append((70.0 + 6 * index, y), label, font=font, fontsize=FONT_SIZE)
        writer.append((x, y), text, font=font, fontsize=FONT_SIZE)
    writer.write_text(page)
    path = tmp_path / "unaligned.pdf"
    doc.save(path)
    doc.close()
    assert _sides(path) == ["left_margin"]
