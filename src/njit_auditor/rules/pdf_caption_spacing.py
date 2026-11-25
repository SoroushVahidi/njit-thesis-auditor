"""Measure consistently wide leading in confidently owned body captions."""

import re
from itertools import pairwise
from math import isfinite
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_caption_continuations import (
    CaptionFragment,
    PageCaptionEnd,
    _font_family,
    _horizontal,
)
from njit_auditor.rules.pdf_captions import CaptionLine, _terminal_punctuation

ISSUE_TYPE = "excessive_caption_line_spacing"

# Empirical evidence gates. These ratios are detection cutoffs, not NJIT
# point values or a way to recover a word processor setting from a PDF.
_MIN_PITCH_IN_FONT_SIZES = 1.8
_MIN_PITCH_IN_LINE_HEIGHTS = 1.4
_MAX_RELATIVE_PITCH_VARIATION = 0.05
_METRIC_TOLERANCE_PT = 0.5
_NAMED_SUBPART = re.compile(r"^\s*(?:legend|key|source|notes?)\s*:", re.IGNORECASE)


def _font(line: PdfTextLine) -> tuple[str, float] | None:
    baseline = line.baseline_y
    if baseline is None or not isfinite(baseline) or not _horizontal(line):
        return None
    spans = [span for span in line.spans if span.text.strip()]
    if not spans:
        return None
    fonts: set[str] = set()
    sizes: list[float] = []
    for span in spans:
        size, origin = span.size, span.baseline_y
        if (
            not span.font or size is None or not isfinite(size) or size <= 0
            or origin is None or not isfinite(origin)
            or abs(origin - baseline) > _METRIC_TOLERANCE_PT
        ):
            return None
        fonts.add(_font_family(span.font).removesuffix("roman"))
        sizes.append(size)
    if len(fonts) != 1 or "" in fonts or max(sizes) - min(sizes) > _METRIC_TOLERANCE_PT:
        return None
    return next(iter(fonts)), max(sizes)


def check_page_caption_spacing(caption: CaptionLine, end: PageCaptionEnd) -> AuditFinding | None:
    """Return one advisory when at least two uniform internal gaps are wide."""
    rows = end.lines
    if not end.resolved or len(rows) < 3:
        return None
    # Sentences can start separate caption paragraphs. Do not infer internal
    # wrap spacing across a possible paragraph boundary.
    if any(_terminal_punctuation(row.text.rstrip()) for row in rows[:-1]) or any(
        _NAMED_SUBPART.match(row.text) for row in rows[1:]
    ):
        return None

    fonts = [_font(row) for row in rows]
    if any(font is None for font in fonts) or len({font[0] for font in fonts if font}) != 1:
        return None
    sizes = [font[1] for font in fonts if font]
    size = max(sizes)
    if size - min(sizes) > _METRIC_TOLERANCE_PT:
        return None
    pitches: list[float] = []
    for upper, lower in pairwise(rows):
        if upper.baseline_y is None or lower.baseline_y is None:
            return None
        pitch = lower.baseline_y - upper.baseline_y
        height = max(upper.bbox.height, lower.bbox.height)
        if (
            not isfinite(pitch) or not isfinite(height)
            or min(upper.bbox.height, lower.bbox.height) <= 0
            or pitch < _MIN_PITCH_IN_FONT_SIZES * size
            or pitch < _MIN_PITCH_IN_LINE_HEIGHTS * height
        ):
            return None
        pitches.append(pitch)
    if max(pitches) - min(pitches) > _MAX_RELATIVE_PITCH_VARIATION * median(pitches):
        return None

    subject = "figure description" if caption.caption_type == "figure" else "table title"
    return AuditFinding(
        rule_id="P017",
        severity=Severity.WARNING,
        page=caption.page_number,
        message=(
            f"The wrapped {subject} appears to have wide internal line spacing "
            f"(median baseline distance {median(pitches):.1f} pt)."
        ),
        details={
            "issue_type": ISSUE_TYPE,
            "page_number": str(caption.page_number),
            "caption_type": caption.caption_type,
            "confidence": "high",
            "caption_line_count": str(len(rows)),
            "caption_font_size_pt": f"{size:.2f}",
            "caption_median_baseline_distance_pt": f"{median(pitches):.2f}",
            "suggested_fix": f"Apply single line spacing within the highlighted {subject}.",
            "bbox": format_bbox_detail(CaptionFragment(caption.page_number, rows).bbox),
            "highlight_bboxes": " | ".join(format_bbox_detail(row.bbox) for row in rows),
        },
    )
