"""Privacy-safe polished comment templates for GUI finding display."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from njit_auditor.caption_continuation_preview import caption_continuation_explanation
from njit_auditor.ester_warning_wording import student_warning_remediation
from njit_auditor.float_layout_advice import float_layout_suggested_fix
from njit_auditor.issue_type_explanations import humanize_issue_type
from njit_auditor.p018_guidance import P018_WRAPPED_TITLE_FIX
from njit_auditor.report_outputs import derive_source_issue_type
from njit_auditor.resource_paths import resource_path
from njit_auditor.toc_order_evidence import P062_ISSUE, describe_p062_pair

REVIEW_PREFIX = "Review needed:"
VERIFY_SUFFIX = "Automated finding — please verify against NJIT guidelines manually."
GLOBAL_AUTOMATED_REVIEW_NOTE = (
    "Automated findings require manual verification against NJIT guidelines."
)

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
        "line_preview",
        "previous_entry_preview",
        "next_entry_preview",
        "affected_entry_preview",
        "body_text",
        "extracted_text",
        "annotation_text",
        "comment_text",
        "content",
        "label",
        "ref",
    }
)

_SOURCE_RULE_IDS = frozenset(
    {"P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"}
)

# P037 anchors Biographical Sketch at iv; later front-matter pages continue
# the Roman sequence, including List of Tables after the TOC (Q060).
_P037_SECTION_KEY_LABELS: dict[str, str] = {
    "biographical_sketch": "Biographical Sketch",
    "dedication": "Dedication",
    "acknowledgements": "Acknowledgements",
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
}

_ISSUE_TEMPLATES: dict[tuple[str, str], str] = {
    ("P011", "margin_boundary_violation"): (
        "Text on page {page} is not contained entirely within the required {side}. "
        "NJIT requires: left margin 1.5 inches; top, bottom, and right margins 1 inch. "
        "Move any text, table, or figure that extends into the margins back inside "
        "the required page area."
    ),
    ("P013", "p013_document_overview"): (
        "Document-level page-number pattern summary detected (informational; "
        "not a page-specific defect). Review the individual page-number "
        "findings below for anything that needs manual verification."
    ),
    ("P019", "missing_page_number"): (
        "Problem: The auditor did not find a clear page number on page {page}. "
        "NJIT requires page numbers on this type of page unless numbering is "
        "intentionally suppressed for that page type. Add the required page "
        "number unless this page type should suppress numbering."
    ),
    ("P019", "multiple_page_numbers"): (
        "Problem: Multiple page-number-like tokens were detected on page {page}. "
        "This may indicate duplicate page numbering or footer/header text "
        "being mistaken for a page number. Verify which token is the actual "
        "page number and remove or correct duplicates."
    ),
    ("P019", "inconsistent_position"): (
        "Problem: The page number on page {page} appears at {observed_location}, "
        "but NJIT expects the page number in the required bottom position. "
        "Move the page number to the required bottom position."
    ),
    ("P019", "mixed_numbering_style"): (
        "Problem: The page number on page {page} appears to use {observed_style}, "
        "but this section is expected to use {expected_style}. Update the "
        "page-numbering style for this section."
    ),
    ("P019", "sequence_gap"): (
        "Problem: The detected page number on page {page} does not appear to "
        "follow the expected numbering sequence. Observed: {observed_sequence}. "
        "Expected: {expected_sequence}. Renumber the affected pages so the "
        "sequence is correct."
    ),
    ("P022", "visible_page_number_on_no_number_page"): (
        "Problem: A page number appears on page {page}, but this {page_type} "
        "page may require the page number to be suppressed or hidden. Remove "
        "the page number unless this page type is intentionally numbered."
    ),
    ("P028", "arabic_number_on_frontmatter_page"): (
        "Problem: The page number on page {page} appears to use {observed_style}, "
        "but this section is expected to use {expected_style}. Use lowercase "
        "Roman numerals for numbered front-matter pages."
    ),
    ("P028", "uppercase_roman_on_frontmatter_page"): (
        "Problem: The page number on page {page} appears to use {observed_style}, "
        "but this section is expected to use {expected_style}. Use lowercase "
        "Roman numerals for numbered front-matter pages."
    ),
    ("P028", "roman_number_on_body_page"): (
        "Problem: The page number on page {page} appears to use {observed_style}, "
        "but this section is expected to use {expected_style}. Use Arabic "
        "numerals for body pages."
    ),
    ("P029", "roman_sequence_gap"): (
        "Problem: Page {page} is numbered '{observed_sequence}', but the previous "
        "numbered front-matter page was followed by '{expected_sequence}' as the "
        "next expected Roman numeral — one or more numerals were skipped. NJIT "
        "expects every front-matter Roman numeral to increase by exactly one with "
        "no gaps. Change this page to '{expected_sequence}' or renumber the "
        "skipped pages so the sequence is consecutive."
    ),
    ("P029", "roman_sequence_repeat"): (
        "Problem: Page {page} repeats the Roman numeral '{observed_sequence}', the "
        "same value already used on the previous front-matter page. NJIT expects "
        "each front-matter page to have its own, increasing Roman numeral "
        "(expected next: '{expected_sequence}'). Renumber this page so it "
        "continues the sequence instead of repeating the previous page's number."
    ),
    ("P029", "roman_sequence_decrease"): (
        "Problem: The Roman numeral on page {page} is '{observed_sequence}', "
        "which is lower than the numeral used on the previous front-matter page. "
        "NJIT expects front-matter Roman numerals to increase by one on every "
        "numbered page (expected: '{expected_sequence}'). Renumber this page so "
        "the sequence keeps increasing instead of going backward."
    ),
    ("P037", "roman_bio_sketch_not_iv"): (
        "Problem: The Biographical Sketch page is numbered '{observed_sequence}', "
        "but NJIT's front-matter template always assigns the Biographical Sketch "
        "page the fixed Roman numeral '{expected_sequence}', regardless of what "
        "comes before it. Change this page's Roman numeral to '{expected_sequence}'."
    ),
    ("P037", "roman_section_wrong_value"): (
        "Problem: The {section_label} page is numbered '{observed_sequence}', but "
        "the Roman sequence continuing from Biographical Sketch page iv calls "
        "for '{expected_sequence}' after the preceding front-matter page. "
        "Continuation pages count in this sequence. Change this page's Roman "
        "numeral to '{expected_sequence}' or correct the preceding sequence."
    ),
    ("P026", "possible_body_font_family_issue"): (
        "Body text on page {page} may use a font family outside the accepted NJIT options."
    ),
    ("P026", "possible_body_font_size_issue"): (
        "Body text on page {page} may not use the expected font size. "
        "Compare body text size against NJIT requirements."
    ),
    ("P030", "missing_continued_heading"): (
        "A continuation page of a multi-page Table of Contents, List of Tables, or "
        "List of Figures on page {page} does not include the correct continued "
        "heading. Add the correct continued heading on this continuation page."
    ),
    ("P030", "missing_symbols_continued_heading"): (
        "The List of Symbols continues on page {page}. "
        "Add LIST OF SYMBOLS (Continued) above the entries."
    ),
    ("P034", "copyright_year_mismatch"): (
        "Copyright page year format on page {page} may need review. "
        "Confirm the copyright block includes the required year format."
    ),
    ("P034", "copyright_top_margin_header_text"): (
        "Text was detected in the top margin area of the copyright page "
        "(page {page}). NJIT requires the copyright page to have no header "
        "text or running head in the top margin. Remove or reposition this "
        "text outside the top margin."
    ),
    ("P034", "copyright_author_mismatch"): (
        "The author name on the copyright page (page {page}) does not appear "
        "to match the author name on the title page. NJIT requires the same "
        "author name to appear consistently on both pages. Verify the "
        "copyright page shows the exact same author name used on the title "
        "page."
    ),
    ("P052", "copyright_author_not_found"): (
        "A copyright page was detected on page {page} but author metadata could not be verified. "
        "Confirm the copyright block includes the required author format."
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
    ("P063", "appendix_subsection_missing_letter_prefix"): (
        "The appendix subsection identifier '{actual_identifier}' in the {appendix_location} "
        "on page {page} is missing its appendix letter. Add '{expected_letter}' at the start "
        "so it reads '{expected_identifier}'."
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
        "Body text on page {page} does not appear to be double-spaced. "
        "NJIT requires body text to be double-spaced, except for tables, figure "
        "descriptions, bullet points, and multi-line titles."
    ),
    ("P023", "blank_line_before_opening_level_three_heading"): (
        "An extra blank line appears above the level-three heading on page {page}."
    ),
    ("P023", "multiline_body_heading_not_single_spaced"): (
        "The highlighted lines of a numbered body heading on page {page} appear "
        "to use the same double-spaced line pitch as the surrounding prose. "
        "Multi-line titles must be single-spaced within the title."
    ),
    ("P023", "blank_line_above_level_three_heading"): (
        "The level-three heading on page {page} appears to have a blank line above it."
    ),
    # --- P016 paragraph/line spacing gaps ---
    ("P016", "blank_line_above_continuing_body_text"): (
        "An extra blank line appears above the continuing body text on page {page}."
    ),
    ("P016", "excessive_line_gap"): (
        "Unusually large spacing (about {largest_gap_pt}pt) was detected between "
        "lines on page {page}. Excluding necessary page breaks, text should flow "
        "consistently from the top margin to the bottom margin. Delete unnecessary "
        "blank lines and ensure body text flows continuously."
    ),
    ("P016", "excessive_paragraph_gap"): (
        "Unusually large spacing (about {largest_gap_pt}pt) was detected between "
        "paragraphs on page {page}. Excluding necessary page breaks for new chapters "
        "or to keep figures and tables with their captions, text should flow from the "
        "top margin to the bottom margin. Delete unnecessary blank lines."
    ),
    ("P016", "suspicious_heading_blank_gap"): (
        "An unusually large blank gap (about {largest_gap_pt}pt) was detected just "
        "after a heading on page {page}. Verify this is intentional spacing "
        "(such as a necessary page break or a heading kept with the text that "
        "follows it) and not an extra blank line. If unnecessary, delete the blank line."
    ),
    ("P061", "lot_cross_page_entry_numbers_not_nondecreasing"): (
        "List of Tables entry numbers may not be non-decreasing across a "
        "multi-page run starting at page {page}. Verify cross-page numbering "
        "continuity in the LoT."
    ),
    ("P061", "lof_cross_page_entry_numbers_not_nondecreasing"): (
        "List of Figures entry numbers may not be non-decreasing across a "
        "multi-page run starting at page {page}. Verify cross-page numbering "
        "continuity in the LoF."
    ),
    ("P057", "lot_page_numbers_not_nondecreasing"): (
        "List of Tables page numbers on page {page} do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "listed page numbers, so they increase from top to bottom."
    ),
    ("P057", "lof_page_numbers_not_nondecreasing"): (
        "List of Figures page numbers on page {page} do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "listed page numbers, so they increase from top to bottom."
    ),
    ("P059", "lot_entry_numbers_not_nondecreasing"): (
        "List of Tables entry numbers on page {page} do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "entry numbers, so they increase from top to bottom."
    ),
    ("P059", "lof_entry_numbers_not_nondecreasing"): (
        "List of Figures entry numbers on page {page} do not appear to be in "
        "non-decreasing order down the list. Reorder entries, or correct the "
        "entry numbers, so they increase from top to bottom."
    ),
    ("P062", "toc_cross_page_entry_numbers_not_nondecreasing"): (
        "Table of Contents section numbers may not be non-decreasing across a "
        "multi-page run starting at page {page}. Verify cross-page numbering "
        "continuity in the TOC."
    ),
    ("P065", "dedication_text_not_centered"): (
        "The dedication text on page {page} does not appear to be centered "
        "horizontally on the page. NJIT requires dedication text to be "
        "centered. Adjust the paragraph alignment in your source document."
    ),
    ("P065", "dedication_text_not_italic"): (
        "The dedication text on page {page} does not appear to be "
        "italicized. NJIT requires dedication text to be in italic font. "
        "Apply italic formatting to the dedication text."
    ),
    ("P078", "abstract_pdf_forbidden_term"): (
        "The abstract on page {page} appears to contain \"paper\" or "
        "\"article\" (or a plural form). NJIT abstract guidance asks you to "
        "avoid these terms. Replace \"paper\" or \"article\" with "
        "\"dissertation,\" \"study,\" \"work,\" or \"research.\""
    ),
    ("P078", "abstract_pdf_first_person_pronoun"): (
        "The abstract on page {page} appears to use a first-person pronoun "
        "such as \"I,\" \"me,\" \"my,\" \"we,\" or \"our.\" NJIT abstract "
        "guidance asks you to write in third person. Rewrite the sentence to "
        "remove first-person pronouns."
    ),
    ("P075", "toc_mixed_leader_styles"): (
        "Problem: The Table of Contents mixes dot and hyphen leaders before "
        "page numbers. The entry identified on page {page} is one example; "
        "check the other TOC entries too. Use one leader style throughout the TOC."
    ),
    ("P075", "toc_missing_leader_style"): (
        "Problem: The Table of Contents has entries without a leader before "
        "the page number while other entries use one. The entry identified "
        "on page {page} is one example. Add the same leader style to each "
        "affected TOC entry."
    ),
    ("P084", "biosketch_birth_information_present"): (
        "Problem: The Biographical Sketch on page {page} appears to include "
        "place-of-birth or date-of-birth information. Remove place of birth "
        "and date of birth from the Biographical Sketch."
    ),
    ("P085", "missing_first_chapter_one_heading"): (
        "The first body page on page {page} does not begin with the required "
        "CHAPTER 1 heading. Add the literal CHAPTER 1 heading at the beginning "
        "of the first body chapter."
    ),
    ("P086", "bold_heading_without_section_number"): (
        "Problem: A bold phrase on page {page} reads like a section heading "
        "but has no section number in front of it. Either add the section "
        "number or remove the bold styling from this phrase."
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
    # --- P017 figure/table captions ---
    ("P017", "unexpected_terminal_period"): (
        "Likely problem: A table title or List of Tables entry on page {page} "
        "appears to end with a terminal period. Remove the final period."
    ),
    ("P017", "missing_terminal_punctuation"): (
        "Likely problem: A figure description on page {page} appears to be missing "
        "terminal punctuation."
    ),
    ("P017", "excessive_caption_line_spacing"): (
        "The wrapped caption on page {page} appears to have wide internal line spacing."
    ),
    ("P017", "possible_sentence_case_issue"): (
        "Likely problem: A {caption_type} caption on page {page} appears to use "
        "Title Case where sentence case may be expected. Review the caption "
        "capitalization against NJIT caption-style guidance for this float type."
    ),
    ("P017", "possible_title_case_issue"): (
        "Likely problem: A table title on page {page} appears to violate "
        "NJIT title-case expectations. Capitalize the first word and major "
        "words; leave prepositions, conjunctions, and articles lowercase "
        "where appropriate."
    ),
    # --- P018 TOC/LoT/LoF alignment ---
    ("P018", "misaligned_page_number_column"): (
        "Likely problem: A TOC, List of Tables, or List of Figures entry on "
        "page {page} has a page-number column that does not align with the "
        "dominant column on this list page. Align entry page numbers to the "
        "same right-hand column throughout the list."
    ),
    ("P018", "missing_page_number"): (
        "Likely problem: A TOC, List of Tables, or List of Figures entry on "
        "page {page} appears to be missing its trailing page number. Add the "
        "correct page number for this entry."
    ),
    ("P018", "inconsistent_leader_dots"): (
        "Likely problem: Leader dots or spacing before page numbers on page "
        "{page} are inconsistent with the dominant style on this list page. "
        "Use consistent leader-dot spacing between entry text and page numbers."
    ),
    ("P018", "inconsistent_hierarchy_indent"): (
        "Likely problem: Entry indentation on page {page} does not match the "
        "expected hierarchy level for this TOC or list page. Adjust indentation "
        "so chapter, section, and subsection entries visually reflect their level."
    ),
    ("P018", "wrapped_title_continuation_misaligned"): (
        "Likely problem: A continuation line of a wrapped Table of Contents "
        "title on page {page} starts left of the first word of the title text. "
        + P018_WRAPPED_TITLE_FIX
    ),
    ("P018", "title_to_leader_gap_too_wide"): (
        "Likely problem: On page {page}, the leader dots in a Table of Contents, "
        "List of Tables, or List of Figures entry start after a visible gap "
        "instead of right after the title. Start the leader dots right after "
        "the last letter of the title, with at most one space before the first dot."
    ),
    ("P018", "leader_dots_before_final_title_line"): (
        "Likely problem: On page {page}, a wrapped Table of Contents, List of "
        "Tables, or List of Figures entry has leader dots on an earlier line of "
        "its title. For a title that runs longer than one line, place the "
        "leader dots after the final line of the title."
    ),
    # --- P021 abstract word count ---
    ("P021", "abstract_word_count_exceeded"): (
        "Problem: The abstract appears to contain {word_count} words, which "
        "exceeds the {limit}-word limit for a {degree_label} thesis. Shorten "
        "the abstract before submission."
    ),
    ("P060", "toc_subsection_number_ambiguous"): (
        "A TOC number conflicts with the preceding subsection and its indentation. "
        "Review the section number and heading level before changing capitalization."
    ),
    # --- P024 TOC/LoT/LoF capitalization and punctuation ---
    ("P024", "toc_level_capitalization"): (
        "Likely problem: A Table of Contents entry on page {page} may not "
        "follow NJIT capitalization rules for its heading level (Level 1 = ALL "
        "CAPS, Level 2 = Title Case, Level 3 = sentence case). Correct the entry "
        "capitalization."
    ),
    ("P024", "list_of_tables_title_case"): (
        "Likely problem: A List of Tables entry on page {page} may not use "
        "Title Case or may include terminal punctuation. Table titles in the "
        "List of Tables should use Title Case with no ending period."
    ),
    ("P024", "list_of_figures_title_case"): (
        "Likely problem: A List of Figures entry on page {page} may not use "
        "sentence case. Figure descriptions in the List of Figures should use sentence case."
    ),
    ("P024", "unexpected_terminal_punctuation"): (
        "Likely problem: A TOC or list entry on page {page} ends with terminal "
        "punctuation where NJIT expects none for that list type. Remove the "
        "trailing period unless the entry is intentionally written as a sentence."
    ),
    # --- P074 title page graduation month (PDF) ---
    ("P074", "title_page_graduation_month_invalid"): (
        "Problem: The graduation month on the Title Page is not August, "
        "December, or May. Change the graduation month on the Title Page to "
        "August, December, or May."
    ),
    # --- P035 figure/table layout ---
    ("P035", "table_caption_not_above_body"): (
        "Likely problem: A table title on page {page} does not appear above "
        "the table body. NJIT expects table titles to appear above the table."
    ),
    ("P035", "figure_caption_not_below_body"): (
        "Likely problem: A figure description on page {page} does not appear below "
        "the figure body. NJIT expects figure descriptions to appear below the figure."
    ),
    ("P035", "table_body_not_centered"): (
        "Likely problem: A table body block on page {page} does not appear "
        "centered between the page margins."
    ),
    ("P035", "figure_body_not_centered"): (
        "Likely problem: A figure body block on page {page} does not appear "
        "centered between the page margins."
    ),
    # --- P039 TOC hierarchy indentation ---
    ("P039", "toc_l2_not_indented_relative_to_l1"): (
        "Likely problem: A level-2 Table of Contents entry on page {page} does not "
        "appear indented to show hierarchy relative to level-1 entries. Indent "
        "level-2 TOC entries to the right of level-1 entries."
    ),
    ("P039", "toc_l3_not_indented_relative_to_l2"): (
        "Likely problem: A level-3 Table of Contents entry on page {page} does not "
        "appear indented to show hierarchy relative to level-2 entries. Indent "
        "level-3 TOC entries further to the right of level-2 entries."
    ),
    # --- P040 List of Figures punctuation ---
    ("P040", "lof_entry_missing_terminal_punctuation"): (
        "Problem: A figure description in the List of Figures on page {page} does "
        "not end with terminal punctuation. Add terminal punctuation, such as a "
        "period, question mark, or exclamation point, to every figure description "
        "in the List of Figures."
    ),
    # --- P041 dedication header text ---
    ("P041", "dedication_top_margin_header_text"): (
        "Problem: Header text appears to be present in the top margin area of "
        "the Dedication page on page {page}. Remove any running header or "
        "header text from the top margin area of the Dedication page."
    ),
    # --- P043 acknowledgements indentation ---
    ("P043", "acknowledgements_first_paragraph_indented"): (
        "Problem: The first paragraph on the Acknowledgements page (page "
        "{page}) appears to be indented. Remove any first-line indent from "
        "the first Acknowledgements paragraph."
    ),
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): (
        "Problem: A paragraph after the first on the Acknowledgements page (page "
        "{page}) appears flush-left where NJIT expects a first-line indent. Apply "
        "a first-line indent to each subsequent Acknowledgements paragraph."
    ),
    # --- P044 abstract indentation ---
    ("P044", "abstract_first_paragraph_indented"): (
        "Problem: The first paragraph on the Abstract page (page {page}) "
        "appears to be indented. Remove any first-line indent from the "
        "first Abstract paragraph."
    ),
    ("P044", "abstract_subsequent_paragraph_not_indented"): (
        "Likely problem: An Abstract paragraph after the first (page {page}) appears "
        "flush-left where NJIT expects a first-line indent. Apply a first-line "
        "indent to each subsequent Abstract paragraph."
    ),
    # --- P053/P054 list terminal periods ---
    ("P053", "lot_entry_has_terminal_period"): (
        "Problem: A List of Tables entry on page {page} ends with a final "
        "period. Remove the final period from each List of Tables entry. "
        "Table titles should use title case without terminal punctuation."
    ),
    ("P054", "toc_entry_has_terminal_period"): (
        "Problem: A Table of Contents entry on page {page} ends with a final "
        "period. Remove the final period from each Table of Contents entry."
    ),
    # --- P055 misplaced list entries ---
    ("P055", "lot_entry_is_figure"): (
        "Problem: A table entry on page {page} appears in the List of Tables "
        "but describes a figure. Move this entry to the List of Figures."
    ),
    ("P055", "lof_entry_is_table"): (
        "Problem: A figure entry on page {page} appears in the List of Figures "
        "but describes a table. Move this entry to the List of Tables."
    ),
    ("P055", "lot_entry_missing_table_prefix"): (
        "A List of Tables entry on page {page} starts with a number. The auditor could "
        "not identify a 'Table' column heading above the entry numbers."
    ),
    ("P055", "lof_entry_missing_figure_prefix"): (
        "This saved List of Figures prefix advisory reflects an older policy."
    ),
    ("P055", "body_figure_reference_abbreviated"): (
        "This body reference uses the abbreviation 'Fig.' before its number."
    ),
    # --- P058/P060 TOC ordering ---
    ("P058", "toc_page_numbers_not_nondecreasing"): (
        "Problem: Table of Contents page numbers on page {page} do not appear "
        "in ascending order. Reorder entries so listed page numbers increase "
        "from top to bottom."
    ),
    ("P087", "toc_abstract_entry_present"): (
        "Likely problem: A Table of Contents entry on page {page} is titled Abstract. "
        "Remove Abstract from the TOC; keep only the front-matter Abstract."
    ),
    ("P087", "toc_generic_title_repeated"): (
        "Review: The Table of Contents repeats the same generic section title "
        "in distinct entries, beginning on page {page}. Check whether the "
        "chapter or section context distinguishes them; if not, qualify the headings."
    ),
    ("P088", "figure_number_malformed"): (
        "Likely problem: A figure caption on page {page} uses a malformed number "
        "with extra concatenated segments. Use a chapter.sequence label such as 4.20."
    ),
    ("P088", "figure_number_duplicate"): (
        "Likely problem: A figure number on page {page} is repeated within the same "
        "chapter. Give each figure a unique sequence number."
    ),
    ("P088", "figure_number_out_of_order"): (
        "Likely problem: A figure number on page {page} appears out of increasing "
        "order within its chapter. Keep body figure numbers rising in reading order."
    ),
    ("P060", "toc_entry_numbers_not_nondecreasing"): (
        "Problem: Table of Contents section numbers on page {page} do not "
        "appear in non-decreasing order. Reorder entries so section numbers "
        "increase correctly down the list."
    ),
    # --- P064 references structural ---
    ("P064", "references_section_heading_not_detected"): (
        "Problem: No recognized REFERENCES or BIBLIOGRAPHY section heading "
        "was detected. Add a REFERENCES (or BIBLIOGRAPHY) heading before the "
        "reference list."
    ),
    ("P064", "references_entry_indentation_inconsistent"): (
        "Likely problem: Reference entries on page {page} appear to use "
        "inconsistent indentation styles. Use either hanging indent or "
        "flush-left formatting consistently for all entries."
    ),
    ("P064", "references_entry_spacing_inconsistent"): (
        "Likely problem: Spacing between reference entries on page {page} "
        "appears inconsistent. Use uniform spacing between all reference "
        "entries throughout the section."
    ),
    ("P064", "references_entry_not_single_spaced"): (
        "Likely problem: Lines within reference entries on page {page} appear "
        "double-spaced. Use single spacing within each reference, while keeping "
        "double spacing between consecutive entries."
    ),
    ("P064", "references_inter_entry_spacing_too_tight"): (
        "Likely problem: Gaps between reference entries on page {page} are close "
        "to the single-line spacing within entries. Use double spacing between "
        "consecutive references and keep each reference single-spaced internally."
    ),
    # --- P068 approval page structure ---
    ("P068", "approval_page_advisor_role_label_missing"): (
        "Problem: The Approval Page on page {page} lists {role_label_count} "
        "committee role label(s), but none of them is a recognizable advisor role "
        "label (for example, 'Dissertation Advisor' or 'Major Professor'). Add the "
        "required advisor or committee role label for each committee entry on the "
        "Approval Page."
    ),
    ("P068", "approval_page_signature_blocks_sparse"): (
        "Problem: The Approval Page on page {page} has {signature_date_indicator_count} "
        "signature/date line(s) for {role_label_count} committee role label(s), but "
        "at least {required_indicator_count} are expected. Add the required "
        "signature/date structural block for each committee entry on the Approval Page."
    ),
}

_RULE_FALLBACKS: dict[str, str] = {
    "P011": (
        "Text on page {page} is not contained entirely within the required page "
        "margins. NJIT requires: left 1.5 in, top/bottom/right 1 in. Move any "
        "text, table, or figure that extends into the margins back inside the "
        "required page area."
    ),
    "P013": (
        "A visible page number on page {page} may not be located exactly in the "
        "designated bottom-center position. Set page numbers at the bottom center "
        "of the page, 0.5 inches from the bottom edge."
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
        "A continuation page of a multi-page Table of Contents, List of Tables, or "
        "List of Figures on page {page} does not include the correct continued "
        "heading. Add the correct continued heading on each continuation page."
    ),
    "P033": (
        "Title-page consistency issue on page {page}. "
        "Review front-matter metadata manually."
    ),
    "P034": (
        "Copyright page issue on page {page}. "
        "Review copyright block format manually."
    ),
    "P051": (
        "Copyright page year issue on page {page}. "
        "Review the copyright block and confirm the copyright year is present."
    ),
    "P052": (
        "Copyright page author issue on page {page}. "
        "Review the copyright block and confirm the author name is present."
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
    "P011": (
        "Set left margin to 1.5 inches and top, bottom, and right margin to 1 inch."
    ),
    "P023": (
        "Apply double spacing to body text. Keep tables, figure descriptions, "
        "bullet points, and multi-line titles single-spaced."
    ),
    "P026": (
        "Word users: set body text to Times New Roman 12pt. "
        "Overleaf users: Computer Modern is an accepted equivalent — "
        "if flagged, verify with your advisor."
    ),
    "P028": (
        "Use lowercase Roman numerals for numbered front-matter pages, and "
        "use Arabic numerals for body pages."
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
    ("P016", "blank_line_above_continuing_body_text"): (
        "Remove the extra blank line so the continuing body text starts at its normal top margin."
    ),
    ("P023", "blank_line_before_opening_level_three_heading"): (
        "Remove the blank line above the heading. Keep the prescribed 8 pt of heading spacing."
    ),
    ("P023", "multiline_body_heading_not_single_spaced"): (
        "Single-space the wrapped lines within this heading. Keep the normal "
        "spacing between the heading and the body paragraph."
    ),
    ("P023", "blank_line_above_level_three_heading"): (
        "Remove the blank line above this level-three heading. Keep the normal body spacing."
    ),
    # P078 has two issue types; the rule-level remediation covers both, so a
    # pronoun finding told students to replace "paper"/"article". Give each
    # issue type only the half of the remediation that applies to it.
    ("P078", "abstract_pdf_first_person_pronoun"): (
        "Rewrite sentences to remove first-person pronouns such as \"I,\" "
        "\"me,\" \"my,\" \"we,\" or \"our.\""
    ),
    ("P078", "abstract_pdf_forbidden_term"): (
        "Replace \"paper\" or \"article\" with \"dissertation,\" \"study,\" "
        "\"work,\" or \"research.\""
    ),
    ("P039", "toc_l2_not_indented_relative_to_l1"): (
        "Indent the highlighted level-2 TOC entries to the right of level-1 entries."
    ),
    ("P039", "toc_l3_not_indented_relative_to_l2"): (
        "Indent the highlighted level-3 TOC entries to the right of level-2 entries."
    ),
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
    # P045's card remediation covers numbering and spacing together; each
    # finding gets only the fix for its own problem.
    ("P045", "biosketch_publication_entry_numbered"): (
        "Remove the number or label (such as [1] or 1.) in front of each "
        "publication or presentation entry. Keep the same citation format as the "
        "References section, just without the number."
    ),
    ("P045", "biosketch_publication_wrapped_line_spacing_not_single"): (
        "Single-space the wrapped lines within each publication or presentation "
        "entry."
    ),
    ("P045", "biosketch_publication_entry_spacing_not_double"): (
        "Add a blank line between separate publication or presentation entries."
    ),
    ("P038", "required_heading_missing"): (
        "Add this required section heading to the front matter, worded "
        "exactly as NJIT specifies."
    ),
    ("P038", "heading_phrase_not_exact"): (
        "Correct this heading to use the exact canonical NJIT phrase."
    ),
    # P014/P018 catalog `remediation` text is a developer index of internal
    # P###/Q### cross-references (per-page/sub-rule notation), not
    # student-facing wording — it must never reach `_remediation_by_rule()`'s
    # raw fallback. These overrides mirror the clean wording already shown on
    # the web UI (report_view.py's `_apply_named_heading_presentation` for
    # P014, toc_list_student_preview.py's `_P018_SHORT_FIX` for P018), so the
    # markdown-export and base-resolver paths (which do not go through those
    # presentation-layer rewrites) show the same clean text instead of the
    # raw catalog string.
    ("P014", "frontmatter_heading_layout_issue"): (
        "Format this front-matter heading in bold, all capital letters, and "
        "centered near the top of the page."
    ),
    ("P014", "frontmatter_heading_not_centered"): (
        "Center this heading within the text area. Keep it bold and in all "
        "capital letters."
    ),
    ("P018", "misaligned_page_number_column"): (
        "Align this entry's page number with the dominant right-hand column "
        "on this list page."
    ),
    ("P018", "missing_page_number"): "Add the missing trailing page number to this entry.",
    ("P018", "inconsistent_leader_dots"): (
        "Make the leader-dot spacing before this entry's page number match "
        "nearby entries."
    ),
    ("P018", "inconsistent_hierarchy_indent"): (
        "Align this entry's left indent with the other TOC entries at the "
        "same level."
    ),
    ("P018", "wrapped_title_continuation_misaligned"): P018_WRAPPED_TITLE_FIX,
    ("P018", "title_to_leader_gap_too_wide"): (
        "Start the leader dots right after the last letter of the title, "
        "leaving no more than one space."
    ),
    ("P018", "leader_dots_before_final_title_line"): (
        "Place the leader dots after the final line of the title, not on an "
        "earlier line."
    ),
    ("P021", "abstract_word_count_exceeded"): "",
    ("P017", "unexpected_terminal_period"): (
        "Remove the final period from this table title or List of Tables entry."
    ),
    ("P017", "missing_terminal_punctuation"): "End the figure description with a period.",
    ("P017", "possible_sentence_case_issue"): "",
    ("P017", "possible_title_case_issue"): (
        "Edit the table title to title case: capitalize the first word and "
        "major words; leave articles, prepositions, and conjunctions lowercase "
        "where appropriate."
    ),
    ("P024", "toc_level_capitalization"): "",
    ("P024", "list_of_tables_title_case"): "Use Title Case for this table title.",
    ("P024", "list_of_figures_title_case"): (
        "Use sentence case for this figure description; "
        "preserve proper names, acronyms and notation."
    ),
    ("P024", "unexpected_terminal_punctuation"): "",
    ("P035", "table_caption_not_above_body"): "Place the table title above the table body.",
    ("P035", "figure_caption_not_below_body"): (
        "Place the figure description below the figure body."
    ),
    ("P035", "table_body_not_centered"): "Center the table within the page margins.",
    ("P035", "figure_body_not_centered"): "Center the figure within the page margins.",
    ("P041", "dedication_top_margin_header_text"): "",
    ("P043", "acknowledgements_first_paragraph_indented"): "",
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): "",
    ("P044", "abstract_first_paragraph_indented"): "",
    ("P044", "abstract_subsequent_paragraph_not_indented"): "",
    ("P053", "lot_entry_has_terminal_period"): "",
    ("P054", "toc_entry_has_terminal_period"): "",
    ("P055", "lot_entry_is_figure"): "Move this misplaced entry to the List of Figures.",
    ("P055", "lof_entry_is_table"): "Move this misplaced entry to the List of Tables.",
    ("P055", "lot_entry_missing_table_prefix"): (
        "Place the 'Table' column heading above the entry numbers on this List of Tables page."
    ),
    ("P055", "lof_entry_missing_figure_prefix"): (
        "List of Figures entries may begin with a number; the word Figure is not required "
        "before each entry. Review body references separately."
    ),
    ("P055", "body_figure_reference_abbreviated"): (
        "Use the full word 'Figure' before the number in this body reference."
    ),
    ("P063", "appendix_subsection_missing_letter_prefix"): (
        "Add the owning appendix's letter before the leading dot in the subsection number."
    ),
    ("P068", "approval_page_advisor_role_label_missing"): "",
    ("P068", "approval_page_signature_blocks_sparse"): "",
}

_NO_ISSUE_OVERRIDE = object()


def _resolve_remediation(rule_id: str, issue_type: str) -> str:
    """Return the remediation text to append, preferring an issue-specific override."""
    override = _ISSUE_REMEDIATION_OVERRIDES.get((rule_id, issue_type), _NO_ISSUE_OVERRIDE)
    if override is not _NO_ISSUE_OVERRIDE:
        text = str(override).strip()
        if text:
            return text
    ester = student_warning_remediation(rule_id)
    if ester:
        return ester
    return _remediation_by_rule().get(rule_id, "")


@lru_cache(maxsize=1)
def _remediation_by_rule() -> dict[str, str]:
    """Load short remediation snippets from processed rule JSON (cached)."""
    rules_path = resource_path("data", "processed", "rules", "project_added_rules.json")
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
            remediation = _truncate_at_word_boundary(remediation, 200)
            result[rule_id] = remediation
    return result


def _truncate_at_word_boundary(text: str, limit: int) -> str:
    """Truncate text to fit within limit, breaking on a word boundary, not mid-word."""
    if len(text) <= limit:
        return text
    budget = limit - 3
    truncated = text[:budget]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return f"{truncated.rstrip()}..."


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


def _safe_position_label(position_type: str) -> str:
    labels = {
        "bottom_center": "bottom center",
        "bottom_right": "bottom right",
        "top_center": "top center",
        "top_right": "top right",
        "other": "an unexpected location",
    }
    return labels.get(position_type, "an unexpected location")


def _format_template(template: str, *, page: int | None, details: dict[str, str]) -> str:
    side = details.get("side", "document") or "document"
    position_type = details.get("position_type", "unknown position") or "unknown position"
    command = details.get("command", "formatting command") or "formatting command"
    page_type = details.get("page_type", "") or "this"
    observed_location = (
        details.get("observed_location", "")
        or details.get("candidate_position_label", "")
        or position_type.replace("_", " ")
        or "an unexpected location"
    )
    observed_style = (
        details.get("observed_style", "")
        or details.get("candidate_style_label", "")
        or details.get("observed_styles", "")
        or details.get("candidate_style", "")
        or "the observed numbering style"
    )
    expected_style = (
        details.get("expected_style", "")
        or details.get("expected_or_reason", "")
        or "the numbering style required for this section"
    )
    observed_sequence = (
        details.get("observed_sequence", "")
        or details.get("observed_value", "")
        or details.get("candidate_text", "")
        or "the detected value"
    )
    expected_sequence = (
        details.get("expected_sequence", "")
        or details.get("expected_value", "")
        or details.get("expected_roman", "")
        or "the expected sequence value"
    )
    section_label = _P037_SECTION_KEY_LABELS.get(
        details.get("section_key", ""), "this front-matter section"
    )
    caption_type = details.get("caption_type", "") or "figure/table"
    word_count = details.get("word_count", "") or "unknown"
    limit = details.get("limit", "") or "unknown"
    inferred_degree = details.get("inferred_degree_type", "") or "unknown"
    degree_labels = {
        "phd": "PhD",
        "ms": "MS",
        "unknown": "PhD (degree type uncertain — using PhD limit as default)",
    }
    degree_label = degree_labels.get(inferred_degree.lower(), inferred_degree.upper() or "unknown")
    largest_gap_pt = details.get("largest_gap_pt", "") or "an unusually large"
    role_label_count = details.get("role_label_count", "") or "0"
    signature_date_indicator_count = details.get("signature_date_indicator_count", "") or "0"
    try:
        required_indicator_count = str(max(2, int(role_label_count)))
    except ValueError:
        required_indicator_count = "2"
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
        appendix_location=details.get("appendix_location", "") or "appendix section",
        actual_identifier=details.get("actual_identifier", "") or "subsection number",
        expected_letter=details.get("expected_letter", "") or "the appendix letter",
        expected_identifier=details.get("expected_identifier", "") or "the corrected number",
        expected_heading=details.get("expected_heading", "") or "the required heading",
        toc_page=details.get("toc_page", "") or "unknown",
        substantial_line_count=details.get("substantial_line_count", "") or "0",
        observed_location=observed_location,
        observed_style=observed_style,
        expected_style=expected_style,
        observed_sequence=observed_sequence,
        expected_sequence=expected_sequence,
        section_label=section_label,
        caption_type=caption_type.replace("_", " "),
        word_count=word_count,
        limit=limit,
        degree_label=degree_label,
        largest_gap_pt=largest_gap_pt,
        role_label_count=role_label_count,
        signature_date_indicator_count=signature_date_indicator_count,
        required_indicator_count=required_indicator_count,
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

    _BOTTOM_CENTER_NOTE = (
        "NJIT requires page numbers at the bottom center of the page, "
        "0.5 inches from the bottom edge."
    )
    if count > 1:
        return (
            f"Multiple page-number-like tokens were detected on page "
            f"{page_label}. This may indicate duplicate numbering, extra "
            "footer/header text being mistaken for a page number, or an "
            "ambiguous page-number location. Verify which token is the "
            f"actual page number and remove or correct any unintended "
            f"duplicate. {_BOTTOM_CENTER_NOTE}"
        )
    if position_type in {"bottom_center", "bottom_right"}:
        position_label = position_type.replace("_", " ")
        return (
            f"A page-number candidate was detected at the {position_label} "
            f"of page {page_label}. This is a verification signal — confirm "
            "the number is visible and correctly placed. "
            f"{_BOTTOM_CENTER_NOTE}"
        )
    if position_type in {"top_center", "top_right", "other"}:
        return (
            f"Problem: The page number on page {page_label} appears at "
            f"{_safe_position_label(position_type)}, but NJIT expects the "
            "page number at the bottom center of the page, 0.5 inches "
            "from the bottom edge. Move the page number to the required "
            "bottom-center position."
        )
    return (
        f"A page-number candidate was detected on page {page_label}. "
        f"Verify it is visible and correctly placed. {_BOTTOM_CENTER_NOTE}"
    )


_TITLE_CASE_REASON_TEXT: dict[str, str] = {
    "first_word_requires_capital": "the first word is not capitalized",
    "word_after_separator_requires_capital": (
        "a word after a colon, dash, or similar separator is not capitalized"
    ),
    "major_word_requires_capital": (
        "a major word (not an article, preposition, or conjunction) is not capitalized"
    ),
}

_TITLE_CASE_REASON_SHORT: dict[str, str] = {
    "first_word_requires_capital": "first word",
    "word_after_separator_requires_capital": "word after separator",
    "major_word_requires_capital": "major word",
}


def title_case_subject_label(source: str) -> str:
    """Short subject label for a P020 finding's `source` field.

    Used to distinguish result cards (table titles vs headings) without
    ever quoting document text.
    """
    return "table title" if source == "caption" else "heading"


def title_case_reason_short_label(reason: str) -> str:
    """Short label for a P020 `expected_or_reason` code.

    Used only to distinguish result cards that would otherwise look like
    duplicates; never reveals the flagged word.
    """
    return _TITLE_CASE_REASON_SHORT.get(reason, "capitalization")


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
        return (
            f"Possible title-case issue in a {subject} on page {page_label}: "
            f"{reason_text}. NJIT requires table titles to use Title Case "
            "(every word capitalized except prepositions, conjunctions, and "
            "articles), and table titles must not end with a period."
        )
    subject = "Level 2 heading"
    rule_text = "NJIT requires Level 2 headings (e.g. 1.1, 1.2) to use Title Case"
    return (
        f"Possible title-case issue in a {subject} on page {page_label}: "
        f"{reason_text}. {rule_text} (capitalize the first word and all major "
        "words; leave articles, prepositions, and conjunctions lowercase in "
        "the middle)."
    )


def _p024_toc_level_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P024 toc_level_capitalization comment body.

    TOC levels are checked against their own capitalization rules; branching on the
    recorded `entry_level` keeps each finding's comment scoped to the rule
    that actually applies, instead of describing both rules generically.
    The flagged word itself is never quoted here.
    """
    page_label = _safe_page_label(page)
    level = details.get("entry_level", "") or ""
    if level == "1":
        return (
            f"Likely problem: A Level 1 Table of Contents entry on page {page_label} "
            "may not follow NJIT capitalization rules: Level 1 entries are expected "
            "to use ALL CAPS. Correct the entry to ALL CAPS."
        )
    if level == "3":
        return (
            f"Likely problem: A Level 3 Table of Contents entry on page {page_label} "
            "appears to use Title Case. NJIT expects sentence case for Level 3 "
            "entries. Capitalize the first word and proper names, and preserve "
            "acronyms and technical notation."
        )
    reason = details.get("expected_or_reason", "") or ""
    reason_text = _TITLE_CASE_REASON_TEXT.get(reason, "a word is not capitalized as expected")
    return (
        f"Likely problem: A Level 2 Table of Contents entry on page {page_label} may "
        f"not follow NJIT capitalization rules for Title Case: {reason_text}. Correct "
        "the entry capitalization (Level 2 entries use Title Case)."
    )


