"""Short, privacy-safe TOC/list entry snippets and gap highlight geometry."""

from __future__ import annotations

import re

from njit_auditor.p018_guidance import (
    P018_MISSING_PAGE_NUMBER_FIX,
    P018_WRAPPED_TITLE_FIX,
)
from njit_auditor.pdf_models import BBox

_ENTRY_PREVIEW_MAX = 72
_LEADER_DOTS_RE = re.compile(r"\.{2,}")
_LEADER_STRIP_RE = re.compile(r"\s*(?:\.\s*){2,}$")
_TRAILING_PAGE_NUM_RE = re.compile(r"\s+\d{1,4}\s*$")
_MIN_GAP_HIGHLIGHT_HEIGHT_PT = 2.0

_TOC_EXPORT_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?$"
)
_TOC_EXPORT_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_TOC_STRUCTURAL_COLUMN_LABELS = frozenset(
    {
        "CHAPTER",
        "CHAPTERS",
        "CHAPTER PAGE",
        "CHAPTERS PAGE",
        "PAGE",
        "PAGES",
        "TITLE",
        "TITLE PAGE",
        "TABLE",
        "TABLE PAGE",
        "TABLES",
        "TABLES PAGE",
        "FIGURE",
        "FIGURE PAGE",
        "FIGURES",
        "FIGURES PAGE",
    }
)


def is_toc_structural_column_label(text: str) -> bool:
    """Return True when text looks like a TOC/list column header, not a real entry."""
    normalized = " ".join(text.strip().split()).upper().rstrip(".:")
    return normalized in _TOC_STRUCTURAL_COLUMN_LABELS


def is_toc_export_metadata_line(text: str) -> bool:
    """Return True when text looks like export/log timestamp metadata, not a real entry."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return False
    if _TOC_EXPORT_DATETIME_RE.match(normalized):
        return True
    return bool(_TOC_EXPORT_DATE_ONLY_RE.match(normalized))


def sanitize_toc_list_entry_preview(text: str, *, max_len: int = _ENTRY_PREVIEW_MAX) -> str:
    """Return a short, collapsed entry snippet safe for student-facing labels."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return ""
    cleaned = _LEADER_DOTS_RE.sub(" ", cleaned).strip()
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


def p018_entry_location_suffix(preview: str) -> str:
    """Format a P018 location suffix for one affected list entry."""
    cleaned = sanitize_toc_list_entry_preview(preview)
    if not cleaned:
        return ""
    return f'entry "{cleaned}"'


def between_entries_phrase(before_preview: str, after_preview: str) -> str:
    """Format a location phrase for the gap between two entries."""
    before = sanitize_toc_list_entry_preview(before_preview)
    after = sanitize_toc_list_entry_preview(after_preview)
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
    before = sanitize_toc_list_entry_preview(before_preview)
    after = sanitize_toc_list_entry_preview(after_preview)
    if before and after:
        return f"the entries '{before}' and '{after}'"
    if before or after:
        single = before or after
        return f"the entry '{single}' and the next consecutive entry"
    return "two consecutive entries"


def p036_short_likely_problem(before_preview: str, after_preview: str) -> str:
    before = sanitize_toc_list_entry_preview(before_preview)
    after = sanitize_toc_list_entry_preview(after_preview)
    if before and after:
        return (
            f"Likely problem: There does not appear to be visible double spacing "
            f"or a blank line between '{before}' and '{after}'."
        )
    return (
        "Likely problem: There does not appear to be visible double spacing or a "
        "blank line between these consecutive entries."
    )


def p036_short_suggested_fix() -> str:
    return (
        "Add visible double spacing or a blank line between consecutive entries in "
        "the TOC, List of Tables, or List of Figures."
    )


_P018_SHORT_LIKELY: dict[str, str] = {
    "misaligned_page_number_column": (
        "Likely problem: This entry's page number does not align with the dominant "
        "column on this list page."
    ),
    "missing_page_number": (
        "Likely problem: This entry appears to be missing its trailing page number."
    ),
    "inconsistent_leader_dots": (
        "Likely problem: Leader-dot spacing before this entry's page number is "
        "inconsistent with nearby entries."
    ),
    "inconsistent_hierarchy_indent": (
        "Likely problem: This entry is indented differently from other entries at "
        "the same hierarchy level."
    ),
    "wrapped_title_continuation_misaligned": (
        "Likely problem: A continuation line of this wrapped title starts left "
        "of the first word of the title text."
    ),
    "title_to_leader_gap_too_wide": (
        "Likely problem: The leader dots for this entry start after a visible gap "
        "instead of right after the title."
    ),
    "leader_dots_before_final_title_line": (
        "Likely problem: The leader dots for this wrapped entry appear on an "
        "earlier line instead of after the final line of the title."
    ),
}

_P018_SHORT_FIX: dict[str, str] = {
    "misaligned_page_number_column": (
        "Align this entry's page number with the dominant right-hand column on this "
        "list page."
    ),
    "missing_page_number": P018_MISSING_PAGE_NUMBER_FIX,
    "inconsistent_leader_dots": (
        "Make the leader-dot spacing before this entry's page number match nearby "
        "entries."
    ),
    "inconsistent_hierarchy_indent": (
        "Align this entry's left indent with the other TOC entries at the same level."
    ),
    "wrapped_title_continuation_misaligned": P018_WRAPPED_TITLE_FIX,
    "title_to_leader_gap_too_wide": (
        "Start the leader dots right after the last letter of the title, leaving no "
        "more than one space."
    ),
    "leader_dots_before_final_title_line": (
        "Place the leader dots after the final line of the title."
    ),
}


def p018_short_likely_problem(issue_type: str) -> str:
    return _P018_SHORT_LIKELY.get(
        issue_type,
        "Likely problem: This TOC or list entry may not match NJIT formatting on this page.",
    )


def p018_short_suggested_fix(issue_type: str, fallback: str = "") -> str:
    return _P018_SHORT_FIX.get(issue_type, fallback)
