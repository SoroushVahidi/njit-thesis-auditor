"""P018 TOC visual-row reconstruction and page-number association regressions."""

from __future__ import annotations

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
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    check_pdf_lot_lof_entry_number_alignment,
)
from njit_auditor.rules.pdf_lot_terminal_period import check_pdf_lot_terminal_period
from njit_auditor.rules.pdf_toc_alignment import (
    TocPageContext,
    check_pdf_toc_alignment,
    extract_toc_entry_lines,
)
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting

_PAGE_W = 612.0
_PAGE_H = 792.0


def _span(text: str, x0: float, y: float, width: float, size: float = 12.0) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        bbox=BBox(x0=x0, y0=y, x1=x0 + width, y1=y + size + 2),
        font="Times-Roman",
        size=size,
    )


def _line_from_spans(spans: list[PdfTextSpan], *, glued: bool = True) -> PdfTextLine:
    bbox = BBox(
        x0=min(s.bbox.x0 for s in spans),
        y0=min(s.bbox.y0 for s in spans),
        x1=max(s.bbox.x1 for s in spans),
        y1=max(s.bbox.y1 for s in spans),
    )
    text = "".join(s.text for s in spans) if glued else " ".join(s.text for s in spans)
    return PdfTextLine(spans=spans, bbox=bbox, text=text)


def _line(text: str, x0: float, y: float, width: float) -> PdfTextLine:
    return _line_from_spans([_span(text, x0, y, width)], glued=True)


def _toc_page(lines: list[PdfTextLine], page_number: int = 11) -> PdfPage:
    heading = _line("TABLE OF CONTENTS", 220, 90, 200)
    return _list_page(heading, lines, page_number)


def _list_page(
    heading: PdfTextLine,
    lines: list[PdfTextLine],
    page_number: int,
) -> PdfPage:
    all_lines = [heading, *lines]
    block = PdfTextBlock(
        lines=all_lines,
        bbox=BBox(x0=100, y0=90, x1=560, y1=700),
        text="\n".join(line.text for line in all_lines),
    )
    return PdfPage(page_number=page_number, width=_PAGE_W, height=_PAGE_H, text_blocks=[block])


def _p018(doc: PdfDocument, issue: str) -> list:
    return [
        f
        for f in check_pdf_toc_alignment(doc)
        if f.rule_id == "P018" and f.details.get("issue_type") == issue
    ]


def test_toc_far_right_page_number_separate_spans_associated() -> None:
    y = 140.0
    page = _toc_page(
        [
            _line("1.1 Title Alpha", 124, y, 200),
            _line("12", 528, y, 14),
            _line("1.2 Title Beta .... 24", 124, 160, 420),
            _line("1.3 Title Gamma .... 36", 124, 180, 420),
            _line("1.4 Title Delta .... 48", 124, 200, 420),
        ]
    )
    # Represent 1.1 as three column fragments on one baseline.
    page = _toc_page(
        [
            _line("1.1", 124, y, 20),
            _line("Title Alpha", 151, y, 200),
            _line("12", 528, y, 14),
            _line("1.2 Title Beta .... 24", 124, 160, 420),
            _line("1.3 Title Gamma .... 36", 124, 180, 420),
            _line("1.4 Title Delta .... 48", 124, 200, 420),
        ]
    )
    ctx = TocPageContext(page=page, page_type="table_of_contents", heading_bottom_y=110)
    entries = extract_toc_entry_lines(ctx)
    target = next(e for e in entries if "Title Alpha" in e.cleaned_text)
    assert target.page_number_token == "12"
    assert "1.1" in target.cleaned_text
    assert not _p018(PdfDocument(path="t.pdf", pages=[page]), "missing_page_number")


def test_toc_split_section_number_not_glued_to_title() -> None:
    y = 140.0
    # Same physical line: number span + title span with trailing page number, historically glued.
    spans = [
        _span("3.3.3", 151.3, y, 26.4),
        _span(
            "Geometric preliminaries: Shape operator and principal curvatures 42",
            186.4,
            y,
            352.6,
        ),
    ]
    glued = _line_from_spans(spans, glued=True)
    assert "3.3.3Geometric" in glued.text
    page = _toc_page(
        [
            glued,
            _line("3.3.4 Other title .... 45", 151, 160, 400),
            _line("3.3.5 Other title .... 46", 151, 180, 400),
            _line("3.3.6 Other title .... 48", 151, 200, 400),
        ]
    )
    ctx = TocPageContext(page=page, page_type="table_of_contents", heading_bottom_y=110)
    entries = extract_toc_entry_lines(ctx)
    target = next(e for e in entries if "Geometric preliminaries" in e.cleaned_text)
    assert "3.3.3 Geometric" in target.cleaned_text
    assert "3.3.3Geometric" not in target.cleaned_text
    assert target.page_number_token == "42"


