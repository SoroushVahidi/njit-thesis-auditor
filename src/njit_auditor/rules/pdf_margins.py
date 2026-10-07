"""Heuristic margin checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p011_margin_presentation import (
    infer_margin_content_kind,
    infer_page_margin_context,
    margin_side_label,
    margin_suggested_fix,
    page_has_numbered_reference_entries,
)
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE, _is_top_or_bottom_zone

INCH_TO_PT = 72.0
LEFT_MARGIN_PT = 1.5 * INCH_TO_PT
RIGHT_MARGIN_PT = 1.0 * INCH_TO_PT
TOP_MARGIN_PT = 1.0 * INCH_TO_PT
BOTTOM_MARGIN_PT = 1.0 * INCH_TO_PT
MIN_ARTIFACT_SIZE_PT = 2.0
OVERFLOW_TOLERANCE_PT = 3.0
# Numeric-stability guard only: PDF/PyMuPDF coordinates can land a few
# thousandths of a point above the nominal tolerance (e.g. 3.00006pt) while the
# displayed overflow rounds to 3.0pt and the rendered ink remains in-bounds.
# This does not widen NJIT policy tolerance; it makes the existing 3.0pt cutoff
# behave consistently at floating-point precision boundaries.
OVERFLOW_TOLERANCE_EPSILON_PT = 0.01

# Bottom-margin-specific overflow tolerance (replaces OVERFLOW_TOLERANCE_PT for
# the bottom side only). A fully justified body line that lands last on an
# otherwise full page routinely has its own descent/leading dip a few extra
# points past the nominal 1-inch line -- normal single-line typographic slack,
# not content placed outside the margin. Esther originally confirmed four
# such single/short-line bottom-margin findings -- both Word and LaTeX source
# PDFs, both prose and equation lines -- as false positives at 3.9-8.2pt
# overflow, and the tolerance was set just above that (9.0pt), deliberately
# stopping short of a recurring ~9.2pt footer-zone cluster that a prior audit
# (docs/status/p011_precision_false_negative_audit_20260710.md, S7
# "Uncertain cases") flagged as an open policy question.
#
# Esther has since reviewed that cluster directly (Muyeed physical PDF page
# 36, "clustering algorithm.", MEDIUM confidence, measured 9.17pt raw / 9.2pt
# displayed overflow) via the R011-R015 follow-up sheet and confirmed it is
# NOT a violation -- see
# docs/evaluation/ester_feedback/next_targeted_followup_after_r011_r015_20260825.md.
# Re-auditing the full 8-12pt bottom-margin population across all seven
# private evaluation dissertations (see
# docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md) shows
# this is not an isolated point: raw overflow of ~9.17pt recurs 47 times
# across two independent LaTeX-source dissertations (Muyeed, Philip) on
# prose, equations, table-of-contents dot-leaders, and reference URLs alike
# -- a content-independent geometric constant, not a real placement issue --
# and the population immediately above it (raw 9.05-9.29pt) is followed by a
# clean, empty gap (no findings from 9.30-9.43pt raw). This remains the base
# tolerance; separate structural checks below handle later adjudicated
# line-box cases without raising this threshold for all bottom content.
BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT = 9.3

# A line whose top is still inside the required margin can have a taller PDF
# line box than its visible glyphs. Ester rejected this ordinary final-line
# pattern in both LaTeX and Word documents. Keep the exception within one
# font em (and at most 12pt): text placed below the margin, or a deeper bleed,
# still warns.
BOTTOM_LINE_BOX_MAX_OVERFLOW_PT = 12.0
BOTTOM_LINE_BOX_MAX_TOP_OFFSET_PT = 0.5

# A LaTeX contents continuation can start at the lower end of Ester's stated
# 0.9-1.0 inch template range. Only a dot-leader row on an identified contents
# page gets the extra allowance; ordinary prose and reference entries do not.
CONTENTS_ROW_MAX_TOP_OFFSET_PT = 7.5
CONTENTS_ROW_MAX_OVERFLOW_PT = 20.0

# Ester rejected a final reference/DOI line on an identified references page
# whose top sits about 7pt below the margin and whose box ends about 23pt
# below it, still above the page number (2026-10-05). The allowance covers
# only that shape: the last text line of a single-spaced reference block on a
# confidently identified references page, with the page number below it.
# Prose, abstract, and contents pages get no such allowance.
REFERENCES_FINAL_LINE_MAX_TOP_OFFSET_PT = 7.5
REFERENCES_FINAL_LINE_MAX_OVERFLOW_PT = 24.0
# The final line must continue the block at single spacing: its step from the
# line above stays within this range of multiples of the font size.
REFERENCES_FINAL_LINE_MIN_STEP_EM = 0.8
REFERENCES_FINAL_LINE_MAX_STEP_EM = 1.6
_REFERENCES_HEADING_KEYS = frozenset({"REFERENCES", "BIBLIOGRAPHY"})

# Extra right/left-margin overflow tolerance for reference-list entries only
# (added on top of OVERFLOW_TOLERANCE_PT). Bibliography/reference entries
# often contain an unbreakable long citation title, DOI, or foreign-language
# phrase that cannot wrap without altering the citation; Esther confirmed a
# references-list right-margin finding (~6.9pt) as a false positive for
# exactly this reason. Bounded rather than unlimited so a genuinely oversized
# reference-block margin problem -- e.g. the ~24pt hanging-indent left-margin
# violations covered by
# test_numbered_reference_left_margin_overflow_stays_high_confidence_with_correct_wording --
# still gets flagged.
REFERENCES_MARGIN_EXTRA_TOLERANCE_PT = 6.0
# Patrick's same-shape right-margin reference entry reaches 10.2pt, while
# Ester explicitly confirmed a separate 18.0pt entry is a real violation.
# Leave the left-margin hanging-indent allowance unchanged.
REFERENCES_RIGHT_MARGIN_EXTRA_TOLERANCE_PT = 7.25

# Outdented reference-number labels. Ester: "there are never problems with
# the left margins in latex" and, for template-produced LaTeX margin
# behavior, "I do not ask students to make this correction". She reviewed
# numbered bibliographies whose "[n]" labels hang left of the 1.5 in edge
# (entry text starting at it) in several LaTeX dissertations without flagging
# the labels, while still flagging text that crossed a margin. So on a
# references page, a right-aligned column of standalone "[n]" label spans is
# measured by where each entry's text starts, not by the label. The entry
# text itself stays fully constrained. Derived application, not a direct
# ruling: docs/status/r011_outdented_reference_labels_20261006.md.
_REFERENCE_LABEL_SPAN_RE = re.compile(r"^\[\d{1,3}\]$")
REFERENCE_LABEL_COLUMN_ALIGN_PT = 1.5
REFERENCE_LABEL_COLUMN_MIN_ENTRIES = 2

# Standard space-glyph advance width as a fraction of font size (~0.25em is a
# near-universal convention across text fonts), used only to correct a
# text-extraction artifact -- see _content_right_edge below.
_SPACE_ADVANCE_EM_FRACTION = 0.25

# Artifact guard: a page/side group with this many lines all below this overflow
# is likely caused by a compressed-PDF coordinate shift rather than a real margin violation.
ARTIFACT_GUARD_MIN_COUNT = 5
ARTIFACT_GUARD_MAX_OVERFLOW_PT = 8.0

# Half-thickness of the drawn margin-boundary guide rectangle. Presentation-only:
# does not affect detection, thresholds, or confidence -- purely how wide the
# guide line is once rendered in the highlighted PDF.
MARGIN_GUIDE_HALF_THICKNESS_PT = 1.5

# Presentation-only minimum width/height for visible overflow aids. Thin actual
# overflow slices are widened only for display, while the raw overflow segment
# geometry stays unchanged in the serialized finding details.
MIN_VISIBLE_OVERFLOW_DIMENSION_PT = 4.0

# Two violating lines on the same side are grouped into one tight highlight
# region only when no other line (violating or not) separates them in the
# page's top-to-bottom reading order. This is presentation-only: it decides
# how many highlight boxes are drawn for an already-decided finding, never
# whether a violation is flagged.
_ADJACENT_LINE_INDEX_GAP = 1


class MarginSide(str, Enum):
    LEFT = "left_margin"
    RIGHT = "right_margin"
    TOP = "top_margin"
    BOTTOM = "bottom_margin"


# NJIT's margins belong to the bound, portrait sheet ("1.5 in left, 1 in right,
# top, and bottom" throughout), and its guideline keeps page numbers in portrait
# when a table or figure is set in landscape. A landscape page is therefore
# the same portrait sheet turned sideways: the 1.5 in binding margin lies
# along one of its long edges, never its left edge. Same aspect threshold as
# ``pdf_layout._is_visually_landscape``.
LANDSCAPE_ASPECT_THRESHOLD = 1.02
_VERTICAL_DIR_MIN_COMPONENT = 0.9


@dataclass(frozen=True)
class MarginFrame:
    """Allowed text area in the page's text coordinate space.

    PyMuPDF reports text boxes in the *unrotated* page space even when the page
    carries ``/Rotate``, so the frame is built from the unrotated size, not the
    displayed ``page.width``/``page.height``.
    """

    allowed_x0: float
    allowed_y0: float
    allowed_x1: float
    allowed_y1: float
    text_space_height: float
    # "portrait", or for a landscape sheet the edge holding the binding margin:
    # "top", "bottom", or "undetermined".
    binding_edge: str = "left"
    # Edge band(s) where the sheet's portrait page number sits; numeric-only
    # lines there are page numbers, exactly like the portrait top/bottom zones.
    page_number_bands: tuple[BBox, ...] = ()

    @property
    def is_landscape_sheet(self) -> bool:
        return self.binding_edge != "left"

    @property
    def last_line_bottom_allowances_apply(self) -> bool:
        """Whether the text-space bottom edge gets the bottom-only allowances.

        BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT, the final-line box exception and
        the references final-line allowance come from Ester's verdicts on the
        last line of a page's text flow dipping into an ordinary 1-inch
        bottom margin ("Bottom ~0.9" to 1"" for LaTeX, Word cases too). They
        follow the text flow's end (the text-space bottom), but never relax the
        1.5-inch binding margin, which keeps the ordinary tolerance on every
        sheet: a sheet turned counter-clockwise puts its binding edge at the
        bottom.
        """
        return self.binding_edge != "bottom"


def _text_space_size(page: PdfPage) -> tuple[float, float]:
    if page.page_rotation % 180 == 90:
        return page.height, page.width
    return page.width, page.height


def _portrait_page_number_direction(page: PdfPage) -> int | None:
    """+1 / -1 when every vertical page-number-like line runs down / up.

    A portrait-orientation page number on a sideways sheet is the one reliable
    marker of which long edge is the binding edge; anything else (none found,
    or conflicting directions) is reported as undetermined.
    """
    signs: set[int] = set()
    for block in page.text_blocks:
        for line in block.lines:
            if line.line_dir is None or not PAGE_NUM_RE.match(line.text.strip()):
                continue
            dx, dy = line.line_dir
            is_vertical = abs(dy) >= _VERTICAL_DIR_MIN_COMPONENT
            if is_vertical and abs(dx) < 1.0 - _VERTICAL_DIR_MIN_COMPONENT:
                signs.add(1 if dy > 0 else -1)
    return signs.pop() if len(signs) == 1 else None


def _margin_frame(page: PdfPage) -> MarginFrame:
    width, height = _text_space_size(page)
    if width <= height * LANDSCAPE_ASPECT_THRESHOLD:
        return MarginFrame(
            allowed_x0=LEFT_MARGIN_PT,
            allowed_y0=TOP_MARGIN_PT,
            allowed_x1=width - RIGHT_MARGIN_PT,
            allowed_y1=height - BOTTOM_MARGIN_PT,
            text_space_height=height,
        )
    left_band = BBox(x0=0.0, y0=0.0, x1=BOTTOM_MARGIN_PT, y1=height)
    right_band = BBox(x0=width - BOTTOM_MARGIN_PT, y0=0.0, x1=width, y1=height)
    direction = _portrait_page_number_direction(page)
    if direction == 1:
        # Portrait text runs down the page: the sheet was turned clockwise, so
        # portrait left (binding) is the top edge, portrait bottom the left edge,
        # portrait right the bottom edge and portrait top the right edge.
        return MarginFrame(
            allowed_x0=BOTTOM_MARGIN_PT,
            allowed_y0=LEFT_MARGIN_PT,
            allowed_x1=width - TOP_MARGIN_PT,
            allowed_y1=height - RIGHT_MARGIN_PT,
            text_space_height=height,
            binding_edge="top",
            page_number_bands=(left_band,),
        )
    if direction == -1:
        # Turned counter-clockwise: binding at the bottom, portrait bottom on the right.
        return MarginFrame(
            allowed_x0=TOP_MARGIN_PT,
            allowed_y0=RIGHT_MARGIN_PT,
            allowed_x1=width - BOTTOM_MARGIN_PT,
            allowed_y1=height - LEFT_MARGIN_PT,
            text_space_height=height,
            binding_edge="bottom",
            page_number_bands=(right_band,),
        )
    # Binding edge unknown (top or bottom): report only what violates the
    # sheet under both possibilities, i.e. the 1 in margin on every edge.
    return MarginFrame(
        allowed_x0=TOP_MARGIN_PT,
        allowed_y0=TOP_MARGIN_PT,
        allowed_x1=width - TOP_MARGIN_PT,
        allowed_y1=height - TOP_MARGIN_PT,
        text_space_height=height,
        binding_edge="undetermined",
        page_number_bands=(left_band, right_band),
    )


def _in_page_number_band(text: str, bbox: BBox, bands: tuple[BBox, ...]) -> bool:
    if not bands or not PAGE_NUM_RE.match(text.strip()):
        return False
    return any(
        bbox.x0 >= band.x0 and bbox.x1 <= band.x1 and bbox.y0 >= band.y0 and bbox.y1 <= band.y1
        for band in bands
    )


@dataclass
class LineViolation:
    side: MarginSide
    overflow_pt: float
    line: PdfTextLine
    line_index: int


def _page_text(page: PdfPage) -> str:
    return " ".join(block.text for block in page.text_blocks)


def _likely_page_number_text(text: str, y0: float, y1: float, page_height: float) -> bool:
    return _is_top_or_bottom_zone(y0, y1, page_height) and bool(PAGE_NUM_RE.match(text.strip()))


def _content_right_edge(line: PdfTextLine) -> float:
    """Return the line's right edge with a trailing whitespace glyph trimmed off.

    PyMuPDF's line bbox is the union of its spans' boxes, and a span's box
    extends to the full advance width of its last character -- including a
    trailing space that fully justified text commonly ends a line with. That
    space carries no visible ink, so leaving it in inflates the measured right
    edge by roughly one space-glyph width (~0.25em) with nothing actually
    crossing the margin. This walks spans from the end, skipping any that are
    pure whitespace, and trims the trailing whitespace characters off the last
    span that has real content -- so it only ever narrows the measured edge,
    never widens it.
    """
    for span in reversed(line.spans):
        if not span.text.strip():
            continue
        stripped = span.text.rstrip(" \t")
        trailing_ws = len(span.text) - len(stripped)
        if trailing_ws and span.size:
            return span.bbox.x1 - trailing_ws * span.size * _SPACE_ADVANCE_EM_FRACTION
        return span.bbox.x1
    return line.bbox.x1


def _is_contents_page(page: PdfPage) -> bool:
    return any(
        "TABLEOFCONTENTS" in "".join(char for char in line.text.upper() if char.isalpha())
        for block in page.text_blocks
        for line in block.lines
        if line.bbox.y0 < 150.0
    )


def _is_confident_references_page(page: PdfPage) -> bool:
    """A REFERENCES/BIBLIOGRAPHY heading or a numbered reference list.

    Stricter than the wording-level page context, which accepts the word
    "references" anywhere in the page text.
    """
    for block in page.text_blocks:
        for line in block.lines:
            text = line.text.strip()
            if any(char.isdigit() for char in text):
                continue
            letters = "".join(char for char in text.upper() if char.isalpha())
            if letters.removesuffix("CONTINUED") in _REFERENCES_HEADING_KEYS:
                return True
    return page_has_numbered_reference_entries(_page_text(page))


def _outdented_label_split(line: PdfTextLine) -> tuple[float, float] | None:
    """(label right edge, entry-text left edge) for a line that opens with a
    standalone "[n]" label span followed by separate entry text, else None."""
    spans = [span for span in line.spans if span.text.strip()]
    if len(spans) < 2 or not _REFERENCE_LABEL_SPAN_RE.match(spans[0].text.strip()):
        return None
    label_x1 = spans[0].bbox.x1
    text_x0 = spans[1].bbox.x0
    if text_x0 < label_x1:
        return None
    return label_x1, text_x0


def _reference_label_column_x1(
    page: PdfPage, page_lines: list[PdfTextLine], *, contents_page: bool
) -> float | None:
    """Right edge of a right-aligned "[n]" label column on a references page.

    None unless the page is a confident references page (not a contents page)
    with at least two such labels whose right edges line up.
    """
    if contents_page or not _is_confident_references_page(page):
        return None
    label_x1s = sorted(
        split[0] for line in page_lines if (split := _outdented_label_split(line)) is not None
    )
    if len(label_x1s) < REFERENCE_LABEL_COLUMN_MIN_ENTRIES:
        return None
    column_x1 = label_x1s[len(label_x1s) // 2]
    aligned = [x1 for x1 in label_x1s if abs(x1 - column_x1) <= REFERENCE_LABEL_COLUMN_ALIGN_PT]
    if len(aligned) < REFERENCE_LABEL_COLUMN_MIN_ENTRIES:
        return None
    return column_x1


_REFERENCE_LINE_LABEL_RE = re.compile(r"^\[(\d{1,3})\]")
# A heading that starts a new section ends a references continuation.
_SECTION_BREAK_PREFIXES = ("CHAPTER", "APPENDIX")
_SECTION_BREAK_KEYS = frozenset({"VITA", "BIOGRAPHICALSKETCH"}) | _REFERENCES_HEADING_KEYS


@dataclass(frozen=True)
class _ReferenceColumn:
    """A page's reference-label column: label right edge, entry-text left
    edge, and the last "[n]" number on the page."""

    label_x1: float
    text_x0: float
    last_label: int | None


def _line_label_numbers(page_lines: list[PdfTextLine]) -> list[int]:
    return [
        int(match.group(1))
        for line in page_lines
        if (match := _REFERENCE_LINE_LABEL_RE.match(line.text.strip()))
    ]


def _has_section_break_heading(page_lines: list[PdfTextLine]) -> bool:
    for line in page_lines:
        letters = "".join(char for char in line.text.upper() if char.isalpha())
        if not letters or _REFERENCE_LINE_LABEL_RE.match(line.text.strip()):
            continue
        if letters.startswith(_SECTION_BREAK_PREFIXES) or (
            not any(char.isdigit() for char in line.text)
            and letters.removesuffix("CONTINUED") in _SECTION_BREAK_KEYS
        ):
            return True
    return False


def _continued_reference_column(
    previous: _ReferenceColumn, page_lines: list[PdfTextLine]
) -> _ReferenceColumn | None:
    """The previous page's label column, carried onto a page that continues the
    same numbered reference list across the page break, else None.

    Requires every structural signal at once: each outdented label on this
    page sits in the previous page's label column with its entry text at the
    previous page's text edge; the page's "[n]" numbers continue the previous
    page's sequence without a gap or restart; and no new section heading
    appears. Geometry alone, or a single bracketed number, never qualifies.
    """
    splits = [split for line in page_lines if (split := _outdented_label_split(line)) is not None]
    if not splits or previous.last_label is None:
        return None
    if any(
        abs(label_x1 - previous.label_x1) > REFERENCE_LABEL_COLUMN_ALIGN_PT
        or abs(text_x0 - previous.text_x0) > REFERENCE_LABEL_COLUMN_ALIGN_PT
        for label_x1, text_x0 in splits
    ):
        return None
    numbers = _line_label_numbers(page_lines)
    expected = list(range(previous.last_label + 1, previous.last_label + 1 + len(numbers)))
    if numbers != expected or _has_section_break_heading(page_lines):
        return None
    return _ReferenceColumn(previous.label_x1, previous.text_x0, numbers[-1])


def _reference_label_columns(pdf_doc: PdfDocument) -> dict[int, float]:
    """Reference-label column right edge per page number, in document order.

    A page establishes its own column (``_reference_label_column_x1``) or, when
    it cannot (e.g. a final page holding a single entry), continues the column
    of the immediately preceding page under ``_continued_reference_column``.
    Any page that does neither ends the chain. Landscape sheets and contents
    pages never carry a column.
    """
    columns: dict[int, float] = {}
    previous: _ReferenceColumn | None = None
    for page in pdf_doc.pages:
        current: _ReferenceColumn | None = None
        page_lines = [line for block in page.text_blocks for line in block.lines]
        contents_page = _is_contents_page(page)
        if not contents_page and not _margin_frame(page).is_landscape_sheet:
            own_x1 = _reference_label_column_x1(page, page_lines, contents_page=contents_page)
            if own_x1 is not None:
                text_x0s = sorted(
                    split[1]
                    for line in page_lines
                    if (split := _outdented_label_split(line)) is not None
                    and abs(split[0] - own_x1) <= REFERENCE_LABEL_COLUMN_ALIGN_PT
                )
                numbers = _line_label_numbers(page_lines)
                current = _ReferenceColumn(
                    own_x1, text_x0s[len(text_x0s) // 2], numbers[-1] if numbers else None
                )
            elif previous is not None:
                current = _continued_reference_column(previous, page_lines)
        if current is not None:
            columns[page.page_number] = current.label_x1
        previous = current
    return columns


def _left_edge_excluding_reference_label(
    line: PdfTextLine, reference_label_column_x1: float | None
) -> float:
    """The line's left edge, measured from its entry text when it opens with a
    label belonging to the page's reference-label column."""
    if reference_label_column_x1 is None:
        return line.bbox.x0
    split = _outdented_label_split(line)
    if split is None or abs(split[0] - reference_label_column_x1) > REFERENCE_LABEL_COLUMN_ALIGN_PT:
        return line.bbox.x0
    return split[1]


