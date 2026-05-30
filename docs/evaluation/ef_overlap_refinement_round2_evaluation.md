# EF Overlap Refinement Round 2 Evaluation

- Date: 2026-05-29
- Selected target: `list_of_tables_figures_toc` coverage gap via TOC/List heading-variant detection
- Rules touched: `P018` and `P024` (shared TOC/List page detection path)

## Selected target and evidence

- `docs/evaluation/current_ef_comment_vs_tool_comparison.md` reports zero tool findings for `list_of_tables_figures_toc` on extractable-comment PDFs while EF comments include this category (Yin Haotian: 4).
- `docs/status/current_project_state_and_next_steps.md` lists EF category coverage expansion (including list/TOC cues) as a high-priority next bundle.
- Round 1 already addressed P013 noise; this round focuses on a remaining EF category miss.

## Implementation summary

Updated `src/njit_auditor/rules/pdf_toc_alignment.py`:

- Added normalized TOC/List heading variant handling for detection:
  - trailing punctuation (for example `TABLE OF CONTENTS.`)
  - continuation suffixes (for example `LIST OF TABLES (CONTINUED)`, `... CONTINUED`)
- Kept rule semantics unchanged; only expanded page-type recognition for already-scoped TOC/List checks.

## Tests added

Added synthetic regression tests in `tests/test_pdf_rules.py`:

- `test_p018_toc_heading_with_trailing_period_is_detected`
- `test_p024_lot_continued_heading_detected`

These verify the new heading variants are recognized and existing checks execute.

## Focused evaluation (round 2)

Generated outputs (gitignored):

- `data/evaluation/generated/ef_overlap_refinement_round2/`

Evaluated files:

- Cibaku Elson extractable-comment PDF
- Yin Haotian 2nd extractable-comment PDF
- Sebastian Fine clean baseline

Before baseline for comparison:

- `data/evaluation/generated/ef_overlap_refinement/*_audit_after.json` (post-round1 snapshot)

## Before/after counts (affected rules)

| File | P018 before | P018 after | P024 before | P024 after | `list_of_tables_figures_toc` category before | after |
|---|---:|---:|---:|---:|---:|---:|
| Cibaku Elson 1st review | 0 | 0 | 0 | 0 | 0 | 0 |
| Yin Haotian 2nd review | 0 | 0 | 0 | 0 | 0 | 0 |
| Sebastian Fine clean baseline | 2 | 2 | 0 | 0 | 2 | 2 |

## Overlap effect (measurable)

- Extractable-comment PDFs showed no count/page changes for P018/P024 in this round.
- Yin Haotian still has EF `list_of_tables_figures_toc` pages (4) with no corresponding tool findings.

Interpretation:

- The refinement increases robustness for TOC/List heading variants and protects against missed detection in common formatting variants.
- The current extractable-comment PDFs do not expose the variant pattern directly, so measurable overlap changes are not observed in this dataset.

## Clean baseline impact

- Sebastian baseline remained stable (`P018=2`, `P024=0`), indicating no new noise from this refinement.

## Limitations

- This round improves detection robustness but does not add new semantic checks for TOC/List content.
- Remaining `list_of_tables_figures_toc` misses likely require deeper entry extraction coverage (for example, multi-line entry continuation handling, split columns, or heading-page boundary logic).

## Next recommended task

- Implement a conservative extraction enhancement for TOC/List entries with wrapped lines or split text/page-number columns, then re-measure `list_of_tables_figures_toc` overlap on Yin Haotian pages (10, 32, 49, 94).
