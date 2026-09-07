"""Heuristic paragraph indentation checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_headings import EXPECTED_HEADINGS, normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

EXPECTED_NORMAL_INDENT_PT = 36.0
INDENT_TOLERANCE_PT = 8.0
STRONG_INDENT_THRESHOLD_PT = 18.0
MIN_TEXT_LEN = 20
MAX_PARAGRAPH_GAP_PT = 14.0
X_GROUP_TOLERANCE_PT = 24.0
FIRST_LINE_INDENT_GROUP_TOLERANCE_PT = 96.0
MAX_LINE_X_SPREAD_PT = 110.0
MAX_FINDINGS_PER_PAGE_ISSUE = 1
NEGATIVE_INDENT_IGNORE_PT = -8.0
MIN_LINES_FOR_MISSING_LATER_INDENT = 4
MIN_LIKELY_INDENTED_PARAGRAPHS_FOR_PAGE_STYLE = 2
MIN_INDENT_STYLE_CONFIDENCE_RATIO = 0.6
SAME_ROW_Y_TOLERANCE_PT = 1.0
# A subscript/superscript glyph immediately preceding a same-baseline split
# can carry a few points of negative kerning into the fragment that follows
# it (e.g. a subscript "i" whose box extends slightly past where the next
# word's box begins) even though the two fragments are genuinely two pieces
# of one row. _merge_same_row_fragments tolerates that much overlap; anything
# more is treated as two visually distinct, non-adjacent elements.
SAME_ROW_OVERLAP_ALLOWANCE_PT = 8.0

# A row split by an inline displayed equation, subscript, or superscript need
# not land its fragments at nearly-identical y0/y1 the way a plain same-baseline
# text split does (SAME_ROW_Y_TOLERANCE_PT) -- a subscript/superscript glyph
# commonly shifts a fragment's bounding box by several points. Vertical extent
# overlap is a more robust "same visual row" signal for that case: this is the
# minimum fraction of the shorter fragment's own height that must be covered by
# the other fragment's vertical extent.
SAME_ROW_OVERLAP_FRACTION = 0.5
# Sanity bound only, not a reverse-fit tolerance: a discarded same-row remnant
# more than this far from the surviving fragment it would be absorbed into is
# treated as unrelated content rather than a truncated prefix of one sentence.
MAX_ROW_REMNANT_ABSORPTION_GAP_PT = 200.0

TOC_LIKE_HEADINGS = {
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
}
REFERENCES_LIKE_HEADINGS = {
    "REFERENCES",
    "BIBLIOGRAPHY",
    "WORKS CITED",
}

CAPTION_PREFIX_RE = re.compile(r"^(figure|table)\s+[\divxlcdm]+[.:)]?\s+", re.IGNORECASE)
BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s+")
_BODY_SECTION_HEADING_RE = re.compile(r"^\d+(?:\.\d+)+\s+\S")
_BODY_CHAPTER_HEADING_RE = re.compile(r"^(?:CHAPTER|APPENDIX)\s+[\dA-Z]")
_SECTION_NUMBER_ONLY_RE = re.compile(r"^\d+(?:\.\d+)+$")
_ALGORITHM_HEADING_RE = re.compile(r"^algorithm\s*\d*[:.]?", re.IGNORECASE)
_CODELIKE_CUE_RE = re.compile(r"(?:Input:|range\(|elseif|until|[{}<>])")


def first_text_x(line: PdfTextLine) -> float:
    """Return the first text x position for a line."""

    return line.bbox.x0


def _is_page_number_line(line: PdfTextLine) -> bool:
    clean = " ".join(line.text.strip().split())
    return bool(clean and PAGE_NUM_RE.match(clean))


def _is_named_heading_line(line: PdfTextLine) -> bool:
    normalized = normalize_heading_text(line.text)
    return normalized.upper() in EXPECTED_HEADINGS


def _is_usable_paragraph_line(line: PdfTextLine) -> bool:
    if _is_named_heading_line(line) or _is_page_number_line(line):
        return False
    clean = " ".join(line.text.strip().split())
    if len(clean) < MIN_TEXT_LEN:
        return False
    if BULLET_PREFIX_RE.match(clean):
        return False
    if CAPTION_PREFIX_RE.match(clean):
        return False
    alpha_count = sum(ch.isalpha() for ch in clean)
    if alpha_count < 10:
        return False
    if alpha_count / max(len(clean), 1) < 0.45:
        return False
    return True


def _is_short_extraction_remnant(line: PdfTextLine) -> bool:
    """True for a fragment that fails the paragraph-line usability bar only
    for being short or symbol-heavy -- a subscript, a stray equation glyph,
    or a sentence prefix truncated by an inline displayed equation -- as
    opposed to being excluded for being a heading, page number, bullet, or
    caption. Those are legitimate distinct exclusions that the row-remnant
    absorption below (`_effective_row_start_x`) must never eat.
    """
    if _is_named_heading_line(line) or _is_page_number_line(line):
        return False
    clean = " ".join(line.text.strip().split())
    if not clean:
        return False
    if BULLET_PREFIX_RE.match(clean) or CAPTION_PREFIX_RE.match(clean):
        return False
    # A bare section number ("2.4.3") split from its title text onto a
    # separate fragment is a distinct, already-handled structural marker
    # (see _find_split_heading_following_paragraph_indices), not a discarded
    # sentence prefix -- absorbing its x0 into the title text would corrupt
    # that heading detection instead of fixing a sentence-continuation split.
    if _SECTION_NUMBER_ONLY_RE.match(clean):
        return False
    return not _is_usable_paragraph_line(line)


def _vertical_overlap_fraction(a: PdfTextLine, b: PdfTextLine) -> float:
    top = max(a.bbox.y0, b.bbox.y0)
    bottom = min(a.bbox.y1, b.bbox.y1)
    overlap = max(0.0, bottom - top)
    shorter = min(a.bbox.y1 - a.bbox.y0, b.bbox.y1 - b.bbox.y0)
    if shorter <= 0:
        return 0.0
    return overlap / shorter


def _line_trailing_span_is_bold(line: PdfTextLine) -> bool:
    return bool(line.spans) and line.spans[-1].bold


def _is_run_in_heading_lead(candidate: PdfTextLine, following: PdfTextLine) -> bool:
    """True when *candidate* is a bold run-in heading sharing a physical row
    with *following*, regular-styled text (e.g. a LaTeX ``\\paragraph{...}``
    lead-in). ``_merge_same_row_fragments`` correctly refuses to merge these
    two into one text line (that would corrupt the heading's own text), but
    paragraph grouping still needs to know the row's true left edge belongs
    to the bold lead, not to wherever the regular continuation happens to
    start -- otherwise the continuation reads as an orphaned, flush-left
    paragraph start of its own. Requires the same same-row geometry as the
    merge check, but the *opposite* style outcome (a genuine style
    transition, not a same-style extraction split).
    """
    if not _line_trailing_span_is_bold(candidate):
        return False
    # A bare section number ("2.1.3.2") sharing a row with both its own
    # title and the title's run-in body text is also bold and to the title's
    # left -- but it is the distinct, already-handled split-heading marker
    # (see _find_split_heading_following_paragraph_indices), not itself the
    # heading's readable lead-in text. Treating it as the row's left anchor
    # would attribute the paragraph's indent to the section number's
    # position instead of the title's, the same trap
    # _is_short_extraction_remnant already guards against.
    candidate_clean = " ".join(candidate.text.strip().split())
    if _SECTION_NUMBER_ONLY_RE.match(candidate_clean):
        return False
    if _same_run_style(candidate, following):
        return False
    return _vertical_overlap_fraction(candidate, following) >= SAME_ROW_OVERLAP_FRACTION


# A row fragmented by an equation can land its pieces in a sort order that
# does not match strict left-to-right reading order: two fragments visually on
# the same row can carry slightly different y0 values (a subscript/superscript
# nudges its own bounding box), which can sort a leftmost fragment *after* the
# surviving usable one. _effective_row_start_x therefore searches a small
# window of neighboring raw-line entries on both sides rather than assuming
# same-row remnants are strictly, contiguously adjacent-before *index*.
_ROW_REMNANT_SEARCH_WINDOW = 8


def _effective_row_start_x(raw_lines: list[PdfTextLine], index: int) -> float:
    """Return the true visual left edge of a usable line's printed row.

    An inline displayed equation, subscript, or superscript can split one
    physical text row into several extraction fragments. When the leftmost
    fragment(s) are too short/symbol-heavy to be usable on their own, they
    are silently dropped before paragraph grouping ever sees them -- leaving
    the surviving fragment to start partway across the row, at whatever
    x-position the equation/subscript happened to end. Grouping and indent
    measurement then read that position as a real first-line indent, when it
    is really just where the dropped prefix stopped.

    This scans a bounded neighborhood of *raw_lines* (sorted by (y0, x0),
    unfiltered) around *index* for fragments that (a) fail usability only for
    being short/symbol-heavy, (b) substantially overlap this line's vertical
    extent, and (c) start to its left -- and returns the leftmost such x0. It
    never looks at or changes a fragment's text -- only which x0
    grouping/indent code sees for the surviving usable line.

    The same window also covers a second, distinct source case: a bold
    run-in heading sharing this line's row (see `_is_run_in_heading_lead`).
    That fragment is fully usable on its own (not a short/symbol-heavy
    remnant) but still marks the row's true visual left edge -- the
    following regular-styled text is a continuation of the same paragraph
    the run-in heading opens, not a fresh paragraph starting mid-row.
    """
    line = raw_lines[index]
    x0 = line.bbox.x0
    lo = max(0, index - _ROW_REMNANT_SEARCH_WINDOW)
    hi = min(len(raw_lines), index + _ROW_REMNANT_SEARCH_WINDOW + 1)
    for i in range(lo, hi):
        if i == index:
            continue
        candidate = raw_lines[i]
        if candidate.bbox.x0 >= x0:
            continue
        if _vertical_overlap_fraction(candidate, line) < SAME_ROW_OVERLAP_FRACTION:
            continue
        if _is_run_in_heading_lead(candidate, line):
            # A bold run-in heading's own text can span most of the column
            # width before the regular continuation starts -- unlike a
            # dropped subscript/equation remnant, this is not bounded by
            # MAX_ROW_REMNANT_ABSORPTION_GAP_PT (calibrated for short
            # discarded fragments, not a full heading phrase). Same-row
            # vertical overlap plus the bold-to-regular style transition is
            # itself the reliable signal here.
            x0 = candidate.bbox.x0
            continue
        if line.bbox.x0 - candidate.bbox.x0 > MAX_ROW_REMNANT_ABSORPTION_GAP_PT:
            continue
        if not _is_short_extraction_remnant(candidate):
            continue
        x0 = candidate.bbox.x0
    return x0


def _has_page_heading_in(page: PdfPage, headings: set[str]) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            normalized = normalize_heading_text(line.text).upper()
            if normalized in headings:
                return True
    return False


def _is_section_heading_line(line: PdfTextLine) -> bool:
    """Return True for section headings that reset first-paragraph indent expectations."""

    if _is_named_heading_line(line):
        return True
    clean = " ".join(line.text.strip().split())
    if not clean or len(clean) > 100:
        return False
    if clean.endswith((".", ",", ";")):
        return False
    return bool(_BODY_SECTION_HEADING_RE.match(clean) or _BODY_CHAPTER_HEADING_RE.match(clean))


def _paragraph_starts_with_run_in_heading(paragraph: list[PdfTextLine]) -> bool:
    """True when a paragraph's own first line is a bold run-in heading whose
    regular-styled continuation shares the same physical row (e.g. a LaTeX
    ``\\paragraph{...}`` lead-in immediately followed by body prose).

    Such a paragraph's real "first line", for indentation purposes, is the
    bold lead-in itself, and a flush-left bold lead-in is the *expected*
    style -- the same treatment already given to a paragraph that opens
    right after a genuine section heading (`_is_section_heading_line`). The
    row-remnant reconnection in `_effective_row_start_x` /
    `_is_run_in_heading_lead` is what lets the regular continuation and any
    later lines correctly join this same paragraph instead of the
    continuation being misread as an orphaned new paragraph start; this
    check is the matching indent-expectation half of that fix.
    """
    if len(paragraph) < 2:
        return False
    return _is_run_in_heading_lead(paragraph[0], paragraph[1])


def _find_heading_exempt_paragraph_indices(
    page: PdfPage, paragraphs: list[list[PdfTextLine]]
) -> frozenset[int]:
    """Return paragraph indices for opening paragraphs immediately after a heading."""

    exempt: set[int] = set()
    heading_spans: list[tuple[float, float]] = []
    for block in page.text_blocks:
        for line in block.lines:
            if _is_section_heading_line(line):
                heading_spans.append((line.bbox.y0, line.bbox.y1))

    for idx, paragraph in enumerate(paragraphs):
        if _is_section_heading_line(paragraph[0]) or _paragraph_starts_with_run_in_heading(
            paragraph
        ):
            exempt.add(idx)
            continue
        if idx == 0 or not heading_spans:
            continue
        prev_end_y = paragraphs[idx - 1][-1].bbox.y1
        this_start_y = paragraph[0].bbox.y0
        for hy0, hy1 in heading_spans:
            if hy0 >= prev_end_y - 4.0 and hy1 <= this_start_y + 4.0:
                exempt.add(idx)
                break

    return frozenset(exempt)


def _find_split_heading_following_paragraph_indices(
    page: PdfPage, paragraphs: list[list[PdfTextLine]]
) -> frozenset[int]:
    """Return paragraph indices that follow split numbered headings like '4.3' + title."""

    exempt: set[int] = set()
    heading_spans: list[tuple[float, float]] = []
    page_lines = sorted(
        (line for block in page.text_blocks for line in block.lines),
        key=lambda line: (line.bbox.y0, line.bbox.x0),
    )
    for index, line in enumerate(page_lines):
        clean = " ".join(line.text.strip().split())
        if not _SECTION_NUMBER_ONLY_RE.match(clean):
            continue
        next_line = page_lines[index + 1] if index + 1 < len(page_lines) else None
        if next_line is None:
            continue
        next_clean = " ".join(next_line.text.strip().split())
        if (
            next_clean
            and len(next_clean) <= 100
            and not next_clean.endswith((".", ",", ";"))
            and sum(ch.isalpha() for ch in next_clean) >= 4
        ):
            gap = next_line.bbox.y0 - line.bbox.y1
            if gap <= MAX_PARAGRAPH_GAP_PT:
                heading_spans.append((line.bbox.y0, max(line.bbox.y1, next_line.bbox.y1)))

    for idx, paragraph in enumerate(paragraphs):
        if idx == 0 or not heading_spans:
            continue
        prev_end_y = paragraphs[idx - 1][-1].bbox.y1
        this_start_y = paragraph[0].bbox.y0
        for hy0, hy1 in heading_spans:
            if hy0 >= prev_end_y - 4.0 and hy1 <= this_start_y + 4.0:
                exempt.add(idx)
                break

    return frozenset(exempt)


def _same_run_style(a: PdfTextLine, b: PdfTextLine) -> bool:
    """Return True when the touching ends of two fragments share one text run's style.

    Used to tell a pure extraction split (identical font/weight on both sides,
    e.g. mid-sentence) apart from a genuine run-in heading like a LaTeX
    ``\\paragraph{...}`` title (bold lead-in immediately followed by regular
    body text on the same baseline), which must not be merged.
    """
    if not a.spans or not b.spans:
        return False
    left = a.spans[-1]
    right = b.spans[0]
    return left.font == right.font and left.bold == right.bold and left.italic == right.italic


def _merge_same_row_fragments(lines: list[PdfTextLine]) -> list[PdfTextLine]:
    """Merge line fragments that text extraction split at an identical baseline.

    Some PDF producers emit one visual text row as two non-overlapping runs at
    the same y-coordinates (for example when a sentence spanning a mid-line
    boundary is extracted as separate "line" entries). Left alone, the trailing
    fragment reads as a short line ending a paragraph and the next real line is
    misread as a new paragraph's first line. Merging same-baseline, same-style
    fragments back into one line before paragraph grouping avoids that spurious
    break without touching genuine paragraph boundaries or run-in heading rows
    (bold lead-in + regular continuation).
    """
    merged: list[PdfTextLine] = []
    for line in lines:
        if merged:
            prev = merged[-1]
            same_baseline = (
                abs(line.bbox.y0 - prev.bbox.y0) <= SAME_ROW_Y_TOLERANCE_PT
                and abs(line.bbox.y1 - prev.bbox.y1) <= SAME_ROW_Y_TOLERANCE_PT
            )
            # A subscript/superscript glyph shifts its own fragment's bounding
            # box, so a row split next to one may miss the strict same-baseline
            # test above even though the two fragments are genuinely one row;
            # substantial vertical overlap is a looser but still reliable
            # fallback signal for that case.
            same_row_extent = same_baseline or (
                _vertical_overlap_fraction(prev, line) >= SAME_ROW_OVERLAP_FRACTION
            )
            same_row = (
                same_row_extent
                and line.bbox.x0 > prev.bbox.x1 - SAME_ROW_OVERLAP_ALLOWANCE_PT
                and _same_run_style(prev, line)
            )
            if same_row:
                merged[-1] = PdfTextLine(
                    spans=prev.spans + line.spans,
                    bbox=BBox(x0=prev.bbox.x0, y0=prev.bbox.y0, x1=line.bbox.x1, y1=prev.bbox.y1),
                    text=f"{prev.text} {line.text}".strip(),
                    line_dir=prev.line_dir,
                    wmode=prev.wmode,
                )
                continue
        merged.append(line)
    return merged


def group_lines_into_paragraphs(page: PdfPage) -> list[list[PdfTextLine]]:
    """Group nearby lines into paragraph candidates on a page."""

    if _has_page_heading_in(page, TOC_LIKE_HEADINGS):
        return []

    raw_lines: list[PdfTextLine] = [
        line for block in page.text_blocks for line in block.lines
    ]
    raw_lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))

    # A candidate row-remnant-corrected x0 per usable line, computed once from
    # the unfiltered raw layout. This is deliberately *not* applied here: a
    # candidate is only trusted in the main loop below, and only when it is
    # the difference between reconnecting to the paragraph directly above and
    # not -- never as an unconditional geometry rewrite. See the loop for why.
    candidate_x0: dict[tuple[float, float], float] = {}
    lines: list[PdfTextLine] = []
    for index, line in enumerate(raw_lines):
        if not _is_usable_paragraph_line(line):
            continue
        effective_x0 = _effective_row_start_x(raw_lines, index)
        if effective_x0 != line.bbox.x0:
            candidate_x0[(line.bbox.y0, line.bbox.x0)] = effective_x0
        lines.append(line)

    if not lines:
        return []

    lines = _merge_same_row_fragments(lines)

    paragraphs: list[list[PdfTextLine]] = []
    current: list[PdfTextLine] = []
    prev_line: PdfTextLine | None = None

    for line in lines:
        if prev_line is None:
            current = [line]
            prev_line = line
            continue

        vertical_gap = line.bbox.y0 - prev_line.bbox.y1
        allowed_x_delta = (
            FIRST_LINE_INDENT_GROUP_TOLERANCE_PT if len(current) == 1 else X_GROUP_TOLERANCE_PT
        )
        x_delta = abs(first_text_x(line) - first_text_x(prev_line))
        joins = vertical_gap <= MAX_PARAGRAPH_GAP_PT and x_delta <= allowed_x_delta

        # An inline displayed equation, subscript, or superscript can split
        # one physical text row so the surviving fragment starts partway
        # across it -- x_delta above then looks too large to continue the
        # paragraph even though it visually does. Retry with the row-remnant
        # candidate only as a way to *reconnect* a break the plain check just
        # found; if that candidate doesn't actually let this line join
        # anything, discard it and keep the line's true, uncorrected geometry
        # -- so an unrelated same-row coincidence (e.g. a run-in heading's
        # own wrapped continuation sitting beside a genuinely new paragraph)
        # never gets to silently zero out that paragraph's real indent.
        line_key = (line.bbox.y0, line.bbox.x0)
        if not joins and line_key in candidate_x0:
            corrected_x0 = candidate_x0[line_key]
            corrected_x_delta = abs(corrected_x0 - first_text_x(prev_line))
            if vertical_gap <= MAX_PARAGRAPH_GAP_PT and corrected_x_delta <= allowed_x_delta:
                line = PdfTextLine(
                    spans=line.spans,
                    bbox=BBox(x0=corrected_x0, y0=line.bbox.y0, x1=line.bbox.x1, y1=line.bbox.y1),
                    text=line.text,
                    line_dir=line.line_dir,
                    wmode=line.wmode,
                )
                joins = True

        if joins:
            current.append(line)
        else:
            if current:
                paragraphs.append(current)
            current = [line]

        prev_line = line

    if current:
        paragraphs.append(current)

    return [paragraph for paragraph in paragraphs if len(paragraph) >= 2]


def _paragraph_indent_pt(paragraph: list[PdfTextLine]) -> float:
    first_x = first_text_x(paragraph[0])
    rest_x = [first_text_x(line) for line in paragraph[1:]]
    median_rest_x = median(rest_x)
    return first_x - median_rest_x


# Headings whose pages are handled atomically by dedicated detectors.
# ABSTRACT → P044 covers Q002 and Q003.
# ACKNOWLEDGEMENTS → P043 covers Q044 and Q045.
_P015_EXCLUDED_HEADINGS: frozenset[str] = frozenset({"ABSTRACT", "ACKNOWLEDGEMENTS"})


def _find_excluded_page_numbers(pdf_document: PdfDocument) -> set[int]:
    """Return page numbers covered by P043/P044 that P015 should skip."""
    pages: set[int] = set()
    for page in pdf_document.pages:
        for block in page.text_blocks:
            for line in block.lines:
                normalized = normalize_heading_text(line.text).upper()
                if normalized in _P015_EXCLUDED_HEADINGS:
                    pages.add(page.page_number)
                    break
    return pages


def _paragraph_is_low_confidence(paragraph: list[PdfTextLine]) -> bool:
    if len(paragraph) < 3:
        return True
    x_values = [first_text_x(line) for line in paragraph]
    return (max(x_values) - min(x_values)) > MAX_LINE_X_SPREAD_PT


_FIRST_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*")


def _paragraph_starts_like_continuation(paragraph: list[PdfTextLine]) -> bool:
    first_line = " ".join(paragraph[0].text.strip().split())
    match = _FIRST_WORD_RE.search(first_line)
    if not match:
        return False
    word = match.group(0)
    if not word[0].islower():
        return False
    # A lowercase-led word with an internal uppercase letter (e.g. "pH",
    # "mRNA", "eBay", "iPhone") is a mixed-case scientific term, unit, or
    # proper noun -- these start genuine new sentences/paragraphs, not a
    # common all-lowercase connector word (e.g. "where", "which", "since")
    # that starts a continuation clause after a displayed equation. Exclude
    # them so a legitimate, correctly indented new paragraph is not mistaken
    # for a continuation line.
    if any(char.isupper() for char in word[1:]):
        return False
    return True


# A leading "(a)" or "[12]" marker means the lowercase letter inside the
# bracket is a list/citation marker, not the start of a continuation
# sentence -- exclude these from the continuation-indent check below so a
# genuinely new list item or citation-led sentence isn't mistaken for a
# stray "where ..."/"which ..." clause after a displayed equation.
_BRACKETED_LEAD_MARKER_RE = re.compile(r"^\s*[\(\[]")


def _paragraph_starts_like_bracketed_marker(paragraph: list[PdfTextLine]) -> bool:
    first_line = paragraph[0].text.strip()
    return bool(_BRACKETED_LEAD_MARKER_RE.match(first_line))


def _paragraph_is_algorithm_or_code_like(paragraph: list[PdfTextLine]) -> bool:
    line_texts = [" ".join(line.text.strip().split()) for line in paragraph]
    if not line_texts:
        return False
    if _ALGORITHM_HEADING_RE.match(line_texts[0]):
        return True
    cue_lines = sum(1 for text in line_texts if _CODELIKE_CUE_RE.search(text))
    return cue_lines >= 2


def _is_likely_expected_indent(indent_pt: float) -> bool:
    return abs(indent_pt - EXPECTED_NORMAL_INDENT_PT) <= INDENT_TOLERANCE_PT


def check_pdf_indentation(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P015 indentation warnings for body-text paragraph layout.

    Skips Abstract pages (Q002/Q003 handled atomically by P044) and Acknowledgements
    pages (Q044/Q045 handled atomically by P043).  P015A flags a first paragraph after
    a section heading that is indented; P015B flags later body paragraphs missing
    first-line indent when the page style supports indentation.
    """
    findings: list[AuditFinding] = []
    excluded_pages = _find_excluded_page_numbers(pdf_document)

    for page in pdf_document.pages:
        if page.page_number in excluded_pages:
            continue
        if _has_page_heading_in(page, REFERENCES_LIKE_HEADINGS):
            continue
        paragraphs = group_lines_into_paragraphs(page)
        if not paragraphs:
            continue

        heading_exempt = _find_heading_exempt_paragraph_indices(page, paragraphs)
        split_heading_exempt = _find_split_heading_following_paragraph_indices(page, paragraphs)

        paragraph_data: list[tuple[int, list[PdfTextLine], float]] = []
        for idx, paragraph in enumerate(paragraphs):
            if _paragraph_is_low_confidence(paragraph):
                continue
            paragraph_data.append((idx, paragraph, _paragraph_indent_pt(paragraph)))
        if not paragraph_data:
            continue

        likely_indented_count = 0
        likely_not_indented_count = 0
        for idx, paragraph, indent_pt in paragraph_data:
            if idx in heading_exempt:
                continue
            if idx in split_heading_exempt:
                continue
            if _paragraph_starts_like_continuation(paragraph):
                continue
            if _paragraph_is_algorithm_or_code_like(paragraph):
                continue
            if indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                likely_indented_count += 1
            elif (
                NEGATIVE_INDENT_IGNORE_PT <= indent_pt < STRONG_INDENT_THRESHOLD_PT
                and len(paragraph) >= MIN_LINES_FOR_MISSING_LATER_INDENT
            ):
                likely_not_indented_count += 1

        comparable_count = likely_indented_count + likely_not_indented_count
        page_has_high_confidence_indent_style = (
            likely_indented_count >= MIN_LIKELY_INDENTED_PARAGRAPHS_FOR_PAGE_STYLE
            and comparable_count > 0
            and (likely_indented_count / comparable_count) >= MIN_INDENT_STYLE_CONFIDENCE_RATIO
        )

        seen_indented_paragraph = False
        page_issue_findings: dict[str, AuditFinding] = {}
        for idx, paragraph, indent_pt in paragraph_data:
            if idx in heading_exempt and indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                current = AuditFinding(
                    rule_id="P015",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "First paragraph after a heading appears indented but should be flush-left."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "unexpected_opening_indent",
                        "indent_pt": f"{indent_pt:.1f}",
                        "expected": "flush_left_opening_paragraph",
                        "paragraph_line_count": str(len(paragraph)),
                        "paragraph_index": str(idx + 1),
                        "bbox": format_bbox_detail(paragraph[0].bbox),
                        "confidence": "high",
                        "suggested_fix": (
                            "Remove the first-line indent from the first paragraph "
                            "after the heading."
                        ),
                    },
                )
                page_issue_findings["unexpected_opening_indent"] = current

            if (
                idx not in heading_exempt
                and idx not in split_heading_exempt
                and _paragraph_starts_like_continuation(paragraph)
                and not _paragraph_starts_like_bracketed_marker(paragraph)
                and not _paragraph_is_algorithm_or_code_like(paragraph)
                and indent_pt >= STRONG_INDENT_THRESHOLD_PT
            ):
                current = AuditFinding(
                    rule_id="P015",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "Line continuing the previous sentence (e.g. after a displayed "
                        "equation) appears to have a paragraph-style indent."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "unexpected_indent_on_continuation_line",
                        "indent_pt": f"{indent_pt:.1f}",
                        "expected": "flush_left_continuation_line",
                        "paragraph_line_count": str(len(paragraph)),
                        "paragraph_index": str(idx + 1),
                        "bbox": format_bbox_detail(paragraph[0].bbox),
                        "confidence": "medium",
                        "suggested_fix": (
                            "Remove the first-line indent from this line -- it "
                            "continues the previous sentence rather than starting a "
                            "new paragraph."
                        ),
                    },
                )
                existing = page_issue_findings.get("unexpected_indent_on_continuation_line")
                if existing is None or indent_pt > float(existing.details["indent_pt"]):
                    page_issue_findings["unexpected_indent_on_continuation_line"] = current

            if indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                seen_indented_paragraph = True

            # Detect body-text paragraphs after the first that are missing first-line indent.
            if idx >= 1:
                if idx in heading_exempt:
                    continue
                if idx in split_heading_exempt:
                    continue
                if _paragraph_starts_like_continuation(paragraph):
                    continue
                if _paragraph_is_algorithm_or_code_like(paragraph):
                    continue
                likely_indented = _is_likely_expected_indent(indent_pt)
                if likely_indented or not seen_indented_paragraph:
                    continue
                if not page_has_high_confidence_indent_style:
                    continue
                if len(paragraph) < MIN_LINES_FOR_MISSING_LATER_INDENT:
                    continue
                if NEGATIVE_INDENT_IGNORE_PT <= indent_pt < STRONG_INDENT_THRESHOLD_PT:
                    existing = page_issue_findings.get("missing_later_indent")
                    current = AuditFinding(
                        rule_id="P015",
                        severity=Severity.WARNING,
                        page=page.page_number,
                        message=(
                            "Later paragraph appears to be missing expected first-line indentation."
                        ),
                        details={
                            "page_number": str(page.page_number),
                            "issue_type": "missing_later_indent",
                            "indent_pt": f"{indent_pt:.1f}",
                            "expected": "first_line_indent_approx_36pt",
                            "paragraph_line_count": str(len(paragraph)),
                            "paragraph_index": str(idx + 1),
                            "bbox": format_bbox_detail(paragraph[0].bbox),
                            "confidence": "high",
                            "suggested_fix": (
                                "Apply a first-line indent to each body paragraph after "
                                "the first paragraph in the section."
                            ),
                        },
                    )
                    if existing is None:
                        page_issue_findings["missing_later_indent"] = current
                    else:
                        existing_indent = float(existing.details.get("indent_pt", "999"))
                        if indent_pt < existing_indent:
                            page_issue_findings["missing_later_indent"] = current

        if page_issue_findings and MAX_FINDINGS_PER_PAGE_ISSUE >= 1:
            findings.extend(page_issue_findings.values())

    return findings
