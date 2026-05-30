"""Heuristic TOC/List alignment checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import normalize_heading_text

TOC_HEADING_MAP = {
    "TABLE OF CONTENTS": "table_of_contents",
    "LIST OF TABLES": "list_of_tables",
    "LIST OF FIGURES": "list_of_figures",
}
HEADING_SUFFIX_RE = re.compile(r"[\s:.\-]+(?:\((?:continued)\)|continued)\s*$", re.IGNORECASE)
TRAILING_PUNCT_RE = re.compile(r"[.:]+$")
PAGE_NUMBER_TOKEN_RE = re.compile(r"(?P<num>(?:[0-9]+|[ivxlcdm]+))$", re.IGNORECASE)
ENTRY_START_RE = re.compile(r"^[A-Za-z0-9(\[]")
NUMERIC_ONLY_RE = re.compile(r"^(?:[0-9]+|[ivxlcdm]+)$", re.IGNORECASE)
LINE_PREVIEW_MAX_LEN = 80
RIGHT_EDGE_TOLERANCE_PT = 10.0
INDENT_CLUSTER_TOLERANCE_PT = 12.0
MIN_ENTRIES_FOR_DOT_STYLE = 4
PAGE_NUMBER_LINE_Y_TOLERANCE_PT = 5.0


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
    ) -> None:
        self.line = line
        self.cleaned_text = cleaned_text
        self.page_number_token = page_number_token
        self.page_number_right_x = page_number_right_x
        self.indent_x = indent_x
        self.has_leader_dots = has_leader_dots


class TocPageContext:
    """TOC-like page with extracted context and heading line position."""

    def __init__(self, page: PdfPage, page_type: str, heading_bottom_y: float) -> None:
        self.page = page
        self.page_type = page_type
        self.heading_bottom_y = heading_bottom_y


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

    contexts: list[TocPageContext] = []

    for page in pdf_document.pages:
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


def _likely_entry_line(cleaned_text: str) -> bool:
    if len(cleaned_text) < 8:
        return False
    if NUMERIC_ONLY_RE.match(cleaned_text):
        return False
    if cleaned_text.isupper() and len(cleaned_text.split()) <= 4:
        return False
    return bool(ENTRY_START_RE.match(cleaned_text))


def extract_toc_entry_lines(context: TocPageContext) -> list[TocEntryLine]:
    """Extract likely entry lines below TOC/List heading on a page."""

    entries: list[TocEntryLine] = []
    numeric_lines: list[PdfTextLine] = []
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= context.heading_bottom_y + 2:
                continue
            cleaned = _clean_text(line.text)
            if NUMERIC_ONLY_RE.match(cleaned):
                numeric_lines.append(line)
                continue
            if not _likely_entry_line(cleaned):
                continue
            page_num, page_right_x = _extract_page_number_token(line, cleaned)
            entries.append(
                TocEntryLine(
                    line=line,
                    cleaned_text=cleaned,
                    page_number_token=page_num,
                    page_number_right_x=page_right_x,
                    indent_x=line.bbox.x0,
                    has_leader_dots="..." in cleaned or " ." in cleaned,
                )
            )

    # Pair right-column numeric-only lines with nearby entry lines when page numbers are split.
    unused_numeric = sorted(numeric_lines, key=lambda line: (line.bbox.y0, line.bbox.x0))
    for entry in entries:
        if entry.page_number_right_x is not None:
            continue
        best_idx: int | None = None
        best_delta = 9999.0
        for idx, num_line in enumerate(unused_numeric):
            y_delta = abs(num_line.bbox.y0 - entry.line.bbox.y0)
            if y_delta > PAGE_NUMBER_LINE_Y_TOLERANCE_PT:
                continue
            if num_line.bbox.x0 <= (entry.indent_x + 100):
                continue
            if y_delta < best_delta:
                best_delta = y_delta
                best_idx = idx
        if best_idx is not None:
            matched_line = unused_numeric.pop(best_idx)
            matched_text = _clean_text(matched_line.text)
            entry.page_number_token = matched_text
            entry.page_number_right_x = matched_line.bbox.x1

    entries.sort(key=lambda entry: (entry.line.bbox.y0, entry.line.bbox.x0))
    return entries


def _find_indent_outliers(indents: list[float]) -> list[float]:
    if len(indents) < 5:
        return []
    sorted_indents = sorted(indents)
    clusters: list[float] = []
    for indent in sorted_indents:
        matched = False
        for idx, center in enumerate(clusters):
            if abs(indent - center) <= INDENT_CLUSTER_TOLERANCE_PT:
                clusters[idx] = (clusters[idx] + indent) / 2.0
                matched = True
                break
        if not matched:
            clusters.append(indent)
    if len(clusters) <= 1:
        return []
    expected = min(clusters)
    return [
        indent
        for indent in indents
        if abs(indent - expected) > (INDENT_CLUSTER_TOLERANCE_PT * 2)
    ]


def check_pdf_toc_alignment(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P018 warnings for strong likely TOC/List alignment issues."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        entries = extract_toc_entry_lines(context)
        if len(entries) < 3:
            continue

        page_issue_findings: dict[str, AuditFinding] = {}

        entries_with_page_num = [
            entry for entry in entries if entry.page_number_right_x is not None
        ]
        entries_missing_page_num = [entry for entry in entries if entry.page_number_right_x is None]

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
                page_issue_findings["misaligned_page_number_column"] = AuditFinding(
                    rule_id="P018",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "TOC/List page-number column appears misaligned across multiple entries."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "page_type": context.page_type,
                        "issue_type": "misaligned_page_number_column",
                        "affected_entry_count": str(misaligned_count),
                        "worst_delta_pt": f"{max(deltas):.1f}",
                        "confidence": "high",
                    },
                )

        if entries_missing_page_num:
            page_issue_findings["missing_page_number"] = AuditFinding(
                rule_id="P018",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message="TOC/List contains likely entries with missing page numbers.",
                details={
                    "page_number": str(context.page.page_number),
                    "page_type": context.page_type,
                    "issue_type": "missing_page_number",
                    "affected_entry_count": str(len(entries_missing_page_num)),
                    "confidence": "medium",
                },
            )

        dotted_count = sum(1 for entry in entries if entry.has_leader_dots)
        dot_majority = dotted_count >= max(3, int(len(entries) * 0.6))
        if dot_majority and len(entries) >= MIN_ENTRIES_FOR_DOT_STYLE:
            missing_dots_count = sum(
                1
                for entry in entries
                if entry.page_number_right_x is not None and not entry.has_leader_dots
            )
            if missing_dots_count > 0:
                page_issue_findings["inconsistent_leader_dots"] = AuditFinding(
                    rule_id="P018",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message="TOC/List entries show inconsistent visible leader-dot usage.",
                    details={
                        "page_number": str(context.page.page_number),
                        "page_type": context.page_type,
                        "issue_type": "inconsistent_leader_dots",
                        "affected_entry_count": str(missing_dots_count),
                        "confidence": "medium",
                    },
                )

        indents = [entry.indent_x for entry in entries if entry.page_number_right_x is not None]
        indent_outliers = _find_indent_outliers(indents)
        if indent_outliers:
            worst_delta = max(abs(indent - min(indents)) for indent in indent_outliers)
            page_issue_findings["inconsistent_hierarchy_indent"] = AuditFinding(
                rule_id="P018",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "TOC/List entries show an indentation outlier likely inconsistent "
                    "with hierarchy."
                ),
                details={
                    "page_number": str(context.page.page_number),
                    "page_type": context.page_type,
                    "issue_type": "inconsistent_hierarchy_indent",
                    "affected_entry_count": str(len(indent_outliers)),
                    "worst_delta_pt": f"{worst_delta:.1f}",
                    "confidence": "medium",
                },
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
