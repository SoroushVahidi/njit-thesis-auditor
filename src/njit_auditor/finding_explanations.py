"""Student-facing detailed explanations and action metadata for finding types.

This module is a presentation-layer helper only. It never changes detection
semantics, thresholds, rule IDs, or stored finding data.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Action kind / label helpers
# ---------------------------------------------------------------------------

_ACTION_HIGHLIGHT = "highlight"
_ACTION_PAGE = "page"
_ACTION_EXPLANATION = "explanation"

_LABEL_HIGHLIGHT = "Open highlighted PDF page"
_LABEL_PAGE = "Open PDF page"
_LABEL_EXPLANATION = "Read explanation"

_NO_HIGHLIGHT_PAGE_REASON = (
    "Exact highlight is not available for this finding, but the relevant page is known."
)
_NO_HIGHLIGHT_DOC_REASON = (
    "This finding is document-level and does not correspond to a specific page or visual location."
)


def get_action_kind(*, has_bbox: bool, page: int | None) -> str:
    """Return the preferred action kind for a finding."""
    if has_bbox:
        return _ACTION_HIGHLIGHT
    if page is not None:
        return _ACTION_PAGE
    return _ACTION_EXPLANATION


def get_action_label(*, has_bbox: bool, page: int | None) -> str:
    """Return the button label for a finding's primary action."""
    if has_bbox:
        return _LABEL_HIGHLIGHT
    if page is not None:
        return _LABEL_PAGE
    return _LABEL_EXPLANATION


def get_no_highlight_reason(*, has_bbox: bool, page: int | None) -> str:
    """Return a student-facing reason why no exact highlight is available."""
    if has_bbox:
        return ""
    if page is not None:
        return _NO_HIGHLIGHT_PAGE_REASON
    return _NO_HIGHLIGHT_DOC_REASON


# ---------------------------------------------------------------------------
# Per-issue-type explanation templates
# ---------------------------------------------------------------------------

