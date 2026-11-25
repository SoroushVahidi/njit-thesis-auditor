"""Heuristic TOC/List alignment checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from collections.abc import Iterator
from copy import copy
from dataclasses import dataclass
from statistics import median

from njit_auditor.digital_commons_wrapper import (
    detect_digital_commons_wrapper_pages,
    without_wrapper_pages,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import join_content_span_texts
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextLine,
    PdfTextSpan,
    format_bbox_detail,
)
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.toc_entry_geometry import (
    LEADER_CHARS,
    LeaderGap,
    measure_title_leader_gap,
    row_font_size,
    row_glyphs,
    title_text_start_x,
    visible_start_x,
)
from njit_auditor.toc_list_student_preview import (
    is_toc_export_metadata_line,
    is_toc_structural_column_label,
    sanitize_toc_list_entry_preview,
)

TOC_HEADING_MAP = {
    "TABLE OF CONTENTS": "table_of_contents",
    "LIST OF TABLES": "list_of_tables",
    "LIST OF FIGURES": "list_of_figures",
}
HEADING_SUFFIX_RE = re.compile(r"[\s:.\-]+(?:\((?:continued)\)|continued)\s*$", re.IGNORECASE)
TRAILING_PUNCT_RE = re.compile(r"[.:]+$")
PAGE_NUMBER_TOKEN_RE = re.compile(
    r"(?:(?:\.{2,}\s*)|(?:\s{2,}))(?P<num>(?:[0-9]+|[ivxlcdm]+))$",
    re.IGNORECASE,
)
# Single-space trailing page numbers are common when leaders are absent and the
# page number is drawn in the same text object as the title. Only accept these
# when the line reaches the right-hand page-number column (geometry gate below).
TRAILING_RIGHT_COLUMN_PAGE_NUM_RE = re.compile(
    r"^(?P<body>.+\S)\s+(?P<num>(?:[0-9]{1,4}|[ivxlcdm]{1,8}))$",
    re.IGNORECASE,
)
ENTRY_START_RE = re.compile(r"^[A-Za-z0-9(\[]")
NUMERIC_ONLY_RE = re.compile(r"^(?:[0-9]+|[ivxlcdm]+)$", re.IGNORECASE)
SECTION_NUMBER_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?[\s:]")
SECTION_NUMBER_ONLY_RE = re.compile(r"^\d+(?:\.\d+)*$")
# Lettered appendix subsections such as "A.1 …" / "B.2.3 …" (require at least one
# ".digit" segment so a bare letter is not treated as a numbered level).
LETTERED_SECTION_PREFIX_RE = re.compile(r"^([A-Z](?:\.\d+)+)\.?[\s:]")
ROMAN_SECTION_PREFIX_RE = re.compile(r"^[IVXLCDM]{2,8}(?:\.\d+)+\.?[\s:]")
ABBREVIATED_LIST_ENTRY_RE = re.compile(
    r"^(?:fig|tab)\.\s+(?:[A-Z]\.)?\d+(?:\.\d+)*\b", re.IGNORECASE
)
# Word-prefix TOC roots that sit at chapter / back-matter level.
TOP_LEVEL_TOC_WORD_PREFIX_RE = re.compile(
    r"^(APPENDIX|CHAPTER|REFERENCES|BIBLIOGRAPHY|ABSTRACT|"
    r"ACKNOWLEDGE?MENTS?|DEDICATION|VITA|BIOGRAPHICAL\s+SKETCH)\b",
    re.IGNORECASE,
)
LINE_PREVIEW_MAX_LEN = 80
RIGHT_EDGE_TOLERANCE_PT = 10.0
MIN_ENTRIES_FOR_DOT_STYLE = 4
PAGE_NUMBER_LINE_Y_TOLERANCE_PT = 5.0
PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT = 8.0
RIGHT_COLUMN_MIN_X_OFFSET_PT = 200.0
# Single-spaced TOC wrap continuations are typically ~14–16 pt below the parent
# title row (line height), so keep this just above one line.
WRAPPED_ENTRY_Y_GAP_PT = 16.0
SAME_BASELINE_Y_TOLERANCE_PT = 3.0
# Entries whose left edge sits in the right half of the page are usually
# margin notes / annotation fragments, not TOC body rows.
TOC_ENTRY_MAX_LEFT_FRACTION = 0.55
PREFIX_ENTRY_MIN_LEN = 4
DEFAULT_ENTRY_MIN_LEN = 8
PREFIX_ENTRY_RE = re.compile(r"^(TABLE|FIGURE|CHAPTER|APPENDIX)\b", re.IGNORECASE)
NUMERIC_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s")
INDENT_CLUSTER_TOLERANCE_PT = 12.0
MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON = 3
HIERARCHY_INDENT_TOLERANCE_PT = 10.0
HIERARCHY_INDENT_MEDIUM_CONFIDENCE_PT = 18.0
# Ester (2026-09-23, R018): when a TOC title runs longer than one line, the
# continuation line aligns with the first line's title text, not with the
# section number. Ester's November 18 follow-up explicitly accepts indentation
# of second and third title lines, so only a line starting left of the title
# text is a supported alignment violation.
#
# The existing TOC x-tolerances (10-12 pt) cluster indent levels across
# entries and are too coarse here: a single-digit label plus its space is only
# ~0.75 em (~9 pt at 12 pt). Observed alignment noise on correctly aligned
# corpus entries is <= 0.1 pt, so a quarter-em band (3 pt at 12 pt, never
# under 2 pt) absorbs extraction jitter while staying well below the
# >= 0.75 em shift that a number-column alignment necessarily produces.
WRAPPED_CONTINUATION_ALIGN_TOLERANCE_EM = 0.25
WRAPPED_CONTINUATION_MIN_TOLERANCE_PT = 2.0
WRAPPED_CONTINUATION_MAX_ROWS = 3
_WRAPPED_CONTINUATION_STOP_RE = re.compile(
    r"^(?:chapter|appendix|references|bibliography|vita|glossary|index)\b",
    re.IGNORECASE,
)
# Ester (2026-09-23, leader placement; TOC, List of Tables, List of Figures):
# leader dots begin right after the title's final line, with at most one
# normal space between the last title character and the first dot.
#
# The gap is measured from the last title glyph's right edge to the first
# leader glyph's left edge. Allowance = one measured space + the dot's in-cell
# padding ((pitch - dot advance) / 2; a spaced leader cell centers its dot) +
# a 0.1 em extraction-jitter band (the fraction ``pdf_layout`` uses as its
# word-space gap floor). When a page's leaders are *grid-aligned* -- every
# first dot sits on one common x-grid (LaTeX dotfill, Word dot-leader tabs;
# measured spread <= 0.4 pt on such corpus pages) -- the typesetter, not the
# author, pushes the first dot up to one pitch past the title end, so one
# pitch of grid phase is added. Typed leaders (spread >= 1.9 pt on the corpus
# and NJIT's model pages) get no phase allowance, so two typed spaces fail.
# Pages with too few leader rows to tell keep the grid allowance (the
# conservative choice).
LEADER_GAP_JITTER_EM = 0.10
LEADER_GRID_MIN_ROWS = 3
LEADER_GRID_MAX_SPREAD_PT = 1.0
_BASELINE_ROUNDING_PT = 0.05


class TocEntryLine:
    """Normalized entry line for TOC/list checks."""

    def __init__(
        self,
        line: PdfTextLine,
        cleaned_text: str,
        page_number_token: str | None,
        page_number_right_x: float | None,
        indent_x: float,
        has_leader_dots: bool,
        *,
        is_wrapped: bool = False,
        page_number_line: PdfTextLine | None = None,
    ) -> None:
        self.line = line
        self.cleaned_text = cleaned_text
        self.page_number_token = page_number_token
        self.page_number_right_x = page_number_right_x
        self.indent_x = indent_x
        self.has_leader_dots = has_leader_dots
        self.is_wrapped = is_wrapped
        self.page_number_line = page_number_line


def has_trailing_page_number_token(entry: TocEntryLine) -> bool:
    """Require a detected page number to occur at the end of its list row.

    The shared parser can find a digit or Roman-looking letter inside a
    mathematical symbol in a wrapped title. That token is not the page-number
    column when title text follows it on the same reconstructed row.
    """
    token = entry.page_number_token
    return bool(
        token
        and re.search(rf"(?:^|\s){re.escape(token)}\s*$", entry.cleaned_text, re.IGNORECASE)
    )


def _has_list_leader_folio(entry: TocEntryLine) -> bool:
    if has_trailing_page_number_token(entry):
        return True

    # The wrap merger strips the folio from display text but retains its
    # visual row. Require the retained row, not a separately paired numeral.
    row = entry.page_number_line
    token = entry.page_number_token
    if not entry.is_wrapped or row is None or not token or not row.spans:
        return False
    if (
        row.bbox.y0 <= entry.line.bbox.y0
        or entry.line.spans[-len(row.spans):] != row.spans
    ):
        return False
    folio = _right_edge_page_number_span(row)
    if (
        folio is None or _clean_text(folio.text).casefold() != token.casefold()
        or folio.bbox.x1 != entry.page_number_right_x
        or folio.baseline_y is None or not folio.size
        or not re.search(rf"\s{re.escape(token)}\s*$", _row_text(row), re.IGNORECASE)
    ):
        return False
    title = [span for span in row.spans if span is not folio and span.text.strip()]
    return bool(
        title
        and any(char.isalpha() for span in title for char in span.text)
        and all(
            span.baseline_y is not None
            and abs(span.baseline_y - folio.baseline_y) <= SAME_BASELINE_Y_TOLERANCE_PT
            for span in title
        )
        and folio.bbox.x0 - max(span.bbox.x1 for span in title) >= folio.size
    )


def _overprints_title(dot: PdfTextSpan, spans: list[PdfTextSpan]) -> bool:
    text = dot.text.strip()
    if not text or dot.baseline_y is None or any(c not in ".…·" and not c.isspace() for c in text):
        return False
    # A run wholly inside another span on the same line cannot connect
    # that title to its folio. Leave touching and unmeasured runs alone.
    return any(
        title.baseline_y is not None
        and abs(title.baseline_y - dot.baseline_y) <= 0.5
        and title.bbox.x0 < dot.bbox.x0 < dot.bbox.x1 < title.bbox.x1
        and any(c.isalpha() for c in title.text)
        for title in spans
    )


def _row_without_overprinted_dots(line: PdfTextLine) -> PdfTextLine:
    spans = [span for span in line.spans if not _overprints_title(span, line.spans)]
    if len(spans) == len(line.spans):
        return line
    return line.model_copy(update={"spans": spans, "text": join_content_span_texts(spans)})


def leader_evidence_entry(entry: TocEntryLine) -> TocEntryLine:
    """Exclude dot-only title overprints when checking leader consistency."""
    if not entry.has_leader_dots:
        return entry
    line = _row_without_overprinted_dots(entry.line)
    folio_row = entry.page_number_line
    if folio_row is entry.line:
        folio_row = line
    elif folio_row is not None:
        folio_row = _row_without_overprinted_dots(folio_row)
    if line is entry.line and folio_row is entry.page_number_line:
        return entry

    adjusted = copy(entry)
    adjusted.line = line
    adjusted.page_number_line = folio_row
    if line is not entry.line:
        text = _row_text(line)
        # Keep the existing folio eligibility if wrapping stripped its
        # token from display text. Ownership is checked separately.
        if not has_trailing_page_number_token(entry):
            text = _strip_trailing_page_token(text, entry.page_number_token)
        adjusted.cleaned_text = text
    adjusted.has_leader_dots = _has_leader_dot_pattern(adjusted.cleaned_text) or (
        folio_row is not None and _has_leader_dot_pattern(_row_text(folio_row))
    )
    return adjusted


def is_isolated_terminal_grid_leader_dot(
    entry: TocEntryLine, peers: list[TocEntryLine]
) -> bool:
    """Identify a lone final leader dot on a page-wide dot-leader grid.

    On some LaTeX pages, a long title leaves room for only the last cell of
    the leader grid. The extracted row then ends ``title . page``. Its dot is
    visual leader formatting, not title punctuation. Require the dot to be a
    separate span at the same rightmost grid position as several multi-dot
    peers; ordinary punctuation attached to a title does not meet this test.
    """
    spans = entry.line.spans
    if (
        len(spans) < 2
        or entry.page_number_token is None
        or spans[-1].text.strip() != entry.page_number_token
        or spans[-2].text.strip() != "."
    ):
        return False
    terminal_dot = spans[-2]
    dot_x = terminal_dot.bbox.x0
    if terminal_dot.char_x_bounds is not None:
        dot_index = next(
            (index for index, char in enumerate(terminal_dot.text) if char == "."),
            None,
        )
        if dot_index is not None:
            dot_x = terminal_dot.char_x_bounds[dot_index][0]
    matching_grid_rows = 0
    for peer in peers:
        if peer is entry:
            continue
        dots = [span for span in peer.line.spans if span.text.strip() == "."]
        if len(dots) < 2:
            continue
        peer_dot = dots[-1]
        peer_dot_x = peer_dot.bbox.x0
        if peer_dot.char_x_bounds is not None:
            dot_index = next(
                (index for index, char in enumerate(peer_dot.text) if char == "."),
                None,
            )
            if dot_index is not None:
                peer_dot_x = peer_dot.char_x_bounds[dot_index][0]
        if abs(peer_dot_x - dot_x) <= LEADER_GRID_MAX_SPREAD_PT:
            matching_grid_rows += 1
    return matching_grid_rows >= LEADER_GRID_MIN_ROWS


@dataclass(frozen=True)
class _DetachedLeaderGap:
    title_right: float
    folio_left: float
    title: PdfTextSpan
    folio: PdfTextSpan

    @property
    def offset_limit(self) -> float:
        # Allow a small typesetting offset relative to both anchors' sizes.
        # Cap at half the visual-row grouping band even for large fonts.
        return min(
            0.15 * min(self.title.size or 0, self.folio.size or 0),
            SAME_BASELINE_Y_TOLERANCE_PT / 2,
        )

    def contains(self, line: PdfTextLine) -> bool:
        box = line.bbox
        if not self.title_right < box.x0 < box.x1 <= self.folio_left:
            return False
        title_y, folio_y = self.title.baseline_y, self.folio.baseline_y
        dot_y = line.baseline_y
        if dot_y is None:
            # Legacy layouts can lack a fragment origin. Use the final
            # title and folio boxes, with the same horizontal bounds.
            return all(
                span.bbox.y0 - 2 <= box.y0 < box.y1 <= span.bbox.y1 + 2
                for span in (self.title, self.folio)
            )
        if title_y is None or folio_y is None:
            return False
        if abs(dot_y - folio_y) <= _BASELINE_ROUNDING_PT:
            # Different ascenders can give the same-baseline dots much
            # taller or shorter boxes than the title and folio.
            return True
        return (
            max(abs(dot_y - y) for y in (title_y, folio_y)) <= self.offset_limit
            and all(
                span.bbox.y0 < dot_y < span.bbox.y1
                and box.y0 < y < box.y1
                for span, y in ((self.title, title_y), (self.folio, folio_y))
            )
        )


def _detached_leader_gap(
    entry: TocEntryLine, title_right: float | None = None,
) -> _DetachedLeaderGap | None:
    row, token = entry.page_number_line, entry.page_number_token
    if row is None or not token or not row.spans or entry.page_number_right_x is None:
        return None
    folio_span = max(row.spans, key=lambda span: span.bbox.x1)
    glyphs = [glyph for glyph in row_glyphs(row) if not glyph.char.isspace()]
    if len(glyphs) <= len(token) or not re.search(
        rf"[\s.…·]{re.escape(token)}\s*$", row.text, re.IGNORECASE
    ):
        return None
    tail = glyphs[-len(token):]
    if "".join(glyph.char for glyph in tail).casefold() != token.casefold():
        return None
    if title_right is None:
        title_right = glyphs[-len(token) - 1].x1
    folio_left, folio_right = tail[0].x0, tail[-1].x1
    jitter = LEADER_GAP_JITTER_EM * row_font_size(glyphs)
    if (
        title_right is None or folio_left is None or folio_right is None
        or not entry.indent_x < title_right < folio_left < folio_right
        or abs(folio_right - entry.page_number_right_x) > jitter
    ):
        return None
    for span in sorted(row.spans, key=lambda span: span.bbox.x0, reverse=True):
        if not span.bbox.x0 < title_right <= span.bbox.x1:
            continue
        if span.baseline_y is not None and folio_span.baseline_y is not None:
            # The final title and folio must already belong to one row.
            if abs(span.baseline_y - folio_span.baseline_y) > jitter:
                continue
        return _DetachedLeaderGap(title_right, folio_left, span, folio_span)
    return None


def _has_competing_baseline(
    fragment: PdfTextLine, gap: _DetachedLeaderGap, source_lines: list[PdfTextLine],
) -> bool:
    dot_y, title_y, folio_y = fragment.baseline_y, gap.title.baseline_y, gap.folio.baseline_y
    if dot_y is None or title_y is None or folio_y is None:
        return False
    if abs(dot_y - folio_y) <= _BASELINE_ROUNDING_PT:
        return False
    # Inspect source lines too. Close rows can merge during reconstruction,
    # and a neighboring title may have no folio or insufficient glyph bounds.
    return any(
        line.baseline_y is not None
        and abs(line.baseline_y - dot_y) <= gap.offset_limit
        and min(abs(line.baseline_y - y) for y in (title_y, folio_y)) > _BASELINE_ROUNDING_PT
        and line.bbox.x0 < fragment.bbox.x0
        and any(char.isalnum() for char in line.text)
        for line in source_lines
    )


def owned_detached_leader_lines(
    entry: TocEntryLine, page: PdfPage, peers: list[TocEntryLine],
    *, title_right: float | None = None,
) -> Iterator[PdfTextLine]:
    """Yield dot-only source fragments with one verified title-to-folio owner."""
    gap = _detached_leader_gap(entry, title_right)
    if gap is None:
        return
    peer_gaps: list[_DetachedLeaderGap] | None = None
    source_lines = [line for block in page.text_blocks for line in block.lines]
    for line in source_lines:
        if (
            not 0 <= line.bbox.y0 < line.bbox.y1 <= page.height
            or not gap.contains(line)
            or not line.text.strip()
            or any(char not in LEADER_CHARS and not char.isspace() for char in line.text)
            or _has_competing_baseline(line, gap, source_lines)
        ):
            continue
        if peer_gaps is None:
            peer_gaps = [
                other for peer in peers
                if peer is not entry and (other := _detached_leader_gap(peer)) is not None
            ]
        if not any(other.contains(line) for other in peer_gaps):
            yield line


def entry_has_visible_dot_leader(
    entry: TocEntryLine, page: PdfPage, peers: list[TocEntryLine]
) -> bool:
    """Recognize leaders even when PDF extraction splits their dots off-row."""
    if entry.has_leader_dots or is_isolated_terminal_grid_leader_dot(entry, peers):
        return True
    if re.search(r"(?:\s[.·…]){2,}\s+\S+\s*$", entry.cleaned_text):
        return True
    # Preserve the legacy bbox path for old rows with no source spans.
    # Measured rows still require the title-to-folio ownership check.
    if (
        entry.page_number_line is None
        and not entry.line.spans
        and entry.page_number_right_x is not None
    ):
        return any(
            line.baseline_y is None
            and re.fullmatch(r"[.·…]{2,}", re.sub(r"\s+", "", line.text))
            and entry.line.bbox.y0 - 2 <= line.bbox.y0 < line.bbox.y1 <= entry.line.bbox.y1 + 2
            and entry.indent_x + 10 < line.bbox.x0 < line.bbox.x1 < entry.page_number_right_x - 2
            for block in page.text_blocks for line in block.lines
        )
    # A long title can leave room for only two dots before the folio.
    return any(
        sum(char in LEADER_CHARS for char in line.text) >= 2
        for line in owned_detached_leader_lines(entry, page, peers)
    )


def _details_with_affected_entry_preview(
    details: dict[str, str],
    entry: TocEntryLine,
) -> dict[str, str]:
    preview = sanitize_toc_list_entry_preview(entry.cleaned_text)
    enriched = {**details, "bbox": format_bbox_detail(entry.line.bbox)}
    if preview:
        enriched["affected_entry_preview"] = preview
    return enriched


class TocPageContext:
    """TOC-like page with extracted context and heading line position."""

    def __init__(self, page: PdfPage, page_type: str, heading_bottom_y: float) -> None:
        self.page = page
        self.page_type = page_type
        self.heading_below_y = heading_bottom_y

    @property
    def heading_bottom_y(self) -> float:
        return self.heading_below_y


class TocPageRun:
    """Consecutive same-type TOC/LoT/LoF pages for cross-page consumers."""

    def __init__(self, page_type: str, contexts: list[TocPageContext]) -> None:
        self.page_type = page_type
        self.contexts = contexts

    def iter_entries(self) -> list[TocEntryLine]:
        combined: list[TocEntryLine] = []
        for context in self.contexts:
            combined.extend(extract_toc_entry_lines(context))
        return combined


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def _normalize_toc_heading_variant(text: str) -> str:
    """Normalize TOC/list heading text for robust page-type detection."""

    normalized = _clean_text(text).upper()
    normalized = TRAILING_PUNCT_RE.sub("", normalized).strip()
    normalized = HEADING_SUFFIX_RE.sub("", normalized).strip()
    normalized = TRAILING_PUNCT_RE.sub("", normalized).strip()
    return _clean_text(normalized)


def _detect_toc_page_type(line_text: str) -> str | None:
    from njit_auditor.rules.pdf_frontmatter_heading_gate import (
        passes_standalone_line_gate,
        resolve_gate_heading_from_line,
    )

    if not passes_standalone_line_gate(line_text):
        return None
    resolved = resolve_gate_heading_from_line(line_text)
    if resolved is not None:
        return TOC_HEADING_MAP.get(resolved[0])
    normalized = _normalize_toc_heading_variant(line_text)
    return TOC_HEADING_MAP.get(normalized)


def classify_toc_heading_line(line_text: str) -> tuple[str, bool] | None:
    """Return ``(page_type, is_continued)`` when *line_text* is a TOC/List heading."""

    cleaned = _clean_text(line_text)
    upper = cleaned.upper()
    upper = TRAILING_PUNCT_RE.sub("", upper).strip()
    is_continued = bool(HEADING_SUFFIX_RE.search(upper))
    page_type = TOC_HEADING_MAP.get(_normalize_toc_heading_variant(cleaned))
    if page_type is None:
        return None
    return page_type, is_continued


def detect_toc_like_pages(pdf_document: PdfDocument) -> list[TocPageContext]:
    """Detect TOC/List pages from named heading lines."""
    wrapper_pages = detect_digital_commons_wrapper_pages(pdf_document)
    working_doc = without_wrapper_pages(pdf_document, wrapper_pages)

    contexts: list[TocPageContext] = []

    for page in working_doc.pages:
        best_match: tuple[str, float] | None = None
        for block in page.text_blocks:
            for line in block.lines:
                normalized = normalize_heading_text(line.text)
                page_type = _detect_toc_page_type(normalized)
                if page_type is None:
                    continue
                heading_bottom = line.bbox.y1
                if best_match is None or heading_bottom < best_match[1]:
                    best_match = (page_type, heading_bottom)
        if best_match is not None:
            contexts.append(
                TocPageContext(page=page, page_type=best_match[0], heading_bottom_y=best_match[1])
            )

    return contexts


def _right_column_page_number_span(
    line: PdfTextLine,
    *,
    min_x_offset: float = 100.0,
) -> PdfTextSpan | None:
    """Return the rightmost numeric-only span that looks like a page-number column."""

    if not line.spans:
        return None
    indent_x = line.bbox.x0
    for span in reversed(line.spans):
        span_text = _clean_text(span.text)
        if not NUMERIC_ONLY_RE.match(span_text):
            continue
        if span.bbox.x0 <= indent_x + min_x_offset:
            continue
        return span
    return None


def _right_edge_page_number_span(line: PdfTextLine) -> PdfTextSpan | None:
    """Return a column number only when it ends at the row's right edge.

    An interior Roman-numeral letter can look numeric to the shared parser,
    but cannot establish a page-number column outlier for R018.
    """
    span = _right_column_page_number_span(line)
    if span is None or span.bbox.x1 < line.bbox.x1 - 1.0:
        return None
    return span


def _extract_page_number_from_spans(
    line: PdfTextLine, *, require_right_edge: bool = False
) -> tuple[str | None, float | None]:
    span = (
        _right_edge_page_number_span(line)
        if require_right_edge
        else _right_column_page_number_span(line)
    )
    if span is None:
        return None, None
    return _clean_text(span.text), span.bbox.x1


def _page_number_right_x_for_token(line: PdfTextLine, token: str) -> float:
    for span in reversed(line.spans):
        if token in span.text:
            return span.bbox.x1
    return line.bbox.x1


def _line_reaches_page_number_column(line: PdfTextLine) -> bool:
    """True when the line's right edge sits in the TOC page-number column band."""

    return (line.bbox.x1 - line.bbox.x0) >= RIGHT_COLUMN_MIN_X_OFFSET_PT or (
        line.bbox.x1 >= line.bbox.x0 + 100 and line.bbox.x1 >= 480.0
    )


