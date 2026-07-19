"""Privacy-safe page-number location phrases and presentation-layer deduplication."""

from __future__ import annotations

from collections.abc import Mapping, MutableSet

from njit_auditor.title_case_student_preview import _bbox_fingerprint

_PAGE_NUMBER_RULE_IDS = frozenset({"P013", "P019", "P022", "P028", "P029", "P037"})

_P037_SECTION_LABELS: dict[str, str] = {
    "biographical_sketch": "Biographical Sketch",
    "dedication": "Dedication",
    "acknowledgements": "Acknowledgements",
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
}

_POSITION_LABELS: dict[str, str] = {
    "bottom_center": "bottom center",
    "bottom_right": "bottom right",
    "top_center": "top center",
    "top_right": "top right",
    "other": "an unexpected location",
}

_DOCUMENT_LABEL_CONFIDENCES = frozenset({"high", "medium"})


def is_page_number_rule(rule_id: str) -> bool:
    return rule_id in _PAGE_NUMBER_RULE_IDS


def classify_visible_page_number_issue(
    rule_id: str,
    issue_type: str,
    details: Mapping[str, str],
) -> tuple[str | None, bool]:
    """Map a raw page-number finding to its student-facing issue type and visibility."""
    if rule_id == "P013":
        if issue_type == "p013_document_overview":
            return None, False
        synthetic_mapping = {
            "missing_page_number": "missing_page_number",
            "multiple_page_numbers": "duplicate_or_ambiguous_page_number",
            "inconsistent_position": "wrong_page_number_location",
            "mixed_numbering_style": "wrong_page_numbering_style",
            "sequence_gap": "wrong_page_number_sequence",
            "page_number_sequence_error": "wrong_page_number_sequence",
        }
        if issue_type != "page_number_candidate":
            return synthetic_mapping.get(issue_type), True
        try:
            candidate_count = int(details.get("candidate_count_on_page", "1") or "1")
        except ValueError:
            candidate_count = 1
        if candidate_count > 1:
            return "duplicate_or_ambiguous_page_number", True
        if details.get("position_type", "").strip() in {"top_center", "top_right", "other"}:
            return "wrong_page_number_location", True
        return None, False

    if rule_id == "P019":
        mapping = {
            "missing_page_number": "missing_page_number",
            "multiple_page_numbers": "duplicate_or_ambiguous_page_number",
            "inconsistent_position": "wrong_page_number_location",
            "mixed_numbering_style": "wrong_page_numbering_style",
            "sequence_gap": "wrong_page_number_sequence",
            "page_number_sequence_error": "wrong_page_number_sequence",
        }
        return mapping.get(issue_type), True

    if rule_id == "P022":
        if issue_type == "visible_page_number_on_no_number_page":
            return "page_number_should_be_suppressed", True
        return None, True

    if rule_id == "P028":
        mapping = {
            "frontmatter_page_number_style_issue": "wrong_page_numbering_style",
            "body_page_roman_number": "wrong_page_numbering_style",
            "frontmatter_arabic_number": "wrong_page_numbering_style",
            "arabic_number_on_frontmatter_page": "wrong_page_numbering_style",
            "uppercase_roman_on_frontmatter_page": "wrong_page_numbering_style",
            "roman_number_on_body_page": "wrong_page_numbering_style",
        }
        return mapping.get(issue_type), True

    if rule_id in {"P029", "P037"}:
        return "wrong_page_number_sequence", True

    return None, True


def _position_label(position_type: str) -> str:
    return _POSITION_LABELS.get(position_type.strip(), "an unexpected location")


def _observed_printed_page_number(details: Mapping[str, str]) -> str:
    for key in (
        "observed_sequence",
        "observed_value",
        "candidate_text",
        "observed_page_number",
        "candidate_sample",
    ):
        value = details.get(key, "").strip()
        if value:
            return value
    return ""


def _expected_printed_page_number(details: Mapping[str, str]) -> str:
    for key in ("expected_sequence", "expected_value", "expected_roman"):
        value = details.get(key, "").strip()
        if value:
            return value
    return ""


def detected_document_page_label(details: Mapping[str, str]) -> str:
    """Return the detected printed document page label when confidence is sufficient."""
    label = details.get("document_page_label", "").strip()
    if not label:
        return ""
    confidence = details.get("document_page_label_confidence", "").strip().lower()
    if confidence and confidence not in _DOCUMENT_LABEL_CONFIDENCES:
        return ""
    return label


def page_number_badge_label(
    rule_id: str,
    details: Mapping[str, str],
    page: int | None,
) -> str:
    """Return the display-only page badge for page-number findings.

    ``page`` remains the physical PDF page used for navigation. The returned
    label may include the document's own printed page label when it was detected
    directly from a page-number token.
    """
    if page is None:
        return "Document-wide"
    if not is_page_number_rule(rule_id):
        return f"Page {page}"
    label = detected_document_page_label(details)
    if label and label != str(page):
        return f"Page {label} (PDF page {page})"
    if label:
        return f"Page {label}"
    return f"PDF page {page}"


def page_number_action_suffix(
    rule_id: str,
    details: Mapping[str, str],
    page: int | None,
) -> str:
    """Return the suffix appended to PDF action buttons without duplicating 'Page'."""
    if page is None:
        return ""
    if not is_page_number_rule(rule_id):
        return str(page)
    label = detected_document_page_label(details)
    if label and label != str(page):
        return f"{label} (PDF page {page})"
    if label:
        return label
    return str(page)


