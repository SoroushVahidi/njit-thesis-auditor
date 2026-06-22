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
        "content",
        "label",
        "ref",
    }
)

_SOURCE_RULE_IDS = frozenset(
    {"P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"}
)

_ISSUE_TEMPLATES: dict[tuple[str, str], str] = {
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
        "but this section is expected to use {expected_style}. Update the "
        "page-numbering style for this section."
    ),
    ("P028", "uppercase_roman_on_frontmatter_page"): (
        "Problem: The page number on page {page} appears to use {observed_style}, "
        "but this section is expected to use {expected_style}. Update the "
        "page-numbering style for this section."
    ),
    ("P028", "roman_number_on_body_page"): (
        "Problem: The page number on page {page} appears to use {observed_style}, "
        "but this section is expected to use {expected_style}. Update the "
        "page-numbering style for this section."
    ),
    ("P029", "roman_sequence_gap"): (
        "Problem: The detected page number on page {page} does not appear to "
        "follow the expected numbering sequence. Observed: {observed_sequence}. "
        "Expected: {expected_sequence}. Renumber the affected pages so the "
        "sequence is correct."
    ),
    ("P029", "roman_sequence_repeat"): (
        "Problem: The detected page number on page {page} does not appear to "
        "follow the expected numbering sequence. Observed: {observed_sequence}. "
        "Expected: {expected_sequence}. Renumber the affected pages so the "
        "sequence is correct."
    ),
    ("P029", "roman_sequence_decrease"): (
        "Problem: The detected page number on page {page} does not appear to "
        "follow the expected numbering sequence. Observed: {observed_sequence}. "
        "Expected: {expected_sequence}. Renumber the affected pages so the "
        "sequence is correct."
    ),
    ("P037", "roman_bio_sketch_not_iv"): (
        "Problem: The detected page number on page {page} does not appear to "
        "follow the expected numbering sequence. Observed: {observed_sequence}. "
        "Expected: {expected_sequence}. Renumber the affected pages so the "
        "sequence is correct."
    ),
    ("P037", "roman_section_wrong_value"): (
        "Problem: The detected page number on page {page} does not appear to "
        "follow the expected numbering sequence. Observed: {observed_sequence}. "
        "Expected: {expected_sequence}. Renumber the affected pages so the "
        "sequence is correct."
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
        "Unusually large spacing (about {largest_gap_pt}pt) was detected between "
        "lines on page {page}. Body text should be double-spaced with consistent "
        "spacing throughout."
    ),
    ("P016", "excessive_paragraph_gap"): (
        "Unusually large spacing (about {largest_gap_pt}pt) was detected between "
        "paragraphs on page {page}. Paragraph spacing should be consistent with "
        "double-spaced body text."
    ),
    ("P016", "suspicious_heading_blank_gap"): (
        "An unusually large blank gap (about {largest_gap_pt}pt) was detected just "
        "before a heading on page {page}. Verify this is intentional heading "
        "spacing and not an extra blank line or page-break artifact."
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
    # --- P017 figure/table captions ---
    ("P017", "unexpected_terminal_period"): (
        "Likely problem: A {caption_type} caption on page {page} appears to end "
        "with a terminal period where NJIT expects no ending punctuation for "
        "this caption type. Remove the trailing period unless the caption is "
        "written as a full sentence that requires one."
    ),
    ("P017", "missing_terminal_punctuation"): (
        "Likely problem: A {caption_type} caption on page {page} appears to "
        "be missing terminal punctuation where NJIT expects a period, question "
        "mark, or exclamation point. Add appropriate ending punctuation."
    ),
    ("P017", "possible_sentence_case_issue"): (
        "Likely problem: A {caption_type} caption on page {page} appears to use "
        "Title Case where sentence case may be expected. Review the caption "
        "capitalization against NJIT caption-style guidance for this float type."
    ),
    ("P017", "possible_title_case_issue"): (
        "Likely problem: A {caption_type} caption on page {page} appears to "
        "violate title-case expectations. Capitalize the first word, last word, "
        "and major words of four or more letters."
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
    # --- P021 abstract word count ---
    ("P021", "abstract_word_count_exceeded"): (
        "Problem: The abstract appears to contain {word_count} words, which "
        "exceeds the {limit}-word limit for a {degree_label} thesis. Shorten "
        "the abstract before submission."
    ),
    # --- P024 TOC/LoT/LoF capitalization and punctuation ---
    ("P024", "toc_level_capitalization"): (
        "Likely problem: A Table of Contents entry on page {page} may not "
        "follow NJIT capitalization rules for its heading level (Level 1 = ALL "
        "CAPS, Level 2 = Title Case). Correct the entry capitalization."
    ),
    ("P024", "list_of_tables_title_case"): (
        "Likely problem: A List of Tables entry on page {page} may not use "
        "Title Case or may include terminal punctuation. Table titles in the "
        "List of Tables should use Title Case with no ending period."
    ),
    ("P024", "list_of_figures_sentence_case"): (
        "Likely problem: A List of Figures entry on page {page} may not use "
        "sentence case. Figure descriptions in the List of Figures should "
        "begin with a capital letter and use sentence case."
    ),
    ("P024", "unexpected_terminal_punctuation"): (
        "Likely problem: A TOC or list entry on page {page} ends with terminal "
        "punctuation where NJIT expects none for that list type. Remove the "
        "trailing period unless the entry is intentionally written as a sentence."
    ),
    # --- P025 title page graduation month ---
    ("P025", "title_page_graduation_month_invalid"): (
        "Problem: The graduation month on the title page may not match the "
        "expected NJIT format. NJIT expects a spelled-out month and year on "
        "the title page (for example, 'May 2025'). Correct the graduation date line."
    ),
    # --- P035 figure/table layout ---
    ("P035", "table_caption_not_above_body"): (
        "Likely problem: A table caption on page {page} does not appear above "
        "the table body. NJIT expects table captions to appear above the table."
    ),
    ("P035", "figure_caption_not_below_body"): (
        "Likely problem: A figure caption on page {page} does not appear below "
        "the figure body. NJIT expects figure captions to appear below the figure."
    ),
    ("P035", "table_body_not_centered"): (
        "Likely problem: A table body block on page {page} does not appear "
        "centered within the text area. Center the table within the page margins."
    ),
    ("P035", "figure_body_not_centered"): (
        "Likely problem: A figure body block on page {page} does not appear "
        "centered within the text area. Center the figure within the page margins."
    ),
    # --- P039 TOC hierarchy indentation ---
    ("P039", "toc_l2_not_indented_relative_to_l1"): (
        "Likely problem: A level-2 Table of Contents entry on page {page} does "
        "not appear indented to the right of its level-1 parent entry. Indent "
        "level-2 section entries relative to chapter entries."
    ),
    ("P039", "toc_l3_not_indented_relative_to_l2"): (
        "Likely problem: A level-3 Table of Contents entry on page {page} does "
        "not appear indented relative to its level-2 parent entry. Indent "
        "level-3 subsection entries further than level-2 entries."
    ),
    # --- P040 List of Figures punctuation ---
    ("P040", "lof_entry_missing_terminal_punctuation"): (
        "Problem: A List of Figures entry on page {page} appears to be missing "
        "terminal punctuation. Every figure description in the List of Figures "
        "should end with a period, question mark, or exclamation point."
    ),
    # --- P041 dedication header text ---
    ("P041", "dedication_top_margin_header_text"): (
        "Problem: Text was detected in the top margin area of the dedication "
        "page on page {page}. The dedication page should not have running "
        "headers or header text in the top margin."
    ),
    # --- P043 acknowledgements indentation ---
    ("P043", "acknowledgements_first_paragraph_indented"): (
        "Problem: The first paragraph on the Acknowledgements page (page "
        "{page}) appears to be indented. NJIT requires the first paragraph "
        "to begin flush with the left margin."
    ),
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): (
        "Problem: A later paragraph on the Acknowledgements page (page {page}) "
        "appears flush-left where NJIT expects a first-line indent. Indent "
        "each paragraph after the first."
    ),
    # --- P044 abstract indentation ---
    ("P044", "abstract_first_paragraph_indented"): (
        "Problem: The first paragraph on the Abstract page (page {page}) "
        "appears to be indented. NJIT requires the first abstract paragraph "
        "to begin flush with the left margin."
    ),
    ("P044", "abstract_subsequent_paragraph_not_indented"): (
        "Problem: A later paragraph on the Abstract page (page {page}) appears "
        "flush-left where NJIT expects a first-line indent. Indent each "
        "abstract paragraph after the first."
    ),
    # --- P053/P054 list terminal periods ---
    ("P053", "lot_entry_has_terminal_period"): (
        "Problem: A List of Tables entry on page {page} ends with a terminal "
        "period. Remove the trailing period — table titles in the List of "
        "Tables should not end with punctuation."
    ),
    ("P054", "toc_entry_has_terminal_period"): (
        "Problem: A Table of Contents entry on page {page} ends with a terminal "
        "period. Remove the trailing period — TOC entries should not end with "
        "punctuation."
    ),
    # --- P055 misplaced list entries ---
    ("P055", "lot_entry_is_figure"): (
        "Problem: A List of Tables entry on page {page} appears to describe a "
        "figure rather than a table. Move this entry to the List of Figures."
    ),
    ("P055", "lof_entry_is_table"): (
        "Problem: A List of Figures entry on page {page} appears to describe a "
        "table rather than a figure. Move this entry to the List of Tables."
    ),
    # --- P058/P060 TOC ordering ---
    ("P058", "toc_page_numbers_not_nondecreasing"): (
        "Problem: Table of Contents page numbers on page {page} do not appear "
        "in ascending order. Reorder entries so listed page numbers increase "
        "from top to bottom."
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
    # --- P068 approval page structure ---
    ("P068", "approval_page_advisor_role_label_missing"): (
        "Problem: The Approval Page on page {page} lists {role_label_count} "
        "committee role label(s), but none of them is a recognizable advisor role "
        "label (for example, 'Dissertation Advisor' or 'Major Professor'). Add the "
        "required advisor role label."
    ),
    ("P068", "approval_page_signature_blocks_sparse"): (
        "Problem: The Approval Page on page {page} has {signature_date_indicator_count} "
        "signature/date line(s) for {role_label_count} committee role label(s), but "
        "at least {required_indicator_count} are expected. Add a signature line and "
        "a date line for each committee member."
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
    ("P021", "abstract_word_count_exceeded"): "",
    ("P025", "title_page_graduation_month_invalid"): (
        "Correct the graduation month and year on the title page to use a "
        "spelled-out month and four-digit year."
    ),
    ("P017", "unexpected_terminal_period"): "",
    ("P017", "missing_terminal_punctuation"): "",
    ("P017", "possible_sentence_case_issue"): "",
    ("P017", "possible_title_case_issue"): "",
    ("P024", "toc_level_capitalization"): "",
    ("P024", "list_of_tables_title_case"): "",
    ("P024", "list_of_figures_sentence_case"): "",
    ("P024", "unexpected_terminal_punctuation"): "",
    ("P035", "table_caption_not_above_body"): "",
    ("P035", "figure_caption_not_below_body"): "",
    ("P035", "table_body_not_centered"): "",
    ("P035", "figure_body_not_centered"): "",
    ("P041", "dedication_top_margin_header_text"): "",
    ("P043", "acknowledgements_first_paragraph_indented"): "",
    ("P043", "acknowledgements_subsequent_paragraph_not_indented"): "",
    ("P044", "abstract_first_paragraph_indented"): "",
    ("P044", "abstract_subsequent_paragraph_not_indented"): "",
    ("P053", "lot_entry_has_terminal_period"): "",
    ("P054", "toc_entry_has_terminal_period"): "",
    ("P055", "lot_entry_is_figure"): "",
    ("P055", "lof_entry_is_table"): "",
    ("P068", "approval_page_advisor_role_label_missing"): "",
    ("P068", "approval_page_signature_blocks_sparse"): "",
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
        expected_heading=details.get("expected_heading", "") or "the required heading",
        toc_page=details.get("toc_page", "") or "unknown",
        substantial_line_count=details.get("substantial_line_count", "") or "0",
        observed_location=observed_location,
        observed_style=observed_style,
        expected_style=expected_style,
        observed_sequence=observed_sequence,
        expected_sequence=expected_sequence,
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
            f"of page {page_label}. This is an internal verification signal "
            "and is not counted as a problem unless another finding reports a "
            "specific defect."
        )
    if position_type in {"top_center", "top_right", "other"}:
        return (
            "Problem: The page number on page "
            f"{page_label} appears at {_safe_position_label(position_type)}, "
            "but NJIT expects the page number in the required bottom "
            "position. Move the page number to the required bottom position."
        )
    return (
        f"A page-number-like token was detected on page {page_label}. This "
        "is an internal verification signal and is not counted as a problem "
        "unless another finding reports a specific defect."
    )


_TITLE_CASE_REASON_TEXT: dict[str, str] = {
    "first_word_requires_capital": "the first word is not capitalized",
    "word_after_separator_requires_capital": (
        "a word after a colon, dash, or similar separator is not capitalized"
    ),
    "major_word_requires_capital": "a major word (4+ letters) is not capitalized",
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
        rule_text = "NJIT requires table titles to use Title Case"
    else:
        subject = "Level 2 heading"
        rule_text = "NJIT requires Level 2 headings (e.g. 1.1, 1.2) to use Title Case"
    return (
        f"Possible title-case issue in a {subject} on page {page_label}: "
        f"{reason_text}. {rule_text} (capitalize the first word, last word, "
        "and all major words of 4+ letters)."
    )


def _p024_toc_level_comment(*, page: int | None, details: dict[str, str]) -> str:
    """Build the P024 toc_level_capitalization comment body.

    Level 1 and Level 2 TOC entries are checked against different
    capitalization rules (ALL CAPS vs. Title Case); branching on the
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


def _p015_paragraph_descriptor(issue_type: str, details: dict[str, str]) -> str:
    if issue_type == "unexpected_opening_indent":
        return "the opening paragraph"
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
            "to have an unintended first-line indent where NJIT expects a flush-left "
            "opening paragraph. Remove the extra indent or confirm this is a permitted "
            "exception such as a block quote or list item."
        )
    return (
        f"Likely problem: {descriptor.capitalize()} on page {page_label} appears to "
        "start flush-left where NJIT expects a first-line indent for a non-opening "
        "paragraph. Add the required first-line indent or confirm this paragraph is "
        "meant to begin a new block."
    )


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


def _p011_margin_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    side = _margin_side_label(details)
    if side == "required page margin":
        return (
            f"Likely problem: Some content on page {page_label} appears too close to or "
            "beyond a required page margin. The auditor could not determine the exact "
            "margin side from the available metadata. NJIT formatting expects body "
            "content to remain inside the required page margins. Review tables, figures, "
            "long lines, indentation, headers, and footers on this page."
        )
    return (
        f"Likely problem: Content on page {page_label} appears to cross the required "
        f"{side} boundary. NJIT formatting expects body content to remain inside the "
        "required page margins. Review the highlighted area if available, or inspect "
        "tables, figures, long lines, indentation, headers, and footers on this page."
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
        "show where a problem is located. Before final submission, accept or reject "
        "any reviewer changes, remove comments, highlights, or markup from the PDF, "
        "and upload a clean copy."
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
        or "Times New Roman or an accepted Times-compatible font"
    )
    if observed:
        return (
            "Likely problem: Body text on page "
            f"{page_label} appears to use font family {observed}. "
            "NJIT expects body text to use "
            f"{expected}. Update the source document's body-text style if this text is "
            "part of the main body."
        )
    return (
        f"Likely problem: Some body-text-like spans on page {page_label} appear not to "
        "match NJIT's expected font family. The auditor could not extract a precise "
        f"observed font value for this card. NJIT expects body text to use {expected}. "
        "Review the explanation and confirm whether the flagged text is body text or "
        "another text role."
    )


_P032_ENTRY_KIND_LABELS: dict[str, str] = {
    "table_entry": "List of Tables entry",
    "figure_entry": "List of Figures entry",
    "toc_level_1": "Table of Contents chapter/appendix entry",
    "toc_level_2": "Table of Contents entry",
    "toc_level_3": "Table of Contents sub-entry",
}


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
        f"Likely problem: A wrapped (continuation) line of a {entry_label} on page "
        f"{page_label} has an unusually large internal gap{gap_clause}. Continuation "
        "lines that belong to the same entry should sit close together, not with "
        "extra blank space between them."
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
        f"Likely problem: Biographical Sketch degree entries on page {page_label} may "
        "not be listed most-recent-first: the candidate years found (in listed order) "
        f"run from {first_year} to {last_year}, with {inversion_count} {place_noun} "
        "where a later-listed entry's year is more recent than the entry just before "
        "it. NJIT requires postgraduate degrees to be listed from most recent to "
        "oldest."
    )


def _p067_publication_order_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    first_year = details.get("first_entry_year", "").strip() or "an earlier year"
    last_year = details.get("last_entry_year", "").strip() or "a later year"
    inversion_count = details.get("inversion_count", "").strip() or "at least one"
    place_noun = "place" if inversion_count == "1" else "places"
    return (
        "Likely problem: Biographical Sketch publication/presentation entries on page "
        f"{page_label} may not be listed most-recent-first: the comparable entry years "
        f"found (in listed order) run from {first_year} to {last_year}, with "
        f"{inversion_count} {place_noun} where a later-listed entry's year is more "
        "recent than the entry just before it. NJIT requires publications/"
        "presentations to be listed from most recent to oldest."
    )


def _p045_hanging_indent_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    block_count = details.get("multi_line_block_count", "").strip()
    threshold = details.get("hanging_indent_threshold_points", "").strip()
    count_clause = f" ({block_count} multi-line entries checked)" if block_count else ""
    threshold_clause = f" by at least {threshold}pt" if threshold else ""
    return (
        "Likely problem: None of the publication/presentation entries on the "
        f"Biographical Sketch page (page {page_label}) use hanging indentation"
        f"{count_clause}: no continuation line is indented{threshold_clause} "
        "relative to its entry's first line. NJIT requires publication/"
        "presentation entries to use hanging indentation (first line flush left, "
        "continuation lines indented)."
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
        "Likely problem: Two consecutive publication/presentation entries on the "
        f"Biographical Sketch page (page {page_label}) appear to lack the required "
        f"gap between them{gap_clause}. NJIT requires a blank-line gap between "
        "publication/presentation entries."
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
        f"Likely problem: A {block_label} on the Biographical Sketch page (page "
        f"{page_label}) has an internal line gap that looks double-spaced rather "
        f"than single-spaced{gap_clause}. NJIT requires bullet/list items in the "
        "Biographical Sketch to be single-spaced internally."
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
            f"Likely problem: The {section_label} page (page {page_label}) appears "
            f"to be missing the expected '{expected_left}' column header label. "
            f"NJIT requires a '{expected_left}' column header directly above the "
            "entry numbers."
        )
    if issue_type == "missing_page_column_header":
        return (
            f"Likely problem: The {section_label} page (page {page_label}) appears "
            f"to be missing the expected '{expected_page}' column header label. "
            f"NJIT requires a '{expected_page}' column header directly above the "
            "page-number column."
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
        f"appear to be aligned in a single consistent left column{range_clause}. "
        f"NJIT requires all {entry_noun} numbers in the {section_label} to line up "
        "vertically at the same left position."
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
        f"do not appear to be aligned in a single consistent right column"
        f"{measure_clause}. NJIT requires all page numbers in the {section_label} "
        "to line up vertically at the same right-hand position."
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
            f"(page {page_label}) does not appear to be right-aligned with the "
            f"page-number column{measure_clause}. NJIT requires the 'Page' header to "
            "be right-aligned directly over the page numbers."
        )
    verify_clause = _font_metadata_clause(details)
    return (
        f"Likely problem: The 'Page' column header on the {section_label} page "
        f"(page {page_label}) does not appear to be bold.{verify_clause} NJIT "
        "requires the 'Page' column header to be formatted in bold."
    )


def _p050_left_bold_comment(*, page: int | None, details: dict[str, str]) -> str:
    page_label = _safe_page_label(page)
    section_label = _lot_lof_section_label(details)
    header_word = "Table" if _lot_lof_entry_noun(details) == "table" else "Figure"
    verify_clause = _font_metadata_clause(details)
    return (
        f"Likely problem: The '{header_word}' column header on the {section_label} "
        f"page (page {page_label}) does not appear to be bold.{verify_clause} NJIT "
        f"requires the '{header_word}' column header to be formatted in bold."
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
            f"Likely problem: The Table of Contents on page {page_label} lists a "
            "single appendix entry that does not appear to include a title after "
            f"'APPENDIX'. NJIT requires a single-appendix entry to follow the "
            f"pattern '{expected_pattern}'. Check this Table of Contents entry "
            "and add the missing appendix title."
        )

    expected_pattern = details.get("expected_pattern", "").strip() or "APPENDIX <A-Z>"
    position_clause = _p042_entry_position_clause(details)
    return (
        f"Likely problem: The Table of Contents on page {page_label} lists "
        f"multiple appendix entries, but one entry{position_clause} does not "
        "appear to include a letter identifier. NJIT requires every appendix "
        f"entry to follow the pattern '{expected_pattern}' (e.g. 'APPENDIX A,' "
        "'APPENDIX B') when there is more than one appendix. Check this Table of "
        "Contents entry and add the missing letter."
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
    if rule_id in _SOURCE_RULE_IDS and not issue:
        issue = derive_source_issue_type(rule_id, safe_details)

    if rule_id == "P013" and issue == "page_number_candidate":
        body = _p013_candidate_comment(page=page, details=safe_details)
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

    if rule_id == "P011" and issue == "margin_boundary_violation":
        body = _p011_margin_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P012" and issue == "pdf_annotation_detected":
        body = _p012_annotation_comment(page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)

    if rule_id == "P015" and issue in {
        "unexpected_opening_indent",
        "missing_later_indent",
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

    if rule_id == "P045" and issue == "biosketch_publication_missing_hanging_indent":
        body = _p045_hanging_indent_comment(page=page, details=safe_details)
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
            return _finish_comment(body, rule_id=rule_id, issue_type=issue)
        body = _format_template(template, page=page, details=safe_details)
        return _finish_comment(body, rule_id=rule_id, issue_type=issue)

    body = _format_template(template, page=page, details=safe_details)
    return _finish_comment(body, rule_id=rule_id, issue_type=issue, specific=True)


def _finish_comment(
    body: str,
    *,
    rule_id: str,
    issue_type: str = "",
    specific: bool = False,
) -> str:
    remediation = _resolve_remediation(rule_id, issue_type)
    parts = [f"{REVIEW_PREFIX} {body}"]
    if remediation and remediation not in body:
        parts.append(remediation)
    if not specific:
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
