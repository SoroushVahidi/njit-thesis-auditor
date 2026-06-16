"""Privacy-safe polished comment templates for GUI finding display."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from njit_auditor.report_outputs import derive_source_issue_type

REVIEW_PREFIX = "Review needed:"
VERIFY_SUFFIX = "Automated finding — please verify against NJIT guidelines manually."

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
        "label",
        "ref",
    }
)

_SOURCE_RULE_IDS = frozenset(
    {"P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"}
)

_ISSUE_TEMPLATES: dict[tuple[str, str], str] = {
    ("P012", "pdf_annotation_detected"): (
        "A PDF annotation or comment was detected on page {page}. "
        "Resolve or remove annotations before final submission."
    ),
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
    ("P001", "risky_command"): (
        "Risky formatting command '\\{command}' at {location}. "
        "Manual overrides can break NJIT layout requirements."
    ),
    ("P002", "duplicate_label"): (
        "Duplicate label detected at {location}. "
        "Rename one label and update related references."
    ),
    ("P003", "invalid_label"): (
        "Label format issue at {location}. "
        "Use label keys without spaces (e.g. fig:result_plot)."
    ),
    ("P004", "dangling_reference"): (
        "Reference may point to an undefined label at {location}. "
        "Define the missing label or correct the reference key."
    ),
    ("P005", "missing_caption"): (
        "Figure/table environment may be missing a \\caption at {location}. "
        "Add a descriptive caption for the float."
    ),
    ("P006", "missing_label"): (
        "Figure/table environment may be missing a \\label at {location}. "
        "Add a unique label for cross-references."
    ),
    ("P007", "caption_punctuation"): (
        "Caption punctuation may need review at {location}. "
        "End caption text with ., !, or ? as appropriate."
    ),
    ("P008", "abstract_structure"): (
        "Abstract structure issue detected at {location}. "
        "Verify abstract block presence and NJIT abstract requirements."
    ),
    ("P009", "chktex_warning"): (
        "CHKTeX linter warning at {location}. "
        "Review the flagged source pattern against NJIT formatting rules."
    ),
    ("P010", "lacheck_warning"): (
        "lacheck linter warning at {location}. "
        "Review the flagged source pattern against NJIT formatting rules."
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
    "P001": (
        "Risky formatting override at {location}. "
        "Remove manual layout commands and rely on template defaults."
    ),
    "P002": "Label/reference consistency issue at {location}. Review labels and refs.",
    "P003": "Label format issue at {location}. Review label key formatting.",
    "P004": "Unresolved reference at {location}. Verify label definitions.",
    "P005": "Figure/table caption issue at {location}. Review float captions.",
    "P006": "Figure/table label issue at {location}. Review float labels.",
    "P007": "Caption punctuation issue at {location}. Review caption endings.",
    "P008": "Abstract structure issue at {location}. Review abstract block.",
    "P009": "LaTeX linter warning at {location}. Review flagged source pattern.",
    "P010": "LaTeX linter warning at {location}. Review flagged source pattern.",
}

# project_added_rules.json's remediation field for these PDF-active rules
# references LaTeX-only syntax (\doublespacing, \pagenumbering{...}, etc.); the
# canonical file stays untouched (also used by the CLI/source audit) but the
# web/GUI-facing comment swaps in student-friendly wording. Mirrors the
# rules-page override of the same names in web_app.py's _RULE_TEXT_OVERRIDES.
_REMEDIATION_OVERRIDES: dict[str, str] = {
    "P023": (
        "Set body text to double line spacing. In Word: set paragraph line "
        "spacing to 'Double'."
    ),
    "P026": (
        "Set body text to Times New Roman 12pt throughout. Word/LibreOffice: "
        "set paragraph font to Times New Roman, size 12."
    ),
    "P028": (
        "Use lowercase Roman numerals (i, ii, iii) for front-matter numbered "
        "pages and Arabic numerals (1, 2, 3) for body pages."
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
            remediation = _REMEDIATION_OVERRIDES.get(rule_id, remediation)
            if len(remediation) > 200:
                remediation = f"{remediation[:197]}..."
            result[rule_id] = remediation
    return result


def _safe_page_label(page: int | None) -> str:
    return str(page) if page is not None else "document level"


def _safe_location_label(details: dict[str, str]) -> str:
    file_path = details.get("file", "").strip()
    line = details.get("line", "").strip()
    if file_path:
        name = Path(file_path).name
        if line:
            return f"{name}:{line}"
        return name
    return "source level"


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
    command = details.get("command", "formatting command") or "formatting command"
    return template.format(
        page=_safe_page_label(page),
        side=side.replace("_", " "),
        position_type=position_type.replace("_", " "),
        page_range=_safe_page_range(details),
        location=_safe_location_label(details),
        command=command,
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
    if rule_id in _SOURCE_RULE_IDS and not issue:
        issue = derive_source_issue_type(rule_id, safe_details)

    template = _ISSUE_TEMPLATES.get((rule_id, issue))
    if template is None:
        template = _RULE_FALLBACKS.get(
            rule_id,
            (
                "Formatting check {rule_id} flagged issue type '{issue}' at {location}."
                if rule_id in _SOURCE_RULE_IDS
                else "Formatting check {rule_id} flagged issue type '{issue}' on page {page}."
            ),
        )
        if "{rule_id}" in template:
            body = template.format(
                rule_id=rule_id,
                issue=issue or "unspecified",
                page=_safe_page_label(page),
                page_range=_safe_page_range(safe_details),
                location=_safe_location_label(safe_details),
                command=safe_details.get("command", "formatting command"),
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


# A finding's suggested_fix normally comes from a detector's own clean wording, but
# this is a defense-in-depth check: any value containing raw LaTeX-only syntax (e.g.
# from a future detector regression) is swapped for the rule's clean remediation text
# before it reaches the PDF-only web UI, rather than rendered as-is.
_RAW_LATEX_SUGGESTED_FIX_TOKENS: tuple[str, ...] = (
    "\\doublespacing",
    "\\usepackage",
    "mathptmx",
    "newtxtext",
    "newtxmath",
    "\\setstretch",
    "\\onehalfspacing",
)


def sanitize_suggested_fix_for_web(rule_id: str, suggested_fix: str) -> str:
    """Replace a suggested_fix value with clean wording if it carries raw LaTeX syntax."""
    if not suggested_fix:
        return suggested_fix
    if not any(token in suggested_fix for token in _RAW_LATEX_SUGGESTED_FIX_TOKENS):
        return suggested_fix
    fallback = _remediation_by_rule().get(rule_id, "")
    if fallback and not any(token in fallback for token in _RAW_LATEX_SUGGESTED_FIX_TOKENS):
        return fallback
    return ""
