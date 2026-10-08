"""Conservative wrapped-entry internal spacing checks for TOC/List pages (P032).

Partial heuristic PDF coverage for Q053-Q055, Q066-Q067, and Q076-Q078.
"""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_lot_lof_column_headers import HEADER_ZONE_ABOVE_HEADING_PT
from njit_auditor.rules.pdf_toc_alignment import (
    INDENT_CLUSTER_TOLERANCE_PT,
    NUMERIC_ONLY_RE,
    TocPageContext,
    _clean_text,
    _extract_page_number_token,
    _likely_entry_line,
    classify_toc_heading_line,
    detect_toc_like_pages,
)

WRAPPED_GAP_RATIO_THRESHOLD = 1.7
MAX_WRAP_INTERNAL_GAP_RATIO = 4.0
FALLBACK_LINE_HEIGHT_PT = 12.0
MIN_CONTINUATION_TEXT_LEN = 8
ENTRY_START_BELOW_HEADING_PT = 20.0

# A LaTeX tocloft-style TOC lays out each entry's number, title, and page
# number in three separate tab-stop columns on one visual row. PyMuPDF's
# text-extraction line segmentation treats each column as its own line
# object even though all three share one baseline (identical, or within
# sub-point rounding of, y0) -- confirmed on the real corpus and represented
# in tests with synthetic entry text plus matching geometry,
# see docs/status/r036_split_section_number_recovery_20260914.md. A lone
# number fragment is either too short to survive
# ``MIN_CONTINUATION_TEXT_LEN`` (e.g. "2.2") or, for a bare integer like
# "7", indistinguishable from a page number by ``NUMERIC_ONLY_RE`` alone,
# so it is silently discarded before ``_reassemble_split_row_fragments``
# runs -- breaking both entry-boundary detection (the numbered title no
# longer looks like a new entry start) and the structural parent-to-
# first-child spacing exemption (``_classify_entry_level`` sees no digit
# prefix and returns "unknown"). The same row-splitting also detaches a
# trailing dot-leader run from its title on some rows (observed gap
# ~0.3pt on a numbered heading / dot-leader split); left alone,
# that stray fragment becomes a second "physical line" of what is really
# a single-line entry, corrupting the Ester 2026-09-14 pitch model's
# same-entry internal-pitch calibration with a near-zero sample. Both are
# fixed by the same row-reassembly pass below.
HIERARCHY_NUMBER_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){0,3}\.?$")
DOT_LEADER_ONLY_RE = re.compile(r"^[.\s․‥…]+$")
# Generous enough to absorb the observed sub-point baseline rounding
# between a title and its own detached number/dot-leader fragment
# (~0.3pt), while staying far below the smallest genuine inter-line pitch
# in the corpus (~13-14pt for single-spaced wrapped titles), so two
# actually-different physical lines are never merged into one.
DETACHED_FRAGMENT_ROW_TOLERANCE_PT = 2.0
# Observed real number-to-title gaps are ~10-13pt (roughly one character);
# this is a generous multiple of that, while remaining far short of a
# typical dot-leader run (150pt+), so it cannot bridge a number column to
# an unrelated far-away fragment.
MAX_NUMBER_TO_TITLE_GAP_PT = 40.0
CHAPTER_WRAP_INDENT_MIN_PT = 10.0
CHAPTER_WRAP_INDENT_MAX_PT = 24.0
CHAPTER_WRAP_LOCAL_PITCH_RATIO = 1.35
CHAPTER_TITLE_RE = re.compile(r"^\d+\s+[A-Z][A-Z\s,:;()\-]+")

