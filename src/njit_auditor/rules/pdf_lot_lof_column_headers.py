"""Conservative List of Tables/Figures column-header checks (P031).

Partial heuristic PDF coverage for Q063, Q064, Q072, and Q073.
Does not verify bold styling or full visual alignment.
"""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    classify_toc_heading_line,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

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


def _expected_left_x(entries: list[TocEntryLine]) -> float:
    indents = [entry.indent_x for entry in entries if entry.page_number_right_x is not None]
    if not indents:
        indents = [entry.indent_x for entry in entries]
    if indents:
        return float(median(indents))
    return LEFT_MARGIN_PT


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

        header_lines = _collect_header_zone_lines(context)
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
