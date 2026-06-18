"""Privacy-safe polished comment templates for GUI finding display."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from njit_auditor.issue_type_explanations import humanize_issue_type
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
    ("P013", "p013_document_overview"): (
        "Document-level page-number pattern summary detected (informational; "
        "not a page-specific defect). Review the individual page-number "
        "findings below for anything that needs manual verification."
    ),
    ("P019", "missing_page_number"): (
        "Page {page} appears to be missing a visible page number, even though "
        "neighboring pages have one. NJIT requires every counted page to "
        "display a visible page number. Verify whether a page number is "
        "missing on this page."
    ),
    ("P019", "multiple_page_numbers"): (
        "Multiple page-number-like tokens were detected on page {page}. A "
        "page should show exactly one page number. Verify which token is the "
        "actual page number and remove or correct any unintended duplicate."
    ),
    ("P019", "inconsistent_position"): (
        "The page-number position on page {page} does not match the dominant "
        "position used elsewhere in the document. NJIT requires page numbers "
        "to be consistently positioned at the bottom of the page. Verify the "
        "page-number placement on this page."
    ),
    ("P019", "mixed_numbering_style"): (
        "Mixed page-numbering styles (e.g., Roman and Arabic numerals) were "
        "detected on page {page}. NJIT requires front-matter pages to use "
        "lowercase Roman numerals and body pages to use Arabic numerals, not "
        "a mix within the same section. Verify the numbering style here."
    ),
    ("P019", "sequence_gap"): (
        "The page-number sequence appears to skip or break around page "
        "{page}. NJIT requires page numbers to increase consecutively with "
        "no gaps. Verify that no pages were removed, duplicated, or "
        "misnumbered near this page."
    ),
    ("P022", "visible_page_number_on_no_number_page"): (
        "A visible page number was detected on the {page_type} page (page "
        "{page}). NJIT requires this page to have no visible page number, "
        "even though it is counted in the page sequence. Remove the page "
        "number from this page."
    ),
    ("P028", "arabic_number_on_frontmatter_page"): (
        "Page {page} is in the front matter but shows an Arabic-numeral page "
        "number ('{candidate_text}'). NJIT requires front-matter pages to use "
        "lowercase Roman numerals (i, ii, iii) instead. Correct the numbering "
        "style for this page."
    ),
    ("P028", "uppercase_roman_on_frontmatter_page"): (
        "Page {page} is in the front matter but shows an uppercase Roman "
        "numeral page number ('{candidate_text}'). NJIT requires lowercase "
        "Roman numerals (i, ii, iii) in the front matter. Correct the "
        "numbering style for this page."
    ),
    ("P028", "roman_number_on_body_page"): (
        "Page {page} is in the main body but shows a Roman-numeral page "
        "number ('{candidate_text}'). NJIT requires body pages to use Arabic "
        "numerals (1, 2, 3) instead. Correct the numbering style for this "
        "page."
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
    ("P063", "single_appendix_uses_letter_label"): (
        "The single appendix heading on page {page} is labeled 'APPENDIX "
        "{letter_found}' with a letter. NJIT requires a single appendix to "
        "be labeled 'APPENDIX' with no letter. Remove the letter, or add the "
        "missing appendix heading(s) if the document actually has more than "
        "one appendix."
    ),
    ("P063", "multiple_appendix_missing_letter"): (
        "An appendix heading on page {page} is missing its letter "
        "identifier. NJIT requires every appendix to be labeled 'APPENDIX "
        "A,' 'APPENDIX B,' etc. when there is more than one. Add the "
        "missing letter to this heading."
    ),
    ("P063", "appendix_letter_sequence_gap"): (
        "The appendix letter sequence on page {page} skips a letter (e.g., "
        "jumps from A to C without a B). NJIT requires appendices to be "
        "lettered consecutively. Correct the lettering sequence."
    ),
    ("P063", "appendix_letter_sequence_repeat"): (
        "The appendix heading on page {page} repeats a letter already used "
        "by another appendix. NJIT requires each appendix to have a unique "
        "letter. Correct the labeling so each letter is used once."
    ),
    # --- P027 heading-level style: one template per level, never combined ---
    ("P027", "level1_not_all_caps"): (
        "A Level 1 heading (CHAPTER/APPENDIX title) on page {page} may not be in "
        "ALL CAPS. NJIT requires Level 1 headings to be ALL CAPS, bold, and centered."
    ),
    ("P027", "level2_title_case_issue"): (
        "A Level 2 heading (e.g. 1.1, 1.2) on page {page} may not use Title Case. "
        "NJIT requires Level 2 headings to use Title Case, bold."
    ),
    ("P027", "level3_sentence_case_issue"): (
        "A Level 3 heading (e.g. 1.1.1) on page {page} may use Title Case where "
        "Sentence case is expected. NJIT requires Level 3 headings to use Sentence "
        "case (only the first word capitalized), bold."
    ),
    ("P027", "level4_sentence_case_issue"): (
        "A Level 4 heading (e.g. 1.1.1.1) on page {page} may use Title Case where "
        "Sentence case is expected. NJIT requires Level 4 headings to use Sentence "
        "case, ending with a period."
    ),
    ("P027", "level4_sentence_case_or_punctuation_issue"): (
        "A Level 4 heading (e.g. 1.1.1.1) on page {page} may be missing its "
        "required terminal period. NJIT requires Level 4 headings to end with a "
        "period."
    ),
    ("P027", "level5_sentence_case_issue"): (
        "A Level 5 heading (e.g. 1.1.1.1.1) on page {page} may use Title Case "
        "where Sentence case is expected. NJIT requires Level 5 headings to use "
        "Sentence case, ending with a period."
    ),
    ("P027", "level5_sentence_case_or_punctuation_issue"): (
        "A Level 5 heading (e.g. 1.1.1.1.1) on page {page} may be missing its "
        "required terminal period. NJIT requires Level 5 headings to end with a "
        "period."
    ),
    # --- P025 front-matter structure: one template per required element ---
    ("P025", "missing_abstract_body"): (
        "An ABSTRACT heading was found on page {page}, but no body text was "
        "detected below it. NJIT requires the Abstract page to contain the "
        "abstract text beneath the heading."
    ),
    ("P025", "missing_title_page_degree_phrase"): (
        "No degree phrase (e.g. 'Doctor of Philosophy', 'Master of Science') was "
        "detected on the title page. NJIT requires the title page to state the "
        "degree being conferred."
    ),
    ("P025", "missing_title_page_institution"): (
        "The institution name was not detected on the title page. NJIT requires "
        "the title page to include 'New Jersey Institute of Technology'."
    ),
    ("P025", "sparse_approval_page_content"): (
        "An APPROVAL PAGE heading was found on page {page}, but the content "
        "below it appears sparse ({substantial_line_count} substantial lines "
        "detected). NJIT requires the Approval Page to include committee member "
        "names, titles, and signature lines."
    ),
    ("P025", "possible_frontmatter_order_issue"): (
        "The ABSTRACT heading appears on page {page}, after the TABLE OF "
        "CONTENTS on page {toc_page}. NJIT requires the Abstract to appear "
        "before the Table of Contents."
    ),
    # --- P038 front-matter exact headings: one template per failure mode ---
    ("P038", "required_heading_missing"): (
        "The required front-matter heading '{expected_heading}' was not found "
        "anywhere in the document."
    ),
    ("P038", "heading_phrase_not_exact"): (
        "A front-matter heading on page {page} uses a non-canonical wording "
        "variant. NJIT requires the exact canonical phrase '{expected_heading}'."
    ),
    # --- P023 body spacing ---
    ("P023", "possible_body_text_not_double_spaced"): (
        "Body text on page {page} appears to be single-spaced or less than "
        "double-spaced. NJIT requires all body text to be double-spaced "
        "throughout."
    ),
    # --- P016 paragraph/line spacing gaps ---
    ("P016", "excessive_line_gap"): (
        "Unusually large spacing was detected between lines on page {page}. "
        "Body text should be double-spaced with consistent spacing throughout."
    ),
    ("P016", "excessive_paragraph_gap"): (
        "Unusually large spacing was detected between paragraphs on page "
        "{page}. Paragraph spacing should be consistent with double-spaced "
        "body text."
    ),
    ("P016", "suspicious_heading_blank_gap"): (
        "An unusually large blank gap was detected just before a heading on "
        "page {page}. Verify this is intentional heading spacing and not an "
        "extra blank line or page-break artifact."
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
        "Page-number candidate detected on page {page} for manual "
        "verification. This does not by itself confirm a formatting defect."
    ),
    "P019": (
        "Page-numbering sequence or style issue detected on page {page}. "
        "Review numbering placement, style, and sequence against NJIT "
        "requirements."
    ),
    "P022": (
        "A visible page number was detected on page {page} where NJIT "
        "requires none. Review whether this page should show a page number."
    ),
    "P028": (
        "Page-numbering style on page {page} may not match the expected "
        "regime for its section. Review whether this page should use Roman "
        "or Arabic numerals."
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
    # P013's comment body already states the verification action for every
    # branch (see _p013_candidate_comment); appending the canonical
    # remediation line on top would repeat "verify..." a third time.
    "P013": "",
}

# Per-issue-type remediation overrides, checked before _REMEDIATION_OVERRIDES /
# _remediation_by_rule(). Needed for rules whose catalog remediation combines
# guidance for several distinct sub-cases into one sentence (e.g. P027 covers
# five heading levels, P025 covers four front-matter elements): appending that
# combined sentence to a single-issue finding would re-describe levels/elements
# that do not apply here. An empty string means "this finding's comment body
# already states the complete fix; do not append anything else."
_ISSUE_REMEDIATION_OVERRIDES: dict[tuple[str, str], str] = {
    ("P020", "possible_title_capitalization_issue"): "",
    ("P027", "level1_not_all_caps"): "",
    ("P027", "level2_title_case_issue"): "",
    ("P027", "level3_sentence_case_issue"): "",
    ("P027", "level4_sentence_case_issue"): "",
    ("P027", "level4_sentence_case_or_punctuation_issue"): "",
    ("P027", "level5_sentence_case_issue"): "",
    ("P027", "level5_sentence_case_or_punctuation_issue"): "",
    ("P025", "missing_abstract_body"): (
        "Add the abstract body text directly below the ABSTRACT heading."
    ),
    ("P025", "missing_title_page_degree_phrase"): (
        "Add the degree phrase to the title page (e.g. 'Doctor of Philosophy' "
        "or 'Master of Science')."
    ),
    ("P025", "missing_title_page_institution"): (
        "Add 'New Jersey Institute of Technology' to the title page."
    ),
    ("P025", "sparse_approval_page_content"): (
        "Add the committee member names, titles, and signature lines to the "
        "Approval Page."
    ),
    ("P025", "possible_frontmatter_order_issue"): (
        "Move the Abstract so it appears before the Table of Contents."
    ),
    ("P038", "required_heading_missing"): (
        "Add this required section heading to the front matter, worded "
        "exactly as NJIT specifies."
    ),
    ("P038", "heading_phrase_not_exact"): (
        "Correct this heading to use the exact canonical NJIT phrase."
    ),
}

_NO_ISSUE_OVERRIDE = object()


def _resolve_remediation(rule_id: str, issue_type: str) -> str:
    """Return the remediation text to append, preferring an issue-specific override."""
    override = _ISSUE_REMEDIATION_OVERRIDES.get((rule_id, issue_type), _NO_ISSUE_OVERRIDE)
    if override is not _NO_ISSUE_OVERRIDE:
        return str(override)
    return _remediation_by_rule().get(rule_id, "")


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
    page_type = details.get("page_type", "") or "this"
    return template.format(
        page=_safe_page_label(page),
        side=side.replace("_", " "),
        position_type=position_type.replace("_", " "),
        page_range=_safe_page_range(details),
        location=_safe_location_label(details),
        command=command,
        candidate_text=details.get("candidate_text", "") or "unknown",
        page_type=page_type.replace("_", " "),
        letter_found=details.get("letter_found", "") or "A",
        expected_heading=details.get("expected_heading", "") or "the required heading",
        toc_page=details.get("toc_page", "") or "unknown",
        substantial_line_count=details.get("substantial_line_count", "") or "0",
    )


def _p013_candidate_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P013 page_number_candidate comment body.

    P013 only ever records a detected token's position/style — it has no
    notion of "correct" on its own. The wording must therefore say what was
    observed and frame it as a verification signal, not a confirmed defect,
    except when the position itself is outside the bottom area NJIT requires.
    """
    page_label = _safe_page_label(page)
    try:
        count = int(details.get("candidate_count_on_page", "1") or "1")
    except ValueError:
        count = 1
    position_type = details.get("position_type", "") or ""

    if count > 1:
        return (
            f"Multiple page-number-like tokens were detected on page "
            f"{page_label}. This may indicate duplicate numbering, extra "
            "footer/header text being mistaken for a page number, or an "
            "ambiguous page-number location. Verify which token is the "
            "actual page number and remove or correct any unintended "
            "duplicate."
        )
    if position_type in {"bottom_center", "bottom_right"}:
        position_label = position_type.replace("_", " ")
        return (
            f"A page-number-like token was detected at the {position_label} "
            f"of page {page_label}. This finding records the detected page "
            "number for manual verification; it does not by itself confirm "
            "a formatting defect. Verify that the number is correct, "
            "visible, in the required bottom position, and consistent with "
            "the document's numbering sequence."
        )
    if position_type in {"top_center", "top_right", "other"}:
        return (
            "A page-number-like token was detected outside the expected "
            f"bottom page-number area on page {page_label}. NJIT page "
            "numbers should appear in the required bottom position. Verify "
            "the page-number placement and correct it if necessary."
        )
    return (
        f"A page-number-like token was detected on page {page_label}. No "
        "specific page-numbering defect is confirmed by this finding; it is "
        "a manual-verification signal. Verify that the number is correct, "
        "visible, and in the required bottom position."
    )