def test_toc_page_number_without_leader_dots_still_associated() -> None:
    y = 140.0
    title = _line(
        "3.3 The Off-Diagonal Weingarten Loss for CAD-Type Neural SDF Reconstruction 40",
        151.3,
        y,
        408.9,
    )
    page = _toc_page(
        [
            _line("3.3", 124.3, y, 16.5),
            title,
            _line("3.4 Next section title .... 50", 124, 160, 400),
            _line("3.5 Another section title .... 60", 124, 180, 400),
            _line("3.6 Final section title .... 70", 124, 200, 400),
        ]
    )
    ctx = TocPageContext(page=page, page_type="table_of_contents", heading_bottom_y=110)
    entries = extract_toc_entry_lines(ctx)
    target = next(e for e in entries if "Weingarten Loss" in e.cleaned_text)
    assert target.page_number_token == "40"
    missing = _p018(PdfDocument(path="t.pdf", pages=[page]), "missing_page_number")
    assert not missing


def test_toc_same_level_title_indents_do_not_warn() -> None:
    page = _toc_page(
        [
            _line("3.1.1", 151.3, 140, 25),
            _line("Motivation", 186.4, 140, 60),
            _line("17", 529, 140, 12),
            _line("3.1.2", 151.3, 160, 25),
            _line("Problem formulation", 186.4, 160, 120),
            _line("19", 529, 160, 12),
            _line("3.1.3", 151.3, 180, 25),
            _line("Related work", 186.4, 180, 80),
            _line("21", 529, 180, 12),
            _line("3.1.4", 151.3, 200, 25),
            _line("Preliminaries", 186.4, 200, 80),
            _line("25", 529, 200, 12),
        ]
    )
    doc = PdfDocument(path="t.pdf", pages=[page])
    assert not _p018(doc, "inconsistent_hierarchy_indent")


def test_toc_genuine_missing_page_number_still_warns(tmp_path) -> None:
    pdf_path = tmp_path / "toc_missing.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16)
    page.insert_text((108, 140), "1 Introduction .... 1")
    page.insert_text((108, 160), "2 Methods .... 2")
    page.insert_text((108, 180), "3 Results without a page number")
    page.insert_text((108, 200), "4 Discussion .... 4")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert _p018(model, "missing_page_number")


def test_toc_genuine_hierarchy_indent_mismatch_still_warns(tmp_path) -> None:
    pdf_path = tmp_path / "toc_indent.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16)
    # Level-3 cohort: three aligned, one clearly shifted.
    page.insert_text((151, 140), "3.1.1 Motivation .... 17")
    page.insert_text((151, 160), "3.1.2 Problem formulation .... 19")
    page.insert_text((151, 180), "3.1.3 Related work .... 21")
    page.insert_text((220, 200), "3.1.4 Preliminaries .... 25")  # shifted +69pt
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert _p018(model, "inconsistent_hierarchy_indent")


def test_toc_wrapped_entry_page_number_on_continuation_row() -> None:
    page = _toc_page(
        [
            _line(
                "3.4 Scheduling the Off-Diagonal Weingarten Loss for CAD-Type Neural",
                124,
                140,
                380,
            ),
            _line("SDF Reconstruction", 163, 154.5, 120),
            _line("63", 528, 154.5, 14),
            _line("3.5 Feature-Aware Sampling .... 72", 124, 180, 400),
            _line("3.6 Another Entry Title .... 80", 124, 200, 400),
            _line("3.7 Final Entry Title .... 90", 124, 220, 400),
        ]
    )
    ctx = TocPageContext(page=page, page_type="table_of_contents", heading_bottom_y=110)
    entries = extract_toc_entry_lines(ctx)
    target = next(e for e in entries if e.cleaned_text.startswith("3.4"))
    assert target.page_number_token == "63"
    assert "SDF Reconstruction" in target.cleaned_text