_EXPLANATION_TEMPLATES: dict[tuple[str, str], str] = {
    # --- P011 margins ---
    ("P011", "margin_boundary_violation"): (
        "Some content appears too close to or beyond the required page margin "
        "({side_label}). "
        "NJIT requires: left margin 1.5 inches, right margin 1 inch, "
        "top and bottom margins 1 inch. "
        "Review the highlighted area or the listed page and adjust layout, "
        "indentation, tables, figures, or long lines."
    ),
    # --- P012 annotations ---
    ("P012", "pdf_annotation_detected"): (
        "This PDF contains an annotation, comment, sticky note, markup, or "
        "similar review object ({annotation_type_label}). "
        "These should usually be resolved or removed before final submission. "
        "Open the PDF in your editor and accept, reject, or delete all reviewer "
        "comments before resubmitting."
    ),
    # --- P013 page number candidates ---
    ("P013", "page_number_candidate"): (
        "A page-number-like token was detected in the {position_type_label} area "
        "of this page. "
        "NJIT requires page numbers to appear at the bottom center or top right, "
        "using lowercase Roman numerals (i, ii, iii) for front matter "
        "and Arabic numerals (1, 2, 3) for body pages. "
        "Verify that the page number is in the required position and uses the "
        "correct style."
    ),
    ("P013", "p013_document_overview"): (
        "This is a document-level summary of page-number patterns detected across "
        "the PDF. It does not correspond to a specific page or visual location. "
        "Review the individual page-number findings for details on specific pages."
    ),
    ("P013", "missing_page_number"): (
        "A page that should carry a page number appears to be missing one. "
        "NJIT requires every numbered page to display a visible page number. "
        "Check this page in the PDF and add a page number if it is missing."
    ),
    ("P013", "multiple_page_numbers"): (
        "Multiple page-number-like tokens were detected on this page. "
        "A page should have exactly one page number. "
        "Review the page and remove any duplicate or extraneous page numbers."
    ),
    ("P013", "inconsistent_position"): (
        "Page numbers appear in inconsistent positions across pages. "
        "NJIT requires page numbers to be consistently positioned (e.g., always "
        "bottom center). "
        "Standardize the position of all page numbers throughout the document."
    ),
    ("P013", "mixed_numbering_style"): (
        "Page numbers appear to use a mix of Roman and Arabic numerals on what "
        "should be a single numbering-regime page. "
        "Front matter must use lowercase Roman numerals (i, ii, iii); "
        "body pages must use Arabic numerals (1, 2, 3). "
        "Review the page-numbering style and correct any inconsistencies."
    ),
    ("P013", "sequence_gap"): (
        "The page-number sequence appears to have a gap or jump on this page. "
        "Page numbers must be consecutive with no skipped values. "
        "Review the affected pages and renumber them to restore the sequence."
    ),
    # --- P019 page number validation ---
    ("P019", "page_number_sequence_error"): (
        "The page-number sequence appears broken or inconsistent at this page. "
        "Check whether page numbers skip values, repeat, or switch regimes "
        "incorrectly. "
        "NJIT requires: front matter uses lowercase Roman numerals (i, ii, iii), "
        "body pages use Arabic numerals starting from 1."
    ),
    ("P019", "missing_page_number"): (
        "A page that should carry a page number appears to be missing one. "
        "NJIT requires every numbered page to display a visible page number."
    ),
    ("P019", "multiple_page_numbers"): (
        "Multiple page-number-like tokens were detected on this page. "
        "A page should have exactly one page number. "
        "Review and remove any duplicate or extraneous page numbers."
    ),
    # --- P021 abstract word count ---
    ("P021", "abstract_word_count_exceeded"): (
        "The abstract appears to contain {word_count} words. "
        "For the detected degree type ({degree_label}), the allowed maximum is "
        "{limit} words. "
        "This is {over_by} words over the limit. "
        "Note: if the abstract spans multiple pages, the word count shown may be "
        "an undercount. "
        "Review the abstract text and shorten it before submission."
    ),
    # --- P022 frontmatter no page number ---
    ("P022", "frontmatter_page_has_page_number"): (
        "A front-matter page that should not be numbered appears to have a visible "
        "page number. "
        "NJIT requires the title page and certain other front-matter pages to "
        "appear unnumbered. "
        "Remove the page number from this page."
    ),
    # --- P023 body spacing ---
    ("P023", "body_spacing_issue"): (
        "Body text on this page appears to be single-spaced or less than "
        "double-spaced. "
        "NJIT requires all body text to be double-spaced throughout. "
        "Set the paragraph line spacing to 'Double' in Word, or use the equivalent "
        "setting in your editor."
    ),
    ("P023", "excessive_line_gap"): (
        "Unusually large spacing was detected between lines on this page. "
        "Body text should be double-spaced with consistent spacing. "
        "Review for extra blank lines or manual spacing overrides."
    ),
    ("P023", "excessive_paragraph_gap"): (
        "Unusually large spacing was detected between paragraphs on this page. "
        "Paragraph spacing should be consistent with double-spaced body text. "
        "Review for extra blank lines or manual paragraph-spacing overrides."
    ),
    # --- P026 font compliance ---
    ("P026", "possible_body_font_family_issue"): (
        "This page contains body-text spans whose embedded PDF font does not appear "
        "to be Times New Roman or an accepted Times-compatible font. "
        "NJIT expects body text to use Times New Roman 12pt throughout. "
        "Review the highlighted text or the listed page and update the source "
        "document font settings."
    ),
    ("P026", "possible_body_font_size_issue"): (
        "This page contains body-text spans outside the expected 12pt range "
        "(11–13 pt). "
        "NJIT expects body text to be 12pt. "
        "Review the highlighted text or the listed page and correct the font size."
    ),
    # --- P027 heading level style ---
    ("P027", "heading_style_issue"): (
        "A heading on this page may not match the expected NJIT heading style "
        "(e.g., bold, capitalization, or font size). "
        "Review the heading formatting and compare it against the NJIT style "
        "guidelines for chapter and section headings."
    ),
    # --- P028 page numbering regime ---
    ("P028", "frontmatter_page_number_style_issue"): (
        "This page appears to use a page number that does not match the expected "
        "numbering regime. "
        "NJIT requires front-matter pages to use lowercase Roman numerals "
        "(i, ii, iii) and body pages to use Arabic numerals (1, 2, 3). "
        "Review the page and correct the numbering style."
    ),
    ("P028", "body_page_roman_number"): (
        "A body page appears to use a Roman numeral page number instead of an "
        "Arabic numeral. "
        "Body pages must use Arabic numerals (1, 2, 3). "
        "Review and correct the page-number style."
    ),
    ("P028", "frontmatter_arabic_number"): (
        "A front-matter page appears to use an Arabic numeral page number instead "
        "of a Roman numeral. "
        "Front-matter numbered pages must use lowercase Roman numerals (i, ii, iii). "
        "Review and correct the page-number style."
    ),
    # --- P029 roman sequence ---
    ("P029", "roman_sequence_gap"): (
        "The Roman numeral sequence in the front matter appears to have a gap or "
        "inconsistency at this page. "
        "Front-matter page numbers should be consecutive lowercase Roman numerals "
        "(i, ii, iii, …). "
        "Review the front-matter page numbering and correct the sequence."
    ),
    # --- P030 TOC continued headings ---
    ("P030", "missing_continued_heading"): (
        "A multi-page table of contents, List of Tables, or List of Figures "
        "continuation page may be missing the required '(Continued)' heading. "
        "NJIT requires continuation pages to include a repeated heading such as "
        "'TABLE OF CONTENTS (Continued)'. "
        "Add the required heading to the top of this continuation page."
    ),
    ("P030", "toc_missing_continued_heading"): (
        "The TABLE OF CONTENTS continuation page may be missing a "
        "'TABLE OF CONTENTS (Continued)' heading. "
        "NJIT requires this heading to appear at the top of every TOC continuation "
        "page. "
        "Add the required heading."
    ),
    # --- P033 title consistency ---
    ("P033", "title_page_mismatch"): (
        "Title-page metadata may be inconsistent or incomplete. "
        "Manually verify the title, degree line, and author block against NJIT "
        "front-matter requirements. "
        "Common issues include a missing department/program line, an incorrect "
        "degree phrase, or a title that differs from the abstract or body."
    ),
    ("P033", "title_consistency_mismatch"): (
        "The title detected on the title page may not match the title found in other "
        "parts of the document. "
        "Manually verify that all occurrences of the title (title page, abstract, "
        "header) are identical."
    ),
    ("P033", "frontmatter_title_mismatch"): (
        "Title-page metadata may be inconsistent with front-matter content. "
        "Review the title page fields and ensure they match throughout the document."
    ),
    # --- P034 copyright page ---
    ("P034", "copyright_year_mismatch"): (
        "The copyright page year format may not match the expected NJIT format. "
        "The copyright page should include the current year in the standard format "
        "(e.g., Copyright © 2025 First Last). "
        "Review the copyright page and confirm the year is present and correct."
    ),
    ("P034", "copyright_author_not_found"): (
        "A copyright page was detected but the author name could not be verified. "
        "The copyright page must include the student's full legal name. "
        "Review the copyright page and ensure the author name is present and "
        "correct."
    ),
    ("P034", "copyright_year_not_found"): (
        "A copyright page was detected but no year token was found. "
        "The copyright page must include the current year in the required format. "
        "Review the copyright page and add the required year."
    ),
    ("P034", "copyright_author_mismatch"): (
        "The author name on the copyright page may not match the author name "
        "detected elsewhere in the document. "
        "Ensure that the author name on the copyright page is the student's full "
        "legal name and matches the name used throughout."
    ),
    ("P034", "copyright_top_margin_header_text"): (
        "Text was detected in the top margin area of the copyright page. "
        "The copyright page typically should not have header text or running heads. "
        "Review the copyright page layout."
    ),
    # --- P038 frontmatter headings ---
    ("P038", "heading_phrase_not_exact"): (
        "A required front-matter section heading may not match the exact expected "
        "phrase. "
        "NJIT requires specific section headings (e.g., 'ABSTRACT', "
        "'TABLE OF CONTENTS', 'REFERENCES'). "
        "Review the heading text and correct it to match the expected wording "
        "exactly."
    ),
    # --- P041 dedication ---
    ("P041", "dedication_top_margin_header_text"): (
        "Text was detected in the top margin area of the dedication page. "
        "The dedication page typically should not have header text or running heads. "
        "Review the dedication page layout."
    ),
    ("P041", "dedication_text_not_centered"): (
        "The dedication text does not appear to be centered horizontally. "
        "NJIT requires dedication text to be centered on the page. "
        "Adjust the text alignment."
    ),
    ("P041", "dedication_text_not_italic"): (
        "The dedication text does not appear to be italicized. "
        "NJIT requires dedication text to be in italic font. "
        "Apply italic formatting to the dedication text."
    ),
    # --- P063 appendix/body headings ---
    ("P063", "appendix_letter_sequence_gap"): (
        "The appendix letter sequence appears to have a gap (e.g., jumps from "
        "Appendix A to Appendix C without a B). "
        "NJIT requires appendices to be lettered consecutively (A, B, C, …). "
        "Review the appendix headings and ensure the lettering sequence is complete."
    ),
    ("P063", "appendix_letter_sequence_repeat"): (
        "An appendix letter appears to be repeated. "
        "NJIT requires each appendix to have a unique letter. "
        "Review the appendix headings and correct the labeling."
    ),
    ("P063", "multiple_appendix_missing_letter"): (
        "Multiple appendices are present but one or more may be missing a letter "
        "designation (e.g., 'Appendix' without 'A', 'B', etc.). "
        "NJIT requires all appendices to be clearly labeled (Appendix A, "
        "Appendix B, …). "
        "Add the required letter to each appendix heading."
    ),
    # --- P064 references structural ---
    ("P064", "references_structural_issue"): (
        "The references or citations section may have a structural issue. "
        "This finding covers the structure of the references section as a whole "
        "rather than a specific highlighted span. "
        "Review the references section against NJIT citation formatting requirements."
    ),
    # --- P065 dedication centering/italic ---
    ("P065", "dedication_text_not_centered"): (
        "The dedication text does not appear to be centered horizontally on the page. "
        "NJIT requires dedication text to be centered. "
        "Adjust the text alignment."
    ),
    ("P065", "dedication_text_not_italic"): (
        "The dedication text does not appear to be italicized. "
        "NJIT requires dedication text to be in italic font. "
        "Apply italic formatting to the dedication text."
    ),
    # --- P078 abstract keywords ---
    ("P078", "abstract_pdf_forbidden_term"): (
        "The abstract contains a term that is not appropriate for an NJIT thesis or "
        "dissertation abstract (e.g., 'paper', 'article'). "
        "Review the abstract and replace the flagged term with more appropriate "
        "academic wording."
    ),
    ("P078", "abstract_pdf_first_person_pronoun"): (
        "The abstract contains a first-person pronoun (e.g., 'I', 'we', 'my'). "
        "NJIT abstracts should typically be written in third person. "
        "Review the abstract and revise any first-person phrasing."
    ),
}

