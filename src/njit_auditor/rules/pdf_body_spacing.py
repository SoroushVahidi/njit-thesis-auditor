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
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_captions import detect_caption_lines
from njit_auditor.rules.pdf_headings import (
    EXPECTED_HEADINGS,
    find_body_start_page,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE, TOP_BOTTOM_ZONE_RATIO
from njit_auditor.rules.pdf_references_citations_structural import (
    references_section_page_numbers,
)

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

# Table-region detection: a text line that follows a table caption with a row
# pitch (top-to-top distance) at or below this multiple of the body font size
# is treated as a table row and excluded from body-spacing measurement. The
# limit sits just above the single-spacing band so tightly packed table rows
# are captured while genuinely double-spaced body prose (ratio ≈ 2.0) ends the
# table region instead of being swallowed by it.
_TABLE_ROW_PITCH_RATIO = 1.7
# Tolerance for treating a line as "below" a caption despite tiny bbox overlap.
_CAPTION_OVERLAP_TOL_PT = 2.0

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

# Bare "Figure N" / "Fig. N" anchor with nothing else on the line. Some PDFs
# (LaTeX output with a wide caption-number/text gap) split a figure caption's
# label from its description text into separate extracted line objects on the
# same visual row. A line consisting of *only* this label never occurs in
# ordinary body prose (a body sentence that references a figure always has
# more words on the same line), so it is a safe, narrow anchor for locating a
# figure-caption region without the fuller prose-vs-caption disambiguation
# that whole-sentence caption detection needs.
FIGURE_LABEL_ANCHOR_RE = re.compile(
    r"^(?:figure|fig\.)\s*[0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*[.:)]?\s*$",
    re.IGNORECASE,
)
# Lines sharing a top-of-bbox within this tolerance are treated as the same
# visual row (split fragments of one caption line, not consecutive lines).
_ROW_Y_TOLERANCE_PT = 1.0


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


def _table_caption_bboxes_by_page(pdf_doc: PdfDocument) -> dict[int, list[BBox]]:
    """Return table-caption line bboxes keyed by page number.

    Only real table captions (``Table N ...``) are used to anchor table-region
    detection; figure captions and List-of-* entries are ignored here.
    """
    result: dict[int, list[BBox]] = {}
    for caption in detect_caption_lines(pdf_doc):
        if caption.caption_type != "table" or caption.bbox is None:
            continue
        result.setdefault(caption.page_number, []).append(caption.bbox)
    return result


def _table_band_ranges(
    caption_bboxes: list[BBox],
    all_lines: list[PdfTextLine],
    font_size: float,
) -> list[tuple[float, float]]:
    """Return vertical (y0, y1) bands covering table captions and their rows.

    Each band starts at a table caption and extends downward across the
    contiguous run of tightly packed rows (single-spacing-like pitch), stopping
    at the first line whose pitch indicates ordinary (double-spaced) body text.
    Lines whose vertical center falls inside any band are table content and must
    not be measured as body text.
    """
    if not caption_bboxes:
        return []
    pitch_limit = max(font_size, 1.0) * _TABLE_ROW_PITCH_RATIO
    ordered = sorted(all_lines, key=lambda ln: (ln.bbox.y0, ln.bbox.x0))
    bands: list[tuple[float, float]] = []
    for caption_bbox in caption_bboxes:
        band_bottom = caption_bbox.y1
        prev_top = caption_bbox.y0
        for line in ordered:
            if line.bbox.y0 < caption_bbox.y1 - _CAPTION_OVERLAP_TOL_PT:
                continue  # at or above the caption line itself
            pitch = line.bbox.y0 - prev_top
            if pitch <= 0:
                # Cell on the same row (side-by-side) — part of the table row.
                band_bottom = max(band_bottom, line.bbox.y1)
                continue
            if pitch > pitch_limit:
                break  # ordinary body spacing resumed — table region ended
            band_bottom = max(band_bottom, line.bbox.y1)
            prev_top = line.bbox.y0
        bands.append((caption_bbox.y0, band_bottom))
    return bands


def _line_in_bands(line: PdfTextLine, bands: list[tuple[float, float]]) -> bool:
    center_y = (line.bbox.y0 + line.bbox.y1) / 2.0
    return any(y0 <= center_y <= y1 for y0, y1 in bands)


def _group_into_rows(lines: list[PdfTextLine]) -> list[list[PdfTextLine]]:
    """Group lines sharing a top-of-bbox into one visual row.

    Handles PDFs whose text extraction splits one visual line (e.g. a figure
    label and its caption text, separated by a wide LaTeX-inserted gap) into
    multiple line objects at the same y-position.
    """
    ordered = sorted(lines, key=lambda ln: (ln.bbox.y0, ln.bbox.x0))
    rows: list[list[PdfTextLine]] = []
    for line in ordered:
        if rows and abs(line.bbox.y0 - rows[-1][0].bbox.y0) <= _ROW_Y_TOLERANCE_PT:
            rows[-1].append(line)
        else:
            rows.append([line])
    return rows


def _figure_caption_band_ranges(
    all_lines: list[PdfTextLine],
    font_size: float,
) -> list[tuple[float, float]]:
    """Return vertical (y0, y1) bands covering figure captions/descriptions.

    Each band starts at a row whose leftmost line is a bare figure-label
    anchor (see ``FIGURE_LABEL_ANCHOR_RE``) and extends downward across the
    contiguous run of tightly packed rows -- the caption's own description
    text -- stopping at the first row whose pitch indicates ordinary
    (double-spaced) body text has resumed. Figure captions/descriptions are
    conventionally single-spaced even in an otherwise double-spaced document,
    so this text must not be measured as ordinary body prose.
    """
    if not all_lines:
        return []
    pitch_limit = max(font_size, 1.0) * _TABLE_ROW_PITCH_RATIO
    rows = _group_into_rows(all_lines)
    bands: list[tuple[float, float]] = []
    row_index = 0
    while row_index < len(rows):
        row = rows[row_index]
        anchor_line = min(row, key=lambda ln: ln.bbox.x0)
        clean = " ".join(anchor_line.text.strip().split())
        if not FIGURE_LABEL_ANCHOR_RE.match(clean):
            row_index += 1
            continue
        band_top = min(ln.bbox.y0 for ln in row)
        band_bottom = max(ln.bbox.y1 for ln in row)
        prev_top = band_top
        next_index = row_index + 1
        while next_index < len(rows):
            next_row = rows[next_index]
            next_top = min(ln.bbox.y0 for ln in next_row)
            pitch = next_top - prev_top
            if pitch > pitch_limit:
                break
            band_bottom = max(band_bottom, max(ln.bbox.y1 for ln in next_row))
            prev_top = next_top
            next_index += 1
        bands.append((band_top, band_bottom))
        row_index = next_index
    return bands


def _bullet_block_band_ranges(
    all_lines: list[PdfTextLine],
    font_size: float,
) -> list[tuple[float, float]]:
    """Return vertical bands covering bullet/list items and wrapped lines.

    P023 measures ordinary dissertation prose. Bullet items may be single-spaced
    internally, so once a bullet marker anchors a row, contiguous single-spaced
    continuation rows belong to that list item rather than to body prose.
    """
    if not all_lines:
        return []
    pitch_limit = max(font_size, 1.0) * _TABLE_ROW_PITCH_RATIO
    rows = _group_into_rows(all_lines)
    bands: list[tuple[float, float]] = []
    row_index = 0
    while row_index < len(rows):
        row = rows[row_index]
        leftmost = min(row, key=lambda ln: ln.bbox.x0)
        clean = " ".join(leftmost.text.strip().split())
        if not BULLET_PREFIX_RE.match(clean):
            row_index += 1
            continue
        band_top = min(ln.bbox.y0 for ln in row)
        band_bottom = max(ln.bbox.y1 for ln in row)
        prev_top = band_top
        next_index = row_index + 1
        while next_index < len(rows):
            next_row = rows[next_index]
            next_top = min(ln.bbox.y0 for ln in next_row)
            pitch = next_top - prev_top
            if pitch > pitch_limit:
                break
            band_bottom = max(band_bottom, max(ln.bbox.y1 for ln in next_row))
            prev_top = next_top
            next_index += 1
        bands.append((band_top, band_bottom))
        row_index = next_index
    return bands


def check_pdf_body_spacing(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P023 warnings when body text appears not to be double-spaced.

    One finding per affected page. Requires strong evidence: ≥ 8 suspicious gaps,
    ≥ 60% of measured pairs suspicious, AND median ratio < 1.55. No body text
    is included in the finding message or details.
    """
    findings: list[AuditFinding] = []

    # Skip all pages that precede the first CHAPTER/APPENDIX heading. These are
    # front-matter pages (biographical sketch, publication lists, TOC continuation
    # pages, etc.) that are legitimately single-spaced or tightly formatted.
    body_start = find_body_start_page(pdf_doc)

    # Exclude the entire References/Bibliography section, including continuation
    # pages that do not repeat the heading. Reference-entry spacing has its own
    # dedicated check (P064) and must not be mislabeled as "body text not
    # double-spaced".
    references_pages = references_section_page_numbers(pdf_doc)

    # Anchor table regions from their captions so table cell text and tightly
    # packed table rows are not measured as ordinary body text.
    table_caption_bboxes = _table_caption_bboxes_by_page(pdf_doc)

    for page in pdf_doc.pages:
        if body_start is not None and page.page_number < body_start:
            continue
        if page.page_number in references_pages:
            continue
        if _page_has_heading_in(page, TOC_LIKE_HEADINGS):
            continue
        if _page_has_heading_in(page, REFERENCES_LIKE_HEADINGS):
            continue
        if _page_has_heading_in(page, _ALL_NAMED_HEADINGS):
            continue

        all_lines: list[PdfTextLine] = []
        for block in page.text_blocks:
            all_lines.extend(block.lines)

        page_font_size = _estimate_font_size(all_lines) if all_lines else FALLBACK_FONT_SIZE_PT
        table_bands = _table_band_ranges(
            table_caption_bboxes.get(page.page_number, []),
            all_lines,
            page_font_size,
        )
        figure_bands = _figure_caption_band_ranges(all_lines, page_font_size)
        bullet_bands = _bullet_block_band_ranges(all_lines, page_font_size)

        body_lines = [
            line
            for line in all_lines
            if _is_body_text_line(line, page.height)
            and not _line_in_bands(line, table_bands)
            and not _line_in_bands(line, figure_bands)
            and not _line_in_bands(line, bullet_bands)
        ]
        # Only warn when actual body-text lines remain to be measured. If all
        # tight spacing lives inside a table or figure-caption region,
        # body_lines is now too small and the page is skipped rather than
        # mislabeled.
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

        measured_bbox = _union_bbox(body_lines)

        details = {
            "page_number": str(page.page_number),
            "issue_type": "possible_body_text_not_double_spaced",
            "median_body_gap_pt": f"{median_spacing:.1f}",
            "estimated_body_font_size_pt": f"{font_size:.1f}",
            "gap_to_font_ratio": f"{median_ratio:.2f}",
            "affected_gap_count": str(suspicious_count),
            "measured_body_line_count": str(len(body_lines)),
            "measured_gap_count": str(len(spacings)),
            "confidence": "medium",
            "suggested_fix": (
                "Ensure body text paragraphs use double line spacing "
                "(\\setstretch{2} or \\doublespacing in LaTeX, "
                "or 'Double' in word processor line spacing settings)."
            ),
        }
        if measured_bbox is not None:
            # Highlight the measured body-text region (table regions are already
            # excluded) so the evidence points at the lines that were measured
            # rather than only showing the original page.
            details["bbox"] = format_bbox_detail(measured_bbox)

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
                details=details,
            )
        )

    return findings


def _union_bbox(lines: list[PdfTextLine]) -> BBox | None:
    if not lines:
        return None
    return BBox(
        x0=min(line.bbox.x0 for line in lines),
        y0=min(line.bbox.y0 for line in lines),
        x1=max(line.bbox.x1 for line in lines),
        y1=max(line.bbox.y1 for line in lines),
    )