def _extract_trailing_right_column_page_number(
    line: PdfTextLine, cleaned_text: str
) -> tuple[str | None, float | None]:
    """Extract a single-space trailing page number when geometry confirms the column.

    NJIT requires a right-aligned page number; leaders (Q052) are a separate
    consistency check. Missing leaders must not make a visible trailing page
    number look "missing" when it occupies the right-hand column.
    """

    if not _line_reaches_page_number_column(line):
        return None, None
    match = TRAILING_RIGHT_COLUMN_PAGE_NUM_RE.match(cleaned_text)
    if match is None:
        return None, None
    body = match.group("body").strip()
    token = match.group("num")
    # Reject bare section numbers or tiny stubs ("3.3 40", "Ch 1").
    if SECTION_NUMBER_ONLY_RE.match(body):
        return None, None
    if len(body) < PREFIX_ENTRY_MIN_LEN:
        return None, None
    if not any(ch.isalpha() for ch in body):
        return None, None
    return token, _page_number_right_x_for_token(line, token)


def _extract_page_number_token(
    line: PdfTextLine, cleaned_text: str, *, require_right_edge: bool = False
) -> tuple[str | None, float | None]:
    match = PAGE_NUMBER_TOKEN_RE.search(cleaned_text)
    if match is not None:
        token = match.group("num")
        right_x = _page_number_right_x_for_token(line, token)
        return token, right_x
    span_token = _extract_page_number_from_spans(line, require_right_edge=require_right_edge)
    if span_token[0] is not None:
        return span_token
    return _extract_trailing_right_column_page_number(line, cleaned_text)