def _p024_lot_title_case_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P024 list_of_tables_title_case comment body.

    Reuses the same `expected_or_reason` violation-category vocabulary as
    P020/TOC Level 2 entries, since List of Tables titles are checked with
    the same Title Case rule. The flagged word itself is never quoted here.
    """
    page_label = _safe_page_label(page)
    reason = details.get("expected_or_reason", "") or ""
    reason_text = _TITLE_CASE_REASON_TEXT.get(reason, "a word is not capitalized as expected")
    return (
        f"Likely problem: A List of Tables entry on page {page_label} may not use "
        f"Title Case: {reason_text}. Table titles in the List of Tables should use "
        "Title Case with no ending period."
    )


def _p024_lof_title_case_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Explain the legacy R024E subtype using the current sentence-case policy."""
    return (
        "Likely problem: A figure description in the List of Figures "
        f"on page {_safe_page_label(page)} "
        "appears to use Title Case. Use sentence case: capitalize the first word "
        "and proper names, and preserve acronyms and technical notation."
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


def _p036_entry_pair_label(details: dict[str, str]) -> str:
    try:
        index = int(details.get("entry_pair_index", "").strip())
    except ValueError:
        return "two consecutive entries"
    return f"entries {index + 1}-{index + 2}"


def _p036_spacing_detail_phrase(details: dict[str, str]) -> str:
    gap_points = details.get("gap_points", "").strip()
    required_gap_points = details.get("required_gap_points", "").strip()
    extras: list[str] = []
    if gap_points:
        extras.append(f"observed gap {gap_points}pt")
    if required_gap_points:
        extras.append(f"expected at least {required_gap_points}pt")
    if not extras:
        return ""
    return f" ({'; '.join(extras)})"


def _p036_spacing_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P036 inter-entry-spacing comment body.

    Deliberately omits entry_pair_index/gap_points so the text stays identical
    across same-page/same-section occurrences: build_grouped_findings() keys
    grouping on this comment text (see report_outputs.py), and per-occurrence
    detail (pair index, exact gap) is added only by the post-grouping display
    override in report_view.py's _apply_spacing_presentation, which mirrors
    this wording. Changing this text without updating that override would
    desync the JSON report's polished_comment from the web/Markdown display.
    """
    page_label = _safe_page_label(page)
    section_label = _P036_SECTION_LABELS.get(details.get("section_type", ""), "TOC/list")
    return (
        f"Problem: Consecutive entries of the {section_label} on page "
        f"{page_label} do not appear to have visible double spacing or a blank "
        "line between them. Add visible double spacing or a blank line between "
        f"consecutive entries in the {section_label}."
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


def _p015_indentation_comment(
    issue_type: str, *, page: int | None, details: dict[str, str]
) -> str:
    page_label = _safe_page_label(page)
    descriptor = _p015_paragraph_descriptor(issue_type, details)
    if issue_type == "unexpected_opening_indent":
        return (
            f"Likely problem: {descriptor.capitalize()} on page {page_label} appears "
            "to have a first-line indent. NJIT expects the first paragraph after a "
            "section heading to begin flush with the left margin. Remove the first-line "
            "indent from this paragraph."
        )
    if issue_type == "unexpected_indent_on_continuation_line":
        return (
            f"Likely problem: {descriptor.capitalize()} on page {page_label} appears "
            "to use a paragraph-style first-line indent. NJIT expects continuation "
            "lines after a displayed equation or similar break to stay flush with the "
            "left margin. Remove the first-line indent from this continuation line."
        )
    return (
        f"Likely problem: {descriptor.capitalize()} on page {page_label} appears to "
        "be missing its required first-line indent. Apply a first-line indent to this "
        "body paragraph after the first paragraph in the section."
    )


def _margin_side_label(details: dict[str, str]) -> str:
    from njit_auditor.p011_margin_presentation import margin_side_label

    return margin_side_label(details)


def _p011_margin_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Card-level P011 comment — kept generic (no per-occurrence overflow amount
    or confidence wording) because this text feeds build_grouped_findings()'s
    grouping key; embedding an instance-specific number here would split every
    margin violation onto its own card. The exact measured overrun and a
    low-confidence caveat are surfaced per-occurrence instead, via
    margin_location_label() and the existing confidence badge (see
    p027_heading_location_label's docstring pattern and
    test_same_problem_with_different_confidence_stays_on_one_card_by_default)."""
    from njit_auditor.p011_margin_presentation import margin_comment_body, page_context_from_details

    page_label = _safe_page_label(page)
    side = _margin_side_label(details)
    page_context = page_context_from_details(details)
    return margin_comment_body(
        page_label=page_label,
        side_label=side,
        page_context=page_context,
        overflow_detail="",
        lines_clause="",
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


def _p012_annotation_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    annotation_label = _p012_annotation_label(details)
    return (
        f"Likely problem: The uploaded PDF appears to already contain a "
        f"{annotation_label} on page {page_label}. This refers to something left in "
        "the original file you uploaded, not a highlight added by this auditor to "
        "show where a problem is located. Resolve or delete all annotations before "
        "final submission: accept or reject any reviewer changes, remove comments, "
        "highlights, or markup from the PDF, and upload a clean copy."
    )


_P014_ATTRIBUTE_LABELS: tuple[tuple[str, str], ...] = (
    ("centered", "centered"),
    ("near_top", "near the top of the page"),
    ("bold", "bold"),
    ("all_caps", "in all capital letters"),
)


def _p014_heading_comment(*, page: int | None, details: dict[str, str]) -> str:
    # Deliberately never echoes details["heading"] (the extracted section-name
    # text) — this comment is meant to be a stable, privacy-conservative
    # template regardless of which named front-matter heading was flagged.
    page_label = _safe_page_label(page)
    failed_labels = [
        label
        for key, label in _P014_ATTRIBUTE_LABELS
        if details.get(key, "").strip().lower() == "false"
    ]
    if failed_labels:
        observed = (
            f"a front-matter heading on page {page_label} is "
            + ", ".join(f"not {label}" for label in failed_labels)
        )
    else:
        observed = (
            f"a front-matter heading on page {page_label} does not match "
            "NJIT's expected layout/style"
        )
    return (
        f"Problem: Detected that {observed}. NJIT requires named front-matter "
        "section headings to be centered near the top of the page, in bold, "
        "and in all capital letters. Correct any attributes that do not match."
    )


def _p026_font_comment(
    *,
    issue_type: str,
    page: int | None,
    details: dict[str, str],
    raw_details: dict[str, str],
) -> str:
    page_label = _safe_page_label(page)
    observed = (
        raw_details.get("observed_font", "").strip()
        or raw_details.get("observed_size", "").strip()
    )
    if issue_type == "possible_body_font_size_issue":
        expected = (
            details.get("expected_size", "").strip()
            or details.get("expected", "").strip()
            or "12pt"
        )
        if observed:
            return (
                "Likely problem: Body text on page "
                f"{page_label} appears to use font size {observed}. "
                f"NJIT expects body text to use {expected}. Update the source document's "
                "body-text style or verify whether the flagged text is a permitted exception "
                "such as a table, figure caption, heading, or footnote."
            )
        return (
            f"Likely problem: Some body-text-like spans on page {page_label} appear not to "
            "match NJIT's expected font size. The auditor could not extract a precise "
            f"observed size value for this card. NJIT expects body text to use {expected}. "
            "Review the explanation and verify whether the flagged text is a permitted "
            "exception such as a table, figure caption, heading, or footnote."
        )
    expected = (
        details.get("expected_font", "").strip()
        or details.get("expected", "").strip()
        or "Times New Roman, Arial, Computer Modern, or Latin Modern"
    )
    _FONT_NOTE = (
        "Use Times New Roman or Arial for Word documents, or Computer Modern/Latin Modern "
        "for Overleaf documents, unless your program has approved a different font."
    )
    if observed:
        return (
            "Likely problem: Body text on page "
            f"{page_label} appears to use font family {observed}. "
            f"NJIT expects body text to use {expected}. "
            f"{_FONT_NOTE} "
            "Update the source document's body-text font settings if this text is "
            "part of the main body."
        )
    return (
        f"Likely problem: Some body-text-like spans on page {page_label} appear not to "
        "match NJIT's expected font family. The auditor could not extract a precise "
        f"observed font value for this card. NJIT expects body text to use {expected}. "
        f"{_FONT_NOTE} "
        "Confirm whether the flagged text is body text or another text role such as "
        "a heading, caption, or footnote."
    )


_P032_ENTRY_KIND_LABELS: dict[str, str] = {
    "table_entry": "List of Tables entry",
    "figure_entry": "List of Figures entry",
    "toc_level_1": "Table of Contents chapter/appendix entry",
    "toc_level_2": "Table of Contents entry",
    "toc_level_3": "Table of Contents sub-entry",
}
P032_ENTRY_KIND_LABELS = _P032_ENTRY_KIND_LABELS


def _p032_wrapped_spacing_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    entry_label = _P032_ENTRY_KIND_LABELS.get(details.get("entry_kind", ""), "list entry")
    observed_gap = details.get("observed_gap_pt", "").strip()
    expected_gap = details.get("expected_max_gap_pt", "").strip()
    gap_clause = (
        f" — about {observed_gap}pt, versus an expected maximum of about "
        f"{expected_gap}pt for this entry's line height"
        if observed_gap and expected_gap
        else ""
    )
    return (
        f"Likely problem: A wrapped {entry_label} on page "
        f"{page_label} does not appear to be single-spaced within the same entry"
        f"{gap_clause}. Single-space wrapped entries so continuation lines stay "
        "within the same entry without extra blank space."
    )


def _p056_format_counts(details: dict[str, str]) -> tuple[str, str]:
    """Parse P056's 'chapter_based:N,sequential:M' details string into (N, M)."""
    counts = {}
    for part in details.get("format_counts", "").split(","):
        key, _, value = part.partition(":")
        if key.strip():
            counts[key.strip()] = value.strip()
    return counts.get("chapter_based", "0"), counts.get("sequential", "0")


_P056_SECTION_LABELS: dict[str, str] = {
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}
_P056_SECTION_NOUNS: dict[str, str] = {
    "list_of_tables": "Table",
    "list_of_figures": "Figure",
}


def _p056_mixed_numbering_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    section = details.get("section_type", "")
    section_label = _P056_SECTION_LABELS.get(section, "list")
    noun = _P056_SECTION_NOUNS.get(section, "entry")
    chapter_count, sequential_count = _p056_format_counts(details)
    dominant = details.get("dominant_format", "")
    dominant_clause = ""
    if dominant == "chapter_based":
        dominant_clause = f" The more common format here is chapter-based (e.g., {noun} 1.2)."
    elif dominant == "sequential":
        dominant_clause = f" The more common format here is sequential (e.g., {noun} 3)."
    return (
        f"Likely problem: The {section_label} on page {page_label} mixes two entry-"
        f"numbering formats: {chapter_count} chapter-based (e.g., {noun} 1.2) and "
        f"{sequential_count} sequential (e.g., {noun} 3) entries.{dominant_clause} "
        "NJIT expects one consistent numbering format throughout this list."
    )


def _p066_degree_order_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    first_year = details.get("first_candidate_year", "").strip() or "an earlier year"
    last_year = details.get("last_candidate_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        f"Problem: Postgraduate degree entries on the Biographical Sketch page "
        f"(page {page_label}) may not be listed from most recent to oldest: the "
        f"candidate years found (in listed order) run from {first_year} to "
        f"{last_year}, with {inversion_count} {place_noun} where a later-listed "
        "entry's year is more recent than the entry just before it. Reorder "
        "postgraduate degree entries in the Biographical Sketch from most recent "
        "to oldest."
    )


def _p067_publication_order_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    first_year = details.get("first_entry_year", "").strip() or "an earlier year"
    last_year = details.get("last_entry_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        "Problem: Publication and presentation entries on the Biographical "
        f"Sketch page (page {page_label}) may not be listed from most recent to "
        f"oldest: the comparable entry years found (in listed order) run from "
        f"{first_year} to {last_year}, with {inversion_count} {place_noun} where a "
        "later-listed entry's year is more recent than the entry just before it. "
        "Reorder publication and presentation entries in the Biographical Sketch "
        "from most recent to oldest."
    )


def _p045_hanging_indent_comment(*, page: int | None, details: dict[str, str]) -> str:
    # The auditor no longer emits this issue type; kept so reports stored
    # before Ester's 2026-10-05 ruling still render accurately.
    page_label = _safe_page_label(page)
    return (
        "Note: Publication/presentation entries on the Biographical Sketch "
        f"page (page {page_label}) do not appear to use a hanging indent. A "
        "hanging indent is optional, so no change is required for this."
    )


def _p045_line_spacing_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    pitch = details.get("observed_line_pitch_points", "").strip()
    font_size = details.get("font_size_points", "").strip()
    gap_clause = (
        f" — wrapped lines about {pitch}pt apart for {font_size}pt text"
        if pitch and font_size
        else ""
    )
    return (
        "Problem: Wrapped lines within a publication/presentation entry on the "
        f"Biographical Sketch page (page {page_label}) do not appear to be "
        f"single-spaced{gap_clause}. Single-space the lines within each entry "
        "and keep a blank line between separate entries."
    )


def _p045_numbered_entry_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    return (
        "Problem: Publication/presentation entries on the Biographical Sketch page "
        f"(page {page_label}) start with a number or label such as [1] or 1. These "
        "entries are not references and must not be numbered. Remove the number in "
        "front of each entry and keep the same citation format as the References "
        "section."
    )


def _p045_entry_spacing_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    observed = details.get("observed_gap_points", "").strip()
    required = details.get("required_gap_points", "").strip()
    gap_clause = (
        f" — about {observed}pt, versus the required minimum of about {required}pt"
        if observed and required
        else ""
    )
    return (
        "Problem: Two consecutive publication/presentation entries on the "
        f"Biographical Sketch page (page {page_label}) do not appear to have a "
        f"blank line between them{gap_clause}. Add a blank line between separate "
        "entries."
    )


def _p047_block_label(details: dict[str, str]) -> str:
    raw = details.get("block_index", "").strip()
    try:
        return f"bullet block {int(raw) + 1}"
    except ValueError:
        return "a bullet/list block"


def _p047_bullet_spacing_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    block_label = _p047_block_label(details)
    observed = details.get("observed_gap_points", "").strip()
    required_max = details.get("required_max_gap_points", "").strip()
    gap_clause = (
        f" — about {observed}pt, versus an expected maximum of about {required_max}pt"
        if observed and required_max
        else ""
    )
    return (
        f"Problem: A {block_label} on the Biographical Sketch page (page "
        f"{page_label}) appears to have extra spacing inside the bullet item"
        f"{gap_clause}. Single-space each bullet item in the Biographical Sketch "
        "education section, with no extra blank lines inside the same bullet item."
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


def _p031_column_header_comment(
    issue_type: str, *, page: int | None, details: dict[str, str]
) -> str:
    page_label = _safe_page_label(page)
    section_label = _lot_lof_section_label(details)
    expected_left = details.get("expected_left_label", "").strip() or "Table/Figure"
    expected_page = details.get("expected_page_label", "").strip() or "Page"

    if issue_type == "missing_left_column_header":
        return (
            f"Likely problem: The {section_label} page (page {page_label}) does not "
            f"show the required '{expected_left}' column header. Add the required "
            "column headers directly below the list heading: "
            f"'{expected_left}' on the left and 'Page' on the right."
        )
    if issue_type == "missing_page_column_header":
        return (
            f"Likely problem: The {section_label} page (page {page_label}) does not "
            f"show the required '{expected_page}' column header. Add the required "
            "column headers directly below the list heading: "
            f"'{expected_left}' on the left and '{expected_page}' on the right."
        )
    observed = _format_points(details.get("observed_x0_pt", ""))
    if issue_type == "left_column_header_misaligned":
        expected = _format_points(details.get("expected_left_x_pt", ""))
        gap_clause = (
            f" (observed at about {observed} from the left margin, versus an "
            f"expected position of about {expected})"
            if observed and expected
            else ""
        )
        return (
            f"Likely problem: The '{expected_left}' column header on the "
            f"{section_label} page (page {page_label}) appears far from the entry "
            f"column it labels{gap_clause}. NJIT requires the '{expected_left}' "
            "header to line up with the entry numbers below it."
        )
    expected = _format_points(details.get("expected_page_x_pt", ""))
    gap_clause = (
        f" (observed at about {observed} from the left margin, versus an "
        f"expected position of about {expected})"
        if observed and expected
        else ""
    )
    return (
        f"Likely problem: The '{expected_page}' column header on the "
        f"{section_label} page (page {page_label}) appears far from the "
        f"page-number column it labels{gap_clause}. NJIT requires the "
        f"'{expected_page}' header to line up with the page numbers below it."
    )


def _p046_entry_alignment_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    section_label = _lot_lof_section_label(details)
    entry_noun = _lot_lof_entry_noun(details)
    observed_range = _format_points(details.get("observed_x0_range_points", ""))
    allowed_range = _format_points(details.get("allowed_x0_range_points", ""))
    range_clause = (
        f" — entry numbers vary by about {observed_range} from left to right, "
        f"versus an allowed variation of about {allowed_range}"
        if observed_range and allowed_range
        else ""
    )
    return (
        f"Likely problem: {section_label} entry numbers on page {page_label} do not "
        f"appear to be aligned vertically in one left column{range_clause}. Align "
        f"all {entry_noun} numbers in the {section_label} into one consistent left "
        "column."
    )


def _p048_page_number_alignment_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    section_label = _lot_lof_section_label(details)
    observed = _format_points(details.get("observed_page_number_x", ""))
    expected = _format_points(details.get("expected_page_number_x", ""))
    measure_clause = (
        f" (observed at about {observed} from the left, versus an expected "
        f"position of about {expected})"
        if observed and expected
        else ""
    )
    return (
        f"Likely problem: Page numbers in the {section_label} (page {page_label}) "
        f"do not appear to be aligned vertically in one right column"
        f"{measure_clause}. Align all page numbers in the {section_label} into one "
        "consistent right column."
    )


def _p049_page_header_style_comment(
    issue_type: str, *, page: int | None, details: dict[str, str]
) -> str:
    page_label = _safe_page_label(page)
    section_label = _lot_lof_section_label(details)
    if issue_type in {
        "lot_page_header_not_right_aligned",
        "lof_page_header_not_right_aligned",
    }:
        observed = _format_points(details.get("observed_x", ""))
        expected = _format_points(details.get("expected_x", ""))
        measure_clause = (
            f" (observed at about {observed} from the left, versus an expected "
            f"position of about {expected})"
            if observed and expected
            else ""
        )
        return (
            f"Likely problem: The 'Page' column header on the {section_label} page "
            f"(page {page_label}) does not appear to be right-aligned over the "
            f"page-number column{measure_clause}. Format the 'Page' column header "
            "in bold and align it over the page-number column on the right."
        )
    verify_clause = _font_metadata_clause(details)
    return (
        f"Likely problem: The 'Page' column header on the {section_label} page "
        f"(page {page_label}) is not formatted in bold.{verify_clause} Format the "
        "'Page' column header in bold and align it over the page-number column on "
        "the right."
    )


def _p050_left_bold_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    section_label = _lot_lof_section_label(details)
    header_word = "Table" if _lot_lof_entry_noun(details) == "table" else "Figure"
    verify_clause = _font_metadata_clause(details)
    return (
        f"Likely problem: The '{header_word}' column header on the {section_label} "
        f"page (page {page_label}) is not formatted in bold.{verify_clause} "
        f"Format the \"{header_word}\" column header in bold."
    )


def _p042_entry_position_clause(details: dict[str, str]) -> str:
    entry_index = details.get("entry_index", "").strip()
    entry_count = details.get("appendix_entry_count", "").strip()
    if entry_index.isdigit() and entry_count.isdigit():
        position = int(entry_index) + 1
        return f" (entry {position} of {entry_count} appendix entries listed)"
    return ""


def _p042_appendix_format_comment(
    issue_type: str, *, page: int | None, details: dict[str, str]
) -> str:
    page_label = _safe_page_label(page)

    if issue_type == "single_appendix_missing_title":
        expected_pattern = details.get("expected_pattern", "").strip() or "APPENDIX <title>"
        return (
            f"Problem: The Table of Contents on page {page_label} lists a "
            "single appendix entry that does not appear to include a title after "
            f"'APPENDIX'. For one appendix, begin the TOC entry with \"APPENDIX\" "
            f"followed by the title (pattern '{expected_pattern}'). Add the "
            "missing appendix title to this Table of Contents entry."
        )

    expected_pattern = details.get("expected_pattern", "").strip() or "APPENDIX <A-Z>"
    position_clause = _p042_entry_position_clause(details)
    return (
        f"Problem: The Table of Contents on page {page_label} lists "
        f"multiple appendix entries, but one entry{position_clause} does not "
        "appear to include a letter identifier. For multiple appendices, label "
        f"each TOC entry with a letter, such as \"APPENDIX A,\" \"APPENDIX B,\" "
        f"and so on (pattern '{expected_pattern}'). Add the missing letter to "
        "this Table of Contents entry."
    )


_P033_ROLE_LABELS: dict[str, str] = {
    "title_page": "Title Page",
    "abstract": "Abstract",
    "approval_page": "Approval Page",
}


def _p033_role_label(role: str) -> str:
    # Callers always prepend "the" (e.g. "the title on the {reference_role}"),
    # so this fallback must read naturally as "the other front-matter page",
    # not "the another front-matter page".
    return _P033_ROLE_LABELS.get(role, "other front-matter page")


def _p033_frontmatter_title_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P033 frontmatter_title_mismatch comment body.

    The detector compares normalized title text across the Title Page,
    Abstract, and Approval Page and never records the title text itself —
    only page roles, hashes, and similarity scores — so this comment names
    the flagged pages and the compared role without ever quoting a title.
    """
    page_label = _safe_page_label(page)
    reference_role = _p033_role_label(details.get("reference_page_role", ""))
    mismatch_pages = details.get("mismatch_pages", "").strip()
    if mismatch_pages and "," in mismatch_pages:
        pages_clause = f"pages {mismatch_pages}"
    elif mismatch_pages:
        pages_clause = f"page {mismatch_pages}"
    else:
        pages_clause = f"page {page_label}"
    return (
        f"Problem: The dissertation title on {pages_clause} does not closely match "
        f"the title on the {reference_role}, based on a normalized text comparison "
        "(not an exact match check). NJIT requires the dissertation title to be "
        "worded identically everywhere it appears in the front matter — Title Page, "
        f"Abstract, and Approval Page. Compare the title as printed on {pages_clause} "
        f"against the {reference_role} and correct whichever one does not match. "
        "Minor line-wrap or spacing differences are not flagged, so a flagged "
        "difference is likely a real wording mismatch — verify by reading both "
        "pages before editing."
    )


def _p051_copyright_year_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P051 copyright_year_not_found comment body.

    This advisory fires when a copyright page is found but no four-digit
    year could be confidently extracted from it; ``copyright_marker_detected``
    distinguishes "marker present, year missing" from "no recognizable
    copyright wording at all" so the comment names the right gap.
    """
    page_label = _safe_page_label(page)
    marker_detected = details.get("copyright_marker_detected", "").strip().lower() == "true"
    if marker_detected:
        observed = (
            "copyright-notice wording was found on this page, but the auditor could "
            "not confidently associate a four-digit year with that notice"
        )
    else:
        observed = (
            "this page was identified as the Copyright Page, but the auditor did not "
            "find recognizable copyright-notice wording or a four-digit year on it"
        )
    return (
        f"Problem: On the Copyright Page (page {page_label}), {observed}. NJIT "
        "requires the Copyright Page to state the copyright year clearly next to "
        "the copyright notice (for example, 'Copyright © 2025 by [Author "
        "Name]. All Rights Reserved.'), matching the year the degree is conferred. "
        "Check this page for the year: add it if missing, or move it directly next "
        "to the copyright notice in a standard readable format if it is present but "
        "in an unusual spot or layout. This is an automated, approximate check — "
        "the year may be present but hard to associate automatically, so always "
        "verify by reading the page directly."
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
    raw_details = {str(k): str(v) for k, v in (details or {}).items()}
    safe_details = {
        k: v for k, v in (details or {}).items() if k not in _BLOCKED_DETAIL_KEYS
    }
    issue = issue_type or safe_details.get("issue_type", "")
    if rule_id == "P062" and issue == P062_ISSUE:
        if pair := describe_p062_pair(safe_details):
            return _finish_comment(pair, rule_id=rule_id, issue_type=issue, specific=True)
    if rule_id in _SOURCE_RULE_IDS and not issue:
        issue = derive_source_issue_type(rule_id, safe_details)
    if (
        rule_id == "P021"
        and not issue
        and safe_details.get("word_count")
        and safe_details.get("limit")
    ):
        issue = "abstract_word_count_exceeded"

    if rule_id == "P013" and issue == "page_number_candidate":
        body = _p013_candidate_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P017" and issue == "missing_terminal_punctuation":
        continuation = caption_continuation_explanation(safe_details)
        if continuation:
            return _finish_comment(continuation, rule_id=rule_id, issue_type=issue, specific=True)
        if (
            safe_details.get("caption_context") == "list_of_figures"
            or safe_details.get("source_q_rule_id") == "Q075"
        ):
            body = (
                f"Likely problem: A List of Figures description on page {_safe_page_label(page)} "
                "appears to be missing terminal punctuation."
            )
            return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P017" and issue == "unexpected_terminal_period":
        subject = (
            "List of Tables entry"
            if safe_details.get("caption_context") == "list_of_tables"
            else "table title"
        )
        body = (
            f"Likely problem: A {subject} on page {_safe_page_label(page)} "
            "appears to end with a terminal period. Remove the final period."
        )
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P020" and issue == "possible_title_capitalization_issue":
        body = _p020_title_case_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P024" and issue == "toc_level_capitalization":
        body = _p024_toc_level_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P024" and issue == "list_of_tables_title_case":
        body = _p024_lot_title_case_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P024" and issue == "list_of_figures_title_case":
        body = _p024_lof_title_case_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P036" and issue in _P036_SPACING_ISSUE_TYPES:
        body = _p036_spacing_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P011" and issue == "margin_boundary_violation":
        body = _p011_margin_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P012" and issue == "pdf_annotation_detected":
        body = _p012_annotation_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P014" and issue in {
        "frontmatter_heading_layout_issue",
        "frontmatter_heading_not_centered",
    }:
        body = _p014_heading_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P015" and issue in {
        "unexpected_opening_indent",
        "missing_later_indent",
        "unexpected_indent_on_continuation_line",
    }:
        body = _p015_indentation_comment(issue, page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P026" and issue in {
        "possible_body_font_family_issue",
        "possible_body_font_size_issue",
    }:
        body = _p026_font_comment(
            issue_type=issue,
            page=page,
            details=safe_details,
            raw_details=raw_details,
        )
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P032" and issue == "wrapped_entry_internal_spacing":
        body = _p032_wrapped_spacing_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P056" and issue in {
        "lot_mixed_numbering_format",
        "lof_mixed_numbering_format",
    }:
        body = _p056_mixed_numbering_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P066" and issue == "biosketch_degree_order_suspicious":
        body = _p066_degree_order_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P067" and issue == "biosketch_publication_order_suspicious":
        body = _p067_publication_order_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P045" and issue == "biosketch_publication_entry_numbered":
        body = _p045_numbered_entry_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P045" and issue == "biosketch_publication_missing_hanging_indent":
        body = _p045_hanging_indent_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P045" and issue == "biosketch_publication_wrapped_line_spacing_not_single":
        body = _p045_line_spacing_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P045" and issue == "biosketch_publication_entry_spacing_not_double":
        body = _p045_entry_spacing_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P047" and issue == "biosketch_bullet_section_not_single_spaced":
        body = _p047_bullet_spacing_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P031" and issue in {
        "missing_left_column_header",
        "missing_page_column_header",
        "left_column_header_misaligned",
        "page_column_header_misaligned",
    }:
        body = _p031_column_header_comment(issue, page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P046" and issue in {
        "lot_entry_number_column_misaligned",
        "lof_entry_number_column_misaligned",
    }:
        body = _p046_entry_alignment_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P048" and issue in {
        "lot_page_number_column_misaligned",
        "lof_page_number_column_misaligned",
    }:
        body = _p048_page_number_alignment_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P049" and issue in {
        "lot_page_header_not_right_aligned",
        "lof_page_header_not_right_aligned",
        "lot_page_header_not_bold",
        "lof_page_header_not_bold",
    }:
        body = _p049_page_header_style_comment(issue, page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P050" and issue in {
        "lot_table_header_not_bold",
        "lof_figure_header_not_bold",
    }:
        body = _p050_left_bold_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P042" and issue in {
        "single_appendix_missing_title",
        "multiple_appendix_missing_letter",
    }:
        body = _p042_appendix_format_comment(issue, page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P033" and issue == "frontmatter_title_mismatch":
        body = _p033_frontmatter_title_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P051" and issue == "copyright_year_not_found":
        body = _p051_copyright_year_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    template = _ISSUE_TEMPLATES.get((rule_id, issue))
    if template is None:
        template = _RULE_FALLBACKS.get(rule_id)
        if template is None:
            issue_label = humanize_issue_type(issue).lower() if issue else "formatting"
            if rule_id in _SOURCE_RULE_IDS:
                body = (
                    f"This automated check found a possible {issue_label} issue "
                    f"at {_safe_location_label(safe_details)}."
                )
            else:
                body = (
                    f"This automated check found a possible {issue_label} issue "
                    f"on page {_safe_page_label(page)}."
                )
            return _finish_comment(body, rule_id=rule_id, issue_type=issue)
        body = _format_template(template, page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue)

    body = _format_template(template, page=page, details=safe_details)
    return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)


