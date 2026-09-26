"""Regression coverage for the R015 follow-up on Youra physical page 101.

See docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md for the
full diagnosis. Summary: Esther's new judgment on the previously-disclosed
Youra p101 open item is that the auditor was identifying the wrong line as a
paragraph's start. The paragraph actually begins at the preceding bold run-in
phrase, sharing its physical row with the paragraph's own regular-text
opening; the later flush-left line the detector had been flagging is ordinary
continuation text, not a new paragraph start.

Root cause: `_merge_same_row_fragments` correctly refuses to merge a bold
run-in heading with its same-row regular continuation (that would corrupt
the heading's own text), but paragraph grouping had no way to recognize that
the regular continuation -- and everything that follows it -- is still part
of the *same* paragraph the bold segment opens. The regular continuation's
own x0 (far right, wherever the bold phrase happened to end) then looked
like a fresh, unindented paragraph start once grouping's generous first-line
tolerance failed to bridge the gap.

Fix (`src/njit_auditor/rules/pdf_indentation.py`):

1. `_is_run_in_heading_lead` (new): true for a bold-styled line sharing a
   physical row (via `_vertical_overlap_fraction`) with a following,
   differently-styled (non-bold) line -- the same geometry
   `_merge_same_row_fragments` already uses to *refuse* to merge text, used
   here instead to identify the row's true left edge for grouping purposes.
   Explicitly excludes a bare section-number-only fragment (e.g. "2.1.3.2")
   as a candidate lead, matching the same guard `_is_short_extraction_remnant`
   already has for the unrelated split-numbered-heading pattern -- a
   numbered sub-heading's own title text, not its section number, is the
   row's true anchor (see the Muyeed regression below).
2. `_effective_row_start_x` (extended): the existing row-remnant search
   window also accepts a run-in-heading lead as a correction source, without
   `MAX_ROW_REMNANT_ABSORPTION_GAP_PT` (calibrated for short dropped
   fragments, not a full heading phrase's width).
3. `_paragraph_starts_with_run_in_heading`: the grouped paragraph's real
   first line is the bold lead-in itself. The R015 missing-indent check
   should therefore report that line when the paragraph is unindented,
   rather than reporting the following continuation line or exempting the
   paragraph entirely. Ester's separate bold-without-section-number feedback
   remains outside R015.

None of `_merge_same_row_fragments`'s own merge decision,
`_paragraph_starts_like_continuation`, `_find_split_heading_following_paragraph_indices`,
or any presentation/wording code changed.
"""

from __future__ import annotations

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_indentation import (
    _effective_row_start_x,
    _is_run_in_heading_lead,
    _paragraph_starts_with_run_in_heading,
    check_pdf_indentation,
    group_lines_into_paragraphs,
)


def _span(
    text: str,
    *,
    bold: bool = False,
    font: str = "TimesNewRomanPSMT",
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
    size: float = 12.0,
) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font=font,
        size=size,
        bold=bold,
        italic=False,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
    )


def _line(
    text: str,
    *,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
    bold: bool = False,
    font: str = "TimesNewRomanPSMT",
    spans: list[PdfTextSpan] | None = None,
) -> PdfTextLine:
    line_spans = spans or [_span(text, bold=bold, font=font, x0=x0, x1=x1, y0=y0, y1=y1)]
    return PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1), spans=line_spans)


def _block(*lines: PdfTextLine) -> PdfTextBlock:
    return PdfTextBlock(
        bbox=BBox(
            x0=min(ln.bbox.x0 for ln in lines),
            y0=min(ln.bbox.y0 for ln in lines),
            x1=max(ln.bbox.x1 for ln in lines),
            y1=max(ln.bbox.y1 for ln in lines),
        ),
        lines=list(lines),
        text=" ".join(ln.text for ln in lines),
    )


def _page(page_number: int, *blocks: PdfTextBlock) -> PdfPage:
    return PdfPage(page_number=page_number, width=612.0, height=792.0, text_blocks=list(blocks))


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(path="synthetic", pages=list(pages))


_CONT = "Continuation synthetic paragraph line text for indentation checks here."


def _bold_line(text: str, *, x0: float, x1: float, y0: float, y1: float) -> PdfTextLine:
    span = _span(text, bold=True, font="CMBX12", x0=x0, x1=x1, y0=y0, y1=y1)
    return _line(text, spans=[span], x0=x0, x1=x1, y0=y0, y1=y1)


