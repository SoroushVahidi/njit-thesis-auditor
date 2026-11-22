"""Issue-type humanization and student-facing explanations for the web UI.

Presentation-layer only. Never changes detection semantics.
"""
from __future__ import annotations

from collections.abc import Mapping

from njit_auditor.caption_continuation_preview import caption_continuation_explanation
from njit_auditor.ester_warning_wording import student_warning_label
from njit_auditor.p018_guidance import P018_WRAPPED_TITLE_FIX

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
    "detected_page_number_candidate": "Detected page-number candidate",
    "missing_page_number": "Missing page number",
    "multiple_page_numbers": "Multiple page numbers on one page",
    "inconsistent_position": "Inconsistent page number position",
    "mixed_numbering_style": "Mixed numbering style",
    "sequence_gap": "Page number sequence gap",
    "wrong_page_number_location": "Wrong page-number location",
    "wrong_page_numbering_style": "Wrong page-numbering style",
    "wrong_page_number_sequence": "Wrong page-number sequence",
    "duplicate_or_ambiguous_page_number": "Duplicate or ambiguous page number",
    "page_number_should_be_suppressed": "Page number should be suppressed",
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
    "possible_body_text_not_double_spaced": "Body text not double-spaced",
    "excessive_line_gap": "Excessive line gap",
    "excessive_paragraph_gap": "Excessive paragraph gap",
    "suspicious_heading_blank_gap": "Suspicious heading blank gap",
    # Abstract
    "abstract_word_count_exceeded": "Abstract word count exceeded",
    "abstract_pdf_forbidden_term": "Abstract contains a forbidden term",
    "abstract_pdf_first_person_pronoun": "Abstract uses first-person pronoun",
    "biosketch_birth_information_present": "Biographical Sketch birth information present",
    "toc_mixed_leader_styles": "TOC mixed leader styles",
    "toc_missing_leader_style": "TOC missing leader style",
    # Headings / TOC
    "missing_continued_heading": "Missing continued heading",
    "toc_missing_continued_heading": "TOC missing continued heading",
    "heading_phrase_not_exact": "Heading phrase not exact",
    "heading_style_issue": "Heading style issue",
    "level1_not_all_caps": "Level-1 heading not all caps",
    "level2_title_case_issue": "Level-2 heading not title case",
    "level3_sentence_case_issue": "Level-3 heading not sentence case",
    "level4_sentence_case_issue": "Level-4 heading not sentence case",
    "level4_sentence_case_or_punctuation_issue": "Level-4 heading missing terminal period",
    "level5_sentence_case_issue": "Level-5 heading not sentence case",
    "level5_sentence_case_or_punctuation_issue": "Level-5 heading missing terminal period",
    "possible_title_capitalization_issue": "Possible title-case issue",
    "missing_abstract_body": "Abstract heading present but body text missing",
    "missing_title_page_degree_phrase": "Title page missing degree phrase",
    "missing_title_page_institution": "Title page missing institution name",
    "sparse_approval_page_content": "Approval page content appears sparse",
    "possible_frontmatter_order_issue": "Front-matter ordering issue",
    "required_heading_missing": "Required front-matter heading missing",
    # Figure / Table
    "table_body_not_centered": "Table body not centered",
    "figure_body_not_centered": "Figure body not centered",
    "table_caption_not_above_body": "Table title not above body",
    "figure_caption_not_below_body": "Figure description not below body",
    # Title / Copyright
    "title_page_mismatch": "Title page mismatch",
    "title_consistency_mismatch": "Title consistency mismatch",
    "frontmatter_title_mismatch": "Front-matter title mismatch",
    "copyright_year_mismatch": "Copyright year mismatch",
    "copyright_author_not_found": "Copyright author not found",
    "copyright_year_not_found": "Copyright year could not be confidently associated",
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
    "title_page_graduation_month_invalid": "Title page graduation month invalid",
    "references_section_heading_not_detected": "References section heading not detected",
    "references_entry_indentation_inconsistent": "References entry indentation inconsistent",
    "references_entry_spacing_inconsistent": "References entry spacing inconsistent",
    "references_entry_not_single_spaced": "Reference entries not single-spaced",
    "references_inter_entry_spacing_too_tight": "Reference inter-entry spacing too tight",
    "toc_page_numbers_not_nondecreasing": "TOC page numbers not in ascending order",
    "toc_entry_numbers_not_nondecreasing": "TOC section numbers not in order",
    "lot_entry_has_terminal_period": "List of Tables entry has terminal period",
    "toc_entry_has_terminal_period": "TOC entry has terminal period",
    "lot_entry_is_figure": "List of Tables entry describes a figure",
    "lof_entry_is_table": "List of Figures entry describes a table",
    "lot_entry_missing_table_prefix": "Numbered entry without a recognized 'Table' heading",
    "lof_entry_missing_figure_prefix": "Legacy List of Figures prefix advisory",
    "body_figure_reference_abbreviated": "Abbreviated body figure reference",
    "lof_entry_missing_terminal_punctuation": "List of Figures entry missing terminal punctuation",
    "toc_l2_not_indented_relative_to_l1": "TOC level-2 entry not indented relative to level-1",
    "toc_l3_not_indented_relative_to_l2": "TOC level-3 entry not indented relative to level-2",
    "toc_subsection_number_ambiguous": "Possible missing dot in TOC subsection number",
    "toc_abstract_entry_present": "Abstract entry listed in the Table of Contents",
    "toc_generic_title_repeated": "Repeated generic TOC section title",
    "figure_number_malformed": "Malformed figure number in body caption",
    "figure_number_duplicate": "Duplicate figure number within a chapter",
    "figure_number_out_of_order": "Out-of-order figure number within a chapter",
    "toc_level_capitalization": "TOC entry capitalization issue",
    "list_of_tables_title_case": "List of Tables title case issue",
    "list_of_figures_title_case": "List of Figures description sentence case issue",
    "misaligned_page_number_column": "Misaligned page-number column",
    "inconsistent_leader_dots": "Inconsistent leader dots",
    "inconsistent_hierarchy_indent": "Inconsistent hierarchy indent",
    "wrapped_title_continuation_misaligned": "Wrapped TOC continuation starts left of title text",
    "title_to_leader_gap_too_wide": "Gap between title and leader dots",
    "leader_dots_before_final_title_line": "Leader dots on an earlier title line",
    "acknowledgements_first_paragraph_indented": "Acknowledgements first paragraph indented",
    "acknowledgements_subsequent_paragraph_not_indented": (
        "Acknowledgements paragraph after the first not indented"
    ),
    "digital_commons_wrapper_pages_detected": "Digital Commons wrapper pages detected",
    "abstract_first_paragraph_indented": "Abstract first paragraph indented",
    "abstract_subsequent_paragraph_not_indented": "Abstract paragraph after the first not indented",
    "biosketch_publication_entry_numbered": "Numbered Biographical Sketch publication entry",
    "biosketch_publication_missing_hanging_indent": (
        "Biographical Sketch publication without hanging indent (optional)"
    ),
    "biosketch_publication_wrapped_line_spacing_not_single": (
        "Biographical Sketch publication lines not single-spaced"
    ),
    "biosketch_publication_entry_spacing_not_double": (
        "Biographical Sketch publication entry spacing not double"
    ),
    "biosketch_bullet_section_not_single_spaced": (
        "Biographical Sketch bullet section not single-spaced"
    ),
    "multiline_body_heading_not_single_spaced": "Wrapped body heading not single-spaced",
    "biosketch_degree_order_suspicious": "Biographical Sketch degree order suspicious",
    "biosketch_publication_order_suspicious": "Biographical Sketch publication order suspicious",
    "unexpected_opening_indent": "Unexpected opening paragraph indent",
    "missing_later_indent": "Missing paragraph-after-first indent",
    "unexpected_indent_on_continuation_line": "Unexpected indent on continuation line",
    "wrapped_entry_internal_spacing": "Wrapped list entry internal spacing",
    "single_appendix_missing_title": "Single appendix missing title",
    "lot_mixed_numbering_format": "List of Tables mixed numbering format",
    "lof_mixed_numbering_format": "List of Figures mixed numbering format",
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