def _line_mid_y(line: PdfTextLine) -> float:
    # Glyph boxes can have different heights even when PDF text origins share
    # one visual baseline. Prefer the extracted origin for TOC column grouping;
    # box centers are only a fallback for synthetic/older layout models.
    if line.baseline_y is not None:
        return line.baseline_y
    return (line.bbox.y0 + line.bbox.y1) / 2.0


def _line_text_for_toc(line: PdfTextLine) -> str:
    """Prefer geometry-aware span joining so section numbers are not glued to titles."""

    if line.spans:
        joined = join_content_span_texts(line.spans).strip()
        if joined:
            return joined
    return line.text.replace("\u00a0", " ").strip()


def _merge_baseline_group_to_line(group: list[PdfTextLine]) -> PdfTextLine:
    """Merge same-baseline TOC column fragments into one left-to-right visual row.

    PyMuPDF frequently emits section number, title, and page number as separate
    ``PdfTextLine`` objects that share a baseline. Concatenating without restoring
    inter-column spaces yields glued tokens such as ``3.3.3Geometric`` and leaves
    the page-number column unpaired from the title.
    """

    ordered = sorted(group, key=lambda line: (line.bbox.x0, line.bbox.y0))
    spans: list[PdfTextSpan] = []
    text_parts: list[str] = []
    prev_x1: float | None = None
    for line in ordered:
        piece = _line_text_for_toc(line)
        if not piece:
            continue
        if text_parts and prev_x1 is not None:
            if not text_parts[-1].endswith(" ") and not piece.startswith(" "):
                text_parts.append(" ")
        text_parts.append(piece)
        spans.extend(line.spans)
        prev_x1 = line.bbox.x1
    merged_text = "".join(text_parts).strip()
    bbox = BBox(
        x0=min(line.bbox.x0 for line in ordered),
        y0=min(line.bbox.y0 for line in ordered),
        x1=max(line.bbox.x1 for line in ordered),
        y1=max(line.bbox.y1 for line in ordered),
    )
    return PdfTextLine(spans=spans or ordered[0].spans, bbox=bbox, text=merged_text)


def _assemble_same_baseline_toc_rows(
    lines: list[PdfTextLine], *, y_tolerance: float = SAME_BASELINE_Y_TOLERANCE_PT
) -> list[PdfTextLine]:
    """Group TOC/list lines that share a baseline into visual rows."""

    if not lines:
        return []
    ordered = sorted(lines, key=lambda line: (_line_mid_y(line), line.bbox.x0))
    groups: list[list[PdfTextLine]] = []
    current: list[PdfTextLine] = []
    current_mid: float | None = None
    for line in ordered:
        mid = _line_mid_y(line)
        if current_mid is None or abs(mid - current_mid) <= y_tolerance:
            current.append(line)
            current_mid = mid if current_mid is None else (current_mid * 0.7 + mid * 0.3)
        else:
            groups.append(current)
            current = [line]
            current_mid = mid
    if current:
        groups.append(current)
    return [_merge_baseline_group_to_line(group) for group in groups]

def _is_leader_page_fragment_line(cleaned_text: str) -> bool:
    """True when a line carries leaders and a trailing page number but is not an entry."""

    if PAGE_NUMBER_TOKEN_RE.search(cleaned_text) is None:
        return False
    return not _likely_entry_line(cleaned_text, has_page_number_signal=True)


def _apply_auxiliary_page_number(entry: TocEntryLine, aux_line: PdfTextLine) -> None:
    cleaned = _clean_text(aux_line.text)
    token, right_x = _extract_page_number_token(aux_line, cleaned)
    if token is None:
        token = cleaned
        right_x = aux_line.bbox.x1
    entry.page_number_token = token
    entry.page_number_right_x = right_x if right_x is not None else aux_line.bbox.x1
    entry.page_number_line = aux_line
    if not entry.has_leader_dots and _has_leader_dot_pattern(cleaned):
        entry.has_leader_dots = True


def _looks_like_wrap_continuation(cleaned_text: str) -> bool:
    """True for mid-entry wrap fragments (hyphen tails / lowercase run-ons)."""

    if not cleaned_text:
        return False
    if cleaned_text.endswith("-") or cleaned_text.endswith("\u2010"):
        return True
    return cleaned_text[0].islower()


def _has_expression_continuation_start(cleaned_text: str) -> bool:
    """An equation continuation is distinct from an unmarked new title."""

    stripped = cleaned_text.lstrip()
    return bool(stripped and stripped[0] in "=+-−–—")


def _has_prefix_entry_shape(cleaned_text: str) -> bool:
    upper = cleaned_text.upper()
    return bool(PREFIX_ENTRY_RE.match(upper) or NUMERIC_PREFIX_RE.match(cleaned_text))


def _has_entry_identifier(cleaned_text: str) -> bool:
    """Recognize a possible numbered or named entry start in extracted text."""

    return _has_prefix_entry_shape(cleaned_text) or _has_lettered_or_abbreviated_identifier(
        cleaned_text
    )


def _has_lettered_or_abbreviated_identifier(cleaned_text: str) -> bool:
    return bool(
        LETTERED_SECTION_PREFIX_RE.match(cleaned_text.upper())
        or ROMAN_SECTION_PREFIX_RE.match(cleaned_text)
        or ABBREVIATED_LIST_ENTRY_RE.match(cleaned_text)
    )


