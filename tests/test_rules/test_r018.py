"""Regression tests for R018/P018 TOC/List alignment checks.

Covers two general (non-hardcoded) bugs found while resolving Ester's R018
feedback -- see docs/status/r018_ester_reconciliation_20260907.md:

1. ``_has_leader_dot_pattern`` only recognized literal ASCII ``...`` runs.
   Many PDFs render leader dots as Unicode horizontal-ellipsis characters
   (``…``), and wrapped (two-line) entries often extract the leader as two
   dot clusters joined by a single space. Both were misread as "no leader
   dots", producing false ``inconsistent_leader_dots`` findings.

2. ``NUMERIC_PREFIX_RE`` / ``SECTION_NUMBER_PREFIX_RE`` required whitespace
   immediately after the section/figure number, so a number written with a
   trailing period (``"2.1. Title"``, common in List of Figures/Tables)
   never qualified as a wrap-mergeable entry start. A two-line List of
   Figures/Tables entry using this style split into two unrelated rows,
   with the continuation's hanging-indent x-position misread as a hierarchy
   indent outlier.
"""

from pathlib import Path

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
    NUMERIC_PREFIX_RE,
    _extract_page_number_token,
    _has_leader_dot_pattern,
    _has_prefix_entry_shape,
    check_pdf_toc_alignment,
)
from njit_auditor.rules.pdf_toc_leader_consistency import check_pdf_toc_leader_consistency


def test_leader_dot_pattern_recognizes_literal_ascii_run() -> None:
    assert _has_leader_dot_pattern("Chapter 1 Introduction .... 5")


def test_leader_dot_pattern_recognizes_unicode_ellipsis_run() -> None:
    assert _has_leader_dot_pattern("Chapter 1 Introduction……………… 5")


def test_leader_dot_pattern_recognizes_short_two_ellipsis_run() -> None:
    """Two ellipsis characters are only 2 raw characters but 6 visible dots."""
    assert _has_leader_dot_pattern("DERIVATIZATION…… 35")


def test_leader_dot_pattern_recognizes_wrap_split_run_with_gap() -> None:
    """A wrapped continuation's leader often extracts as two dot clusters
    joined by a single space -- still a single visible leader to a reader."""
    assert _has_leader_dot_pattern("mass spectrometry……………… ……………………… 15")


def test_leader_dot_pattern_recognizes_spaced_period_leader() -> None:
    """LaTeX-style dotfill leaders often extract with a space between each
    period rather than a contiguous run."""
    assert _has_leader_dot_pattern("Background . . . . . . . . . . . . . . 4")


def test_leader_dot_pattern_rejects_single_trailing_period() -> None:
    assert not _has_leader_dot_pattern("Some Concluding Sentence. 5")


def test_leader_dot_pattern_rejects_two_periods() -> None:
    assert not _has_leader_dot_pattern("sample the global minimum . 43")


def test_leader_dot_pattern_rejects_no_dots_at_all() -> None:
    assert not _has_leader_dot_pattern("Research Questions and Prior Work 6")


def test_numeric_prefix_accepts_trailing_period_before_space() -> None:
    """Figure/table numbers are sometimes written "2.1." (trailing period)
    rather than "2.1 "; both must be recognized as a numbered entry start."""
    assert NUMERIC_PREFIX_RE.match("2.1. Representative snake species")
    assert NUMERIC_PREFIX_RE.match("2.1 Representative snake species")


def test_has_prefix_entry_shape_accepts_trailing_period_section_number() -> None:
    assert _has_prefix_entry_shape("2.1. Representative snake species")


def test_roman_letter_inside_title_is_not_a_page_number_span() -> None:
    """A one-letter variable in a title can match the Roman numeral grammar."""
    prefix = PdfTextSpan(text="Figure 8.7 Features (", bbox=BBox(x0=108, y0=100, x1=445, y1=112))
    variable = PdfTextSpan(text="d", bbox=BBox(x0=445, y0=100, x1=451, y1=112))
    suffix = PdfTextSpan(text="); horizontal axis", bbox=BBox(x0=451, y0=100, x1=511, y1=112))
    line = PdfTextLine(
        spans=[prefix, variable, suffix],
        bbox=BBox(x0=108, y0=100, x1=511, y1=112),
        text="Figure 8.7 Features (d); horizontal axis",
    )
    assert _extract_page_number_token(line, line.text) == (None, None)

    page_number = PdfTextSpan(text="157", bbox=BBox(x0=523, y0=100, x1=540, y1=112))
    numbered = line.model_copy(
        update={
            "spans": [prefix, variable, suffix, page_number],
            "bbox": BBox(x0=108, y0=100, x1=540, y1=112),
            "text": line.text + " 157",
        }
    )
    assert _extract_page_number_token(numbered, numbered.text) == ("157", 540)


def _draw_line(page: fitz.Page, x: float, y: float, text: str) -> None:
    page.insert_text((x, y), text, fontsize=12)


