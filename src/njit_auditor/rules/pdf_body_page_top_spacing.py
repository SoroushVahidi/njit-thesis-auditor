"""Detect a corroborated blank body line at a page boundary (P016)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from math import isclose, isfinite

import pymupdf

from njit_auditor.digital_commons_wrapper import page_identity
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_captions import CAPTION_START_RE, normalize_caption_candidate_text
from njit_auditor.rules.pdf_headings import find_body_start_page
from njit_auditor.rules.pdf_indentation import (
    _is_named_heading_line,
    _is_section_heading_line,
    _is_usable_paragraph_line,
)
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    LEFT_MARGIN_PT,
    OVERFLOW_TOLERANCE_PT,
    TOP_MARGIN_PT,
)
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE
from njit_auditor.rules.pdf_references_citations_structural import references_section_page_numbers

# Match measured positions across extraction APIs and adjacent pages.
_POSITION_TOLERANCE_PT = 1.0
_ISSUE_TYPE = "blank_line_above_continuing_body_text"


@dataclass(frozen=True)
class _ProseLine:
    line: PdfTextLine
    baseline: float
    font: str
    size: float


def _near(first: float, second: float) -> bool:
    return isclose(first, second, rel_tol=0, abs_tol=_POSITION_TOLERANCE_PT)


def _reading_order(page: PdfPage) -> list[PdfTextLine]:
    return sorted(
        (
            line
            for block in page.text_blocks
            for line in block.lines
            if line.text.strip()
            and not (
                line.bbox.y0 >= page.height - BOTTOM_MARGIN_PT
                and PAGE_NUM_RE.fullmatch(line.text.strip())
            )
        ),
        key=lambda line: (line.bbox.y0, line.bbox.x0),
    )


def _prose(line: PdfTextLine, page: PdfPage) -> _ProseLine | None:
    box = line.bbox
    baseline = line.baseline_y
    if (
        baseline is None
        or line.line_dir != (1.0, 0.0)
        or line.wmode != 0
        or not (0 <= box.x0 < box.x1 <= page.width and 0 <= box.y0 < baseline <= box.y1)
        or not _is_usable_paragraph_line(line)
        or _is_section_heading_line(line)
        or line.text.isupper()
        or any(span.bold for span in line.spans)
    ):
        return None
    # Small inline scripts can land close to the main line's origin. Use
    # the largest regular style on that baseline to identify the prose.
    styles = [
        (span.font, span.size)
        for span in line.spans
        if span.text.strip()
        and not span.italic
        and span.baseline_y is not None
        and _near(span.baseline_y, baseline)
        and span.size is not None
        and isfinite(span.size)
        and span.size > 0
    ]
    size = max((size for _, size in styles), default=0)
    fonts = {font for font, span_size in styles if span_size == size}
    if len(fonts) != 1:
        return None
    font, = fonts
    if not font:
        return None
    return _ProseLine(line, baseline, font, size)


def _opening(page: PdfPage, rows: list[PdfTextLine]) -> tuple[_ProseLine, float, float] | None:
    """Measure two consecutive line pitches in the opening prose."""
    if len(rows) < 3:
        return None
    first, second, third = (_prose(line, page) for line in rows[:3])
    if first is None or second is None or third is None:
        return None
    opening = (first, second, third)
    if any(
        (row.font, row.size) != (first.font, first.size)
        or not _near(row.line.bbox.x0, first.line.bbox.x0)
        for row in opening
    ):
        return None
    pitch = second.baseline - first.baseline
    if (
        pitch <= max(row.line.bbox.height for row in opening)
        or not _near(third.baseline - second.baseline, pitch)
        or any(left.line.bbox.y1 >= right.line.bbox.y0 for left, right in pairwise(opening))
        or any(
            box.y0 < third.line.bbox.y1 and 0 < box.y1
            for box in (*page.horizontal_rules, *(block.bbox for block in page.graphic_blocks))
        )
    ):
        return None
    return first, pitch, third.line.bbox.y1


def _ends_with_body_content(
    page: PdfPage, rows: list[PdfTextLine], first: _ProseLine, pitch: float,
) -> bool:
    last = rows[-1]
    box = last.bbox
    bottom_margin = page.height - BOTTOM_MARGIN_PT
    if (
        not (0 < box.y0 < bottom_margin and box.y0 < box.y1 <= page.height)
        or box.y1 + pitch <= bottom_margin
    ):
        return False
    caption = CAPTION_START_RE.match(normalize_caption_candidate_text(last.text))
    if caption and caption.group("label").lower() in {"figure", "fig."}:
        # An image that ends just above its caption can legitimately occupy
        # the rest of the preceding page. The caption stays with that image.
        return any(
            0 <= box.y0 - block.bbox.y1 <= pitch
            and block.bbox.x0 < box.x1 and box.x0 < block.bbox.x1
            for block in page.graphic_blocks
        )
    penultimate, final = (_prose(row, page) for row in rows[-2:])
    return (
        penultimate is not None and final is not None
        and _near(final.baseline - penultimate.baseline, pitch)
        and all(
            row.font == first.font and row.size == first.size
            and _near(row.line.bbox.x0, first.line.bbox.x0)
            for row in (penultimate, final)
        )
    )


def _reference_baseline(
    previous: PdfPage, page: PdfPage, first: _ProseLine, pitch: float,
) -> float | None:
    if (
        previous.width != page.width
        or previous.height != page.height
        or previous.page_number + 1 != page.page_number
        or page_identity(previous).original_page_index + 1
        != page_identity(page).original_page_index
        or previous.text_extraction_unavailable
        or previous.page_rotation
        or previous.is_visually_landscape
    ):
        return None
    rows = _reading_order(previous)
    if len(rows) < 2 or any(_is_named_heading_line(row) for row in rows):
        return None
    reference = _prose(rows[0], previous)
    if (
        reference is None
        or (reference.font, reference.size) != (first.font, first.size)
        or not _near(reference.line.bbox.x0, first.line.bbox.x0)
        or abs(reference.line.bbox.y0 - TOP_MARGIN_PT) > OVERFLOW_TOLERANCE_PT
        or abs(reference.line.bbox.x0 - LEFT_MARGIN_PT) > OVERFLOW_TOLERANCE_PT
        or not _near(first.baseline - reference.baseline, pitch)
        or not _ends_with_body_content(previous, rows, first, pitch)
    ):
        return None
    # The visible opening lines occupy the same body column. One em allows for
    # an ordinary wrap that ends a little short of the neighboring right edge.
    if abs(first.line.bbox.x1 - reference.line.bbox.x1) > first.size:
        return None
    return reference.baseline


def _source_confirms_blank_line(
    source: pymupdf.Document,
    page: PdfPage,
    first: _ProseLine,
    expected_baseline: float,
    opening_bottom: float,
) -> bool:
    original_index = page_identity(page).original_page_index
    if not 0 <= original_index < len(source):
        return False
    original = source[original_index]
    box = first.line.bbox
    if (
        original.rotation
        or not _near(original.rect.width, page.width)
        or not _near(original.rect.height, page.height)
    ):
        return False
    # A whitespace-only text run is omitted by layout extraction. Require a
    # source run matching the body gutter, font and predicted empty baseline.
    if not any(
        span["dir"] == (1.0, 0.0)
        and span["wmode"] == 0
        and span["type"] == 0
        and span["opacity"] == 1
        and span["font"] == first.font
        and _near(span["size"], first.size)
        and (chars := span["chars"])
        and _near(chars[0][2][0], box.x0)
        and all(_near(char[2][1], expected_baseline) and chr(char[0]).isspace() for char in chars)
        for span in original.get_texttrace()
    ):
        return False
    # Vector tables and artwork may extend alongside the opening rows, even
    # when the band above them is visibly empty.
    if any(
        not kind.endswith("-text") and bounds[1] < opening_bottom and bounds[3] > 0
        for kind, bounds in original.get_bboxlog()
    ):
        return False
    # Outlined text and artwork can be absent from extracted layout. Confirm
    # the area above the first real line is visibly blank, including the margins.
    clip = pymupdf.Rect(0, 0, page.width, box.y0 - 1)
    pixels = original.get_pixmap(
        matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csGRAY, clip=clip, annots=False,
    )
    return bool(pixels.width and pixels.height) and min(pixels.samples) >= 250


def check_pdf_body_page_top_spacing(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Report a positively identified extra line before continuing body prose."""
    body_start = find_body_start_page(pdf_doc)
    if body_start is None:
        return []
    reference_pages = references_section_page_numbers(pdf_doc)
    candidates = []
    for previous, page in pairwise(pdf_doc.pages):
        if (
            previous.page_number < body_start
            or previous.page_number in reference_pages
            or page.page_number in reference_pages
            or page.text_extraction_unavailable
            or page.page_rotation
            or page.is_visually_landscape
            or page.width >= page.height
        ):
            continue
        rows = _reading_order(page)
        if any(_is_named_heading_line(row) for row in rows):
            continue
        opening = _opening(page, rows)
        if opening is None:
            continue
        first, pitch, opening_bottom = opening
        baseline = _reference_baseline(previous, page, first, pitch)
        if baseline is not None:
            candidates.append((page, first, pitch, baseline, opening_bottom))

    if not candidates:
        return []
    try:
        source = pymupdf.open(pdf_doc.path)
    except (OSError, RuntimeError, ValueError):
        return []
    findings = []
    with source:
        for page, first, pitch, baseline, opening_bottom in candidates:
            try:
                confirmed = _source_confirms_blank_line(
                    source, page, first, baseline, opening_bottom,
                )
            except (OSError, RuntimeError, ValueError, IndexError):
                continue
            if confirmed:
                findings.append(AuditFinding(
                    rule_id="P016",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message="An extra blank line appears above the continuing body text.",
                    details={
                        "issue_type": _ISSUE_TYPE,
                        "bbox": format_bbox_detail(first.line.bbox),
                        "blank_baseline_pt": f"{baseline:.1f}",
                        "first_text_baseline_pt": f"{first.baseline:.1f}",
                        "body_line_pitch_pt": f"{pitch:.1f}",
                        "confidence": "high",
                    },
                ))
    return findings
