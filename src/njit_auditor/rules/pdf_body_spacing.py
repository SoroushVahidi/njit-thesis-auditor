"""Heuristic check for body-text double-spacing in layout-aware PDF pages.

Conservative rule (P023). Checks whether ordinary body-text paragraphs appear
to be double-spaced as required by NJIT thesis/dissertation formatting guidelines.

Guideline basis:
  - Thesis and Dissertation Formatting Guidelines (WIP).docx: body text must be
    double-spaced.
  - Self-Self Assessment Sheet.pdf: explicit double-spacing checklist item.

Pages excluded:
  - Pages with named front-matter headings (ABSTRACT, APPROVAL PAGE, BIOGRAPHICAL
    SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS, LIST OF TABLES, LIST OF FIGURES).
  - REFERENCES, BIBLIOGRAPHY, WORKS CITED pages.

Lines excluded per page:
  - Lines in the top/bottom 15% margin zones (running headers, page numbers,
    footnotes near the page boundary).
  - Named front-matter heading lines.
  - Page-number candidates.
  - Figure/table caption lines.
  - Bullet or list item lines.
  - Lines shorter than 30 characters or with low alpha density.

Heuristic thresholds:
  - Line spacing = distance between top-of-bbox of consecutive body-text lines,
    which approximates baseline-to-baseline spacing.
  - Ratio = line_spacing / estimated_body_font_size.
  - For double-spacing at 12pt: ratio ≈ 2.0–2.4 → passes.
  - For single-spacing at 12pt: ratio ≈ 1.0–1.2 → fails.
  - Suspicious threshold: ratio < 1.55 (strong evidence of under-spacing, per task
    specification).
  - Paragraph-break gap (ratio > 4.0): pair skipped; not consecutive body lines.
  - Emit one warning per page when ALL three conditions hold:
      1. Suspicious gap count  ≥ MIN_SUSPICIOUS_GAP_COUNT (8)
      2. Suspicious fraction   ≥ MIN_SUSPICIOUS_FRACTION  (0.60, i.e. majority)
      3. Median ratio          < DOUBLE_SPACING_RATIO_THRESHOLD (1.55)
  - Minimum 7 qualifying body lines on the page before checking.
  - Calibrated on 4 EF review PDFs: 0 findings on the cleanest (4th review);
    some findings on earlier drafts that may correspond to tables, code blocks,
    or legitimately under-spaced list content.
"""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import EXPECTED_HEADINGS, normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE, TOP_BOTTOM_ZONE_RATIO

DOUBLE_SPACING_RATIO_THRESHOLD = 1.55
PARAGRAPH_BREAK_RATIO = 4.0
FALLBACK_FONT_SIZE_PT = 12.0
MIN_SUSPICIOUS_GAP_COUNT = 8
MIN_SUSPICIOUS_FRACTION = 0.60
MIN_BODY_LINES_FOR_CHECK = 7
MIN_GAPS_FOR_CHECK = 5
MIN_LINE_TEXT_LEN = 30
MIN_ALPHA_RATIO = 0.45
MIN_ALPHA_COUNT = 15

_ALL_NAMED_HEADINGS = frozenset(EXPECTED_HEADINGS)

TOC_LIKE_HEADINGS = frozenset({
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
})
REFERENCES_LIKE_HEADINGS = frozenset({
    "REFERENCES",
    "BIBLIOGRAPHY",
    "WORKS CITED",
})

CAPTION_PREFIX_RE = re.compile(r"^(figure|table)\s+[\divxlcdm]+[.:)]?\s+", re.IGNORECASE)
BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s+")


def _normalized_heading(line: PdfTextLine) -> str:
    return normalize_heading_text(line.text).upper()


def _page_has_heading_in(page: PdfPage, headings: frozenset[str]) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            if _normalized_heading(line) in headings:
                return True
    return False


def _is_page_number_line(line: PdfTextLine, page_height: float) -> bool:
    clean = " ".join(line.text.strip().split())
    if not clean or not PAGE_NUM_RE.match(clean):
        return False
    top_limit = page_height * TOP_BOTTOM_ZONE_RATIO
    bottom_limit = page_height * (1.0 - TOP_BOTTOM_ZONE_RATIO)
    return line.bbox.y1 <= top_limit or line.bbox.y0 >= bottom_limit


