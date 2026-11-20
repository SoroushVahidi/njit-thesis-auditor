"""Student-facing detailed explanations and action metadata for finding types.

This module is a presentation-layer helper only. It never changes detection
semantics, thresholds, rule IDs, or stored finding data.
"""

from __future__ import annotations

from njit_auditor.title_case_student_preview import (
    affected_title_phrase,
    sanitize_title_case_line_preview,
    title_case_subject_kind,
)
from njit_auditor.toc_list_student_preview import (
    sanitize_toc_list_entry_preview,
    spacing_entries_phrase,
)

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

_NO_HIGHLIGHT_DOC_REASON_WITH_LOCATION = (
    "This finding has no specific PDF page or on-page highlight, but it does apply to a "
    "specific part of the document -- see the location above."
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
    if rule_id == "P012":
        return "the annotation area"
    if rule_id == "P015":
        if issue_type == "unexpected_opening_indent":
            return "the first line of the opening paragraph"
        if issue_type == "unexpected_indent_on_continuation_line":
            paragraph_index = details.get("paragraph_index", "").strip()
            if paragraph_index:
                return f"the continuation line in body paragraph {paragraph_index}"
            return "the continuation line after a displayed equation or similar break"
        paragraph_index = details.get("paragraph_index", "").strip()
        if paragraph_index:
            return f"the first line of body paragraph {paragraph_index}"
        return "the first line of a paragraph after the first"
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
        if location_label.strip():
            return _NO_HIGHLIGHT_DOC_REASON_WITH_LOCATION
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
        "Problem: Text on this page is not contained entirely within the required "
        "page margin ({side_label}). "
        "NJIT requires: left margin 1.5 inches; top, bottom, and right margins 1 inch. "
        "Move any text, table, or figure that extends into the margins back inside "
        "the required page area."
    ),
    # --- P013 page number candidates ---
    # P013 only records a candidate's observed position/style — it has no
    # notion of "correct" on its own (see P019/P028 for confirmed defects),
    # so this explanation frames it as a verification signal rather than a
    # defect. NJIT only specifies a bottom placement (0.5" from the bottom
    # edge); there is no "top right" allowance.
    ("P013", "page_number_candidate"): (
        "A page-number candidate was detected in the {position_type_label} "
        "area of this page. This finding is a manual-verification signal: it "
        "records where the candidate was found so a person can confirm it. "
        "It does not by itself confirm a formatting defect. "
        "NJIT requires page numbers to appear at the bottom of the page, "
        "centered, 0.5 inches from the bottom edge. Use lowercase Roman "
        "numerals (i, ii, iii) for front matter and Arabic numerals (1, 2, 3) "
        "for body pages. Verify that this page number is visible, correctly "
        "placed at the bottom-center, and uses the correct numbering style."
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
        "Problem: Body text on this page does not appear to be double-spaced. "
        "NJIT requires body text to be double-spaced, except for tables, figure "
        "descriptions, bullet points, and multi-line titles."
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
        "Excluding necessary page breaks for new chapters or to keep figures "
        "and tables with their captions, text should flow consistently from "
        "the top margin to the bottom margin. Delete unnecessary blank lines "
        "or correct manual spacing overrides."
    ),
    ("P016", "excessive_paragraph_gap"): (
        "Unusually large spacing was detected between paragraphs on this page. "
        "Excluding necessary page breaks for new chapters or to keep figures "
        "and tables with their captions, paragraph spacing should remain "
        "consistent. Delete unnecessary blank lines or manual paragraph-spacing "
        "overrides."
    ),
    ("P016", "suspicious_heading_blank_gap"): (
        "An unusually large blank gap was detected just after a heading on this "
        "page. Verify this is an intentional necessary page break (for example, "
        "starting a new chapter). If it is just an extra blank line, delete it."
    ),
    # --- P026 font compliance ---
    ("P026", "possible_body_font_family_issue"): (
        "This page contains body-text spans whose embedded PDF font does not appear "
        "to be one of the accepted NJIT body font families (Times New Roman, Arial, "
        "Computer Modern, or Latin Modern). "
        "Review the highlighted text or the listed page and update the source "
        "document font settings if this text is part of the main body."
    ),
    ("P026", "possible_body_font_size_issue"): (
        "This page contains body-text spans outside the expected 12pt range "
        "(11–13 pt). "
        "NJIT expects body text to be 12pt. "
        "Review the highlighted text or the listed page and correct the font size. "
        "Verify whether the flagged text is body text or a permitted exception "
        "such as a table, figure caption, heading, or footnote."
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
        "should use lowercase Roman numerals. Use lowercase Roman numerals "
        "for numbered front-matter pages."
    ),
    ("P028", "uppercase_roman_on_frontmatter_page"): (
        "Problem: This page appears to use uppercase Roman numerals, but front "
        "matter should use lowercase Roman numerals. Use lowercase Roman "
        "numerals for numbered front-matter pages."
    ),
    ("P028", "roman_number_on_body_page"): (
        "Problem: This page appears to use Roman numerals, but the main body "
        "should use Arabic numerals. Use Arabic numerals for body pages."
    ),
    # --- P029 roman sequence ---
    ("P029", "roman_sequence_gap"): (
        "Problem: The detected page number does not appear to follow the expected "
        "front-matter Roman numeral sequence. Review the front-matter page "
        "numbering and correct the sequence."
    ),
    # --- P030 TOC continued headings ---
    ("P030", "missing_continued_heading"): (
        "Problem: A continuation page of a multi-page Table of Contents, List of "
        "Tables, or List of Figures does not include the correct continued heading. "
        "Add the correct continued heading on this continuation page."
    ),
    # --- P033 title consistency ---
    ("P033", "frontmatter_title_mismatch"): (
        "The dissertation title appears to differ between two or more front-matter "
        "pages — the Title Page, Abstract, and/or Approval Page — based on a "
        "normalized text comparison rather than an exact match. NJIT requires the "
        "title to be worded identically everywhere it appears in the front matter. "
        "Common causes include an abbreviated or reworded title on one page, a "
        "typo introduced when retyping the title, or a title that was updated on "
        "one page but not the others. Open the flagged pages, compare the title "
        "wording word-for-word, and correct whichever page does not match; this is "
        "a similarity heuristic, so always verify by reading the pages directly."
    ),
    # --- P034 copyright page ---
    ("P034", "copyright_year_mismatch"): (
        "The copyright page year format may not match the expected NJIT format. "
        "The copyright page should include the current year in the standard format "
        "(e.g., Copyright © 2025 First Last). "
        "Review the copyright page and confirm the year is present and correct."
    ),
    ("P052", "copyright_author_not_found"): (
        "A copyright page was detected but the author name could not be verified. "
        "The copyright page must include the student's full legal name. "
        "Review the copyright page and ensure the author name is present and "
        "correct."
    ),
    ("P051", "copyright_year_not_found"): (
        "A copyright page was detected, but the auditor could not confidently "
        "associate a four-digit copyright year with the copyright notice. NJIT "
        "requires the copyright page to state the copyright year clearly next to "
        "the copyright notice (for "
        "example, 'Copyright © 2025 by [Author Name]. All Rights Reserved.'), "
        "matching the year the degree is conferred. This often happens when the "
        "year is split across lines, uses unusual spacing, or is present elsewhere "
        "on the page but not clearly attached to the copyright notice. Review the "
        "copyright page and add or reposition the year if needed. This is an "
        "automated, approximate check, so verify by reading the page directly "
        "before editing."
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
        "Header text appears to be present in the top margin area of the "
        "Dedication page. Remove any running header or header text from the "
        "top margin area of the Dedication page."
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
        "The abstract appears to contain \"paper\" or \"article\" (or a plural "
        "form). Replace \"paper\" or \"article\" with \"dissertation,\" "
        "\"study,\" \"work,\" or \"research.\""
    ),
    ("P078", "abstract_pdf_first_person_pronoun"): (
        "The abstract appears to use a first-person pronoun such as \"I,\" "
        "\"me,\" \"my,\" \"we,\" or \"our.\" Rewrite the sentence to remove "
        "first-person pronouns."
    ),
    # --- P017 figure/table captions ---
    ("P017", "unexpected_terminal_period"): (
        "A table title or List of Tables entry on this page appears to end with "
        "a period. Remove the final period."
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
        "A table title on this page may violate NJIT title-case expectations. "
        "Capitalize the first word and major words; leave prepositions, conjunctions, "
        "and articles lowercase where appropriate."
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
    ("P018", "wrapped_title_continuation_misaligned"): (
        "A Table of Contents title on this page wraps onto a second line that does "
        "not start under the first line's title text. Align the second line with "
        "the text of the first line, not the section number."
    ),
    ("P018", "title_to_leader_gap_too_wide"): (
        "Leader dots in a list entry on this page start after a visible gap "
        "instead of right after the title. Start the leader dots right after the "
        "last letter of the title, with at most one space."
    ),
    ("P018", "leader_dots_before_final_title_line"): (
        "A wrapped list entry on this page has leader dots on an earlier line of "
        "its title. Place the leader dots after the final line of the title."
    ),
    # --- P024 TOC/LoT/LoF capitalization ---
    ("P024", "toc_level_capitalization"): (
        "A Table of Contents entry on this page may not follow NJIT capitalization "
        "rules for its heading level (Level 1 = ALL CAPS, Level 2 = Title Case, "
        "Level 3 = sentence case)."
    ),
    ("P024", "list_of_tables_title_case"): (
        "A List of Tables entry on this page may not use Title Case or may include "
        "terminal punctuation. Table titles should use Title Case with no ending period."
    ),
    ("P024", "list_of_figures_title_case"): (
        "A figure description in the List of Figures appears to use Title Case. "
        "Use sentence case, preserving proper names, acronyms and technical notation."
    ),
    ("P024", "unexpected_terminal_punctuation"): (
        "A TOC or list entry on this page ends with terminal punctuation where "
        "NJIT expects none for that list type."
    ),
    # --- P074 title page graduation month (PDF) ---
    ("P074", "title_page_graduation_month_invalid"): (
        "The graduation month detected on the Title Page is not August, December, "
        "or May. Change the graduation month on the Title Page to August, "
        "December, or May."
    ),
    # --- P035 figure/table layout ---
    ("P035", "table_caption_not_above_body"): (
        "A table title on this page does not appear above the table body. "
        "NJIT expects table titles above the table."
    ),
    ("P035", "figure_caption_not_below_body"): (
        "A figure description on this page does not appear below the figure body. "
        "NJIT expects figure descriptions below the figure."
    ),
    ("P035", "table_body_not_centered"): (
        "A table body block on this page does not appear centered within the "
        "area between the page margins. Center the table within the page margins."
    ),
    ("P035", "figure_body_not_centered"): (
        "A figure body block on this page does not appear centered within the "
        "area between the page margins. Center the figure within the page margins."
    ),
    # --- P039 TOC hierarchy indentation ---
    ("P039", "toc_l2_not_indented_relative_to_l1"): (
        "A level-2 Table of Contents entry on this page does not appear indented "
        "to show hierarchy relative to level-1 entries. Indent level-2 TOC entries "
        "to the right of level-1 entries."
    ),
    ("P039", "toc_l3_not_indented_relative_to_l2"): (
        "A level-3 Table of Contents entry on this page does not appear indented "
        "to show hierarchy relative to level-2 entries. Indent level-3 TOC entries "
        "further to the right of level-2 entries."
    ),
    # --- P040 List of Figures punctuation ---
    ("P040", "lof_entry_missing_terminal_punctuation"): (
        "A figure description in the List of Figures on this page does not end "
        "with terminal punctuation. Add terminal punctuation, such as a period, "
        "question mark, or exclamation point, to every figure description in the "
        "List of Figures."
    ),
    # --- P043 acknowledgements indentation ---
    ("P043", "acknowledgements_first_paragraph_indented"): (
        "The first paragraph on the Acknowledgements page appears to be "
        "indented. Remove any first-line indent from the first "
        "Acknowledgements paragraph."
    ),
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): (
        "A later paragraph on the Acknowledgements page appears flush-left "
        "where NJIT expects a first-line indent. Apply a first-line indent "
        "to each subsequent Acknowledgements paragraph."
    ),
    # --- P044 abstract indentation ---
    ("P044", "abstract_first_paragraph_indented"): (
        "The first paragraph on the Abstract page appears to be indented. "
        "Remove any first-line indent from the first Abstract paragraph."
    ),
    ("P044", "abstract_subsequent_paragraph_not_indented"): (
        "A later paragraph on the Abstract page appears flush-left where NJIT "
        "expects a first-line indent. Apply a first-line indent to each "
        "subsequent Abstract paragraph."
    ),
    # --- P053/P054 list terminal periods ---
    ("P053", "lot_entry_has_terminal_period"): (
        "A List of Tables entry on this page ends with a final period. "
        "Remove the final period from each List of Tables entry. Table titles "
        "should use title case without terminal punctuation."
    ),
    ("P054", "toc_entry_has_terminal_period"): (
        "A Table of Contents entry on this page ends with a final period. "
        "Remove the final period from each Table of Contents entry."
    ),
    ("P075", "toc_mixed_leader_styles"): (
        "The Table of Contents uses both dot and hyphen leaders between titles "
        "and page numbers. The identified entry on page {page} is one example "
        "of the differing style; inspect the other TOC entries as well. NJIT "
        "requires one consistent leader style throughout the TOC."
    ),
    ("P075", "toc_missing_leader_style"): (
        "Some Table of Contents entries have no leader between the title and "
        "page number, while other entries use one. The identified entry on "
        "page {page} is one example without a leader. Inspect the other TOC "
        "entries and add the same leader style where it is absent."
    ),
    # --- P055 misplaced list entries ---
    ("P055", "lot_entry_is_figure"): (
        "A table entry appears in the List of Tables but describes a figure. "
        "Move this entry to the List of Figures."
    ),
    ("P055", "lof_entry_is_table"): (
        "A figure entry appears in the List of Figures but describes a table. "
        "Move this entry to the List of Tables."
    ),
    ("P055", "lot_entry_missing_table_prefix"): (
        "A List of Tables entry on this page is missing the required 'Table' prefix. "
        "Each entry in the List of Tables must begin with the word 'Table' (e.g., Table 1.1)."
    ),
    ("P055", "lof_entry_missing_figure_prefix"): (
        "List of Figures entries may begin with a number; the word Figure is not required "
        "before each entry. Review body references separately."
    ),
    ("P055", "body_figure_reference_abbreviated"): (
        "Use the full word 'Figure' before the number in this body reference."
    ),
    # --- P058/P060 TOC ordering ---
    ("P058", "toc_page_numbers_not_nondecreasing"): (
        "Table of Contents page numbers on this page do not appear in ascending "
        "order. Reorder entries so listed page numbers increase from top to bottom."
    ),
    ("P060", "toc_subsection_number_ambiguous"): (
        "The number may be missing a dot: its preceding subsection and indentation "
        "suggest a deeper heading. Confirm the number and level before changing case."
    ),
    ("P060", "toc_entry_numbers_not_nondecreasing"): (
        "Table of Contents section numbers on this page do not appear in "
        "non-decreasing order. Reorder entries so section numbers increase correctly."
    ),
    ("P087", "toc_abstract_entry_present"): (
        "A Table of Contents entry on page {page} is titled Abstract. "
        "NJIT dissertations include the Abstract only in the front matter. "
        "Remove this Abstract entry from the TOC."
    ),
    ("P087", "toc_generic_title_repeated"): (
        "The Table of Contents repeats the same generic section title in "
        "distinct entries. This is a review prompt: check whether chapter or "
        "section context already distinguishes the entries. If readers cannot "
        "tell them apart, add the chapter topic or another distinctive label."
    ),
    ("P088", "figure_number_malformed"): (
        "A figure caption on page {page} uses a malformed number with extra "
        "concatenated segments. NJIT figure numbers follow a chapter.sequence "
        "form such as 4.20. Correct the label and match the List of Figures."
    ),
    ("P088", "figure_number_duplicate"): (
        "A figure number on page {page} is repeated within the same chapter. "
        "Assign a unique sequence number to each figure in the chapter."
    ),
    ("P088", "figure_number_out_of_order"): (
        "A figure number on page {page} appears out of increasing order within "
        "its chapter. Renumber or reorder body figures so sequence numbers rise "
        "in reading order."
    ),
    ("P057", "lot_page_numbers_not_nondecreasing"): (
        "List of Tables page numbers on this page do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "listed page numbers, so they increase from top to bottom."
    ),
    ("P057", "lof_page_numbers_not_nondecreasing"): (
        "List of Figures page numbers on this page do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "listed page numbers, so they increase from top to bottom."
    ),
    ("P059", "lot_entry_numbers_not_nondecreasing"): (
        "List of Tables entry numbers on this page do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "entry numbers, so they increase from top to bottom."
    ),
    ("P059", "lof_entry_numbers_not_nondecreasing"): (
        "List of Figures entry numbers on this page do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "entry numbers, so they increase from top to bottom."
    ),
    ("P061", "lot_cross_page_entry_numbers_not_nondecreasing"): (
        "List of Tables entry numbers may not be non-decreasing across a "
        "multi-page run. Verify cross-page numbering continuity in the LoT."
    ),
    ("P061", "lof_cross_page_entry_numbers_not_nondecreasing"): (
        "List of Figures entry numbers may not be non-decreasing across a "
        "multi-page run. Verify cross-page numbering continuity in the LoF."
    ),
    ("P062", "toc_cross_page_entry_numbers_not_nondecreasing"): (
        "Table of Contents section numbers may not be non-decreasing across a "
        "multi-page run. Verify cross-page numbering continuity in the TOC."
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
    ("P064", "references_entry_not_single_spaced"): (
        "Lines within one or more reference entries appear double-spaced. "
        "NJIT reviewer guidance asks for single spacing within each reference "
        "and double spacing between consecutive references. "
        "Open the References page and compare the line spacing inside a "
        "multi-line entry with the larger gap between entries. "
        "If the text layer is ambiguous or your citation style sets different "
        "internal spacing, review the entry manually with your advisor rather "
        "than forcing an automatic change."
    ),
    ("P064", "references_inter_entry_spacing_too_tight"): (
        "Gaps between consecutive reference entries appear close to the "
        "single-line spacing measured inside those entries. "
        "NJIT reviewer guidance asks for double spacing between references "
        "while keeping each reference single-spaced internally. "
        "Open the References page and check the blank space between the end of "
        "one entry and the start of the next. "
        "If wrapping, column layout, or citation-style rules make the intended "
        "gap unclear, prefer a careful manual review over an automatic rewrite."
    ),
    # --- P068 approval page structure ---
    ("P068", "approval_page_advisor_role_label_missing"): (
        "The Approval Page may be missing a recognizable advisor or committee role "
        "label (for example, 'Dissertation Advisor' or 'Major Professor'). Add the "
        "required advisor or committee role label for each committee entry on the "
        "Approval Page."
    ),
    ("P068", "approval_page_signature_blocks_sparse"): (
        "The Approval Page appears to have too few signature/date structural blocks "
        "for the committee entries present. Add the required signature/date "
        "structural block for each committee entry on the Approval Page."
    ),
}

