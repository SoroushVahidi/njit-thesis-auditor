"""Synthetic boundaries for Ester's wrapped-entry and capitalization judgments."""

from __future__ import annotations

from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextLine
from njit_auditor.rules.pdf_lof_terminal_punctuation import (
    _strip_trailing_lof_dot_leaders,
    check_pdf_lof_terminal_punctuation,
)
from njit_auditor.rules.pdf_toc_alignment import (
    check_pdf_toc_alignment,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)
from njit_auditor.rules.pdf_toc_leader_consistency import check_pdf_toc_leader_consistency
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting


def _doc(heading: str, rows: list[tuple[str, float, float, float]]) -> PdfDocument:
    lines = [PdfTextLine(text=heading, bbox=BBox(x0=220, y0=80, x1=390, y1=94))]
    lines.extend(
        PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 12))
        for text, x0, x1, y in rows
    )
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=560, y1=max(line.bbox.y1 for line in lines)),
        text="\n".join(line.text for line in lines),
    )
    page = PdfPage(page_number=1, width=612, height=792, text_blocks=[block])
    return PdfDocument(path="synthetic.pdf", pages=[page])


def _issues(doc: PdfDocument, rule: str) -> list[str]:
    detectors = {
        "P018": check_pdf_toc_alignment,
        "P024": check_pdf_toc_list_formatting,
        "P040": check_pdf_lof_terminal_punctuation,
    }
    return [f.details["issue_type"] for f in detectors[rule](doc) if f.rule_id == rule]


def _logical_entries(doc: PdfDocument):
    context = detect_toc_like_pages(doc)[0]
    return extract_toc_logical_entry_lines(context)


def test_wrapped_list_entry_rejoins_filtered_and_numeric_continuations() -> None:
    doc = _doc(
        "LIST OF FIGURES",
        [
            ("Figure 2.1 An example description that wraps", 108, 510, 140),
            ("-including a filtered continuation", 149, 510, 157),
            ("2 cases ending with punctuation. . . 21", 149, 540, 174),
            ("Figure 2.2 Second complete title. .... 22", 108, 540, 198),
            ("Figure 2.3 Third complete title. .... 23", 108, 540, 222),
        ],
    )
    first = _logical_entries(doc)[0]
    assert first.page_number_token == "21"
    assert "filtered continuation" in first.cleaned_text
    assert "missing_page_number" not in _issues(doc, "P018")
    assert "inconsistent_hierarchy_indent" not in _issues(doc, "P018")


def test_wrapped_toc_entry_with_detached_final_page_number() -> None:
    doc = _doc(
        "TABLE OF CONTENTS",
        [
            ("2 Long synthetic chapter title without a number", 108, 524, 140),
            ("continuation ending in leaders……", 126, 522, 160.6),
            ("35", 539, 551, 167.6),
            ("2.1 Next section……………………………… 36", 126, 551, 195),
            ("2.2 Further section…………………………… 37", 126, 551, 223),
        ],
    )
    assert _logical_entries(doc)[0].page_number_token == "35"
    assert "missing_page_number" not in _issues(doc, "P018")


def test_internal_title_numeral_is_replaced_by_continuation_page_number() -> None:
    doc = _doc(
        "LIST OF FIGURES",
        [
            ("Figure 5.1 Synthetic comparison of cases 1", 108, 510, 140),
            ("2.5 final comparison result. . 61", 149, 540, 155.7),
            ("Figure 5.2 Another complete title. .... 62", 108, 540, 180),
            ("Figure 5.3 Third complete title. .... 63", 108, 540, 204),
        ],
    )
    entries = _logical_entries(doc)
    assert len(entries) == 3
    assert entries[0].page_number_token == "61"
    assert "inconsistent_hierarchy_indent" not in _issues(doc, "P018")
    assert "missing_page_number" not in _issues(doc, "P018")


def test_glued_page_number_uses_column_and_rejects_decimal_near_miss() -> None:
    peers = [
        ("Figure 5.3 Second title. .... 125", 108, 540, 165),
        ("Figure 5.4 Third title. .... 126", 108, 540, 189),
        ("Figure 5.5 Fourth title. .... 127", 108, 540, 213),
    ]
    glued = _doc(
        "LIST OF FIGURES",
        [("Figure 5.2 A complete synthetic title.124", 108, 540, 140), *peers],
    )
    assert _logical_entries(glued)[0].page_number_token == "124"
    assert "missing_page_number" not in _issues(glued, "P018")

    decimal = _doc(
        "LIST OF FIGURES",
        [("Figure 5.2 A title ending in decimal 0.124", 108, 540, 140), *peers],
    )
    assert _logical_entries(decimal)[0].page_number_token is None
    assert "missing_page_number" in _issues(decimal, "P018")


