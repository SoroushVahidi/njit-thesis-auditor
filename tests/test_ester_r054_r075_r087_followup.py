"""Synthetic regression cases for the November TOC rule clarifications."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfPage, PdfTextLine, PdfTextSpan
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_toc_alignment import TocEntryLine, TocPageContext
from njit_auditor.rules.pdf_toc_terminal_period import _check_toc_terminal_period_page
from njit_auditor.rules.pdf_toc_title_structure import check_pdf_toc_title_structure


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
        ("Chapter 1 Synthetic Topic.", 400, True, 0),
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
