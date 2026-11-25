"""Privacy-safe shapes of Ester-confirmed false-positive regressions."""

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfPage, PdfTextBlock, PdfTextLine, PdfTextSpan
from njit_auditor.rules.pdf_heading_levels import check_pdf_heading_level_styles
from njit_auditor.rules.pdf_indentation import _paragraph_starts_like_continuation
from njit_auditor.rules.pdf_lof_terminal_punctuation import _check_lof_terminal_punctuation_page
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    _is_numbered_title_continuation,
)
from njit_auditor.rules.pdf_lot_lof_page_number_alignment import _complete_entries
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    _add_entry_consistency_findings,
    entry_has_visible_dot_leader,
    is_isolated_terminal_grid_leader_dot,
)
from njit_auditor.rules.pdf_toc_continued_headings import _continued_heading_status
from njit_auditor.rules.pdf_toc_leader_consistency import _classify_entry


def test_p030_space_collapsed_heading_with_separate_continued_marker() -> None:
    heading = PdfTextLine(text="TABLEOFCONTENTS", bbox=BBox(x0=200, y0=90, x1=330, y1=103))
    marker = PdfTextLine(text="(Continued)", bbox=BBox(x0=220, y0=104, x1=310, y1=117))
    page = PdfPage(
        page_number=2,
        width=612,
        height=792,
        text_blocks=[
            PdfTextBlock(lines=[heading], bbox=heading.bbox, text=heading.text),
            PdfTextBlock(lines=[marker], bbox=marker.bbox, text=marker.text),
        ],
    )
    assert _continued_heading_status(page, "table_of_contents")[0]
    assert not _continued_heading_status(page, "list_of_figures")[0]


