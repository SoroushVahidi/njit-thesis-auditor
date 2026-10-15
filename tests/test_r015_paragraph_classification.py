"""R015 classification of captions and numbered run-in headings from PDF spans."""

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_indentation import (
    _is_section_heading_line,
    _is_usable_paragraph_line,
    check_pdf_indentation,
)


def _line(y: float, text: str, x: float = 108.0) -> PdfTextLine:
    span = PdfTextSpan(text=text, bbox=BBox(x0=x, y0=y, x1=x + 400, y1=y + 12))
    return PdfTextLine(text=text, spans=[span], bbox=span.bbox)


def _split_line(y: float, pieces: list[tuple[str, float, float, bool]]) -> PdfTextLine:
    spans = [
        PdfTextSpan(text=text, bold=bold, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 12))
        for text, x0, x1, bold in pieces
    ]
    return PdfTextLine(
        text="".join(span.text for span in spans),
        spans=spans,
        bbox=BBox(x0=spans[0].bbox.x0, y0=y, x1=spans[-1].bbox.x1, y1=y + 12),
    )


def _paragraph(y: float, first: PdfTextLine) -> list[PdfTextLine]:
    return [
        first,
        *(
            _line(
                y + step * 14,
                "Synthetic continuation of this paragraph with enough prose to qualify.",
            )
            for step in (1, 2, 3)
        ),
    ]


def _doc(candidate: PdfTextLine, later: PdfTextLine | None = None) -> PdfDocument:
    lines = [
        *_paragraph(
            80, _line(80, "First indented paragraph establishes the expected page style.", 144)
        ),
        *_paragraph(
            160, _line(160, "Second indented paragraph confirms that expected page style.", 144)
        ),
        *_paragraph(260, candidate),
    ]
    if later is not None:
        lines.extend(_paragraph(340, later))
    block = PdfTextBlock(
        text="\n".join(line.text for line in lines),
        lines=lines,
        bbox=BBox(x0=108, y0=80, x1=550, y1=394),
    )
    return PdfDocument(
        path="synthetic.pdf",
        pages=[PdfPage(page_number=56, width=612, height=792, text_blocks=[block])],
    )


def _missing(doc: PdfDocument) -> list[str]:
    return [
        finding.details["bbox"]
        for finding in check_pdf_indentation(doc)
        if finding.details["issue_type"] == "missing_later_indent"
    ]


def test_glued_figure_caption_is_excluded_by_label_number_and_style() -> None:
    caption = _split_line(
        260,
        [
            ("Figure", 108, 146, True),
            ("4.5", 151, 168, True),
            ("Description of experiment results", 173, 500, False),
        ],
    )
    assert not _is_usable_paragraph_line(caption)
    assert _missing(_doc(caption)) == []


def test_figure_reference_in_regular_prose_remains_eligible() -> None:
    prose = _line(260, "Figure4.5shows the experimental result in this paragraph.")
    assert _is_usable_paragraph_line(prose)
    assert _missing(_doc(prose)) == ["108.0,260.0,508.0,272.0"]


def test_numbered_bold_run_in_heading_is_not_later_paragraph() -> None:
    heading = _split_line(
        260,
        [
            ("3.3.9.8", 108, 150, True),
            ("Summary. ", 159, 226, True),
            ("The experiment continues here.", 230, 540, False),
        ],
    )
    assert _is_section_heading_line(heading)
    assert _missing(_doc(heading)) == []


def test_run_in_heading_tolerates_small_pdf_span_overlap() -> None:
    # Sample D p120 has a visible title/prose boundary despite 0.6 pt of
    # overlapping span boxes from PDF extraction.
    heading = _split_line(
        260,
        [
            ("4.2.3.2", 108, 150.1, True),
            ("Evaluation metrics. ", 159.5, 282.6, True),
            ("To evaluate reconstruction quality.", 282.0, 543.1, False),
        ],
    )
    assert _is_section_heading_line(heading)
    assert _missing(_doc(heading)) == []


def test_genuine_unindented_paragraph_after_run_in_heading_still_warns() -> None:
    heading = _split_line(
        260,
        [
            ("4.2.3.3", 108, 150, True),
            ("Results. ", 159, 226, True),
            ("The first discussion begins here.", 230, 540, False),
        ],
    )
    later = _line(340, "A separate later paragraph starts without its required first-line indent.")
    assert _missing(_doc(heading, later)) == ["108.0,340.0,508.0,352.0"]


def test_numeric_led_prose_without_bold_heading_structure_still_warns() -> None:
    prose = _split_line(
        260,
        [
            ("3.3.9.8", 108, 150, False),
            ("describes ", 159, 226, False),
            ("the measured result in ordinary prose.", 230, 540, False),
        ],
    )
    assert not _is_section_heading_line(prose)
    assert _missing(_doc(prose)) == ["108.0,260.0,540.0,272.0"]
