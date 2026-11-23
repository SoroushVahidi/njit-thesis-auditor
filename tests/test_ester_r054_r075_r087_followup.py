"""Synthetic regression cases for the November TOC rule clarifications."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_highlight import build_highlighted_pdf
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfPage, PdfTextLine, PdfTextSpan
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
    is_isolated_terminal_grid_leader_dot,
)
from njit_auditor.rules.pdf_toc_terminal_period import (
    _check_toc_terminal_period_page,
    check_pdf_toc_terminal_period,
)
from njit_auditor.rules.pdf_toc_title_structure import check_pdf_toc_title_structure
from njit_auditor.web_app import _highlight_boxes_by_page


def _span(text: str, x0: float, x1: float) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font="Times-Roman",
        size=12.0,
        bold=False,
        italic=False,
        bbox=BBox(x0=x0, y0=140, x1=x1, y1=153),
    )


def _entry(title: str, dot_x: float, *, with_spans: bool = True) -> TocEntryLine:
    spans = (
        [_span(title, 72, 310), _span(".", dot_x, dot_x + 4), _span("1", 500, 508)]
        if with_spans
        else []
    )
    line = PdfTextLine(
        text=f"{title} . 1",
        bbox=BBox(x0=72, y0=140, x1=508, y1=153),
        spans=spans,
    )
    return TocEntryLine(
        line=line,
        cleaned_text=line.text,
        page_number_token="1",
        page_number_right_x=508,
        indent_x=72,
        has_leader_dots=False,
    )


@pytest.mark.parametrize(
    ("title", "dot_x", "with_spans", "expected"),
    [
        ("Chapter 1 Synthetic Topic", 400, True, 0),
        ("Chapter 1 Synthetic Topic", 314, True, 0),
        ("Chapter 1 Synthetic Topic", 400, False, 0),
        ("Chapter 1 Synthetic Topic.", 400, True, 1),
        ("Chapter 1 Synthetic Topic.", 309, True, 0),
        ("Chapter 1 Synthetic Topic.", 400, False, 0),
    ],
)
def test_p054_single_dot_geometry_and_ambiguous_extraction(
    title: str, dot_x: float, with_spans: bool, expected: int
) -> None:
    page = PdfPage(page_number=3, width=612, height=792, text_blocks=[])
    context = TocPageContext(page, "table_of_contents", 100)
    entry = _entry(title, dot_x, with_spans=with_spans)
    assert len(_check_toc_terminal_period_page(context, [entry], 0)) == expected


def test_p054_attached_title_period_still_warns() -> None:
    line = PdfTextLine(
        text="Chapter 1 Synthetic Topic. 1",
        bbox=BBox(x0=72, y0=140, x1=508, y1=153),
        spans=[_span("Chapter 1 Synthetic Topic.", 72, 310), _span("1", 500, 508)],
    )
    entry = TocEntryLine(
        line=line,
        cleaned_text=line.text,
        page_number_token="1",
        page_number_right_x=508,
        indent_x=72,
        has_leader_dots=False,
    )
    page = PdfPage(page_number=3, width=612, height=792, text_blocks=[])
    context = TocPageContext(page, "table_of_contents", 100)
    assert len(_check_toc_terminal_period_page(context, [entry], 0)) == 1


def test_p054_geometry_distinguishes_leader_when_extraction_loses_space() -> None:
    page = PdfPage(page_number=3, width=612, height=792)
    context = TocPageContext(page, "table_of_contents", 100)
    entry = _entry("Chapter 1 Synthetic Topic.", 400)
    entry.cleaned_text = "Chapter 1 Synthetic Topic.. 1"
    finding, = _check_toc_terminal_period_page(context, [entry], 0)
    assert finding.details["bbox"] == "72.0,140.0,310.0,153.0"


@pytest.fixture
def mixed_dot_toc(tmp_path: Path) -> Path:
    """Separate text operators reproduce both historical one-dot cases."""
    path = tmp_path / "mixed_dot_toc.pdf"
    with fitz.open() as doc:
        doc.new_page()
        page = doc.new_page(width=612, height=792)
        page.insert_text((225, 96), "TABLE OF CONTENTS", fontname="Times-Bold", fontsize=12)
        rows = [
            ("1 EXPERIMENTAL METHODS.", (282,), 11, 12),
            ("2 MEASUREMENT PROCEDURE.", (312,), 22, 12),
            ("3 ORDINARY TERMINAL PERIOD.", (), 33, 12),
            ("4 ISOLATED LEADER ONLY", (312,), 44, 12),
            ("5 NO TERMINAL PUNCTUATION", (), 55, 12),
            ("6 LEADER GRID CONTROL", (270, 284, 298, 312), 66, 12),
            ("7 LEADER GRID CONTROL", (270, 284, 298, 312), 77, 12),
            ("8 LEADER GRID CONTROL", (270, 284, 298, 312), 88, 12),
            ("9 INPUT FROM DR. RIVERS", (270, 284, 298, 312), 99, 12),
            ("10 A MULTI-DOT LEADER. . . . . .", (), 110, 14),
            ("11 A WRAPPED CHAPTER TITLE THAT", (), None, 10),
            ("continues on its final line.", (274, 288, 302, 316), 121, 10),
            ("12 CONTIGUOUS LEADER ONLY.....", (), 132, 12),
        ]
        for i, (title, leaders, folio, size) in enumerate(rows):
            y = 135 + 24 * i - (6 if i == 11 else 0)
            x = 126 if i == 11 else 108
            page.insert_text((x, y), title, fontname="Times-Roman", fontsize=size)
            for dot_x in leaders:
                page.insert_text((dot_x, y), ".", fontname="Times-Roman", fontsize=size)
            if folio is not None:
                # Keep the folio in a distinct text operator and aligned at x=540.
                page.insert_text((540 - len(str(folio)) * 6, y), str(folio),
                                 fontname="Times-Roman", fontsize=12)
        doc.save(path)
    return path


@pytest.mark.parametrize(("folio", "grid_match"), [("11", False), ("22", True)])
def test_p054_historical_mixed_dot_rows(
    mixed_dot_toc: Path, folio: str, grid_match: bool
) -> None:
    layout = load_pdf_layout(str(mixed_dot_toc))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    index, entry = next((i, e) for i, e in enumerate(entries) if e.page_number_token == folio)
    assert is_isolated_terminal_grid_leader_dot(entry, entries) is grid_match
    findings = [
        f for f in check_pdf_toc_terminal_period(layout) if f.details["entry_index"] == str(index)
    ]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.page == 2
    assert finding.details["issue_type"] == "toc_entry_has_terminal_period"
    assert finding.details["terminal_punctuation"] == "."


def test_p054_mixed_leader_controls_and_highlights(mixed_dot_toc: Path, tmp_path: Path) -> None:
    layout = load_pdf_layout(str(mixed_dot_toc))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    findings = check_pdf_toc_terminal_period(layout)
    by_folio = {entries[int(f.details["entry_index"])].page_number_token: f for f in findings}
    assert set(by_folio) == {"11", "22", "33", "110", "121"}
    wrapped = next(e for e in entries if e.page_number_token == "121")
    assert wrapped.is_wrapped
    assert wrapped.cleaned_text.endswith("line. . . . .")

    with fitz.open(mixed_dot_toc) as original:
        glyphs = [
            char for block in original[1].get_text("rawdict")["blocks"]
            for line in block.get("lines", []) for span in line["spans"] for char in span["chars"]
        ]
    for folio, y in (("11", 135), ("22", 159), ("110", 351), ("121", 393)):
        bbox = tuple(float(v) for v in by_folio[folio].details["bbox"].split(","))
        period, first_leader, *_ = sorted(
            char["bbox"] for char in glyphs if char["c"] == "." and char["origin"][1] == y
        )
        assert bbox[0] <= period[0] + 0.1
        assert bbox[2] == pytest.approx(period[2], abs=0.1)
        assert bbox[2] + 1 < first_leader[0]

    mixed_findings = [finding for folio, finding in by_folio.items() if folio != "33"]
    export = audit_findings_to_json_dict(mixed_findings, {"audit_type": "pdf"})
    view = build_report_view(export, pdf_page_sizes=[(612, 792)] * 2)
    assert len(view.findings) == 4
    assert all(card.page == 2 and card.has_highlight and "period" in card.polished_comment
               for card in view.findings)
    highlighted = tmp_path / "highlighted.pdf"
    boxes = _highlight_boxes_by_page(export["findings"])
    result = build_highlighted_pdf(mixed_dot_toc, highlighted, boxes)
    assert result.drawn_count == 4
    with fitz.open(highlighted) as rendered:
        assert not list(rendered[0].annots())
        marks = sorted((mark.rect for mark in rendered[1].annots()), key=lambda rect: rect.y0)
    for mark, folio in zip(marks, ("11", "22", "110", "121"), strict=True):
        bbox = tuple(float(v) for v in by_folio[folio].details["bbox"].split(","))
        assert tuple(mark) == pytest.approx(
            (bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1), abs=0.11
        )


def test_p054_wrapped_period_with_partial_glyph_metrics(mixed_dot_toc: Path) -> None:
    layout = load_pdf_layout(str(mixed_dot_toc))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    index, entry = next(
        (index, entry) for index, entry in enumerate(entries) if entry.page_number_token == "121"
    )
    assert entry.is_wrapped
    assert entry.page_number_line is not None
    title_span = next(s for s in entry.page_number_line.spans if s.text.endswith("line."))
    assert title_span.char_x_bounds is not None
    title_span.char_x_bounds = None

    finding, = [
        finding for finding in _check_toc_terminal_period_page(context, entries, 0)
        if finding.details["entry_index"] == str(index)
    ]
    bbox = tuple(float(v) for v in finding.details["bbox"].split(","))
    assert bbox[0] == pytest.approx(title_span.bbox.x0, abs=0.05)
    assert bbox[2] == pytest.approx(title_span.bbox.x1, abs=0.05)
    assert bbox[2] < float(finding.details["highlight_right_limit"])


def _toc_pdf(tmp_path: Path, lines: list[str]):
    path = tmp_path / "synthetic_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 85), "TABLE OF CONTENTS", fontsize=12)
    for index, line in enumerate(lines):
        page.insert_text((108, 140 + index * 25), line, fontsize=10)
    doc.save(path)
    doc.close()
    return load_pdf_layout(str(path))


def test_p087_question_matches_exact_generic_repeat_scope(tmp_path: Path) -> None:
    rules = json.loads(
        (Path(__file__).resolve().parents[1] / "data/processed/rules/project_added_rules.json")
        .read_text(encoding="utf-8")
    )
    question = next(rule["question"] for rule in rules if rule["id"] == "P087")
    assert "same generic section title" in question
    assert "distinct numbered sections" in question
    assert "across chapters" not in question

    doc = _toc_pdf(
        tmp_path,
        [
            "1.1 Introduction .... 1",
            "2.1 Introduction .... 10",
            "2.2 Introduction to Optics .... 11",
        ],
    )
    findings = check_pdf_toc_title_structure(doc)
    repeats = [f for f in findings if f.details["issue_type"] == "toc_generic_title_repeated"]
    assert len(repeats) == 1
    assert repeats[0].details["normalized_title"] == "introduction"
    assert repeats[0].details["confidence"] == "medium"
    assert "Check whether" in repeats[0].message
    view = build_report_view(audit_findings_to_json_dict(repeats, {"audit_type": "pdf"}))
    assert "chapter or section context" in view.findings[0].polished_comment


def test_p087_unique_generic_titles_do_not_warn(tmp_path: Path) -> None:
    doc = _toc_pdf(
        tmp_path,
        [
            "1.1 Introduction .... 1",
            "2.1 Methods .... 10",
            "2.2 Introduction to Optics .... 11",
        ],
    )
    assert not [
        f
        for f in check_pdf_toc_title_structure(doc)
        if f.details["issue_type"] == "toc_generic_title_repeated"
    ]