# The bare-number alternative (``\d+(?:\.|\s)\s*(?-i:[A-Z])``) recognizes a
# top-level chapter/section heading numbered without the word "CHAPTER" and
# without a decimal sub-number, in either extraction style actually seen in
# the real corpus: with a space after the number or with the space dropped
# after the period (a PDF text-extraction artifact, not a real missing space
# in the source document). Both match the same shape
# ``NUMERIC_PREFIX_RE`` in pdf_toc_alignment.py already treats as an entry
# prefix elsewhere in this pipeline. Without this, a bare-numbered heading
# whose own title wraps across two physical lines is invisible to
# `_looks_like_new_entry_start[_given_previous]` (its first physical line
# has no dot leaders and doesn't match "chapter"/"appendix"/"N.N"), so it
# gets silently absorbed as a "continuation" of whatever entry precedes it
# -- corrupting any single-vs-double-spacing measurement that trusts the
# resulting (bogus, oversized) "entry" as calibration data. See
# docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md for the
# real cases this fixes. The uppercase requirement (scoped off from
# the outer IGNORECASE via ``(?-i:...)``) keeps this narrow to ALL-CAPS/
# Title-Case heading style and avoids matching an ordinary LOT/LOF caption
# continuation sentence that happens to start with a lowercase numeral-led
# word (e.g. "3 replicate trials were performed"); requiring an explicit
# period-or-whitespace separator (not zero of both) avoids matching a
# digit fused directly onto a word with no separator at all.
#
# The ``references|bibliography|vita|glossary|index`` alternatives cover
# the other top-level structural headings ``_classify_entry_level`` in
# pdf_toc_list_entry_spacing.py already recognizes as ``toc_level_1`` (kept
# as a literal, cross-referenced list here rather than a shared import to
# avoid a deeper cross-module refactor for this fix). Without them, a
# short (<=4-word) all-caps structural heading fails
# ``_likely_entry_line``'s all-caps-short-line filter (designed to reject
# noise, not to reject a genuine structural heading) and, since it also
# correctly fails ``_is_wrap_continuation_pair`` (it has its own page
# number), fell through the boundary check entirely and was silently
# appended to the PRECEDING entry by ``_group_lines_into_entries``'s
# default-to-continuation behavior -- the real structural-row case this fixes.
NEW_ENTRY_START_RE = re.compile(
    r"^(?:chapter|appendix|references|bibliography|vita|glossary|index"
    r"|\d+\.\d+|\d+(?:\.|\s)\s*(?-i:[A-Z]))",
    re.IGNORECASE,
)
COLUMN_HEADER_TOKENS = frozenset({"page", "pages", "table", "tables", "figure", "figures"})


def _line_has_page_number(line: PdfTextLine, cleaned: str) -> bool:
    token, _ = _extract_page_number_token(line, cleaned)
    if token is None:
        return False
    if token.isdigit():
        if "..." in cleaned or "...." in cleaned:
            return True
        return len(cleaned.strip()) <= len(token) + 3
    if len(token) <= 4 and re.fullmatch(r"[ivxlcdm]+", token, re.IGNORECASE):
        return True
    return False


def _is_column_header_line(cleaned: str) -> bool:
    return _clean_text(cleaned).lower() in COLUMN_HEADER_TOKENS


def _estimate_line_height(first: PdfTextLine, second: PdfTextLine) -> float:
    sizes = [span.size for line in (first, second) for span in line.spans if span.size]
    if sizes:
        return float(max(sizes))
    heights = [first.bbox.height, second.bbox.height]
    positive = [height for height in heights if height > 0]
    return max(positive) if positive else FALLBACK_LINE_HEIGHT_PT


def _looks_like_new_entry_start(cleaned: str) -> bool:
    if NEW_ENTRY_START_RE.match(cleaned):
        return True
    return _likely_entry_line(cleaned) and ("...." in cleaned or "..." in cleaned)


