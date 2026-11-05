"""Synthetic controls for periods on geometrically spaced run-in headings."""

from __future__ import annotations

import pytest

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_heading_levels import check_pdf_heading_level_styles


def _document(
    number: str,
    title: str,
    *,
    split_number: bool = True,
    tail: str = "ordinary text continues on this row",
    tail_italic: bool = False,
) -> PdfDocument:
    x = 108.0
    spans: list[PdfTextSpan] = []
    for word in [number, *title.split()]:
        width = 4.0 * len(word)
        spans.append(PdfTextSpan(
            text=word, font="Times-Bold", size=12, bold=True,
            bbox=BBox(x0=x, y0=300, x1=x + width, y1=312),
        ))
        x += width + 5.0
    if tail:
        spans.append(PdfTextSpan(
            text=tail, font="Times-Italic" if tail_italic else "Times-Roman",
            size=12, bold=False, italic=tail_italic,
            bbox=BBox(x0=x, y0=300, x1=x + 4.0 * len(tail), y1=312),
        ))

    def line(parts: list[PdfTextSpan], text: str) -> PdfTextLine:
        return PdfTextLine(
            text=text, spans=parts,
            bbox=BBox(x0=parts[0].bbox.x0, y0=300, x1=parts[-1].bbox.x1, y1=312),
        )

    if split_number:
        lines = [line(spans[:1], number), line(spans[1:], "".join(s.text for s in spans[1:]))]
    else:
        lines = [line(spans, f"{number} {title} {tail}".strip())]
    blocks = [PdfTextBlock(text=ln.text, bbox=ln.bbox, lines=[ln]) for ln in lines]
    return PdfDocument(
        path="synthetic-run-in.pdf",
        pages=[PdfPage(page_number=5, width=612, height=792, text_blocks=blocks)],
    )


def _issues(doc: PdfDocument) -> list[str]:
    return [f.details["issue_type"] for f in check_pdf_heading_level_styles(doc)]


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
def test_existing_heading_period_before_regular_body_is_not_missing(
    number: str, split_number: bool,
) -> None:
    assert not any("punctuation" in issue for issue in _issues(
        _document(number, "Synthetic heading boundary.", split_number=split_number)
    ))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_genuine_missing_heading_period_still_warns(number: str) -> None:
    assert any("punctuation" in issue for issue in _issues(
        _document(number, "Synthetic heading boundary")
    ))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_colon_ended_heading_still_requires_period(number: str) -> None:
    assert any("punctuation" in issue for issue in _issues(
        _document(number, "Synthetic heading boundary:")
    ))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_heading_case_warning_is_preserved_independently(number: str) -> None:
    issues = _issues(_document(number, "Synthetic Heading Boundary."))
    assert any(issue.endswith("_sentence_case_issue") for issue in issues)
    assert not any("punctuation" in issue for issue in issues)


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_period_before_italic_heading_continuation_is_not_a_run_in_boundary(number: str) -> None:
    assert any("punctuation" in issue for issue in _issues(
        _document(number, "Synthetic heading e.g.", tail="variable", tail_italic=True)
    ))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_period_before_single_math_symbol_is_not_a_run_in_boundary(number: str) -> None:
    assert any("punctuation" in issue for issue in _issues(
        _document(number, "Synthetic heading e.g.", tail="x")
    ))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_fully_bold_heading_with_period_remains_valid(number: str) -> None:
    assert not any("punctuation" in issue for issue in _issues(
        _document(number, "Synthetic heading boundary.", tail="")
    ))
