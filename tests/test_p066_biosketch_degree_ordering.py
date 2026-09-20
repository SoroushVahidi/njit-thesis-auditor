"""Synthetic tests for P066 — Biographical Sketch degree ordering check.

All PDFs are built from scratch using PyMuPDF (fitz) with clearly fake
placeholder text and synthetic years only. No real dissertation content,
biographical prose, degree names, institution names, or author names are
used anywhere in this test file.

Q023 (no birthplace/date) and Q024 (no work experience) are explicitly out of
scope for P066 and are not tested here.
"""

from __future__ import annotations

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
from njit_auditor.rules.pdf_biosketch_degree_ordering import (
    _MIN_YEAR_CANDIDATES,
    check_pdf_biosketch_degree_ordering,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAGE_W = 612.0
_PAGE_H = 792.0
_MARGIN_L = 108.0
_CENTER_X = _PAGE_W / 2

# Clearly fake placeholder strings — must NOT appear in findings.
_PLACEHOLDER_DEGREE = "Placeholder Degree Synthetic Text"
_PLACEHOLDER_INST = "Placeholder Institution Synthetic"


def _make_biosketch_page(
    *,
    degree_lines: list[tuple[str, int]] | None = None,
    add_publications_section: bool = False,
    double_heading: bool = False,
) -> fitz.Document:
    """Return a single-page fitz.Document with a BIOGRAPHICAL SKETCH heading.

    degree_lines: list of (label_text, year) inserted as short education entries.
    add_publications_section: add a 'Publications and Presentations' sub-heading.
    double_heading: add a second BIOGRAPHICAL SKETCH heading (ambiguity test).
    """
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    # Insert BIOGRAPHICAL SKETCH heading
    page.insert_text((_CENTER_X - 60, 100.0), "BIOGRAPHICAL SKETCH", fontsize=14)
    if double_heading:
        page.insert_text((_CENTER_X - 60, 130.0), "BIOGRAPHICAL SKETCH", fontsize=14)

    page.insert_text((_MARGIN_L, 170.0), "Undergraduate and Graduate Education:", fontsize=12)
    y = 200.0
    if degree_lines:
        for label, year in degree_lines:
            # Format: "Label, Year" — short line with exactly one year token.
            line_text = f"{label}, {year}"
            page.insert_text((_MARGIN_L, y), line_text, fontsize=11)
            y += 22.0

    if add_publications_section:
        y += 10.0
        page.insert_text((_MARGIN_L, y), "Publications and Presentations", fontsize=12)
        y += 22.0
        # Simulate a long publication citation line (excluded from year extraction)
        long_pub = (
            "Synthetic Author A, Synthetic Author B. Synthetic publication title "
            "in synthetic proceedings, 2015. Synthetic conference venue."
        )
        page.insert_text((_MARGIN_L, y), long_pub, fontsize=11)

    return doc


def _load(doc: fitz.Document, tmp_path: Path) -> PdfDocument:
    p = tmp_path / "test.pdf"
    doc.save(str(p))
    doc.close()
    return load_pdf_layout(str(p))


# ---------------------------------------------------------------------------
# Direct model construction helpers for edge-case tests
# ---------------------------------------------------------------------------


def _make_span(text: str) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        bbox=BBox(x0=108.0, y0=200.0, x1=400.0, y1=216.0),
        font="Helvetica",
        italic=False,
    )


def _make_line(text: str, y0: float) -> PdfTextLine:
    span = PdfTextSpan(
        text=text,
        bbox=BBox(x0=108.0, y0=y0, x1=108.0 + len(text) * 6, y1=y0 + 16.0),
        font="Helvetica",
        italic=False,
    )
    return PdfTextLine(
        spans=[span],
        bbox=BBox(x0=108.0, y0=y0, x1=108.0 + len(text) * 6, y1=y0 + 16.0),
        text=text,
    )