def _regular_line(text: str, *, x0: float, x1: float, y0: float, y1: float) -> PdfTextLine:
    span = _span(text, bold=False, font="CMR12", x0=x0, x1=x1, y0=y0, y1=y1)
    return _line(text, spans=[span], x0=x0, x1=x1, y0=y0, y1=y1)


# ---------------------------------------------------------------------------
# 1. Youra-style case: bold phrase begins paragraph, regular continuation
#    shares its row, later flush-left continuation lines follow. R015 should
#    report the actual paragraph start, not the following continuation line.
# ---------------------------------------------------------------------------


def test_youra_style_bold_run_in_paragraph_reports_bold_start_not_continuation() -> None:
    para1 = [
        _line(
            "Indented synthetic paragraph opener establishing page style one.",
            x0=144.0,
            y0=80.0,
            y1=92.0,
        ),
        *[_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (94.0, 108.0, 122.0)],
    ]
    para2 = [
        _line(
            "Second indented synthetic paragraph opener for page style two.",
            x0=144.0,
            y0=150.0,
            y1=162.0,
        ),
        *[_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (164.0, 178.0, 192.0)],
    ]
    heading_line = _bold_line(
        "Synthetic run-in heading phrase", x0=108.0, x1=280.0, y0=220.0, y1=232.0
    )
    body_lead_line = _regular_line(
        "Body prose begins on the same row as the heading here",
        x0=292.0,
        x1=540.0,
        y0=220.0,
        y1=232.0,
    )
    run_in_para_rest = [_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (244.0, 258.0, 272.0)]

    doc = _doc(_page(40, _block(*para1, *para2, heading_line, body_lead_line, *run_in_para_rest)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015" and f.details.get("issue_type") == "missing_later_indent"
    ]
    assert len(findings) == 1
    assert findings[0].details["bbox"] == "108.0,220.0,280.0,232.0"
    assert findings[0].details["paragraph_index"] == "3"
    assert all(f.details["bbox"] != "108.0,244.0,504.0,256.0" for f in findings)


# ---------------------------------------------------------------------------
# 2. A correctly indented run-in paragraph must not mask a genuinely new,
#    later paragraph -- unrelated to the run-in heading -- that is missing
#    its expected indent.
# ---------------------------------------------------------------------------


def test_missing_indent_later_paragraph_still_flagged_alongside_run_in_heading() -> None:
    y = 80.0
    indented_style_paragraphs: list[PdfTextLine] = []
    for index in range(4):
        indented_style_paragraphs.append(
            _line(
                f"Indented synthetic paragraph opener establishing page style {index}.",
                x0=144.0,
                y0=y,
                y1=y + 12,
            )
        )
        y += 14.0
        for _ in range(3):
            indented_style_paragraphs.append(_line(_CONT, x0=108.0, y0=y, y1=y + 12))
            y += 14.0
        y += 14.0

    heading_line = _bold_line(
        "Synthetic run-in heading phrase", x0=144.0, x1=280.0, y0=y, y1=y + 12
    )
    body_lead_line = _regular_line(
        "Body prose begins on the same row as the heading here",
        x0=292.0,
        x1=540.0,
        y0=y,
        y1=y + 12,
    )
    y += 24.0
    run_in_para_rest = [_line(_CONT, x0=144.0, y0=y, y1=y + 12)]
    y += 28.0
    # A genuinely new, unrelated, flush-left later paragraph with no bold
    # run-in lead at all -- must still be flagged.
    unindented_para = [
        _line(
            "Flush-left synthetic paragraph missing its expected indent.", x0=108.0, y0=y, y1=y + 12
        )
        for y in (y, y + 14.0, y + 28.0, y + 42.0)
    ]

    doc = _doc(
        _page(
            41,
            _block(
                *indented_style_paragraphs,
                heading_line,
                body_lead_line,
                *run_in_para_rest,
                *unindented_para,
            ),
        )
    )
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015" and f.details.get("issue_type") == "missing_later_indent"
    ]
    assert len(findings) == 1
    assert findings[0].details["bbox"] == "108.0,412.0,504.0,424.0"