def _is_body_text_line(line: PdfTextLine, page_height: float) -> bool:
    """Return True if line looks like an ordinary body-text line.

    Lines in the top/bottom 15% margin zones are excluded to avoid counting
    running headers, footnotes, and page-number regions.
    """
    top_limit = page_height * TOP_BOTTOM_ZONE_RATIO
    bottom_limit = page_height * (1.0 - TOP_BOTTOM_ZONE_RATIO)
    if line.bbox.y0 < top_limit or line.bbox.y0 > bottom_limit:
        return False
    if _normalized_heading(line) in _ALL_NAMED_HEADINGS:
        return False
    if _is_page_number_line(line, page_height):
        return False
    clean = " ".join(line.text.strip().split())
    if len(clean) < MIN_LINE_TEXT_LEN:
        return False
    if CAPTION_PREFIX_RE.match(clean):
        return False
    if BULLET_PREFIX_RE.match(clean):
        return False
    alpha_count = sum(ch.isalpha() for ch in clean)
    if alpha_count < MIN_ALPHA_COUNT:
        return False
    if alpha_count / max(len(clean), 1) < MIN_ALPHA_RATIO:
        return False
    return True


def _estimate_font_size(lines: list[PdfTextLine]) -> float:
    """Estimate body font size from span sizes on body-text lines."""
    sizes: list[float] = []
    for line in lines:
        for span in line.spans:
            if span.size is not None and span.size > 0:
                sizes.append(span.size)
    if not sizes:
        return FALLBACK_FONT_SIZE_PT
    return median(sizes)


def check_pdf_body_spacing(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P023 warnings when body text appears not to be double-spaced.

    One finding per affected page. Requires strong evidence: ≥ 8 suspicious gaps,
    ≥ 60% of measured pairs suspicious, AND median ratio < 1.55. No body text
    is included in the finding message or details.
    """
    findings: list[AuditFinding] = []

    for page in pdf_doc.pages:
        if _page_has_heading_in(page, TOC_LIKE_HEADINGS):
            continue
        if _page_has_heading_in(page, REFERENCES_LIKE_HEADINGS):
            continue
        if _page_has_heading_in(page, _ALL_NAMED_HEADINGS):
            continue

        all_lines: list[PdfTextLine] = []
        for block in page.text_blocks:
            all_lines.extend(block.lines)

        body_lines = [
            line for line in all_lines if _is_body_text_line(line, page.height)
        ]
        if len(body_lines) < MIN_BODY_LINES_FOR_CHECK:
            continue

        body_lines.sort(key=lambda ln: (ln.bbox.y0, ln.bbox.x0))
        font_size = _estimate_font_size(body_lines)

        spacings: list[float] = []
        for upper, lower in zip(body_lines, body_lines[1:]):
            line_spacing = lower.bbox.y0 - upper.bbox.y0
            if line_spacing <= 0:
                continue
            ratio = line_spacing / font_size
            if ratio > PARAGRAPH_BREAK_RATIO:
                continue
            spacings.append(line_spacing)

        if len(spacings) < MIN_GAPS_FOR_CHECK:
            continue

        median_spacing = median(spacings)
        median_ratio = median_spacing / font_size
        suspicious_count = sum(
            1 for s in spacings if (s / font_size) < DOUBLE_SPACING_RATIO_THRESHOLD
        )
        suspicious_fraction = suspicious_count / len(spacings)

        if median_ratio >= DOUBLE_SPACING_RATIO_THRESHOLD:
            continue
        if suspicious_count < MIN_SUSPICIOUS_GAP_COUNT:
            continue
        if suspicious_fraction < MIN_SUSPICIOUS_FRACTION:
            continue

        findings.append(
            AuditFinding(
                rule_id="P023",
                severity=Severity.WARNING,
                page=page.page_number,
                message=(
                    f"Body text on page {page.page_number} appears to be under-spaced "
                    f"(median line spacing {median_spacing:.1f}pt, "
                    f"ratio {median_ratio:.2f}× font size). "
                    f"NJIT requires double-spaced body text."
                ),
                details={
                    "page_number": str(page.page_number),
                    "issue_type": "possible_body_text_not_double_spaced",
                    "median_body_gap_pt": f"{median_spacing:.1f}",
                    "estimated_body_font_size_pt": f"{font_size:.1f}",
                    "gap_to_font_ratio": f"{median_ratio:.2f}",
                    "affected_gap_count": str(suspicious_count),
                    "confidence": "medium",
                    "suggested_fix": (
                        "Ensure body text paragraphs use double line spacing "
                        "(\\setstretch{2} or \\doublespacing in LaTeX, "
                        "or 'Double' in word processor line spacing settings)."
                    ),
                },
            )
        )

    return findings
