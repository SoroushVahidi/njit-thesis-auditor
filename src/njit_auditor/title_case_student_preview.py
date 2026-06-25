"""Short, privacy-safe title-case line snippets and P020 display deduplication."""

from __future__ import annotations

import re
from collections.abc import Mapping, MutableSet

_LINE_PREVIEW_MAX = 72
_BBOX_PARTS = 4
_BBOX_ROUND_DIGITS = 1

_TABLE_PREFIX_RE = re.compile(r"^table\s+\d+(?:\.\d+)*\s*", re.IGNORECASE)


def sanitize_title_case_line_preview(text: str, *, max_len: int = _LINE_PREVIEW_MAX) -> str:
    """Return a short, collapsed heading/table-title snippet safe for student-facing text."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return ""
    cleaned = _TABLE_PREFIX_RE.sub("", cleaned).strip()
    if not cleaned:
        return ""
    if len(cleaned) > max_len:
        return f"{cleaned[: max_len - 3].rstrip()}..."
    return cleaned


def title_case_subject_kind(source: str) -> str:
    """Return a short subject label for a P020 finding's `source` field."""
    return "table title" if source == "caption" else "heading"


def affected_title_phrase(preview: str, *, source: str) -> str:
    """Format a location phrase for the affected heading or table title."""
    cleaned = preview.strip()
    if not cleaned:
        return ""
    subject = title_case_subject_kind(source)
    return f'{subject} "{cleaned}"'


def _bbox_fingerprint(bbox_text: str) -> tuple[float, ...] | None:
    parts = [part.strip() for part in bbox_text.split(",")]
    if len(parts) != _BBOX_PARTS:
        return None
    try:
        return tuple(round(float(part), _BBOX_ROUND_DIGITS) for part in parts)
    except ValueError:
        return None


def p020_display_dedup_key(details: Mapping[str, str], *, page: int | None = None) -> tuple:
    """Build a presentation-layer key for exact duplicate P020 cards."""
    page_token = str(page) if page is not None else details.get("page_number", "").strip()
    preview = sanitize_title_case_line_preview(details.get("line_preview", "")).casefold()
    return (
        details.get("issue_type", "").strip(),
        page_token,
        preview,
        details.get("flagged_word", "").strip(),
        details.get("corrected_word", "").strip(),
        details.get("expected_or_reason", "").strip(),
        details.get("source", "").strip(),
    )


def p020_short_suggested_fix(
    flagged_word: str,
    corrected_word: str,
    line_preview: str,
) -> str:
    preview = sanitize_title_case_line_preview(line_preview)
    if preview and flagged_word:
        pattern = re.compile(re.escape(flagged_word), re.IGNORECASE)
        if pattern.search(preview):
            updated = pattern.sub(corrected_word, preview, count=1)
            return f'Change "{preview}" to "{updated}".'
    if flagged_word and corrected_word:
        return f'Change "{flagged_word}" to "{corrected_word}" in this heading.'
    return "Correct the flagged word capitalization in this heading."


def p020_short_likely_problem(flagged_word: str, corrected_word: str) -> str:
    if flagged_word and corrected_word:
        return (
            f"Likely problem: In this heading, '{flagged_word}' should be "
            f"capitalized as '{corrected_word}'."
        )
    return "Likely problem: A word in this heading may not follow Title Case."


def consume_p020_display_slot(
    details: Mapping[str, str],
    seen: MutableSet[tuple],
    *,
    page: int | None = None,
) -> bool:
    """Return True when a P020 finding should remain visible; suppress exact duplicates."""
    key = p020_display_dedup_key(details, page=page)
    if key in seen:
        return False
    seen.add(key)
    return True