def _starts_independent_logical_entry(
    text: str, parent_text: str, page_type: str, *, continues_hanging_row: bool = False,
) -> bool:
    """Stop at explicit entry starts while retaining numeric title continuations.

    A number at the start of a Figure/Table title can be ordinary title text
    on a hanging list row. Numeric TOC starts and numeric-to-numeric list
    starts that advance the list sequence are independent; lettered appendix
    and word prefixes are explicit boundaries in every TOC/List type.
    """

    if _has_lettered_or_abbreviated_identifier(text) or PREFIX_ENTRY_RE.match(text):
        return True
    follower_number = NUMERIC_PREFIX_RE.match(text)
    if follower_number is None:
        return False
    if page_type == "table_of_contents":
        return True
    if continues_hanging_row and follower_number.group().strip().rstrip(".").isdecimal():
        # A lone integer on an already established hanging indent can be
        # the start of a wrapped measurement. Explicit or dotted entry IDs
        # still start a new entry.
        return False
    following_title = text[follower_number.end() :].lstrip()
    if re.match(r"^[A-Z][a-z]{2,}\b", following_title):
        # An entry title can begin after a number even when a List switches
        # numbering styles or has an out-of-order entry. Require a title-like
        # word: a short unit such as W, Pa, or MHz after a decimal is not one.
        return True
    parent_number = NUMERIC_PREFIX_RE.match(parent_text)
    if parent_number is None:
        return False
    # A list's numbered entries progress through their figure/table labels.
    # A scalar at the start of a wrapped mathematical caption (for example
    # 0.417 after 5.12) is not evidence of a new list entry.
    def parts(match: re.Match[str]) -> tuple[int, ...]:
        return tuple(int(part) for part in match.group().strip().rstrip(".").split("."))

    return parts(follower_number) > parts(parent_number)


_LEADER_DOT_SPAN_RE = re.compile(r"[.…][.…\s]*[.…]")


def _has_leader_dot_pattern(cleaned_text: str) -> bool:
    """True when *cleaned_text* ends in a visible dot/ellipsis leader run.

    PDF text extraction renders TOC leader runs inconsistently: some are a
    literal run of ASCII periods, others are Unicode horizontal-ellipsis
    characters (``…``, each visually three dots), and wrapped (two-line)
    entries often extract as two separate dot clusters joined by a single
    space (the second line's leader run does not visually start flush with
    the first). All of these are the same visible leader-dot pattern to a
    reader; only literal ASCII runs were previously recognized, which
    produced false "missing dots" findings for any entry using an
    ellipsis-based or wrap-split leader. A run is scored by visible dot
    weight (an ellipsis counts as 3, a period as 1) rather than raw
    character count, so a short two-ellipsis leader (``……``, six visible
    dots) is not missed just because it is only two characters wide.
    """
    if "..." in cleaned_text or cleaned_text.rstrip().endswith("...."):
        return True
    for match in _LEADER_DOT_SPAN_RE.finditer(cleaned_text):
        dot_weight = sum(3 if ch == "…" else 1 for ch in match.group() if ch in ".…")
        if dot_weight >= 3:
            return True
    return False


def _likely_entry_line(cleaned_text: str, *, has_page_number_signal: bool = False) -> bool:
    if is_toc_export_metadata_line(cleaned_text):
        return False
    if NUMERIC_ONLY_RE.match(cleaned_text):
        return False
    has_prefix = _has_prefix_entry_shape(cleaned_text)
    if (
        cleaned_text.endswith(".")
        and len(cleaned_text.split()) > 6
        and not _has_leader_dot_pattern(cleaned_text)
        and not has_prefix
        and not _looks_like_wrap_continuation(cleaned_text)
    ):
        return False
    min_len = (
        PREFIX_ENTRY_MIN_LEN
        if has_prefix
        or has_page_number_signal
        or _looks_like_wrap_continuation(cleaned_text)
        else DEFAULT_ENTRY_MIN_LEN
    )
    if len(cleaned_text) < min_len:
        return False
    if (
        cleaned_text.isupper()
        and len(cleaned_text.split()) <= 4
        and not has_page_number_signal
        and not has_prefix
    ):
        return False
    return bool(ENTRY_START_RE.match(cleaned_text))


def _is_list_heading_line(cleaned_text: str) -> bool:
    return classify_toc_heading_line(cleaned_text) is not None


def _y_tolerance_for_pairing(entry_indent_x: float, numeric_x0: float) -> float:
    if numeric_x0 >= entry_indent_x + RIGHT_COLUMN_MIN_X_OFFSET_PT:
        return PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT
    return PAGE_NUMBER_LINE_Y_TOLERANCE_PT


def _pair_right_column_number(
    entry: TocEntryLine,
    auxiliary_lines: list[PdfTextLine],
    candidate_rows: list[TocEntryLine],
    *,
    max_y_gap: float,
    require_below: bool = False,
    relax_y_tolerance: bool = False,
) -> PdfTextLine | None:
    best_idx: int | None = None
    best_delta = 9999.0
    for idx, aux_line in enumerate(auxiliary_lines):
        y_delta = aux_line.bbox.y0 - entry.line.bbox.y0
        if require_below and y_delta < 0:
            continue
        y_delta_abs = abs(y_delta)
        if y_delta_abs > max_y_gap:
            continue
        if aux_line.bbox.x0 <= (entry.indent_x + 100):
            continue
        tolerance = max_y_gap if relax_y_tolerance else _y_tolerance_for_pairing(
            entry.indent_x,
            aux_line.bbox.x0,
        )
        if y_delta_abs > tolerance:
            continue
        # A looser wrapped-row tolerance must not take a number with an
        # equally close or closer visual title row.
        if any(
            other is not entry
            and (
                (
                    other.line.bbox.x1 < aux_line.bbox.x0
                    and abs(aux_line.bbox.y0 - other.line.bbox.y0) <= y_delta_abs
                )
                or (
                    entry.line.bbox.y0 < other.line.bbox.y0 <= aux_line.bbox.y0
                    and _has_entry_identifier(other.cleaned_text)
                )
            )
            for other in candidate_rows
        ):
            continue
        if y_delta_abs == best_delta:
            best_idx = None
        elif y_delta_abs < best_delta:
            best_delta = y_delta_abs
            best_idx = idx
    if best_idx is None:
        return None
    return auxiliary_lines.pop(best_idx)


def _make_entry_from_line(
    line: PdfTextLine, cleaned: str, *, require_right_edge: bool = False
) -> TocEntryLine:
    page_num, page_right_x = _extract_page_number_token(
        line, cleaned, require_right_edge=require_right_edge
    )
    return TocEntryLine(
        line=line,
        cleaned_text=cleaned,
        page_number_token=page_num,
        page_number_right_x=page_right_x,
        indent_x=line.bbox.x0,
        has_leader_dots=_has_leader_dot_pattern(cleaned),
        page_number_line=line if page_num is not None else None,
    )


def _strip_trailing_page_token(text: str, token: str | None) -> str:
    if not token:
        return text
    stripped = text.rstrip()
    if stripped.endswith(token):
        stripped = stripped[: -len(token)].rstrip()
    return stripped


def _merge_wrapped_entries(
    entries: list[TocEntryLine],
    auxiliary_lines: list[PdfTextLine],
) -> list[TocEntryLine]:
    if not entries:
        return entries

    merged: list[TocEntryLine] = []
    sorted_entries = sorted(entries, key=lambda entry: (entry.line.bbox.y0, entry.line.bbox.x0))
    idx = 0
    while idx < len(sorted_entries):
        entry = sorted_entries[idx]
        idx += 1
        if entry.page_number_token is None and _has_prefix_entry_shape(entry.cleaned_text):
            # Only numbered/typed entry starts may absorb wrap continuations /
            # below-row page numbers. Mid-wrap fragments must not steal tokens.
            matched = _pair_right_column_number(
                entry,
                auxiliary_lines,
                sorted_entries,
                max_y_gap=WRAPPED_ENTRY_Y_GAP_PT,
                require_below=True,
                relax_y_tolerance=True,
            )
            if matched is not None:
                _apply_auxiliary_page_number(entry, matched)
                entry.is_wrapped = True
            else:
                prev_y = entry.line.bbox.y0
                while idx < len(sorted_entries):
                    nxt = sorted_entries[idx]
                    y_gap = nxt.line.bbox.y0 - prev_y
                    if y_gap > WRAPPED_ENTRY_Y_GAP_PT:
                        break
                    if _has_entry_identifier(nxt.cleaned_text):
                        break
                    cont = _strip_trailing_page_token(
                        nxt.cleaned_text, nxt.page_number_token
                    )
                    if cont:
                        entry.cleaned_text = f"{entry.cleaned_text} {cont}".strip()
                        entry.is_wrapped = True
                        entry.line = PdfTextLine(
                            spans=list(entry.line.spans) + list(nxt.line.spans),
                            bbox=BBox(
                                x0=min(entry.line.bbox.x0, nxt.line.bbox.x0),
                                y0=min(entry.line.bbox.y0, nxt.line.bbox.y0),
                                x1=max(entry.line.bbox.x1, nxt.line.bbox.x1),
                                y1=max(entry.line.bbox.y1, nxt.line.bbox.y1),
                            ),
                            text=entry.cleaned_text,
                        )
                    if nxt.has_leader_dots:
                        entry.has_leader_dots = True
                    if nxt.page_number_token is not None:
                        entry.page_number_token = nxt.page_number_token
                        entry.page_number_right_x = nxt.page_number_right_x
                        entry.page_number_line = nxt.page_number_line
                        idx += 1
                        break
                    prev_y = nxt.line.bbox.y0
                    idx += 1
                if entry.page_number_token is None:
                    matched = _pair_right_column_number(
                        entry,
                        auxiliary_lines,
                        sorted_entries[idx:],
                        max_y_gap=WRAPPED_ENTRY_Y_GAP_PT,
                        require_below=True,
                        relax_y_tolerance=True,
                    )
                    if matched is not None:
                        _apply_auxiliary_page_number(entry, matched)
                        entry.is_wrapped = True
        merged.append(entry)
    return merged


def _drop_merge_orphans(entries: list[TocEntryLine]) -> list[TocEntryLine]:
    retained: list[TocEntryLine] = []
    for entry in entries:
        if entry.page_number_token is not None:
            retained.append(entry)
            continue
        if _likely_entry_line(entry.cleaned_text):
            retained.append(entry)
            continue
        if _has_prefix_entry_shape(entry.cleaned_text) and len(entry.cleaned_text) >= (
            PREFIX_ENTRY_MIN_LEN
        ):
            retained.append(entry)
    return retained


def collect_toc_visual_rows(
    context: TocPageContext, *, require_right_edge: bool = False
) -> list[PdfTextLine]:
    """Return the page's entry-region lines assembled into visual rows.

    Rows are ordered top to bottom; same-baseline column fragments (section
    number, title, leader, page number) are merged left to right with their
    spans (and any per-character geometry) preserved.
    """

    page_width = context.page.width or 612.0
    max_entry_left = page_width * TOC_ENTRY_MAX_LEFT_FRACTION
    ordered_lines: list[PdfTextLine] = []
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= context.heading_bottom_y + 2:
                continue
            raw_cleaned = _clean_text(_line_text_for_toc(line))
            if (
                line.bbox.x0 >= max_entry_left
                and not NUMERIC_ONLY_RE.match(raw_cleaned)
                and not _is_leader_page_fragment_line(raw_cleaned)
                and not is_toc_structural_column_label(raw_cleaned)
            ):
                # Exclude right-margin annotations before same-baseline row
                # assembly. Filtering only after assembly lets comments such as
                # reviewer names become glued into a legitimate TOC entry.
                continue
            ordered_lines.append(line)
    ordered_lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))
    # Rebuild visual TOC rows from same-baseline column fragments before
    # classifying entries / pairing page numbers.
    # R055 sees some number/title fragments with baselines a few points apart.
    # Keep the wider grouping local to its right-edge parsing mode.
    return _assemble_same_baseline_toc_rows(
        ordered_lines,
        y_tolerance=5.0 if require_right_edge else SAME_BASELINE_Y_TOLERANCE_PT,
    )


