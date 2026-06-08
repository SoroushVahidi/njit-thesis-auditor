"""Synthetic tests for P069 — front-matter heading gate recall refinement.

All fixtures use clearly fake placeholder text only. No real dissertation content.
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
from njit_auditor.rules.pdf_approval_page_committee_blocks import (
    check_pdf_approval_page_committee_blocks,
)
from njit_auditor.rules.pdf_biosketch_degree_ordering import check_pdf_biosketch_degree_ordering
from njit_auditor.rules.pdf_dedication_centering_italic import check_pdf_dedication_centering_italic
from njit_auditor.rules.pdf_frontmatter_heading_gate import (
    find_frontmatter_headings_for_gates,
    find_gate_matches_for_heading,
    passes_standalone_line_gate,
    resolve_gate_heading_from_line,
)
from njit_auditor.rules.pdf_headings import find_named_frontmatter_headings

_PAGE_W = 612.0
_PAGE_H = 792.0
_MARGIN_L = 108.0
_CENTER_X = _PAGE_W / 2

_PLACEHOLDER_DEGREE = "Placeholder Degree Synthetic Text"
_PLACEHOLDER_LINE = "Placeholder synthetic dedication line one"


def _make_line(text: str, y: float, *, x0: float = _MARGIN_L, x1: float = 500.0) -> PdfTextLine:
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


def _save_and_load(doc: fitz.Document) -> PdfDocument:
    path = Path("/tmp") / f"p069_test_{id(doc)}.pdf"
    doc.save(path)
    doc.close()
    loaded = load_pdf_layout(str(path))
    path.unlink(missing_ok=True)
    return loaded


def test_exact_biographical_sketch_resolves_high() -> None:
    page = _make_page(1, [_make_line("BIOGRAPHICAL SKETCH", 90.0)])
    matches = find_frontmatter_headings_for_gates(_doc(page))
    assert len(matches) == 1
    assert matches[0].heading == "BIOGRAPHICAL SKETCH"
    assert matches[0].match_path == "exact"
    assert matches[0].match_confidence == "high"


def test_acknowledgments_variant_maps_to_acknowledgements() -> None:
    resolved = resolve_gate_heading_from_line("ACKNOWLEDGMENTS")
    assert resolved == ("ACKNOWLEDGEMENTS", "variant_map", "medium")


def test_list_of_tables_continued_maps_to_canonical() -> None:
    resolved = resolve_gate_heading_from_line("LIST OF TABLES (Continued)")
    assert resolved == ("LIST OF TABLES", "continued_suffix", "medium")


def test_long_prose_with_biographical_sketch_mid_sentence_no_match() -> None:
    prose = (
        "This placeholder paragraph discusses the BIOGRAPHICAL SKETCH section "
        "requirements in synthetic prose for testing only."
    )
    assert resolve_gate_heading_from_line(prose) is None
    assert not passes_standalone_line_gate(prose)


def test_dedication_embedded_in_long_prose_no_match() -> None:
    prose = (
        "A long placeholder dedication paragraph that mentions DEDICATION formatting "
        "but is clearly not a standalone heading line."
    )
    assert resolve_gate_heading_from_line(prose) is None


def test_exact_match_on_body_classified_page_no_gate_match() -> None:
    front = _make_page(1, [_make_line("ABSTRACT", 90.0)])
    body = _make_page(
        2,
        [
            _make_line("BIOGRAPHICAL SKETCH", 90.0),
            _make_line("CHAPTER 1", 600.0),
        ],
    )
    matches = find_frontmatter_headings_for_gates(_doc(front, body))
    headings = {match.heading for match in matches}
    assert "BIOGRAPHICAL SKETCH" not in headings


def test_image_only_page_no_gate_match() -> None:
    page = PdfPage(page_number=1, width=_PAGE_W, height=_PAGE_H, text_blocks=[])
    assert find_frontmatter_headings_for_gates(_doc(page)) == []


def test_p068_exact_approval_page_baseline_unchanged(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 55, 100.0), "APPROVAL PAGE", fontsize=14)
    for idx, line in enumerate(
        [
            "Dissertation Advisor",
            "Placeholder Advisor Synthetic",
            "Signature: ____________________",
            "Date: ____________________",
            "Committee Member",
            "Placeholder Member Synthetic",
            "Signature: ____________________",
            "Date: ____________________",
            "Committee Member",
            "Placeholder Member Two Synthetic",
            "Signature: ____________________",
            "Date: ____________________",
        ]
    ):
        page.insert_text((_MARGIN_L, 140.0 + idx * 24.0), line, fontsize=11)
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_p066_reaches_biosketch_via_trailing_colon_variant(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 60, 100.0), "BIOGRAPHICAL SKETCH:", fontsize=14)
    y = 200.0
    for year in (2020, 2015, 2010):
        page.insert_text(
            (_MARGIN_L, y), f"{_PLACEHOLDER_DEGREE}, {year}", fontsize=11
        )
        y += 22.0
    pdf_doc = _save_and_load(doc)
    strict = find_named_frontmatter_headings(pdf_doc)
    assert not any(match.heading == "BIOGRAPHICAL SKETCH" for match in strict)
    findings = check_pdf_biosketch_degree_ordering(pdf_doc)
    assert findings == []


def test_multiple_approval_page_gate_matches_keep_ambiguous_skip(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 55, 100.0), "APPROVAL PAGE", fontsize=14)
    page2 = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page2.insert_text((_CENTER_X - 55, 100.0), "APPROVAL PAGE", fontsize=14)
    pdf_doc = _save_and_load(doc)
    assert len(find_gate_matches_for_heading(pdf_doc, "APPROVAL PAGE")) == 2
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_resolver_exports_no_raw_line_text() -> None:
    resolved = resolve_gate_heading_from_line("ACKNOWLEDGMENTS")
    assert resolved is not None
    assert len(resolved) == 3
    for value in resolved:
        assert isinstance(value, str)


def test_strict_synthetic_doc_finding_counts_unchanged(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 30, 100.0), "DEDICATION", fontsize=14)
    for idx, text in enumerate(
        [_PLACEHOLDER_LINE, "Placeholder synthetic dedication line two"]
    ):
        page.insert_text((_MARGIN_L, 250.0 + idx * 30.0), text, fontsize=12)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    issue_types = {finding.details.get("issue_type") for finding in findings}
    assert "dedication_text_not_centered" in issue_types


def test_p065_dedication_gate_without_privacy_leakage(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 30, 100.0), "Dedication", fontsize=14)
    page.insert_text((_CENTER_X - 80, 250.0), _PLACEHOLDER_LINE, fontsize=12)
    page.insert_text(
        (_CENTER_X - 80, 280.0), "Placeholder synthetic dedication line two", fontsize=12
    )
    page.insert_text(
        (_CENTER_X - 80, 310.0), "Placeholder synthetic dedication line three", fontsize=12
    )
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_dedication_centering_italic(pdf_doc)
    for finding in findings:
        details = finding.details
        for value in details.values():
            assert _PLACEHOLDER_LINE not in str(value)