def _looks_like_new_entry_start_given_previous(
    previous: PdfTextLine, cleaned: str
) -> bool:
    """Like ``_looks_like_new_entry_start``, but aware that a dot-leader
    line only signals a genuinely NEW entry when the entry currently being
    built already reached its own dot-leader/page-number column (i.e. is
    already complete). A wrapped entry's title normally spans a line with
    no dot leaders followed by a line that finishes with dot leaders (and,
    on the actual PDF page, a page number -- which text extraction may
    split off onto its own short numeric line and which
    ``_collect_entry_region_lines`` then discards, so the page number
    itself cannot be relied on as the signal). That finishing line must
    complete the still-open previous entry, not start another one, even
    though it has the same dot-leader shape as a real new entry. Checking
    whether *previous* itself already has dot leaders avoids that
    extraction quirk: if it does, previous is already a complete entry and
    this line is a new one; if it does not, previous is still an open
    title and this line's dots complete it. The strong numbered/Chapter/
    Appendix prefix signal is unaffected: it always means a new entry.

    A rigorously-confirmed page number on *previous* -- both an actual
    dot-leader run AND ``_line_has_page_number`` agreeing there is a page
    number token, not just the raw "..." substring test used below for
    *cleaned* -- is an even stronger, unconditional signal: *previous* is
    unambiguously a finished entry, so *cleaned* must start a new one even
    when *cleaned* itself has no dot leaders yet -- e.g. because it is the
    first physical line of the NEXT entry's own wrapped (multi-line)
    title/caption, which by definition has no dot leaders on this line.
    Two real, previously-mis-grouped cases this covers: an unnumbered,
    no-prefix all-caps chapter title swallowed into the preceding complete
    numbered entry, and a wrapping List of Figures caption's first line
    swallowed into the preceding page-numbered caption.

    Requiring an actual dot-leader run on *previous* in addition to
    ``_line_has_page_number`` (rather than trusting either alone) matters
    because ``_line_has_page_number``'s short-roman-numeral branch has no
    dot-leader requirement of its own and readily false-triggers on an
    ordinary trailing word that happens to be spelled entirely with roman
    numeral letters -- confirmed on the real corpus, where a List of
    Figures caption line ending in an all-roman-letter abbreviation (not a
    page number) was misread as ending in the roman numeral "LC" (=150)
    and wrongly split the caption's own
    wrapped continuation into a bogus second entry. The plain "..."
    substring test *previous* uses below for *cleaned* is looser still (it
    also matches ordinary prose containing an ellipsis or a run of
    periods with no page number at all), which caused unacceptable
    over-splitting across the corpus (verified empirically) when tried as
    the unconditional trigger instead of this rigorous one. See
    docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md.
    """
    if NEW_ENTRY_START_RE.match(cleaned):
        return True
    previous_text = _clean_text(previous.text)
    previous_has_dot_leader = "...." in previous_text or "..." in previous_text
    if previous_has_dot_leader and _line_has_page_number(previous, previous_text):
        return True
    if not (_likely_entry_line(cleaned) and ("...." in cleaned or "..." in cleaned)):
        return False
    return previous_has_dot_leader


def _classify_entry_kind(page_type: str, cleaned: str) -> str:
    if page_type == "list_of_tables":
        return "table_entry"
    if page_type == "list_of_figures":
        return "figure_entry"
    if re.match(r"^[0-9]+\.[0-9]+\.[0-9]+", cleaned):
        return "toc_level_3"
    if re.match(r"^[0-9]+\.[0-9]+", cleaned):
        return "toc_level_2"
    if re.match(r"^(?:chapter|appendix)\b", cleaned, re.IGNORECASE):
        return "toc_level_1"
    if page_type == "table_of_contents" and CHAPTER_TITLE_RE.match(cleaned):
        return "toc_level_1"
    return "unknown"


def _is_chapter_title_wrap_pair(first: PdfTextLine, second: PdfTextLine) -> bool:
    """Recognize a numbered chapter title whose wrap hangs under its title text."""
    first_text, second_text = _clean_text(first.text), _clean_text(second.text)
    indent = second.bbox.x0 - first.bbox.x0
    return bool(
        CHAPTER_TITLE_RE.match(first_text)
        and second_text
        and second_text[0].isupper()
        and second_text.upper() == second_text
        and CHAPTER_WRAP_INDENT_MIN_PT <= indent <= CHAPTER_WRAP_INDENT_MAX_PT
        and not _looks_like_new_entry_start(second_text)
        and not _line_has_page_number(first, first_text)
        and not _line_has_page_number(second, second_text)
    )


def _local_single_wrap_pitch(context: TocPageContext, lines: list[PdfTextLine]) -> float | None:
    """Calibrate against an unambiguous wrapped entry on the same TOC page."""
    pitches = [
        second.bbox.y0 - first.bbox.y0
        for first, second in zip(lines, lines[1:])
        if _is_wrap_continuation_pair(first, second, context.page_type)
        and not _has_intervening_page_number_line(context, first, second)
        and 0 < second.bbox.y0 - first.bbox.y0 <= 1.4 * _estimate_line_height(first, second)
    ]
    return median(pitches) if pitches else None


def _cluster_rows_by_y0(candidates: list[PdfTextLine]) -> list[list[int]]:
    """Group candidate-list indices into visual rows: consecutive (by y0)
    fragments where each one sits within ``DETACHED_FRAGMENT_ROW_TOLERANCE_PT``
    of the previous fragment in the same row. Sequential/greedy rather than
    a fixed grid (``round(y0 / tol)``) so two fragments a hair apart never
    land in different buckets just because they straddle a grid boundary.
    """
    order = sorted(range(len(candidates)), key=lambda i: candidates[i].bbox.y0)
    rows: list[list[int]] = []
    for index in order:
        gap = candidates[index].bbox.y0 - candidates[rows[-1][-1]].bbox.y0 if rows else None
        if gap is not None and gap <= DETACHED_FRAGMENT_ROW_TOLERANCE_PT:
            rows[-1].append(index)
        else:
            rows.append([index])
    return rows