# ---------------------------------------------------------------------------
# 3. Direct unit coverage: paragraph start is recognized at the bold segment.
# ---------------------------------------------------------------------------


def test_group_lines_recognizes_bold_segment_as_paragraph_start() -> None:
    heading_line = _bold_line(
        "Synthetic run-in heading phrase", x0=108.0, x1=280.0, y0=80.0, y1=92.0
    )
    body_lead_line = _regular_line(
        "Body prose begins on the same row as the heading here",
        x0=292.0,
        x1=540.0,
        y0=80.0,
        y1=92.0,
    )
    rest = [_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (104.0, 118.0)]

    page = _page(42, _block(heading_line, body_lead_line, *rest))
    paragraphs = group_lines_into_paragraphs(page)

    assert len(paragraphs) == 1
    paragraph = paragraphs[0]
    assert len(paragraph) == 4
    assert paragraph[0].text == heading_line.text
    # The bold lead's own geometry is untouched.
    assert paragraph[0].bbox.x0 == 108.0
    # The same-row continuation's x0 is corrected to the row's true left
    # edge so downstream lines can chain-join normally.
    assert paragraph[1].bbox.x0 == 108.0
    assert _paragraph_starts_with_run_in_heading(paragraph) is True


# ---------------------------------------------------------------------------
# 4. Multi-line paragraph with normal indentation -- unaffected.
# ---------------------------------------------------------------------------


def test_ordinary_indented_paragraph_unaffected() -> None:
    para = [
        _line(
            "Ordinary indented synthetic paragraph opener for this test.",
            x0=144.0,
            y0=80.0,
            y1=92.0,
        ),
        *[_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (94.0, 108.0, 122.0)],
    ]
    doc = _doc(_page(43, _block(*para)))
    findings = [f for f in check_pdf_indentation(doc) if f.rule_id == "P015"]
    assert not findings


# ---------------------------------------------------------------------------
# 5. Regression lock: a numbered sub-heading ("2.1.3.2" + bold title) sharing
#    its row with run-in body text (the real Muyeed p34 shape found while
#    validating this fix) must anchor on the title, not the bare section
#    number.
# ---------------------------------------------------------------------------


def test_numbered_heading_with_run_in_body_anchors_on_title_not_number() -> None:
    number_line = _bold_line("2.1.3.2", x0=108.0, x1=146.0, y0=220.0, y1=232.0)
    title_line = _bold_line(
        "Synthetic Nondeterministic Algorithms Title", x0=160.0, x1=331.0, y0=220.0, y1=232.0
    )
    body_lead_line = _regular_line(
        "Regular body prose continues on the same row as the title",
        x0=343.0,
        x1=540.0,
        y0=220.0,
        y1=232.0,
    )
    # A later, unrelated line at the base left margin must NOT be absorbed
    # into this paragraph -- it belongs to whatever follows on the page.
    next_row = _regular_line(
        "Unrelated next line back at the ordinary body margin for this test.",
        x0=108.0,
        x1=374.0,
        y0=244.0,
        y1=256.0,
    )

    page = _page(44, _block(number_line, title_line, body_lead_line, next_row))
    paragraphs = group_lines_into_paragraphs(page)

    run_in_paragraphs = [p for p in paragraphs if p[0].text == title_line.text]
    assert len(run_in_paragraphs) == 1
    paragraph = run_in_paragraphs[0]
    # The row's anchor is the title (x0=160.0), not the bare section number
    # (x0=108.0) -- both are bold, but the number is explicitly excluded.
    assert paragraph[1].bbox.x0 == 160.0
    assert _paragraph_starts_with_run_in_heading(paragraph) is True


def test_effective_row_start_x_ignores_bare_section_number_as_run_in_lead() -> None:
    number = _bold_line("2.1.3.2", x0=108.0, x1=146.0, y0=220.0, y1=232.0)
    title = _bold_line(
        "Synthetic Nondeterministic Algorithms Title", x0=160.0, x1=331.0, y0=220.0, y1=232.0
    )
    body = _regular_line(
        "Regular body prose continues on the same row as the title",
        x0=343.0,
        x1=540.0,
        y0=220.0,
        y1=232.0,
    )
    raw_lines = [number, title, body]
    assert _effective_row_start_x(raw_lines, 2) == title.bbox.x0