def _is_references_final_line_allowance(
    page: PdfPage,
    page_lines: list[PdfTextLine],
    line: PdfTextLine,
    allowed_y1: float,
    overflow: float,
    *,
    contents_page: bool,
) -> bool:
    """Ester's 2026-10-05 references-page final-line false positive shape."""
    if contents_page or not _is_confident_references_page(page):
        return False
    if line.bbox.y0 - allowed_y1 > REFERENCES_FINAL_LINE_MAX_TOP_OFFSET_PT:
        return False
    if overflow > REFERENCES_FINAL_LINE_MAX_OVERFLOW_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
        return False

    page_numbers = [
        other
        for other in page_lines
        if _likely_page_number_text(
            other.text, other.bbox.y0, other.bbox.y1, _text_space_size(page)[1]
        )
    ]
    text_lines = [other for other in page_lines if other.text.strip() and other not in page_numbers]
    # The line is the last text on the page ...
    if any(other.bbox.y0 > line.bbox.y0 + 1.0 for other in text_lines):
        return False
    # ... and sits above the page number rather than running into the footer.
    line_middle = (line.bbox.y0 + line.bbox.y1) / 2.0
    if not any(
        number.bbox.y0 > line.bbox.y0 and line_middle < number.bbox.y0 for number in page_numbers
    ):
        return False

    font_size = max((span.size or 0.0 for span in line.spans), default=0.0) or line.bbox.height
    min_step = REFERENCES_FINAL_LINE_MIN_STEP_EM * font_size
    max_step = REFERENCES_FINAL_LINE_MAX_STEP_EM * font_size
    return any(
        min_step <= line.bbox.y0 - other.bbox.y0 <= max_step
        and min(line.bbox.x1, other.bbox.x1) > max(line.bbox.x0, other.bbox.x0)
        for other in text_lines
        if other is not line
    )