def extract_toc_entry_lines(
    context: TocPageContext,
    *,
    require_right_edge: bool = False,
) -> list[TocEntryLine]:
    """Extract likely entry lines below TOC/List heading on a page."""

    page_width = context.page.width or 612.0
    max_entry_left = page_width * TOC_ENTRY_MAX_LEFT_FRACTION
    ordered_lines = collect_toc_visual_rows(context, require_right_edge=require_right_edge)

    entries: list[TocEntryLine] = []
    auxiliary_lines: list[PdfTextLine] = []
    for line in ordered_lines:
        cleaned = _clean_text(_line_text_for_toc(line))
        if _is_list_heading_line(cleaned):
            continue
        if is_toc_structural_column_label(cleaned):
            continue
        if NUMERIC_ONLY_RE.match(cleaned):
            auxiliary_lines.append(line)
            continue
        if _is_leader_page_fragment_line(cleaned):
            auxiliary_lines.append(line)
            continue
        # Margin notes / annotation fragments in the right half are not TOC rows.
        if line.bbox.x0 >= max_entry_left and not _has_prefix_entry_shape(cleaned):
            continue
        page_num, page_right_x = _extract_page_number_token(
            line, cleaned, require_right_edge=require_right_edge
        )
        has_signal = page_num is not None or page_right_x is not None
        if not _likely_entry_line(cleaned, has_page_number_signal=has_signal):
            continue
        entries.append(_make_entry_from_line(line, cleaned, require_right_edge=require_right_edge))

    unused_auxiliary = sorted(auxiliary_lines, key=lambda line: (line.bbox.y0, line.bbox.x0))
    for entry in entries:
        if entry.page_number_right_x is not None:
            continue
        matched = _pair_right_column_number(
            entry,
            unused_auxiliary,
            entries,
            max_y_gap=PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT,
        )
        if matched is not None:
            _apply_auxiliary_page_number(entry, matched)

    entries = _merge_wrapped_entries(entries, unused_auxiliary)
    entries = _drop_merge_orphans(entries)
    entries.sort(key=lambda entry: (entry.line.bbox.y0, entry.line.bbox.x0))
    return entries


_GLUED_FINAL_PAGE_NUMBER_RE = re.compile(r"(?<![0-9])\.(?P<num>[0-9]{1,4})$")
LOGICAL_WRAP_Y_GAP_PT = 21.0
LOGICAL_WRAP_MIN_INDENT_PT = 8.0
LOGICAL_WRAP_MAX_ROWS = 8


def _logical_page_column_edge(entries: list[TocEntryLine]) -> float | None:
    """Use the page's own numbered entries to locate its page-number column."""
    edges = [
        entry.page_number_right_x
        for entry in entries
        if entry.page_number_right_x is not None
    ]
    return median(edges) if len(edges) >= 3 else None


def _append_logical_row(entry: TocEntryLine, row: PdfTextLine, text: str) -> None:
    entry.cleaned_text = f"{entry.cleaned_text} {text}".strip()
    entry.line = PdfTextLine(
        spans=list(entry.line.spans) + list(row.spans),
        bbox=_union_bbox(entry.line.bbox, row.bbox),
        text=entry.cleaned_text,
    )
    entry.has_leader_dots |= _has_leader_dot_pattern(text)
    entry.is_wrapped = True


def _is_first_figure_wrap_with_integer(
    first: PdfTextLine,
    follower: PdfTextLine,
    following: PdfTextLine,
    column: float,
) -> bool:
    """Distinguish an integer in a title from a new figure identifier."""
    # A comma and coordinating conjunction mark an enumeration within the title.
    if not re.match(r"^\d+ \S+, (?:and|or)\b", _row_text(follower)):
        return False
    if _row_text(first).endswith((".", "?", "!")):
        return False
    first_label = SECTION_NUMBER_PREFIX_RE.match(_row_text(first))
    following_label = SECTION_NUMBER_PREFIX_RE.match(_row_text(following))
    if first_label is None or following_label is None:
        return False
    first_parts = first_label[1].split(".")
    following_parts = following_label[1].split(".")
    folio = _right_edge_page_number_span(follower)
    return (
        len(first_parts) > 1
        and first_parts[:-1] == following_parts[:-1]
        and int(following_parts[-1]) == int(first_parts[-1]) + 1
        and abs(following.bbox.x0 - first.bbox.x0) <= INDENT_CLUSTER_TOLERANCE_PT
        and following.bbox.y0 - follower.bbox.y1 <= WRAPPED_ENTRY_Y_GAP_PT
        and follower.bbox.y0 - first.bbox.y0 <= WRAPPED_ENTRY_Y_GAP_PT
        and folio is not None
        and folio.text.strip().isdecimal()
        and abs(folio.bbox.x1 - column) <= RIGHT_EDGE_TOLERANCE_PT
    )


def extract_toc_logical_entry_lines(
    context: TocPageContext,
    *,
    require_right_edge: bool = False,
    recover_displaced_leader_folio: bool = False,
) -> list[TocEntryLine]:
    """Repair demonstrable wrapped entries for R018/R024/R040.

    The ordinary extractor deliberately filters rows that do not resemble a
    standalone entry. A wrapped title can contain exactly such a row, or a
    numeral inside its first row can be mistaken for the page number. Normally, it rejoins hanging rows with a terminal folio in the page's established column. P018's missing-number check can also use a final
    hanging row's own right-side dot leaders when the column estimate is
    contaminated. Other rules keep the established entry geometry.
    """
    entries = extract_toc_entry_lines(context, require_right_edge=require_right_edge)
    rows = collect_toc_visual_rows(context, require_right_edge=require_right_edge)
    column_edge = _logical_page_column_edge(entries)
    figure_folio_column = (
        _trusted_folio_column(entries)
        if recover_displaced_leader_folio and context.page_type == "list_of_figures"
        else None
    )
    if not entries or not rows:
        return entries

    repaired: list[TocEntryLine] = []
    absorbed_y: set[float] = set()
    for original in entries:
        first_y = original.line.bbox.y0
        if first_y in absorbed_y:
            continue
        first_index = next(
            (index for index, row in enumerate(rows) if abs(row.bbox.y0 - first_y) < 0.5),
            None,
        )
        if first_index is None:
            repaired.append(original)
            continue
        first = rows[first_index]
        first_text = _row_text(first)
        # Some list PDFs extract the number and title without a separating
        # space. In right-edge mode, retain that numbered start so its wrapped
        # page token can be attached to the same logical entry.
        if not (
            _has_prefix_entry_shape(first_text)
            or (
                require_right_edge
                and re.match(r"^\d+(?:[.\-]\d+)*[A-Z]", first_text)
            )
        ):
            repaired.append(original)
            continue

        # A page number glued to the final title span ("title.124") is
        # accepted only at the page's established number-column edge.
        if original.page_number_token is None and column_edge is not None:
            glued = _GLUED_FINAL_PAGE_NUMBER_RE.search(first_text)
            if glued and abs(first.bbox.x1 - column_edge) <= RIGHT_EDGE_TOLERANCE_PT:
                original.page_number_token = glued.group("num")
                original.page_number_right_x = first.bbox.x1
                original.page_number_line = first
                repaired.append(original)
                continue

        # A numeral inside a title can look like a trailing page token. It
        # is only reconsidered when its edge disagrees with the page column
        # and a following indented row supplies the actual page number.
        weak_first_number = (
            original.page_number_token is not None
            and column_edge is not None
            and original.page_number_right_x is not None
            and abs(original.page_number_right_x - column_edge) > RIGHT_EDGE_TOLERANCE_PT
        )
        if original.page_number_token is not None and not weak_first_number:
            repaired.append(original)
            continue

        continuation_rows: list[PdfTextLine] = []
        final_number: str | None = None
        final_edge: float | None = None
        previous = first
        for row_index, follower in enumerate(rows[first_index + 1 :], first_index + 1):
            gap = follower.bbox.y0 - previous.bbox.y0
            if gap < 0 or gap > LOGICAL_WRAP_Y_GAP_PT:
                break
            text = _row_text(follower)
            if NUMERIC_ONLY_RE.fullmatch(text):
                if (
                    continuation_rows
                    and gap <= PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT
                    and follower.bbox.x0 >= first.bbox.x0 + RIGHT_COLUMN_MIN_X_OFFSET_PT
                    and not any(
                        other is not original
                        and other.page_number_line is not None
                        and other.page_number_line.bbox == follower.bbox
                        and not any(row.bbox.y0 == other.line.bbox.y0 for row in continuation_rows)
                        for other in entries
                    )
                    and (
                        (
                            column_edge is None
                            and follower.bbox.x1 >= context.page.width - 100.0
                        )
                        or (
                            column_edge is not None
                            and abs(follower.bbox.x1 - column_edge) <= RIGHT_EDGE_TOLERANCE_PT
                        )
                    )
                ):
                    final_number, final_edge = text, follower.bbox.x1
                    continuation_rows.append(follower)
                break
            if (
                _is_non_entry_row(text)
                or follower.bbox.x0 < first.bbox.x0 + LOGICAL_WRAP_MIN_INDENT_PT
                or (
                    _starts_independent_logical_entry(
                        text,
                        first_text,
                        context.page_type,
                        continues_hanging_row=(
                            bool(continuation_rows)
                            and abs(follower.bbox.x0 - previous.bbox.x0)
                            <= WRAPPED_CONTINUATION_MIN_TOLERANCE_PT
                            and previous.bbox.x1 >= first.bbox.x1 - RIGHT_EDGE_TOLERANCE_PT
                        ),
                    )
                    and not (
                        not continuation_rows
                        and figure_folio_column is not None
                        and row_index + 1 < len(rows)
                        and _is_first_figure_wrap_with_integer(
                            first, follower, rows[row_index + 1], figure_folio_column
                        )
                    )
                )
                or len(continuation_rows) >= LOGICAL_WRAP_MAX_ROWS
            ):
                break
            continuation_rows.append(follower)
            token, edge = _extract_page_number_token(
                follower, text, require_right_edge=require_right_edge
            )
            if token is None and figure_folio_column is not None:
                # The visible right-edge folio can share its PDF text span
                # with the closing punctuation of a wrapped figure title.
                glued = _GLUED_FINAL_PAGE_NUMBER_RE.search(text)
                if (
                    glued
                    and text[:glued.start()].endswith(")")
                    and abs(follower.bbox.x1 - figure_folio_column) <= RIGHT_EDGE_TOLERANCE_PT
                ):
                    final_number, final_edge = glued["num"], follower.bbox.x1
                    break
            if token is not None and (
                (
                    column_edge is None
                    and edge is not None
                    and edge >= context.page.width - 100.0
                )
                or (
                    edge is not None
                    and column_edge is not None
                    and abs(edge - column_edge) <= RIGHT_EDGE_TOLERANCE_PT
                )
                or (
                    # A wrapped title's final hanging line can have its own
                    # terminal leader and folio even when earlier fragments
                    # distort the page-wide column estimate. The leader,
                    # right-side token and non-entry start establish ownership
                    # without relaxing column alignment for bare numbers.
                    recover_displaced_leader_folio
                    # One hanging row alone could be a following entry whose
                    # identifier was lost in extraction. Require an earlier
                    # title continuation before using its final leader row.
                    and len(continuation_rows) >= 2
                    and edge is not None
                    and edge >= context.page.width - 100.0
                    and _has_leader_dot_pattern(text)
                    and not _has_entry_identifier(text)
                    and _has_expression_continuation_start(text)
                    and abs(follower.bbox.x0 - continuation_rows[-2].bbox.x0)
                    <= INDENT_CLUSTER_TOLERANCE_PT
                )
            ):
                final_number, final_edge = token, edge
                break
            previous = follower

        if final_number is None or final_edge is None:
            repaired.append(original)
            continue
        logical = _make_entry_from_line(first, first_text)
        for follower in continuation_rows:
            _append_logical_row(logical, follower, _row_text(follower))
            absorbed_y.add(follower.bbox.y0)
        logical.page_number_token = final_number
        logical.page_number_right_x = final_edge
        logical.page_number_line = continuation_rows[-1] if continuation_rows else first
        repaired.append(logical)
    return repaired


