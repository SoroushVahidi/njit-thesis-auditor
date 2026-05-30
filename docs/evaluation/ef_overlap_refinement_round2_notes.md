# EF Overlap Refinement Round 2 Notes

- Date: 2026-05-29
- Selected target: **list_of_tables_figures_toc false negatives via TOC/List heading variant detection**

## Evidence from current comparison/status docs

- `docs/evaluation/current_ef_comment_vs_tool_comparison.md` shows `list_of_tables_figures_toc` EF comments on Yin Haotian (4) while tool counts remain 0 in the extractable-comment comparison.
- `docs/status/current_project_state_and_next_steps.md` lists EF category coverage expansion as a high-priority next task and highlights TOC/list formatting cues as uncovered.
- Prior round addressed P013 noise; round 2 should target a remaining EF-coverage gap rather than additional P013 changes.

## Affected rules

- `P018` (`src/njit_auditor/rules/pdf_toc_alignment.py`)
- `P024` (`src/njit_auditor/rules/pdf_toc_list_formatting.py`) indirectly via shared TOC/List page detection

## Planned refinement

- Make TOC/List page detection robust to common heading variants:
  - trailing punctuation (e.g., `TABLE OF CONTENTS.`)
  - continuation suffixes (e.g., `LIST OF TABLES (CONTINUED)`, `TABLE OF CONTENTS CONTINUED`)
- Keep checks conservative; only expand heading normalization/detection, not rule semantics.

## Expected improvement

- Increase chances that P018/P024 run on legitimate TOC/List continuation pages.
- Improve potential overlap for `list_of_tables_figures_toc` without broad noisy behavior changes.

## Risk/noise considerations

- Low risk: this change only broadens page-type recognition for already-scoped TOC/List rules.
- Guardrail: continue requiring explicit TOC/List base heading phrases to avoid triggering on unrelated body pages.