def _reassemble_split_row_fragments(candidates: list[PdfTextLine]) -> list[PdfTextLine]:
    """Reassemble one logical TOC row that PDF text extraction split into
    multiple line objects at (or within sub-point rounding of) one shared
    baseline -- a leading hierarchy-number fragment (e.g. "7", "2.2",
    "1.1.1"), the title itself, and sometimes a trailing dot-leader run,
    each in its own tab-stop column. See the module-level comment above
    ``HIERARCHY_NUMBER_RE`` for why this is necessary and what each half
    fixes.

    Only ever merges onto a row's single unambiguous "primary" fragment --
    the one that is neither a hierarchy-number shape, a plain page-number
    shape, nor a pure dot-leader run. A row with zero or more than one such
    fragment is left completely untouched (nothing safe to reassemble: no
    identifiable title, or more than one candidate title on the same
    baseline). A leading number is only attached when it sits immediately
    to the *left* of the primary fragment within a sensible gap -- never
    an arbitrary nearby numeral -- and a trailing dot-leader run only when
    it sits immediately to the *right*. A page-number fragment (already
    handled by the existing ``NUMERIC_ONLY_RE`` filter) is never merged
    onto anything.
    """
    consumed: set[int] = set()
    merged_text: dict[int, str] = {}

    for row in _cluster_rows_by_y0(candidates):
        if len(row) < 2:
            continue
        row = sorted(row, key=lambda i: candidates[i].bbox.x0)

        def _shape(i: int) -> str:
            cleaned = _clean_text(candidates[i].text)
            if HIERARCHY_NUMBER_RE.match(cleaned) or NUMERIC_ONLY_RE.match(cleaned):
                return "number"
            if DOT_LEADER_ONLY_RE.match(candidates[i].text.strip()):
                return "dots"
            return "primary"

        primary_positions = [pos for pos, i in enumerate(row) if _shape(i) == "primary"]
        if len(primary_positions) != 1:
            continue
        primary_pos = primary_positions[0]
        primary_index = row[primary_pos]
        primary_line = candidates[primary_index]
        merged = primary_line.text.strip()
        changed = False

        if primary_pos > 0:
            left_index = row[primary_pos - 1]
            left_line = candidates[left_index]
            cleaned_left = _clean_text(left_line.text)
            gap = primary_line.bbox.x0 - left_line.bbox.x1
            if HIERARCHY_NUMBER_RE.match(cleaned_left) and 0 <= gap <= MAX_NUMBER_TO_TITLE_GAP_PT:
                merged = f"{cleaned_left} {merged}"
                consumed.add(left_index)
                changed = True

        if primary_pos + 1 < len(row):
            right_index = row[primary_pos + 1]
            right_line = candidates[right_index]
            if DOT_LEADER_ONLY_RE.match(right_line.text.strip()):
                merged = f"{merged} {right_line.text.strip()}"
                consumed.add(right_index)
                changed = True

        if changed:
            merged_text[primary_index] = merged

    result: list[PdfTextLine] = []
    for index, line in enumerate(candidates):
        if index in consumed:
            continue
        if index in merged_text:
            result.append(line.model_copy(update={"text": merged_text[index]}))
        else:
            result.append(line)
    return result


def _collect_entry_region_lines(context: TocPageContext) -> list[PdfTextLine]:
    entry_start_y = context.heading_bottom_y + ENTRY_START_BELOW_HEADING_PT
    header_y_min = context.heading_bottom_y - HEADER_ZONE_ABOVE_HEADING_PT
    candidates: list[PdfTextLine] = []
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= context.heading_bottom_y + 2:
                continue
            if line.bbox.y0 < header_y_min:
                continue
            if line.bbox.y0 <= entry_start_y:
                continue
            cleaned = _clean_text(line.text)
            if not cleaned:
                continue
            if classify_toc_heading_line(normalize_heading_text(line.text)) is not None:
                continue
            if _is_column_header_line(cleaned):
                continue
            candidates.append(line)
    candidates.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))

    lines: list[PdfTextLine] = []
    for line in _reassemble_split_row_fragments(candidates):
        cleaned = _clean_text(line.text)
        if NUMERIC_ONLY_RE.match(cleaned):
            continue
        if len(cleaned) < MIN_CONTINUATION_TEXT_LEN:
            continue
        lines.append(line)
    return lines