def _make_biosketch_doc_from_lines(
    lines: list[PdfTextLine], pre_education_lines: list[PdfTextLine] | None = None
) -> PdfDocument:
    """Build a PdfDocument directly with a BIOGRAPHICAL SKETCH heading and given lines."""
    heading_text = "BIOGRAPHICAL SKETCH"
    heading_span = PdfTextSpan(
        text=heading_text,
        bbox=BBox(x0=200.0, y0=84.0, x1=400.0, y1=100.0),
        font="Helvetica",
        italic=False,
    )
    heading_line = PdfTextLine(
        spans=[heading_span],
        bbox=BBox(x0=200.0, y0=84.0, x1=400.0, y1=100.0),
        text=heading_text,
    )
    heading_block = PdfTextBlock(
        lines=[heading_line],
        bbox=BBox(x0=200.0, y0=84.0, x1=400.0, y1=100.0),
        text=heading_text,
    )
    education_heading_span = PdfTextSpan(
        text="Undergraduate and Graduate Education:",
        bbox=BBox(x0=108.0, y0=150.0, x1=400.0, y1=166.0),
        font="Helvetica",
        italic=False,
    )
    education_heading = PdfTextLine(
        spans=[education_heading_span],
        bbox=education_heading_span.bbox,
        text=education_heading_span.text,
    )
    content_blocks: list[PdfTextBlock] = []
    if pre_education_lines:
        content_blocks.append(
            PdfTextBlock(
                lines=pre_education_lines,
                bbox=BBox(
                    x0=min(ln.bbox.x0 for ln in pre_education_lines),
                    y0=min(ln.bbox.y0 for ln in pre_education_lines),
                    x1=max(ln.bbox.x1 for ln in pre_education_lines),
                    y1=max(ln.bbox.y1 for ln in pre_education_lines),
                ),
                text=" ".join(ln.text for ln in pre_education_lines),
            )
        )
    if lines:
        content_block = PdfTextBlock(
            lines=lines,
            bbox=BBox(
                x0=min(ln.bbox.x0 for ln in lines),
                y0=min(ln.bbox.y0 for ln in lines),
                x1=max(ln.bbox.x1 for ln in lines),
                y1=max(ln.bbox.y1 for ln in lines),
            ),
            text=" ".join(ln.text for ln in lines),
        )
        content_blocks.append(content_block)
    blocks = [heading_block, PdfTextBlock(
        lines=[education_heading],
        bbox=education_heading.bbox,
        text=education_heading.text,
    ), *content_blocks]
    page = PdfPage(
        page_number=1,
        width=_PAGE_W,
        height=_PAGE_H,
        text_blocks=blocks,
    )
    return PdfDocument(path="synthetic_test.pdf", pages=[page])


# ---------------------------------------------------------------------------
# Test 1 — No BIOGRAPHICAL SKETCH page → no findings
# ---------------------------------------------------------------------------