def student_facing_issue_label(rule_id: str, issue_type: str) -> str:
    """Prefer Ester yes/no questions over internal issue-type labels when mapped."""
    ester = student_warning_label(rule_id, issue_type)
    if ester:
        return ester
    return humanize_issue_type(issue_type)


def issue_type_title(rule_id: str, issue_type: str) -> str:
    """Return a precise, issue-specific page title for a (rule_id, issue_type) pair.

    Falls back to the humanized issue-type label when no explicit override
    exists, so every issue type still gets a specific (not broad-category)
    title.

    Titles are student-facing prose and must not embed raw internal ``P###``/
    ``Q###`` identifiers. Rule IDs remain available as separate rule-reference
    links elsewhere in the UI.
    """
    explicit = _ISSUE_TYPE_TITLES.get((rule_id, issue_type))
    if explicit is not None:
        return explicit
    ester = student_warning_label(rule_id, issue_type)
    if ester:
        return ester
    label = humanize_issue_type(issue_type)
    return label or "Finding"


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
        "This means the uploaded PDF already contains an annotation, comment, "
        "sticky note, markup, or similar review object -- something left in the "
        "original file you uploaded, not a highlight added by this auditor. These "
        "should usually be resolved or removed before final submission. Open the "
        "original PDF in your editor and accept, reject, or delete all reviewer "
        "comments before resubmitting."
    ),
    ("P026", "possible_body_font_family_issue"): (
        "This means sampled body-text-like spans appear to use a font family other "
        "than Times New Roman or an accepted Times-compatible font. Review the card's "
        "observed font value, confirm whether the flagged text is body text rather than "
        "a caption, heading, table entry, or footnote, and then correct the source "
        "document's body-text font settings if needed."
    ),
    ("P026", "possible_body_font_size_issue"): (
        "This means sampled body-text-like spans appear outside the expected 12pt "
        "body-text size. Review the card's observed size value, confirm whether the "
        "flagged text is body text rather than a caption, heading, table entry, or "
        "footnote, and then correct the source document's body-text size if needed."
    ),
    ("P011", "margin_boundary_violation"): (
        "This means the auditor found content that appears too close to or beyond a "
        "required page margin boundary. Review the card for the flagged side and page, "
        "then inspect tables, figures, long lines, indentation, headers, and footers. "
        "NJIT requires a 1.5-inch left margin and 1-inch top, right, and bottom margins."
    ),
    ("P020", "possible_title_capitalization_issue"): (
        "This means a Level 2 heading or table title appears to violate NJIT "
        "title-case rules: the first word, last word, or a major word (4+ "
        "letters) is not capitalized. Capitalize the flagged word so the "
        "title-like text follows Title Case."
    ),
    ("P027", "level1_not_all_caps"): (
        "This means a Level 1 heading (a CHAPTER or APPENDIX title) does not "
        "appear to be in ALL CAPS. NJIT requires Level 1 headings to be ALL "
        "CAPS, bold, and centered. This applies only to Level 1 headings."
    ),
    ("P027", "level2_title_case_issue"): (
        "This means a Level 2 heading (numbered like 1.1 or 1.2) does not "
        "appear to use Title Case. NJIT requires Level 2 headings to use "
        "Title Case, bold. This applies only to Level 2 headings."
    ),
    ("P027", "level3_sentence_case_issue"): (
        "This means a Level 3 heading (numbered like 1.1.1) appears to use "
        "Title Case where Sentence case is expected. NJIT requires Level 3 "
        "headings to use Sentence case, bold. This applies only to Level 3 "
        "headings."
    ),
    ("P027", "level4_sentence_case_issue"): (
        "This means a Level 4 heading (numbered like 1.1.1.1) appears to use "
        "Title Case where Sentence case is expected. NJIT requires Level 4 "
        "headings to use Sentence case, ending with a period. This applies "
        "only to Level 4 headings."
    ),
    ("P027", "level4_sentence_case_or_punctuation_issue"): (
        "This means a Level 4 heading (numbered like 1.1.1.1) appears to be "
        "missing its required terminal period. NJIT requires Level 4 "
        "headings to end with a period."
    ),
    ("P027", "level5_sentence_case_issue"): (
        "This means a Level 5 heading (numbered like 1.1.1.1.1) appears to "
        "use Title Case where Sentence case is expected. NJIT requires Level "
        "5 headings to use Sentence case, ending with a period. This "
        "applies only to Level 5 headings."
    ),
    ("P027", "level5_sentence_case_or_punctuation_issue"): (
        "This means a Level 5 heading (numbered like 1.1.1.1.1) appears to "
        "be missing its required terminal period. NJIT requires Level 5 "
        "headings to end with a period."
    ),
    ("P025", "missing_abstract_body"): (
        "This means an ABSTRACT heading was found but no body text was "
        "detected below it. NJIT requires the Abstract page to contain the "
        "abstract text. Add the abstract body text below the heading."
    ),
    ("P025", "missing_title_page_degree_phrase"): (
        "This means no degree phrase (e.g. 'Doctor of Philosophy', 'Master "
        "of Science') was detected on the title page. NJIT requires the "
        "title page to state the degree being conferred."
    ),
    ("P025", "missing_title_page_institution"): (
        "This means the institution name was not detected on the title "
        "page. NJIT requires the title page to include 'New Jersey "
        "Institute of Technology'."
    ),
    ("P025", "sparse_approval_page_content"): (
        "This means an APPROVAL PAGE heading was found but the content "
        "below it appears sparse. NJIT requires the Approval Page to "
        "include committee member names, titles, and signature lines."
    ),
    ("P025", "possible_frontmatter_order_issue"): (
        "This means the ABSTRACT heading appears after the TABLE OF "
        "CONTENTS. NJIT requires the Abstract to appear before the Table "
        "of Contents."
    ),
    ("P023", "possible_body_text_not_double_spaced"): (
        "Body text on this page does not appear to use the required double line "
        "spacing. NJIT requires double line spacing throughout the body text. "
        "Check paragraph spacing settings and ensure no manual spacing overrides "
        "are in effect."
    ),
    ("P023", "multiline_body_heading_not_single_spaced"): (
        "Two lines of the same numbered body heading appear to use the page's "
        "double-spaced prose line pitch. Multi-line titles should be single-spaced "
        "within the title. Change the heading's line spacing; leave the spacing "
        "between the heading and body paragraph alone."
    ),
    ("P016", "excessive_line_gap"): (
        "This means unusually large spacing was detected between lines on this "
        "page. Body text should be double-spaced with consistent spacing. "
        "Review for extra blank lines or manual spacing overrides."
    ),
    ("P016", "excessive_paragraph_gap"): (
        "This means unusually large spacing was detected between paragraphs on "
        "this page. Paragraph spacing should be consistent with double-spaced "
        "body text. Review for extra blank lines or manual paragraph-spacing "
        "overrides."
    ),
    ("P016", "suspicious_heading_blank_gap"): (
        "This means an unusually large blank gap was detected just after a "
        "heading on this page. Verify this is intentional heading spacing and "
        "not an extra blank line or page-break artifact."
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
        "degree type. PhD abstracts must be 400 words or fewer; MS/Master abstracts "
        "must be 200 words or fewer. Shorten the abstract before submission."
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
        "A front-matter page appears to be numbered with an Arabic numeral "
        "instead of a Roman numeral. Use lowercase Roman numerals for "
        "numbered front-matter pages."
    ),
    ("P028", "uppercase_roman_on_frontmatter_page"): (
        "A front-matter page appears to be numbered with an uppercase Roman "
        "numeral. Use lowercase Roman numerals for numbered front-matter "
        "pages."
    ),
    ("P028", "roman_number_on_body_page"): (
        "A body page appears to be numbered with a Roman numeral instead of "
        "an Arabic numeral. Use Arabic numerals for body pages."
    ),
    ("P029", "roman_sequence_gap"): (
        "A front-matter page skips one or more Roman numerals in the sequence "
        "(for example, jumping from 'ii' to 'iv'). Each numbered front-matter page "
        "must use the next consecutive Roman numeral with no gaps. Renumber the "
        "affected page or restore any missing front-matter pages."
    ),
    ("P029", "roman_sequence_repeat"): (
        "A front-matter page repeats the same Roman numeral as the page before it. "
        "Each front-matter page must have its own, increasing Roman numeral. "
        "Verify no front-matter page was duplicated or mislabeled."
    ),
    ("P029", "roman_sequence_decrease"): (
        "A front-matter page's Roman numeral is lower than the page before it. "
        "Front-matter Roman numerals must increase by one on every numbered page. "
        "Verify no front-matter page was inserted, removed, or mislabeled out of order."
    ),
    ("P037", "roman_bio_sketch_not_iv"): (
        "The Biographical Sketch page is not numbered 'iv'. NJIT's front-matter "
        "template assigns the Biographical Sketch a fixed Roman numeral of 'iv', "
        "regardless of how other front-matter pages are numbered. "
        "Change this page's Roman numeral to 'iv'."
    ),
    ("P037", "roman_section_wrong_value"): (
        "A front-matter section does not continue the Roman sequence from "
        "Biographical Sketch page iv. Each numbered page, including a continuation "
        "page, advances the sequence by one. Correct this page's Roman numeral "
        "or the preceding front-matter sequence."
    ),
    ("P030", "missing_continued_heading"): (
        "A multi-page list (such as a List of Tables or List of Figures) may be "
        "missing a required continued heading on a continuation page. "
        "NJIT requires '(Continued)' in the heading when such lists span multiple pages."
    ),
    ("P033", "frontmatter_title_mismatch"): (
        "The dissertation title text differs between two or more front-matter "
        "pages — the Title Page, Abstract, and/or Approval Page — based on a "
        "normalized comparison, not an exact match. NJIT requires the title to be "
        "worded identically everywhere it appears in the front matter. Compare the "
        "title wording on the flagged pages and correct whichever one does not "
        "match the others."
    ),
    ("P034", "copyright_year_mismatch"): (
        "The copyright year on the copyright page may not match the expected format "
        "or year. Confirm the copyright block includes the correct year."
    ),
    ("P034", "copyright_top_margin_header_text"): (
        "This means text was detected in the top margin area of the copyright "
        "page, where NJIT expects no header text or running head."
    ),
    ("P034", "copyright_author_mismatch"): (
        "This means the author name on the copyright page does not appear to "
        "match the author name on the title page."
    ),
    ("P052", "copyright_author_not_found"): (
        "A copyright page was detected but the author name could not be verified. "
        "Confirm the copyright block includes the required author name."
    ),
    ("P051", "copyright_year_not_found"): (
        "A copyright page was detected, but the auditor could not confidently "
        "associate a four-digit copyright year with the copyright notice. Check "
        "the copyright page and confirm the year is present, clearly next to the "
        "copyright notice, and matches the year the degree is conferred."
    ),
    ("P038", "required_heading_missing"): (
        "This means a required front-matter section heading was not found "
        "anywhere in the document. NJIT requires APPROVAL PAGE, "
        "BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, and TABLE OF CONTENTS to "
        "all be present. Add the missing section with its exact heading."
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
        "This means the abstract appears to contain \"paper\" or \"article\" "
        "(or a plural form). Replace \"paper\" or \"article\" with "
        "\"dissertation,\" \"study,\" \"work,\" or \"research.\""
    ),
    ("P078", "abstract_pdf_first_person_pronoun"): (
        "This means the abstract appears to use a first-person pronoun such as "
        "\"I,\" \"me,\" \"my,\" \"we,\" or \"our.\" Rewrite the sentence to "
        "remove first-person pronouns."
    ),
    ("P084", "biosketch_birth_information_present"): (
        "This means the Biographical Sketch appears to contain place-of-birth "
        "or date-of-birth information. Remove place of birth and date of birth "
        "from the Biographical Sketch."
    ),
    ("P085", "missing_first_chapter_one_heading"): (
        "This means the first body page does not begin with the required "
        "CHAPTER 1 heading. Add the literal CHAPTER 1 heading at the beginning "
        "of the first body chapter."
    ),
    ("P086", "bold_heading_without_section_number"): (
        "This means a bold phrase reads like a section heading but has no "
        "section number in front of it. Bold styling is reserved for "
        "numbered heading levels 1-4; either add the section number or "
        "remove the bold styling from this phrase."
    ),
    ("P075", "toc_mixed_leader_styles"): (
        "The Table of Contents uses different leader styles, such as dots and "
        "hyphens, to connect entries to page numbers. Use one consistent "
        "leader style throughout the entire TOC."
    ),
    ("P075", "toc_missing_leader_style"): (
        "Some Table of Contents entries are missing a leader style before the "
        "page number while others use one. Add a consistent leader style "
        "between entry text and page numbers."
    ),
    ("P015", "unexpected_opening_indent"): (
        "This means the first paragraph after a section heading appears indented when "
        "NJIT expects it to begin flush with the left margin. Remove the first-line "
        "indent from that paragraph."
    ),
    ("P015", "missing_later_indent"): (
        "This means a later body paragraph appears to be missing its required "
        "first-line indent. Apply a first-line indent to that paragraph."
    ),
    ("P015", "unexpected_indent_on_continuation_line"): (
        "This means a continuation line after a displayed equation or similar "
        "break appears to use a paragraph-style first-line indent. Keep that "
        "continuation line flush with the left margin."
    ),
    ("P017", "unexpected_terminal_period"): (
        "This means a table title or List of Tables entry ends with a period "
        "that should be removed."
    ),
    ("P017", "missing_terminal_punctuation"): (
        "This means a figure or table caption is missing terminal punctuation. "
        "Add a period, question mark, or exclamation point as appropriate."
    ),
    ("P017", "possible_sentence_case_issue"): (
        "This means a caption appears to use Title Case where sentence case may "
        "be expected. Review caption capitalization against NJIT guidance."
    ),
    ("P017", "possible_title_case_issue"): (
        "This means a table title may violate NJIT title-case expectations. "
        "Capitalize the first word and major words; leave prepositions, conjunctions, "
        "and articles lowercase where appropriate."
    ),
    ("P018", "misaligned_page_number_column"): (
        "This means a TOC or list entry page-number column does not align with "
        "the dominant column on this list page."
    ),
    ("P018", "missing_page_number"): (
        "This means a TOC or list entry appears to be missing its trailing page "
        "number. Add the correct page number."
    ),
    ("P018", "inconsistent_leader_dots"): (
        "This means leader dots or spacing before page numbers are inconsistent "
        "with the dominant style on this list page."
    ),
    ("P018", "inconsistent_hierarchy_indent"): (
        "This means entry indentation does not match the expected hierarchy "
        "level for this TOC or list page."
    ),
    ("P018", "wrapped_title_continuation_misaligned"): (
        "This means a continuation line of a wrapped Table of Contents title "
        "starts left of the first word of the title text. " + P018_WRAPPED_TITLE_FIX
    ),
    ("P018", "title_to_leader_gap_too_wide"): (
        "This means the leader dots in a Table of Contents, List of Tables, or "
        "List of Figures entry do not start right after the title. Leader dots "
        "should begin right after the last letter of the title, with at most one "
        "space before the first dot."
    ),
    ("P018", "leader_dots_before_final_title_line"): (
        "This means the leader dots of an entry whose title runs onto more than "
        "one line appear on an earlier line. For a wrapped title, the leader dots "
        "should start after the final line of the title."
    ),
    ("P024", "toc_level_capitalization"): (
        "This means a Table of Contents entry may not follow NJIT capitalization "
        "rules for its heading level: Level 1 uses ALL CAPS, Level 2 uses Title "
        "Case, and Level 3 uses sentence case."
    ),
    ("P024", "list_of_tables_title_case"): (
        "This means a List of Tables entry may not use Title Case or may include "
        "terminal punctuation."
    ),
    ("P024", "list_of_figures_title_case"): (
        "This means a figure description in the List of Figures may not use sentence case."
    ),
    ("P024", "unexpected_terminal_punctuation"): (
        "This means a TOC or list entry ends with terminal punctuation where "
        "NJIT expects none for that list type."
    ),
    ("P074", "title_page_graduation_month_invalid"): (
        "This means the graduation month detected on the Title Page is not "
        "August, December, or May. Change the graduation month on the Title Page "
        "to August, December, or May."
    ),
    ("P035", "table_caption_not_above_body"): (
        "This means a table title does not appear above the table body. "
        "NJIT expects table titles above the table."
    ),
    ("P035", "figure_caption_not_below_body"): (
        "This means a figure description does not appear below the figure body. "
        "NJIT expects figure descriptions below the figure."
    ),
    ("P035", "table_body_not_centered"): (
        "This means a table body block does not appear centered within the "
        "area between the page margins."
    ),
    ("P035", "figure_body_not_centered"): (
        "This means a figure body block does not appear centered within the "
        "area between the page margins."
    ),
    ("P039", "toc_l2_not_indented_relative_to_l1"): (
        "This means a level-2 Table of Contents entry does not appear indented "
        "to show hierarchy relative to level-1 entries."
    ),
    ("P039", "toc_l3_not_indented_relative_to_l2"): (
        "This means a level-3 Table of Contents entry does not appear indented "
        "to show hierarchy relative to level-2 entries."
    ),
    ("P040", "lof_entry_missing_terminal_punctuation"): (
        "This means a figure description in the List of Figures is missing "
        "terminal punctuation. Add terminal punctuation, such as a period, question "
        "mark, or exclamation point, to every figure description."
    ),
    ("P041", "dedication_top_margin_header_text"): (
        "This means header text appears to be present in the top margin area of "
        "the Dedication page. Remove any running header or header text from the "
        "top margin area of the Dedication page."
    ),
    ("P043", "acknowledgements_first_paragraph_indented"): (
        "This means the first paragraph on the Acknowledgements page appears "
        "indented. Remove any first-line indent from the first "
        "Acknowledgements paragraph."
    ),
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): (
        "This means a later Acknowledgements paragraph appears flush-left "
        "where NJIT expects a first-line indent. Apply a first-line indent "
        "to each subsequent Acknowledgements paragraph."
    ),
    ("P044", "abstract_first_paragraph_indented"): (
        "This means the first paragraph on the Abstract page appears indented. "
        "Remove any first-line indent from the first Abstract paragraph."
    ),
    ("P044", "abstract_subsequent_paragraph_not_indented"): (
        "This means an Abstract paragraph after the first appears flush-left "
        "where NJIT expects a first-line indent. Apply a first-line indent "
        "to each subsequent Abstract paragraph."
    ),
    ("P053", "lot_entry_has_terminal_period"): (
        "This means a List of Tables entry ends with a final period. Remove the "
        "final period from each List of Tables entry. Table titles should use "
        "title case without terminal punctuation."
    ),
    ("P054", "toc_entry_has_terminal_period"): (
        "This means a Table of Contents entry ends with a final period. Remove "
        "the final period from each Table of Contents entry."
    ),
    ("P055", "lot_entry_is_figure"): (
        "This means a table entry appears in the List of Tables but describes a "
        "figure. Move this entry to the List of Figures."
    ),
    ("P055", "lof_entry_is_table"): (
        "This means a figure entry appears in the List of Figures but describes "
        "a table. Move this entry to the List of Tables."
    ),
    ("P055", "lot_entry_missing_table_prefix"): (
        "The auditor found a numbered entry but could not match it to a 'Table' column "
        "heading. Entries under that heading may begin with just their number."
    ),
    ("P055", "lof_entry_missing_figure_prefix"): (
        "List of Figures entries may begin with a number; the word Figure is not required "
        "before each entry. Review body references separately."
    ),
    ("P055", "body_figure_reference_abbreviated"): (
        "Use the full word 'Figure' before the number in this body reference."
    ),
    ("P058", "toc_page_numbers_not_nondecreasing"): (
        "This means Table of Contents page numbers do not appear in ascending "
        "order on this page."
    ),
    ("P060", "toc_subsection_number_ambiguous"): (
        "The number may be missing a dot: its preceding subsection and indentation "
        "suggest a deeper heading. Confirm the number and level before changing case."
    ),
    ("P060", "toc_entry_numbers_not_nondecreasing"): (
        "This means Table of Contents section numbers do not appear in "
        "non-decreasing order on this page."
    ),
    ("P087", "toc_abstract_entry_present"): (
        "This means a Table of Contents entry is titled Abstract. The dissertation "
        "Abstract belongs only in the front matter, not in the TOC."
    ),
    ("P087", "toc_generic_title_repeated"): (
        "This means the same generic section title appears more than once in the "
        "Table of Contents. Qualify each repeated heading so readers can tell the "
        "sections apart."
    ),
    ("P088", "figure_number_malformed"): (
        "This means a body figure caption number has extra concatenated segments "
        "beyond the usual chapter.sequence form."
    ),
    ("P088", "figure_number_duplicate"): (
        "This means the same figure number appears more than once in one chapter."
    ),
    ("P088", "figure_number_out_of_order"): (
        "This means body figure numbers in a chapter do not increase in reading "
        "order."
    ),
    ("P057", "lot_page_numbers_not_nondecreasing"): (
        "This means List of Tables page numbers do not appear in "
        "non-decreasing order down this page."
    ),
    ("P057", "lof_page_numbers_not_nondecreasing"): (
        "This means List of Figures page numbers do not appear in "
        "non-decreasing order down this page."
    ),
    ("P059", "lot_entry_numbers_not_nondecreasing"): (
        "This means List of Tables entry numbers do not appear in "
        "non-decreasing order down this page."
    ),
    ("P059", "lof_entry_numbers_not_nondecreasing"): (
        "This means List of Figures entry numbers do not appear in "
        "non-decreasing order down this page."
    ),
    ("P061", "lot_cross_page_entry_numbers_not_nondecreasing"): (
        "This means List of Tables entry numbers do not appear in "
        "non-decreasing order across this multi-page run."
    ),
    ("P061", "lof_cross_page_entry_numbers_not_nondecreasing"): (
        "This means List of Figures entry numbers do not appear in "
        "non-decreasing order across this multi-page run."
    ),
    ("P062", "toc_cross_page_entry_numbers_not_nondecreasing"): (
        "This means Table of Contents section numbers do not appear in "
        "non-decreasing order across this multi-page run."
    ),
    ("P064", "references_section_heading_not_detected"): (
        "This means no recognized REFERENCES or BIBLIOGRAPHY section heading "
        "was detected."
    ),
    ("P064", "references_entry_indentation_inconsistent"): (
        "This means reference entries appear to use inconsistent indentation "
        "styles."
    ),
    ("P064", "references_entry_spacing_inconsistent"): (
        "This means spacing between reference entries appears inconsistent."
    ),
    ("P064", "references_entry_not_single_spaced"): (
        "Measured gaps between lines within reference entries are consistent "
        "with double spacing. Reviewer guidance specifies single spacing "
        "within each reference."
    ),
    ("P064", "references_inter_entry_spacing_too_tight"): (
        "Measured gaps between consecutive reference entries are close to the "
        "single-line pitch measured within those entries. Reviewer guidance "
        "specifies double spacing between references."
    ),
    ("P068", "approval_page_advisor_role_label_missing"): (
        "This means the Approval Page may be missing a recognizable advisor or "
        "committee role label such as 'Dissertation Advisor' or 'Major Professor'. "
        "Add the required advisor or committee role label for each committee entry "
        "on the Approval Page."
    ),
    ("P068", "approval_page_signature_blocks_sparse"): (
        "This means the Approval Page appears to have too few signature/date "
        "structural blocks for the committee entries present. Add the required "
        "signature/date structural block for each committee entry on the Approval "
        "Page."
    ),
    ("P036", "toc_inter_entry_spacing_too_tight"): (
        "This means consecutive Table of Contents entries do not appear to have "
        "visible double spacing or a blank line between them. Add visible double "
        "spacing or a blank line between consecutive TOC entries."
    ),
    ("P036", "lot_inter_entry_spacing_too_tight"): (
        "This means consecutive List of Tables entries do not appear to have "
        "visible double spacing or a blank line between them. Add visible double "
        "spacing or a blank line between consecutive List of Tables entries."
    ),
    ("P036", "lof_inter_entry_spacing_too_tight"): (
        "This means consecutive List of Figures entries do not appear to have "
        "visible double spacing or a blank line between them. Add visible double "
        "spacing or a blank line between consecutive List of Figures entries."
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
    "detected_page_number_candidate": (
        "The checker detected a normal-looking page-number candidate in the "
        "expected bottom area. This is inventory-only verification data and is "
        "not counted as a formatting problem unless another finding reports a "
        "specific defect such as missing, misplaced, duplicate, wrong-style, "
        "or wrong-sequence numbering."
    ),
    "wrong_page_number_location": (
        "This means the detected page number appears outside the required bottom "
        "position. Review the page and move the page number to the required "
        "bottom location."
    ),
    "wrong_page_numbering_style": (
        "This means the detected page number does not appear to use the numbering "
        "style expected for that section. Front matter should use lowercase Roman "
        "numerals and body pages should use Arabic numerals."
    ),
    "wrong_page_number_sequence": (
        "This means the page number printed on this page does not match what NJIT's "
        "front-matter numbering rules expect at this position -- for example, it may "
        "repeat, skip, or go backward relative to nearby pages, or it may not match a "
        "section that has a fixed, required numeral. Compare this page's number with "
        "the pages immediately before and after it, and correct the numbering so it "
        "follows the required sequence."
    ),
    "duplicate_or_ambiguous_page_number": (
        "This means multiple page-number-like tokens were detected on the same "
        "page. Verify which token is the real page number and remove or correct "
        "duplicates or misleading footer/header text."
    ),
    "page_number_should_be_suppressed": (
        "This means a page number appears on a page type that may need to hide "
        "or suppress numbering. Remove the page number unless this page type is "
        "intentionally numbered."
    ),
    "possible_body_text_not_double_spaced": (
        "Body text on this page does not appear to use the required double line "
        "spacing. NJIT requires double line spacing throughout the body text."
    ),
    "excessive_line_gap": (
        "Unusually large spacing was detected between lines on this page. Body "
        "text should be double-spaced with consistent spacing."
    ),
    "excessive_paragraph_gap": (
        "Unusually large spacing was detected between paragraphs on this page. "
        "Paragraph spacing should be consistent with double-spaced body text."
    ),
    "suspicious_heading_blank_gap": (
        "An unusually large blank gap was detected just after a heading on "
        "this page. Verify this is intentional heading spacing."
    ),
    "frontmatter_page_number_style_issue": (
        "The page number style on this front-matter page does not match NJIT "
        "requirements. Front-matter pages must use lowercase Roman numerals (i, ii, iii). "
        "Body pages must use Arabic numerals (1, 2, 3)."
    ),
    "abstract_word_count_exceeded": (
        "The abstract appears to exceed the allowed word count. "
        "PhD abstracts must be 400 words or fewer; MS/Master abstracts "
        "must be 200 words or fewer."
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


_P014_ATTRIBUTE_LABELS: tuple[tuple[str, str], ...] = (
    ("centered", "centered"),
    ("near_top", "near the top of the page"),
    ("bold", "bold"),
    ("all_caps", "in all capital letters"),
)


def _p014_issue_type_explanation(details: Mapping[str, str]) -> str:
    """Name which P014 layout attribute(s) failed, using detector-recorded booleans."""
    failed_labels = [
        label
        for key, label in _P014_ATTRIBUTE_LABELS
        if details.get(key, "").strip().lower() == "false"
    ]
    if failed_labels:
        observed = "this heading is " + ", ".join(f"not {label}" for label in failed_labels)
    else:
        observed = "this heading does not match NJIT's expected layout/style"
    return (
        f"This means {observed}. NJIT requires named front-matter headings (such as "
        "ABSTRACT or APPROVAL PAGE) to be centered near the top of the page, in bold, "
        "and in all capital letters. Review the heading's formatting and correct any "
        "attributes that do not match."
    )


def _p016_issue_type_explanation(issue_type: str, details: Mapping[str, str]) -> str:
    gap = details.get("largest_gap_pt", "").strip()
    gap_clause = f" (about {gap}pt)" if gap else ""
    if issue_type == "excessive_line_gap":
        return (
            f"This means unusually large spacing{gap_clause} was detected between lines "
            "on this page. Body text should be double-spaced with consistent spacing. "
            "Review for extra blank lines or manual spacing overrides."
        )
    if issue_type == "excessive_paragraph_gap":
        return (
            f"This means unusually large spacing{gap_clause} was detected between "
            "paragraphs on this page. Paragraph spacing should be consistent with "
            "double-spaced body text. Review for extra blank lines or manual "
            "paragraph-spacing overrides."
        )
    return (
        f"This means an unusually large blank gap{gap_clause} was detected just after "
        "a heading on this page. Verify this is intentional heading spacing and not an "
        "extra blank line or page-break artifact."
    )


def _p068_issue_type_explanation(issue_type: str, details: Mapping[str, str]) -> str:
    role_label_count = details.get("role_label_count", "").strip() or "0"
    indicator_count = details.get("signature_date_indicator_count", "").strip() or "0"
    try:
        required = str(max(2, int(role_label_count)))
    except ValueError:
        required = "2"
    if issue_type == "approval_page_advisor_role_label_missing":
        return (
            f"This means the Approval Page lists {role_label_count} committee role "
            "label(s), but none of them is a recognizable advisor role label (for "
            "example, 'Dissertation Advisor' or 'Major Professor'). Add the required "
            "advisor or committee role label for each committee entry on the "
            "Approval Page."
        )
    return (
        f"This means the Approval Page has {indicator_count} signature/date line(s) "
        f"for {role_label_count} committee role label(s), but at least {required} are "
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


def _p032_issue_type_explanation(details: Mapping[str, str]) -> str:
    entry_label = _P032_ENTRY_KIND_LABELS.get(details.get("entry_kind", ""), "list entry")
    observed_gap = details.get("observed_gap_pt", "").strip()
    expected_gap = details.get("expected_max_gap_pt", "").strip()
    gap_clause = (
        f" (about {observed_gap}pt observed vs. an expected maximum of about "
        f"{expected_gap}pt)"
        if observed_gap and expected_gap
        else ""
    )
    return (
        f"This means a wrapped {entry_label} does not appear to be single-spaced "
        f"within the same entry{gap_clause}. Single-space wrapped entries so "
        "continuation lines stay within the same entry without extra blank space."
    )


def _p056_format_counts(details: Mapping[str, str]) -> tuple[str, str]:
    """Parse P056's 'chapter_based:N,sequential:M' details string into (N, M)."""
    counts: dict[str, str] = {}
    for part in details.get("format_counts", "").split(","):
        key, _, value = part.partition(":")
        if key.strip():
            counts[key.strip()] = value.strip()
    return counts.get("chapter_based", "0"), counts.get("sequential", "0")


def _p056_issue_type_explanation(issue_type: str, details: Mapping[str, str]) -> str:
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
        f"This means the {section_label} contains a mix of {chapter_count} chapter-"
        f"based (e.g., {noun} 1.2) and {sequential_count} sequential (e.g., {noun} 3) "
        f"entry-numbering formats.{dominant_clause} NJIT expects one consistent "
        "numbering format throughout. Pick one format and apply it to every entry in "
        "this list."
    )


def _p066_issue_type_explanation(details: Mapping[str, str]) -> str:
    first_year = details.get("first_candidate_year", "").strip() or "an earlier year"
    last_year = details.get("last_candidate_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        "This means the postgraduate degree entries on the Biographical Sketch page "
        "appear to be out of order: the candidate years found (in listed order) run "
        f"from {first_year} to {last_year}, with {inversion_count} {place_noun} where "
        "a later-listed entry's year is more recent than the entry just before it. "
        "Reorder postgraduate degree entries in the Biographical Sketch from most "
        "recent to oldest."
    )


def _p067_issue_type_explanation(details: Mapping[str, str]) -> str:
    first_year = details.get("first_entry_year", "").strip() or "an earlier year"
    last_year = details.get("last_entry_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        "This means the publication and presentation entries on the Biographical "
        "Sketch page appear to be out of order: the comparable entry years found "
        f"(in listed order) run from {first_year} to {last_year}, with "
        f"{inversion_count} {place_noun} where a later-listed entry's year is more "
        "recent than the entry just before it. Reorder publication and presentation "
        "entries in the Biographical Sketch from most recent to oldest."
    )


def _p045_hanging_indent_issue_type_explanation(details: Mapping[str, str]) -> str:
    # Legacy issue type (no longer emitted); see polished_comments.
    return (
        "This means publication/presentation entries on the Biographical Sketch page "
        "do not appear to use a hanging indent. A hanging indent is optional, so no "
        "change is required for this."
    )


def _p045_line_spacing_issue_type_explanation(details: Mapping[str, str]) -> str:
    pitch = details.get("observed_line_pitch_points", "").strip()
    font_size = details.get("font_size_points", "").strip()
    gap_clause = (
        f" (wrapped lines about {pitch}pt apart for {font_size}pt text)"
        if pitch and font_size
        else ""
    )
    return (
        "This means wrapped lines within a publication/presentation entry on the "
        f"Biographical Sketch page do not appear to be single-spaced{gap_clause}. "
        "Single-space the lines within each entry."
    )


def _p045_numbered_entry_issue_type_explanation(details: Mapping[str, str]) -> str:
    return (
        "This means publication/presentation entries on the Biographical Sketch "
        "page start with a number or label such as [1] or 1. They are not "
        "references and must not be numbered; keep the References citation "
        "format without the number in front."
    )


def _p045_entry_spacing_issue_type_explanation(details: Mapping[str, str]) -> str:
    observed = details.get("observed_gap_points", "").strip()
    required = details.get("required_gap_points", "").strip()
    gap_clause = (
        f" (about {observed}pt observed vs. a required minimum of about {required}pt)"
        if observed and required
        else ""
    )
    return (
        "This means two consecutive publication/presentation entries on the "
        "Biographical Sketch page do not appear to have a blank line between "
        f"them{gap_clause}. Add a blank line between separate entries."
    )


def _p047_block_label(details: Mapping[str, str]) -> str:
    raw = details.get("block_index", "").strip()
    try:
        return f"bullet block {int(raw) + 1}"
    except ValueError:
        return "a bullet/list block"


def _p047_issue_type_explanation(details: Mapping[str, str]) -> str:
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
        f"This means {block_label} on the Biographical Sketch page appears to have "
        f"extra spacing inside the bullet item{gap_clause}. Single-space each bullet "
        "item in the Biographical Sketch education section, with no extra blank "
        "lines inside the same bullet item."
    )


_LOT_LOF_SECTION_LABELS: dict[str, str] = {
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}
_LOT_LOF_ENTRY_NOUNS: dict[str, str] = {
    "list_of_tables": "table",
    "list_of_figures": "figure",
}


def _lot_lof_section_label(details: Mapping[str, str]) -> str:
    section = details.get("section_type", "").strip()
    return _LOT_LOF_SECTION_LABELS.get(section, "List of Tables/List of Figures")


def _lot_lof_entry_noun(details: Mapping[str, str]) -> str:
    section = details.get("section_type", "").strip()
    return _LOT_LOF_ENTRY_NOUNS.get(section, "entry")


def _format_points(value: str) -> str:
    cleaned = value.strip()
    return f"{cleaned}pt" if cleaned else ""


def _font_metadata_clause(details: Mapping[str, str]) -> str:
    available = details.get("font_metadata_available", "").strip().lower()
    if available and available != "true":
        return (
            " Reliable style information could not be detected for this header, so "
            "please verify its boldness visually."
        )
    return ""


def _p031_issue_type_explanation(issue_type: str, details: Mapping[str, str]) -> str:
    section_label = _lot_lof_section_label(details)
    expected_left = details.get("expected_left_label", "").strip() or "Table/Figure"
    expected_page = details.get("expected_page_label", "").strip() or "Page"

    if issue_type == "missing_left_column_header":
        return (
            f"This means the {section_label} page does not show the required "
            f"'{expected_left}' column header. Add the required column headers "
            "directly below the list heading: "
            f"'{expected_left}' on the left and 'Page' on the right."
        )
    if issue_type == "missing_page_column_header":
        return (
            f"This means the {section_label} page does not show the required "
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
            f"This means the '{expected_left}' column header on the {section_label} "
            f"page appears far from the entry column it labels{gap_clause}. Align "
            f"the '{expected_left}' header with the entry numbers below it."
        )
    expected = _format_points(details.get("expected_page_x_pt", ""))
    gap_clause = (
        f" (about {observed} observed vs. an expected position of about {expected})"
        if observed and expected
        else ""
    )
    return (
        f"This means the '{expected_page}' column header on the {section_label} "
        f"page appears far from the page-number column it labels{gap_clause}. "
        f"Align the '{expected_page}' header with the page numbers below it."
    )


def _p046_issue_type_explanation(details: Mapping[str, str]) -> str:
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
        f"This means {section_label} entry numbers do not appear to be aligned "
        f"vertically in one left column{range_clause}. Align all {entry_noun} "
        f"numbers in the {section_label} into one consistent left column."
    )


