# P031 Current Dataset Evaluation

- **Date:** 2026-05-30 (refreshed after PR #55)
- **Current baseline commit:** `e0f70f8ab6f8adecbafebea82ffa2611fe615c20`
- **Auditor scope:** P001–P031 (P031 only reported here)
- **Generated artifacts (gitignored):**
  - Original run (PR #54): `data/evaluation/generated/p031_evaluation/`
  - Post–PR #55 rerun: `data/evaluation/generated/p031_evaluation_after_header_band_fix/`

## 1. Purpose and scope

Evaluate the conservative P031 List of Tables/Figures column-header rule on the
repository’s documented evaluation PDF set identified in
`data/processed/evaluation_data_manifest.json`.

This document tracks **two evaluation snapshots**:

1. **Before PR #55** (commit `e0ebbd324f6c620ad57375466e887ce858c368e2`, PR #54) — first
   current-dataset evaluation.
2. **After PR #55** (commit `e0f70f8ab6f8adecbafebea82ffa2611fe615c20`) — rerun after the
   header-band geometry refinement.

Reporting is **aggregate-only**. No dissertation body text is quoted. No generated audit
outputs are committed.

## 2. Evaluation history

| Milestone | Commit | Sebastian Fine P031 count | Outcome |
|---|---|---:|---|
| PR #54 initial evaluation | `e0ebbd3` | 2 (page 11) | Documented in this file (original run) |
| PR #55 investigation | `e0f70f8` | — | Likely false positives; header band extended upward |
| PR #55 post-fix rerun | `e0f70f8` | **0** | Confirmed by re-run (this refresh) |

See `docs/evaluation/p031_sebastian_clean_baseline_investigation.md` for the structural
explanation (labels present in text layer but outside the old header band).

## 3. Current results (after PR #55)

| File label | LoT/LoF pages detected | P031 before PR #55 | P031 after PR #55 | Pages after PR #55 | Notes |
|---|---:|---:|---:|---|---|
| Cibaku Elson 1st review | 0 | 0 | 0 | — | No LoT/LoF pages detected |
| Yin H 2nd review (flattened) | 0 | 0 | 0 | — | No LoT/LoF pages detected |
| Yin Haotian 2nd review | 0 | 0 | 0 | — | No LoT/LoF pages detected |
| Yin H 4th review (compressed) | 4 | 0 | 0 | — | LoT p.14; LoF pp.15,17,18 |
| Sebastian Fine clean baseline | 2 | 2 | **0** | — | LoT p.11; LoF p.12 — no P031 after fix |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

**Total P031 findings after PR #55:** **0** across all five evaluated PDFs.

## 4. Before PR #55 detail (historical — Sebastian only)

The original PR #54 run reported two **high-confidence** warnings on Sebastian Fine page 11
(`list_of_tables`):

| Page | Issue types | Expected labels | Observed header labels (before fix) |
|---:|---|---|---|
| 11 | missing_left_column_header; missing_page_column_header | Table; Page | (none detected in old band) |

PR #55 showed **Table** and **Page** short labels were present at **y0 ≈ 84.3 pt** but
outside the old header band starting at **heading_bottom_y + 2 (≈ 89.1 pt)**.

## 5. Structural context (privacy-safe, unchanged)

LoT/LoF pages detected per file (page numbers only):

| File label | list_of_tables | list_of_figures |
|---|---|---|
| Cibaku Elson 1st review | — | — |
| Yin H 2nd review (flattened) | — | — |
| Yin Haotian 2nd review | — | — |
| Yin H 4th review (compressed) | 14 | 15, 17, 18 |
| Sebastian Fine clean baseline | 11 | 12 |

Page counts: Cibaku 99; Yin H 2nd flat 108; Yin Haotian 2nd 108; Yin H 4th 137;
Sebastian Fine 29.

## 6. Interpretation (current behavior)

**After PR #55, P031 is silent on the full five-PDF evaluation set (0 findings).**

- The Sebastian Fine change (2 → 0) aligns with the header-band false-positive diagnosis;
  not a change in the underlying PDF.
- Yin H 4th remains **0 findings** with four detected list pages (unchanged).
- Three EF PDFs still have **no LoT/LoF pages detected**; P031 cannot evaluate them. Zero
  findings there does not prove compliance.

**Usefulness vs noise:** Post-fix behavior is **low-noise** on this dataset. The earlier
Sebastian warnings should **not** be treated as open P031 defects. Bold/right-alignment
requirements (Q063/Q064/Q072/Q073 visual scope) may still need manual review outside P031.

## 7. Limitations

- Heuristic PDF-only partial coverage; no bold/exact alignment checks.
- Depends on shared LoT/LoF page detection and extractable list entries.
- Header-band geometry remains approximate (now extends 12 pt above `heading_bottom_y`).
- Small sample; no precision/recall vs human review.
- Sebastian Fine PDF extracted locally from tracked ZIP; not committed.
- Generated summaries remain under gitignored `data/evaluation/generated/` paths.

## 8. Related docs

- Sebastian investigation: `docs/evaluation/p031_sebastian_clean_baseline_investigation.md`
- Synthetic validation: `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md`
- P030 current-dataset evaluation: `docs/evaluation/p030_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