def group_toc_page_runs(contexts: list[TocPageContext]) -> list[TocPageRun]:
    """Group consecutive pages of the same TOC/List type into runs."""

    by_type: dict[str, list[TocPageContext]] = {}
    for context in contexts:
        by_type.setdefault(context.page_type, []).append(context)

    runs: list[TocPageRun] = []
    for page_type, typed_contexts in by_type.items():
        sorted_contexts = sorted(typed_contexts, key=lambda ctx: ctx.page.page_number)
        current: list[TocPageContext] = []
        for ctx in sorted_contexts:
            page_number = ctx.page.page_number
            if not current or page_number <= current[-1].page.page_number + 1:
                current.append(ctx)
            else:
                if current:
                    runs.append(TocPageRun(page_type, current))
                current = [ctx]
        if current:
            runs.append(TocPageRun(page_type, current))
    return runs


def _parse_toc_hierarchy_level(cleaned_text: str) -> int | None:
    """Return 1-based hierarchy depth for structurally classified TOC entries.

    Numeric: ``"1 INTRODUCTION"`` → 1, ``"1.1 Background"`` → 2,
    ``"1.1.1 Detail"`` → 3.

    Lettered appendix subsections: ``"A.1 Bounds"`` → 2, ``"B.2.1 Note"`` → 3.

    Word-prefix chapter / back-matter roots (``APPENDIX …``, ``CHAPTER …``,
    ``REFERENCES``, …) → 1 so they are never peer-compared with lettered or
    numeric subsections.

    Unclassified titles return ``None`` and are excluded from indent-outlier
    comparison (ambiguous hierarchy must not produce unsupported warnings).
    """
    m = SECTION_NUMBER_PREFIX_RE.match(cleaned_text)
    if m is not None:
        return m.group(1).count(".") + 1

    m = LETTERED_SECTION_PREFIX_RE.match(cleaned_text)
    if m is not None:
        return m.group(1).count(".") + 1

    if TOP_LEVEL_TOC_WORD_PREFIX_RE.match(cleaned_text):
        return 1

    return None


def _find_hierarchy_indent_outliers(
    entries: list[TocEntryLine],
) -> list[tuple[TocEntryLine, float]]:
    """Find entries whose left indent diverges from their same-level peers.

    Entries are grouped by hierarchy level so level-2 entries are only compared
    against other level-2 entries — never against level-1 entries.  A level group
    needs at least MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON entries before any
    outlier can be flagged, and the deviation must exceed HIERARCHY_INDENT_TOLERANCE_PT.

    Unclassified (``None``-level) entries are never compared: mixing ambiguous
    fragments, appendix roots, and lettered subsections as a single peer set
    produced false positives on lettered-only TOC continuation pages.

    Returns a list of (entry, delta_pt) pairs for outliers, empty when none found.
    """
    by_level: dict[int, list[TocEntryLine]] = {}
    for entry in entries:
        level = _parse_toc_hierarchy_level(entry.cleaned_text)
        if level is None:
            continue
        by_level.setdefault(level, []).append(entry)

    outlier_pairs: list[tuple[TocEntryLine, float]] = []
    for level_entries in by_level.values():
        if len(level_entries) < MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON:
            continue
        indents = [e.indent_x for e in level_entries]
        med = median(indents)
        for entry in level_entries:
            delta = abs(entry.indent_x - med)
            if delta > HIERARCHY_INDENT_TOLERANCE_PT:
                outlier_pairs.append((entry, delta))
    return outlier_pairs


def _local_dot_conformity_score(
    entry: TocEntryLine,
    entries: list[TocEntryLine],
    entry_positions: dict[TocEntryLine, int],
) -> int:
    """Count this entry's immediate document-order neighbors (previous/next)
    that DO have leader dots -- 0, 1, or 2.

    A singleton non-dotted entry surrounded by dotted neighbors on both sides
    (score 2) is a cleaner, more representative single example of "this entry
    breaks the page's dotted pattern" than one that is part of a consecutive
    run of non-dotted entries (score 0 or 1), where the departure is shared
    and no single entry stands out as *the* example.
    """
    idx = entry_positions[entry]
    score = 0
    if idx - 1 >= 0 and entries[idx - 1].has_leader_dots:
        score += 1
    if idx + 1 < len(entries) and entries[idx + 1].has_leader_dots:
        score += 1
    return score


def _hierarchy_group_dot_conformity_ratio(
    entry: TocEntryLine, entries: list[TocEntryLine]
) -> float:
    """Return the fraction of *entry*'s same-hierarchy-level peers that have
    leader dots -- how strongly that level's own comparison group (the same
    grouping used by _find_hierarchy_indent_outliers) conforms to the dotted
    style. A level with too few peers for a meaningful pattern (below
    MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON) scores 0.0, the lowest priority,
    since no real "dominant pattern" can be established there.
    """
    level = _parse_toc_hierarchy_level(entry.cleaned_text)
    peers = [e for e in entries if _parse_toc_hierarchy_level(e.cleaned_text) == level]
    if len(peers) < MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON:
        return 0.0
    return sum(1 for e in peers if e.has_leader_dots) / len(peers)


def _select_worst_leader_dots_entry(
    entries: list[TocEntryLine],
    missing_dots_entries: list[TocEntryLine],
    entry_positions: dict[TocEntryLine, int],
) -> TocEntryLine:
    """Pick the missing-dots entry that best demonstrates departure from the
    page's dominant leader-dot pattern, instead of always the first affected
    entry in document order.

    Mirrors misaligned_page_number_column's magnitude-based worst-case
    selection (deviation from a median, argmax): ranked by
    (local isolation, hierarchy-group conformity ratio, document order)
    descending --

    1. Local isolation (_local_dot_conformity_score): an entry whose immediate
       neighbors both have dots stands out more clearly than one buried in a
       run of non-dotted entries.
    2. Hierarchy-group conformity ratio (_hierarchy_group_dot_conformity_ratio):
       ties go to the entry whose own hierarchy level has the stronger dotted
       majority -- a bigger departure from *that* level's dominant pattern.
    3. Document order (lowest index): final deterministic tiebreak so ties
       never depend on set/dict iteration order.
    """

    def sort_key(entry: TocEntryLine) -> tuple[int, float, int]:
        return (
            _local_dot_conformity_score(entry, entries, entry_positions),
            _hierarchy_group_dot_conformity_ratio(entry, entries),
            -entry_positions[entry],
        )

    return max(missing_dots_entries, key=sort_key)


def _row_text(row: PdfTextLine) -> str:
    return _clean_text(_line_text_for_toc(row))


def _row_completes_entry(row: PdfTextLine, text: str) -> bool:
    return _has_leader_dot_pattern(text) or _extract_page_number_token(row, text)[0] is not None


def _is_non_entry_row(text: str) -> bool:
    return (
        not text
        or _is_list_heading_line(text)
        or is_toc_structural_column_label(text)
        or is_toc_export_metadata_line(text)
    )


def _union_bbox(first: BBox, second: BBox) -> BBox:
    return BBox(
        x0=min(first.x0, second.x0),
        y0=min(first.y0, second.y0),
        x1=max(first.x1, second.x1),
        y1=max(first.y1, second.y1),
    )


def _wrapped_title_continuations(
    rows: list[PdfTextLine], index: int
) -> list[PdfTextLine]:
    """Continuation rows of the numbered entry starting at ``rows[index]``.

    Returns an empty list unless the entry demonstrably ends (leader, page
    number, or a detached page-number row) within a few single-spaced rows.
    """

    continuations: list[PdfTextLine] = []
    previous = rows[index]
    for follower in rows[index + 1 :]:
        text = _row_text(follower)
        if follower.bbox.y0 - previous.bbox.y0 > WRAPPED_ENTRY_Y_GAP_PT:
            return []
        if NUMERIC_ONLY_RE.match(text):
            # A detached page number closes the entry; with no continuation yet
            # it belongs to the first row, which was therefore not wrapped.
            return continuations
        if (
            _is_non_entry_row(text)
            or _has_prefix_entry_shape(text)
            or _WRAPPED_CONTINUATION_STOP_RE.match(text)
        ):
            return []
        continuations.append(follower)
        if _row_completes_entry(follower, text):
            return continuations
        if len(continuations) >= WRAPPED_CONTINUATION_MAX_ROWS:
            return []
        previous = follower
    return []


class _WrappedMisalignment:
    """One wrapped continuation line that does not start under the title text."""

    def __init__(
        self,
        first_row: PdfTextLine,
        continuation: PdfTextLine,
        number_x: float,
        title_x: float,
        continuation_x: float,
        tolerance: float,
        exact: bool,
    ) -> None:
        self.first_row = first_row
        self.continuation = continuation
        self.number_x = number_x
        self.title_x = title_x
        self.continuation_x = continuation_x
        self.tolerance = tolerance
        self.exact = exact

    @property
    def signed_delta(self) -> float:
        """``continuation_x - title_x``: negative = left of the title text."""
        return self.continuation_x - self.title_x

    @property
    def alignment(self) -> str:
        if self.signed_delta > 0:
            return "right_of_title_text"
        if abs(self.continuation_x - self.number_x) <= self.tolerance:
            return "section_number"
        if self.continuation_x < self.number_x:
            return "left_of_section_number"
        return "between_section_number_and_title"


