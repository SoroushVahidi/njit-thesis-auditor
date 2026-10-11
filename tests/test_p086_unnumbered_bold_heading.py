"""Synthetic regression coverage for P086 (unnumbered bold heading-shaped phrase).

See docs/status/p086_unnumbered_bold_heading_design_20260922.md for the
design-gate discussion and docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md
("Separate Bold-Heading Observation") for the underlying Ester-adjudicated
case this rule tracks. All fixtures here are synthetic/generic -- no
dissertation prose, author names, or physical-page-specific hardcoding.
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
from njit_auditor.rules.pdf_unnumbered_bold_heading import check_pdf_unnumbered_bold_heading


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
        text=text, font=font, size=size, bold=bold, italic=False,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
    )


def _line(
    text: str,
    *,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
    spans: list[PdfTextSpan] | None = None,
) -> PdfTextLine:
    line_spans = spans or [_span(text, x0=x0, x1=x1, y0=y0, y1=y1)]
    return PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1), spans=line_spans)


def _bold_line(text: str, *, x0: float, x1: float, y0: float, y1: float) -> PdfTextLine:
    span = _span(text, bold=True, font="CMBX12", x0=x0, x1=x1, y0=y0, y1=y1)
    return _line(text, spans=[span], x0=x0, x1=x1, y0=y0, y1=y1)


def _regular_line(text: str, *, x0: float, x1: float, y0: float, y1: float) -> PdfTextLine:
    span = _span(text, bold=False, font="CMR12", x0=x0, x1=x1, y0=y0, y1=y1)
    return _line(text, spans=[span], x0=x0, x1=x1, y0=y0, y1=y1)


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


_CONT = "Continuation synthetic paragraph line text used for grouping only here."


def _run_in_row(
    bold_text: str, regular_text: str, *, y0: float, y1: float, bold_x1: float = 280.0
) -> tuple[PdfTextLine, PdfTextLine]:
    """A bold lead sharing a physical row with regular continuation text --
    the exact structural shape this rule fires on."""
    lead = _bold_line(bold_text, x0=108.0, x1=bold_x1, y0=y0, y1=y1)
    tail = _regular_line(regular_text, x0=bold_x1 + 12.0, x1=540.0, y0=y0, y1=y1)
    return lead, tail


def _following_body(y_start: float) -> list[PdfTextLine]:
    return [_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (y_start, y_start + 14, y_start + 28)]


def _issue_types(findings) -> list[str]:
    return [f.details.get("issue_type") for f in findings if f.rule_id == "P086"]


# 1. Numbered legitimate bold heading (run-in shaped) -- no finding: it already
#    carries a section number, matching P027's own numbered patterns.
def test_numbered_bold_run_in_heading_no_finding() -> None:
    lead, tail = _run_in_row(
        "2.1 Overview Of The Synthetic Approach", "and its supporting context begins here",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(10, _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 2. Standalone heading-like bold run-in phrase, no section number -- finding.
#    This is the exact Youra-style shape Ester adjudicated.
def test_unnumbered_bold_run_in_heading_reports_finding() -> None:
    lead, tail = _run_in_row(
        "Synthetic Comparison Discussion Heading", "continues in regular style on the same row",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(12, _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == ["bold_heading_without_section_number"]
    assert findings[0].page == 12
    assert findings[0].details["bbox"] == "108.0,220.0,280.0,232.0"


def test_run_in_heading_with_wider_word_spacing_remains_connected() -> None:
    lead = _bold_line(
        "Synthetic Comparison Discussion Heading", x0=108.0, x1=327.9, y0=220.0, y1=232.0
    )
    tail = _regular_line(
        "continues in regular style on the same row", x0=345.2, x1=540.0, y0=220.0, y1=232.0
    )
    doc = _doc(_page(12, _block(lead, tail, *_following_body(244.0))))
    assert _issue_types(check_pdf_unnumbered_bold_heading(doc)) == [
        "bold_heading_without_section_number"
    ]


def test_regular_sentence_with_bold_math_symbol_is_not_run_in_heading() -> None:
    lead = _line(
        "Given a synthetic direction vector v",
        x0=108.0, x1=280.0, y0=220.0, y1=232.0,
        spans=[
            _span("Given a synthetic direction vector ", x0=108.0, x1=270.0,
                  y0=220.0, y1=232.0),
            _span("v", bold=True, font="CMBX12", x0=270.0, x1=280.0,
                  y0=220.0, y1=232.0),
        ],
    )
    tail = _regular_line(
        "the ordinary sentence continues here", x0=292.0, x1=540.0,
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(12, _block(lead, tail, *_following_body(244.0))))
    assert _issue_types(check_pdf_unnumbered_bold_heading(doc)) == []


# 3. Known legitimate front-matter bold heading (e.g. ABSTRACT) -- no finding:
#    the whole page is skipped, same as P027's own named-heading page gate.
def test_frontmatter_named_heading_page_no_finding() -> None:
    heading = _bold_line("ABSTRACT", x0=250.0, x1=340.0, y0=90.0, y1=104.0)
    lead, tail = _run_in_row(
        "Synthetic Comparison Discussion Heading", "continues in regular style on the same row",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(3, _block(heading), _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 4. LoF/LoT page -- no finding: the whole page is skipped, same as P027's
#    own TOC/List-of-... named-heading page gate.
def test_list_of_figures_page_no_finding() -> None:
    heading = _bold_line("LIST OF FIGURES", x0=220.0, x1=380.0, y0=90.0, y1=104.0)
    lead, tail = _run_in_row(
        "Synthetic Comparison Discussion Heading", "continues in regular style on the same row",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(7, _block(heading), _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 5. Figure/table caption label where the "Figure N." prefix is bold -- no
#    finding: caption-shaped lines are excluded from paragraph grouping
#    entirely (CAPTION_PREFIX_RE), so they never reach this check at all.
def test_bold_figure_caption_prefix_no_finding() -> None:
    lead, tail = _run_in_row(
        "Figure 4.2.", "Synthetic caption description text for a generic plot",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(20, _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 6. Ambiguous inline bold emphasis mid-sentence (not a same-row style-
#    transition split, just a bold span inside an otherwise ordinary line
#    followed by an ordinary next line) -- abstain, no finding.
def test_inline_bold_emphasis_not_run_in_shape_no_finding() -> None:
    mixed_line = _line(
        "Regular text with an emphasized phrase mid sentence continues here",
        spans=[
            _span("Regular text with an ", bold=False, x0=108.0, x1=220.0, y0=220.0, y1=232.0),
            _span("emphasized phrase", bold=True, x0=220.0, x1=300.0, y0=220.0, y1=232.0),
            _span(
                " mid sentence continues here",
                bold=False, x0=300.0, x1=460.0, y0=220.0, y1=232.0,
            ),
        ],
        x0=108.0, x1=460.0, y0=220.0, y1=232.0,
    )
    next_row = _line(_CONT, x0=108.0, y0=234.0, y1=246.0)
    doc = _doc(_page(25, _block(mixed_line, next_row, *_following_body(248.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 7. Ordinary non-bold body text -- no finding.
def test_plain_body_text_no_finding() -> None:
    lines = [_line(_CONT, x0=108.0, y0=y, y1=y + 12) for y in (220.0, 234.0, 248.0)]
    doc = _doc(_page(30, _block(*lines)))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 9. Numbered heading whose number is glued to the title with no whitespace
#    at all ("1.4.1.3Atypical...") -- a real PDF text-extraction artifact
#    found on the corpus. Still recognized as numbered -- no finding.
def test_numbered_heading_no_space_extraction_artifact_no_finding() -> None:
    lead, tail = _run_in_row(
        "1.4.1.3Atypical Geographical Distribution", "continues in regular style on the same row",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(40, _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 10. Numbered heading with a trailing period glued before the space
#     ("3.2.4.4. Title") -- a real PDF text-extraction shape found on the
#     corpus. Still recognized as numbered -- no finding.
def test_numbered_heading_trailing_period_no_finding() -> None:
    lead, tail = _run_in_row(
        "3.2.4.4. Online Microdroplet Digestion", "continues in regular style on the same row",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(41, _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 11. Bulleted definition-list term glued with no whitespace after the
#     bullet ("•RobustCovariance...") -- a real PDF text-extraction
#     artifact found on the corpus. Still recognized as a bullet item, not
#     an unnumbered heading -- no finding.
def test_bullet_item_no_space_extraction_artifact_no_finding() -> None:
    lead, tail = _run_in_row(
        "•Robust Covariance Estimator", "the fraction of features each estimator explores",
        y0=220.0, y1=232.0,
    )
    doc = _doc(_page(42, _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 12. A numbered heading whose bare section number extracted as a separate
#     same-row fragment to the left of the bold title (a real PDF
#     text-extraction shape found on the corpus) -- still recognized as
#     numbered via the same-row bare-number check -- no finding.
def test_split_same_row_bare_number_no_finding() -> None:
    number_only = _bold_line("2.1.3.2", x0=108.0, x1=140.0, y0=220.0, y1=232.0)
    lead = _bold_line("Nondeterministic Algorithms", x0=144.0, x1=280.0, y0=220.0, y1=232.0)
    tail = _regular_line(
        "continues in regular style on the same row", x0=292.0, x1=540.0, y0=220.0, y1=232.0
    )
    doc = _doc(_page(43, _block(number_only, lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []


# 8. Short bold call-out label (e.g. "Note:") sharing a row with regular text
#    -- no finding: fails the same "looks like a real heading title, not a
#    short label" qualifying filter P027 already uses (_is_qualified_heading).
def test_short_bold_label_lead_in_no_finding() -> None:
    lead, tail = _run_in_row(
        "Note:", "a short call-out label, not a heading-shaped phrase",
        y0=220.0, y1=232.0, bold_x1=150.0,
    )
    doc = _doc(_page(33, _block(lead, tail, *_following_body(244.0))))
    findings = check_pdf_unnumbered_bold_heading(doc)
    assert _issue_types(findings) == []
