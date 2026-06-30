"""Heuristic TOC/List alignment checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.digital_commons_wrapper import (
    detect_digital_commons_wrapper_pages,
    without_wrapper_pages,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
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
ENTRY_START_RE = re.compile(r"^[A-Za-z0-9(\[]")
NUMERIC_ONLY_RE = re.compile(r"^(?:[0-9]+|[ivxlcdm]+)$", re.IGNORECASE)
SECTION_NUMBER_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)\s")
LINE_PREVIEW_MAX_LEN = 80
RIGHT_EDGE_TOLERANCE_PT = 10.0
MIN_ENTRIES_FOR_DOT_STYLE = 4
PAGE_NUMBER_LINE_Y_TOLERANCE_PT = 5.0
PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT = 8.0
RIGHT_COLUMN_MIN_X_OFFSET_PT = 200.0
WRAPPED_ENTRY_Y_GAP_PT = 12.0
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


def _extract_page_number_token(
    line: PdfTextLine, cleaned_text: str
) -> tuple[str | None, float | None]:
    match = PAGE_NUMBER_TOKEN_RE.search(cleaned_text)
    if match is None:
        return None, None
    token = match.group("num")
    span = line.spans[-1] if line.spans else None
    right_x = span.bbox.x1 if span is not None else line.bbox.x1
    return token, right_x


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
    ):
        return False
    min_len = (
        PREFIX_ENTRY_MIN_LEN
        if has_prefix or has_page_number_signal
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
    numeric_lines: list[PdfTextLine],
    *,
    max_y_gap: float,
    require_below: bool = False,
    relax_y_tolerance: bool = False,
) -> PdfTextLine | None:
    best_idx: int | None = None
    best_delta = 9999.0
    for idx, num_line in enumerate(numeric_lines):
        y_delta = num_line.bbox.y0 - entry.line.bbox.y0
        if require_below and y_delta < 0:
            continue
        y_delta_abs = abs(y_delta)
        if y_delta_abs > max_y_gap:
            continue
        if num_line.bbox.x0 <= (entry.indent_x + 100):
            continue
        tolerance = max_y_gap if relax_y_tolerance else _y_tolerance_for_pairing(
            entry.indent_x,
            num_line.bbox.x0,
        )
        if y_delta_abs > tolerance:
            continue
        if y_delta_abs < best_delta:
            best_delta = y_delta_abs
            best_idx = idx
    if best_idx is None:
        return None
    return numeric_lines.pop(best_idx)


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


def _merge_wrapped_entries(
    entries: list[TocEntryLine],
    numeric_lines: list[PdfTextLine],
) -> list[TocEntryLine]:
    if not entries:
        return entries

    merged: list[TocEntryLine] = []
    skip_next = False
    sorted_entries = sorted(entries, key=lambda entry: (entry.line.bbox.y0, entry.line.bbox.x0))
    for idx, entry in enumerate(sorted_entries):
        if skip_next:
            skip_next = False
            continue
        if entry.page_number_token is None:
            matched = _pair_right_column_number(
                entry,
                numeric_lines,
                max_y_gap=WRAPPED_ENTRY_Y_GAP_PT,
                require_below=True,
                relax_y_tolerance=True,
            )
            if matched is not None:
                entry.page_number_token = _clean_text(matched.text)
                entry.page_number_right_x = matched.bbox.x1
                entry.is_wrapped = True
            elif idx + 1 < len(sorted_entries):
                nxt = sorted_entries[idx + 1]
                y_gap = nxt.line.bbox.y0 - entry.line.bbox.y0
                if (
                    y_gap <= WRAPPED_ENTRY_Y_GAP_PT
                    and nxt.page_number_token is not None
                    and entry.page_number_token is None
                ):
                    entry.page_number_token = nxt.page_number_token
                    entry.page_number_right_x = nxt.page_number_right_x
                    entry.is_wrapped = True
                    skip_next = True
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

    ordered_lines: list[PdfTextLine] = []
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= context.heading_bottom_y + 2:
                continue
            ordered_lines.append(line)
    ordered_lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))

    entries: list[TocEntryLine] = []
    numeric_lines: list[PdfTextLine] = []
    for line in ordered_lines:
        cleaned = _clean_text(line.text)
        if _is_list_heading_line(cleaned):
            continue
        if NUMERIC_ONLY_RE.match(cleaned):
            numeric_lines.append(line)
            continue
        page_num, page_right_x = _extract_page_number_token(line, cleaned)
        has_signal = page_num is not None or page_right_x is not None
        if not _likely_entry_line(cleaned, has_page_number_signal=has_signal):
            continue
        entries.append(_make_entry_from_line(line, cleaned))

    unused_numeric = sorted(numeric_lines, key=lambda line: (line.bbox.y0, line.bbox.x0))
    for entry in entries:
        if entry.page_number_right_x is not None:
            continue
        matched = _pair_right_column_number(
            entry,
            unused_numeric,
            max_y_gap=PAGE_NUMBER_RELAXED_Y_TOLERANCE_PT,
        )
        if matched is not None:
            entry.page_number_token = _clean_text(matched.text)
            entry.page_number_right_x = matched.bbox.x1

    entries = _merge_wrapped_entries(entries, unused_numeric)
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

    outlier_pairs: list[tuple[TocEntryLine, float]] = []
    for _level, level_entries in by_level.items():
        if len(level_entries) < MIN_SAME_LEVEL_FOR_HIERARCHY_COMPARISON:
            continue
        indents = [e.indent_x for e in level_entries]
        med = median(indents)
        for entry in level_entries:
            delta = abs(entry.indent_x - med)
            if delta > HIERARCHY_INDENT_TOLERANCE_PT:
                outlier_pairs.append((entry, delta))
    return outlier_pairs


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
            entry for entry in entries if entry.page_number_right_x is not None
        ]
        entries_missing_page_num = [
            entry
            for entry in entries
            if entry.page_number_right_x is None
            and not is_toc_structural_column_label(entry.cleaned_text)
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
                worst_entry = missing_dots_entries[0]
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
