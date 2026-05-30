# P032 Current Dataset Evaluation

- **Date:** 2026-05-30
- **Baseline commit:** `b700b946038704f70b745922464cbe4966c10c9c`
- **Auditor scope:** P001–P032 (P032 only reported here)
- **Generated artifacts (gitignored):** `data/evaluation/generated/p032_evaluation/`

## 1. Purpose and scope

Evaluate the conservative P032 wrapped-entry internal-spacing rule on the repository’s
documented evaluation PDF set identified in
`data/processed/evaluation_data_manifest.json`.

This run reports **aggregate P032 counts and structural metadata only**. No dissertation
body text is quoted. No generated audit JSON/Markdown outputs are committed.

Evaluated inputs match the five-PDF full-evaluation set used for P030/P031, excluding the
rule-matrix XLSX and archive-only materials not verified locally.

## 2. Results summary

| File label | TOC/List pages detected | Likely wrapped pairs | P032 count | Pages | Issue types | Notes |
|---|---|---:|---:|---|---|---|
| Cibaku Elson 1st review | 0 | 0 | 0 | — | — | No TOC/List pages detected |
| Yin H 2nd review (flattened) | 0 | 0 | 0 | — | — | No TOC/List pages detected |
| Yin Haotian 2nd review | 0 | 0 | 0 | — | — | No TOC/List pages detected |
| Yin H 4th review (compressed) | 7 | 75 | **3** | 15 | wrapped_entry_internal_spacing | LoF p.15 only; 72 wrap pairs within threshold |
| Sebastian Fine clean baseline | 3 | 0 | 0 | — | — | Single-page TOC/LoT/LoF; no wrap pairs classified |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

**Total P032 findings:** **3** across all five evaluated PDFs (all on Yin H 4th review).

## 3. P032 detail summary (Yin H 4th review only)

All three findings use `issue_type: wrapped_entry_internal_spacing`, `section_type:
list_of_figures`, `entry_kind: figure_entry`, and `confidence: high`.

| Page | Observed gap (pt) | Expected max gap (pt) | Line height (pt) |
|---:|---:|---:|---:|
| 15 | 32.3 | 20.4 | 12.0 |
| 15 | 38.5 | 20.4 | 12.0 |
| 15 | 38.8 | 20.4 | 12.0 |

On this file, **75 likely wrapped-entry pairs** were structurally detected across detected
TOC/List pages; **72** had internal gaps at or below the 1.7× line-height threshold and
**3** exceeded it (matching the P032 finding count).

No P032 findings were reported on TOC pages (11–13) or List of Tables page 14 in this run,
despite wrap pairs being detected elsewhere on those pages.

## 4. Structural context (privacy-safe)

TOC/List pages detected per file (page numbers only):

| File label | table_of_contents | list_of_tables | list_of_figures |
|---|---|---|---|
| Cibaku Elson 1st review | — | — | — |
| Yin H 2nd review (flattened) | — | — | — |
| Yin Haotian 2nd review | — | — | — |
| Yin H 4th review (compressed) | 11, 12, 13 | 14 | 15, 17, 18 |
| Sebastian Fine clean baseline | 9 | 11 | 12 |

Page counts: Cibaku 99; Yin H 2nd flat 108; Yin Haotian 2nd 108; Yin H 4th 137;
Sebastian Fine 29.

## 5. Interpretation

**Overall:** P032 produced **0 findings on four of five evaluated PDFs** and **3 findings
on one file** (Yin H 4th compressed, List of Figures page 15 only).

**Zero-finding files do not prove compliance.**

- In three EF-commented PDFs, the shared TOC/List heading detector found **no qualifying
  pages**, so P032 had no section context to evaluate. This is the same detection gap seen
  for P030/P031 — not evidence that wrapped-entry spacing is correct.
- On **Sebastian Fine clean baseline**, three single-page TOC/LoT/LoF sections were
  detected but **no likely wrapped-entry pairs** were classified (entries appear
  single-line or complete per line in the text layer). P032 correctly remained silent;
  this does not prove all entries are single-spaced if wraps exist but were not grouped.

**Yin H 4th findings appear structurally plausible** based on geometry metadata alone:
gaps of ~32–39 pt vs an expected maximum of ~20 pt at 12 pt line height exceed the 1.7×
threshold with high confidence. However, **precision/recall against human review is not
measured** here, and wrap pairing remains heuristic.

**Usefulness vs noise:** On this small dataset, P032 appears **moderately selective** — it
flagged only 3 of 75 detected wrap pairs on the one file with rich TOC/List content, and
stayed silent on the clean baseline. The concentration of all findings on one LoF page
warrants manual spot-checking before treating them as definite formatting defects.

## 6. Limitations

- Heuristic PDF-only partial coverage for Q053–Q055, Q066–Q067, Q076–Q078; does not
  assess spacing between separate entries or full visual layout compliance.
- Wrap grouping depends on continuation-line signals (no terminal page number, similar
  indent, not a new entry start); mis-grouping can cause false positives or false negatives.
- Page-number tokens on separate text objects at the same row may not always be recognized.
- Three EF PDFs had no detected TOC/List pages; P032 cannot assess them.
- “Likely wrapped pairs” counts come from the same structural logic as P032 but are
  reported only in gitignored summary JSON for this evaluation run.
- Sebastian Fine PDF extracted/reused locally from the tracked ZIP; not committed.
- Generated summary JSON lives under gitignored `data/evaluation/generated/p032_evaluation/`.

## 7. Related docs

- Synthetic validation: `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md`
- P030 current-dataset evaluation: `docs/evaluation/p030_current_dataset_evaluation.md`
- P031 current-dataset evaluation: `docs/evaluation/p031_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
