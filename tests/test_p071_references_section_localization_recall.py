"""Synthetic tests for P071 — references section localization recall (P064 companion).

All fixtures use clearly fake placeholder text only.
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
from njit_auditor.rules.pdf_references_citations_structural import (
    _compute_x_variance,
    _dominant_entry_cluster,
    _find_body_start_page,
    _find_references_heading_tail,
    _localize_references_heading,
    check_pdf_references_citations_structural,
)

_PAGE_W = 612.0
_PAGE_H = 792.0
_LEFT = 72.0
_LINE_H = 14.0
_ENTRY_GAP = 28.0


def _make_line(
    text: str,
    y: float,
    *,
    x0: float = _LEFT,
    x1: float = 420.0,
) -> PdfTextLine:
    bbox = BBox(x0=x0, y0=y, x1=x1, y1=y + _LINE_H)
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
    return PdfDocument(path="synthetic_p071.pdf", pages=list(pages))


def _p064_findings(pdf_path: Path) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [f for f in check_pdf_references_citations_structural(model) if f.rule_id == "P064"]


def _insert_hanging_entry(
    doc: fitz.Document,
    page_idx: int,
    y_start: float,
    *,
    first_x: float = 72.0,
    cont_x: float = 90.0,
) -> float:
    page = doc[page_idx]
    page.insert_text(
        (first_x, y_start),
        "Placeholder first line of a synthetic reference entry here",
        fontsize=12,
    )
    y = y_start + _LINE_H
    page.insert_text(
        (cont_x, y),
        "continuation placeholder text for the reference entry above",
        fontsize=12,
    )
    return y + _LINE_H


def test_normal_references_heading_still_detected(tmp_path: Path) -> None:
    doc = fitz.open()
    for _ in range(7):
        doc.new_page(width=_PAGE_W, height=_PAGE_H)
    doc[0].insert_text((_LEFT, 120.0), "CHAPTER 1 Introduction", fontsize=14)
    doc[6].insert_text((_LEFT, 100.0), "REFERENCES", fontsize=14)
    y = 130.0
    for _ in range(3):
        y = _insert_hanging_entry(doc, 6, y)
        y += 10.0
    pdf_path = tmp_path / "p071_normal_heading.pdf"
    doc.save(pdf_path)
    doc.close()

    issue_types = [f.details.get("issue_type") for f in _p064_findings(pdf_path)]
    assert "references_section_heading_not_detected" not in issue_types


def test_collapsed_chapter1_body_start_detected() -> None:
    page = _make_page(
        1,
        [
            _make_line("CHAPTER1", 100.0, x1=200.0),
            _make_line("Body placeholder text for synthetic chapter page only", 200.0),
        ],
    )
    assert _find_body_start_page(_doc(page)) == 1


def test_collapsed_appendixa_body_start_detected() -> None:
    page = _make_page(
        3,
        [
            _make_line("APPENDIXA", 110.0, x1=200.0),
            _make_line("Appendix placeholder body text synthetic only here", 200.0),
        ],
    )
    assert _find_body_start_page(_doc(page)) == 3


def test_tail_scan_finds_bibliography_without_chapter_heading(tmp_path: Path) -> None:
    doc = fitz.open()
    for _ in range(25):
        doc.new_page(width=_PAGE_W, height=_PAGE_H)
    doc[24].insert_text((_LEFT, 120.0), "BIBLIOGRAPHY", fontsize=14)
    y = 150.0
    for _ in range(6):
        y = _insert_hanging_entry(doc, 24, y)
        y += _ENTRY_GAP
    pdf_path = tmp_path / "p071_tail_bibliography.pdf"
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    assert _localize_references_heading(model, None) == (25, "BIBLIOGRAPHY")
    issue_types = [f.details.get("issue_type") for f in _p064_findings(pdf_path)]
    assert "references_section_heading_not_detected" not in issue_types


def test_tail_scan_ignores_body_prose_references_word() -> None:
    pages = [
        _make_page(
            idx,
            [
                _make_line(
                    "See references for additional synthetic placeholder context only",
                    400.0,
                )
            ],
        )
        for idx in range(1, 22)
    ]
    pages.append(
        _make_page(
            22,
            [_make_line("BIBLIOGRAPHY", 120.0, x1=200.0)],
        )
    )
    doc = _doc(*pages)
    assert _find_references_heading_tail(doc) == (22, "BIBLIOGRAPHY")


def test_tail_scan_rejects_toc_style_references_line() -> None:
    pages = [
        _make_page(i, [_make_line("Front matter placeholder text", 200.0)])
        for i in range(1, 24)
    ]
    pages.append(
        _make_page(
            24,
            [_make_line("REFERENCES .... 42", 120.0, x1=500.0)],
        ),
    )
    assert _find_references_heading_tail(_doc(*pages)) is None


def test_multiple_tail_references_candidates_skipped() -> None:
    pages = [
        _make_page(i, [_make_line("Body placeholder page text synthetic", 300.0)])
        for i in range(1, 23)
    ]
    pages.extend(
        [
            _make_page(23, [_make_line("REFERENCES", 120.0, x1=200.0)]),
            _make_page(24, [_make_line("BIBLIOGRAPHY", 120.0, x1=200.0)]),
        ]
    )
    assert _find_references_heading_tail(_doc(*pages)) is None


def test_cluster_x_variance_ignores_annotation_outlier_positions() -> None:
    lines = [
        _make_line(
            "Placeholder first line of a synthetic reference entry here",
            100.0 + i * 30,
            x0=72.0,
        )
        for i in range(6)
    ]
    lines.extend(
        _make_line("EF", 100.0 + i * 5, x0=450.0)
        for i in range(4)
    )
    cluster = _dominant_entry_cluster(lines)
    assert len(cluster) == 6
    assert _compute_x_variance(lines) < 50.0


def test_genuinely_inconsistent_x_variance_still_skips(tmp_path: Path) -> None:
    doc = fitz.open()
    for _ in range(8):
        doc.new_page(width=_PAGE_W, height=_PAGE_H)
    doc[0].insert_text((_LEFT, 120.0), "CHAPTER 1 Introduction", fontsize=14)
    doc[6].insert_text((_LEFT, 100.0), "REFERENCES", fontsize=14)
    y = 130.0
    for i in range(6):
        x0 = 72.0 if i % 2 == 0 else 220.0
        doc[6].insert_text(
            (x0, y),
            "Placeholder single-line reference entry text here synthetic only",
            fontsize=12,
        )
        y += _ENTRY_GAP
    pdf_path = tmp_path / "p071_high_variance.pdf"
    doc.save(pdf_path)
    doc.close()

    assert _p064_findings(pdf_path) == []


def _insert_flush_entry(
    doc: fitz.Document, page_idx: int, y_start: float, *, x: float = 72.0
) -> float:
    page = doc[page_idx]
    page.insert_text(
        (x, y_start),
        "Placeholder first line of a synthetic reference entry flush",
        fontsize=12,
    )
    y = y_start + _LINE_H
    page.insert_text(
        (x, y),
        "continuation flush left placeholder text for reference entry",
        fontsize=12,
    )
    return y + _LINE_H


def test_p064_indentation_issue_emitted_for_mixed_entries(tmp_path: Path) -> None:
    doc = fitz.open()
    for _ in range(8):
        doc.new_page(width=_PAGE_W, height=_PAGE_H)
    doc[0].insert_text((_LEFT, 120.0), "CHAPTER 1 Introduction", fontsize=14)
    doc[6].insert_text((_LEFT, 100.0), "REFERENCES", fontsize=14)
    y = 130.0
    for _ in range(3):
        y = _insert_hanging_entry(doc, 6, y, first_x=72.0, cont_x=102.0)
        y += _ENTRY_GAP
    for _ in range(3):
        y = _insert_flush_entry(doc, 6, y, x=72.0)
        y += _ENTRY_GAP
    pdf_path = tmp_path / "p071_indent_issue.pdf"
    doc.save(pdf_path)
    doc.close()

    issue_types = [f.details.get("issue_type") for f in _p064_findings(pdf_path)]
    assert "references_entry_indentation_inconsistent" in issue_types


def test_clean_references_section_produces_no_findings(tmp_path: Path) -> None:
    doc = fitz.open()
    for _ in range(8):
        doc.new_page(width=_PAGE_W, height=_PAGE_H)
    doc[0].insert_text((_LEFT, 120.0), "CHAPTER 1 Introduction", fontsize=14)
    doc[6].insert_text((_LEFT, 100.0), "REFERENCES", fontsize=14)
    y = 130.0
    for _ in range(6):
        y = _insert_hanging_entry(doc, 6, y, first_x=72.0, cont_x=90.0)
        y += _ENTRY_GAP
    pdf_path = tmp_path / "p071_clean_section.pdf"
    doc.save(pdf_path)
    doc.close()

    assert _p064_findings(pdf_path) == []


def test_privacy_no_reference_entry_text_in_findings(tmp_path: Path) -> None:
    secret = "SECRET_SYNTHETIC_AUTHOR_NAME_XYZ"
    doc = fitz.open()
    for _ in range(8):
        doc.new_page(width=_PAGE_W, height=_PAGE_H)
    doc[0].insert_text((_LEFT, 120.0), "CHAPTER 1 Introduction", fontsize=14)
    doc[6].insert_text((_LEFT, 100.0), "REFERENCES", fontsize=14)
    y = 130.0
    for i in range(6):
        first_x = 72.0 if i % 2 == 0 else 72.0
        cont_x = 90.0 if i % 2 == 0 else 72.0
        doc[6].insert_text(
            (first_x, y),
            f"Placeholder first line synthetic entry {secret} here",
            fontsize=12,
        )
        y += _LINE_H
        doc[6].insert_text(
            (cont_x, y),
            f"continuation placeholder synthetic text {secret}",
            fontsize=12,
        )
        y += _ENTRY_GAP
    pdf_path = tmp_path / "p071_privacy.pdf"
    doc.save(pdf_path)
    doc.close()

    for finding in _p064_findings(pdf_path):
        blob = str(finding.message) + str(finding.details)
        assert secret not in blob