def _toc_doc(heading: str, rows: list[tuple[float, float, str]]) -> PdfDocument:
    """Build a PdfDocument directly from (x0, y0, text) rows, one line per row.

    Bypasses actual PDF rendering: PyMuPDF's base-14 fonts do not reliably
    round-trip Unicode ellipsis (``…``) through insert-then-extract, which
    would make a rendered-PDF test of ellipsis handling font-fidelity
    dependent rather than a test of the parsing logic itself. Each row gets
    no spans, so ``_line_text_for_toc`` falls back to the given ``text``
    verbatim -- an exact, font-independent stand-in for extracted text.
    """
    lines = [
        PdfTextLine(spans=[], bbox=BBox(x0=0.0, y0=60.0, x1=300.0, y1=75.0), text=heading)
    ]
    for x0, y0, text in rows:
        width = max(len(text) * 5.5, 40.0)
        lines.append(
            PdfTextLine(
                spans=[],
                bbox=BBox(x0=x0, y0=y0, x1=x0 + width, y1=y0 + 13.0),
                text=text,
            )
        )
    block = PdfTextBlock(lines=lines, bbox=BBox(x0=0.0, y0=60.0, x1=612.0, y1=780.0), text="")
    page = PdfPage(
        page_number=1,
        original_page_index=0,
        original_page_number=1,
        manuscript_page_index=0,
        manuscript_page_number=1,
        width=612.0,
        height=792.0,
        text_blocks=[block],
        graphic_blocks=[],
    )
    return PdfDocument(path="<test>", pages=[page])


def test_ellipsis_wrapped_entry_does_not_false_positive_missing_dots() -> None:
    """Regression guard for the Ester-reviewed Praneeth false positive: a
    two-line entry whose leader-dot run is Unicode ellipsis, split across
    the wrap with a space gap, must not be reported as missing dots when
    every other entry on the page is consistently dotted."""
    doc = _toc_doc(
        "TABLE OF CONTENTS",
        [
            (108.0, 140.0, "1 INTRODUCTION………………………………………………… 1"),
            (126.0, 160.0, "1.1 Background and Need for the Present"),
            (108.0, 175.0, "Study……………………… ………………………… 3"),
            (126.0, 200.0, "1.2 Prior Work…………………………………………… 6"),
            (126.0, 220.0, "1.3 Research Questions…………………………… 9"),
            (126.0, 240.0, "1.4 Overview of Chapters………………………… 12"),
        ],
    )
    warnings = [f for f in check_pdf_toc_alignment(doc) if f.rule_id == "P018"]
    assert not any(w.details.get("issue_type") == "inconsistent_leader_dots" for w in warnings)
    assert check_pdf_toc_leader_consistency(doc) == []


def test_ellipsis_toc_still_flags_a_genuinely_missing_dots_entry() -> None:
    """The ellipsis fix must not blind the check to a real violation: one
    entry with no leader at all, among otherwise consistently ellipsis-
    dotted peers, must still be flagged by P075 (Q052). P018 retains its
    alignment and placement checks without duplicating TOC leader style."""
    doc = _toc_doc(
        "TABLE OF CONTENTS",
        [
            (108.0, 140.0, "1 INTRODUCTION………………………………………………… 1"),
            (126.0, 160.0, "1.1 Background…………………………………………… 2"),
            (126.0, 180.0, "1.2 Prior Work…………………………………………… 6"),
            (126.0, 200.0, "1.3 Research Questions and Aims Overview          9"),
            (126.0, 220.0, "1.4 Overview of Chapters………………………… 12"),
            (126.0, 240.0, "1.5 Significance of the Study……………… 14"),
        ],
    )
    warnings = [f for f in check_pdf_toc_alignment(doc) if f.rule_id == "P018"]
    assert not any(w.details.get("issue_type") == "inconsistent_leader_dots" for w in warnings)
    leader_findings = check_pdf_toc_leader_consistency(doc)
    assert len(leader_findings) == 1
    finding = leader_findings[0]
    assert finding.rule_id == "P075"
    assert finding.details["issue_type"] == "toc_missing_leader_style"
    assert finding.details["entries_without_leader"] == "1"
    assert finding.details["dominant_style"] == "dot"
    assert finding.details["source_q_rule_id"] == "Q052"
    assert finding.page == 1


def test_trailing_period_figure_number_wrap_merges_and_does_not_misalign(
    tmp_path: Path,
) -> None:
    """Regression guard for the Ester-reviewed Anthony false positive: a
    List of Figures entry numbered "2.1." (trailing period) that wraps to a
    second, hanging-indented line must merge into one logical entry instead
    of leaving the continuation's indent misread as a hierarchy outlier."""
    pdf_path = tmp_path / "lof_trailing_period_wrap.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_line(page, 230, 90, "LIST OF FIGURES")
    _draw_line(page, 108, 140, "1.1. Supporting publications for prior work (1990-2020).. 7")
    _draw_line(page, 108, 170, "2.1. Representative snake species (Families: Elapidae,")
    _draw_line(page, 144, 185, "Aniliidae, and Dipsadidae)........................... 33")
    _draw_line(page, 108, 215, "2.2. Principal coordinates analysis of variation..... 39")
    _draw_line(page, 108, 245, "2.3. Multi-panel regression of geographic distance and")
    _draw_line(page, 144, 260, "phenotypic dissimilarity............................. 40")
    _draw_line(page, 108, 290, "2.4. Species-pair analysis of phenotypic convergence. 43")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    assert not any(
        w.details.get("issue_type") == "inconsistent_hierarchy_indent" for w in warnings
    )
