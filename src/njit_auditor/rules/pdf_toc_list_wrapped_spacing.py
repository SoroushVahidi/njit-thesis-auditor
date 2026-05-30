"""Conservative wrapped-entry internal spacing checks for TOC/List pages (P032).

Partial heuristic PDF coverage for Q053-Q055, Q066-Q067, and Q076-Q078.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine
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

NEW_ENTRY_START_RE = re.compile(r"^(?:chapter|appendix|\d+\.\d+)", re.IGNORECASE)
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
    return "unknown"


def _collect_entry_region_lines(context: TocPageContext) -> list[PdfTextLine]:
    entry_start_y = context.heading_bottom_y + ENTRY_START_BELOW_HEADING_PT
    header_y_min = context.heading_bottom_y - HEADER_ZONE_ABOVE_HEADING_PT
    lines: list[PdfTextLine] = []
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= context.heading_bottom_y + 2:
                continue
            if line.bbox.y0 < header_y_min:
                continue
            if line.bbox.y0 <= entry_start_y:
                continue
            cleaned = _clean_text(line.text)
            if classify_toc_heading_line(normalize_heading_text(line.text)) is not None:
                continue
            if _is_column_header_line(cleaned):
                continue
            if NUMERIC_ONLY_RE.match(cleaned):
                continue
            if len(cleaned) < MIN_CONTINUATION_TEXT_LEN:
                continue
            lines.append(line)
    lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))
    return lines


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

        for first, second in zip(lines, lines[1:]):
            if not _is_wrap_continuation_pair(first, second, context.page_type):
                continue

            gap_pt = second.bbox.y0 - first.bbox.y1
            if gap_pt <= 0:
                continue

            line_height = _estimate_line_height(first, second)
            gap_ratio = gap_pt / line_height
            if gap_ratio <= WRAPPED_GAP_RATIO_THRESHOLD:
                continue
            if gap_ratio >= MAX_WRAP_INTERNAL_GAP_RATIO:
                continue

            expected_max_gap_pt = line_height * WRAPPED_GAP_RATIO_THRESHOLD
            confidence = "high" if gap_ratio >= (WRAPPED_GAP_RATIO_THRESHOLD + 0.3) else "medium"
            first_text = _clean_text(first.text)

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
                        "confidence": confidence,
                        "source_q_rule_ids": "Q053-Q055,Q066-Q067,Q076-Q078",
                    },
                )
            )

    return findings