def test_p027_run_in_body_after_period_is_not_missing_heading_period(tmp_path: Path) -> None:
    pdf_path = tmp_path / "run_in_level4.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    title = "3.2.3.2 Synthetic method. "
    page.insert_text((108, 140), title, fontname="Times-Bold", fontsize=12)
    title_width = fitz.get_text_length(title, fontname="Times-Bold", fontsize=12)
    page.insert_text((108 + title_width, 140), "The body sentence continues here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    findings = check_pdf_heading_level_styles(load_pdf_layout(str(pdf_path)))
    assert not any("punctuation" in f.details.get("issue_type", "") for f in findings)


def _entry(title: str, dot_x: float, dots: int) -> TocEntryLine:
    spans = [
        PdfTextSpan(text=title, bbox=BBox(x0=110, y0=100, x1=480, y1=112))
    ]
    for index in range(dots):
        x0 = dot_x - (dots - index - 1) * 9.2
        spans.append(PdfTextSpan(text=".", bbox=BBox(x0=x0, y0=100, x1=x0 + 3, y1=112)))
    spans.append(PdfTextSpan(text="42", bbox=BBox(x0=528, y0=100, x1=540, y1=112)))
    line = PdfTextLine(
        text=f"{title} {'.' * dots} 42",
        bbox=BBox(x0=110, y0=100, x1=540, y1=112),
        spans=spans,
    )
    return TocEntryLine(line, line.text, "42", 540, 110, True)


def test_p053_p054_lone_dot_on_peer_leader_grid_is_not_title_period() -> None:
    target = _entry("Long synthetic title", 508.2, 1)
    peers = [target] + [_entry("Short synthetic title", 508.2, 7) for _ in range(3)]
    assert is_isolated_terminal_grid_leader_dot(target, peers)
    assert not is_isolated_terminal_grid_leader_dot(target, [target])


def test_p048_roman_letter_inside_title_is_not_page_number() -> None:
    line = PdfTextLine(
        text="Figure 3 Synthetic title with symbol Tm in body",
        bbox=BBox(x0=110, y0=100, x1=540, y1=112),
    )
    false_entry = TocEntryLine(line, line.text, "m", 326.3, 110, False)
    real_entry = TocEntryLine(line, "Figure 4 Synthetic title 42", "42", 540, 110, False)
    assert _complete_entries([false_entry, real_entry]) == [real_entry]


def test_p048_number_at_end_of_wrapped_title_on_leader_page_is_not_page_number() -> None:
    title = PdfTextLine(
        text="Figure 2 Synthetic title observed by IMP 8",
        bbox=BBox(x0=110, y0=100, x1=510, y1=112),
    )
    false_entry = TocEntryLine(title, title.text, "8", 510, 110, False)
    true_entries = [_entry(f"Figure {i} Synthetic caption.", 508.2, 7) for i in range(3)]
    assert _complete_entries([*true_entries, false_entry]) == true_entries


def test_p018_embedded_title_number_is_not_missing_list_leader() -> None:
    page = PdfPage(page_number=15, width=612, height=792)
    context = TocPageContext(page, "list_of_figures", 80)
    dotted = [_entry(f"Figure {i} Synthetic caption", 508.2, 7) for i in range(3)]
    fragment = PdfTextLine(
        text="Figure 4 Synthetic title observed by IMP 8",
        bbox=BBox(x0=108, y0=160, x1=510, y1=172),
    )
    false_entry = TocEntryLine(fragment, fragment.text, "8", 326.3, 108, False)
    findings = {}
    entries = [*dotted, false_entry]
    _add_entry_consistency_findings(context, entries, [entry.line for entry in entries], findings)
    assert "inconsistent_leader_dots" not in findings

    true_entry = TocEntryLine(fragment, "Figure 4 Synthetic title 42", "42", 540, 108,
                              False)
    findings = {}
    entries = [*dotted, true_entry]
    _add_entry_consistency_findings(context, entries, [entry.line for entry in entries], findings)
    assert "inconsistent_leader_dots" in findings


def test_p040_right_column_number_survives_cleaned_row_omission() -> None:
    page = PdfPage(page_number=16, width=612, height=792)
    context = TocPageContext(page, "list_of_figures", 90)
    entries = []
    for index, title in enumerate((
        "Figure 2.1 Complete title.",
        "Figure 2.2 Missing terminal punctuation",
        "Figure 2.3 Another complete title.",
    )):
        line = PdfTextLine(
            text=title,
            bbox=BBox(x0=110, y0=110 + index * 20, x1=510, y1=122 + index * 20),
        )
        entries.append(TocEntryLine(line, title, str(40 + index), 540, 110, True))
    findings = _check_lof_terminal_punctuation_page(context, entries, 0)
    assert len(findings) == 1
    assert findings[0].details["page_entry_index"] == "1"


def test_p015_math_index_is_not_lowercase_prose_continuation() -> None:
    math_line = PdfTextLine(
        text="k=0isarealization,orsamplepath",
        bbox=BBox(x0=130, y0=100, x1=410, y1=112),
    )
    prose_line = PdfTextLine(
        text="where the sample continues",
        bbox=BBox(x0=130, y0=100, x1=410, y1=112),
    )
    assert not _paragraph_starts_like_continuation([math_line])
    assert _paragraph_starts_like_continuation([prose_line])


def test_p075_detached_dot_run_is_a_leader_but_missing_run_is_not() -> None:
    title = PdfTextLine(
        text="1 SYNTHETIC CHAPTER 4",
        bbox=BBox(x0=108, y0=100, x1=540, y1=112),
    )
    dots = PdfTextLine(text="........", bbox=BBox(x0=440, y0=100, x1=510, y1=112))
    entry = TocEntryLine(title, title.text, "4", 540, 108, False)
    with_dots = PdfPage(
        page_number=7,
        width=612,
        height=792,
        text_blocks=[PdfTextBlock(lines=[dots], bbox=dots.bbox, text=dots.text)],
    )
    without_dots = PdfPage(page_number=7, width=612, height=792)
    assert _classify_entry(entry, with_dots) == "dot"
    assert _classify_entry(entry, without_dots) == "none"


def test_p018_wrapped_list_entry_detached_dots_on_final_row_are_leaders() -> None:
    """Muyeed LoT p16 extracts the wrapped title and dot row separately."""
    title = PdfTextLine(
        text="3.3 Synthetic long list title continued on a second row",
        bbox=BBox(x0=108, y0=100, x1=540, y1=130),
    )
    dots = PdfTextLine(text="..................", bbox=BBox(x0=351, y0=118, x1=512, y1=130))
    entry = TocEntryLine(title, title.text, "25", 540, 108, False, is_wrapped=True)
    page = PdfPage(
        page_number=16,
        width=612,
        height=792,
        text_blocks=[PdfTextBlock(lines=[dots], bbox=dots.bbox, text=dots.text)],
    )
    assert entry_has_visible_dot_leader(entry, page, [entry])


def test_p075_two_detached_dots_between_title_and_page_number_are_leaders() -> None:
    """A long Pennock TOC title leaves room for just two leader dots."""
    title = PdfTextLine(text="6 SYNTHETIC LONG CHAPTER TITLE 96",
                        bbox=BBox(x0=108, y0=100, x1=540, y1=112))
    dots = PdfTextLine(text="..", bbox=BBox(x0=499, y0=100, x1=511, y1=112))
    entry = TocEntryLine(title, title.text, "96", 540, 108, False)
    page = PdfPage(page_number=11, width=612, height=792,
                   text_blocks=[PdfTextBlock(lines=[dots], bbox=dots.bbox, text=dots.text)])
    assert _classify_entry(entry, page, [entry]) == "dot"


def test_p075_two_spaced_dots_are_a_short_leader() -> None:
    line = PdfTextLine(
        text="1 SYNTHETIC CHAPTER . . 4",
        bbox=BBox(x0=108, y0=100, x1=540, y1=112),
    )
    entry = TocEntryLine(line, line.text, "4", 540, 108, False)
    page = PdfPage(page_number=7, width=612, height=792)
    assert _classify_entry(entry, page) == "dot"


def test_p046_number_in_wrapped_title_is_not_new_entry_number() -> None:
    previous_line = PdfTextLine(
        text="2.2 Synthetic caption mentioning a model",
        bbox=BBox(x0=108, y0=100, x1=510, y1=112),
    )
    continuation_line = PdfTextLine(
        text="5.5 Thinking .... 18",
        bbox=BBox(x0=149, y0=114.4, x1=540, y1=126.4),
    )
    previous = TocEntryLine(previous_line, previous_line.text, None, None, 108, False)
    continuation = TocEntryLine(
        continuation_line, continuation_line.text, "18", 540, 149, False
    )
    assert _is_numbered_title_continuation(continuation, previous)
    complete_previous = TocEntryLine(previous_line, previous_line.text, "17", 540, 108, False)
    assert not _is_numbered_title_continuation(continuation, complete_previous)
