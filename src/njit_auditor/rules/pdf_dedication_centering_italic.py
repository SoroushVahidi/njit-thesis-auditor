"""Conservative Dedication page centering and italic style checks (P065).

Heuristic PDF coverage for Q033 and Q034:

  A. dedication_text_not_centered — the main dedication text block's horizontal
     center deviates from the text-area center by more than
     _CENTER_OFFSET_THRESHOLD_PT (20 pt).  Gate: ≥2 usable text lines required.

  B. dedication_text_not_italic — fewer than half of the usable text spans have
     italic/oblique font style metadata.  Gate: ≥3 usable spans required, and at
     least one span must have non-None font metadata.

Guideline basis:
  - Q033: "Is the full dedication text block visually centered on the page?"
    (260330_YESNO_audit_logic_matrix.xlsx)
  - Q034: "If the dedication text uses the Latin alphabet, is the entire text
    italicized?" (260330_YESNO_audit_logic_matrix.xlsx)

Companion to P041 (pdf_dedication_page.py), which covers Q032 (no header text
in the top margin).  P065 does not duplicate P041, P022, P029, or P037.

P065 does NOT check:
  - Dedication content, wording, or professionalism.
  - Whether the dedication page is present (optional section; absence → no finding).
  - Page number presence/placement (P022, P037, P029).
  - Page order relative to other front matter (P029).
  - Top-margin header text (P041 / Q032).

Conservative skip conditions:
  - No DEDICATION heading found in first _MAX_SCAN_PAGES pages.
  - Multiple DEDICATION headings found (ambiguous layout).
  - Fewer than _MIN_TEXT_LINES usable text lines below the heading.
  - Fewer than _MIN_SPANS usable spans for italic check.
  - All span fonts are None (no font metadata available).
  - Image-only page (no text blocks at all).

Privacy: all finding fields are geometric or numeric metadata only.  No
dedication text, names, font name strings, or dissertation content appears
in any finding field.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine, PdfTextSpan
from njit_auditor.rules.pdf_frontmatter_heading_gate import (
    find_gate_matches_for_heading,
    line_resolves_to_gate_heading,
)
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_SCAN_PAGES = 15
_DEDICATION_HEADING = "DEDICATION"
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)

_MIN_TEXT_LINES = 2
_MIN_SPANS = 3
_CENTER_OFFSET_THRESHOLD_PT = 20.0
_ITALIC_RATIO_THRESHOLD = 0.5
_BOTTOM_ZONE_RATIO = 0.10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_page_number_line(text: str) -> bool:
    return bool(_PAGE_NUM_RE.match(text))


def _find_dedication_page_unique(pdf_document: PdfDocument) -> PdfPage | None:
    """Return the dedication page iff exactly one DEDICATION gate match exists."""
    matches = find_gate_matches_for_heading(
        pdf_document, _DEDICATION_HEADING, max_scan_pages=_MAX_SCAN_PAGES
    )
    if len(matches) != 1:
        return None
    page_number = matches[0].page_number
    for page in pdf_document.pages:
        if page.page_number == page_number:
            return page
    return None


def _find_heading_y(page: PdfPage) -> float | None:
    """Return the y1 (bottom) of the DEDICATION heading line, for use as a cutoff."""
    for block in page.text_blocks:
        for line in block.lines:
            if line_resolves_to_gate_heading(line.text, _DEDICATION_HEADING):
                return line.bbox.y1
    return None


def _collect_dedication_text_lines(page: PdfPage, heading_y: float) -> list[PdfTextLine]:
    """Return usable dedication text lines: below heading, not a page number,
    not in the bottom margin zone, containing at least one alphabetic character."""
    bottom_cutoff = page.height * (1.0 - _BOTTOM_ZONE_RATIO)
    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 < heading_y:
                continue
            if line.bbox.y0 >= bottom_cutoff:
                continue
            cleaned = normalize_heading_text(line.text)
            if not cleaned:
                continue
            if line_resolves_to_gate_heading(cleaned, _DEDICATION_HEADING):
                continue
            if _is_page_number_line(cleaned):
                continue
            if not re.search(r"[A-Za-z]", cleaned):
                continue
            lines.append(line)
    return lines


def _collect_spans(lines: list[PdfTextLine]) -> list[PdfTextSpan]:
    """Return all spans with non-empty text from the given lines."""
    spans: list[PdfTextSpan] = []
    for line in lines:
        for span in line.spans:
            if span.text.strip():
                spans.append(span)
    return spans


def _text_area_center_x(page: PdfPage) -> float:
    return (LEFT_MARGIN_PT + (page.width - RIGHT_MARGIN_PT)) / 2.0


def _block_center_x(lines: list[PdfTextLine]) -> float:
    x0 = min(line.bbox.x0 for line in lines)
    x1 = max(line.bbox.x1 for line in lines)
    return (x0 + x1) / 2.0


def _check_centering(
    page: PdfPage, lines: list[PdfTextLine]
) -> AuditFinding | None:
    if len(lines) < _MIN_TEXT_LINES:
        return None
    ta_center = _text_area_center_x(page)
    blk_center = _block_center_x(lines)
    offset_pt = abs(blk_center - ta_center)
    if offset_pt <= _CENTER_OFFSET_THRESHOLD_PT:
        return None
    text_area_width = page.width - LEFT_MARGIN_PT - RIGHT_MARGIN_PT
    offset_ratio = offset_pt / text_area_width if text_area_width > 0 else 0.0
    return AuditFinding(
        rule_id="P065",
        severity=Severity.WARNING,
        page=page.page_number,
        message=(
            "Dedication text block center deviates from the text-area center by "
            f"{offset_pt:.1f} pt (threshold: {_CENTER_OFFSET_THRESHOLD_PT:.0f} pt). "
            "NJIT requires the dedication text to be centered on the page."
        ),
        details={
            "issue_type": "dedication_text_not_centered",
            "page_number": str(page.page_number),
            "text_area_center_x": f"{ta_center:.1f}",
            "observed_block_center_x": f"{blk_center:.1f}",
            "center_offset_pt": f"{offset_pt:.1f}",
            "center_offset_ratio": f"{offset_ratio:.3f}",
            "text_line_count": str(len(lines)),
            "triage_tier": "medium",
            "source_q_rule_ids": "Q033",
        },
    )


def _check_italic(
    page: PdfPage, spans: list[PdfTextSpan]
) -> AuditFinding | None:
    if len(spans) < _MIN_SPANS:
        return None
    # Skip if no font metadata is available.
    if all(s.font is None for s in spans):
        return None
    italic_count = sum(1 for s in spans if s.italic)
    italic_ratio = italic_count / len(spans)
    if italic_ratio >= _ITALIC_RATIO_THRESHOLD:
        return None
    return AuditFinding(
        rule_id="P065",
        severity=Severity.WARNING,
        page=page.page_number,
        message=(
            f"Dedication text italic span ratio is {italic_ratio:.2f} "
            f"(threshold: {_ITALIC_RATIO_THRESHOLD:.1f}). "
            "NJIT requires dedication text in the Latin alphabet to be italicized."
        ),
        details={
            "issue_type": "dedication_text_not_italic",
            "page_number": str(page.page_number),
            "span_count": str(len(spans)),
            "italic_span_count": str(italic_count),
            "italic_span_ratio": f"{italic_ratio:.3f}",
            "triage_tier": "medium",
            "source_q_rule_ids": "Q034",
        },
    )


# ---------------------------------------------------------------------------
# Public check function
# ---------------------------------------------------------------------------


def check_pdf_dedication_centering_italic(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P065 warnings for dedication page centering and italic style issues.

    Two conservative checks:
      A. dedication_text_not_centered — text block center deviates from text-area center.
      B. dedication_text_not_italic — italic span ratio below threshold.

    Returns an empty list when skip conditions apply.
    Privacy: no dedication text, names, or font content in findings.
    """
    dedication_page = _find_dedication_page_unique(pdf_document)
    if dedication_page is None:
        return []

    if not dedication_page.text_blocks:
        return []

    heading_y = _find_heading_y(dedication_page)
    if heading_y is None:
        return []

    text_lines = _collect_dedication_text_lines(dedication_page, heading_y)
    if not text_lines:
        return []

    findings: list[AuditFinding] = []

    centering_finding = _check_centering(dedication_page, text_lines)
    if centering_finding is not None:
        findings.append(centering_finding)

    spans = _collect_spans(text_lines)
    italic_finding = _check_italic(dedication_page, spans)
    if italic_finding is not None:
        findings.append(italic_finding)

    return findings
