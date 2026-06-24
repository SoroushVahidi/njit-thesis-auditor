"""Location labels and presentation dedup for high-volume grouped PDF findings."""

from __future__ import annotations

from collections.abc import Mapping, MutableSet

from njit_auditor.title_case_student_preview import _bbox_fingerprint

_MARGIN_SIDE_LABELS: dict[str, str] = {
    "left_margin": "left",
    "right_margin": "right",
    "top_margin": "top",
    "bottom_margin": "bottom",
    "left": "left",
    "right": "right",
    "top": "top",
    "bottom": "bottom",
}

_P026_FAMILY_ISSUE = "possible_body_font_family_issue"
_P026_SIZE_ISSUE = "possible_body_font_size_issue"

_GROUPED_DEDUP_RULES = frozenset({"P011", "P024", "P026", "P036", "P044", "P046"})


def is_grouped_dedup_rule(rule_id: str) -> bool:
    return rule_id in _GROUPED_DEDUP_RULES


def _page_prefix(page: int | None) -> str:
    return f"Page {page}" if page is not None else ""


def normalize_area_phrase(bbox_label: str) -> str:
    cleaned = bbox_label.strip()
    if not cleaned:
        return ""
    if cleaned.lower() == "body area":
        return "body text"
    return cleaned[0].lower() + cleaned[1:] if cleaned else cleaned


def margin_location_label(
    details: Mapping[str, str],
    page: int | None,
    *,
    bbox_label: str = "",
) -> str:
    """Return a student-facing margin location label."""
    side = _MARGIN_SIDE_LABELS.get(details.get("side", "").strip(), "")
    if side:
        area_phrase = f"{side} margin"
    elif bbox_label:
        area_phrase = normalize_area_phrase(bbox_label)
    else:
        area_phrase = "margin boundary"
    prefix = _page_prefix(page)
    if prefix:
        return f"{prefix} — {area_phrase}"
    return area_phrase


def font_location_label(
    issue_type: str,
    details: Mapping[str, str],
    page: int | None,
    *,
    bbox_label: str = "",
) -> str:
    """Return a student-facing body-font location label."""
    if issue_type == _P026_FAMILY_ISSUE:
        kind_phrase = "possible font family issue"
    elif issue_type == _P026_SIZE_ISSUE:
        kind_phrase = "possible font size issue"
    else:
        kind_phrase = "possible font issue"
    area_phrase = normalize_area_phrase(bbox_label) or "body text"
    prefix = _page_prefix(page)
    if prefix:
        return f"{prefix} — {area_phrase}, {kind_phrase}"
    return f"{area_phrase}, {kind_phrase}"


def abstract_indent_location_label(
    issue_type: str,
    details: Mapping[str, str],
    page: int | None,
    *,
    bbox_label: str = "",
) -> str:
    """Return a student-facing Abstract indentation location label."""
    if issue_type == "abstract_first_paragraph_indented":
        paragraph_phrase = "first paragraph"
    else:
        paragraph_index = details.get("paragraph_index", "").strip()
        if paragraph_index.isdigit():
            paragraph_phrase = f"paragraph {int(paragraph_index) + 1}"
        else:
            paragraph_phrase = "later paragraph"
    prefix = _page_prefix(page)
    if prefix:
        return f"{prefix} — Abstract, {paragraph_phrase}"
    if bbox_label:
        return f"Abstract, {paragraph_phrase} ({normalize_area_phrase(bbox_label)})"
    return f"Abstract, {paragraph_phrase}"


def grouped_finding_display_dedup_key(
    rule_id: str,
    issue_type: str,
    details: Mapping[str, str],
    *,
    page: int | None = None,
) -> tuple:
    """Build a presentation-layer key for exact duplicate grouped finding cards."""
    preview_token = ""
    for key in (
        "line_preview",
        "previous_entry_preview",
        "next_entry_preview",
        "affected_entry_preview",
        "flagged_word",
    ):
        value = details.get(key, "").strip()
        if value:
            preview_token = value[:40]
            break
    return (
        rule_id,
        issue_type,
        str(page) if page is not None else "",
        details.get("paragraph_index", "").strip(),
        details.get("side", "").strip(),
        details.get("entry_pair_index", "").strip(),
        details.get("entry_index", "").strip(),
        details.get("affected_entry_count", "").strip(),
        details.get("expected_or_reason", "").strip(),
        preview_token,
        _bbox_fingerprint(details.get("bbox", "").strip() or ""),
    )


def consume_grouped_finding_display_slot(
    rule_id: str,
    issue_type: str,
    details: Mapping[str, str],
    seen: MutableSet[tuple],
    *,
    page: int | None = None,
) -> bool:
    """Return True when a grouped finding should remain visible."""
    if rule_id not in _GROUPED_DEDUP_RULES:
        return True
    key = grouped_finding_display_dedup_key(rule_id, issue_type, details, page=page)
    if key in seen:
        return False
    seen.add(key)
    return True