def _is_bottom_math_fragment(
    line: PdfTextLine, page_lines: list[PdfTextLine], allowed_y1: float
) -> bool:
    """Recognize a small subscript split off an otherwise in-bounds equation."""
    if line.bbox.height > 8.0 or not line.spans:
        return False
    if any(not span.size or span.size > 8.0 for span in line.spans):
        return False
    for other in page_lines:
        if other is line or other.bbox.y0 > allowed_y1 + BOTTOM_LINE_BOX_MAX_TOP_OFFSET_PT:
            continue
        if (
            min(line.bbox.x1, other.bbox.x1) - max(line.bbox.x0, other.bbox.x0) >= 1.0
            and min(line.bbox.y1, other.bbox.y1) - max(line.bbox.y0, other.bbox.y0) >= 1.0
        ):
            return True
    return False


def _is_ester_rejected_bottom_line_box(
    line: PdfTextLine,
    page_lines: list[PdfTextLine],
    allowed_y1: float,
    overflow: float,
    *,
    contents_page: bool,
) -> bool:
    largest_font = max((span.size or 0.0 for span in line.spans), default=0.0)
    line_box_limit = min(BOTTOM_LINE_BOX_MAX_OVERFLOW_PT, largest_font + 0.25)
    if (
        line.bbox.y0 <= allowed_y1 + BOTTOM_LINE_BOX_MAX_TOP_OFFSET_PT
        and overflow <= line_box_limit + OVERFLOW_TOLERANCE_EPSILON_PT
    ):
        return True
    if overflow <= BOTTOM_LINE_BOX_MAX_OVERFLOW_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
        return _is_bottom_math_fragment(line, page_lines, allowed_y1)
    return (
        contents_page
        and line.text.count(".") >= 4
        and line.bbox.y0 <= allowed_y1 + CONTENTS_ROW_MAX_TOP_OFFSET_PT
        and overflow <= CONTENTS_ROW_MAX_OVERFLOW_PT + OVERFLOW_TOLERANCE_EPSILON_PT
    )