_TITLE_CASE_REASON_TEXT: dict[str, str] = {
    "first_word_requires_capital": "the first word is not capitalized",
    "word_after_separator_requires_capital": (
        "a word after a colon, dash, or similar separator is not capitalized"
    ),
    "major_word_requires_capital": "a major word (4+ letters) is not capitalized",
}


def _p020_title_case_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P020 possible_title_capitalization_issue comment body.

    P020 covers two unrelated kinds of title-like text (Level 2 headings and
    table titles) under one issue_type. Branching on the line's recorded
    `source` keeps the comment scoped to the one rule that actually applies,
    instead of describing both at once. The flagged word itself is never
    quoted here — only the violation category from `expected_or_reason`.
    """
    page_label = _safe_page_label(page)
    source = details.get("source", "") or "heading"
    reason = details.get("expected_or_reason", "") or ""
    reason_text = _TITLE_CASE_REASON_TEXT.get(reason, "a word is not capitalized as expected")
    if source == "caption":
        subject = "table title"
        rule_text = "NJIT requires table titles to use Title Case"
    else:
        subject = "Level 2 heading"
        rule_text = "NJIT requires Level 2 headings (e.g. 1.1, 1.2) to use Title Case"
    return (
        f"Possible title-case issue in a {subject} on page {page_label}: "
        f"{reason_text}. {rule_text} (capitalize the first word, last word, "
        "and all major words of 4+ letters)."
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

    if rule_id == "P013" and issue == "page_number_candidate":
        body = _p013_candidate_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, details=safe_details)

    if rule_id == "P020" and issue == "possible_title_capitalization_issue":
        body = _p020_title_case_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, details=safe_details)

    template = _ISSUE_TEMPLATES.get((rule_id, issue))
    if template is None:
        template = _RULE_FALLBACKS.get(rule_id)
        if template is None:
            issue_label = humanize_issue_type(issue).lower() if issue else "formatting"
            if rule_id in _SOURCE_RULE_IDS:
                body = (
                    f"This check ({rule_id}) found a possible {issue_label} issue "
                    f"at {_safe_location_label(safe_details)}."
                )
            else:
                body = (
                    f"This check ({rule_id}) found a possible {issue_label} issue "
                    f"on page {_safe_page_label(page)}."
                )
            return _finish_comment(body, rule_id=rule_id, issue_type=issue, details=safe_details)
        body = _format_template(template, page=page, details=safe_details)
    else:
        body = _format_template(template, page=page, details=safe_details)

    return _finish_comment(body, rule_id=rule_id, issue_type=issue, details=safe_details)


def _finish_comment(
    body: str, *, rule_id: str, issue_type: str = "", details: dict[str, str]
) -> str:
    remediation = _resolve_remediation(rule_id, issue_type)
    parts = [f"{REVIEW_PREFIX} {body}"]
    if remediation and remediation not in body:
        parts.append(remediation)
    confidence = details.get("confidence", "")
    triage_tier = details.get("triage_tier", "")
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
