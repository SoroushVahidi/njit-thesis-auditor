# EF Overlap-Driven Refinement Evaluation

- Date: 2026-05-29
- Target selected from EF overlap comparison: **P013 noise reduction**
- Scope: reporting/triage refinement only (candidate detection logic preserved)

## Comparison evidence

From `docs/evaluation/current_ef_comment_vs_tool_comparison.md`:

- `page_numbering` is a highest-volume category in both extractable-comment PDFs.
- Tool-only coverage is high, while overlap remains narrow in category-level matching.
- Recommended next work explicitly calls for noise-reduction/grouping of high-volume categories (`page_numbering`, `font_format`).

## Implementation summary

Changed `src/njit_auditor/rules/pdf_page_numbers.py`:

- P013 now emits one page-level warning per page with candidates (instead of one warning per candidate line).
- Added structured detail fields for triage:
  - `issue_type=page_number_candidate`
  - `candidate_count_on_page`
  - `candidate_sample`
  - `position_type`
  - `number_style`
  - `observed_summary`
  - `confidence`
- Underlying candidate detector remains unchanged; dependent sequence/regime checks continue to use raw candidates.

Tests:

- Added synthetic coverage in `tests/test_pdf_rules.py`:
  - verifies page-level grouping behavior
  - verifies new structured P013 detail fields

## Focused evaluation setup

Generated under gitignored path:

- `data/evaluation/generated/ef_overlap_refinement/`

Files run:

- Cibaku Elson 1st review (extractable EF comments)
- Yin Haotian 2nd review (extractable EF comments)
- Sebastian Fine clean baseline

## Before/after counts (affected metrics)

| File | P013 before | P013 after | Delta | Total findings before | Total findings after | Delta |
|---|---:|---:|---:|---:|---:|---:|
| Cibaku Elson 1st review | 99 | 95 | -4 | 321 | 317 | -4 |
| Yin Haotian 2nd review | 113 | 104 | -9 | 349 | 340 | -9 |
| Sebastian Fine clean baseline | 27* | 25 | -2 | — | — | — |

\* Baseline "before" from prior documented snapshot (`docs/evaluation/current_auditor_after_p014_p029_evaluation.md`).

## Overlap effect (measurable)

- **P013 page coverage unchanged** on extractable-comment PDFs:
  - Cibaku: 94 P013 pages before/after
  - Yin Haotian: 103 P013 pages before/after
- **P013 page overlap with EF-comment pages unchanged**:
  - Cibaku: 40 pages before/after
  - Yin Haotian: 42 pages before/after

Interpretation:

- This refinement reduces repeated warnings while preserving page-level coverage and EF-overlap behavior.
- It improves actionability without reducing detection footprint.

## Clean baseline impact

- Sebastian Fine P013 count reduced from 27 to 25, with no broad behavior change.
- Result is consistent with intended noise reduction on pages containing multiple candidate tokens.

## Limitations

- This does not add new EF category coverage; it only improves triage noise in a high-volume category.
- Semantic/manual EF feedback categories remain out of deterministic scope.

## Next recommended task

- Apply the same evidence-driven triage refinement pattern to `font_format` high-volume output (P026), or implement targeted deterministic coverage for high-frequency uncaptured EF categories (`list_of_tables_figures_toc`, `committee_approval_page` cues) where feasible.