# Rule-level fallback explanations (used when issue_type not matched above,
# or for grouped-problem cards where a single finding-level explanation
# is not appropriate).
_RULE_FALLBACKS: dict[str, str] = {
    "P011": (
        "Some content appears too close to or beyond the required page margin. "
        "NJIT requires: left 1.5 inches, right 1 inch, top and bottom 1 inch. "
        "Review the highlighted area or the listed page and adjust layout, "
        "indentation, tables, figures, or long lines."
    ),
    "P012": (
        "This PDF contains an annotation, comment, sticky note, markup, or "
        "similar review object. "
        "These should usually be resolved or removed before final submission. "
        "Open the PDF in your editor and accept, reject, or delete all reviewer "
        "comments before resubmitting."
    ),
    "P013": (
        "This finding concerns page-numbering style, placement, sequence, or "
        "presence. "
        "Check whether the page number appears in the required position and whether "
        "front matter uses lowercase Roman numerals while the main body uses "
        "Arabic numerals."
    ),
    "P019": (
        "This finding concerns page-numbering style, placement, sequence, or "
        "presence. "
        "Check whether the page number appears in the required position and whether "
        "front matter uses lowercase Roman numerals while the main body uses "
        "Arabic numerals."
    ),
    "P021": (
        "The abstract appears to exceed the allowed word count for the detected "
        "degree type. "
        "NJIT limits: PhD abstracts to 350 words, MS abstracts to 150 words. "
        "Review the abstract text and shorten it before submission."
    ),
    "P022": (
        "A front-matter page that should not carry a page number may have one. "
        "Remove visible page numbers from unnumbered front-matter pages such as "
        "the title page."
    ),
    "P023": (
        "Body text on this page may not be double-spaced as required by NJIT "
        "guidelines. "
        "Set the paragraph line spacing to 'Double' throughout the body of the "
        "document."
    ),
    "P026": (
        "Body text on this page may not use the expected font (Times New Roman 12pt). "
        "NJIT expects body text to use Times New Roman 12pt throughout. "
        "Review the highlighted text or the listed page and update the font settings "
        "in your source document."
    ),
    "P027": (
        "A heading on this page may not match the expected NJIT heading style. "
        "Review heading formatting (bold, capitalization, font size) against the "
        "NJIT style guidelines."
    ),
    "P028": (
        "Page numbering on this page may not follow the required NJIT regime. "
        "Use lowercase Roman numerals (i, ii, iii) for front-matter numbered pages "
        "and Arabic numerals (1, 2, 3) for body pages."
    ),
    "P029": (
        "The Roman numeral page-number sequence in the front matter may be "
        "inconsistent. "
        "Front-matter numbered pages should use consecutive lowercase Roman numerals."
    ),
    "P030": (
        "A multi-page table of contents or list may be missing a continuation "
        "heading. "
        "NJIT requires '(Continued)' headings on continuation pages for the TOC, "
        "List of Tables, and List of Figures."
    ),
    "P033": (
        "Title-page metadata may be inconsistent or incomplete. "
        "Manually verify title, degree line, and author information against NJIT "
        "front-matter requirements."
    ),
    "P034": (
        "The copyright page may have a formatting issue. "
        "Review the copyright page and confirm that the year and author name are "
        "in the required format."
    ),
    "P038": (
        "A required front-matter section heading may be missing or not recognized. "
        "Review the document structure and ensure all required headings are present "
        "and worded exactly as NJIT specifies."
    ),
    "P041": (
        "The dedication page may have a formatting issue (centering, italic style, "
        "or header text). "
        "Review the dedication page against NJIT requirements."
    ),
    "P063": (
        "An appendix or body heading may have a formatting or ordering issue. "
        "Review appendix headings against NJIT requirements for labeling and "
        "chapter/section heading style."
    ),
    "P064": (
        "The references or citations section may have a structural issue. "
        "Review the references section against NJIT citation formatting requirements."
    ),
    "P065": (
        "The dedication text may not meet NJIT formatting requirements "
        "(centering and italic style). "
        "Review the dedication page."
    ),
    "P078": (
        "The abstract may contain wording that does not meet NJIT guidelines "
        "(forbidden terms or first-person pronouns). "
        "Review the abstract and revise the flagged wording."
    ),
}

