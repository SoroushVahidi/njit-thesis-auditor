# Phase 2: Ester Comment Categories vs Tool Findings (Private-Safe)

Date: 2026-05-21  
Source PDF: `Yin_Haotian_Second_R_with_EF_Feedback.pdf`

## Scope

This is a deterministic, category-level comparison between:

- extracted reviewer annotation comments, and
- automatic PDF audit findings on the clean (annotation-removed) copy.

No semantic AI matching is used. No dissertation body text is included.

## Input Counts

- Extracted annotations/comments: 65
- Clean PDF audit findings (category-level):
  - `margin_or_overflow` (`P011`): 33
  - `page_numbering` (`P013`): 113
  - `annotations` (`P012`): 0 (as expected on clean copy)

## Comment Category Counts

- `unclear_or_other`: 35
- `indentation`: 11
- `spacing_blank_lines`: 7
- `heading_title`: 6
- `table_format`: 6
- `capitalization_case`: 3
- `punctuation`: 4
- `references_citations`: 4
- `list_of_tables_figures_toc`: 4
- `committee_approval_page`: 2
- `acknowledgements`: 1
- `margin_or_overflow`: 1

## High-Level Overlap

Currently detected by the tool and also present in comments:

- `margin_or_overflow`

Detected by the tool but not a dominant comment category:

- `page_numbering` (high volume from candidate detection)

Comment categories not yet covered by current PDF rules:

- `indentation`
- `spacing_blank_lines`
- `heading_title`
- `table_format`
- `capitalization_case`
- `punctuation`
- `references_citations`
- `list_of_tables_figures_toc`
- `committee_approval_page`
- `acknowledgements`

## Recommended Next Rules

1. Named front-matter heading checks (title/case/expected section names).
2. Paragraph indentation consistency checks in key sections.
3. Spacing/blank-line checks around headings, lists, and captions.
4. Table/list title case and terminal punctuation checks.
5. TOC/List of Tables/List of Figures alignment and formatting checks.
6. Committee approval page structural checks (presence/order/signature layout cues).

## Privacy Notes

- Generated detailed artifacts remain under ignored paths:
  - `data/evaluation/generated/ester_yin_second_review/`
- This committed summary includes category counts only, not full annotation text.
