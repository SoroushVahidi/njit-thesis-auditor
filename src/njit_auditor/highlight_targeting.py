"""Resolve the smallest reliable PDF highlight boxes for student-facing findings."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from itertools import zip_longest

from njit_auditor.pdf_highlight import (
    NO_RIGHT_PADDING_KIND,
    RECT_ANNOT_PADDING_PT,
    HighlightBox,
    is_drawable_bbox,
)
from njit_auditor.pdf_models import BBox, PdfTextLine, format_bbox_detail

_BBOX_PARTS = 4


# Keep lookarounds aligned with title-case tokenization so PDF ligatures
# (ﬀ/ﬁ/ﬂ/ﬃ/ﬄ) count as letters and cannot host a short-token false match.
_WORD_BOUNDARY_LETTER = r"A-Za-zﬀﬁﬂﬃﬄ"


def _whole_word_match(target: str, haystack: str) -> re.Match[str] | None:
    """Find *target* as a standalone token in *haystack*.

    When *target* begins or ends with a letter, letter lookarounds are required
    so a short/single-letter token is never matched inside a larger word (the
    flagged "n" in "(n = 97)" must never resolve to the "n" in "Linear"). A plain
    search is used only for fully non-alphabetic targets (e.g. numbers/symbols).
    """
    escaped = re.escape(target)
    if target[:1].isalpha() or target[-1:].isalpha():
        return re.search(
            rf"(?<![{_WORD_BOUNDARY_LETTER}]){escaped}(?![{_WORD_BOUNDARY_LETTER}])",
            haystack,
            flags=re.IGNORECASE,
        )
    return re.search(escaped, haystack, flags=re.IGNORECASE)
_TOKEN_HIGHLIGHT_RULES: frozenset[tuple[str, str]] = frozenset(
    {
        ("P020", "possible_title_capitalization_issue"),
        ("P017", "possible_sentence_case_issue"),
        ("P027", "level3_sentence_case_issue"),
        ("P027", "level4_sentence_case_issue"),
        ("P027", "level5_sentence_case_issue"),
        ("P027", "level4_sentence_case_or_punctuation_issue"),
        ("P027", "level5_sentence_case_or_punctuation_issue"),
    }
)
_P035_PLACEMENT_ISSUES: frozenset[str] = frozenset(
    {
        "figure_caption_not_below_body",
        "table_caption_not_above_body",
    }
)
_EXTRA_BBOX_KEYS: tuple[str, ...] = (
    "body_bbox",
    "caption_bbox",
    "candidate_year_bbox",
    "token_bbox",
    "word_bbox",
    "rect",
)


_P011_MARGIN_ISSUE = "margin_boundary_violation"


def _parse_bbox_text(raw: str) -> tuple[float, float, float, float] | None:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != _BBOX_PARTS:
        return None
    try:
        box = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
    except ValueError:
        return None
    return box if is_drawable_bbox(box) else None


def _parse_bbox_list(raw: str) -> list[tuple[float, float, float, float]]:
    """Parse a " | "-separated list of "x0,y0,x1,y1" boxes (see pdf_margins.py)."""
    boxes: list[tuple[float, float, float, float]] = []
    for chunk in raw.split("|"):
        parsed = _parse_bbox_text(chunk.strip())
        if parsed is not None:
            boxes.append(parsed)
    return boxes


def _union_boxes(
    boxes: Sequence[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    drawable = [box for box in boxes if is_drawable_bbox(box)]
    if not drawable:
        return None
    return (
        min(box[0] for box in drawable),
        min(box[1] for box in drawable),
        max(box[2] for box in drawable),
        max(box[3] for box in drawable),
    )


def word_bbox_in_line(line: PdfTextLine, word: str) -> BBox | None:
    """Return the tightest bbox covering *word* inside *line*, when spans allow it."""
    target = word.strip()
    if not target or not line.text.strip():
        return None

    haystack = line.text
    match = _whole_word_match(target, haystack)
    if match is None:
        return None
    start, end = match.start(), match.end()
    if start >= end:
        return None

    cursor = 0
    start_box: BBox | None = None
    end_box: BBox | None = None
    for span in line.spans:
        span_text = span.text
        if not span_text:
            continue
        span_start = cursor
        span_end = cursor + len(span_text)
        if start_box is None and span_end > start:
            start_box = span.bbox
        if span_start < end:
            end_box = span.bbox
        cursor = span_end

    if start_box is None or end_box is None:
        return None
    return BBox(
        x0=min(start_box.x0, end_box.x0),
        y0=min(start_box.y0, end_box.y0),
        x1=max(start_box.x1, end_box.x1),
        y1=max(start_box.y1, end_box.y1),
    )


def estimate_word_bbox_in_line_bbox(
    line_bbox: tuple[float, float, float, float],
    line_text: str,
    word: str,
) -> tuple[float, float, float, float] | None:
    """Estimate a word-sized bbox from a full-line box when span data is unavailable."""
    target = word.strip()
    cleaned = line_text.strip()
    if not target or not cleaned or not is_drawable_bbox(line_bbox):
        return None
    match = _whole_word_match(target, cleaned)
    if match is None:
        return None
    start, end = match.start(), match.end()
    if end <= start or not cleaned:
        return None
    x0, y0, x1, y1 = line_bbox
    width = x1 - x0
    if width <= 0:
        return None
    char_width = width / max(len(cleaned), 1)
    word_x0 = x0 + start * char_width
    word_x1 = x0 + end * char_width
    box = (word_x0, y0, word_x1, y1)
    return box if is_drawable_bbox(box) else None


def _token_specific_bbox(
    details: Mapping[str, str],
    *,
    rule_id: str,
    issue_type: str,
    line_bbox: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float] | None:
    if (rule_id, issue_type) not in _TOKEN_HIGHLIGHT_RULES:
        return None
    for key in ("token_bbox", "word_bbox"):
        parsed = _parse_bbox_text(str(details.get(key, "")).strip())
        if parsed is not None:
            return parsed
    flagged_word = str(details.get("flagged_word", "")).strip()
    if not flagged_word or line_bbox is None:
        return None
    preview = (
        str(details.get("line_preview", "")).strip()
        or str(details.get("affected_entry_preview", "")).strip()
    )
    return estimate_word_bbox_in_line_bbox(line_bbox, preview, flagged_word)


def parse_highlight_bboxes_from_details(
    details: Mapping[str, str],
    *,
    rule_id: str = "",
    issue_type: str = "",
) -> list[tuple[float, float, float, float]]:
    """Return every drawable highlight box encoded in finding details."""
    if rule_id == "P011" and issue_type == _P011_MARGIN_ISSUE:
        line_boxes = _parse_bbox_list(str(details.get("highlight_bboxes", "")).strip())
        if line_boxes:
            result: list[tuple[float, float, float, float]] = [
                HighlightBox.from_tuple(box, kind="line") for box in line_boxes
            ]
            display_boxes = _parse_bbox_list(
                str(details.get("overflow_display_bboxes", "")).strip()
            )
            overflow_boxes = _parse_bbox_list(
                str(details.get("overflow_segment_bboxes", "")).strip()
            )
            for display_box, overflow_box in zip_longest(display_boxes, overflow_boxes):
                if display_box is not None and display_box != overflow_box:
                    result.append(HighlightBox.from_tuple(display_box, kind="overflow_display"))
                if overflow_box is not None:
                    result.append(HighlightBox.from_tuple(overflow_box, kind="overflow"))
            guide_boxes = _parse_bbox_list(str(details.get("margin_boundary_bboxes", "")).strip())
            if not guide_boxes:
                guide_box = _parse_bbox_text(str(details.get("margin_boundary_bbox", "").strip()))
                if guide_box is not None:
                    guide_boxes = [guide_box]
            result.extend(HighlightBox.from_tuple(box, kind="guide") for box in guide_boxes)
            return result

    # Findings that name several separate targets (e.g. each unindented TOC
    # entry for P039) list them in highlight_bboxes; draw those instead of
    # their union bbox, which would also cover correctly formatted lines.
    target_boxes = _parse_bbox_list(str(details.get("highlight_bboxes", "")).strip())
    if target_boxes:
        return target_boxes

    boxes: list[tuple[float, float, float, float]] = []
    line_bbox = _parse_bbox_text(str(details.get("bbox", "")).strip())
    if line_bbox is None:
        line_bbox = _parse_bbox_text(str(details.get("rect", "")).strip())
    if line_bbox is not None:
        if rule_id == "P054":
            try:
                leader_x = float(details.get("highlight_right_limit", ""))
            except ValueError:
                leader_x = None
            if leader_x is not None and line_bbox[2] <= leader_x <= (
                line_bbox[2] + RECT_ANNOT_PADDING_PT
            ):
                return [HighlightBox.from_tuple(line_bbox, kind=NO_RIGHT_PADDING_KIND)]
        boxes.append(line_bbox)
    for key in _EXTRA_BBOX_KEYS:
        if key in {"token_bbox", "word_bbox"}:
            continue
        parsed = _parse_bbox_text(str(details.get(key, "")).strip())
        if parsed is not None:
            boxes.append(parsed)

    if rule_id == "P035" and issue_type in _P035_PLACEMENT_ISSUES:
        placement_boxes = [
            box
            for box in (
                _parse_bbox_text(str(details.get("body_bbox", "")).strip()),
                _parse_bbox_text(str(details.get("caption_bbox", "")).strip()),
            )
            if box is not None
        ]
        if placement_boxes:
            return placement_boxes

    token_bbox = _token_specific_bbox(
        details,
        rule_id=rule_id,
        issue_type=issue_type,
        line_bbox=line_bbox,
    )
    if token_bbox is not None:
        return [token_bbox]

    deduped: list[tuple[float, float, float, float]] = []
    seen: set[tuple[float, float, float, float]] = set()
    for box in boxes:
        rounded: tuple[float, float, float, float] = (
            round(box[0], 1),
            round(box[1], 1),
            round(box[2], 1),
            round(box[3], 1),
        )
        if rounded in seen:
            continue
        seen.add(rounded)
        deduped.append(box)
    return deduped


def resolve_primary_highlight_bbox(
    details: Mapping[str, str],
    *,
    rule_id: str = "",
    issue_type: str = "",
) -> tuple[float, float, float, float] | None:
    """Return the primary bbox used for highlight availability and location metadata."""
    boxes = parse_highlight_bboxes_from_details(
        details,
        rule_id=rule_id,
        issue_type=issue_type,
    )
    # Report models carry plain geometry. Rendering kinds stay on draw targets.
    return _union_boxes(boxes)


def format_optional_bbox_detail(bbox: BBox | tuple[float, float, float, float] | None) -> str:
    if bbox is None:
        return ""
    return format_bbox_detail(bbox)