_GENERIC_FALLBACK = (
    "This finding was generated by an automated formatting check. "
    "Review the flagged page or area against the NJIT thesis/dissertation "
    "formatting guidelines before submission."
)


def _humanize_issue_type(issue_type: str) -> str:
    """Convert a snake_case issue type to a readable phrase for fallback text."""
    return issue_type.replace("_", " ").strip()


def _resolve_issue_type(rule_id: str, issue_type: str, details: dict[str, str]) -> str:
    """Normalize the effective issue_type for explanation lookup.

    Some rules (e.g. P021) do not set issue_type in their details dict.
    For those cases, derive the effective issue_type from other detail keys.
    """
    if issue_type:
        return issue_type
    # P021 — abstract word count: identify by word_count + limit keys
    if rule_id == "P021" and details.get("word_count") and details.get("limit"):
        return "abstract_word_count_exceeded"
    return issue_type


def build_detailed_explanation(
    *,
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    page: int | None,
) -> str:
    """Build a student-facing detailed explanation for a finding.

    Returns a non-empty string in all cases. Never reproduces dissertation body
    text, author names, or raw LaTeX.
    """
    effective_issue_type = _resolve_issue_type(rule_id, issue_type, details)
    template = _EXPLANATION_TEMPLATES.get((rule_id, effective_issue_type))

    if template is not None:
        # Substitute known safe details into the template.
        annotation_type = details.get("annotation_type", "annotation")
        annotation_type_label = (
            annotation_type
            if annotation_type and annotation_type != "Unknown"
            else "annotation"
        )
        side = details.get("side", "")
        side_label = side.replace("_", " ") if side else "page margin"

        position_type = details.get("position_type", "")
        position_type_label = position_type.replace("_", " ") if position_type else "margin"

        # P021-specific
        word_count_raw = details.get("word_count", "")
        limit_raw = details.get("limit", "")
        inferred_degree = details.get("inferred_degree_type", "unknown")
        degree_label = _format_degree_label(inferred_degree)

        try:
            word_count = int(word_count_raw) if word_count_raw else None
            limit = int(limit_raw) if limit_raw else None
            over_by = (
                (word_count - limit)
                if (word_count is not None and limit is not None)
                else None
            )
        except ValueError:
            word_count = None
            limit = None
            over_by = None

        try:
            result = template.format(
                annotation_type_label=annotation_type_label,
                side_label=side_label,
                position_type_label=position_type_label,
                word_count=word_count or "unknown",
                limit=limit or "unknown",
                over_by=over_by or "unknown",
                degree_label=degree_label,
                worst_overflow_pt=details.get("worst_overflow_pt", ""),
                page=page if page is not None else "unknown",
            )
        except (KeyError, ValueError):
            result = template

        return result.strip()

    # Rule-level fallback
    fallback = _RULE_FALLBACKS.get(rule_id)
    if fallback:
        return fallback.strip()

    # Generic fallback with humanized issue_type
    if issue_type:
        return (
            f"This automated check flagged an issue of type "
            f"'{_humanize_issue_type(issue_type)}'. "
            f"Review the finding and verify it against NJIT formatting requirements."
        )
    return _GENERIC_FALLBACK


def build_group_explanation(
    *,
    rule_id: str,
    issue_type: str,
) -> str:
    """Return a group-level explanation for a grouped problem card.

    Uses the rule-level fallback rather than per-finding details, since a
    grouped card spans multiple findings with varying detail values.
    """
    fallback = _RULE_FALLBACKS.get(rule_id)
    if fallback:
        return fallback.strip()
    if issue_type:
        return (
            f"These findings were grouped under the automated check for "
            f"'{_humanize_issue_type(issue_type)}'. "
            f"Review each example against NJIT formatting requirements."
        )
    return _GENERIC_FALLBACK


def _format_degree_label(inferred_degree: str) -> str:
    mapping = {
        "phd": "PhD",
        "ms": "MS",
        "unknown": "PhD (degree type uncertain — using PhD limit as default)",
    }
    return mapping.get(inferred_degree.lower(), inferred_degree.upper() or "unknown")