def _has_intervening_page_number_line(
    context: TocPageContext,
    first: PdfTextLine,
    second: PdfTextLine,
) -> bool:
    """Return True when a page-number-only line sits between two entry-region lines."""

    y_lo = first.bbox.y1
    y_hi = second.bbox.y0
    if y_hi <= y_lo:
        return False
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= y_lo or line.bbox.y0 >= y_hi:
                continue
            cleaned = _clean_text(line.text)
            if NUMERIC_ONLY_RE.match(cleaned):
                return True
            if _line_has_page_number(line, cleaned) and len(cleaned) <= 6:
                return True
    return False


def _is_wrap_continuation_pair(
    first: PdfTextLine,
    second: PdfTextLine,
    page_type: str,
) -> bool:
    first_text = _clean_text(first.text)
    second_text = _clean_text(second.text)
    if _line_has_page_number(first, first_text) or _line_has_page_number(second, second_text):
        return False
    if abs(first.bbox.x0 - second.bbox.x0) > INDENT_CLUSTER_TOLERANCE_PT:
        return False
    if _is_column_header_line(second_text):
        return False
    if _looks_like_new_entry_start(second_text):
        return False
    if not (_likely_entry_line(first_text) or len(first_text) >= 15):
        return False
    if page_type == "list_of_tables" and re.match(
        r"^table\s+[0-9]", second_text, re.IGNORECASE
    ):
        return False
    if page_type == "list_of_figures" and re.match(
        r"^fig(?:ure)?\.?\s+[0-9]", second_text, re.IGNORECASE
    ):
        return False
    return True


def check_pdf_toc_list_wrapped_spacing(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P032 warnings for likely wrapped TOC/List entries with excessive internal gaps."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        lines = _collect_entry_region_lines(context)
        if len(lines) < 2:
            continue
        local_pitch = (
            _local_single_wrap_pitch(context, lines)
            if context.page_type == "table_of_contents"
            else None
        )

        for first, second in zip(lines, lines[1:]):
            ordinary_wrap = _is_wrap_continuation_pair(first, second, context.page_type)
            chapter_wrap = bool(
                local_pitch is not None
                and context.page_type == "table_of_contents"
                and _is_chapter_title_wrap_pair(first, second)
            )
            if not (ordinary_wrap or chapter_wrap):
                continue
            if _has_intervening_page_number_line(context, first, second):
                continue

            gap_pt = second.bbox.y0 - first.bbox.y1
            if gap_pt <= 0:
                continue

            line_height = _estimate_line_height(first, second)
            gap_ratio = gap_pt / line_height
            if chapter_wrap:
                assert local_pitch is not None
                expected_max_gap_pt = (
                    local_pitch * CHAPTER_WRAP_LOCAL_PITCH_RATIO - first.bbox.height
                )
                if gap_pt <= expected_max_gap_pt:
                    continue
                confidence = "medium"
            else:
                if gap_ratio <= WRAPPED_GAP_RATIO_THRESHOLD:
                    continue
                if gap_ratio >= MAX_WRAP_INTERNAL_GAP_RATIO:
                    continue
                expected_max_gap_pt = line_height * WRAPPED_GAP_RATIO_THRESHOLD
                confidence = (
                    "high" if gap_ratio >= (WRAPPED_GAP_RATIO_THRESHOLD + 0.3) else "medium"
                )
            first_text = _clean_text(first.text)
            pair_box = BBox(
                x0=min(first.bbox.x0, second.bbox.x0),
                y0=first.bbox.y0,
                x1=max(first.bbox.x1, second.bbox.x1),
                y1=second.bbox.y1,
            )

            findings.append(
                AuditFinding(
                    rule_id="P032",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "Wrapped TOC/List entry appears to have excessive internal "
                        "line spacing."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "section_type": context.page_type,
                        "issue_type": "wrapped_entry_internal_spacing",
                        "entry_kind": _classify_entry_kind(context.page_type, first_text),
                        "observed_gap_pt": f"{gap_pt:.1f}",
                        "expected_max_gap_pt": f"{expected_max_gap_pt:.1f}",
                        "line_height_or_font_size_pt": f"{line_height:.1f}",
                        "bbox": format_bbox_detail(pair_box),
                        "confidence": confidence,
                        "source_q_rule_ids": "Q053-Q055,Q066-Q067,Q076-Q078",
                    },
                )
            )

    return findings