def _line_violation(
    line: PdfTextLine,
    page_height: float,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
    line_index: int,
    *,
    page_lines: list[PdfTextLine] | None = None,
    contents_page: bool = False,
    page_number_bands: tuple[BBox, ...] = (),
    reference_label_column_x1: float | None = None,
    last_line_bottom_allowances: bool = True,
) -> LineViolation | None:
    text = line.text.strip()
    if not text:
        return None
    bbox: BBox = line.bbox
    if bbox.width < MIN_ARTIFACT_SIZE_PT or bbox.height < MIN_ARTIFACT_SIZE_PT:
        return None
    if _likely_page_number_text(text, bbox.y0, bbox.y1, page_height):
        return None
    if _in_page_number_band(text, bbox, page_number_bands):
        return None

    content_x1 = min(bbox.x1, _content_right_edge(line))

    overflow_by_side: dict[MarginSide, float] = {}
    left_edge = _left_edge_excluding_reference_label(line, reference_label_column_x1)
    if left_edge < allowed_x0:
        raw = allowed_x0 - left_edge
        if raw > OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
            overflow_by_side[MarginSide.LEFT] = raw
    if content_x1 > allowed_x1:
        raw = content_x1 - allowed_x1
        if raw > OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
            overflow_by_side[MarginSide.RIGHT] = raw
    if bbox.y0 < allowed_y0:
        raw = allowed_y0 - bbox.y0
        if raw > OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
            overflow_by_side[MarginSide.TOP] = raw
    if bbox.y1 > allowed_y1:
        raw = bbox.y1 - allowed_y1
        if not last_line_bottom_allowances:
            if raw > OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
                overflow_by_side[MarginSide.BOTTOM] = raw
        elif (
            raw > BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT
            and not _is_ester_rejected_bottom_line_box(
                line, page_lines or [], allowed_y1, raw, contents_page=contents_page
            )
        ):
            overflow_by_side[MarginSide.BOTTOM] = raw

    if not overflow_by_side:
        return None
    side, overflow = max(overflow_by_side.items(), key=lambda item: item[1])
    return LineViolation(side=side, overflow_pt=overflow, line=line, line_index=line_index)