def _add_wrapped_title_alignment_finding(
    context: TocPageContext,
    rows: list[PdfTextLine],
    page_issue_findings: dict[str, AuditFinding],
) -> None:
    """R018: wrapped numbered TOC titles must not start left of title text.

    A continuation under the section number is a violation; additional
    second- or third-line indentation is accepted per the later reviewer
    clarification. The fallback title-start estimate is a lower bound, so a
    detected leftward deviation remains supported without exact glyph boxes.
    """

    violations: list[_WrappedMisalignment] = []
    for index, row in enumerate(rows):
        text = _row_text(row)
        match = SECTION_NUMBER_PREFIX_RE.match(text)
        if match is None or _row_completes_entry(row, text):
            continue
        label_len = len("".join(match.group(0).split()))
        number_x = visible_start_x(row)
        title_x, exact = title_text_start_x(row, label_len)
        if number_x is None or title_x is None or title_x <= number_x:
            continue
        size = row_font_size(row_glyphs(row))
        tolerance = max(
            WRAPPED_CONTINUATION_MIN_TOLERANCE_PT,
            WRAPPED_CONTINUATION_ALIGN_TOLERANCE_EM * size,
        )
        for continuation in _wrapped_title_continuations(rows, index):
            continuation_x = visible_start_x(continuation)
            if continuation_x is None:
                continue
            delta = continuation_x - title_x
            if delta < -tolerance:
                violations.append(
                    _WrappedMisalignment(
                        row, continuation, number_x, title_x, continuation_x, tolerance, exact
                    )
                )
    if not violations:
        return
    worst = max(violations, key=lambda item: abs(item.signed_delta))
    preview_entry = _make_entry_from_line(worst.first_row, _row_text(worst.first_row))
    details = _details_with_affected_entry_preview(
        {
            "page_number": str(context.page.page_number),
            "page_type": context.page_type,
            "issue_type": "wrapped_title_continuation_misaligned",
            "affected_entry_count": str(len({id(item.first_row) for item in violations})),
            "worst_delta_pt": f"{abs(worst.signed_delta):.1f}",
            "signed_delta_pt": f"{worst.signed_delta:.1f}",
            "title_text_start_x": f"{worst.title_x:.1f}",
            "continuation_start_x": f"{worst.continuation_x:.1f}",
            "continuation_alignment": worst.alignment,
            "measurement": "glyph" if worst.exact else "estimated_lower_bound",
            "confidence": "medium" if worst.exact else "low",
        },
        preview_entry,
    )
    details["bbox"] = format_bbox_detail(
        _union_bbox(worst.first_row.bbox, worst.continuation.bbox)
    )
    # One box per affected entry (its first row through its misaligned
    # continuation), so every entry that needs fixing is highlighted, not
    # only the one with the largest offset.
    entry_boxes: dict[int, BBox] = {}
    for item in violations:
        key = id(item.first_row)
        box = _union_bbox(item.first_row.bbox, item.continuation.bbox)
        entry_boxes[key] = _union_bbox(entry_boxes[key], box) if key in entry_boxes else box
    details["highlight_bboxes"] = " | ".join(
        format_bbox_detail(box) for box in sorted(entry_boxes.values(), key=lambda b: b.y0)
    )
    page_issue_findings["wrapped_title_continuation_misaligned"] = AuditFinding(
        rule_id="P018",
        severity=Severity.WARNING,
        page=context.page.page_number,
        message=(
            "A wrapped Table of Contents title continues on a line that does not "
            "start directly under the first line's title text."
        ),
        details=details,
    )


def _page_leader_layout(gaps: list[LeaderGap]) -> str:
    """Return ``grid``, ``typed``, or ``undetermined`` for a page's leaders.

    Grid-aligned leaders put every row's first dot on one common x-grid, so
    the first-dot positions agree modulo the leader pitch.
    """

    if len(gaps) < LEADER_GRID_MIN_ROWS:
        return "undetermined"
    pitch = median(gap.leader_pitch_pt for gap in gaps)
    if pitch <= 0:
        return "undetermined"
    residues = sorted(gap.leader_start_x % pitch for gap in gaps)
    wrap_gaps = [b - a for a, b in zip(residues, residues[1:])]
    wrap_gaps.append(residues[0] + pitch - residues[-1])
    spread = pitch - max(wrap_gaps)
    return "grid" if spread <= LEADER_GRID_MAX_SPREAD_PT else "typed"


def _allowed_title_leader_gap_pt(gap: LeaderGap, layout: str = "undetermined") -> float:
    in_cell_padding = max(0.0, gap.leader_pitch_pt - gap.dot_advance_pt) / 2.0
    grid_phase = 0.0 if layout == "typed" else gap.leader_pitch_pt
    return (
        gap.space_width_pt
        + grid_phase
        + in_cell_padding
        + LEADER_GAP_JITTER_EM * gap.font_size_pt
    )


def _next_title_row_carries_page_number(rows: list[PdfTextLine], index: int) -> PdfTextLine | None:
    """Return the following wrapped title row if it, not ``rows[index]``, ends the entry."""

    previous = rows[index]
    for follower in rows[index + 1 :]:
        text = _row_text(follower)
        if follower.bbox.y0 - previous.bbox.y0 > WRAPPED_ENTRY_Y_GAP_PT:
            return None
        if NUMERIC_ONLY_RE.match(text):
            return None
        if (
            _is_non_entry_row(text)
            or _has_prefix_entry_shape(text)
            or _WRAPPED_CONTINUATION_STOP_RE.match(text)
            or sum(1 for ch in text if ch.isalpha()) < 3
        ):
            return None
        if _extract_page_number_token(follower, text)[0] is None:
            return None
        return follower
    return None


def _add_leader_placement_findings(
    context: TocPageContext,
    rows: list[PdfTextLine],
    page_issue_findings: dict[str, AuditFinding],
) -> None:
    """Leader dots must start right after the title's final line (TOC/LoT/LoF)."""

    measured: list[tuple[PdfTextLine, LeaderGap]] = []
    early_leaders: list[tuple[PdfTextLine, PdfTextLine]] = []
    for index, row in enumerate(rows):
        if _is_non_entry_row(_row_text(row)):
            continue
        gap = measure_title_leader_gap(row)
        if gap is None:
            continue
        if not gap.has_page_number:
            final_row = _next_title_row_carries_page_number(rows, index)
            if final_row is not None:
                early_leaders.append((row, final_row))
                continue
        measured.append((row, gap))

    layout = _page_leader_layout([gap for _, gap in measured])
    gap_violations: list[tuple[PdfTextLine, LeaderGap, float]] = []
    for row, gap in measured:
        allowed = _allowed_title_leader_gap_pt(gap, layout)
        if gap.gap_pt > allowed:
            gap_violations.append((row, gap, allowed))

    if gap_violations:
        row, gap, allowed = max(gap_violations, key=lambda item: item[1].gap_pt - item[2])
        details = _details_with_affected_entry_preview(
            {
                "page_number": str(context.page.page_number),
                "page_type": context.page_type,
                "issue_type": "title_to_leader_gap_too_wide",
                "affected_entry_count": str(len(gap_violations)),
                "worst_delta_pt": f"{gap.gap_pt:.1f}",
                "observed_gap_pt": f"{gap.gap_pt:.1f}",
                "allowed_gap_pt": f"{allowed:.1f}",
                "space_width_pt": f"{gap.space_width_pt:.1f}",
                "observed_gap_spaces": f"{gap.gap_pt / gap.space_width_pt:.1f}"
                if gap.space_width_pt > 0
                else "",
                "leader_layout": layout,
                "confidence": "medium",
            },
            _make_entry_from_line(row, _row_text(row)),
        )
        page_issue_findings["title_to_leader_gap_too_wide"] = AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                "Leader dots do not start right after the end of the entry title."
            ),
            details=details,
        )

    if early_leaders:
        row, final_row = early_leaders[0]
        details = _details_with_affected_entry_preview(
            {
                "page_number": str(context.page.page_number),
                "page_type": context.page_type,
                "issue_type": "leader_dots_before_final_title_line",
                "affected_entry_count": str(len(early_leaders)),
                "confidence": "low",
            },
            _make_entry_from_line(row, _row_text(row)),
        )
        details["bbox"] = format_bbox_detail(_union_bbox(row.bbox, final_row.bbox))
        page_issue_findings["leader_dots_before_final_title_line"] = AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                "Leader dots appear on an earlier line of a wrapped entry title "
                "instead of after its final line."
            ),
            details=details,
        )


_STANDALONE_FOLIO_RE = re.compile(
    r"(?:[0-9]{1,4}|(?=[ivxlcdm])m{0,3}(?:cm|cd|d?c{0,3})"
    r"(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3}))",
    re.IGNORECASE,
)


def _trusted_folio_column(entries: list[TocEntryLine]) -> float | None:
    """Locate a compact majority of independently measured terminal folios."""
    edges: list[float] = []
    for entry in entries:
        row = entry.page_number_line
        if row is None:
            continue
        span = _right_edge_page_number_span(row)
        if span is not None and _clean_text(span.text) == entry.page_number_token:
            edges.append(span.bbox.x1)
    if len(edges) < 3:
        return None
    center = median(edges)
    peers = [edge for edge in edges if abs(edge - center) <= RIGHT_EDGE_TOLERANCE_PT]
    if (
        len(peers) >= 3
        and len(peers) * 2 > len(edges)
        and max(peers) - min(peers) <= RIGHT_EDGE_TOLERANCE_PT
    ):
        return median(peers)
    return None


