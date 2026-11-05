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


def _continued_title(
    number: str, continuation: str, *, split_number: bool,
    packed_prefix: bool = False, body: str = "", whitespace: str = " ",
) -> PdfDocument:
    doc = _document(number, "Synthetic heading e.g.", tail=continuation,
                    split_number=split_number)
    line = doc.pages[0].text_blocks[-1].lines[0]
    if packed_prefix:
        prefix = line.spans[:-1]
        line.spans[:-1] = [PdfTextSpan(
            text=("" if split_number else number + " ") + "Synthetic heading e.g.",
            font="Times-Bold", size=12, bold=True,
            bbox=BBox(x0=prefix[0].bbox.x0, y0=300,
                      x1=prefix[-1].bbox.x1, y1=312),
        )]
    tail = line.spans[-1]
    tail.bold = True
    tail.font = "Times-Bold"
    line.spans.insert(-1, PdfTextSpan(
        text=whitespace, font="Times-Roman", size=12,
        bbox=BBox(x0=line.spans[-2].bbox.x1, y0=300, x1=tail.bbox.x0, y1=312),
    ))
    if body:
        line.spans.append(PdfTextSpan(
            text=body, font="Times-Roman", size=12,
            bbox=BBox(x0=tail.bbox.x1 + 5, y0=300,
                      x1=tail.bbox.x1 + 5 + 4 * len(body), y1=312),
        ))
        line.text += " " + body
        line.bbox.x1 = line.spans[-1].bbox.x1
    return doc


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
@pytest.mark.parametrize("packed_prefix", [False, True])
def test_regular_whitespace_does_not_end_a_bold_heading(
    number: str, split_number: bool, packed_prefix: bool,
) -> None:
    issues = _issues(_continued_title(
        number, "continued heading", split_number=split_number,
        packed_prefix=packed_prefix,
    ))
    assert any("punctuation" in issue for issue in issues)


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
@pytest.mark.parametrize("packed_prefix", [False, True])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("whitespace", [" ", "\u00a0", "\t"])
def test_only_the_complete_bold_title_controls_the_period_before_body(
    number: str, split_number: bool, packed_prefix: bool,
    terminal_period: bool, whitespace: str,
) -> None:
    continuation = "continued heading" + ("." if terminal_period else "")
    issues = _issues(_continued_title(
        number, continuation, split_number=split_number, whitespace=whitespace,
        packed_prefix=packed_prefix,
        body="ordinary paragraph body continues here",
    ))
    assert any("punctuation" in issue for issue in issues) is not terminal_period


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_body_emphasis_does_not_extend_the_completed_heading(number: str) -> None:
    doc = _continued_title(
        number, "continued heading.", split_number=True,
        body="ordinary paragraph body continues here",
    )
    line = doc.pages[0].text_blocks[-1].lines[0]
    line.spans.append(PdfTextSpan(
        text="emphasized body words", font="Times-Bold", size=12, bold=True,
        bbox=BBox(x0=line.bbox.x1 + 5, y0=300, x1=line.bbox.x1 + 100, y1=312),
    ))
    line.text += " emphasized body words"
    line.bbox.x1 = line.spans[-1].bbox.x1
    assert not any("punctuation" in issue for issue in _issues(doc))


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