def _group_confidence(worst_overflow_pt: float, count: int) -> str:
    large_count_ok = (
        count >= ARTIFACT_GUARD_MIN_COUNT and worst_overflow_pt >= ARTIFACT_GUARD_MAX_OVERFLOW_PT
    )
    if worst_overflow_pt >= 12.0 or large_count_ok:
        return "high"
    if worst_overflow_pt >= 5.0 or count >= 2:
        return "medium"
    return "low"


def _union_bbox_of(violations: list[LineViolation]) -> BBox:
    return BBox(
        x0=min(v.line.bbox.x0 for v in violations),
        y0=min(v.line.bbox.y0 for v in violations),
        x1=max(v.line.bbox.x1 for v in violations),
        y1=max(v.line.bbox.y1 for v in violations),
    )


def _group_adjacent_violations(violations: list[LineViolation]) -> list[list[LineViolation]]:
    """Split same-side violations into tight groups with no line between them.

    Presentation-only: groups violating lines for highlight geometry so a
    highlighted PDF shows tight boxes around each cluster of affected lines
    instead of one region spanning unrelated content between separated
    violations. Two violations land in the same group only when their
    position in the page's top-to-bottom line order is consecutive (no other
    line -- violating or not -- separates them); this never changes which
    lines are flagged, only how many highlight boxes are drawn for them.
    """
    ordered = sorted(violations, key=lambda v: v.line_index)
    groups: list[list[LineViolation]] = []
    for violation in ordered:
        if groups and violation.line_index - groups[-1][-1].line_index <= _ADJACENT_LINE_INDEX_GAP:
            groups[-1].append(violation)
        else:
            groups.append([violation])
    return groups