def _p048_issue_type_explanation(details: Mapping[str, str]) -> str:
    section_label = _lot_lof_section_label(details)
    observed = _format_points(details.get("observed_page_number_x", ""))
    expected = _format_points(details.get("expected_page_number_x", ""))
    measure_clause = (
        f" (about {observed} observed vs. an expected position of about {expected})"
        if observed and expected
        else ""
    )
    return (
        f"This means page numbers in the {section_label} do not appear to be "
        f"aligned vertically in one right column{measure_clause}. Align all page "
        f"numbers in the {section_label} into one consistent right column."
    )


def _p049_issue_type_explanation(issue_type: str, details: Mapping[str, str]) -> str:
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
            f"This means the 'Page' column header on the {section_label} page "
            f"does not appear to be right-aligned over the page-number column"
            f"{measure_clause}. Format the 'Page' column header in bold and align "
            "it over the page-number column on the right."
        )
    verify_clause = _font_metadata_clause(details)
    return (
        f"This means the 'Page' column header on the {section_label} page is not "
        f"formatted in bold.{verify_clause} Format the 'Page' column header in "
        "bold and align it over the page-number column on the right."
    )


def _p050_issue_type_explanation(details: Mapping[str, str]) -> str:
    section_label = _lot_lof_section_label(details)
    header_word = "Table" if _lot_lof_entry_noun(details) == "table" else "Figure"
    verify_clause = _font_metadata_clause(details)
    return (
        f"This means the '{header_word}' column header on the {section_label} page "
        f"is not formatted in bold.{verify_clause} Format the '{header_word}' "
        "column header in bold."
    )