# Rule-level fallback explanations (used when issue_type not matched above,
# or for grouped-problem cards where a single finding-level explanation
# is not appropriate).
_RULE_FALLBACKS: dict[str, str] = {
    "P011": (
        "Problem: Text on this page is not contained entirely within the required "
        "page margins. "
        "NJIT requires: left 1.5 inches, right 1 inch, top and bottom 1 inch. "
        "Move any text, table, or figure that extends into the margins back inside "
        "the required page area."
    ),
    "P012": (
        "This finding refers to an annotation, comment, sticky note, markup, or "
        "similar review object that was already present in the uploaded PDF -- not "
        "a highlight added by this auditor. "
        "These should usually be resolved or removed before final submission. "
        "Open the original PDF in your editor and accept, reject, or delete all "
        "reviewer comments before resubmitting."
    ),
    "P013": (
        "A visible page number on this page may not be located exactly in the "
        "designated bottom-center position. "
        "Set page numbers at the bottom center of the page, 0.5 inches from the "
        "bottom edge."
    ),
    "P019": (
        "Visible page numbers may not follow the expected style, position, or "
        "sequence for their section. "
        "Front matter should use lowercase Roman numerals in sequence; the main "
        "body should use Arabic numerals starting at 1."
    ),
    "P021": (
        "The abstract appears to exceed the allowed word count for the detected "
        "degree type. "
        "NJIT limits: PhD abstracts to 400 words, MS abstracts to 200 words. "
        "Review the abstract text and shorten it before submission."
    ),
    "P022": (
        "A front-matter page that should not carry a page number may have one. "
        "Remove visible page numbers from unnumbered front-matter pages such as "
        "the title page."
    ),
    "P023": (
        "Problem: Body text on this page does not appear to be double-spaced. "
        "Apply double spacing to body text and keep tables, figure descriptions, "
        "bullet points, and multi-line titles single-spaced."
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
        "Use lowercase Roman numerals for numbered front-matter pages and "
        "Arabic numerals for body pages."
    ),
    "P029": (
        "The Roman numeral page-number sequence in the front matter may be "
        "inconsistent. "
        "Correct the front-matter Roman numeral page numbers so they increase "
        "continuously in order."
    ),
    "P030": (
        "Problem: A continuation page of a multi-page Table of Contents, List of "
        "Tables, or List of Figures does not include the correct continued heading. "
        "Add the correct continued heading on each continuation page."
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
    "P051": (
        "The auditor may not have been able to confidently associate a copyright "
        "year with the copyright notice. Review the copyright page and confirm "
        "the year is present next to the copyright notice."
    ),
    "P052": (
        "The copyright page may be missing a clearly readable author name. "
        "Review the copyright page and confirm the author's name is present next "
        "to the copyright notice."
    ),
    "P038": (
        "A required front-matter section heading may be missing or not recognized. "
        "Review the document structure and ensure all required headings are present "
        "and worded exactly as NJIT specifies."
    ),
    "P041": (
        "Header text appears to be present in the top margin area of the "
        "Dedication page. Remove any running header or header text from the "
        "top margin area of the Dedication page."
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
        "The abstract may contain \"paper\" or \"article\" or first-person "
        "pronouns. Replace \"paper\" or \"article\" with \"dissertation,\" "
        "\"study,\" \"work,\" or \"research,\" and rewrite sentences to remove "
        "first-person pronouns such as \"I,\" \"me,\" \"my,\" \"we,\" or \"our.\""
    ),
    "P087": (
        "A Table of Contents title-structure issue was detected. Remove Abstract "
        "entries from the TOC, and qualify repeated generic headings so readers "
        "can tell chapter sections apart."
    ),
    "P088": (
        "A body figure-numbering issue was detected. Use a simple chapter.sequence "
        "label, keep numbers unique within each chapter, and keep them in order."
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
    from njit_auditor.p011_margin_presentation import margin_side_label

    return margin_side_label(details)


def _p011_margin_explanation(details: dict[str, str], *, page: int | None) -> str:
    from njit_auditor.p011_margin_presentation import (
        content_kind_from_details,
        margin_content_label,
        margin_detailed_fix_guidance,
        margin_expected_phrase,
        margin_requirement_phrase,
        page_context_from_details,
    )

    side = _margin_side_label(details)
    overflow = details.get("worst_overflow_pt", "").strip()
    line_count = details.get("affected_line_count", "").strip()
    page_context = page_context_from_details(details)
    content_kind = content_kind_from_details(details)
    if side == "required page margin":
        observed = (
            "Some content appears too close to or beyond a required page margin, "
            "but the exact side is unavailable"
        )
    else:
        observed = (
            f"{margin_content_label(page_context)} appears to cross the required "
            f"{side} boundary"
        )
    extras: list[str] = []
    if overflow:
        extras.append(f"about {overflow}pt beyond the boundary")
    if line_count:
        noun = "line" if line_count == "1" else "lines"
        extras.append(f"{line_count} affected text {noun}")
    if extras:
        observed = f"{observed} ({'; '.join(extras)})"
    fix_guidance = margin_detailed_fix_guidance(
        page_context=page_context,
        content_kind=content_kind,
        side_label=side,
        details=details,
    )
    return (
        f"Observed: {observed}. "
        f"Expected: {margin_expected_phrase(page_context)} "
        f"{margin_requirement_phrase(details)}. "
        "Why this is suspicious: layout content appears outside the printable area. "
        f"{fix_guidance}"
    )


_P012_ANNOTATION_LABELS: dict[str, str] = {
    "highlight": "highlight annotation",
    "text": "sticky note",
    "freetext": "comment annotation",
    "popup": "comment annotation",
}


def _p012_annotation_label(details: dict[str, str]) -> str:
    raw = details.get("annotation_type", "").strip()
    if not raw or raw.lower() == "unknown":
        return "PDF annotation"
    return _P012_ANNOTATION_LABELS.get(raw.lower(), "markup annotation")


def _p012_annotation_explanation(details: dict[str, str], *, page: int | None) -> str:
    annotation_label = _p012_annotation_label(details)
    location = f" on page {page}" if page is not None else ""
    return (
        f"Observed: The uploaded PDF appears to already contain a {annotation_label}"
        f"{location}. "
        "Expected: Before final submission, the PDF should be free of reviewer "
        "annotations, comments, sticky notes, and markup. "
        "Why this is suspicious: this finding refers to an annotation that was "
        "already present in the original file you uploaded -- it is not a highlight "
        "added by this auditor to show you where to look. "
        "What to check or fix: open the original PDF in your editor, accept or "
        "reject all reviewer changes, delete remaining comments, highlights, or "
        "markup, and upload a clean copy before final submission."
    )


def _p015_paragraph_descriptor(issue_type: str, details: dict[str, str]) -> str:
    if issue_type == "unexpected_opening_indent":
        return "the first paragraph after a heading"
    if issue_type == "unexpected_indent_on_continuation_line":
        paragraph_index = details.get("paragraph_index", "").strip()
        if paragraph_index:
            return f"continuation line in body paragraph {paragraph_index}"
        return "a continuation line after a displayed equation or similar break"
    paragraph_index = details.get("paragraph_index", "").strip()
    if paragraph_index:
        return f"body paragraph {paragraph_index}"
    return "a later body paragraph"


def _p015_indentation_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    descriptor = _p015_paragraph_descriptor(issue_type, details)
    indent_pt = details.get("indent_pt", "").strip()

    if issue_type == "unexpected_opening_indent":
        observed = f"{descriptor.capitalize()} starts with a first-line indent"
        if indent_pt:
            observed = f"{observed} (about {indent_pt}pt from the left margin)"
        expected = (
            f"{descriptor.capitalize()} should begin flush with the left margin"
        )
    elif issue_type == "unexpected_indent_on_continuation_line":
        observed = (
            f"{descriptor.capitalize()} starts with a paragraph-style first-line indent"
        )
        if indent_pt:
            observed = f"{observed} (about {indent_pt}pt from the left margin)"
        expected = (
            "Continuation lines after a displayed equation or similar break should "
            "begin flush with the left margin"
        )
    else:
        observed = f"{descriptor.capitalize()} appears to be missing its first-line indent"
        if indent_pt:
            observed = f"{observed} (about {indent_pt}pt first-line offset observed)"
        expected = (
            "Later body paragraphs should have a first-line indent of about 36pt "
            "(approximately half an inch)"
        )

    return (
        f"Observed: {observed}. "
        f"Expected: {expected}. "
        f"Why this is suspicious: the first line of {descriptor} does not match "
        "NJIT's expected paragraph-indentation pattern for this part of the document. "
        "What to check or fix: open the highlighted line and adjust the first-line "
        "indent, unless this paragraph intentionally starts a new block such as a "
        "heading, block quote, or list."
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


def _p029_roman_sequence_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    page_phrase = f"page {page}" if page is not None else "a front-matter page"
    observed = (
        details.get("observed_sequence", "").strip()
        or details.get("candidate_text", "").strip()
        or "the detected value"
    )
    expected = details.get("expected_sequence", "").strip() or "the expected value"
    if issue_type == "roman_sequence_repeat":
        return (
            f"Observed: {page_phrase.capitalize()} repeats the Roman numeral "
            f"'{observed}', the same value already used on the previous front-matter "
            "page. "
            "Expected: each front-matter page should have its own, increasing Roman "
            f"numeral (expected next: '{expected}'). "
            "Why this is suspicious: NJIT front-matter pages must be numbered "
            "consecutively with no repeats, so a repeated numeral usually means a "
            "page was duplicated or mislabeled. "
            "What to check or fix: renumber this page so it continues the sequence "
            "instead of repeating the previous page's number."
        )
    if issue_type == "roman_sequence_gap":
        return (
            f"Observed: {page_phrase.capitalize()} is numbered '{observed}', but the "
            f"next expected Roman numeral after the previous numbered front-matter page "
            f"was '{expected}' — one or more numerals were skipped. "
            "Expected: front-matter Roman numerals must increase by exactly one on "
            "every numbered page with no gaps. "
            "Why this is suspicious: a skipped numeral usually means a front-matter "
            "page was removed, left unnumbered, or mislabeled. "
            f"What to check or fix: change this page to '{expected}' or restore and "
            "renumber the missing front-matter pages so the sequence is consecutive."
        )
    if issue_type == "roman_sequence_decrease":
        return (
            f"Observed: The Roman numeral on {page_phrase} is '{observed}', lower than "
            "the numeral used on the previous front-matter page. "
            "Expected: front-matter Roman numerals should increase by one on every "
            f"numbered page (expected: '{expected}'). "
            "Why this is suspicious: a decreasing page number usually means a page was "
            "inserted, removed, or mislabeled. "
            "What to check or fix: renumber this page so the sequence keeps increasing "
            "instead of going backward."
        )
    return _GENERIC_FALLBACK


_P037_SECTION_KEY_LABELS: dict[str, str] = {
    "biographical_sketch": "Biographical Sketch",
    "dedication": "Dedication",
    "acknowledgements": "Acknowledgements",
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
}


def _p037_roman_section_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    page_phrase = f"page {page}" if page is not None else "this front-matter page"
    observed = (
        details.get("observed_roman", "").strip()
        or details.get("observed_sequence", "").strip()
        or "the detected value"
    )
    expected = (
        details.get("expected_roman", "").strip()
        or details.get("expected_sequence", "").strip()
        or "the expected value"
    )
    if issue_type == "roman_bio_sketch_not_iv":
        section_name = "Biographical Sketch"
    else:
        section_name = _P037_SECTION_KEY_LABELS.get(
            details.get("section_key", "").strip(), "front-matter section"
        )
    if issue_type == "roman_bio_sketch_not_iv":
        return (
            f"Observed: The Biographical Sketch page ({page_phrase}) is numbered '{observed}'. "
            "Expected: Biographical Sketch starts the numbered front matter at 'iv'. "
            "Why this is suspicious: later front-matter pages continue sequentially "
            "from this anchor. What to check or fix: change this page's Roman numeral "
            "to 'iv' and check the sequence on following pages."
        )
    return (
        f"Observed: The {section_name} page ({page_phrase}) is numbered '{observed}'. "
        f"Expected: '{expected}', the next Roman numeral after the preceding "
        "front-matter page. Why this is suspicious: numbering continues from "
        "Biographical Sketch page iv across every numbered front-matter page, "
        "including continuation pages. "
        f"What to check or fix: change this page's Roman numeral to '{expected}' "
        "or correct the preceding front-matter sequence."
    )


_P020_TITLE_CASE_REASON_TEXT: dict[str, str] = {
    "first_word_requires_capital": "the first word is not capitalized",
    "word_after_separator_requires_capital": (
        "a word after a colon, dash, or similar separator is not capitalized"
    ),
    "major_word_requires_capital": (
        "a major word (not an article, preposition, or conjunction) is not capitalized"
    ),
}


def _p020_title_case_explanation(details: dict[str, str], *, page: int | None) -> str:
    page_phrase = f"page {page}" if page is not None else "this document"
    source = details.get("source", "").strip() or "heading"
    reason = details.get("expected_or_reason", "").strip()
    reason_text = _P020_TITLE_CASE_REASON_TEXT.get(
        reason, "a word is not capitalized as expected"
    )
    subject = title_case_subject_kind(source)
    preview = sanitize_title_case_line_preview(details.get("line_preview", ""))
    title_phrase = affected_title_phrase(preview, source=source)
    if title_phrase:
        location_phrase = f"the {title_phrase} on {page_phrase}"
    else:
        location_phrase = f"a {subject} on {page_phrase}"
    flagged_word = details.get("flagged_word", "").strip()
    corrected_word = details.get("corrected_word", "").strip()
    word_clause = ""
    if flagged_word and corrected_word:
        word_clause = (
            f" Flagged word: '{flagged_word}' should be '{corrected_word}'."
        )
    if source == "caption":
        return (
            f"Observed: {location_phrase.capitalize()} appears to have a "
            f"capitalization problem: {reason_text}.{word_clause} "
            "Expected: NJIT requires table titles to use Title Case (every word "
            "capitalized except prepositions, conjunctions, and articles), and "
            "table titles must not end with a period. "
            "Why this is suspicious: the detector compares each word against "
            "NJIT's Title Case rule for table titles, so connector words "
            "(a, of, the, with, and similar) are correctly left lowercase and not "
            "flagged. "
            "What to check or fix: open the flagged page and capitalize the "
            "specific word the finding identifies as missing a capital letter."
        )
    rule_text = "NJIT requires Level 2 headings (e.g. 1.1, 1.2) to use Title Case"
    return (
        f"Observed: {location_phrase.capitalize()} appears to have a capitalization "
        f"problem: {reason_text}.{word_clause} "
        f"Expected: {rule_text} (capitalize the first word and all major "
        "words; leave articles, prepositions, and conjunctions lowercase "
        "in the middle). "
        "Why this is suspicious: the detector compares each word against NJIT's "
        "Title Case rule for this text role, so connector words (a, of, the, with, "
        "and similar) are correctly left lowercase and not flagged. "
        "What to check or fix: open the flagged page and capitalize the specific "
        "word the finding identifies as missing a capital letter."
    )


_P036_SPACING_ISSUE_TYPES: frozenset[str] = frozenset(
    {
        "toc_inter_entry_spacing_too_tight",
        "lot_inter_entry_spacing_too_tight",
        "lof_inter_entry_spacing_too_tight",
    }
)
_P036_SECTION_LABELS: dict[str, str] = {
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}


_P018_EXPECTED_BY_ISSUE_TYPE: dict[str, str] = {
    "wrapped_title_continuation_misaligned": (
        "when a title runs longer than one line, the second line aligns with the "
        "text of the first line, not the section number. What to check or fix: "
        "move the wrapped line so it starts directly under the first word of the "
        "title, neither left of it nor indented past it."
    ),
    "title_to_leader_gap_too_wide": (
        "leader dots begin right after the last letter of the title, with at most "
        "one space before the first dot. What to check or fix: remove the extra "
        "space between the title and its leader dots."
    ),
    "leader_dots_before_final_title_line": (
        "for a title that runs longer than one line, the leader dots start after "
        "the final line of the title. What to check or fix: move the leader dots "
        "to the final line of the title."
    ),
}


def _p018_alignment_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    page_phrase = f"page {page}" if page is not None else "this page"
    section_label = _P036_SECTION_LABELS.get(
        details.get("page_type", details.get("section_type", "")).strip(),
        "TOC/list",
    )
    preview = sanitize_toc_list_entry_preview(details.get("affected_entry_preview", ""))
    entry_clause = f' Entry: "{preview}".' if preview else ""
    count = details.get("affected_entry_count", "").strip()
    delta = details.get("worst_delta_pt", "").strip()
    extras: list[str] = []
    if count:
        noun = "entry" if count == "1" else "entries"
        extras.append(f"{count} {noun} affected on this page")
    if delta:
        extras.append(f"worst offset about {delta}pt")
    metrics = f" ({'; '.join(extras)})" if extras else ""
    expected = _P018_EXPECTED_BY_ISSUE_TYPE.get(
        issue_type,
        "list entries should keep consistent page numbers, leader dots, and "
        "hierarchy indentation. What to check or fix: open the flagged list page "
        "and compare the affected entry with nearby entries at the same level.",
    )
    return (
        f"Observed: A {section_label} alignment issue on {page_phrase}{metrics}."
        f"{entry_clause} Expected: {expected}"
    )

    try:
        index = int(details.get("entry_pair_index", "").strip())
    except ValueError:
        return "two consecutive entries"
    return f"entries {index + 1}-{index + 2}"


def _p036_spacing_explanation(details: dict[str, str], *, page: int | None) -> str:
    page_phrase = f"page {page}" if page is not None else "this page"
    section_label = _P036_SECTION_LABELS.get(
        details.get("section_type", "").strip(), "TOC/list"
    )
    entries_phrase = spacing_entries_phrase(
        details.get("previous_entry_preview", ""),
        details.get("next_entry_preview", ""),
    )
    gap_points = details.get("gap_points", "").strip()
    required_gap_points = details.get("required_gap_points", "").strip()
    extras: list[str] = []
    if gap_points:
        extras.append(f"observed gap {gap_points}pt")
    if required_gap_points:
        extras.append(f"expected at least {required_gap_points}pt")
    gap_ratio = details.get("gap_ratio", "").strip()
    if gap_ratio:
        extras.append(f"about {gap_ratio}x the expected spacing")
    detail_phrase = f" ({'; '.join(extras)})" if extras else ""
    return (
        f"Observed: {entries_phrase} of the {section_label} on "
        f"{page_phrase} do not appear to have visible double spacing or a blank "
        f"line between them{detail_phrase}. "
        "Expected: NJIT expects visible double spacing or a blank line between "
        "consecutive entries. "
        "Why this is suspicious: the gap between these two entries is smaller "
        "than the spacing NJIT's formatting rule expects. "
        "What to check or fix: add visible double spacing or a blank line "
        "between these entries, then compare with nearby entries in the same list."
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
        f"An unusually large blank gap{gap_clause} was detected just after a "
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
            "or committee role label for each committee entry on the Approval Page."
        )
    return (
        f"The Approval Page has {indicator_count} signature/date line(s) for "
        f"{role_label_count} committee role label(s), but at least {required} are "
        "expected. Add the required signature/date structural block for each "
        "committee entry on the Approval Page."
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
        f"A wrapped {entry_label} does not appear to be single-spaced within the "
        f"same entry{gap_clause}. Single-space wrapped entries so continuation "
        "lines stay within the same entry without extra blank space."
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
        "Postgraduate degree entries on the Biographical Sketch page appear to be "
        "out of order: the candidate years found (in listed order) run from "
        f"{first_year} to {last_year}, with {inversion_count} {place_noun} where a "
        "later-listed entry's year is more recent than the entry just before it. "
        "Reorder postgraduate degree entries in the Biographical Sketch from most "
        "recent to oldest."
    )


def _p067_publication_order_explanation(details: dict[str, str], *, page: int | None) -> str:
    first_year = details.get("first_entry_year", "").strip() or "an earlier year"
    last_year = details.get("last_entry_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        "Publication and presentation entries on the Biographical Sketch page "
        "appear to be out of order: the comparable entry years found (in listed "
        f"order) run from {first_year} to {last_year}, with {inversion_count} "
        f"{place_noun} where a later-listed entry's year is more recent than the "
        "entry just before it. Reorder publication and presentation entries in the "
        "Biographical Sketch from most recent to oldest. Manual review may still be "
        "needed for citation style, authorship, title correctness, venue correctness, "
        "and ambiguous multi-year entries."
    )


def _p045_hanging_indent_explanation(details: dict[str, str], *, page: int | None) -> str:
    # Legacy issue type (no longer emitted); see polished_comments.
    return (
        "Publication/presentation entries on the Biographical Sketch page do not "
        "appear to use a hanging indent. A hanging indent is optional, so no change "
        "is required for this."
    )


def _p045_line_spacing_explanation(details: dict[str, str], *, page: int | None) -> str:
    pitch = details.get("observed_line_pitch_points", "").strip()
    font_size = details.get("font_size_points", "").strip()
    gap_clause = (
        f" (wrapped lines about {pitch}pt apart for {font_size}pt text)"
        if pitch and font_size
        else ""
    )
    return (
        "Wrapped lines within a publication/presentation entry on the Biographical "
        f"Sketch page do not appear to be single-spaced{gap_clause}. Single-space the "
        "lines within each entry."
    )


def _p045_numbered_entry_explanation(details: dict[str, str], *, page: int | None) -> str:
    return (
        "Publication/presentation entries on the Biographical Sketch page start "
        "with a number or label such as [1] or 1. They are not references and "
        "must not be numbered. Remove the number in front of each entry and keep "
        "the same citation format as the References section."
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
        f"Sketch page do not appear to have a blank line between them{gap_clause}. "
        "Add a blank line between separate entries."
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
        f"{block_label} on the Biographical Sketch page appears to have extra spacing "
        f"inside the bullet item{gap_clause}. Single-space each bullet item in the "
        "Biographical Sketch education section, with no extra blank lines inside the "
        "same bullet item."
    )


_LOT_LOF_SECTION_LABELS: dict[str, str] = {
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}
_LOT_LOF_ENTRY_NOUNS: dict[str, str] = {
    "list_of_tables": "table",
    "list_of_figures": "figure",
}


def _lot_lof_section_label(details: dict[str, str]) -> str:
    section = details.get("section_type", "").strip()
    return _LOT_LOF_SECTION_LABELS.get(section, "List of Tables/List of Figures")


def _lot_lof_entry_noun(details: dict[str, str]) -> str:
    section = details.get("section_type", "").strip()
    return _LOT_LOF_ENTRY_NOUNS.get(section, "entry")


def _format_points(value: str) -> str:
    cleaned = value.strip()
    return f"{cleaned}pt" if cleaned else ""


def _font_metadata_clause(details: dict[str, str]) -> str:
    available = details.get("font_metadata_available", "").strip().lower()
    if available and available != "true":
        return (
            " Reliable style information could not be detected for this header, so "
            "please verify its boldness visually."
        )
    return ""


def _p031_column_header_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    section_label = _lot_lof_section_label(details)
    expected_left = details.get("expected_left_label", "").strip() or "Table/Figure"
    expected_page = details.get("expected_page_label", "").strip() or "Page"

    if issue_type == "missing_left_column_header":
        return (
            f"The {section_label} page does not show the required "
            f"'{expected_left}' column header. Add the required column headers "
            "directly below the list heading: "
            f"'{expected_left}' on the left and 'Page' on the right."
        )
    if issue_type == "missing_page_column_header":
        return (
            f"The {section_label} page does not show the required "
            f"'{expected_page}' column header. Add the required column headers "
            "directly below the list heading: "
            f"'{expected_left}' on the left and '{expected_page}' on the right."
        )
    observed = _format_points(details.get("observed_x0_pt", ""))
    if issue_type == "left_column_header_misaligned":
        expected = _format_points(details.get("expected_left_x_pt", ""))
        gap_clause = (
            f" (about {observed} observed vs. an expected position of about "
            f"{expected})"
            if observed and expected
            else ""
        )
        return (
            f"The '{expected_left}' column header on the {section_label} page "
            f"appears far from the entry column it labels{gap_clause}. NJIT "
            f"requires the '{expected_left}' header to line up with the entry "
            "numbers below it. Reposition the header to align with the entries."
        )
    expected = _format_points(details.get("expected_page_x_pt", ""))
    gap_clause = (
        f" (about {observed} observed vs. an expected position of about {expected})"
        if observed and expected
        else ""
    )
    return (
        f"The '{expected_page}' column header on the {section_label} page appears "
        f"far from the page-number column it labels{gap_clause}. NJIT requires the "
        f"'{expected_page}' header to line up with the page numbers below it. "
        "Reposition the header to align with the page numbers."
    )


def _p046_entry_alignment_explanation(details: dict[str, str], *, page: int | None) -> str:
    section_label = _lot_lof_section_label(details)
    entry_noun = _lot_lof_entry_noun(details)
    observed_range = _format_points(details.get("observed_x0_range_points", ""))
    allowed_range = _format_points(details.get("allowed_x0_range_points", ""))
    range_clause = (
        f" (entry numbers vary by about {observed_range} from left to right, vs. "
        f"an allowed variation of about {allowed_range})"
        if observed_range and allowed_range
        else ""
    )
    return (
        f"{section_label} entry numbers do not appear to be aligned vertically in "
        f"one left column{range_clause}. Align all {entry_noun} numbers in the "
        f"{section_label} into one consistent left column."
    )


def _p048_page_number_alignment_explanation(
    details: dict[str, str], *, page: int | None
) -> str:
    section_label = _lot_lof_section_label(details)
    observed = _format_points(details.get("observed_page_number_x", ""))
    expected = _format_points(details.get("expected_page_number_x", ""))
    measure_clause = (
        f" (about {observed} observed vs. an expected position of about {expected})"
        if observed and expected
        else ""
    )
    return (
        f"Page numbers in the {section_label} do not appear to be aligned "
        f"vertically in one right column{measure_clause}. Align all page numbers "
        f"in the {section_label} into one consistent right column."
    )


def _p049_page_header_style_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    section_label = _lot_lof_section_label(details)
    if issue_type in {
        "lot_page_header_not_right_aligned",
        "lof_page_header_not_right_aligned",
    }:
        observed = _format_points(details.get("observed_x", ""))
        expected = _format_points(details.get("expected_x", ""))
        measure_clause = (
            f" (about {observed} observed vs. an expected position of about "
            f"{expected})"
            if observed and expected
            else ""
        )
        return (
            f"The 'Page' column header on the {section_label} page does not appear "
            f"to be right-aligned over the page-number column{measure_clause}. "
            "Format the 'Page' column header in bold and align it over the "
            "page-number column on the right."
        )
    verify_clause = _font_metadata_clause(details)
    return (
        f"The 'Page' column header on the {section_label} page is not formatted "
        f"in bold.{verify_clause} Format the 'Page' column header in bold and "
        "align it over the page-number column on the right."
    )


def _p050_left_bold_explanation(details: dict[str, str], *, page: int | None) -> str:
    section_label = _lot_lof_section_label(details)
    header_word = "Table" if _lot_lof_entry_noun(details) == "table" else "Figure"
    verify_clause = _font_metadata_clause(details)
    return (
        f"Problem: The '{header_word}' column header on the {section_label} page "
        f"is not formatted in bold.{verify_clause} "
        f"Format the \"{header_word}\" column header in bold."
    )


def _p042_entry_position_clause(details: dict[str, str]) -> str:
    entry_index = details.get("entry_index", "").strip()
    entry_count = details.get("appendix_entry_count", "").strip()
    if entry_index.isdigit() and entry_count.isdigit():
        position = int(entry_index) + 1
        return f" (entry {position} of {entry_count} appendix entries listed)"
    return ""


def _p042_appendix_format_explanation(
    issue_type: str, details: dict[str, str], *, page: int | None
) -> str:
    if issue_type == "single_appendix_missing_title":
        expected_pattern = details.get("expected_pattern", "").strip() or "APPENDIX <title>"
        return (
            "The Table of Contents lists a single appendix entry that does not "
            "appear to include a title after 'APPENDIX'. For one appendix, begin "
            "the TOC entry with \"APPENDIX\" followed by the title "
            f"(pattern '{expected_pattern}'). Add the missing appendix title to "
            "this Table of Contents entry."
        )
    expected_pattern = details.get("expected_pattern", "").strip() or "APPENDIX <A-Z>"
    position_clause = _p042_entry_position_clause(details)
    return (
        f"The Table of Contents lists multiple appendix entries, but one entry"
        f"{position_clause} does not appear to include a letter identifier. "
        "For multiple appendices, label each TOC entry with a letter, such as "
        f"\"APPENDIX A,\" \"APPENDIX B,\" and so on (pattern '{expected_pattern}'). "
        "Add the missing letter to this Table of Contents entry."
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
    if rule_id == "P012" and effective_issue_type == "pdf_annotation_detected":
        return _p012_annotation_explanation(details, page=page)
    if rule_id == "P015" and effective_issue_type in {
        "unexpected_opening_indent",
        "missing_later_indent",
        "unexpected_indent_on_continuation_line",
    }:
        return _p015_indentation_explanation(effective_issue_type, details, page=page)
    if rule_id == "P026" and effective_issue_type in {
        "possible_body_font_family_issue",
        "possible_body_font_size_issue",
    }:
        return _p026_font_explanation(effective_issue_type, details, page=page)
    if rule_id == "P029" and effective_issue_type in {
        "roman_sequence_repeat",
        "roman_sequence_decrease",
        "roman_sequence_gap",
    }:
        return _p029_roman_sequence_explanation(effective_issue_type, details, page=page)
    if rule_id == "P037" and effective_issue_type in {
        "roman_bio_sketch_not_iv",
        "roman_section_wrong_value",
    }:
        return _p037_roman_section_explanation(effective_issue_type, details, page=page)
    if rule_id == "P020" and effective_issue_type == "possible_title_capitalization_issue":
        return _p020_title_case_explanation(details, page=page)
    if rule_id == "P036" and effective_issue_type in _P036_SPACING_ISSUE_TYPES:
        return _p036_spacing_explanation(details, page=page)
    if rule_id == "P018" and effective_issue_type in {
        "misaligned_page_number_column",
        "missing_page_number",
        "inconsistent_leader_dots",
        "inconsistent_hierarchy_indent",
        "wrapped_title_continuation_misaligned",
        "title_to_leader_gap_too_wide",
        "leader_dots_before_final_title_line",
    }:
        return _p018_alignment_explanation(effective_issue_type, details, page=page)
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
    if rule_id == "P045" and effective_issue_type == "biosketch_publication_entry_numbered":
        return _p045_numbered_entry_explanation(details, page=page)
    if (
        rule_id == "P045"
        and effective_issue_type == "biosketch_publication_missing_hanging_indent"
    ):
        return _p045_hanging_indent_explanation(details, page=page)
    if (
        rule_id == "P045"
        and effective_issue_type == "biosketch_publication_wrapped_line_spacing_not_single"
    ):
        return _p045_line_spacing_explanation(details, page=page)
    if (
        rule_id == "P045"
        and effective_issue_type == "biosketch_publication_entry_spacing_not_double"
    ):
        return _p045_entry_spacing_explanation(details, page=page)
    if rule_id == "P047" and effective_issue_type == "biosketch_bullet_section_not_single_spaced":
        return _p047_bullet_spacing_explanation(details, page=page)
    if rule_id == "P031" and effective_issue_type in {
        "missing_left_column_header",
        "missing_page_column_header",
        "left_column_header_misaligned",
        "page_column_header_misaligned",
    }:
        return _p031_column_header_explanation(effective_issue_type, details, page=page)
    if rule_id == "P046" and effective_issue_type in {
        "lot_entry_number_column_misaligned",
        "lof_entry_number_column_misaligned",
    }:
        return _p046_entry_alignment_explanation(details, page=page)
    if rule_id == "P048" and effective_issue_type in {
        "lot_page_number_column_misaligned",
        "lof_page_number_column_misaligned",
    }:
        return _p048_page_number_alignment_explanation(details, page=page)
    if rule_id == "P049" and effective_issue_type in {
        "lot_page_header_not_right_aligned",
        "lof_page_header_not_right_aligned",
        "lot_page_header_not_bold",
        "lof_page_header_not_bold",
    }:
        return _p049_page_header_style_explanation(effective_issue_type, details, page=page)
    if rule_id == "P050" and effective_issue_type in {
        "lot_table_header_not_bold",
        "lof_figure_header_not_bold",
    }:
        return _p050_left_bold_explanation(details, page=page)
    if rule_id == "P042" and effective_issue_type in {
        "single_appendix_missing_title",
        "multiple_appendix_missing_letter",
    }:
        return _p042_appendix_format_explanation(effective_issue_type, details, page=page)
    template = _EXPLANATION_TEMPLATES.get((rule_id, effective_issue_type))

    if template is not None:
        # Substitute known safe details into the template.
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
