"""Regression coverage for the 2026-08 Esther/R015 false-positive batch.

Esther reviewed three real P015 findings and classified all three as false
positives. All three share one root cause -- see
docs/status/p015_r015_esther_feedback_false_positive_fix_20260825.md for the
full diagnosis:

An inline displayed equation, subscript, or superscript can split one
physical printed text row into several extraction fragments. When the
leftmost fragment(s) are too short/symbol-heavy to pass the paragraph-line
usability bar (`_is_usable_paragraph_line`), they are silently dropped before
paragraph grouping ever sees them -- leaving the surviving fragment to start
partway across the row, at whatever x-position the equation/subscript
happened to end. Grouping and indent measurement then read that position as
a real first-line indent, when it is really just where the dropped prefix
stopped. Depending on where in the paragraph this happens, this either (a)
produces a bogus large "indent" on a genuine continuation line (Muyeed,
Philip), or (b) orphans the true continuation as an unlinked one-line
"paragraph" (silently dropped, since paragraphs need >=2 lines), making the
next genuinely flush-left continuation line look like a brand new,
unindented paragraph (Youra).

Each fixture below is synthetic (no real dissertation content), built with
direct PdfDocument/PdfPage/PdfTextBlock/PdfTextLine/PdfTextSpan construction
(matching the technique already used in test_p015_body_indent_ester_split.py)
for exact control over the row-split geometry, paired with a positive
control proving the corresponding genuine violation is still detected.
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
    _merge_same_row_fragments,
    check_pdf_indentation,
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


# ---------------------------------------------------------------------------
# Root cause: a same-row fragment too short to pass usability is silently
# dropped, leaving a same-row remnant to be misread as a paragraph boundary.
# ---------------------------------------------------------------------------


def test_youra_style_dropped_prefix_orphan_not_flagged_missing_indent() -> None:
    """A short trailing word ends one sentence, and a new sentence -- still
    the same paragraph -- shares its row. The dropped short fragment must not
    orphan the new-sentence fragment, which would otherwise make the next
    flush continuation line look like an unindented new paragraph."""
    para = [
        _line(
            "Synthetic sentence establishing this test paragraph's content here.",
            x0=137.0,
            y0=80.0,
            y1=92.0,
        ),
        _line("responses.", x0=108.0, x1=155.0, y0=104.0, y1=116.0),
        _line(
            "However, despite these theoretical expectations for this test,",
            x0=214.0,
            y0=104.0,
            y1=116.0,
        ),
        _line(_CONT, x0=108.0, y0=128.0, y1=140.0),
        _line(_CONT, x0=108.0, y0=152.0, y1=164.0),
        _line(_CONT, x0=108.0, y0=176.0, y1=188.0),
    ]
    doc = _doc(_page(30, _block(*para)))
    findings = [f for f in check_pdf_indentation(doc) if f.rule_id == "P015"]
    assert not findings


def test_muyeed_style_subscript_overlap_prose_not_flagged() -> None:
    """A subscript-affected fragment ends one row (short, dropped), and the
    row below starts the continuation partway across (mid-row remnant). The
    continuation must not be read as a newly, wrongly indented line."""
    para = [
        _line(
            "Synthetic sentence establishing this test paragraph's content here.",
            x0=137.0,
            y0=80.0,
            y1=92.0,
        ),
        _line(_CONT, x0=108.0, y0=104.0, y1=116.0),
        # Short subscript-affected remnant, dropped by the usability filter.
        _line("index,andZi", x0=108.0, x1=179.0, y0=128.0, y1=141.0),
        # The surviving fragment starts mid-row where the remnant left off.
        _line(
            "one is the output of the model for this synthetic test case.",
            x0=176.0,
            y0=129.0,
            y1=144.0,
        ),
        _line(_CONT, x0=108.0, y0=152.0, y1=164.0),
        _line(_CONT, x0=108.0, y0=176.0, y1=188.0),
    ]
    doc = _doc(_page(31, _block(*para)))
    findings = [f for f in check_pdf_indentation(doc) if f.rule_id == "P015"]
    assert not findings


def test_philip_style_equation_prefix_continuation_not_flagged() -> None:
    """A short prefix before a displayed-equation-style row, plus a tiny
    intervening symbol fragment at a slightly different y0/y1 (as a
    subscript/exponent glyph would produce), must not leave the ", where ..."
    continuation reading as an indented new paragraph."""
    para = [
        _line(
            "Synthetic sentence establishing this test paragraph's content here.",
            x0=137.0,
            y0=80.0,
            y1=92.0,
        ),
        _line(_CONT, x0=108.0, y0=104.0, y1=116.0),
        # Symbol-only equation glyph remnant, dropped by the usability filter.
        _line("\x00", x0=160.0, x1=166.0, y0=127.5, y1=139.5),
        # Short prefix remnant, dropped by the usability filter.
        _line("of order O", x0=108.0, x1=160.0, y0=129.0, y1=141.0),
        _line(
            ", where the parameter is defined for this synthetic test case.",
            x0=190.0,
            y0=129.0,
            y1=141.0,
        ),
        _line(_CONT, x0=108.0, y0=152.0, y1=164.0),
        _line(_CONT, x0=108.0, y0=176.0, y1=188.0),
    ]
    doc = _doc(_page(32, _block(*para)))
    findings = [f for f in check_pdf_indentation(doc) if f.rule_id == "P015"]
    assert not findings


# ---------------------------------------------------------------------------
# Positive controls: genuine violations of each kind must still be detected,
# including in the presence of an unrelated short/dropped fragment elsewhere.
# ---------------------------------------------------------------------------


def test_missing_later_indent_still_flagged_with_unrelated_dropped_fragment() -> None:
    """A genuinely unindented later paragraph must still be flagged even when
    an unrelated too-short fragment (e.g. a stray page artifact) sits nearby
    but does not actually precede any usable line on its own row."""
    para1 = [
        _line(
            "Indented synthetic paragraph opener for this fixture case.", x0=144.0, y0=80.0, y1=92.0
        ),
        *[
            _line(
                "Continuation line of the correctly indented first paragraph.",
                x0=108.0,
                y0=y,
                y1=y + 12,
            )
            for y in (94.0, 108.0, 122.0)
        ],
    ]
    para2 = [
        _line(
            "Second indented synthetic paragraph opener for this fixture.",
            x0=144.0,
            y0=150.0,
            y1=162.0,
        ),
        *[
            _line(
                "Continuation line of the correctly indented second paragraph.",
                x0=108.0,
                y0=y,
                y1=y + 12,
            )
            for y in (164.0, 178.0, 192.0)
        ],
    ]
    # Unrelated short fragment far from any usable row-mate: must not be
    # absorbed into anything (no usable line shares its row).
    stray = _line("(1)", x0=500.0, x1=520.0, y0=206.0, y1=218.0)
    para3 = [
        _line(
            "Flush-left synthetic paragraph missing its expected indent.", x0=108.0, y0=y, y1=y + 12
        )
        for y in (230.0, 244.0, 258.0, 272.0)
    ]
    doc = _doc(_page(33, _block(*para1, *para2, stray, *para3)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015" and f.details.get("issue_type") == "missing_later_indent"
    ]
    assert findings


def test_unexpected_indent_on_continuation_line_still_flagged_without_remnant() -> None:
    """A genuinely mis-indented continuation line (no row-split involved at
    all) must still be flagged -- the fix targets the extraction artifact,
    not continuation-line detection generally."""
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
    para = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=130.0,
            y1=142.0,
        ),
        _line(_CONT, x0=108.0, y0=144.0, y1=156.0),
        _line(_CONT, x0=108.0, y0=158.0, y1=170.0),
    ]
    doc = _doc(_page(34, _block(*opening_para), _block(*para)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert len(findings) == 1


def test_real_new_paragraph_after_period_still_gets_expected_indent_check() -> None:
    """A short trailing word ends one paragraph, and a genuinely NEW,
    correctly-indented paragraph starts on the very next row (not sharing a
    row with anything) -- ordinary layout, not a row split. It must be
    evaluated as its own paragraph like any other, with no residual
    absorption from the unrelated short line above it."""
    para1 = [
        _line(
            "Synthetic sentence establishing this test paragraph's content here.",
            x0=137.0,
            y0=80.0,
            y1=92.0,
        ),
        _line("concludes.", x0=108.0, x1=160.0, y0=104.0, y1=116.0),
    ]
    para2 = [
        _line(
            "A brand new, correctly indented paragraph starts here for this test.",
            x0=144.0,
            y0=128.0,
            y1=140.0,
        ),
        _line(_CONT, x0=108.0, y0=152.0, y1=164.0),
        _line(_CONT, x0=108.0, y0=176.0, y1=188.0),
    ]
    doc = _doc(_page(35, _block(*para1, *para2)))
    findings = [f for f in check_pdf_indentation(doc) if f.rule_id == "P015"]
    assert not findings


# ---------------------------------------------------------------------------
# Boundary: a split section-number heading ("2.4.3" + title) must not be
# absorbed by the new row-remnant logic -- that pattern already has its own
# dedicated handling (_find_split_heading_following_paragraph_indices).
# ---------------------------------------------------------------------------


def test_split_section_number_heading_not_absorbed_as_row_remnant() -> None:
    para1 = [
        _line(
            "Indented synthetic paragraph opener for this fixture case.", x0=144.0, y0=80.0, y1=92.0
        ),
        *[
            _line(
                "Continuation line of the correctly indented first paragraph.",
                x0=108.0,
                y0=y,
                y1=y + 12,
            )
            for y in (94.0, 108.0, 122.0)
        ],
    ]
    heading_number = _line("2.4.3", x0=108.0, x1=136.0, y0=146.0, y1=158.0)
    heading_title = _line("Synthetic Section Title", x0=149.0, x1=300.0, y0=146.0, y1=158.0)
    para2 = [
        _line(
            "Indented synthetic paragraph opener for this fixture case.",
            x0=144.0,
            y0=170.0,
            y1=182.0,
        ),
        *[
            _line(
                "Continuation line of the correctly indented second paragraph.",
                x0=108.0,
                y0=y,
                y1=y + 12,
            )
            for y in (184.0, 198.0, 212.0)
        ],
    ]
    doc = _doc(_page(36, _block(*para1, heading_number, heading_title, *para2)))
    findings = [f for f in check_pdf_indentation(doc) if f.rule_id == "P015"]
    assert not findings


# ---------------------------------------------------------------------------
# Direct unit coverage for the new geometry helpers.
# ---------------------------------------------------------------------------


def test_effective_row_start_x_absorbs_short_prefix_with_subscript_offset_y() -> None:
    """A short remnant with a slightly different y0/y1 (as a subscript would
    produce) is still absorbed via vertical-overlap, not exact baseline
    match."""
    remnant = _line("index,andZi", x0=108.36, x1=179.33, y0=286.72, y1=299.90)
    usable = _line(
        "one is the output of the model for this synthetic test case.",
        x0=175.59,
        x1=540.40,
        y0=287.94,
        y1=303.01,
    )
    raw_lines = [remnant, usable]
    assert _effective_row_start_x(raw_lines, 1) == remnant.bbox.x0


def test_effective_row_start_x_ignores_bare_section_number() -> None:
    number = _line("2.4.3", x0=108.0, x1=136.0, y0=407.4, y1=419.4)
    title = _line("Synthetic Section Title", x0=149.5, x1=300.0, y0=407.4, y1=419.4)
    raw_lines = [number, title]
    assert _effective_row_start_x(raw_lines, 1) == title.bbox.x0


def test_merge_same_row_fragments_tolerates_subscript_overlap_and_y_shift() -> None:
    """Two independently-usable fragments with a few points of overlap and a
    slightly shifted y0/y1 (a subscript kerning/box artifact) must still
    merge when their touching spans share style."""
    span_a = _span("logit Zi", font="CMMI8", x0=108.36, x1=291.50, y0=262.81, y1=275.99)
    span_b = _span("out for the sample", font="CMMI8", x0=287.75, x1=540.36, y0=264.03, y1=278.94)
    line_a = _line("logit Zi", spans=[span_a], x0=108.36, x1=291.50, y0=262.81, y1=275.99)
    line_b = _line("out for the sample", spans=[span_b], x0=287.75, x1=540.36, y0=264.03, y1=278.94)

    merged = _merge_same_row_fragments([line_a, line_b])

    assert len(merged) == 1
    assert merged[0].bbox.x0 == 108.36


def test_merge_same_row_fragments_still_keeps_run_in_heading_separate_with_y_shift() -> None:
    """The bold-run-in-heading guard must hold even when the new
    overlap-fraction fallback would otherwise consider the rows close enough
    -- style mismatch alone must still block the merge."""
    heading_span = _span(
        "Synthetic Bold Heading.", bold=True, font="CMBX12", x0=108.0, x1=306.0, y0=322.5, y1=334.4
    )
    body_span = _span(
        "The synthetic body continuation begins",
        font="CMR12",
        x0=317.6,
        x1=547.6,
        y0=323.7,
        y1=335.6,
    )
    line_a = _line(
        "Synthetic Bold Heading.", spans=[heading_span], x0=108.0, x1=306.0, y0=322.5, y1=334.4
    )
    line_b = _line(
        "The synthetic body continuation begins",
        spans=[body_span],
        x0=317.6,
        x1=547.6,
        y0=323.7,
        y1=335.6,
    )

    merged = _merge_same_row_fragments([line_a, line_b])
    assert len(merged) == 2
