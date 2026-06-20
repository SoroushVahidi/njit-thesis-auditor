"""Student-facing detailed explanations and action metadata for finding types.

This module is a presentation-layer helper only. It never changes detection
semantics, thresholds, rule IDs, or stored finding data.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Action kind / label helpers
# ---------------------------------------------------------------------------

_ACTION_HIGHLIGHT = "highlight"
_ACTION_ORIGINAL_PAGE = "original_page"
_ACTION_EXPLANATION = "explanation"

_LABEL_HIGHLIGHT = "Open highlighted PDF page"
_LABEL_ORIGINAL_PAGE = "Open original PDF page"
_LABEL_EXPLANATION = "Read explanation"

_NO_HIGHLIGHT_DOC_REASON = (
    "This finding is document-level and does not correspond to a specific page or visual location."
)


def get_action_kind(*, has_highlight: bool, page: int | None) -> str:
    """Return the action kind for a finding.

    Actionability policy:
    - real visible highlight -> "highlight"
    - no highlight, but page known -> "original_page"
    - no page -> "explanation"
    """
    if has_highlight:
        return _ACTION_HIGHLIGHT
    if page is not None:
        return _ACTION_ORIGINAL_PAGE
    return _ACTION_EXPLANATION


def get_action_label(*, has_highlight: bool, page: int | None) -> str:
    """Return the button label for a finding's primary action."""
    if has_highlight:
        return _LABEL_HIGHLIGHT
    if page is not None:
        return _LABEL_ORIGINAL_PAGE
    return _LABEL_EXPLANATION


def _humanize_safe_label(raw: str) -> str:
    return raw.replace("_", " ").strip()


def _location_phrase(
    *, page: int | None, location_label: str, details: dict[str, str]
) -> str:
    parts: list[str] = []
    if page is not None:
        parts.append(f"on page {page}")
    location = location_label.strip()
    if location:
        parts.append(f"near the {location.lower()}")
    page_type = (
        details.get("page_type_label", "").strip()
        or details.get("page_type", "").strip()
        or details.get("section_type", "").strip()
    )
    if page_type:
        parts.append(f"in the {_humanize_safe_label(page_type)} section")
    if not parts:
        return "in this document"
    return " ".join(parts)


def _inspection_target(rule_id: str, issue_type: str, details: dict[str, str]) -> str:
    caption_type = _humanize_safe_label(details.get("caption_type", ""))
    page_type = _humanize_safe_label(
        details.get("page_type_label", "")
        or details.get("page_type", "")
        or details.get("section_type", "")
    )
    if rule_id == "P017" and caption_type:
        return f"the {caption_type} caption area"
    if rule_id in {"P013", "P019", "P022", "P028", "P029", "P037"}:
        return "the page-number region"
    if rule_id == "P011":
        side = _humanize_safe_label(details.get("side", ""))
        return f"the {side} area" if side else "the page-margin area"
    if rule_id in {"P020", "P027", "P038", "P063"}:
        return "the heading area"
    if caption_type:
        return f"the {caption_type} caption area"
    if "caption" in issue_type:
        return "the caption area"
    if "heading" in issue_type or "title" in issue_type:
        return "the heading area"
    if "margin" in issue_type:
        return "the page-margin area"
    if page_type:
        return f"the {page_type} section"
    return "the flagged area"


def build_no_highlight_guidance(
    *,
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    page: int | None,
    location_label: str = "",
) -> str:
    """Return a precise student-facing fallback when no exact highlight exists."""
    if page is None:
        return _NO_HIGHLIGHT_DOC_REASON
    location = _location_phrase(page=page, location_label=location_label, details=details)
    target = _inspection_target(rule_id, issue_type, details)
    return (
        f"No exact highlight is available, but this finding is {location}. "
        f"Open the original PDF page and inspect {target}."
    )


