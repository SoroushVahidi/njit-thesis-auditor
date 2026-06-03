"""Conservative Dedication page top-margin header check (P041).

Partial heuristic PDF coverage for Q032:
  - Q032: Is there no header text in the top margin area of the Dedication page?

Checks only the Dedication page; skips if DEDICATION heading is not detected.
Does not check dedication text centering (Q033) or italicization (Q034).
Does not duplicate P034 (copyright page), P022 (page-number absence), or P037 (Roman numerals).
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import normalize_heading_text

_TOP_ZONE_RATIO = 0.15
_MAX_SCAN_PAGES = 15
_DEDICATION_HEADING = "DEDICATION"
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)


def _sorted_lines(page: PdfPage) -> list[PdfTextLine]:
    lines = [line for block in page.text_blocks for line in block.lines]
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


def _in_top_zone(line: PdfTextLine, page_height: float) -> bool:
    return line.bbox.y1 <= page_height * _TOP_ZONE_RATIO


def _is_page_number_candidate(cleaned: str) -> bool:
    return bool(_PAGE_NUM_RE.match(cleaned))


def _find_dedication_page(pdf_document: PdfDocument) -> PdfPage | None:
    """Return the first page with a DEDICATION heading in the first _MAX_SCAN_PAGES pages."""
    for page in pdf_document.pages[:_MAX_SCAN_PAGES]:
        for block in page.text_blocks:
            for line in block.lines:
                if normalize_heading_text(line.text).upper() == _DEDICATION_HEADING:
                    return page
    return None


def check_pdf_dedication_page(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P041 warning when header text is found in the top margin of the Dedication page."""
    dedication_page = _find_dedication_page(pdf_document)
    if dedication_page is None:
        return []

    threshold_pt = dedication_page.height * _TOP_ZONE_RATIO
    findings: list[AuditFinding] = []

    for line in _sorted_lines(dedication_page):
        if not _in_top_zone(line, dedication_page.height):
            continue
        cleaned = normalize_heading_text(line.text)
        if not cleaned or len(cleaned) < 3:
            continue
        if _is_page_number_candidate(cleaned):
            continue
        if cleaned.upper() == _DEDICATION_HEADING:
            continue
        if not re.search(r"[A-Za-z]", cleaned):
            continue
        findings.append(
            AuditFinding(
                rule_id="P041",
                severity=Severity.WARNING,
                page=dedication_page.page_number,
                message=(
                    "Possible header or running text detected in the top margin of the "
                    "Dedication page (NJIT expects no header text in this area)."
                ),
                details={
                    "issue_type": "dedication_top_margin_header_text",
                    "page_number": str(dedication_page.page_number),
                    "top_region_threshold_points": f"{threshold_pt:.1f}",
                    "line_y": f"{line.bbox.y0:.1f}",
                    "line_x0": f"{line.bbox.x0:.1f}",
                    "line_x1": f"{line.bbox.x1:.1f}",
                    "triage_tier": "medium",
                    "source_q_rule_id": "Q032",
                },
            )
        )
        break  # At most one finding per Dedication page.

    return findings