def _p042_entry_position_clause(details: Mapping[str, str]) -> str:
    entry_index = details.get("entry_index", "").strip()
    entry_count = details.get("appendix_entry_count", "").strip()
    if entry_index.isdigit() and entry_count.isdigit():
        position = int(entry_index) + 1
        return f" (entry {position} of {entry_count} appendix entries listed)"
    return ""


def _p042_issue_type_explanation(issue_type: str, details: Mapping[str, str]) -> str:
    if issue_type == "single_appendix_missing_title":
        expected_pattern = details.get("expected_pattern", "").strip() or "APPENDIX <title>"
        return (
            "This means the Table of Contents lists a single appendix entry "
            "that does not appear to include a title after 'APPENDIX'. For one "
            "appendix, begin the TOC entry with \"APPENDIX\" followed by the "
            f"title (pattern '{expected_pattern}'). Add the missing appendix "
            "title to this Table of Contents entry."
        )
    expected_pattern = details.get("expected_pattern", "").strip() or "APPENDIX <A-Z>"
    position_clause = _p042_entry_position_clause(details)
    return (
        "This means the Table of Contents lists multiple appendix entries, "
        f"but one entry{position_clause} does not appear to include a letter "
        "identifier. For multiple appendices, label each TOC entry with a "
        f"letter, such as \"APPENDIX A,\" \"APPENDIX B,\" and so on (pattern "
        f"'{expected_pattern}'). Add the missing letter to this Table of "
        "Contents entry."
    )


