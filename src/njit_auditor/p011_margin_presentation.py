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
_TOC_ENTRY_RIGHT_MARGIN_FIX = (
    "Adjust the Table of Contents entry wrapping, leader dots, or page-number tab stop "
    "so the entry and page number remain within the required right margin."
)
_TOC_ENTRY_BOTTOM_MARGIN_FIX = (
    "Adjust the Table of Contents pagination, spacing, or page break so TOC entries "
    "remain above the required bottom margin."
)


_REFERENCE_LINE_RE = re.compile(
    r"^[A-Z][\w\-'']+(?:,\s+[A-Z]\.)+(?:\s*,?\s+et al\.)?\s*\(\d{4}\)",
    re.IGNORECASE,
)
_TOC_ENTRY_LEADER_RE = re.compile(r"\.{2,}\s*\d{1,4}\s*$|-{3,}\s*\d{1,4}\s*$")
_TOC_ENTRY_NUMBERING_RE = re.compile(r"^[A-Z]?\d+(?:\.\d+)*\.?\s+\S")
_TOC_TRAILING_NUMBER_RE = re.compile(r"\d{1,4}\s*$")


def _looks_like_reference_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _REFERENCE_LINE_RE.match(stripped):
        return True
    return bool(re.search(r"\(\d{4}\)", stripped) and re.search(r",\s*[A-Z]", stripped))


def _reference_line_ratio(previews: Sequence[str]) -> float:
    nonempty = [preview.strip() for preview in previews if preview.strip()]
    if not nonempty:
        return 0.0
    hits = sum(1 for preview in nonempty if _looks_like_reference_line(preview))
    return hits / len(nonempty)


def _looks_like_toc_entry_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _TOC_ENTRY_LEADER_RE.search(stripped):
        return True
    return bool(
        _TOC_ENTRY_NUMBERING_RE.match(stripped) and _TOC_TRAILING_NUMBER_RE.search(stripped)
    )


def _toc_entry_ratio(previews: Sequence[str]) -> float:
    nonempty = [preview.strip() for preview in previews if preview.strip()]
    if not nonempty:
        return 0.0
    hits = sum(1 for preview in nonempty if _looks_like_toc_entry_line(preview))
    return hits / len(nonempty)


def infer_page_margin_context(
    page_text: str,
    line_previews: Sequence[str] = (),
) -> str:
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
    if _reference_line_ratio(line_previews) >= 0.5:
        return "references"
    return "general"


def margin_content_label(page_context: str) -> str:
    return _PAGE_CONTEXT_CONTENT_LABELS.get(page_context, "thesis content")


def infer_margin_content_kind(
    page_context: str,
    line_previews: Sequence[str],
    side: str = "",
) -> str:
    previews = [preview.strip() for preview in line_previews if preview.strip()]
    is_toc = page_context == "table_of_contents" or _toc_entry_ratio(previews) >= 0.5
    if is_toc:
        if side == "right_margin":
            return "toc_entry_right_margin"
        if side == "bottom_margin":
            return "toc_entry_bottom_margin"
        return "text_paragraph"
    if page_context == "approval_page" and any(
        re.match(r"^date\b", preview, flags=re.IGNORECASE) for preview in previews
    ):
        return "approval_date_layout"
    if page_context == "references" or _reference_line_ratio(previews) >= 0.5:
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
    if content_kind in ("toc_entry_right_margin", "toc_entry_bottom_margin"):
        if worst_overflow_pt <= 5.0:
            return "medium" if count >= 2 else "low"
        return "medium"
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
    if content_kind == "toc_entry_right_margin":
        return _TOC_ENTRY_RIGHT_MARGIN_FIX
    if content_kind == "toc_entry_bottom_margin":
        return _TOC_ENTRY_BOTTOM_MARGIN_FIX
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
    content_kind: str,
    overflow_detail: str,
    overflow_pt: str,
    lines_clause: str,
) -> str:
    if content_kind == "toc_entry_right_margin":
        return (
            "Likely problem: This Table of Contents entry appears to extend about "
            f"{overflow_pt} pt beyond the required right margin.{lines_clause}"
        )
    if content_kind == "toc_entry_bottom_margin":
        return (
            "Likely problem: This Table of Contents entry appears to extend about "
            f"{overflow_pt} pt below the required bottom text boundary.{lines_clause}"
        )
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