# ---------------------------------------------------------------------------
# 6. Existing stable true-positive control: an unrelated
#    unexpected_indent_on_continuation_line finding must still be emitted
#    even with an unrelated bold run-in heading elsewhere on the same page.
# ---------------------------------------------------------------------------


def test_unexpected_indent_on_continuation_line_still_flagged_with_unrelated_run_in_heading() -> (
    None
):
    opening_para = [
        _line(
            "Prior sentence establishing a displayed equation context here.",
            x0=144.0,
            y0=40.0,
            y1=52.0,
        ),
        _line(_CONT, x0=108.0, y0=54.0, y1=66.0),
        _line(_CONT, x0=108.0, y0=68.0, y1=80.0),
    ]
    continuation_para = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=130.0,
            y1=142.0,
        ),
        _line(_CONT, x0=108.0, y0=144.0, y1=156.0),
        _line(_CONT, x0=108.0, y0=158.0, y1=170.0),
    ]
    heading_line = _bold_line(
        "Synthetic run-in heading phrase", x0=108.0, x1=280.0, y0=220.0, y1=232.0
    )
    body_lead_line = _regular_line(
        "Body prose begins on the same row as the heading here",
        x0=292.0,
        x1=540.0,
        y0=220.0,
        y1=232.0,
    )
    run_in_para_rest = [_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (244.0, 258.0)]

    doc = _doc(
        _page(
            45,
            _block(*opening_para),
            _block(*continuation_para, heading_line, body_lead_line, *run_in_para_rest),
        )
    )
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# 7. Boundary: a bold line that is a genuinely standalone heading (no
#    same-row continuation at all) must not be treated as a run-in lead, and
#    must not exempt an unrelated, genuinely unindented later paragraph.
# ---------------------------------------------------------------------------


def test_standalone_bold_heading_not_treated_as_run_in_lead() -> None:
    heading_line = _bold_line(
        "Synthetic Standalone Heading", x0=108.0, x1=280.0, y0=150.0, y1=162.0
    )
    assert _is_run_in_heading_lead(heading_line, heading_line) is False

    # No same-row neighbor exists at all in this raw-line window: the
    # heading's own row-start correction must be a no-op.
    raw_lines = [
        heading_line,
        _line(
            "Unrelated next-row body text for this synthetic test.", x0=108.0, y0=174.0, y1=186.0
        ),
    ]
    assert _effective_row_start_x(raw_lines, 1) == raw_lines[1].bbox.x0


def test_standalone_bold_heading_does_not_exempt_unrelated_missing_indent_paragraph() -> None:
    para1 = [
        _line(
            "Indented synthetic paragraph opener establishing page style one.",
            x0=144.0,
            y0=80.0,
            y1=92.0,
        ),
        *[_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (94.0, 108.0, 122.0)],
    ]
    para2 = [
        _line(
            "Second indented synthetic paragraph opener for page style two.",
            x0=144.0,
            y0=136.0,
            y1=148.0,
        ),
        _line(_CONT, x0=108.0, y0=150.0, y1=162.0),
    ]
    # A standalone bold heading on its own row, with no same-row
    # continuation -- must not be confused with a run-in lead.
    heading_line = _bold_line(
        "Synthetic Standalone Heading", x0=108.0, x1=280.0, y0=176.0, y1=188.0
    )
    # A third, ordinary indented paragraph opens right after the heading
    # (correctly exempt as the paragraph following a heading, via the
    # pre-existing generous first-line grouping tolerance).
    opener_para = [
        _line(
            "Correctly flush opening paragraph right after the heading.",
            x0=108.0,
            y0=200.0,
            y1=212.0,
        ),
        *[_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (214.0, 228.0)],
    ]
    # A later, unrelated, genuinely unindented paragraph must still be
    # flagged -- it does not directly follow the heading.
    unindented_para = [
        _line(
            "Flush-left synthetic paragraph missing its expected indent.", x0=108.0, y0=y, y1=y + 12
        )
        for y in (256.0, 270.0, 284.0, 298.0)
    ]

    doc = _doc(
        _page(46, _block(*para1, *para2, heading_line, *opener_para, *unindented_para))
    )
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015" and f.details.get("issue_type") == "missing_later_indent"
    ]
    assert len(findings) == 1
