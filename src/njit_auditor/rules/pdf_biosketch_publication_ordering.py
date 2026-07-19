"""Conservative Biographical Sketch publication/presentation year-ordering check (P067).

Partial heuristic PDF coverage for Q027:
  - Q027: are publications/presentations listed from most recent to oldest?

Biographical Sketch page only. Does not read or quote publication titles, venue names,
author names, DOI strings, URL strings, or any biographical prose. Findings contain
only structural metadata and year integers explicitly allowed by the P067 scope doc.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_biosketch_degree_ordering import (
    _YEAR_RE,
    _find_biosketch_page_and_heading_y,
)
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    _group_paragraphs,
    _has_hanging_indent,
    _is_usable_line,
)
from njit_auditor.rules.pdf_headings import normalize_heading_text

_PUBLICATION_SECTION_LABELS = frozenset(
    {
        "PUBLICATIONS",
        "PRESENTATIONS",
        "PUBLICATIONS AND PRESENTATIONS",
        "PAPERS",
        "ARTICLES",
        "CONFERENCE PRESENTATIONS",
    }
)
_DOI_OR_URL_RE = re.compile(r"(doi\s*:|https?://|www\.)", re.IGNORECASE)

_MIN_COMPARABLE_ENTRIES = 3
_INVERSION_TOLERANCE_YEARS = 1
_SINGLE_LINE_MIN_CHARS = 45
_SINGLE_LINE_MAX_CHARS = 220
_SINGLE_LINE_MIN_ALPHA = 20
_MULTI_COLUMN_X_SPREAD_PT = 160.0


def _sorted_lines(page: PdfPage) -> list[PdfTextLine]:
    lines = [line for block in page.text_blocks for line in block.lines]
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


def _collapse_text(text: str) -> str:
    return " ".join(text.strip().split())


def _is_publication_section_heading(text: str) -> bool:
    return normalize_heading_text(text).upper() in _PUBLICATION_SECTION_LABELS


def _is_stop_heading(text: str) -> bool:
    cleaned = normalize_heading_text(text)
    if not cleaned:
        return False
    upper = cleaned.upper()
    if upper in _PUBLICATION_SECTION_LABELS:
        return False
    if any(ch.isdigit() for ch in cleaned):
        return False
    if any(ch in cleaned for ch in ",.;:()"):
        return False
    if len(cleaned) > 36:
        return False
    if upper == cleaned:
        return True
    words = cleaned.split()
    return 1 <= len(words) <= 4 and all(word[:1].isupper() for word in words)


def _find_publication_zone(
    page: PdfPage, heading_bottom_y: float
) -> tuple[float, float | None] | None:
    zone_start_y: float | None = None
    zone_end_y: float | None = None
    for line in _sorted_lines(page):
        if line.bbox.y0 <= heading_bottom_y + 2:
            continue
        cleaned = _collapse_text(line.text)
        if zone_start_y is None:
            if _is_publication_section_heading(cleaned):
                zone_start_y = line.bbox.y1
            continue
        if _is_stop_heading(cleaned):
            zone_end_y = line.bbox.y0
            break
    if zone_start_y is None:
        return None
    return zone_start_y, zone_end_y


def _zone_lines(
    page: PdfPage, zone_start_y: float, zone_end_y: float | None
) -> list[PdfTextLine]:
    lines: list[PdfTextLine] = []
    for line in _sorted_lines(page):
        if line.bbox.y0 <= zone_start_y + 2:
            continue
        if zone_end_y is not None and line.bbox.y0 >= zone_end_y:
            continue
        if _is_stop_heading(line.text):
            continue
        if _is_usable_line(line):
            lines.append(line)
    return lines


def _unique_years_from_text(text: str) -> list[int]:
    return sorted({int(year) for year in _YEAR_RE.findall(text)})


def _looks_like_single_line_citation(line: PdfTextLine) -> bool:
    cleaned = _collapse_text(line.text)
    if len(cleaned) < _SINGLE_LINE_MIN_CHARS or len(cleaned) > _SINGLE_LINE_MAX_CHARS:
        return False
    if _DOI_OR_URL_RE.search(cleaned):
        return False
    if len(_unique_years_from_text(cleaned)) != 1:
        return False
    alpha_count = sum(ch.isalpha() for ch in cleaned)
    if alpha_count < _SINGLE_LINE_MIN_ALPHA:
        return False
    punctuation_count = sum(ch in ",.;:()" for ch in cleaned)
    return punctuation_count >= 2


def _is_candidate_block(block: list[PdfTextLine]) -> bool:
    if not block:
        return False
    joined = " ".join(_collapse_text(line.text) for line in block)
    if _DOI_OR_URL_RE.search(joined):
        return False
    if len(block) == 1:
        return _looks_like_single_line_citation(block[0])
    return _has_hanging_indent(block)


def _representative_year(block: list[PdfTextLine]) -> int | None:
    years = _unique_years_from_text(" ".join(line.text for line in block))
    if len(years) != 1:
        return None
    return years[0]


def _has_suspected_multi_column_layout(blocks: list[list[PdfTextLine]]) -> bool:
    if len(blocks) < 2:
        return False
    first_line_x0s = [block[0].bbox.x0 for block in blocks if block]
    if len(first_line_x0s) < 2:
        return False
    return max(first_line_x0s) - min(first_line_x0s) > _MULTI_COLUMN_X_SPREAD_PT


def check_pdf_biosketch_publication_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit a P067 warning when Bio Sketch publications are not most-recent-first."""
    result = _find_biosketch_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_bottom_y = result
    if not page.text_blocks:
        return []

    zone = _find_publication_zone(page, heading_bottom_y)
    if zone is None:
        return []

    zone_start_y, zone_end_y = zone
    lines = _zone_lines(page, zone_start_y, zone_end_y)
    if not lines:
        return []

    blocks = _group_paragraphs(lines)
    candidate_blocks = [block for block in blocks if _is_candidate_block(block)]
    if _has_suspected_multi_column_layout(candidate_blocks):
        return []

    comparable_years: list[int] = []
    for block in candidate_blocks:
        year = _representative_year(block)
        if year is not None:
            comparable_years.append(year)

    if len(comparable_years) < _MIN_COMPARABLE_ENTRIES:
        return []

    inversion_count = 0
    first_inversion_index = -1
    for idx in range(len(comparable_years) - 1):
        if comparable_years[idx + 1] > comparable_years[idx] + _INVERSION_TOLERANCE_YEARS:
            inversion_count += 1
            if first_inversion_index < 0:
                first_inversion_index = idx

    if inversion_count == 0:
        return []

    confidence = "high" if len(comparable_years) >= 4 else "medium"
    return [
        AuditFinding(
            rule_id="P067",
            severity=Severity.WARNING,
            page=page.page_number,
            message=(
                "Biographical Sketch publication/presentation entries may not be listed in "
                "most-recent-first order. NJIT guidelines require reverse "
                "chronological ordering."
            ),
            details={
                "issue_type": "biosketch_publication_order_suspicious",
                "entry_candidate_count": str(len(candidate_blocks)),
                "comparable_entry_count": str(len(comparable_years)),
                "first_entry_year": str(comparable_years[0]),
                "last_entry_year": str(comparable_years[-1]),
                "inversion_count": str(inversion_count),
                "first_inversion_index": str(first_inversion_index),
                "expected_order": "descending",
                "confidence": confidence,
                "triage_tier": "medium",
                "source_q_rule_ids": "Q027",
            },
        )
    ]