def resolve_suggested_fix_for_display(
    rule_id: str,
    issue_type: str = "",
    *,
    existing: str = "",
    float_number: str = "",
) -> str:
    """Resolve advice, retaining recorded R035 identity over older generic text."""
    if rule_id == "P035" and float_number.strip():
        numbered_fix = float_layout_suggested_fix(issue_type, float_number)
        if numbered_fix:
            return numbered_fix
    cleaned = sanitize_suggested_fix_for_web(rule_id, existing.strip())
    if cleaned:
        return cleaned
    return sanitize_suggested_fix_for_web(rule_id, _resolve_remediation(rule_id, issue_type))


# Inner labels that rule templates write before the generic review prefix is
# added. Stacked together ("Review needed: Problem: ...") they read as two
# labels, and "Problem:" contradicts a low-confidence card.
_STACKED_LEAD_IN_RE = re.compile(
    r"^Review needed:\s+(?:(?:Likely problem|Problem|Review needed):\s+)+"
)


def collapse_stacked_lead_in(comment: str) -> str:
    """Keep one lead-in label: ``Review needed: Problem: X`` becomes ``Review needed: X``.

    The confidence label shown with every finding carries the certainty, so
    the neutral review prefix is kept and the inner label is dropped. Text
    after the labels is unchanged.
    """
    return _STACKED_LEAD_IN_RE.sub(f"{REVIEW_PREFIX} ", comment, count=1)


def finalize_student_facing_comment_and_fix(
    rule_id: str,
    issue_type: str,
    comment: str,
    suggested_fix: str,
) -> tuple[str, str]:
    """Prepare comment/fix for display without repeated boilerplate or duplicate fix prose."""
    fix = resolve_suggested_fix_for_display(rule_id, issue_type, existing=suggested_fix)
    cleaned = collapse_stacked_lead_in(comment.replace(VERIFY_SUFFIX, "").strip())
    remediation = _resolve_remediation(rule_id, issue_type)
    if remediation and remediation in cleaned and remediation != cleaned:
        cleaned = cleaned.replace(remediation, "").strip()
    if fix and fix in cleaned and fix != cleaned:
        cleaned = cleaned.replace(fix, "").strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" .")
    return cleaned, fix


def _finish_comment(
    body: str,
    *,
    rule_id: str,
    issue_type: str = "",
    specific: bool = False,
) -> str:
    # Remediation is shown on its own Suggested fix line; VERIFY_SUFFIX is omitted
    # here because reports surface one global automated-review caveat instead.
    _ = specific
    _ = issue_type
    _ = rule_id
    return f"{REVIEW_PREFIX} {body}".strip()


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
