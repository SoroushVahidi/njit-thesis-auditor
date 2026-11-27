"""Conservative List of Tables/Figures column-header checks (P031).

Partial heuristic PDF coverage for Q063, Q064, Q072, and Q073.
Does not verify bold styling or full visual alignment.
"""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import LIST_COLUMN_PAIR_RE
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    classify_toc_heading_line,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)
from njit_auditor.toc_entry_geometry import row_font_size, row_glyphs

HEADER_ZONE_ABOVE_HEADING_PT = 12.0
HEADER_ZONE_BELOW_HEADING_PT = 60.0
HEADER_LABEL_MAX_LEN = 20
LEFT_HEADER_TOLERANCE_PT = 80.0
PAGE_HEADER_TOLERANCE_PT = 80.0
DEFAULT_PAGE_COLUMN_X_PT = 500.0

LOT_LEFT_LABELS = frozenset({"table", "tables"})
LOF_LEFT_LABELS = frozenset({"figure", "figures"})
PAGE_LABELS = frozenset({"page", "pages"})
ENTRY_PREFIX_RE = re.compile(r"^(?:table|figure)s?\s+[0-9]", re.IGNORECASE)

EXPECTED_LEFT_LABEL = {
    "list_of_tables": "Table",
    "list_of_figures": "Figure",
}
EXPECTED_PAGE_LABEL = "Page"
TARGET_PAGE_TYPES = frozenset({"list_of_tables", "list_of_figures"})


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def _normalize_label(text: str) -> str:
    return _clean_text(text).lower()


def _is_short_header_candidate(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned or len(cleaned) > HEADER_LABEL_MAX_LEN:
        return False
    return len(cleaned.split()) <= 2


def _looks_like_entry_not_header(text: str) -> bool:
    return bool(ENTRY_PREFIX_RE.match(_clean_text(text)))


def _matches_left_label(text: str, page_type: str) -> bool:
    if _looks_like_entry_not_header(text):
        return False
    token = _normalize_label(text)
    if page_type == "list_of_tables":
        return token in LOT_LEFT_LABELS
    if page_type == "list_of_figures":
        return token in LOF_LEFT_LABELS
    return False


def _matches_page_label(text: str) -> bool:
    return _normalize_label(text) in PAGE_LABELS


def _paired_header_labels(
    line: PdfTextLine, page_type: str, left_column: float, page_column: float
) -> list[PdfTextLine]:
    # Some PDFs use one text run with spaces between both column labels.
    # Recognize it only when both visible labels occupy the list's columns.
    if line.line_dir not in (None, (1.0, 0.0)):
        return []
    glyphs = row_glyphs(line)
    match = LIST_COLUMN_PAIR_RE.fullmatch("".join(g.char for g in glyphs))
    if match is None or not _matches_left_label(match[1], page_type):
        return []
    left_start, left_end = match.span(1)
    right_start, right_end = match.span(2)
    left_x0 = glyphs[left_start].x0
    left_x1 = glyphs[left_end - 1].x1
    right_x0 = glyphs[right_start].x0
    right_x1 = glyphs[right_end - 1].x1
    if (
        left_x0 is None or left_x1 is None or right_x0 is None or right_x1 is None
        or not left_x0 < left_x1 < right_x0 < right_x1
        or right_x0 - left_x1 < row_font_size(glyphs)
        or abs(left_x0 - left_column) > LEFT_HEADER_TOLERANCE_PT
        or abs(right_x0 - page_column) > PAGE_HEADER_TOLERANCE_PT
    ):
        return []
    return [
        PdfTextLine(text=text, bbox=BBox(x0=x0, y0=line.bbox.y0, x1=x1, y1=line.bbox.y1))
        for text, x0, x1 in ((match[1], left_x0, left_x1), (match[2], right_x0, right_x1))
    ]


def _collect_header_zone_lines(context: TocPageContext) -> list[PdfTextLine]:
    y_min = context.heading_bottom_y - HEADER_ZONE_ABOVE_HEADING_PT
    y_max = context.heading_bottom_y + HEADER_ZONE_BELOW_HEADING_PT
    header_lines: list[PdfTextLine] = []
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 < y_min or line.bbox.y0 > y_max:
                continue
            normalized = normalize_heading_text(line.text)
            if classify_toc_heading_line(normalized) is not None:
                continue
            if not _is_short_header_candidate(line.text):
                continue
            header_lines.append(line)
    header_lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))
    return header_lines


def _column_header_lines(
    context: TocPageContext, entries: list[TocEntryLine]
) -> list[PdfTextLine]:
    left_column = _expected_left_x(entries)
    page_column = _expected_page_x(entries)
    first_numbered_top = min(
        (entry.line.bbox.y0 for entry in entries if entry.page_number_token is not None),
        default=context.heading_bottom_y + HEADER_ZONE_BELOW_HEADING_PT,
    )
    result: list[PdfTextLine] = []
    for line in _collect_header_zone_lines(context):
        paired = (
            _paired_header_labels(line, context.page_type, left_column, page_column)
            if line.bbox.y1 <= first_numbered_top
            else []
        )
        result.extend(paired or [line])
    return result