def test_lof_multiline_wrap_chains_to_trailing_page_number() -> None:
    """Multi-line LoF description with page number on the final wrap row."""
    heading = _line("LIST OF FIGURES", 220, 90, 200)
    lines = [
        heading,
        _line(
            "3.2 Comparison of automatic-differentiation and finite-difference",
            108,
            140,
            400,
        ),
        _line("second-order regularization on ABC CAD models.", 149, 154, 300),
        _line("order differentiation.", 149, 168, 140),
        _line("39", 528, 168, 14),
        _line("3.3 Another figure description ends here .... 40", 108, 200, 400),
        _line("3.4 Third figure description ends here .... 41", 108, 220, 400),
    ]
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=90, x1=560, y1=700),
        text="\n".join(line.text for line in lines),
    )
    page = PdfPage(page_number=15, width=_PAGE_W, height=_PAGE_H, text_blocks=[block])
    ctx = TocPageContext(page=page, page_type="list_of_figures", heading_bottom_y=110)
    entries = extract_toc_entry_lines(ctx)
    target = next(e for e in entries if e.cleaned_text.startswith("3.2"))
    assert target.page_number_token == "39"
    assert "order differentiation." in target.cleaned_text
    missing = [
        f
        for f in check_pdf_toc_alignment(PdfDocument(path="t.pdf", pages=[page]))
        if f.details.get("issue_type") == "missing_page_number"
        and "3.2" in (f.details.get("affected_entry_preview") or "")
    ]
    assert not missing


def test_right_margin_annotation_not_merged_into_toc_entry() -> None:
    """Reviewer notes on the same baseline are not entry content."""
    page = _toc_page(
        [
            _line("5.2.2", 151, 140, 25),
            _line("Future Work", 186, 140, 80),
            _line("Reviewer Name", 430, 140, 80),
            _line("107", 528, 140, 16),
        ]
    )
    ctx = TocPageContext(page=page, page_type="table_of_contents", heading_bottom_y=110)
    entries = extract_toc_entry_lines(ctx)
    assert len(entries) == 1
    assert entries[0].cleaned_text == "5.2.2 Future Work 107"


def test_p024_wrapped_lot_continuation_not_checked_as_separate_title() -> None:
    """A lowercase continuation is parsed in its complete title context."""
    page = _list_page(
        _line("LIST OF TABLES", 220, 90, 200),
        [
            _line("3.10", 108, 140, 25),
            _line("Comparison of Uniform Sampling on", 137, 140, 250),
            _line("the ABC Dataset with NSH Backbone", 149, 154, 220),
            _line("80", 528, 154, 14),
            _line("3.11 Another Properly Capitalized Table Title", 108, 180, 350),
            _line("81", 528, 180, 14),
        ],
        14,
    )
    findings = check_pdf_toc_list_formatting(PdfDocument(path="lot.pdf", pages=[page]))
    assert not [
        finding
        for finding in findings
        if finding.details.get("issue_type") == "list_of_tables_title_case"
    ]


def test_p046_wrapped_lof_entry_uses_entry_start_column() -> None:
    """Wrapped description text does not become a shifted figure-number row."""
    page = _list_page(
        _line("LIST OF FIGURES", 220, 90, 200),
        [
            _line("3.1 First figure description.", 108, 140, 250),
            _line("30", 528, 140, 14),
            _line("3.2 Second figure description wraps onto", 108, 170, 320),
            _line("a continuation line.", 149, 184, 150),
            _line("39", 528, 184, 14),
            _line("3.3 Third figure description.", 108, 220, 250),
            _line("40", 528, 220, 14),
        ],
        15,
    )
    findings = check_pdf_lot_lof_entry_number_alignment(
        PdfDocument(path="lof.pdf", pages=[page])
    )
    assert not [finding for finding in findings if finding.rule_id == "P046"]


def test_p053_reconstructed_lot_rows_retain_terminal_periods() -> None:
    """Complete reconstructed LoT entries expose each visible terminal period."""
    page = _list_page(
        _line("LIST OF TABLES", 220, 90, 200),
        [
            _line("4.1", 108, 140, 20),
            _line("Quantitative Results on the ABC Dataset.", 137, 140, 260),
            _line("98", 528, 140, 14),
            _line("4.2", 108, 170, 20),
            _line("Quantitative Results on Spot and Bunny.", 137, 170, 250),
            _line("99", 528, 170, 14),
        ],
        14,
    )
    findings = check_pdf_lot_terminal_period(PdfDocument(path="lot.pdf", pages=[page]))
    assert len(findings) == 2
    assert all(finding.details.get("bbox") for finding in findings)