def _margin_boundary_guide_bbox(
    side: MarginSide,
    violations: list[LineViolation],
    *,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
) -> BBox:
    """Return a thin rectangle marking the required margin boundary line.

    Spans only the vertical (for left/right) or horizontal (for top/bottom)
    extent of the affected lines, not the full page, so the guide stays
    contextual to the violation instead of drawing a page-length line.
    """
    thickness = MARGIN_GUIDE_HALF_THICKNESS_PT
    if side in (MarginSide.LEFT, MarginSide.RIGHT):
        y0 = min(v.line.bbox.y0 for v in violations)
        y1 = max(v.line.bbox.y1 for v in violations)
        boundary_x = allowed_x0 if side is MarginSide.LEFT else allowed_x1
        return BBox(x0=boundary_x - thickness, y0=y0, x1=boundary_x + thickness, y1=y1)
    x0 = min(v.line.bbox.x0 for v in violations)
    x1 = max(v.line.bbox.x1 for v in violations)
    boundary_y = allowed_y0 if side is MarginSide.TOP else allowed_y1
    return BBox(x0=x0, y0=boundary_y - thickness, x1=x1, y1=boundary_y + thickness)


def _overflow_segment_bbox(
    side: MarginSide,
    group: list[LineViolation],
    *,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
) -> BBox:
    """Return the sub-rectangle of *group*'s union box that actually crosses
    the margin boundary -- presentation-only geometry derived from the same
    line boxes and boundary already used for detection, never a new measure
    of overflow. Used to render the crossing segment distinctly from the
    rest of the (in-bounds) line in the highlighted PDF.
    """
    full = _union_bbox_of(group)
    if side is MarginSide.RIGHT:
        return BBox(x0=max(full.x0, allowed_x1), y0=full.y0, x1=full.x1, y1=full.y1)
    if side is MarginSide.LEFT:
        return BBox(x0=full.x0, y0=full.y0, x1=min(full.x1, allowed_x0), y1=full.y1)
    if side is MarginSide.BOTTOM:
        return BBox(x0=full.x0, y0=max(full.y0, allowed_y1), x1=full.x1, y1=full.y1)
    return BBox(x0=full.x0, y0=full.y0, x1=full.x1, y1=min(full.y1, allowed_y0))