def _expected_left_x(entries: list[TocEntryLine]) -> float:
    indents = [entry.indent_x for entry in entries if entry.page_number_right_x is not None]
    if not indents:
        indents = [entry.indent_x for entry in entries]
    if indents:
        return float(median(indents))
    return LEFT_MARGIN_PT


def has_lot_table_column_header(context: TocPageContext, entries: list[TocEntryLine]) -> bool:
    """Confirm a Table label above the entries and near their number column."""
    if context.page_type != "list_of_tables" or not entries:
        return False
    # A continuation subtitle or paired header can be recovered as an
    # unnumbered logical row. Neither starts the list of entries.
    first_entry_top = min(
        (entry.line.bbox.y0 for entry in entries
         if _normalize_label(entry.cleaned_text) != "(continued)"
         and not LIST_COLUMN_PAIR_RE.fullmatch(entry.cleaned_text)),
        default=None,
    )
    if first_entry_top is None:
        return False
    expected_left_x = _expected_left_x(entries)
    return any(
        _matches_left_label(line.text, context.page_type)
        and context.heading_bottom_y <= line.bbox.y0
        and line.bbox.y1 <= first_entry_top
        and abs(line.bbox.x0 - expected_left_x) <= LEFT_HEADER_TOLERANCE_PT
        for line in _column_header_lines(context, entries)
    )


def _expected_page_x(entries: list[TocEntryLine]) -> float:
    right_edges = [
        entry.page_number_right_x
        for entry in entries
        if entry.page_number_right_x is not None
    ]
    if right_edges:
        return float(median(right_edges))
    return DEFAULT_PAGE_COLUMN_X_PT


def _observed_header_labels(lines: list[PdfTextLine]) -> str:
    labels = [_clean_text(line.text) for line in lines if _clean_text(line.text)]
    return ", ".join(labels[:4])


def _append_finding(
    findings: list[AuditFinding],
    *,
    context: TocPageContext,
    issue_type: str,
    message: str,
    observed_header_labels: str,
    confidence: str,
    extra: dict[str, str] | None = None,
) -> None:
    details: dict[str, str] = {
        "page_number": str(context.page.page_number),
        "section_type": context.page_type,
        "issue_type": issue_type,
        "expected_left_label": EXPECTED_LEFT_LABEL[context.page_type],
        "expected_page_label": EXPECTED_PAGE_LABEL,
        "observed_header_labels": observed_header_labels,
        "confidence": confidence,
        "source_q_rule_ids": "Q063,Q064,Q072,Q073",
    }
    if extra:
        details.update(extra)
    findings.append(
        AuditFinding(
            rule_id="P031",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=message,
            details=details,
        )
    )


def check_pdf_lot_lof_column_headers(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P031 warnings for missing or misaligned LoT/LoF column header labels."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        if context.page_type not in TARGET_PAGE_TYPES:
            continue

        entries = extract_toc_entry_lines(context)
        if len(entries) < 1:
            continue

        header_lines = _column_header_lines(context, entries)
        left_matches = [
            line
            for line in header_lines
            if _matches_left_label(line.text, context.page_type)
        ]
        page_matches = [line for line in header_lines if _matches_page_label(line.text)]
        observed_labels = _observed_header_labels(header_lines)

        expected_left_x = _expected_left_x(entries)
        expected_page_x = _expected_page_x(entries)

        if not left_matches:
            _append_finding(
                findings,
                context=context,
                issue_type="missing_left_column_header",
                message=(
                    "List page appears to be missing the expected left column header label."
                ),
                observed_header_labels=observed_labels,
                confidence="high",
            )
        else:
            left_line = min(left_matches, key=lambda line: line.bbox.x0)
            if left_line.bbox.x0 > expected_left_x + LEFT_HEADER_TOLERANCE_PT:
                _append_finding(
                    findings,
                    context=context,
                    issue_type="left_column_header_misaligned",
                    message=(
                        "List page left column header label appears far from the "
                        "expected entry column."
                    ),
                    observed_header_labels=_clean_text(left_line.text),
                    confidence="medium",
                    extra={
                        "observed_x0_pt": f"{left_line.bbox.x0:.1f}",
                        "expected_left_x_pt": f"{expected_left_x:.1f}",
                    },
                )

        if not page_matches:
            _append_finding(
                findings,
                context=context,
                issue_type="missing_page_column_header",
                message=(
                    "List page appears to be missing the expected Page column header label."
                ),
                observed_header_labels=observed_labels,
                confidence="high",
            )
        else:
            page_line = max(page_matches, key=lambda line: line.bbox.x1)
            if page_line.bbox.x0 < expected_page_x - PAGE_HEADER_TOLERANCE_PT:
                _append_finding(
                    findings,
                    context=context,
                    issue_type="page_column_header_misaligned",
                    message=(
                        "List page Page column header label appears far from the "
                        "expected page-number column."
                    ),
                    observed_header_labels=_clean_text(page_line.text),
                    confidence="medium",
                    extra={
                        "observed_x0_pt": f"{page_line.bbox.x0:.1f}",
                        "expected_page_x_pt": f"{expected_page_x:.1f}",
                    },
                )

    return findings
