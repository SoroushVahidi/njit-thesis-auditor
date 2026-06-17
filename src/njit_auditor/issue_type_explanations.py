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
    # Page numbering — P022/P028/P029 style
    "visible_page_number_on_no_number_page": "Page number visible on a no-number page",
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
    "single_appendix_uses_letter_label": "Single appendix uses letter label",
    "multiple_appendix_missing_letter": "Appendix missing letter label",
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
# Precise, issue-specific titles (used when a category/rule/issue-type page
# narrows down to exactly one issue type, instead of a broad category/rule
# title that could describe several unrelated checks).
# ---------------------------------------------------------------------------

_ISSUE_TYPE_TITLES: dict[tuple[str, str], str] = {
    ("P063", "single_appendix_uses_letter_label"): "Appendix heading label convention",
    ("P063", "multiple_appendix_missing_letter"): "Appendix heading label convention",
    ("P063", "appendix_letter_sequence_gap"): "Appendix letter sequence gap",
    ("P063", "appendix_letter_sequence_repeat"): "Appendix letter sequence repeated",
}


def issue_type_title(rule_id: str, issue_type: str) -> str:
    """Return a precise, issue-specific page title for a (rule_id, issue_type) pair.

    Falls back to the humanized issue-type label when no explicit override
    exists, so every issue type still gets a specific (not broad-category)
    title.
    """
    explicit = _ISSUE_TYPE_TITLES.get((rule_id, issue_type))
    if explicit is not None:
        return explicit
    label = humanize_issue_type(issue_type)
    if label and rule_id:
        return f"{label} ({rule_id})"
    return label or rule_id or "Finding"


def has_curated_issue_type_title(rule_id: str, issue_type: str) -> bool:
    """Return True when an explicit, hand-curated title override exists.

    Used to decide whether a rule page (whose canonical rule title is
    usually already specific to one check) should be replaced with an
    issue-specific title, versus a category page (whose label is always a
    broad umbrella) which should switch to *some* issue-specific title
    whenever exactly one issue type is present, curated or not.
    """
    return (rule_id, issue_type) in _ISSUE_TYPE_TITLES


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
        "This means the auditor detected text that looks like a page number. "
        "This issue type is primarily a verification signal: it helps identify "
        "where the page number appears so that placement, style, visibility, "
        "and sequence can be checked. NJIT requires page numbers to appear at "
        "the bottom of the page, using lowercase Roman numerals (i, ii, iii) "
        "for front matter and Arabic numerals (1, 2, 3) for body pages. If "
        "the number is already in the required bottom position and uses the "
        "correct numbering style, this finding may not require any change."
    ),
    ("P013", "p013_document_overview"): (
        "This is a document-level, informational summary of page numbering "
        "patterns across the PDF. It does not by itself identify a specific "
        "formatting defect and does not correspond to a single page. Review "
        "individual page-number findings below for specific issues to correct."
    ),
    ("P019", "page_number_sequence_error"): (
        "The page number sequence has an error — a number is out of order, repeated, "
        "or missing. Page numbers must increase sequentially with no gaps or repeats."
    ),
    ("P019", "missing_page_number"): (
        "A page is missing a visible page number even though neighboring pages "
        "have one. NJIT requires every counted page to display a visible page "
        "number. Verify that no page was accidentally left unnumbered."
    ),
    ("P019", "multiple_page_numbers"): (
        "More than one page-number-like token was found on this page. Each page "
        "should have exactly one page number in the correct position. Review the "
        "page and remove any extra numbers."
    ),
    ("P019", "inconsistent_position"): (
        "The page number position on this page does not match the dominant "
        "placement used elsewhere in the document. "
        "NJIT requires page numbers to be consistently placed at the bottom "
        "of each page throughout the document."
    ),
    ("P019", "mixed_numbering_style"): (
        "This page uses a numbering style that does not match the expected section. "
        "Front-matter pages must use Roman numerals (i, ii, iii) and body pages "
        "must use Arabic numerals (1, 2, 3) in their respective sections."
    ),
    ("P019", "sequence_gap"): (
        "There is a gap in the page number sequence. Page numbers must be "
        "consecutive with no skipped numbers. Verify no pages were accidentally "
        "removed or misnumbered."
    ),
    ("P021", "abstract_word_count_exceeded"): (
        "The abstract appears to exceed the allowed word count for the detected "
        "degree type. PhD abstracts must be 350 words or fewer; MS/Master abstracts "
        "must be 150 words or fewer. Shorten the abstract before submission."
    ),
    ("P022", "visible_page_number_on_no_number_page"): (
        "A front-matter page that should not display a page number was found with "
        "one. The abstract, title, approval, and copyright pages should not show "
        "a page number even though they are counted in the sequence."
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
    ("P028", "arabic_number_on_frontmatter_page"): (
        "A front-matter page is numbered with an Arabic numeral instead of a "
        "Roman numeral. Front-matter pages must use lowercase Roman numerals "
        "(i, ii, iii)."
    ),
    ("P028", "uppercase_roman_on_frontmatter_page"): (
        "A front-matter page is numbered with an uppercase Roman numeral. "
        "Front-matter pages must use lowercase Roman numerals (i, ii, iii), "
        "not uppercase (I, II, III)."
    ),
    ("P028", "roman_number_on_body_page"): (
        "A body page is numbered with a Roman numeral instead of an Arabic "
        "numeral. Body pages (starting from the main text) must use Arabic "
        "numerals (1, 2, 3). Only front-matter pages use Roman numerals."
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
    ("P063", "single_appendix_uses_letter_label"): (
        "This means the document appears to have only one appendix, but its "
        "heading uses a lettered label such as 'APPENDIX A.' NJIT convention "
        "expects a single appendix to be labeled 'APPENDIX' without a "
        "letter. Lettered labels ('APPENDIX A,' 'APPENDIX B,' etc.) are only "
        "used when the document has multiple appendices. Rename the "
        "appendix heading, or check whether the document actually has "
        "additional appendices that were not detected."
    ),
    ("P063", "multiple_appendix_missing_letter"): (
        "This means multiple appendices were detected, but at least one "
        "appendix heading does not include a letter identifier. NJIT "
        "convention requires every appendix to be labeled 'APPENDIX A,' "
        "'APPENDIX B,' etc. when there is more than one. Add the missing "
        "letter to the appendix heading."
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
        "The checker detected text that looks like a page number. This is "
        "primarily a verification signal, not a confirmed defect by itself. "
        "Verify that the page number is in the required bottom position and "
        "uses the correct Roman or Arabic numbering style for that section."
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
