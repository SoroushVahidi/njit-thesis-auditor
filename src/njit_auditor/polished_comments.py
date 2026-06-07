"""Privacy-safe polished comment templates for GUI finding display."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

REVIEW_PREFIX = "Review needed:"
VERIFY_SUFFIX = "Heuristic signal — please verify against NJIT guidelines manually."

# Detail keys that may contain dissertation text and must never appear in comments.
_BLOCKED_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "observed_summary",
        "entry_text",
        "caption",
        "caption_text",
        "title",
        "title_text",
        "author",
        "author_name",
        "committee",
        "heading_text",
        "line_text",
        "body_text",
        "extracted_text",
        "annotation_text",
        "comment_text",
    }
)

_ISSUE_TEMPLATES: dict[tuple[str, str], str] = {
    ("P011", "margin_boundary_violation"): (
        "Possible text crossing the {side} margin on page {page}. "
        "Check that body text and headings respect NJIT margin requirements."
    ),
    ("P013", "page_number_candidate"): (
        "A page-number-like token was detected ({position_type}) on page {page}. "
        "Verify page numbering placement and style match NJIT requirements."
    ),
    ("P013", "p013_document_overview"): (
        "Document-level page-number pattern summary detected. "
        "Review overall page numbering consistency across the PDF."
    ),
    ("P026", "possible_body_font_family_issue"): (
        "Body text on page {page} may not use the expected font family. "
        "Compare embedded fonts against NJIT font requirements."
    ),
    ("P026", "possible_body_font_size_issue"): (
        "Body text on page {page} may not use the expected font size. "
        "Compare body text size against NJIT requirements."
    ),
    ("P030", "missing_continued_heading"): (
        "A multi-page list may be missing a continued heading on page {page}. "
        "Verify the appropriate '(Continued)' heading appears on continuation pages."
    ),
    ("P030", "toc_missing_continued_heading"): (
        "TABLE OF CONTENTS continuation on page {page} may be missing a continued heading. "
        "Verify 'TABLE OF CONTENTS (Continued)' where required."
    ),
    ("P033", "title_page_mismatch"): (
        "Title-page metadata may be inconsistent on page {page}. "
        "Manually verify title, degree line, and author block match NJIT front-matter requirements."
    ),
    ("P033", "title_consistency_mismatch"): (
        "Title consistency check flagged a possible mismatch on page {page}. "
        "Manually verify title-page fields against NJIT requirements."
    ),
    ("P034", "copyright_year_mismatch"): (
        "Copyright page year format on page {page} may need review. "
        "Confirm the copyright block includes the required year format."
    ),
    ("P034", "copyright_author_not_found"): (
        "A copyright page was detected on page {page} but author metadata could not be verified. "
        "Confirm the copyright block includes the required author format."
    ),
    ("P034", "copyright_year_not_found"): (
        "A copyright page was detected on page {page} but no year token was found. "
        "Confirm the copyright block includes the required year."
    ),
    ("P061", "lot_cross_page_entry_numbers_not_nondecreasing"): (
        "List of Tables entry numbers may not be non-decreasing across pages {page_range}. "
        "Verify cross-page numbering continuity in the LoT."
    ),
    ("P061", "lof_cross_page_entry_numbers_not_nondecreasing"): (
        "List of Figures entry numbers may not be non-decreasing across pages {page_range}. "
        "Verify cross-page numbering continuity in the LoF."
    ),
}

_RULE_FALLBACKS: dict[str, str] = {
    "P011": (
        "Possible margin or overflow issue on page {page}. "
        "Review layout against NJIT margin rules."
    ),
    "P013": (
        "Page-number candidate detected on page {page}. "
        "Review numbering placement and style."
    ),
    "P026": (
        "Possible font compliance issue on page {page}. "
        "Review fonts against NJIT requirements."
    ),
    "P030": (
        "TOC or list continued-heading issue on page {page}. "
        "Review multi-page list headings."
    ),
    "P033": (
        "Title-page consistency issue on page {page}. "
        "Review front-matter metadata manually."
    ),
    "P034": (
        "Copyright page issue on page {page}. "
        "Review copyright block format manually."
    ),
    "P061": (
        "LoT/LoF cross-page entry ordering on pages {page_range}. "
        "Review list numbering continuity."
    ),
}


@lru_cache(maxsize=1)
def _remediation_by_rule() -> dict[str, str]:
    """Load short remediation snippets from processed rule JSON (cached)."""
    rules_path = (
        Path(__file__).resolve().parents[2] / "data/processed/rules/project_added_rules.json"
    )
    if not rules_path.exists():
        return {}
    try:
        import json

        payload = json.loads(rules_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    result: dict[str, str] = {}
    if not isinstance(payload, list):
        return result
    for item in payload:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("id", "")).strip()
        remediation = str(item.get("remediation", "")).strip()
        if rule_id and remediation:
            if len(remediation) > 200:
                remediation = f"{remediation[:197]}..."
            result[rule_id] = remediation
    return result


def _safe_page_label(page: int | None) -> str:
    return str(page) if page is not None else "document level"


def _safe_page_range(details: dict[str, str]) -> str:
    start = details.get("run_start_page", "")
    end = details.get("run_end_page", "")
    if start and end and start != end:
        return f"{start}–{end}"
    if start:
        return str(start)
    return "listed pages"


def _format_template(template: str, *, page: int | None, details: dict[str, str]) -> str:
    side = details.get("side", "document") or "document"
    position_type = details.get("position_type", "unknown position") or "unknown position"
    return template.format(
        page=_safe_page_label(page),
        side=side.replace("_", " "),
        position_type=position_type.replace("_", " "),
        page_range=_safe_page_range(details),
    )


def build_polished_comment(
    *,
    rule_id: str,
    issue_type: str = "",
    severity: str = "WARNING",
    page: int | None = None,
    details: dict[str, str] | None = None,
    category: str | None = None,
) -> str:
    """Build a privacy-safe polished comment from finding metadata only."""
    safe_details = {
        k: v for k, v in (details or {}).items() if k not in _BLOCKED_DETAIL_KEYS
    }
    issue = issue_type or safe_details.get("issue_type", "")

    template = _ISSUE_TEMPLATES.get((rule_id, issue))
    if template is None:
        template = _RULE_FALLBACKS.get(
            rule_id,
            "Formatting check {rule_id} flagged issue type '{issue}' on page {page}.",
        )
        if "{rule_id}" in template:
            body = template.format(
                rule_id=rule_id,
                issue=issue or "unspecified",
                page=_safe_page_label(page),
                page_range=_safe_page_range(safe_details),
            )
        else:
            body = _format_template(template, page=page, details=safe_details)
    else:
        body = _format_template(template, page=page, details=safe_details)

    remediation = _remediation_by_rule().get(rule_id, "")
    parts = [f"{REVIEW_PREFIX} {body}"]
    if remediation and remediation not in body:
        parts.append(remediation)
    confidence = safe_details.get("confidence", "")
    triage_tier = safe_details.get("triage_tier", "")
    if confidence:
        parts.append(f"Confidence: {confidence}.")
    elif triage_tier:
        parts.append(f"Triage tier: {triage_tier}.")
    parts.append(VERIFY_SUFFIX)
    return " ".join(parts)


def contains_blocked_detail_text(comment: str, details: dict[str, str]) -> bool:
    """Return True if comment appears to quote blocked detail values (test helper)."""
    for key in _BLOCKED_DETAIL_KEYS:
        value = (details or {}).get(key, "").strip()
        if len(value) >= 8 and value in comment:
            return True
    return False