def test_no_biosketch_page_no_findings(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_MARGIN_L, 200.0), "ABSTRACT", fontsize=14)
    page.insert_text(
        (_MARGIN_L, 250.0), "Placeholder abstract content here.", fontsize=11
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 2 — Correct descending order → no findings
# ---------------------------------------------------------------------------


def test_correct_descending_order_no_findings(tmp_path: Path) -> None:
    doc = _make_biosketch_page(
        degree_lines=[
            (_PLACEHOLDER_DEGREE, 2023),
            (_PLACEHOLDER_INST, 2019),
            (_PLACEHOLDER_DEGREE, 2015),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 3 — Ascending order (wrong) → biosketch_degree_order_suspicious
# ---------------------------------------------------------------------------


def test_ascending_order_emits_finding(tmp_path: Path) -> None:
    doc = _make_biosketch_page(
        degree_lines=[
            (_PLACEHOLDER_DEGREE, 2015),
            (_PLACEHOLDER_INST, 2019),
            (_PLACEHOLDER_DEGREE, 2023),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "biosketch_degree_order_suspicious" in issue_types


# ---------------------------------------------------------------------------
# Test 4 — Partial inversion → finding
# ---------------------------------------------------------------------------


def test_partial_inversion_emits_finding(tmp_path: Path) -> None:
    doc = _make_biosketch_page(
        degree_lines=[
            (_PLACEHOLDER_DEGREE, 2023),
            (_PLACEHOLDER_INST, 2015),
            (_PLACEHOLDER_DEGREE, 2019),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert any(
        f.details.get("issue_type") == "biosketch_degree_order_suspicious"
        for f in findings
    )


# ---------------------------------------------------------------------------
# Test 5 — Too few candidates → no findings
# ---------------------------------------------------------------------------


def test_too_few_candidates_skips(tmp_path: Path) -> None:
    count = _MIN_YEAR_CANDIDATES - 1
    doc = _make_biosketch_page(
        degree_lines=[
            (_PLACEHOLDER_DEGREE, 2015 + i * 5) for i in range(count)
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 6 — All equal years → no findings
# ---------------------------------------------------------------------------


def test_equal_years_skips() -> None:
    lines = [
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2020", 200.0 + i * 22.0)
        for i in range(3)
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 7 — Image-only page (no text blocks) → no findings
# ---------------------------------------------------------------------------


def test_image_only_page_no_findings(tmp_path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=_PAGE_W, height=_PAGE_H)
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 8 — Multiple BIOGRAPHICAL SKETCH headings → skip
# ---------------------------------------------------------------------------


def test_multiple_biosketch_headings_skips(tmp_path: Path) -> None:
    doc = _make_biosketch_page(
        degree_lines=[
            (_PLACEHOLDER_DEGREE, 2015),
            (_PLACEHOLDER_INST, 2019),
            (_PLACEHOLDER_DEGREE, 2023),
        ],
        double_heading=True,
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 9 — Years only in Publications section → no finding
# ---------------------------------------------------------------------------


def test_publication_zone_years_excluded(tmp_path: Path) -> None:
    """Year tokens appearing only after the Publications boundary should not trigger."""
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 60, 100.0), "BIOGRAPHICAL SKETCH", fontsize=14)
    # Add prose narrative (no year, below heading)
    page.insert_text((_MARGIN_L, 180.0), "Synthetic prose content here.", fontsize=11)
    # Publications section marker
    page.insert_text((_MARGIN_L, 250.0), "Publications and Presentations", fontsize=12)
    # Short lines with years — but BELOW the Publications boundary
    y = 280.0
    for yr in [2015, 2019, 2023]:
        page.insert_text((_MARGIN_L, y), f"{_PLACEHOLDER_DEGREE}, {yr}", fontsize=11)
        y += 22.0
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 10 — Long prose line with year token excluded
# ---------------------------------------------------------------------------


def test_long_prose_line_with_year_excluded() -> None:
    """Lines exceeding _MAX_DEGREE_LINE_CHARS must not be treated as candidates."""
    long_prose = (
        "This is a long placeholder prose sentence that mentions the year 2015 somewhere "
        "within the text and is clearly not a short degree-entry line as it exceeds the "
        "maximum character threshold set by the rule implementation for education candidates."
    )
    # Short lines with wrong order — they would trigger a finding if included.
    lines = [
        _make_line(long_prose, 200.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2015", 230.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2019", 252.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2023", 274.0),
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    # The long line must not be counted; only the 3 short lines count.
    # Short lines are ascending (wrong), so a finding is expected.
    assert any(
        f.details.get("issue_type") == "biosketch_degree_order_suspicious"
        for f in findings
    )
    # Confirm: the long prose text must NOT appear in any finding detail value.
    for f in findings:
        for v in f.details.values():
            assert "long placeholder prose" not in v
            assert long_prose[:30] not in v


# ---------------------------------------------------------------------------
# Test 11 — Privacy: no bio-sketch text in findings
# ---------------------------------------------------------------------------


def test_no_biosketch_text_in_findings(tmp_path: Path) -> None:
    doc = _make_biosketch_page(
        degree_lines=[
            (_PLACEHOLDER_DEGREE, 2015),
            (_PLACEHOLDER_INST, 2019),
            (_PLACEHOLDER_DEGREE, 2023),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    for f in findings:
        for v in f.details.values():
            assert _PLACEHOLDER_DEGREE not in v
            assert _PLACEHOLDER_INST not in v
            assert "placeholder" not in v.lower()
            assert "synthetic" not in v.lower()


# ---------------------------------------------------------------------------
# Test 12 — Rule ID is P066
# ---------------------------------------------------------------------------


def test_finding_rule_id_is_p066(tmp_path: Path) -> None:
    doc = _make_biosketch_page(
        degree_lines=[
            (_PLACEHOLDER_DEGREE, 2015),
            (_PLACEHOLDER_INST, 2019),
            (_PLACEHOLDER_DEGREE, 2023),
        ]
    )
    pdf_doc = _load(doc, tmp_path)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    for f in findings:
        assert f.rule_id == "P066"


def test_non_education_date_before_section_is_ignored() -> None:
    pre_education = [_make_line("Date of Birth, 1993", 120.0)]
    lines = [
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2026", 200.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2019", 222.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2013", 244.0),
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines, pre_education)
    assert check_pdf_biosketch_degree_ordering(pdf_doc) == []


def test_reverse_order_with_date_range_is_conservative() -> None:
    lines = [
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2020-2024", 200.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2016-2018", 222.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2012", 244.0),
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines)
    assert check_pdf_biosketch_degree_ordering(pdf_doc) == []


def test_month_year_uses_documented_year_precision() -> None:
    lines = [
        _make_line(f"{_PLACEHOLDER_DEGREE}, May 2024", 200.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, January 2020", 222.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2016", 244.0),
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines)
    assert check_pdf_biosketch_degree_ordering(pdf_doc) == []


def test_expected_degree_is_ranked_by_its_single_year() -> None:
    lines = [
        _make_line(f"Expected {_PLACEHOLDER_DEGREE}, 2027", 200.0),
        _make_line(f"Current {_PLACEHOLDER_DEGREE}, 2023", 222.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2018", 244.0),
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines)
    assert check_pdf_biosketch_degree_ordering(pdf_doc) == []


def test_fragmented_date_line_causes_abstention() -> None:
    lines = [
        _make_line(_PLACEHOLDER_DEGREE, 200.0),
        _make_line("2024", 216.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2019", 244.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2016", 266.0),
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines)
    assert check_pdf_biosketch_degree_ordering(pdf_doc) == []


def test_same_year_entries_are_not_ordered() -> None:
    lines = [
        _make_line(f"{_PLACEHOLDER_DEGREE}, June 2020", 200.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, January 2020", 222.0),
        _make_line(f"{_PLACEHOLDER_DEGREE}, 2016", 244.0),
    ]
    pdf_doc = _make_biosketch_doc_from_lines(lines)
    assert check_pdf_biosketch_degree_ordering(pdf_doc) == []