def _recover_displaced_standalone_folios(
    entries: list[TocEntryLine], rows: list[PdfTextLine], reference_edge: float,
) -> dict[TocEntryLine, PdfTextLine]:
    """Recover a displaced folio on its own line after a completed wrapped title.

    The numeral must sit at the hanging title's indent and be bracketed by
    that title and a separate identified entry. This excludes footer numbers,
    in-title numerals and digits competing with the next entry's baseline.
    """
    recovered: dict[TocEntryLine, PdfTextLine] = {}
    entry_starts = {entry.line.bbox.y0 for entry in entries}
    owned_boxes = [entry.page_number_line.bbox for entry in entries if entry.page_number_line]
    for entry in entries:
        if (
            entry.page_number_token is not None
            or not entry.is_wrapped
            or not _has_entry_identifier(entry.cleaned_text)
        ):
            continue
        # Look for the last owned title row, rather than the closest arbitrary
        # text or numeral to the beginning of a wrapped entry.
        last_index = next(
            (
                i for i, row in enumerate(rows)
                if abs(row.bbox.y1 - entry.line.bbox.y1) < 0.5
                and row.spans
                and entry.line.spans[-len(row.spans):] == row.spans
            ),
            None,
        )
        if last_index is None or last_index + 2 >= len(rows):
            continue
        last, number, following = rows[last_index : last_index + 3]
        tail = _row_text(last)
        token = _row_text(number)
        if (
            len(tail) < 2
            or not tail.endswith(".")
            or not tail[-2].isalpha()
            or not _STANDALONE_FOLIO_RE.fullmatch(token)
            # A lone Roman-looking letter at the title indent can be text.
            or (len(token) == 1 and token.isalpha())
            or abs(number.bbox.x1 - reference_edge) <= RIGHT_EDGE_TOLERANCE_PT
            or last.bbox.x0 < entry.indent_x + LOGICAL_WRAP_MIN_INDENT_PT
            or abs(number.bbox.x0 - last.bbox.x0) > INDENT_CLUSTER_TOLERANCE_PT
            # Adjacent line boxes can overlap at ordinary single spacing.
            # Distinct visual rows still need separation from both neighbors.
            or _line_mid_y(number) - _line_mid_y(last) <= PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT
            or _line_mid_y(following) - _line_mid_y(number) <= PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT
            or number.bbox.y0 - last.bbox.y1 > WRAPPED_ENTRY_Y_GAP_PT
            or following.bbox.y0 - number.bbox.y1 > WRAPPED_ENTRY_Y_GAP_PT
            or not _has_entry_identifier(_row_text(following))
            or following.bbox.y0 not in entry_starts
            or number.bbox in owned_boxes
        ):
            continue
        _apply_auxiliary_page_number(entry, number)
        owned_boxes.append(number.bbox)
        recovered[entry] = number
    return recovered


def _add_entry_consistency_findings(
    context: TocPageContext,
    entries: list[TocEntryLine],
    rows: list[PdfTextLine],
    page_issue_findings: dict[str, AuditFinding],
) -> None:
    """Peer-relative checks: page-number column, presence, leader dots, indent."""

    entry_positions: dict[TocEntryLine, int] = {
        entry: idx for idx, entry in enumerate(entries)
    }

    entries_with_page_num = [
        entry
        for entry in entries
        if entry.page_number_right_x is not None
        # Column-alignment compares dedicated right-column number spans.
        # Trailing digits embedded in a long title span are still valid page
        # numbers for presence checks, but their span x1 is not the column.
        and _right_edge_page_number_span(entry.line) is not None
    ]
    # Missing-folio ownership is evaluated with explicit appendix boundaries
    # and the narrowly gated displaced-folio recovery. Other P018 checks keep
    # their established entries and geometry.
    presence_entries = extract_toc_logical_entry_lines(
        context, recover_displaced_leader_folio=True
    )
    presence_positions = {entry: idx for idx, entry in enumerate(presence_entries)}
    reference_edge = _trusted_folio_column(presence_entries)
    recovered = (
        _recover_displaced_standalone_folios(presence_entries, rows, reference_edge)
        if reference_edge is not None else {}
    )
    if recovered:
        entries_with_page_num.extend(recovered)
    entries_missing_page_num = [
        entry
        for entry in presence_entries
        if entry.page_number_right_x is None
        and not is_toc_structural_column_label(entry.cleaned_text)
        # Wrap continuations (no section/Figure/Table prefix) are not
        # independent entries; do not treat them as "missing page number".
        and (
            _has_prefix_entry_shape(entry.cleaned_text) or entry.has_leader_dots
        )
    ]

    # Recovery already requires three or more agreeing terminal folio spans.
    # Those peers may be wrapped entries whose titles extend beyond the
    # folio column, so the ordinary whole-entry comparison can exclude them.
    if recovered or len(entries_with_page_num) >= 3:
        right_edges = [
            entry.page_number_right_x
            for entry in entries_with_page_num
            if entry.page_number_right_x is not None
        ]
        median_right_edge = (
            reference_edge if recovered and reference_edge is not None else median(right_edges)
        )
        deltas = [abs(edge - median_right_edge) for edge in right_edges]
        misaligned_count = sum(1 for delta in deltas if delta > RIGHT_EDGE_TOLERANCE_PT)
        if misaligned_count > 0:
            worst_entry = entries_with_page_num[deltas.index(max(deltas))]
            page_issue_findings["misaligned_page_number_column"] = AuditFinding(
                rule_id="P018",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "TOC/List page-number column appears misaligned across multiple entries."
                ),
                details=_details_with_affected_entry_preview(
                    {
                        "page_number": str(context.page.page_number),
                        "page_type": context.page_type,
                        "issue_type": "misaligned_page_number_column",
                        "affected_entry_count": str(misaligned_count),
                        "worst_entry_index": str(
                            presence_positions[worst_entry] if worst_entry in recovered
                            else entry_positions[worst_entry]
                        ),
                        "worst_delta_pt": f"{max(deltas):.1f}",
                        "confidence": "high",
                    },
                    worst_entry,
                ),
            )
            if recovered:
                details = page_issue_findings["misaligned_page_number_column"].details
                if worst_entry in recovered:
                    details["bbox"] = format_bbox_detail(recovered[worst_entry].bbox)
                    if worst_entry.page_number_token is not None:
                        details["destination_folio"] = worst_entry.page_number_token
                details["highlight_bboxes"] = " | ".join(
                    format_bbox_detail(
                        recovered[entry].bbox if entry in recovered else entry.line.bbox
                    )
                    for entry, delta in zip(entries_with_page_num, deltas, strict=True)
                    if delta > RIGHT_EDGE_TOLERANCE_PT
                )

    if entries_missing_page_num:
        worst_entry = entries_missing_page_num[0]
        page_issue_findings["missing_page_number"] = AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message="TOC/List contains likely entries with missing page numbers.",
            details=_details_with_affected_entry_preview(
                {
                    "page_number": str(context.page.page_number),
                    "page_type": context.page_type,
                    "issue_type": "missing_page_number",
                    "affected_entry_count": str(len(entries_missing_page_num)),
                    "worst_entry_index": str(presence_positions[worst_entry]),
                    "confidence": "medium",
                },
                worst_entry,
            ),
        )

    leader_sources = {leader_evidence_entry(entry): entry for entry in entries}
    leader_entries = list(leader_sources)
    dotted_count = sum(1 for entry in leader_entries if entry.has_leader_dots)
    dot_majority = dotted_count >= max(3, int(len(leader_entries) * 0.6))
    if (
        context.page_type != "table_of_contents"
        and dot_majority
        and len(entries) >= MIN_ENTRIES_FOR_DOT_STYLE
    ):
        # TOC-wide leader-style consistency belongs to the focused P075/Q052
        # rule. Keep P018's list-page coverage without asking twice for TOC.
        leader_page_edges = [
            entry.page_number_right_x for entry in leader_entries
            if entry.has_leader_dots and entry.page_number_right_x is not None
        ]
        expected_page_edge = median(leader_page_edges) if len(leader_page_edges) >= 3 else None
        missing_dots_entries = [
            entry
            for entry in leader_entries
            if expected_page_edge is not None
            and entry.page_number_right_x is not None
            and abs(entry.page_number_right_x - expected_page_edge) <= RIGHT_EDGE_TOLERANCE_PT
            and _has_list_leader_folio(entry)
            and not entry_has_visible_dot_leader(entry, context.page, leader_entries)
        ]
        if missing_dots_entries:
            previously_eligible = [
                entry for entry in missing_dots_entries
                if not leader_sources[entry].has_leader_dots
                and has_trailing_page_number_token(leader_sources[entry])
            ]
            leader_positions = {
                entry: entry_positions[original] for entry, original in leader_sources.items()
            }
            worst_entry = _select_worst_leader_dots_entry(
                leader_entries, previously_eligible or missing_dots_entries, leader_positions
            )
            page_issue_findings["inconsistent_leader_dots"] = AuditFinding(
                rule_id="P018",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message="TOC/List entries show inconsistent visible leader-dot usage.",
                details=_details_with_affected_entry_preview(
                    {
                        "page_number": str(context.page.page_number),
                        "page_type": context.page_type,
                        "issue_type": "inconsistent_leader_dots",
                        "affected_entry_count": str(len(missing_dots_entries)),
                        "worst_entry_index": str(leader_positions[worst_entry]),
                        "confidence": "medium",
                        "source_q_rule_id": "Q052",
                        **({} if previously_eligible else {"_preserve_prior_finding_ids": "true"}),
                    },
                    worst_entry,
                ),
            )

    ambiguous: dict[int, str] = {}
    if context.page_type == "table_of_contents":
        # Local import: P060 uses this module's logical-entry extraction.
        from njit_auditor.rules.pdf_toc_entry_number_ordering import ambiguous_collapsed_subsections

        ambiguous = ambiguous_collapsed_subsections(entries)
    # An uncertain level must neither receive indent advice nor set its peers' baseline.
    # Keep these entries in the independent page-number and leader checks above.
    entries_with_indent = [
        entry for index, entry in enumerate(entries)
        if entry.page_number_right_x is not None and index not in ambiguous
    ]
    indent_outlier_pairs = _find_hierarchy_indent_outliers(entries_with_indent)
    if indent_outlier_pairs:
        worst_entry, worst_delta = max(indent_outlier_pairs, key=lambda pair: pair[1])
        confidence = (
            "medium" if worst_delta >= HIERARCHY_INDENT_MEDIUM_CONFIDENCE_PT else "low"
        )
        page_issue_findings["inconsistent_hierarchy_indent"] = AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                "This TOC entry's left indent does not match other entries at the "
                "same hierarchy level."
            ),
            details=_details_with_affected_entry_preview(
                {
                    "page_number": str(context.page.page_number),
                    "page_type": context.page_type,
                    "issue_type": "inconsistent_hierarchy_indent",
                    "affected_entry_count": str(len(indent_outlier_pairs)),
                    "worst_entry_index": str(entry_positions[worst_entry]),
                    "worst_delta_pt": f"{worst_delta:.1f}",
                    "confidence": confidence,
                },
                worst_entry,
            ),
        )


def check_pdf_toc_alignment(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P018 warnings for strong likely TOC/List alignment issues."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        page_issue_findings: dict[str, AuditFinding] = {}
        rows = collect_toc_visual_rows(context)
        _add_leader_placement_findings(context, rows, page_issue_findings)
        if context.page_type == "table_of_contents":
            _add_wrapped_title_alignment_finding(context, rows, page_issue_findings)

        entries = extract_toc_logical_entry_lines(context)
        if len(entries) >= 3:
            _add_entry_consistency_findings(context, entries, rows, page_issue_findings)

        for issue_type in (
            "misaligned_page_number_column",
            "missing_page_number",
            "inconsistent_leader_dots",
            "inconsistent_hierarchy_indent",
            "wrapped_title_continuation_misaligned",
            "title_to_leader_gap_too_wide",
            "leader_dots_before_final_title_line",
        ):
            finding = page_issue_findings.get(issue_type)
            if finding is not None:
                findings.append(finding)

    return findings
