"""Heuristic check for body-text double-spacing in layout-aware PDF pages.

Conservative rule (P023). Evaluates ordinary body-text paragraphs — not whole pages —
for double-spacing as required by NJIT thesis/dissertation formatting guidelines.

Pages/regions excluded:
  - Front-matter, TOC/List, and named heading pages.
  - References/bibliography section pages.
  - Figure/table captions and compact float bodies (table cells, figure content).
  - Margin zones, page numbers, bullets, and short/noisy lines.

Findings require a localized body paragraph with measured spacing evidence and a
highlight bbox. Page-level warnings without a specific paragraph are suppressed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_captions import CAPTION_START_RE, CaptionLine, detect_caption_lines
from njit_auditor.rules.pdf_headings import (
    EXPECTED_HEADINGS,
    find_body_start_page,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE, TOP_BOTTOM_ZONE_RATIO
from njit_auditor.rules.pdf_references_citations_structural import (
    _collect_references_section_pages,
    _localize_references_heading,
)

DOUBLE_SPACING_RATIO_THRESHOLD = 1.55
PARAGRAPH_BREAK_RATIO = 4.0
FALLBACK_FONT_SIZE_PT = 12.0
MIN_SUSPICIOUS_GAP_COUNT = 4
MIN_SUSPICIOUS_FRACTION = 0.60
MIN_PARAGRAPH_LINES = 3
MIN_PARAGRAPH_GAPS = 2
MIN_LINE_TEXT_LEN = 30
MIN_ALPHA_RATIO = 0.45
MIN_ALPHA_COUNT = 15
MAX_SNIPPET_LEN = 72
COLUMN_X_TOLERANCE_PT = 24.0
PRIMARY_BODY_X_MAX_PT = LEFT_MARGIN_PT + 28.0
SECONDARY_COLUMN_MIN_X_PT = 200.0
FLOAT_REGION_GAP_PT = 8.0
BODY_PARAGRAPH_MIN_GAP_RATIO = 2.0
BODY_PARAGRAPH_MIN_CHARS = 40

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
TABLE_HEADER_RE = re.compile(
    r"^(research question|corresponding survey items?)$",
    re.IGNORECASE,
)
RQ_LINE_RE = re.compile(r"^RQ\d+:", re.IGNORECASE)
SURVEY_ITEM_RE = re.compile(
    r"^(Benefits|Barriers|Perceptions|Readiness|Composite)\s+Q\d+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _ParagraphMetrics:
    lines: tuple[PdfTextLine, ...]
    median_spacing: float
    median_ratio: float
    suspicious_count: int
    suspicious_fraction: float
    font_size: float


def _normalized_heading(line: PdfTextLine) -> str:
    return normalize_heading_text(line.text).upper()


def _page_has_heading_in(page: PdfPage, headings: frozenset[str]) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            if _normalized_heading(line) in headings:
                return True
    return False


def _references_page_numbers(pdf_doc: PdfDocument) -> frozenset[int]:
    body_start = find_body_start_page(pdf_doc)
    heading = _localize_references_heading(pdf_doc, body_start)
    if heading is None:
        return frozenset()
    heading_page, _keyword = heading
    return frozenset(
        page.page_number
        for page in _collect_references_section_pages(pdf_doc, heading_page)
    )


def _is_page_number_line(line: PdfTextLine, page_height: float) -> bool:
    clean = " ".join(line.text.strip().split())
    if not clean or not PAGE_NUM_RE.match(clean):
        return False
    top_limit = page_height * TOP_BOTTOM_ZONE_RATIO
    bottom_limit = page_height * (1.0 - TOP_BOTTOM_ZONE_RATIO)
    return line.bbox.y1 <= top_limit or line.bbox.y0 >= bottom_limit


def _is_caption_line(line: PdfTextLine) -> bool:
    clean = " ".join(line.text.strip().split())
    return bool(CAPTION_PREFIX_RE.match(clean) or CAPTION_START_RE.match(clean))


def _is_table_like_line(line: PdfTextLine) -> bool:
    clean = " ".join(line.text.strip().split())
    if TABLE_HEADER_RE.match(clean):
        return True
    if RQ_LINE_RE.match(clean):
        return True
    if SURVEY_ITEM_RE.match(clean):
        return True
    if line.bbox.x0 >= SECONDARY_COLUMN_MIN_X_PT and len(clean) >= MIN_LINE_TEXT_LEN:
        return True
    return False


def _is_body_text_line(line: PdfTextLine, page_height: float) -> bool:
    """Return True if line could be ordinary body text before region exclusions."""
    top_limit = page_height * TOP_BOTTOM_ZONE_RATIO
    bottom_limit = page_height * (1.0 - TOP_BOTTOM_ZONE_RATIO)
    if line.bbox.y0 < top_limit or line.bbox.y0 > bottom_limit:
        return False
    if _normalized_heading(line) in _ALL_NAMED_HEADINGS:
        return False
    if _is_page_number_line(line, page_height):
        return False
    if _is_caption_line(line):
        return False
    if _is_table_like_line(line):
        return False
    clean = " ".join(line.text.strip().split())
    if len(clean) < MIN_LINE_TEXT_LEN:
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
    sizes: list[float] = []
    for line in lines:
        for span in line.spans:
            if span.size is not None and span.size > 0:
                sizes.append(span.size)
    if not sizes:
        return FALLBACK_FONT_SIZE_PT
    return median(sizes)


def _collect_page_lines(page: PdfPage) -> list[PdfTextLine]:
    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        lines.extend(block.lines)
    return lines


def _line_in_band(line: PdfTextLine, bands: list[tuple[float, float]]) -> bool:
    mid_y = (line.bbox.y0 + line.bbox.y1) / 2.0
    return any(y0 <= mid_y <= y1 for y0, y1 in bands)


def _page_has_multi_column_table(lines: list[PdfTextLine]) -> bool:
    primary = 0
    secondary = 0
    for line in lines:
        clean = line.text.strip()
        if not clean:
            continue
        if line.bbox.x0 >= SECONDARY_COLUMN_MIN_X_PT:
            secondary += 1
        elif line.bbox.x0 <= PRIMARY_BODY_X_MAX_PT:
            primary += 1
    return primary >= 3 and secondary >= 3


def _find_float_region_end(
    lines: list[PdfTextLine],
    caption: CaptionLine,
    font_size: float,
) -> float:
    """Return the y1 coordinate where a table/figure float region ends."""
    if caption.bbox is None:
        return 0.0

    below = sorted(
        (line for line in lines if line.bbox.y0 > caption.bbox.y1 + FLOAT_REGION_GAP_PT),
        key=lambda ln: (ln.bbox.y0, ln.bbox.x0),
    )
    if not below:
        return caption.bbox.y1

    last_y1 = caption.bbox.y1
    prev_y1 = caption.bbox.y1
    multi_column = _page_has_multi_column_table(below)

    for line in below:
        gap = line.bbox.y0 - prev_y1
        gap_ratio = gap / font_size if font_size else gap / FALLBACK_FONT_SIZE_PT
        clean = " ".join(line.text.strip().split())

        if (
            line.bbox.x0 <= PRIMARY_BODY_X_MAX_PT
            and len(clean) >= BODY_PARAGRAPH_MIN_CHARS
            and gap_ratio >= BODY_PARAGRAPH_MIN_GAP_RATIO
            and not _is_table_like_line(line)
        ):
            break

        if multi_column or _is_table_like_line(line) or line.bbox.x0 >= SECONDARY_COLUMN_MIN_X_PT:
            last_y1 = max(last_y1, line.bbox.y1)
            prev_y1 = line.bbox.y1
            continue

        if gap_ratio < PARAGRAPH_BREAK_RATIO:
            last_y1 = max(last_y1, line.bbox.y1)
            prev_y1 = line.bbox.y1
            continue
        break

    return last_y1


def _float_exclusion_bands(
    page: PdfPage,
    captions: list[CaptionLine],
    lines: list[PdfTextLine],
    font_size: float,
) -> list[tuple[float, float]]:
    bands: list[tuple[float, float]] = []
    for caption in captions:
        if caption.page_number != page.page_number or caption.bbox is None:
            continue
        y_end = _find_float_region_end(lines, caption, font_size)
        bands.append((caption.bbox.y0, y_end))
    return bands


def _is_primary_body_column(line: PdfTextLine) -> bool:
    return line.bbox.x0 <= PRIMARY_BODY_X_MAX_PT


def _group_paragraphs(
    lines: list[PdfTextLine],
    font_size: float,
) -> list[list[PdfTextLine]]:
    if not lines:
        return []
    ordered = sorted(lines, key=lambda ln: (ln.bbox.y0, ln.bbox.x0))
    paragraphs: list[list[PdfTextLine]] = [[ordered[0]]]
    for line in ordered[1:]:
        prev = paragraphs[-1][-1]
        anchor_x = paragraphs[-1][0].bbox.x0
        same_column = abs(line.bbox.x0 - anchor_x) <= COLUMN_X_TOLERANCE_PT
        gap = line.bbox.y0 - prev.bbox.y0
        if gap <= 0:
            paragraphs.append([line])
            continue
        ratio = gap / font_size if font_size else gap / FALLBACK_FONT_SIZE_PT
        if same_column and ratio <= PARAGRAPH_BREAK_RATIO:
            paragraphs[-1].append(line)
        else:
            paragraphs.append([line])
    return paragraphs


def _paragraph_metrics(lines: list[PdfTextLine], font_size: float) -> _ParagraphMetrics | None:
    if len(lines) < MIN_PARAGRAPH_LINES:
        return None
    spacings: list[float] = []
    for upper, lower in zip(lines, lines[1:]):
        line_spacing = lower.bbox.y0 - upper.bbox.y0
        if line_spacing <= 0:
            continue
        ratio = line_spacing / font_size if font_size else line_spacing / FALLBACK_FONT_SIZE_PT
        if ratio > PARAGRAPH_BREAK_RATIO:
            continue
        spacings.append(line_spacing)
    if len(spacings) < MIN_PARAGRAPH_GAPS:
        return None
    median_spacing = median(spacings)
    median_ratio = (
        median_spacing / font_size
        if font_size
        else median_spacing / FALLBACK_FONT_SIZE_PT
    )
    suspicious_count = sum(
        1 for spacing in spacings if (spacing / font_size) < DOUBLE_SPACING_RATIO_THRESHOLD
    )
    suspicious_fraction = suspicious_count / len(spacings)
    return _ParagraphMetrics(
        lines=tuple(lines),
        median_spacing=median_spacing,
        median_ratio=median_ratio,
        suspicious_count=suspicious_count,
        suspicious_fraction=suspicious_fraction,
        font_size=font_size,
    )


def _paragraph_is_suspicious(metrics: _ParagraphMetrics) -> bool:
    if metrics.median_ratio >= DOUBLE_SPACING_RATIO_THRESHOLD:
        return False
    if metrics.suspicious_count < MIN_SUSPICIOUS_GAP_COUNT:
        return False
    if metrics.suspicious_fraction < MIN_SUSPICIOUS_FRACTION:
        return False
    return True


def _union_line_bbox(lines: list[PdfTextLine]) -> BBox:
    return BBox(
        x0=min(line.bbox.x0 for line in lines),
        y0=min(line.bbox.y0 for line in lines),
        x1=max(line.bbox.x1 for line in lines),
        y1=max(line.bbox.y1 for line in lines),
    )


def _paragraph_snippet(lines: list[PdfTextLine]) -> str:
    clean = " ".join(lines[0].text.strip().split())
    if len(clean) <= MAX_SNIPPET_LEN:
        return clean
    return clean[: MAX_SNIPPET_LEN - 1].rstrip() + "…"


def check_pdf_body_spacing(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P023 warnings for localized body paragraphs that appear under-spaced."""
    findings: list[AuditFinding] = []
    body_start = find_body_start_page(pdf_doc)
    references_pages = _references_page_numbers(pdf_doc)
    captions = detect_caption_lines(pdf_doc)
    captions_by_page: dict[int, list[CaptionLine]] = {}
    for caption in captions:
        captions_by_page.setdefault(caption.page_number, []).append(caption)

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

        page_lines = _collect_page_lines(page)
        candidate_lines = [
            line for line in page_lines if _is_body_text_line(line, page.height)
        ]
        if not candidate_lines:
            continue

        font_size = _estimate_font_size(candidate_lines)
        exclusion_bands = _float_exclusion_bands(
            page,
            captions_by_page.get(page.page_number, []),
            page_lines,
            font_size,
        )
        eligible_lines = [
            line
            for line in candidate_lines
            if not _line_in_band(line, exclusion_bands) and _is_primary_body_column(line)
        ]
        if not eligible_lines:
            continue

        for paragraph in _group_paragraphs(eligible_lines, font_size):
            metrics = _paragraph_metrics(paragraph, font_size)
            if metrics is None or not _paragraph_is_suspicious(metrics):
                continue

            bbox = _union_line_bbox(list(metrics.lines))
            snippet = _paragraph_snippet(list(metrics.lines))
            findings.append(
                AuditFinding(
                    rule_id="P023",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        f"Body paragraph on page {page.page_number} beginning "
                        f"'{snippet}' appears under-spaced "
                        f"(median line spacing {metrics.median_spacing:.1f}pt, "
                        f"ratio {metrics.median_ratio:.2f}× font size)."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "possible_body_text_not_double_spaced",
                        "affected_text_snippet": snippet,
                        "page_context": "body",
                        "median_body_gap_pt": f"{metrics.median_spacing:.1f}",
                        "estimated_body_font_size_pt": f"{metrics.font_size:.1f}",
                        "gap_to_font_ratio": f"{metrics.median_ratio:.2f}",
                        "affected_gap_count": str(metrics.suspicious_count),
                        "confidence": "medium",
                        "bbox": format_bbox_detail(bbox),
                        "suggested_fix": (
                            "Set this body paragraph to double spacing while keeping "
                            "allowed table, figure, and caption spacing rules separate."
                        ),
                    },
                )
            )

    return findings