def _overflow_display_bbox(
    side: MarginSide,
    group: list[LineViolation],
    *,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
) -> BBox:
    """Return a display-friendly version of the overflow slice.

    The underlying overflow segment geometry remains exact; this helper only
    widens very thin slices enough to stay visible in the highlighted PDF.
    """
    segment = _overflow_segment_bbox(
        side,
        group,
        allowed_x0=allowed_x0,
        allowed_y0=allowed_y0,
        allowed_x1=allowed_x1,
        allowed_y1=allowed_y1,
    )
    full = _union_bbox_of(group)
    if side in (MarginSide.LEFT, MarginSide.RIGHT):
        width = segment.width
        if width >= MIN_VISIBLE_OVERFLOW_DIMENSION_PT:
            return segment
        target = min(MIN_VISIBLE_OVERFLOW_DIMENSION_PT, full.width)
        center = (segment.x0 + segment.x1) / 2
        x0 = max(full.x0, center - target / 2)
        x1 = min(full.x1, x0 + target)
        if x1 - x0 < target:
            x0 = max(full.x0, x1 - target)
        return BBox(x0=x0, y0=segment.y0, x1=x1, y1=segment.y1)
    height = segment.height
    if height >= MIN_VISIBLE_OVERFLOW_DIMENSION_PT:
        return segment
    target = min(MIN_VISIBLE_OVERFLOW_DIMENSION_PT, full.height)
    center = (segment.y0 + segment.y1) / 2
    y0 = max(full.y0, center - target / 2)
    y1 = min(full.y1, y0 + target)
    if y1 - y0 < target:
        y0 = max(full.y0, y1 - target)
    return BBox(x0=segment.x0, y0=y0, x1=segment.x1, y1=y1)