def test_genuine_missing_page_number_and_toc_leader_ownership_survive() -> None:
    missing_number = _doc(
        "TABLE OF CONTENTS",
        [
            ("1 Introductory title .... 1", 108, 540, 140),
            ("2 A genuinely unnumbered entry", 108, 440, 164),
            ("3 Next chapter title .... 3", 108, 540, 188),
            ("4 Final chapter title .... 4", 108, 540, 212),
        ],
    )
    assert "missing_page_number" in _issues(missing_number, "P018")

    missing_leader = _doc(
        "TABLE OF CONTENTS",
        [
            ("1 Introductory title .... 1", 108, 540, 140),
            ("2 A complete title with page number 2", 108, 540, 164),
            ("3 Next chapter title .... 3", 108, 540, 188),
            ("4 Final chapter title .... 4", 108, 540, 212),
        ],
    )
    assert "inconsistent_leader_dots" not in _issues(missing_leader, "P018")
    assert check_pdf_toc_leader_consistency(missing_leader)


def test_curly_possessive_is_one_title_word_but_lowercase_major_word_warns() -> None:
    peers = [
        ("3.4 Baseline Method .... 4", 124, 540, 140),
        ("3.6 Comparative Analysis .... 6", 124, 540, 188),
        ("3.7 Final Discussion .... 7", 124, 540, 212),
    ]
    correct = _doc(
        "TABLE OF CONTENTS",
        [peers[0], ("3.5 Algorithm’s Impact Analysis .... 5", 124, 540, 164), *peers[1:]],
    )
    assert "toc_level_capitalization" not in _issues(correct, "P024")
    incorrect = _doc(
        "TABLE OF CONTENTS",
        [peers[0], ("3.5 Algorithm’s impact Analysis .... 5", 124, 540, 164), *peers[1:]],
    )
    assert "toc_level_capitalization" in _issues(incorrect, "P024")


def test_lof_software_names_follow_title_case_not_sentence_case() -> None:
    """Ester 2026-10-05: List of Figures titles use title case (R024E)."""
    peers = [
        ("Figure 2 Basic Reference Chart. .... 2", 108, 540, 164),
        ("Figure 3 Another Reference Chart. .... 3", 108, 540, 188),
    ]
    title_case = _doc(
        "LIST OF FIGURES",
        [
            ("Figure 1 Covariance Analysis Methods in Sklearn and Matlab. .... 1", 108, 540, 140),
            *peers,
        ],
    )
    assert _issues(title_case, "P024") == []
    sentence_case = _doc(
        "LIST OF FIGURES",
        [
            ("Figure 1 Covariance analysis methods in Sklearn and Matlab. .... 1", 108, 540, 140),
            *peers,
        ],
    )
    assert "list_of_figures_title_case" in _issues(sentence_case, "P024")


def test_short_leader_after_attached_period_is_terminal_punctuation() -> None:
    assert _strip_trailing_lof_dot_leaders("Synthetic title. .") == "Synthetic title."
    assert _strip_trailing_lof_dot_leaders("Synthetic title . .") == "Synthetic title"


def test_wrapped_lof_title_uses_final_line_and_keeps_real_missing_punctuation() -> None:
    peers = [
        ("Figure 2.2 Second title. .... 22", 108, 540, 180),
        ("Figure 2.3 Third title. .... 23", 108, 540, 204),
    ]
    correct = _doc(
        "LIST OF FIGURES",
        [
            ("Figure 2.1 An extended comparison for case 10", 108, 510, 140),
            ("continues to its actual end. . 21", 149, 540, 154.3),
            *peers,
        ],
    )
    assert "lof_entry_missing_terminal_punctuation" not in _issues(correct, "P040")
    incorrect = _doc(
        "LIST OF FIGURES",
        [
            ("Figure 2.1 An extended comparison for case 10", 108, 510, 140),
            ("continues without a final period . . 21", 149, 540, 154.3),
            *peers,
        ],
    )
    assert "lof_entry_missing_terminal_punctuation" in _issues(incorrect, "P040")
