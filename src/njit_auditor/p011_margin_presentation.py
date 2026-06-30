"""Page-context-aware P011 margin warning wording and remediation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

_PAGE_CONTEXT_CONTENT_LABELS: dict[str, str] = {
    "abstract": "Abstract content",
    "approval_page": "Approval Page content",
    "references": "References content",
    "table_of_contents": "Table of Contents content",
    "list_front_matter": "list front-matter content",
    "body": "body text",
    "general": "thesis content",
}

_TEXT_PARAGRAPH_FIX = (
    "Adjust the paragraph, text wrapping, or line spacing so the highlighted text "
    "stays within the required margin."
)
_APPROVAL_DATE_FIX = (
    "Move the Date label and signature/date line layout left, or shorten the line, "
    "so all approval-page content stays within the required margin."
)
_REFERENCES_FIX = (
    "Adjust the references paragraph indentation or hanging-indent settings so all "
    "reference text stays within the required margin."
)
_FLOAT_LAYOUT_FIX = (
    "Adjust the table or figure layout so the full object stays within the required "
    "margin."
)
_GENERIC_SIDE_FIX = (
    "Move the flagged content back inside the required {side} so all thesis content "
    "stays within the allowed page area."
)


def infer_page_margin_context(page_text: str) -> str:
    upper = page_text.upper()
    if re.search(r"\bREFERENCES\b|\bBIBLIOGRAPHY\b", upper):
        return "references"
    if "APPROVAL PAGE" in upper:
        return "approval_page"
    if re.search(r"\bABSTRACT\b", upper):
        return "abstract"
    if "TABLE OF CONTENTS" in upper:
        return "table_of_contents"
    if "LIST OF TABLES" in upper or "LIST OF FIGURES" in upper:
        return "list_front_matter"
    if re.search(r"CHAPTER\s+\d", upper):
        return "body"
    return "general"


def margin_content_label(page_context: str) -> str:
    return _PAGE_CONTEXT_CONTENT_LABELS.get(page_context, "thesis content")


def infer_margin_content_kind(page_context: str, line_previews: Sequence[str]) -> str:
    previews = [preview.strip() for preview in line_previews if preview.strip()]
    if page_context == "approval_page" and any(
        re.match(r"^date\b", preview, flags=re.IGNORECASE) for preview in previews
    ):
        return "approval_date_layout"
    if page_context == "references":
        return "references_hanging_indent"
    combined = " ".join(previews).lower()
    if re.search(r"\btable\s+\d", combined) or re.search(r"\bfigure\s+\d", combined):
        return "float_layout"
    return "text_paragraph"


def margin_confidence(
    worst_overflow_pt: float,
    count: int,
    *,
    page_context: str,
    content_kind: str,
) -> str:
    if worst_overflow_pt >= 25.0:
        if page_context == "references" and content_kind == "references_hanging_indent":
            return "medium" if worst_overflow_pt < 40.0 else "high"
        return "high"
    if worst_overflow_pt >= 5.0:
        return "medium"
    if count >= 2 and worst_overflow_pt > 4.0:
        return "medium"
    if worst_overflow_pt <= 4.0:
        return "low"
    return "medium"


def margin_suggested_fix(
    *,
    page_context: str,
    content_kind: str,
    side_label: str,
) -> str:
    if content_kind == "approval_date_layout":
        return _APPROVAL_DATE_FIX
    if content_kind == "references_hanging_indent":
        return _REFERENCES_FIX
    if content_kind == "float_layout":
        return _FLOAT_LAYOUT_FIX
    if content_kind == "text_paragraph":
        return _TEXT_PARAGRAPH_FIX
    return _GENERIC_SIDE_FIX.format(side=side_label)


def margin_comment_body(
    *,
    page_label: str,
    side_label: str,
    page_context: str,
    overflow_detail: str,
    lines_clause: str,
) -> str:
    content_label = margin_content_label(page_context)
    if side_label == "required page margin":
        return (
            f"Likely problem: Some {content_label} on page {page_label} appears too close "
            "to or beyond a required page margin. The auditor could not determine the "
            f"exact margin side from the available metadata{overflow_detail}."
            f"{lines_clause}"
        )
    return (
        f"Likely problem: {content_label.capitalize()} on page {page_label} appears to "
        f"cross the required {side_label} boundary{overflow_detail}."
        f"{lines_clause}"
    )


def margin_detailed_fix_guidance(
    *,
    page_context: str,
    content_kind: str,
    side_label: str,
) -> str:
    fix = margin_suggested_fix(
        page_context=page_context,
        content_kind=content_kind,
        side_label=side_label,
    )
    return f"What to check or fix: {fix}"


def margin_expected_phrase(page_context: str) -> str:
    label = margin_content_label(page_context)
    return f"{label.capitalize()} should stay inside NJIT's required page margins"


def page_context_from_details(details: Mapping[str, str]) -> str:
    return str(details.get("page_context", "")).strip() or "general"


def content_kind_from_details(details: Mapping[str, str]) -> str:
    return str(details.get("margin_content_kind", "")).strip() or "text_paragraph"
