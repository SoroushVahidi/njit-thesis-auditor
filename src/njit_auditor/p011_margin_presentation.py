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

_ESTER_MARGIN_REMEDIATION = (
    "Set left margin to 1.5 inches and top, bottom, and right margin to 1 inch."
)

_APPROVAL_DATE_FIX = (
    "Move the Date label and signature/date line layout left, or shorten the line, "
    "so all approval-page content stays within the required margin."
)
_REFERENCES_FIX = (
    "Adjust the references paragraph formatting or hanging-indent settings, and wrap "
    "long URLs if needed, so all reference numbers and text remain within the "
    "required margin."
)
_TABLE_FIX = (
    "Reduce the table width, adjust column widths, wrap cell content, or reposition "
    "the table so it stays within the required margin."
)
_FIGURE_FIX = (
    "Resize or reposition the figure so it stays within the required margin, and "
    "check whether the caption also crosses the margin."
)
_CODE_LISTING_FIX = (
    "Wrap long lines, reduce the listing width, or adjust the listing indentation so "
    "the code stays within the required margin."
)
_TOC_FIX = (
    "Check the table-of-contents tab stops, dot leaders, indentation, and entry "
    "formatting so all entries stay within the required margin."
)
_GENERIC_FIX = (
    "Adjust the content formatting, indentation, wrapping, or object width so the "
    "highlighted material remains within the required margin."
)

# Vertical (top/bottom) margin overflow is the only case where the stored
# `side` detail itself is evidence of a vertical-spacing problem; horizontal
# (left/right) overflow is a wrapping/indentation issue, not a line-spacing one.
_VERTICAL_SIDE_LABELS = frozenset({"top margin", "bottom margin"})


def _text_paragraph_fix(*, page_context: str, side_label: str) -> str:
    if page_context == "general":
        return _GENERIC_FIX
    label = "body text" if page_context == "body" else "text"
    if side_label in _VERTICAL_SIDE_LABELS:
        clause = (
            "paragraph formatting, line spacing, indentation, manual line breaks, "
            "justification, or text wrapping"
        )
    else:
        clause = (
            "paragraph formatting, indentation, manual line breaks, justification, "
            "or text wrapping"
        )
    return f"Adjust the {clause} so the highlighted {label} remains within the required margin."


_REFERENCE_LINE_RE = re.compile(
    r"^[A-Z][\w\-'']+(?:,\s+[A-Z]\.)+(?:\s*,?\s+et al\.)?\s*\(\d{4}\)",
    re.IGNORECASE,
)

# IEEE/numeric-style reference entry, e.g. "[24]H. Oshitani, T. Kamigaki..." --
# a bracketed number immediately (optionally after whitespace) followed by a
# capital letter. Continuation pages of a numbered reference list repeat this
# shape on every entry but never carry a literal "References" heading, so this
# is the signal that identifies them.
_NUMBERED_REFERENCE_LINE_RE = re.compile(r"^\[\d{1,3}\]\s*\S")
_NUMBERED_REFERENCE_ENTRY_RE = re.compile(r"\[\d{1,3}\]\s*[A-Z]")


def _looks_like_reference_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _REFERENCE_LINE_RE.match(stripped):
        return True
    if _NUMBERED_REFERENCE_LINE_RE.match(stripped):
        return True
    return bool(re.search(r"\(\d{4}\)", stripped) and re.search(r",\s*[A-Z]", stripped))


def _reference_line_ratio(previews: Sequence[str]) -> float:
    nonempty = [preview.strip() for preview in previews if preview.strip()]
    if not nonempty:
        return 0.0
    hits = sum(1 for preview in nonempty if _looks_like_reference_line(preview))
    return hits / len(nonempty)


def _page_has_numbered_reference_entries(page_text: str) -> bool:
    # Two or more bracket-numbered entries on a page is specific to a numbered
    # reference list; a single inline body citation like "[12] Recent work..."
    # can coincidentally match the same shape once, but not repeatedly.
    return len(_NUMBERED_REFERENCE_ENTRY_RE.findall(page_text)) >= 2