def page_number_location_prefix(details: Mapping[str, str], page: int | None) -> str:
    """Return a location prefix that separates document label from physical page."""
    if page is None:
        return "Document-wide"
    label = detected_document_page_label(details)
    if label:
        return f"Document page: {label} · PDF page: {page}"
    return f"PDF page {page}"


def _p037_section_phrase(details: Mapping[str, str]) -> str:
    section_key = details.get("section_key", "").strip()
    if not section_key:
        return ""
    return _P037_SECTION_LABELS.get(section_key, section_key.replace("_", " ").title())


def page_number_location_label(
    rule_id: str,
    visible_issue_type: str | None,
    details: Mapping[str, str],
    page: int | None,
    *,
    bbox_label: str = "",
) -> str:
    """Return a student-facing Where label for a page-number warning."""
    if visible_issue_type is None:
        return ""

    if page is None:
        if visible_issue_type == "wrong_page_numbering_style":
            observed_style = details.get("observed_style", "").strip() or details.get(
                "observed_styles", ""
            ).strip()
            if observed_style:
                return (
                    "Document-wide — mixed page-numbering styles "
                    f"({observed_style})"
                )
            return "Document-wide — page-numbering style inconsistency"
        if visible_issue_type == "wrong_page_number_sequence":
            return "Document-wide — page-numbering sequence inconsistency"
        return "Document-wide page-numbering issue"

    page_prefix = page_number_location_prefix(details, page)
    section_phrase = _p037_section_phrase(details)
    section_clause = f"{section_phrase}, " if section_phrase else ""

    if visible_issue_type == "missing_page_number":
        return f"{page_prefix} — no printed page number detected"

    if visible_issue_type == "wrong_page_number_location":
        observed_location = (
            details.get("observed_location", "").strip()
            or details.get("candidate_position_label", "").strip()
            or _position_label(details.get("position_type", ""))
        )
        return f"{page_prefix} — {section_clause}page number at {observed_location}"

    if visible_issue_type == "duplicate_or_ambiguous_page_number":
        candidate_tokens = details.get("candidate_tokens", "").strip()
        if candidate_tokens:
            return f"{page_prefix} — multiple page-number candidates ({candidate_tokens})"
        sample = details.get("candidate_sample", "").strip()
        if sample:
            return (
                f"{page_prefix} — multiple page-number-like tokens "
                f"(e.g. {sample})"
            )
        return f"{page_prefix} — multiple page-number-like tokens"

    if visible_issue_type == "wrong_page_numbering_style":
        observed_style = (
            details.get("observed_style", "").strip()
            or details.get("candidate_style_label", "").strip()
            or details.get("observed_styles", "").strip()
        )
        if observed_style:
            return (
                f"{page_prefix} — {section_clause}printed page number uses "
                f"{observed_style}"
            )
        return f"{page_prefix} — {section_clause}page-numbering style mismatch"

    if visible_issue_type == "wrong_page_number_sequence":
        observed = _observed_printed_page_number(details)
        expected = _expected_printed_page_number(details)
        previous_value = details.get("previous_sequence_value", "").strip()
        next_value = details.get("next_sequence_value", "").strip()
        neighbor_bits: list[str] = []
        if previous_value:
            neighbor_bits.append(f"prev {previous_value}")
        if next_value:
            neighbor_bits.append(f"next {next_value}")
        neighbor_clause = f"; {'; '.join(neighbor_bits)}" if neighbor_bits else ""
        if observed and expected:
            return (
                f'{page_prefix} — {section_clause}printed page number "{observed}" '
                f'(expected "{expected}"{neighbor_clause})'
            )
        if observed:
            return f'{page_prefix} — {section_clause}printed page number "{observed}"'
        return page_prefix

    if visible_issue_type == "page_number_should_be_suppressed":
        return f"{page_prefix} — page number should be suppressed on this page type"

    if bbox_label:
        return f"{page_prefix} — {bbox_label}"
    return page_prefix


def page_number_display_dedup_key(
    rule_id: str,
    visible_issue_type: str,
    details: Mapping[str, str],
    *,
    page: int | None = None,
) -> tuple:
    """Build a presentation-layer key for exact duplicate page-number cards."""
    page_token = str(page) if page is not None else ""
    return (
        rule_id,
        visible_issue_type,
        page_token,
        details.get("issue_type", "").strip(),
        _observed_printed_page_number(details),
        _expected_printed_page_number(details),
        details.get("observed_style", "").strip(),
        details.get("expected_style", "").strip(),
        details.get("position_type", "").strip(),
        details.get("section_key", "").strip(),
        _bbox_fingerprint(details.get("bbox", "").strip() or ""),
    )


def consume_page_number_display_slot(
    rule_id: str,
    visible_issue_type: str,
    details: Mapping[str, str],
    seen: MutableSet[tuple],
    *,
    page: int | None = None,
) -> bool:
    """Return True when a page-number finding should remain visible."""
    key = page_number_display_dedup_key(
        rule_id, visible_issue_type, details, page=page
    )
    if key in seen:
        return False
    seen.add(key)
    return True
