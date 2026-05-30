# Current EF Comment-vs-Tool Comparison (P001-P029)

- Date: 2026-05-29
- Auditor scope: current P001-P029 rules on `main` baseline (`559814d`)
- Comparison mode: high-level page/category overlap only (no semantic text matching)

## 1. Purpose

Compare current auditor findings against extractable EF comments for the two PDFs where comments are machine-extractable, using deterministic page/category overlap.

Generated artifacts (gitignored):

- `data/evaluation/generated/current_ef_comment_comparison/*_audit.{json,md}`
- `data/evaluation/generated/current_ef_comment_comparison/*_comments.{json,md}`
- `data/evaluation/generated/current_ef_comment_comparison/current_ef_comment_overlap_summary.{json,md}`

## 2. Dataset

Included in EF comment-vs-tool comparison:

- `250218 Cibaku Elson First Review.pdf` (extractable comments)
- `Yin_Haotian_Second_R_with_EF_Feedback.pdf` (extractable comments)

Excluded from EF comment matching:

- `260415 Yin H _2nd_review with EF Comments.pdf` (flattened comments; none extractable)
- `Yin_H_4th_Review_with_EF_comments_compressed.pdf` (flattened/compressed; none extractable)
- Clean baseline (`Sebastian.Fine...`) excluded from EF-comment overlap because it has no EF comments.

## 3. Per-file summary

| File | EF comments | Tool findings | Pages with EF comments | Pages with tool findings | Pages with both | EF-only pages | Tool-only pages |
|---|---:|---:|---:|---:|---:|---:|---:|
| Cibaku Elson 1st review | 78 | 321 | 42 | 98 | 42 | 0 | 56 |
| Yin Haotian 2nd review | 65 | 349 | 44 | 108 | 44 | 0 | 64 |

Notes:

- All EF-comment pages are detected by at least one tool finding in both files (EF-only pages = 0).
- Tool findings cover many additional pages beyond EF-comment pages, largely from high-volume heuristic checks.

## 4. Category comparison

### EF comment category counts

| Category | Cibaku | Yin Haotian |
|---|---:|---:|
| unclear_or_other | 53 | 35 |
| indentation | 2 | 11 |
| spacing_blank_lines | 0 | 7 |
| heading_title | 11 | 6 |
| table_format | 1 | 6 |
| figure_format | 2 | 0 |
| references_citations | 5 | 4 |
| list_of_tables_figures_toc | 0 | 4 |
| capitalization_case | 9 | 3 |
| committee_approval_page | 3 | 2 |
| margin_or_overflow | 0 | 1 |
| acknowledgements | 1 | 1 |

### Tool finding category counts

| Category | Cibaku | Yin Haotian |
|---|---:|---:|
| page_numbering | 115 | 128 |
| font_format | 92 | 103 |
| annotations | 78 | 65 |
| margin_or_overflow | 21 | 33 |
| indentation | 5 | 13 |
| spacing_blank_lines | 7 | 6 |
| capitalization_case | 3 | 3 |
| heading_title | 1 | 1 |
| list_of_tables_figures_toc | 0 | 0 |
| references_citations | 0 | 0 |
| committee_approval_page | 0 | 0 |

### Category overlap and gaps (page-based)

- **Cibaku:** no positive page-level overlap in the shared comparison category set; EF comments are concentrated in categories not yet directly modeled (`references_citations`, `committee_approval_page`) or in manual/semantic feedback (`unclear_or_other`).
- **Yin Haotian:** positive page-level overlap appears in:
  - `indentation` (2 pages overlap)
  - `margin_or_overflow` (1 page overlap)
- **Tool-strong/high-volume areas:** `page_numbering`, `font_format`, and `margin_or_overflow`.
- **Tool-weak or uncovered areas vs EF comments:** `references_citations`, `committee_approval_page`, `list_of_tables_figures_toc`, and many `heading_title`/`table_format` feedback items that are semantic/editorial rather than strict formatting signals.

## 5. Interpretation

- Current overlap is strongest for mechanical layout signals (`indentation`, limited `margin_or_overflow`), especially on Yin Haotian.
- The largest false-negative area relative to EF feedback is semantic/manual feedback grouped into `unclear_or_other`, plus categories that do not yet have dedicated deterministic rules (`references_citations`, `committee_approval_page`).
- The largest high-volume tool outputs remain `page_numbering` and `font_format`, which provide broad coverage but produce many pages without EF comments.
- Best alignment today comes from rules tied to direct geometry/text-structure constraints (indentation/margin) rather than content-level editorial judgment.
- A substantial portion of EF comments remain uncaptured by design because they require semantic interpretation, policy judgment, or cross-section editorial consistency checks.

## 6. Recommended next work

1. Add noise-reduction/grouping for high-volume categories (`page_numbering`, `font_format`) to improve reviewer actionability.
2. Add targeted deterministic checks for currently uncovered but frequent EF categories where feasible (for example, committee page structure cues and list/TOC formatting cues).
3. Expand EF-commented evaluation set with additional extractable PDFs to stabilize overlap metrics across document styles.
4. Keep semantic/manual EF feedback explicitly out-of-scope for deterministic rule claims, and continue reporting it as manual-review-required.