def infer_page_margin_context(
    page_text: str,
    line_previews: Sequence[str] = (),
) -> str:
    upper = page_text.upper()
    if re.search(r"\bREFERENCES\b|\bBIBLIOGRAPHY\b", upper):
        return "references"
    if "APPROVAL PAGE" in upper:
        return "approval_page"
    # Checked before the single-word "ABSTRACT" match below: reference-list
    # continuation pages don't repeat the section heading, and citation URLs
    # such as "...proceedings.neurips.cc/.../hash/...-Abstract.html" contain
    # the standalone word "Abstract", which would otherwise misclassify a
    # references page as the Abstract section.
    if _page_has_numbered_reference_entries(page_text) or _reference_line_ratio(
        line_previews
    ) >= 0.5:
        return "references"
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


_LISTING_CAPTION_RE = re.compile(r"\blisting\s+\d", re.IGNORECASE)
_TABLE_CAPTION_RE = re.compile(r"\btable\s+\d", re.IGNORECASE)
_FIGURE_CAPTION_RE = re.compile(r"\bfigure\s+\d", re.IGNORECASE)


def infer_margin_content_kind(page_context: str, line_previews: Sequence[str]) -> str:
    previews = [preview.strip() for preview in line_previews if preview.strip()]
    if page_context == "approval_page" and any(
        re.match(r"^date\b", preview, flags=re.IGNORECASE) for preview in previews
    ):
        return "approval_date_layout"
    if page_context == "references" or _reference_line_ratio(previews) >= 0.5:
        return "references_hanging_indent"
    if page_context == "table_of_contents":
        return "toc_entry"
    combined = " ".join(previews)
    # Caption numbering ("Listing 3.1", "Table 2", "Figure 4") is checked in
    # this order because a listing/table page can also legitimately contain
    # the word "table" (e.g. a "truth table" inside example code).
    if _LISTING_CAPTION_RE.search(combined):
        return "code_listing"
    if _TABLE_CAPTION_RE.search(combined):
        return "table_layout"
    if _FIGURE_CAPTION_RE.search(combined):
        return "figure_layout"
    return "text_paragraph"


def _secondary_margin_fix(
    *,
    page_context: str,
    content_kind: str,
    side_label: str,
) -> str:
    if content_kind == "approval_date_layout":
        return _APPROVAL_DATE_FIX
    if content_kind == "references_hanging_indent":
        return _REFERENCES_FIX
    if content_kind == "table_layout":
        return _TABLE_FIX
    if content_kind == "figure_layout":
        return _FIGURE_FIX
    if content_kind == "code_listing":
        return _CODE_LISTING_FIX
    if content_kind == "toc_entry":
        return _TOC_FIX
    if content_kind == "text_paragraph":
        return _text_paragraph_fix(page_context=page_context, side_label=side_label)
    return _GENERIC_FIX


def margin_suggested_fix(
    *,
    page_context: str,
    content_kind: str,
    side_label: str,
) -> str:
    primary = _ESTER_MARGIN_REMEDIATION
    secondary = _secondary_margin_fix(
        page_context=page_context,
        content_kind=content_kind,
        side_label=side_label,
    )
    if secondary:
        return f"{primary} {secondary}"
    return primary


def margin_comment_body(
    *,
    page_label: str,
    side_label: str,
    page_context: str,
    overflow_detail: str,
    lines_clause: str,
) -> str:
    content_label = margin_content_label(page_context)
    strict_note = (
        " NJIT margin rules are strict: no text, table, or figure may cross a "
        "required boundary, even by a small amount."
    )
    if side_label == "required page margin":
        return (
            f"Likely problem: Some {content_label} on page {page_label} appears too close "
            "to or beyond a required page margin. The auditor could not determine the "
            f"exact margin side from the available metadata{overflow_detail}."
            f"{lines_clause}{strict_note}"
        )
    return (
        f"Likely problem: {content_label.capitalize()} on page {page_label} appears to "
        f"cross the required {side_label} boundary{overflow_detail}."
        f"{lines_clause}{strict_note}"
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