def explain_issue_type(
    rule_id: str, issue_type: str, details: Mapping[str, str] | None = None
) -> str:
    """Return a student-facing explanation for a (rule_id, issue_type) pair.

    Never reproduces dissertation body text. Falls back gracefully for
    unknown issue types. When *details* is supplied, P014/P016/P068 use
    detector-recorded metadata (layout attributes, gap size, label/signature
    counts) to make the explanation specific instead of generic.
    """
    safe_details = details or {}
    if rule_id == "P017" and issue_type == "missing_terminal_punctuation":
        continuation = caption_continuation_explanation(safe_details)
        if continuation:
            return continuation
    if rule_id == "P014":
        return _p014_issue_type_explanation(safe_details)
    if rule_id == "P016" and issue_type in {
        "excessive_line_gap",
        "excessive_paragraph_gap",
        "suspicious_heading_blank_gap",
    }:
        return _p016_issue_type_explanation(issue_type, safe_details)
    if rule_id == "P068" and issue_type in {
        "approval_page_advisor_role_label_missing",
        "approval_page_signature_blocks_sparse",
    }:
        return _p068_issue_type_explanation(issue_type, safe_details)
    if rule_id == "P032" and issue_type == "wrapped_entry_internal_spacing":
        return _p032_issue_type_explanation(safe_details)
    if rule_id == "P056" and issue_type in {
        "lot_mixed_numbering_format",
        "lof_mixed_numbering_format",
    }:
        return _p056_issue_type_explanation(issue_type, safe_details)
    if rule_id == "P066" and issue_type == "biosketch_degree_order_suspicious":
        return _p066_issue_type_explanation(safe_details)
    if rule_id == "P067" and issue_type == "biosketch_publication_order_suspicious":
        return _p067_issue_type_explanation(safe_details)
    if rule_id == "P045" and issue_type == "biosketch_publication_entry_numbered":
        return _p045_numbered_entry_issue_type_explanation(safe_details)
    if rule_id == "P045" and issue_type == "biosketch_publication_missing_hanging_indent":
        return _p045_hanging_indent_issue_type_explanation(safe_details)
    if rule_id == "P045" and issue_type == "biosketch_publication_wrapped_line_spacing_not_single":
        return _p045_line_spacing_issue_type_explanation(safe_details)
    if rule_id == "P045" and issue_type == "biosketch_publication_entry_spacing_not_double":
        return _p045_entry_spacing_issue_type_explanation(safe_details)
    if rule_id == "P047" and issue_type == "biosketch_bullet_section_not_single_spaced":
        return _p047_issue_type_explanation(safe_details)
    if rule_id == "P031" and issue_type in {
        "missing_left_column_header",
        "missing_page_column_header",
        "left_column_header_misaligned",
        "page_column_header_misaligned",
    }:
        return _p031_issue_type_explanation(issue_type, safe_details)
    if rule_id == "P046" and issue_type in {
        "lot_entry_number_column_misaligned",
        "lof_entry_number_column_misaligned",
    }:
        return _p046_issue_type_explanation(safe_details)
    if rule_id == "P048" and issue_type in {
        "lot_page_number_column_misaligned",
        "lof_page_number_column_misaligned",
    }:
        return _p048_issue_type_explanation(safe_details)
    if rule_id == "P049" and issue_type in {
        "lot_page_header_not_right_aligned",
        "lof_page_header_not_right_aligned",
        "lot_page_header_not_bold",
        "lof_page_header_not_bold",
    }:
        return _p049_issue_type_explanation(issue_type, safe_details)
    if rule_id == "P050" and issue_type in {
        "lot_table_header_not_bold",
        "lof_figure_header_not_bold",
    }:
        return _p050_issue_type_explanation(safe_details)
    if rule_id == "P042" and issue_type in {
        "single_appendix_missing_title",
        "multiple_appendix_missing_letter",
    }:
        return _p042_issue_type_explanation(issue_type, safe_details)
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
