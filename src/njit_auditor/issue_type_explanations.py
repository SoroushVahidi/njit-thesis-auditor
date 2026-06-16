"""Issue-type humanization and student-facing explanations for the web UI.

Presentation-layer only. Never changes detection semantics.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Explicit humanized labels for known issue types
# ---------------------------------------------------------------------------

_ISSUE_TYPE_LABELS: dict[str, str] = {
    # Annotation
    "pdf_annotation_detected": "PDF annotation detected",
    # Font
    "possible_body_font_family_issue": "Possible body font family issue",
    "possible_body_font_size_issue": "Possible body font size issue",
    # Margin
    "margin_boundary_violation": "Margin boundary violation",
    # Page numbering — P013 candidates
    "page_number_candidate": "Page number candidate",
    "missing_page_number": "Missing page number",
    "multiple_page_numbers": "Multiple page numbers on one page",
    "inconsistent_position": "Inconsistent page number position",
    "mixed_numbering_style": "Mixed numbering style",
    "sequence_gap": "Page number sequence gap",
    "p013_document_overview": "Page numbering overview (document-level)",
    # Page numbering — P028/P029 style
    "frontmatter_page_has_page_number": "Front-matter page has a page number",
    "frontmatter_page_number_style_issue": "Front-matter page number style issue",
    "body_page_roman_number": "Body page uses Roman numeral",
    "frontmatter_arabic_number": "Front-matter page uses Arabic numeral",
    "arabic_number_on_frontmatter_page": "Arabic numeral on front-matter page",
    "roman_number_on_body_page": "Roman numeral on body page",
    "uppercase_roman_on_frontmatter_page": "Uppercase Roman numeral on front-matter page",
    # Roman sequence (P029)
    "roman_sequence_gap": "Roman numeral sequence gap",
    "roman_sequence_repeat": "Roman numeral repeated",
    "roman_sequence_decrease": "Roman numeral decreased",
    # Page number sequence (P019)
    "page_number_sequence_error": "Page number sequence error",
    # Spacing
    "body_spacing_issue": "Body spacing issue",
    # Abstract
    "abstract_word_count_exceeded": "Abstract word count exceeded",
    "abstract_pdf_forbidden_term": "Abstract contains a forbidden term",
    "abstract_pdf_first_person_pronoun": "Abstract uses first-person pronoun",
    # Headings / TOC
    "missing_continued_heading": "Missing continued heading",
    "toc_missing_continued_heading": "TOC missing continued heading",
    "heading_phrase_not_exact": "Heading phrase not exact",
    "heading_style_issue": "Heading style issue",
    "level1_not_all_caps": "Level-1 heading not all caps",
    "level2_title_case_issue": "Level-2 heading not title case",
    # Figure / Table
    "table_body_not_centered": "Table body not centered",
    "figure_body_not_centered": "Figure body not centered",
    "table_caption_not_above_body": "Table caption not above body",
    "figure_caption_not_below_body": "Figure caption not below body",
    # Title / Copyright
    "title_page_mismatch": "Title page mismatch",
    "title_consistency_mismatch": "Title consistency mismatch",
    "copyright_year_mismatch": "Copyright year mismatch",
    "copyright_author_not_found": "Copyright author not found",
    "copyright_year_not_found": "Copyright year not found",
    # Dedication
    "dedication_text_not_centered": "Dedication text not centered",
    "dedication_text_not_italic": "Dedication text not italic",
    # References
    "references_structural_issue": "References structural issue",
    # Appendix
    "appendix_letter_sequence_gap": "Appendix letter sequence gap",
    "appendix_letter_sequence_repeat": "Appendix letter sequence repeated",
    # Approval page
    "approval_page_advisor_role_label_missing": "Approval page advisor role label missing",
    "approval_page_signature_blocks_sparse": "Approval page signature blocks sparse",
    # Captions
    "unexpected_terminal_period": "Unexpected terminal period in caption",
    "missing_terminal_punctuation": "Missing terminal punctuation in caption",
    "possible_sentence_case_issue": "Possible sentence case issue",
    "possible_title_case_issue": "Possible title case issue",
}

# ---------------------------------------------------------------------------
# Student-facing explanations
# ---------------------------------------------------------------------------

_RULE_ISSUE_EXPLANATIONS: dict[tuple[str, str], str] = {
    ("P012", "pdf_annotation_detected"): (
        "This means the PDF contains an annotation, comment, sticky note, markup, "
        "or similar review object. These should usually be resolved or removed before "
        "final submission. Open the PDF in your editor and accept, reject, or delete "
        "all reviewer comments before resubmitting."
    ),
    ("P026", "possible_body_font_family_issue"): (
        "This means some body text on this page appears to use a font that does not "
        "look like Times New Roman or an accepted Times-compatible font. Review the "
        "listed or highlighted text and correct the source document's font settings. "
        "NJIT requires Times New Roman 12pt for body text throughout."
    ),
    ("P026", "possible_body_font_size_issue"): (
        "This means some body text on this page appears outside the expected 12pt "
        "body-text size range. Review the listed or highlighted text and correct the "
        "source document's font size. NJIT requires Times New Roman 12pt for body text."
    ),
    ("P011", "margin_boundary_violation"): (
        "Some content appears too close to or beyond the required page margin. "
        "NJIT requires: left margin 1.5 inches, right margin 1 inch, top and bottom "
        "margins 1 inch. Review the highlighted area or listed page and adjust "
        "layout, indentation, tables, figures, or long lines."
    ),
    ("P023", "body_spacing_issue"): (
        "Body text on this page does not appear to use the required double line "
        "spacing. NJIT requires double line spacing throughout the body text. "
        "Check paragraph spacing settings and ensure no manual spacing overrides "
        "are in effect."
    ),
    ("P013", "page_number_candidate"): (
        "The checker detected text that looks like a page number. Verify that the "
        "page number is in the required position and uses the correct numbering style. "
        "Front-matter pages should use lowercase Roman numerals (i, ii, iii). "
        "Body pages should use Arabic numerals (1, 2, 3)."
    ),
    ("P013", "p013_document_overview"): (
        "This is a document-level summary of page numbering patterns across the PDF. "
        "It does not correspond to a single page. Review individual page-number "
        "findings below for specific issues to correct."
    ),
    ("P013", "missing_page_number"): (
        "A page is missing a visible page number. NJIT requires page numbers on all "
        "pages except the title page and possibly the first body page. Verify that "
        "no pages have been accidentally left unnumbered."
    ),
    ("P013", "multiple_page_numbers"): (
        "More than one page-number-like token was found on this page. Each page "
        "should have exactly one page number in the correct position. Review the "
        "page and remove any extra numbers."
    ),
    ("P013", "inconsistent_position"): (
        "The page number position on this page does not match the expected placement. "
        "NJIT requires page numbers to be consistently placed — typically centered "
        "at the bottom of each page throughout the document."
    ),
    ("P013", "mixed_numbering_style"): (
        "This page uses a numbering style that does not match the expected section. "
        "Front-matter pages must use Roman numerals (i, ii, iii) and body pages "
        "must use Arabic numerals (1, 2, 3) in their respective sections."
    ),
    ("P013", "sequence_gap"): (
        "There is a gap in the page number sequence. Page numbers must be "
        "consecutive with no skipped numbers. Verify no pages were accidentally "
        "removed or misnumbered."
    ),
    ("P019", "page_number_sequence_error"): (
        "The page number sequence has an error — a number is out of order, repeated, "
        "or missing. Page numbers must increase sequentially with no gaps or repeats."
    ),
    ("P021", "abstract_word_count_exceeded"): (
        "The abstract appears to exceed the allowed word count for the detected "
        "degree type. PhD abstracts must be 350 words or fewer; MS/Master abstracts "
        "must be 150 words or fewer. Shorten the abstract before submission."
    ),
    ("P022", "frontmatter_page_has_page_number"): (
        "A front-matter page that should not display a page number was found with "
        "one. Certain pages (such as the title page) should not show a page number "
        "even though they are counted in the sequence."
    ),
    ("P028", "frontmatter_page_number_style_issue"): (
        "The page number style on this front-matter page does not match NJIT "
        "requirements. Front-matter pages must use lowercase Roman numerals "
        "(i, ii, iii). Body pages must use Arabic numerals (1, 2, 3)."
    ),
    ("P028", "body_page_roman_number"): (
        "A body page is numbered with a Roman numeral instead of an Arabic numeral. "
        "Body pages (starting from the main text) must use Arabic numerals (1, 2, 3). "
        "Only front-matter pages use Roman numerals."
    ),
    ("P028", "frontmatter_arabic_number"): (
        "A front-matter page is numbered with an Arabic numeral instead of a Roman "
        "numeral. Front-matter pages must use lowercase Roman numerals (i, ii, iii)."
    ),
    ("P029", "roman_sequence_gap"): (
        "There is a gap in the Roman numeral page number sequence for front-matter "
        "pages. Roman numeral numbers must be consecutive with no skipped values. "
        "Verify no front-matter pages were accidentally removed or misnumbered."
    ),
    ("P030", "missing_continued_heading"): (
        "A multi-page list (such as a List of Tables or List of Figures) may be "
        "missing a required continued heading on a continuation page. "
        "NJIT requires '(Continued)' in the heading when such lists span multiple pages."
    ),
    ("P030", "toc_missing_continued_heading"): (
        "The Table of Contents spans multiple pages but may be missing a "
        "'TABLE OF CONTENTS (Continued)' heading on continuation pages. "
        "NJIT requires this heading on each continuation page of the TOC."
    ),
    ("P033", "title_page_mismatch"): (
        "Title-page metadata may be inconsistent. Common issues include the degree "
        "line, author block, or university name not matching the expected format. "
        "Manually verify the title page against NJIT front-matter requirements."
    ),
    ("P033", "title_consistency_mismatch"): (
        "The title shown in different parts of the document may not be consistent. "
        "Verify that the title is identical wherever it appears: title page, "
        "abstract, and table of contents."
    ),
    ("P034", "copyright_year_mismatch"): (
        "The copyright year on the copyright page may not match the expected format "
        "or year. Confirm the copyright block includes the correct year."
    ),
    ("P034", "copyright_author_not_found"): (
        "A copyright page was detected but the author name could not be verified. "
        "Confirm the copyright block includes the required author name."
    ),
    ("P034", "copyright_year_not_found"): (
        "A copyright page was detected but no year token was found. "
        "Confirm the copyright block includes the required year."
    ),
    ("P038", "heading_phrase_not_exact"): (
        "A required heading phrase does not exactly match the expected wording. "
        "NJIT requires specific exact heading text for sections such as the abstract, "
        "dedication, acknowledgements, and others. Check spelling, capitalization, "
        "and spacing against the official NJIT formatting guidelines."
    ),
    ("P063", "appendix_letter_sequence_gap"): (
        "The appendix letters appear to have a gap in their sequence "
        "(for example, A, B, D — missing C). "
        "Appendices must be labeled consecutively with no gaps."
    ),
    ("P063", "appendix_letter_sequence_repeat"): (
        "An appendix letter is repeated in the sequence. Each appendix must have "
        "a unique letter label (A, B, C, ...). Review appendix headings and "
        "correct the labels."
    ),
    ("P064", "references_structural_issue"): (
        "The references section may have a structural issue. Verify that all "
        "references are properly formatted and that the references heading and "
        "list structure match NJIT guidelines."
    ),
    ("P065", "dedication_text_not_centered"): (
        "The dedication text does not appear to be centered on the page. "
        "NJIT requires dedication text to be centered. Adjust the paragraph "
        "alignment in your source document."
    ),
    ("P065", "dedication_text_not_italic"): (
        "The dedication text does not appear to be in italic. "
        "NJIT requires dedication text to be italicized. Apply italic formatting "
        "to the dedication text in your source document."
    ),
    ("P078", "abstract_pdf_forbidden_term"): (
        "The abstract contains a term that is not recommended for formal thesis "
        "abstracts. Review the abstract text and revise as needed to meet "
        "NJIT submission requirements."
    ),
    ("P078", "abstract_pdf_first_person_pronoun"): (
        "The abstract uses a first-person pronoun (I, we, my, our). Thesis "
        "abstracts should typically be written in third person. Revise the "
        "abstract to avoid first-person language."
    ),
}

# Issue-type-only fallback explanations (no rule_id match needed)
_ISSUE_TYPE_EXPLANATIONS: dict[str, str] = {
    "pdf_annotation_detected": (
        "This means the PDF contains an annotation, comment, sticky note, markup, "
        "or similar review object. These should usually be resolved or removed before "
        "final submission."
    ),
    "possible_body_font_family_issue": (
        "This means some body text appears to use a font that does not look like "
        "Times New Roman or an accepted Times-compatible font. Review the highlighted "
        "text and correct the font settings. NJIT requires Times New Roman 12pt."
    ),
    "possible_body_font_size_issue": (
        "This means some body text appears outside the expected 12pt size range. "
        "Review the highlighted text and correct the font size. "
        "NJIT requires Times New Roman 12pt for body text."
    ),
    "margin_boundary_violation": (
        "Some content may be too close to, or outside, the required page margin. "
        "Review the highlighted area or listed page and adjust layout, indentation, "
        "tables, figures, or long lines."
    ),
    "page_number_candidate": (
        "The checker detected text that looks like a page number. Verify that the "
        "page number is in the required position and uses the correct numbering "
        "style for that section."
    ),
    "body_spacing_issue": (
        "Body text on this page does not appear to use the required double line "
        "spacing. NJIT requires double line spacing throughout the body text."
    ),
    "frontmatter_page_number_style_issue": (
        "The page number style on this front-matter page does not match NJIT "
        "requirements. Front-matter pages must use lowercase Roman numerals (i, ii, iii). "
        "Body pages must use Arabic numerals (1, 2, 3)."
    ),
    "abstract_word_count_exceeded": (
        "The abstract appears to exceed the allowed word count. "
        "PhD abstracts must be 350 words or fewer; MS/Master abstracts "
        "must be 150 words or fewer."
    ),
}

_GENERIC_FALLBACK = (
    "This is an internal issue category used by the automated check. "
    "Review the finding and verify it against NJIT formatting requirements."
)

# Abbreviations that should stay uppercase in humanized labels
_UPPERCASE_WORDS: frozenset[str] = frozenset({"PDF", "TOC", "LOF", "LOT", "URL", "ID"})


def humanize_issue_type(issue_type: str) -> str:
    """Return a readable label for an internal issue_type string.

    Uses explicit mappings for known types; falls back to capitalized
    underscore-to-space conversion with common abbreviations preserved.
    """
    if not issue_type:
        return ""
    explicit = _ISSUE_TYPE_LABELS.get(issue_type)
    if explicit is not None:
        return explicit
    words = issue_type.replace("_", " ").split()
    if not words:
        return issue_type
    result = []
    for i, word in enumerate(words):
        if word.upper() in _UPPERCASE_WORDS:
            result.append(word.upper())
        elif i == 0:
            result.append(word.capitalize())
        else:
            result.append(word)
    return " ".join(result)


def explain_issue_type(rule_id: str, issue_type: str) -> str:
    """Return a student-facing explanation for a (rule_id, issue_type) pair.

    Never reproduces dissertation body text. Falls back gracefully for
    unknown issue types.
    """
    explicit = _RULE_ISSUE_EXPLANATIONS.get((rule_id, issue_type))
    if explicit is not None:
        return explicit
    fallback = _ISSUE_TYPE_EXPLANATIONS.get(issue_type)
    if fallback is not None:
        return fallback
    if not issue_type:
        return _GENERIC_FALLBACK
    label = humanize_issue_type(issue_type)
    return (
        f"This issue type ({label}) was flagged by an automated check. "
        "Review the finding and verify it against NJIT formatting requirements."
    )