def get_no_highlight_reason(
    *,
    has_highlight: bool,
    page: int | None,
    rule_id: str = "",
    issue_type: str = "",
    details: dict[str, str] | None = None,
    location_label: str = "",
) -> str:
    """Return a student-facing reason why no exact highlight is available."""
    if has_highlight:
        return ""
    return build_no_highlight_guidance(
        rule_id=rule_id,
        issue_type=issue_type,
        details=details or {},
        page=page,
        location_label=location_label,
    )


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
    # P013 only records a candidate's observed position/style — it has no
    # notion of "correct" on its own (see P019/P028 for confirmed defects),
    # so this explanation frames it as a verification signal rather than a
    # defect. NJIT only specifies a bottom placement (0.5" from the bottom
    # edge); there is no "top right" allowance.
    ("P013", "page_number_candidate"): (
        "A page-number-like token was detected in the {position_type_label} "
        "area of this page. This finding is a manual-verification signal: it "
        "records where the candidate page number was found so a person can "
        "confirm it. It does not by itself confirm a formatting defect. "
        "NJIT requires page numbers to appear at the bottom of the page "
        "(0.5 inches from the bottom edge), using lowercase Roman numerals "
        "(i, ii, iii) for front matter and Arabic numerals (1, 2, 3) for "
        "body pages. Verify that this page number is visible, correctly "
        "placed, and uses the correct style."
    ),
    ("P013", "p013_document_overview"): (
        "This is a document-level, informational summary of page-number "
        "patterns detected across the PDF. It does not by itself identify a "
        "specific formatting defect, and does not correspond to a specific "
        "page or visual location. Review the individual page-number findings "
        "below for page-specific details."
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
        "Problem: The auditor did not find a clear page number on this page. "
        "NJIT requires page numbers on this type of page unless numbering is "
        "intentionally suppressed for that page type."
    ),
    ("P019", "multiple_page_numbers"): (
        "Problem: Multiple page-number-like tokens were detected on this page. "
        "This may indicate duplicate page numbering or footer/header text being "
        "mistaken for a page number. Verify which token is the actual page "
        "number and remove or correct duplicates."
    ),
    ("P019", "inconsistent_position"): (
        "Problem: The detected page number appears outside the required bottom "
        "position. NJIT expects page numbers in the required bottom position."
    ),
    ("P019", "mixed_numbering_style"): (
        "Problem: The detected page number appears to use a numbering style "
        "that does not match what this section should use. Front matter should "
        "use lowercase Roman numerals and body pages should use Arabic numerals."
    ),
    ("P019", "sequence_gap"): (
        "Problem: The detected page number does not appear to follow the expected "
        "numbering sequence. Review the affected pages and renumber them to "
        "restore the sequence."
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
    ("P022", "visible_page_number_on_no_number_page"): (
        "Problem: A page number appears on a page type that may require the "
        "page number to be suppressed or hidden ({page_type_label}). Remove "
        "the page number unless this page type is intentionally numbered."
    ),
    # --- P023 body spacing ---
    ("P023", "possible_body_text_not_double_spaced"): (
        "Body text on this page appears to be single-spaced or less than "
        "double-spaced. "
        "NJIT requires all body text to be double-spaced throughout. "
        "Set the paragraph line spacing to 'Double' in Word, or use the equivalent "
        "setting in your editor."
    ),
    # --- P014 named front-matter heading style ---
    # P014 never sets issue_type, so this is keyed on the empty string. Text here
    # is a registry placeholder for build_group_explanation; _build_explanation_text
    # always intercepts P014 via _p014_heading_explanation before reaching this dict.
    ("P014", ""): (
        "A named front-matter heading does not match NJIT's expected layout/style "
        "(centered, near the top of the page, bold, and in all capital letters)."
    ),
    # --- P016 paragraph/line spacing gaps ---
    ("P016", "excessive_line_gap"): (
        "Unusually large spacing was detected between lines on this page. "
        "Body text should be double-spaced with consistent spacing. "
        "Review for extra blank lines or manual spacing overrides."
    ),
    ("P016", "excessive_paragraph_gap"): (
        "Unusually large spacing was detected between paragraphs on this page. "
        "Paragraph spacing should be consistent with double-spaced body text. "
        "Review for extra blank lines or manual paragraph-spacing overrides."
    ),
    ("P016", "suspicious_heading_blank_gap"): (
        "An unusually large blank gap was detected just before a heading on this "
        "page. Verify this is intentional heading spacing and not an extra blank "
        "line or page-break artifact."
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
    # --- P027 heading level style: one explanation per level, never combined ---
    ("P027", "level1_not_all_caps"): (
        "A Level 1 heading (a CHAPTER or APPENDIX title) on this page may not be "
        "in ALL CAPS. "
        "NJIT requires Level 1 headings to be ALL CAPS, bold, and centered. "
        "This explanation applies only to Level 1 — other heading levels use "
        "different capitalization rules."
    ),
    ("P027", "level2_title_case_issue"): (
        "A Level 2 heading (numbered like 1.1 or 1.2) on this page may not use "
        "Title Case. "
        "NJIT requires Level 2 headings to use Title Case, bold. "
        "This explanation applies only to Level 2 — other heading levels use "
        "different capitalization rules."
    ),
    ("P027", "level3_sentence_case_issue"): (
        "A Level 3 heading (numbered like 1.1.1) on this page may use Title "
        "Case where Sentence case is expected. "
        "NJIT requires Level 3 headings to use Sentence case (only the first "
        "word capitalized), bold. "
        "This explanation applies only to Level 3 — other heading levels use "
        "different capitalization rules."
    ),
    ("P027", "level4_sentence_case_issue"): (
        "A Level 4 heading (numbered like 1.1.1.1) on this page may use Title "
        "Case where Sentence case is expected. "
        "NJIT requires Level 4 headings to use Sentence case, ending with a "
        "period. "
        "This explanation applies only to Level 4 — other heading levels use "
        "different capitalization rules."
    ),
    ("P027", "level4_sentence_case_or_punctuation_issue"): (
        "A Level 4 heading (numbered like 1.1.1.1) on this page may be missing "
        "its required terminal period. "
        "NJIT requires Level 4 headings to end with a period."
    ),
    ("P027", "level5_sentence_case_issue"): (
        "A Level 5 heading (numbered like 1.1.1.1.1) on this page may use "
        "Title Case where Sentence case is expected. "
        "NJIT requires Level 5 headings to use Sentence case, ending with a "
        "period. "
        "This explanation applies only to Level 5 — other heading levels use "
        "different capitalization rules."
    ),
    ("P027", "level5_sentence_case_or_punctuation_issue"): (
        "A Level 5 heading (numbered like 1.1.1.1.1) on this page may be "
        "missing its required terminal period. "
        "NJIT requires Level 5 headings to end with a period."
    ),
    # --- P025 front-matter structure: one explanation per required element ---
    ("P025", "missing_abstract_body"): (
        "An ABSTRACT heading was found on this page, but no body text was "
        "detected below it. "
        "NJIT requires the Abstract page to contain the abstract text beneath "
        "the heading. Add the abstract body text below the heading."
    ),
    ("P025", "missing_title_page_degree_phrase"): (
        "No degree phrase (e.g. 'Doctor of Philosophy', 'Master of Science') "
        "was detected on the title page. "
        "NJIT requires the title page to state the degree being conferred. "
        "Add the degree phrase to the title page."
    ),
    ("P025", "missing_title_page_institution"): (
        "The institution name was not detected on the title page. "
        "NJIT requires the title page to include 'New Jersey Institute of "
        "Technology'. Add the institution name to the title page."
    ),
    ("P025", "sparse_approval_page_content"): (
        "An APPROVAL PAGE heading was found on this page, but the content "
        "below it appears sparse. "
        "NJIT requires the Approval Page to include committee member names, "
        "titles, and signature lines. Add the missing committee content."
    ),
    ("P025", "possible_frontmatter_order_issue"): (
        "The ABSTRACT heading appears after the TABLE OF CONTENTS in the "
        "document. "
        "NJIT requires the Abstract to appear before the Table of Contents. "
        "Move the Abstract earlier in the front matter."
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
    ("P028", "arabic_number_on_frontmatter_page"): (
        "Problem: This page appears to use Arabic numerals, but front matter "
        "should use lowercase Roman numerals."
    ),
    ("P028", "uppercase_roman_on_frontmatter_page"): (
        "Problem: This page appears to use uppercase Roman numerals, but front "
        "matter should use lowercase Roman numerals."
    ),
    ("P028", "roman_number_on_body_page"): (
        "Problem: This page appears to use Roman numerals, but the main body "
        "should use Arabic numerals."
    ),
    # --- P029 roman sequence ---
    ("P029", "roman_sequence_gap"): (
        "Problem: The detected page number does not appear to follow the expected "
        "front-matter Roman numeral sequence. Review the front-matter page "
        "numbering and correct the sequence."
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
    ("P038", "required_heading_missing"): (
        "A required front-matter section heading was not found anywhere in "
        "the document. "
        "NJIT requires APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, "
        "and TABLE OF CONTENTS to all be present. "
        "Add the missing section with its exact required heading."
    ),
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
    ("P063", "single_appendix_uses_letter_label"): (
        "Observed: The document appears to have only one appendix, but its "
        "heading is labeled 'APPENDIX {letter_found}' with a letter. "
        "Expected: NJIT convention requires a single appendix to be labeled "
        "'APPENDIX' with no letter. Use 'APPENDIX A,' 'APPENDIX B,' etc. "
        "only when the document has multiple appendices. "
        "What to fix: Rename the appendix heading to 'APPENDIX' (remove the "
        "letter), or, if the document actually has more than one appendix, "
        "add the missing appendix heading(s) so every appendix is present "
        "and lettered."
    ),
    ("P063", "multiple_appendix_missing_letter"): (
        "Observed: Multiple appendices were detected, but at least one "
        "appendix heading does not include a letter identifier. "
        "Expected: NJIT convention requires every appendix to be labeled "
        "'APPENDIX A,' 'APPENDIX B,' etc. when there is more than one. "
        "What to fix: Add the missing letter to the appendix heading so it "
        "matches the 'APPENDIX <letter>' format."
    ),
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
    # --- P015 paragraph indentation ---
    ("P015", "unexpected_opening_indent"): (
        "A paragraph on this page appears to have an unintended first-line indent "
        "where NJIT expects a flush-left opening paragraph. Remove the extra indent "
        "or confirm this is a permitted exception."
    ),
    ("P015", "missing_later_indent"): (
        "A paragraph on this page appears to start flush-left where NJIT expects "
        "a first-line indent for a non-opening paragraph. Add the required indent."
    ),
    # --- P017 figure/table captions ---
    ("P017", "unexpected_terminal_period"): (
        "A figure or table caption on this page appears to end with a terminal "
        "period where NJIT expects no ending punctuation for this caption type. "
        "Remove the trailing period unless the caption is written as a full sentence."
    ),
    ("P017", "missing_terminal_punctuation"): (
        "A figure or table caption on this page appears to be missing terminal "
        "punctuation. Add a period, question mark, or exclamation point as "
        "appropriate for the caption style."
    ),
    ("P017", "possible_sentence_case_issue"): (
        "A caption on this page appears to use Title Case where sentence case may "
        "be expected. Review caption capitalization against NJIT guidance."
    ),
    ("P017", "possible_title_case_issue"): (
        "A caption on this page may violate title-case expectations. Capitalize "
        "the first word, last word, and major words of four or more letters."
    ),
    # --- P018 TOC/LoT/LoF alignment ---
    ("P018", "misaligned_page_number_column"): (
        "A TOC, List of Tables, or List of Figures entry on this page has a "
        "page-number column that does not align with the dominant column. Align "
        "entry page numbers to the same right-hand column throughout the list."
    ),
    ("P018", "missing_page_number"): (
        "A TOC or list entry on this page appears to be missing its trailing "
        "page number. Add the correct page number for this entry."
    ),
    ("P018", "inconsistent_leader_dots"): (
        "Leader dots or spacing before page numbers on this list page are "
        "inconsistent. Use consistent leader-dot spacing between entry text "
        "and page numbers."
    ),
    ("P018", "inconsistent_hierarchy_indent"): (
        "Entry indentation on this list page does not match the expected "
        "hierarchy level. Adjust indentation so entries visually reflect their level."
    ),
    # --- P024 TOC/LoT/LoF capitalization ---
    ("P024", "toc_level_capitalization"): (
        "A Table of Contents entry on this page may not follow NJIT capitalization "
        "rules for its heading level (Level 1 = ALL CAPS, Level 2 = Title Case)."
    ),
    ("P024", "list_of_tables_title_case"): (
        "A List of Tables entry on this page may not use Title Case or may include "
        "terminal punctuation. Table titles should use Title Case with no ending period."
    ),
    ("P024", "list_of_figures_sentence_case"): (
        "A List of Figures entry on this page may not use sentence case. Figure "
        "descriptions should begin with a capital letter and use sentence case."
    ),
    ("P024", "unexpected_terminal_punctuation"): (
        "A TOC or list entry on this page ends with terminal punctuation where "
        "NJIT expects none for that list type."
    ),
    # --- P025 title page graduation month ---
    ("P025", "title_page_graduation_month_invalid"): (
        "The graduation month on the title page may not match the expected NJIT "
        "format. NJIT expects a spelled-out month and year (for example, 'May 2025')."
    ),
    # --- P035 figure/table layout ---
    ("P035", "table_caption_not_above_body"): (
        "A table caption on this page does not appear above the table body. "
        "NJIT expects table captions above the table."
    ),
    ("P035", "figure_caption_not_below_body"): (
        "A figure caption on this page does not appear below the figure body. "
        "NJIT expects figure captions below the figure."
    ),
    ("P035", "table_body_not_centered"): (
        "A table body block on this page does not appear centered within the "
        "text area. Center the table within the page margins."
    ),
    ("P035", "figure_body_not_centered"): (
        "A figure body block on this page does not appear centered within the "
        "text area. Center the figure within the page margins."
    ),
    # --- P039 TOC hierarchy indentation ---
    ("P039", "toc_l2_not_indented_relative_to_l1"): (
        "A level-2 Table of Contents entry on this page does not appear indented "
        "to the right of its level-1 parent entry."
    ),
    ("P039", "toc_l3_not_indented_relative_to_l2"): (
        "A level-3 Table of Contents entry on this page does not appear indented "
        "relative to its level-2 parent entry."
    ),
    # --- P040 List of Figures punctuation ---
    ("P040", "lof_entry_missing_terminal_punctuation"): (
        "A List of Figures entry on this page appears to be missing terminal "
        "punctuation. Every figure description should end with a period, question "
        "mark, or exclamation point."
    ),
    # --- P043 acknowledgements indentation ---
    ("P043", "acknowledgements_first_paragraph_indented"): (
        "The first paragraph on the Acknowledgements page appears to be indented. "
        "NJIT requires the first paragraph to begin flush with the left margin."
    ),
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): (
        "A later paragraph on the Acknowledgements page appears flush-left where "
        "NJIT expects a first-line indent."
    ),
    # --- P044 abstract indentation ---
    ("P044", "abstract_first_paragraph_indented"): (
        "The first paragraph on the Abstract page appears to be indented. "
        "NJIT requires the first abstract paragraph to begin flush-left."
    ),
    ("P044", "abstract_subsequent_paragraph_not_indented"): (
        "A later paragraph on the Abstract page appears flush-left where NJIT "
        "expects a first-line indent."
    ),
    # --- P053/P054 list terminal periods ---
    ("P053", "lot_entry_has_terminal_period"): (
        "A List of Tables entry on this page ends with a terminal period. "
        "Remove the trailing period — table titles should not end with punctuation."
    ),
    ("P054", "toc_entry_has_terminal_period"): (
        "A Table of Contents entry on this page ends with a terminal period. "
        "Remove the trailing period — TOC entries should not end with punctuation."
    ),
    # --- P055 misplaced list entries ---
    ("P055", "lot_entry_is_figure"): (
        "A List of Tables entry on this page appears to describe a figure rather "
        "than a table. Move this entry to the List of Figures."
    ),
    ("P055", "lof_entry_is_table"): (
        "A List of Figures entry on this page appears to describe a table rather "
        "than a figure. Move this entry to the List of Tables."
    ),
    # --- P058/P060 TOC ordering ---
    ("P058", "toc_page_numbers_not_nondecreasing"): (
        "Table of Contents page numbers on this page do not appear in ascending "
        "order. Reorder entries so listed page numbers increase from top to bottom."
    ),
    ("P060", "toc_entry_numbers_not_nondecreasing"): (
        "Table of Contents section numbers on this page do not appear in "
        "non-decreasing order. Reorder entries so section numbers increase correctly."
    ),
    # --- P064 references structural (issue-specific) ---
    ("P064", "references_section_heading_not_detected"): (
        "No recognized REFERENCES or BIBLIOGRAPHY section heading was detected. "
        "Add a REFERENCES heading before the reference list."
    ),
    ("P064", "references_entry_indentation_inconsistent"): (
        "Reference entries on this page appear to use inconsistent indentation "
        "styles. Use either hanging indent or flush-left formatting consistently."
    ),
    ("P064", "references_entry_spacing_inconsistent"): (
        "Spacing between reference entries on this page appears inconsistent. "
        "Use uniform spacing between all reference entries."
    ),
    # --- P068 approval page structure ---
    ("P068", "approval_page_advisor_role_label_missing"): (
        "The Approval Page may be missing a recognizable advisor role label "
        "(for example, 'Dissertation Advisor' or 'Major Professor')."
    ),
    ("P068", "approval_page_signature_blocks_sparse"): (
        "The Approval Page appears to have too few signature or date structural "
        "blocks for the committee entries present."
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
    "P025": (
        "A required front-matter structural element may be missing or "
        "incomplete — the Abstract body, the title page's degree phrase or "
        "institution name, the Approval Page's committee content, or the "
        "Abstract-before-Table-of-Contents ordering. "
        "Review the specific element noted in this finding against NJIT "
        "front-matter requirements."
    ),
    "P026": (
        "Body text on this page may not use the expected font (Times New Roman 12pt). "
        "NJIT expects body text to use Times New Roman 12pt throughout. "
        "Review the highlighted text or the listed page and update the font settings "
        "in your source document."
    ),
    "P027": (
        "A numbered heading on this page may not match the capitalization or "
        "punctuation style expected for its heading level. "
        "NJIT uses a different style for each level (1 = ALL CAPS, 2 = Title "
        "Case, 3-5 = Sentence case), so check the level noted on this finding "
        "and apply only that level's style."
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


def _margin_side_label(details: dict[str, str]) -> str:
    side = details.get("side", "").strip().lower()
    labels = {
        "left_margin": "left margin",
        "right_margin": "right margin",
        "top_margin": "top margin",
        "bottom_margin": "bottom margin",
        "left": "left margin",
        "right": "right margin",
        "top": "top margin",
        "bottom": "bottom margin",
    }
    return labels.get(side, "required page margin")


def _p011_margin_explanation(details: dict[str, str], *, page: int | None) -> str:
    side = _margin_side_label(details)
    overflow = details.get("worst_overflow_pt", "").strip()
    line_count = details.get("affected_line_count", "").strip()
    if side == "required page margin":
        observed = (
            "Some content appears too close to or beyond a required page margin, "
            "but the exact side is unavailable"
        )
    else:
        observed = f"Content appears to cross the required {side} boundary"
    extras: list[str] = []
    if overflow:
        extras.append(f"about {overflow}pt beyond the boundary")
    if line_count:
        noun = "line" if line_count == "1" else "lines"
        extras.append(f"{line_count} affected text {noun}")
    if extras:
        observed = f"{observed} ({'; '.join(extras)})"
    return (
        f"Observed: {observed}. "
        "Expected: Content should stay inside NJIT's required page margins "
        "(left 1.5 inches; right, top, and bottom 1 inch). "
        "Why this is suspicious: layout content appears outside the printable body area. "
        "What to check or fix: inspect tables, figures, long lines, indentation, headers, "
        "and footers on this page."
    )


def _p026_font_explanation(
    issue_type: str,
    details: dict[str, str],
    *,
    page: int | None,
) -> str:
    observed = (
        details.get("observed_font", "").strip()
        or details.get("observed_size", "").strip()
        or details.get("observed_summary", "").strip()
    )
    span_count = details.get("affected_span_count", "").strip()
    candidate_count = details.get("candidate_count", "").strip()
    count_bits: list[str] = []
    if span_count:
        noun = "span" if span_count == "1" else "spans"
        count_bits.append(f"{span_count} flagged {noun}")
    if candidate_count:
        noun = "candidate" if candidate_count == "1" else "candidates"
        count_bits.append(f"{candidate_count} sampled {noun}")
    counts = f" ({'; '.join(count_bits)})" if count_bits else ""
    if issue_type == "possible_body_font_size_issue":
        expected = (
            details.get("expected_size", "").strip()
            or details.get("expected", "").strip()
            or "12pt"
        )
        if observed:
            observed_text = f"Body-text-like spans appear at {observed}{counts}"
        else:
            observed_text = (
                "Some body-text-like spans appear not to match the expected size, "
                "but the precise observed value was unavailable"
            )
        expected_text = f"Body text should use {expected}"
    else:
        expected = (
            details.get("expected_font", "").strip()
            or details.get("expected", "").strip()
            or "Times New Roman or an accepted Times-compatible font"
        )
        if observed:
            observed_text = f"Body-text-like spans appear to use {observed}{counts}"
        else:
            observed_text = (
                "Some body-text-like spans appear not to match the expected font family, "
                "but the precise observed value was unavailable"
            )
        expected_text = f"Body text should use {expected}"
    return (
        f"Observed: {observed_text}. "
        f"Expected: {expected_text}. "
        "Why this is suspicious: the detector repeatedly saw a non-matching font pattern "
        "in body-text-like spans on this page. "
        "What to check or fix: confirm whether the flagged text is body text, a caption, "
        "a heading, table text, a footnote, or another exception, then correct the source "
        "document's font settings if needed."
    )


_P014_ATTRIBUTE_LABELS: tuple[tuple[str, str], ...] = (
    ("centered", "centered"),
    ("near_top", "near the top of the page"),
    ("bold", "bold"),
    ("all_caps", "in all capital letters"),
)


def _p014_heading_explanation(details: dict[str, str], *, page: int | None) -> str:
    heading = details.get("heading", "").strip()
    heading_clause = f" ('{heading}')" if heading else ""
    failed_labels = [
        label
        for key, label in _P014_ATTRIBUTE_LABELS
        if details.get(key, "").strip().lower() == "false"
    ]
    if failed_labels:
        observed = (
            f"This front-matter heading{heading_clause} is "
            + ", ".join(f"not {label}" for label in failed_labels)
        )
    else:
        observed = (
            f"This front-matter heading{heading_clause} does not match NJIT's "
            "expected layout/style"
        )
    return (
        f"{observed}. NJIT requires named front-matter headings (such as ABSTRACT "
        "or APPROVAL PAGE) to be centered near the top of the page, in bold, and in "
        "all capital letters. Review the heading's formatting and correct any "
        "attributes that do not match."
    )


def _p016_spacing_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    gap = details.get("largest_gap_pt", "").strip()
    gap_clause = f" (about {gap}pt)" if gap else ""
    if issue_type == "excessive_line_gap":
        return (
            f"Unusually large spacing{gap_clause} was detected between lines on this "
            "page. Body text should be double-spaced with consistent spacing. "
            "Review for extra blank lines or manual spacing overrides."
        )
    if issue_type == "excessive_paragraph_gap":
        return (
            f"Unusually large spacing{gap_clause} was detected between paragraphs on "
            "this page. Paragraph spacing should be consistent with double-spaced "
            "body text. Review for extra blank lines or manual paragraph-spacing "
            "overrides."
        )
    return (
        f"An unusually large blank gap{gap_clause} was detected just before a "
        "heading on this page. Verify this is intentional heading spacing and not "
        "an extra blank line or page-break artifact."
    )


def _p068_approval_page_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    role_label_count = details.get("role_label_count", "").strip() or "0"
    indicator_count = details.get("signature_date_indicator_count", "").strip() or "0"
    try:
        required = str(max(2, int(role_label_count)))
    except ValueError:
        required = "2"
    if issue_type == "approval_page_advisor_role_label_missing":
        return (
            f"The Approval Page lists {role_label_count} committee role label(s), "
            "but none of them is a recognizable advisor role label (for example, "
            "'Dissertation Advisor' or 'Major Professor'). Add the required advisor "
            "role label."
        )
    return (
        f"The Approval Page has {indicator_count} signature/date line(s) for "
        f"{role_label_count} committee role label(s), but at least {required} are "
        "expected. Add a signature line and a date line for each committee member."
    )


_P032_ENTRY_KIND_LABELS: dict[str, str] = {
    "table_entry": "List of Tables entry",
    "figure_entry": "List of Figures entry",
    "toc_level_1": "Table of Contents chapter/appendix entry",
    "toc_level_2": "Table of Contents entry",
    "toc_level_3": "Table of Contents sub-entry",
}


def _p032_spacing_explanation(details: dict[str, str], *, page: int | None) -> str:
    entry_label = _P032_ENTRY_KIND_LABELS.get(details.get("entry_kind", ""), "list entry")
    observed_gap = details.get("observed_gap_pt", "").strip()
    expected_gap = details.get("expected_max_gap_pt", "").strip()
    gap_clause = (
        f" (about {observed_gap}pt, versus an expected maximum of about "
        f"{expected_gap}pt)"
        if observed_gap and expected_gap
        else ""
    )
    return (
        f"A wrapped (continuation) line in a {entry_label} has an unusually large "
        f"internal gap{gap_clause}. Continuation lines that belong to the same "
        "entry should sit close together on the next line, not with extra blank "
        "space. Review the entry and remove any extra spacing within it."
    )


def _p056_format_counts(details: dict[str, str]) -> tuple[str, str]:
    """Parse P056's 'chapter_based:N,sequential:M' details string into (N, M)."""
    counts: dict[str, str] = {}
    for part in details.get("format_counts", "").split(","):
        key, _, value = part.partition(":")
        if key.strip():
            counts[key.strip()] = value.strip()
    return counts.get("chapter_based", "0"), counts.get("sequential", "0")


def _p056_numbering_format_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    noun = "Table" if issue_type == "lot_mixed_numbering_format" else "Figure"
    section_label = (
        "List of Tables" if issue_type == "lot_mixed_numbering_format" else "List of Figures"
    )
    chapter_count, sequential_count = _p056_format_counts(details)
    dominant = details.get("dominant_format", "").strip()
    dominant_clause = ""
    if dominant == "chapter_based":
        dominant_clause = f" The more common format here is chapter-based (e.g., {noun} 1.2)."
    elif dominant == "sequential":
        dominant_clause = f" The more common format here is sequential (e.g., {noun} 3)."
    return (
        f"The {section_label} mixes {chapter_count} chapter-based (e.g., {noun} 1.2) "
        f"and {sequential_count} sequential (e.g., {noun} 3) entry-numbering "
        f"formats.{dominant_clause} NJIT expects one consistent numbering format "
        "throughout this list. Choose one format and apply it to every entry."
    )


def _p066_degree_order_explanation(details: dict[str, str], *, page: int | None) -> str:
    first_year = details.get("first_candidate_year", "").strip() or "an earlier year"
    last_year = details.get("last_candidate_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        "Postgraduate degree entries on the Biographical Sketch page appear out of "
        "order: the candidate years found (in listed order) run from "
        f"{first_year} to {last_year}, with {inversion_count} {place_noun} where a "
        "later-listed entry's year is more recent than the entry just before it. "
        "NJIT requires postgraduate degrees to be listed from most recent to "
        "oldest. Reorder the entries."
    )


def _p067_publication_order_explanation(details: dict[str, str], *, page: int | None) -> str:
    first_year = details.get("first_entry_year", "").strip() or "an earlier year"
    last_year = details.get("last_entry_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        "Publication/presentation entries on the Biographical Sketch page appear "
        "out of order: the comparable entry years found (in listed order) run from "
        f"{first_year} to {last_year}, with {inversion_count} {place_noun} where a "
        "later-listed entry's year is more recent than the entry just before it. "
        "NJIT requires publications/presentations to be listed from most recent to "
        "oldest. Reorder the entries."
    )


def _p045_hanging_indent_explanation(details: dict[str, str], *, page: int | None) -> str:
    block_count = details.get("multi_line_block_count", "").strip()
    threshold = details.get("hanging_indent_threshold_points", "").strip()
    count_clause = f" out of {block_count} multi-line entries checked" if block_count else ""
    threshold_clause = f" by at least {threshold}pt" if threshold else ""
    return (
        "None of the publication/presentation entries on the Biographical Sketch "
        f"page use hanging indentation{count_clause}: no continuation line is "
        f"indented{threshold_clause} relative to its entry's first line. NJIT "
        "requires publication/presentation entries to use hanging indentation "
        "(first line flush left, continuation lines indented). Indent the "
        "continuation lines of each entry."
    )


def _p045_entry_spacing_explanation(details: dict[str, str], *, page: int | None) -> str:
    observed = details.get("observed_gap_points", "").strip()
    required = details.get("required_gap_points", "").strip()
    gap_clause = (
        f" (about {observed}pt observed vs. a required minimum of about {required}pt)"
        if observed and required
        else ""
    )
    return (
        "Two consecutive publication/presentation entries on the Biographical "
        f"Sketch page appear to lack the required gap between them{gap_clause}. "
        "NJIT requires a blank-line gap between publication/presentation entries. "
        "Add a blank line between these entries."
    )


def _p047_block_label(details: dict[str, str]) -> str:
    raw = details.get("block_index", "").strip()
    try:
        return f"Bullet block {int(raw) + 1}"
    except ValueError:
        return "A bullet/list block"


def _p047_bullet_spacing_explanation(details: dict[str, str], *, page: int | None) -> str:
    block_label = _p047_block_label(details)
    observed = details.get("observed_gap_points", "").strip()
    required_max = details.get("required_max_gap_points", "").strip()
    gap_clause = (
        f" (about {observed}pt observed vs. an expected maximum of about "
        f"{required_max}pt)"
        if observed and required_max
        else ""
    )
    return (
        f"{block_label} on the Biographical Sketch page has an internal line gap "
        f"that looks double-spaced rather than single-spaced{gap_clause}. NJIT "
        "requires bullet/list items in the Biographical Sketch to be "
        "single-spaced internally. Remove the extra blank space within this "
        "bullet item."
    )


def build_detailed_explanation(
    *,
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    page: int | None,
    has_highlight: bool = False,
    location_label: str = "",
) -> str:
    """Build a student-facing detailed explanation for a finding.

    Returns a non-empty string in all cases. Never reproduces dissertation body
    text, author names, or raw LaTeX. When *page* is known, the page number is
    appended to the explanation so it is visible even when no PDF action
    button is shown (e.g. when no highlight is available).
    """
    text = _build_explanation_text(
        rule_id=rule_id, issue_type=issue_type, details=details, page=page
    )
    if not has_highlight and page is not None:
        guidance = build_no_highlight_guidance(
            rule_id=rule_id,
            issue_type=issue_type,
            details=details,
            page=page,
            location_label=location_label,
        )
        return (
            f"{text} "
            f"{guidance}"
        )
    if page is not None:
        return f"{text} This finding is on page {page}."
    return text


def _build_explanation_text(
    *,
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    page: int | None,
) -> str:
    effective_issue_type = _resolve_issue_type(rule_id, issue_type, details)
    if rule_id == "P011" and effective_issue_type == "margin_boundary_violation":
        return _p011_margin_explanation(details, page=page)
    if rule_id == "P026" and effective_issue_type in {
        "possible_body_font_family_issue",
        "possible_body_font_size_issue",
    }:
        return _p026_font_explanation(effective_issue_type, details, page=page)
    if rule_id == "P014":
        return _p014_heading_explanation(details, page=page)
    if rule_id == "P016" and effective_issue_type in {
        "excessive_line_gap",
        "excessive_paragraph_gap",
        "suspicious_heading_blank_gap",
    }:
        return _p016_spacing_explanation(effective_issue_type, details, page=page)
    if rule_id == "P068" and effective_issue_type in {
        "approval_page_advisor_role_label_missing",
        "approval_page_signature_blocks_sparse",
    }:
        return _p068_approval_page_explanation(effective_issue_type, details, page=page)
    if rule_id == "P032" and effective_issue_type == "wrapped_entry_internal_spacing":
        return _p032_spacing_explanation(details, page=page)
    if rule_id == "P056" and effective_issue_type in {
        "lot_mixed_numbering_format",
        "lof_mixed_numbering_format",
    }:
        return _p056_numbering_format_explanation(effective_issue_type, details, page=page)
    if rule_id == "P066" and effective_issue_type == "biosketch_degree_order_suspicious":
        return _p066_degree_order_explanation(details, page=page)
    if rule_id == "P067" and effective_issue_type == "biosketch_publication_order_suspicious":
        return _p067_publication_order_explanation(details, page=page)
    if (
        rule_id == "P045"
        and effective_issue_type == "biosketch_publication_missing_hanging_indent"
    ):
        return _p045_hanging_indent_explanation(details, page=page)
    if (
        rule_id == "P045"
        and effective_issue_type == "biosketch_publication_entry_spacing_not_double"
    ):
        return _p045_entry_spacing_explanation(details, page=page)
    if rule_id == "P047" and effective_issue_type == "biosketch_bullet_section_not_single_spaced":
        return _p047_bullet_spacing_explanation(details, page=page)
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

        page_type = details.get("page_type", "")
        page_type_label = page_type.replace("_", " ") if page_type else "this"

        candidate_text = details.get("candidate_text", "") or "this token"
        letter_found = details.get("letter_found", "") or "A"

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
                page_type_label=page_type_label,
                candidate_text=candidate_text,
                letter_found=letter_found,
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

    Prefers the same per-issue-type template used for individual findings,
    rendered with neutral defaults instead of per-finding details (since a
    grouped card spans multiple findings with varying detail values). Falls
    back to the rule-level text, then a generic phrase, when no template
    exists for this exact (rule_id, issue_type) pair.
    """
    effective_issue_type = _resolve_issue_type(rule_id, issue_type, {})
    if (rule_id, effective_issue_type) in _EXPLANATION_TEMPLATES:
        return build_detailed_explanation(
            rule_id=rule_id, issue_type=issue_type, details={}, page=None
        )
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