def run_pdf_margin_rule(
    pdf_doc: PdfDocument,
    *,
    skip_pages: set[int] | None = None,
) -> list[AuditFinding]:
    """Detect possible text lines outside expected margin rectangle."""

    findings: list[AuditFinding] = []
    skipped = skip_pages or set()
    reference_label_columns = _reference_label_columns(pdf_doc)
    for page in pdf_doc.pages:
        if page.page_number in skipped:
            continue
        frame = _margin_frame(page)
        allowed_x0 = frame.allowed_x0
        allowed_y0 = frame.allowed_y0
        allowed_x1 = frame.allowed_x1
        allowed_y1 = frame.allowed_y1
        page_lines = [line for block in page.text_blocks for line in block.lines]
        contents_page = _is_contents_page(page)
        # Landscape sheets keep the plain measurement: the authority concerns
        # the portrait left (binding) margin.
        reference_label_column_x1 = reference_label_columns.get(page.page_number)

        grouped: dict[MarginSide, list[LineViolation]] = {}
        line_index = 0
        for line in page_lines:
            violation = _line_violation(
                line,
                frame.text_space_height,
                allowed_x0,
                allowed_y0,
                allowed_x1,
                allowed_y1,
                line_index,
                page_lines=page_lines,
                contents_page=contents_page,
                page_number_bands=frame.page_number_bands,
                reference_label_column_x1=reference_label_column_x1,
                last_line_bottom_allowances=frame.last_line_bottom_allowances_apply,
            )
            line_index += 1
            if not violation:
                continue
            grouped.setdefault(violation.side, []).append(violation)

        for side, violations in grouped.items():
            worst_violation = max(violations, key=lambda v: v.overflow_pt)
            worst = worst_violation.overflow_pt
            count = len(violations)
            # Suppress groups where many lines all barely cross the margin: this pattern
            # indicates a compressed-PDF coordinate shift, not a real margin violation.
            if count >= ARTIFACT_GUARD_MIN_COUNT and worst < ARTIFACT_GUARD_MAX_OVERFLOW_PT:
                continue

            # Collect truncated text previews of all violating lines for student-facing
            # wording, and classify the page/content up front: both the references
            # exception right below and the finding's remediation wording later need
            # the same classification, computed once from the same evidence.
            _MAX_PREVIEW_LEN = 60
            _MAX_PREVIEW_LINES = 5
            line_previews: list[str] = []
            for v in violations[:_MAX_PREVIEW_LINES]:
                txt = v.line.text.strip()
                if txt:
                    line_previews.append(
                        (txt[:_MAX_PREVIEW_LEN] + "…") if len(txt) > _MAX_PREVIEW_LEN else txt
                    )
            page_context = infer_page_margin_context(_page_text(page), line_previews)
            content_kind = infer_margin_content_kind(page_context, line_previews)

            # Reference-list entries often contain an unbreakable long citation
            # title, DOI, or foreign-language phrase that cannot wrap without
            # altering the citation; Esther confirmed a references-list
            # right-margin finding as a false positive for exactly this reason.
            # Bounded (not unlimited) so a genuinely oversized reference-block
            # margin problem -- e.g. the much larger hanging-indent left-margin
            # violations -- still gets flagged.
            if (
                side is MarginSide.BOTTOM
                and count == 1
                and frame.last_line_bottom_allowances_apply
                and _is_references_final_line_allowance(
                    page,
                    page_lines,
                    worst_violation.line,
                    allowed_y1,
                    worst,
                    contents_page=contents_page,
                )
            ):
                continue

            if (
                side in (MarginSide.LEFT, MarginSide.RIGHT)
                and content_kind == "references_hanging_indent"
                and worst
                <= OVERFLOW_TOLERANCE_PT
                + (
                    REFERENCES_RIGHT_MARGIN_EXTRA_TOLERANCE_PT
                    if side is MarginSide.RIGHT
                    else REFERENCES_MARGIN_EXTRA_TOLERANCE_PT
                )
                + OVERFLOW_TOLERANCE_EPSILON_PT
            ):
                continue

            confidence = _group_confidence(worst, count)
            # A "low" confidence group is, by construction, a single line whose
            # measured overflow is under the 5pt medium-confidence floor -- text
            # extraction/font-metric rounding noise rather than a real margin
            # violation. Ester's Sample B review confirmed exactly this pattern
            # (single-line, sub-5pt right-margin "overflow") as false positives
            # on several pages while every reviewed medium/high-confidence
            # finding was a real violation. See
            # docs/status/ester_sample_b_p011_margin_low_overflow.md.
            if confidence == "low":
                continue

            # `bbox` stays the union of every violating line's box, unchanged, for
            # backward compatibility with any consumer reading a single box (e.g.
            # the has_highlight availability check). It does not add a new box
            # concept on its own (see docs/status/highlight_quality_improvement_plan.md)
            # and every other field below (worst_overflow_pt, affected_line_count,
            # confidence, side) still reflects the single worst offender exactly
            # as before.
            highlight_bbox = _union_bbox_of(violations)

            # Precise per-region highlight boxes: violating lines are grouped so
            # that only lines with nothing (violating or not) between them share
            # one tight box, instead of one region spanning unrelated content
            # between separated violations.
            adjacent_groups = _group_adjacent_violations(violations)
            highlight_bboxes = [_union_bbox_of(group) for group in adjacent_groups]

            # For each same group, the sub-rectangle that actually crosses the
            # margin boundary -- lets the highlighted PDF draw the crossing
            # segment more strongly than the rest of the (in-bounds) line,
            # instead of highlighting the whole line uniformly.
            overflow_segment_bboxes = [
                _overflow_segment_bbox(
                    side,
                    group,
                    allowed_x0=allowed_x0,
                    allowed_y0=allowed_y0,
                    allowed_x1=allowed_x1,
                    allowed_y1=allowed_y1,
                )
                for group in adjacent_groups
            ]
            overflow_display_bboxes = [
                _overflow_display_bbox(
                    side,
                    group,
                    allowed_x0=allowed_x0,
                    allowed_y0=allowed_y0,
                    allowed_x1=allowed_x1,
                    allowed_y1=allowed_y1,
                )
                for group in adjacent_groups
            ]

            # A thin guide rectangle marking the exact required margin boundary
            # line the content must not cross, scoped to the affected region's
            # extent rather than spanning the full page.
            margin_boundary_bbox = _margin_boundary_guide_bbox(
                side,
                violations,
                allowed_x0=allowed_x0,
                allowed_y0=allowed_y0,
                allowed_x1=allowed_x1,
                allowed_y1=allowed_y1,
            )

            # Tiny, single-line overflows are more likely measurement noise (font
            # metric rounding, a stray descender) than a real violation. This is
            # already reflected in `confidence` ("low"); `triage_tier` stays a
            # constant "informational" for all P011 findings because it is part
            # of build_grouped_findings()'s grouping key (report_outputs.py) —
            # varying it by confidence would split identical margin problems
            # across separate cards purely because occurrences differed in
            # measured overflow.
            finding_details: dict[str, str] = {
                "side": side.value,
                "issue_type": "margin_boundary_violation",
                "worst_overflow_pt": f"{worst:.1f}",
                "affected_line_count": str(count),
                "confidence": confidence,
                "triage_tier": "informational",
                "bbox": format_bbox_detail(highlight_bbox),
                "highlight_bboxes": " | ".join(
                    format_bbox_detail(box) for box in highlight_bboxes
                ),
                "overflow_display_bboxes": " | ".join(
                    format_bbox_detail(box) for box in overflow_display_bboxes
                ),
                "overflow_segment_bboxes": " | ".join(
                    format_bbox_detail(box) for box in overflow_segment_bboxes
                ),
                "margin_boundary_bbox": format_bbox_detail(margin_boundary_bbox),
            }
            if line_previews:
                finding_details["affected_line_texts"] = " | ".join(line_previews)

            finding_details["page_context"] = page_context
            finding_details["margin_content_kind"] = content_kind
            if frame.is_landscape_sheet:
                finding_details["page_orientation"] = "landscape"
                finding_details["binding_edge"] = frame.binding_edge
            finding_details["suggested_fix"] = margin_suggested_fix(
                page_context=page_context,
                content_kind=content_kind,
                side_label=margin_side_label(finding_details),
                details=finding_details,
            )

            findings.append(
                AuditFinding(
                    rule_id="P011",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        f"Possible text crossing {side.value} by approximately "
                        f"{worst:.1f} pt."
                    ),
                    details=finding_details,
                )
            )

    if findings:
        return findings
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.PASS,
            message="No obvious margin-boundary text violations detected.",
        )
    ]
