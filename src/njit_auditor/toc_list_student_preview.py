"""Short, privacy-safe TOC/list entry snippets and gap highlight geometry."""

from __future__ import annotations

import re

from njit_auditor.pdf_models import BBox

_ENTRY_PREVIEW_MAX = 72
_LEADER_STRIP_RE = re.compile(r"\s*(?:\.\s*){2,}$")
_TRAILING_PAGE_NUM_RE = re.compile(r"\s+\d{1,4}\s*$")
_MIN_GAP_HIGHLIGHT_HEIGHT_PT = 2.0


def sanitize_toc_list_entry_preview(text: str, *, max_len: int = _ENTRY_PREVIEW_MAX) -> str:
    """Return a short, collapsed entry snippet safe for student-facing labels."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return ""
    cleaned = _LEADER_STRIP_RE.sub("", cleaned).strip()
    cleaned = _TRAILING_PAGE_NUM_RE.sub("", cleaned).strip()
    if not cleaned:
        return ""
    if len(cleaned) > max_len:
        return f"{cleaned[: max_len - 3].rstrip()}..."
    return cleaned


def gap_bbox_between_boxes(
    last_bbox: BBox,
    first_bbox: BBox,
    *,
    min_visible_height_pt: float = _MIN_GAP_HIGHLIGHT_HEIGHT_PT,
) -> BBox | None:
    """Build a highlight rectangle for the vertical whitespace between two entry lines."""
    gap_y0 = last_bbox.y1
    gap_y1 = first_bbox.y0
    if gap_y1 <= gap_y0:
        return None
    x0 = min(last_bbox.x0, first_bbox.x0)
    x1 = max(last_bbox.x1, first_bbox.x1)
    if x1 <= x0:
        return None
    height = gap_y1 - gap_y0
    if height < min_visible_height_pt:
        mid = (gap_y0 + gap_y1) / 2.0
        half = min_visible_height_pt / 2.0
        gap_y0 = mid - half
        gap_y1 = mid + half
    return BBox(x0=x0, y0=gap_y0, x1=x1, y1=gap_y1)


def between_entries_phrase(before_preview: str, after_preview: str) -> str:
    """Format a location phrase for the gap between two entries."""
    before = before_preview.strip()
    after = after_preview.strip()
    if before and after:
        return f"between '{before}' and '{after}'"
    if before:
        return f"after '{before}'"
    if after:
        return f"before '{after}'"
    return ""


def affected_entry_phrase(preview: str) -> str:
    """Format a location phrase for a single affected list entry."""
    cleaned = preview.strip()
    if not cleaned:
        return ""
    return f"affected entry: '{cleaned}'"


def spacing_entries_phrase(before_preview: str, after_preview: str) -> str:
    """Format comment wording for the two entries in a tight-spacing pair."""
    before = before_preview.strip()
    after = after_preview.strip()
    if before and after:
        return f"the entries '{before}' and '{after}'"
    if before or after:
        single = before or after
        return f"the entry '{single}' and the next consecutive entry"
    return "two consecutive entries"
