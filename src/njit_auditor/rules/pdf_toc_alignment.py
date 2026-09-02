"""Heuristic TOC/List alignment checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
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
SECTION_NUMBER_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)[\s:]")
SECTION_NUMBER_ONLY_RE = re.compile(r"^\d+(?:\.\d+)*$")
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
NUMERIC_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)*\s")
INDENT_CLUSTER_TOLERANCE_PT = 12.0
MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON = 3
HIERARCHY_INDENT_TOLERANCE_PT = 10.0
HIERARCHY_INDENT_MEDIUM_CONFIDENCE_PT = 18.0


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
    ) -> None:
        self.line = line
        self.cleaned_text = cleaned_text
        self.page_number_token = page_number_token
        self.page_number_right_x = page_number_right_x
        self.indent_x = indent_x
        self.has_leader_dots = has_leader_dots
        self.is_wrapped = is_wrapped


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


def _extract_page_number_from_spans(line: PdfTextLine) -> tuple[str | None, float | None]:
    span = _right_column_page_number_span(line)
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
    line: PdfTextLine, cleaned_text: str
) -> tuple[str | None, float | None]:
    match = PAGE_NUMBER_TOKEN_RE.search(cleaned_text)
    if match is not None:
        token = match.group("num")
        right_x = _page_number_right_x_for_token(line, token)
        return token, right_x
    span_token = _extract_page_number_from_spans(line)
    if span_token[0] is not None:
        return span_token
    return _extract_trailing_right_column_page_number(line, cleaned_text)


def _line_mid_y(line: PdfTextLine) -> float:
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


def _assemble_same_baseline_toc_rows(lines: list[PdfTextLine]) -> list[PdfTextLine]:
    """Group TOC/list lines that share a baseline into visual rows."""

    if not lines:
        return []
    ordered = sorted(lines, key=lambda line: (_line_mid_y(line), line.bbox.x0))
    groups: list[list[PdfTextLine]] = []
    current: list[PdfTextLine] = []
    current_mid: float | None = None
    for line in ordered:
        mid = _line_mid_y(line)
        if current_mid is None or abs(mid - current_mid) <= SAME_BASELINE_Y_TOLERANCE_PT:
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
    if not entry.has_leader_dots and _has_leader_dot_pattern(cleaned):
        entry.has_leader_dots = True


def _looks_like_wrap_continuation(cleaned_text: str) -> bool:
    """True for mid-entry wrap fragments (hyphen tails / lowercase run-ons)."""

    if not cleaned_text:
        return False
    if cleaned_text.endswith("-") or cleaned_text.endswith("\u2010"):
        return True
    return cleaned_text[0].islower()


def _has_prefix_entry_shape(cleaned_text: str) -> bool:
    upper = cleaned_text.upper()
    return bool(PREFIX_ENTRY_RE.match(upper) or NUMERIC_PREFIX_RE.match(cleaned_text))


def _has_leader_dot_pattern(cleaned_text: str) -> bool:
    return "..." in cleaned_text or cleaned_text.rstrip().endswith("....")


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
        if y_delta_abs < best_delta:
            best_delta = y_delta_abs
            best_idx = idx
    if best_idx is None:
        return None
    return auxiliary_lines.pop(best_idx)


def _make_entry_from_line(line: PdfTextLine, cleaned: str) -> TocEntryLine:
    page_num, page_right_x = _extract_page_number_token(line, cleaned)
    return TocEntryLine(
        line=line,
        cleaned_text=cleaned,
        page_number_token=page_num,
        page_number_right_x=page_right_x,
        indent_x=line.bbox.x0,
        has_leader_dots="..." in cleaned or " ." in cleaned,
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
                    if _has_prefix_entry_shape(nxt.cleaned_text):
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
                        idx += 1
                        break
                    prev_y = nxt.line.bbox.y0
                    idx += 1
                if entry.page_number_token is None:
                    matched = _pair_right_column_number(
                        entry,
                        auxiliary_lines,
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


def extract_toc_entry_lines(context: TocPageContext) -> list[TocEntryLine]:
    """Extract likely entry lines below TOC/List heading on a page."""

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
    ordered_lines = _assemble_same_baseline_toc_rows(ordered_lines)

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
        page_num, page_right_x = _extract_page_number_token(line, cleaned)
        has_signal = page_num is not None or page_right_x is not None
        if not _likely_entry_line(cleaned, has_page_number_signal=has_signal):
            continue
        entries.append(_make_entry_from_line(line, cleaned))

    unused_auxiliary = sorted(auxiliary_lines, key=lambda line: (line.bbox.y0, line.bbox.x0))
    for entry in entries:
        if entry.page_number_right_x is not None:
            continue
        matched = _pair_right_column_number(
            entry,
            unused_auxiliary,
            max_y_gap=PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT,
        )
        if matched is not None:
            _apply_auxiliary_page_number(entry, matched)

    entries = _merge_wrapped_entries(entries, unused_auxiliary)
    entries = _drop_merge_orphans(entries)
    entries.sort(key=lambda entry: (entry.line.bbox.y0, entry.line.bbox.x0))
    return entries


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
    """Return 1-based hierarchy depth for numbered section entries, None for others.

    "1 INTRODUCTION" → 1, "1.1 Background" → 2, "1.1.1 Detail" → 3.
    Entries without a leading numeric section number (chapter titles, appendix
    labels, etc.) all return None and are compared only against each other.
    """
    m = SECTION_NUMBER_PREFIX_RE.match(cleaned_text)
    if m is None:
        return None
    return m.group(1).count(".") + 1


def _find_hierarchy_indent_outliers(
    entries: list[TocEntryLine],
) -> list[tuple[TocEntryLine, float]]:
    """Find entries whose left indent diverges from their same-level peers.

    Entries are grouped by hierarchy level so level-2 entries are only compared
    against other level-2 entries — never against level-1 entries.  A level group
    needs at least MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON entries before any
    outlier can be flagged, and the deviation must exceed HIERARCHY_INDENT_TOLERANCE_PT.

    Returns a list of (entry, delta_pt) pairs for outliers, empty when none found.
    """
    by_level: dict[int | None, list[TocEntryLine]] = {}
    for entry in entries:
        level = _parse_toc_hierarchy_level(entry.cleaned_text)
        by_level.setdefault(level, []).append(entry)

    has_named_levels = any(
        lvl is not None and len(lvl_entries) >= MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON
        for lvl, lvl_entries in by_level.items()
    )

    outlier_pairs: list[tuple[TocEntryLine, float]] = []
    for level, level_entries in by_level.items():
        if len(level_entries) < MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON:
            continue
        # Skip unclassified (None-level) entries when the TOC has well-populated
        # numbered levels. None-level entries are often PDF-split fragments whose
        # x-coord reflects the title text start, not the section number — mixing
        # them with numbered-level entries or with each other across hierarchy
        # boundaries causes false positives.
        if level is None and has_named_levels:
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


def check_pdf_toc_alignment(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P018 warnings for strong likely TOC/List alignment issues."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        entries = extract_toc_entry_lines(context)
        if len(entries) < 3:
            continue

        page_issue_findings: dict[str, AuditFinding] = {}
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
            and _right_column_page_number_span(entry.line) is not None
        ]
        entries_missing_page_num = [
            entry
            for entry in entries
            if entry.page_number_right_x is None
            and not is_toc_structural_column_label(entry.cleaned_text)
            # Wrap continuations (no section/Figure/Table prefix) are not
            # independent entries; do not treat them as "missing page number".
            and (
                _has_prefix_entry_shape(entry.cleaned_text) or entry.has_leader_dots
            )
        ]

        if len(entries_with_page_num) >= 3:
            right_edges = [
                entry.page_number_right_x
                for entry in entries_with_page_num
                if entry.page_number_right_x is not None
            ]
            if len(right_edges) < 3:
                continue
            median_right_edge = median(right_edges)
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
                            "worst_entry_index": str(entry_positions[worst_entry]),
                            "worst_delta_pt": f"{max(deltas):.1f}",
                            "confidence": "high",
                        },
                        worst_entry,
                    ),
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
                        "worst_entry_index": str(entry_positions[worst_entry]),
                        "confidence": "medium",
                    },
                    worst_entry,
                ),
            )

        dotted_count = sum(1 for entry in entries if entry.has_leader_dots)
        dot_majority = dotted_count >= max(3, int(len(entries) * 0.6))
        if dot_majority and len(entries) >= MIN_ENTRIES_FOR_DOT_STYLE:
            missing_dots_entries = [
                entry
                for entry in entries
                if entry.page_number_right_x is not None and not entry.has_leader_dots
            ]
            if missing_dots_entries:
                worst_entry = _select_worst_leader_dots_entry(
                    entries, missing_dots_entries, entry_positions
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
                            "worst_entry_index": str(entry_positions[worst_entry]),
                            "confidence": "medium",
                            "source_q_rule_id": "Q052",
                        },
                        worst_entry,
                    ),
                )

        entries_with_indent = [
            entry for entry in entries if entry.page_number_right_x is not None
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

        for issue_type in (
            "misaligned_page_number_column",
            "missing_page_number",
            "inconsistent_leader_dots",
            "inconsistent_hierarchy_indent",
        ):
            finding = page_issue_findings.get(issue_type)
            if finding is not None:
                findings.append(finding)

    return findings
