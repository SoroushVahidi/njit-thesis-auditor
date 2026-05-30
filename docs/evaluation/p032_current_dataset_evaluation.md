# P032 Current Dataset Evaluation

- **Date:** 2026-05-30 (refreshed after PR #59)
- **Current baseline commit:** `b0d4471` (post–PR #59 split-page-number fix)
- **Auditor scope:** P001–P032 (P032 only reported here)
- **Generated artifacts (gitignored):**
  - Original run (PR #58): `data/evaluation/generated/p032_evaluation/`
  - Post–PR #59 rerun: `data/evaluation/generated/p032_evaluation_after_split_page_number_fix/`

## 1. Purpose and scope

Evaluate the conservative P032 wrapped-entry internal-spacing rule on the repository’s
documented evaluation PDF set identified in
`data/processed/evaluation_data_manifest.json`.

This document tracks **two evaluation snapshots**:

1. **Before PR #59** (commit `b700b94`, PR #58) — first current-dataset evaluation.
2. **After PR #59** (commit `b0d4471`) — rerun after the split-page-number false-positive
   refinement.

Reporting is **aggregate-only**. No dissertation body text is quoted. No generated audit
outputs are committed.

Evaluated inputs match the five-PDF full-evaluation set used for P030/P031, excluding the
rule-matrix XLSX and archive-only materials not verified locally.

## 2. Evaluation history

| Milestone | Commit | Yin H 4th P032 count | Outcome |
|---|---|---:|---|
| PR #58 initial evaluation | `b700b94` | 3 (page 15, LoF) | Documented in this file (original run) |
| PR #59 investigation | `b0d4471` | — | Likely false positives; intervening page-number guard |
| PR #59 post-fix rerun | `b0d4471` | **0** | Confirmed by re-run (this refresh) |

See `docs/evaluation/p032_yin_h_4th_page15_investigation.md` for the structural explanation
(orphan page-number lines between entry rows bridged continuation lines to the next entry).

## 3. Current results (after PR #59)

| File label | TOC/List pages | Wrap pairs | P032 before PR #59 | P032 after PR #59 | Pages after PR #59 | Notes |
|---|---:|---:|---:|---:|---|---|
| Cibaku Elson 1st review | 0 | 0 | 0 | 0 | — | No TOC/List pages detected |
| Yin H 2nd review (flattened) | 0 | 0 | 0 | 0 | — | No TOC/List pages detected |
| Yin Haotian 2nd review | 0 | 0 | 0 | 0 | — | No TOC/List pages detected |
| Yin H 4th review (compressed) | 7 | 72 | **3** | **0** | — | Was LoF p.15 only; resolved by PR #59 |
| Sebastian Fine clean baseline | 3 | 0 | 0 | 0 | — | Single-page TOC/LoT/LoF; no wrap pairs |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

**Total P032 findings after PR #59:** **0** across all five evaluated PDFs.

### Yin H 4th wrap-pair note (privacy-safe)

Before PR #59, **75** likely wrap pairs were detected on Yin H 4th (**72** within the
1.7× line-height threshold, **3** flagged). After PR #59, **72** wrap pairs are detected and
**none** are flagged — the three former pairs are no longer treated as wrap continuations
because a page-number-only line sits between the two entry-region lines.

## 4. Prior findings detail (before PR #59 only)

All three pre-fix findings used `issue_type: wrapped_entry_internal_spacing`,
`section_type: list_of_figures`, `entry_kind: figure_entry`, and `confidence: high` on
**page 15** only:

| Page | Observed gap (pt) | Expected max gap (pt) | Line height (pt) |
|---:|---:|---:|---:|
| 15 | 32.3 | 20.4 | 12.0 |
| 15 | 38.5 | 20.4 | 12.0 |
| 15 | 38.8 | 20.4 | 12.0 |

These counts are **historical**; the post–PR #59 rerun reports **0** P032 findings on this file.

## 5. Structural context (privacy-safe)

TOC/List pages detected per file (page numbers only); unchanged between runs:

| File label | table_of_contents | list_of_tables | list_of_figures |
|---|---|---|---|
| Cibaku Elson 1st review | — | — | — |
| Yin H 2nd review (flattened) | — | — | — |
| Yin Haotian 2nd review | — | — | — |
| Yin H 4th review (compressed) | 11, 12, 13 | 14 | 15, 17, 18 |
| Sebastian Fine clean baseline | 9 | 11 | 12 |

Page counts: Cibaku 99; Yin H 2nd flat 108; Yin Haotian 2nd 108; Yin H 4th 137;
Sebastian Fine 29.

## 6. Interpretation (current behavior)

**Overall:** After PR #59, P032 reports **0 findings on all five evaluated PDFs**, including
Yin H 4th compressed where PR #58 had reported 3 findings on List of Figures page 15.

**Zero-finding files do not prove compliance.**

- In three EF-commented PDFs, the shared TOC/List heading detector found **no qualifying
  pages**, so P032 had no section context to evaluate (same detection gap as P030/P031).
- On **Sebastian Fine clean baseline**, three single-page TOC/LoT/LoF sections were detected
  but **no likely wrapped-entry pairs** were classified; P032 correctly remained silent.

**PR #59 impact:** The Yin H 4th page-15 warnings were investigated as **likely false
positives** from split page-number rows between separate list entries, not as confirmed
excessive internal wrap spacing. The post-fix rerun supports that conclusion at the automated
layer; manual visual review is still outside this evaluation scope.

**Usefulness vs noise:** P032 remains **selective** on this small dataset — it stays silent
on four files and, after refinement, does not flag the previously noisy Yin H 4th page-15
cases. True wrapped-entry spacing defects may still exist but were not observed in this
aggregate rerun.

## 7. Limitations

- Heuristic PDF-only partial coverage for Q053–Q055, Q066–Q067, Q076–Q078.
- Wrap grouping and intervening page-number detection depend on text-layer geometry; compressed
  or flattened PDFs may decompose lines differently.
- Three EF PDFs had no detected TOC/List pages; P032 cannot assess them.
- Wrap-pair and P032 counts are in gitignored summary JSON only (see paths above).
- Sebastian Fine PDF extracted locally from the tracked ZIP; not committed.
- Pre–PR #59 counts are preserved for history; current behavior is defined by the post–PR #59
  rerun at commit `b0d4471`.

## 8. Related docs

- Yin H 4th page-15 investigation: `docs/evaluation/p032_yin_h_4th_page15_investigation.md`
- Synthetic validation: `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md`
- P030 current-dataset evaluation: `docs/evaluation/p030_current_dataset_evaluation.md`
- P031 current-dataset evaluation: `docs/evaluation/p031_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
