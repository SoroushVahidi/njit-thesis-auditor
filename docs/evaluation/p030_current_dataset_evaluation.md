# P030 Current Dataset Evaluation

- **Date:** 2026-05-30
- **Baseline commit:** `cd04f5280483fa2edf021fc4c712427f7d0f3e34`
- **Auditor scope:** P001–P030 (P030 only reported here)
- **Generated artifacts (gitignored):** `data/evaluation/generated/p030_evaluation/`

## 1. Purpose and scope

Evaluate the conservative P030 continued-heading rule on the repository’s documented
evaluation PDF set identified in `data/processed/evaluation_data_manifest.json`.

This run reports **aggregate P030 counts and structural metadata only**. No dissertation
body text is quoted. No generated audit JSON/Markdown outputs are committed.

Evaluated inputs match the five-PDF full-evaluation set documented in
`docs/evaluation/current_auditor_after_p014_p029_evaluation.md`, excluding the rule-matrix
XLSX and archive-only materials not verified locally.

## 2. Evaluated files

| File label | Availability | P030 count | Pages with P030 | Notes |
|---|---|---:|---|---|
| Cibaku Elson 1st review | tracked | 0 | — | No TOC/List pages detected by shared heading logic |
| Yin H 2nd review (flattened) | tracked | 0 | — | No TOC/List pages detected |
| Yin Haotian 2nd review | tracked | 0 | — | No TOC/List pages detected |
| Yin H 4th review (compressed) | tracked | 3 | 12, 13, 18 | Multi-page TOC (pp. 11–13) and LoF (pp. 17–18) sections detected |
| Sebastian Fine clean baseline | archive-contained (local ZIP extract) | 0 | — | Single-page TOC/LoT/LoF sections only (pp. 9, 11, 12) |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

## 3. P030 detail summary (Yin H 4th review only)

All three findings use `issue_type: missing_continued_heading` with `confidence: high`.

| Page | Section type | Expected continued heading | Observed heading (short) | Section start page |
|---:|---|---|---|---:|
| 12 | table_of_contents | TABLE OF CONTENTS (Continued) | TABLE OF CONTENTS | 11 |
| 13 | table_of_contents | TABLE OF CONTENTS (Continued) | TABLE OF CONTENTS | 11 |
| 18 | list_of_figures | LIST OF FIGURES (Continued) | LIST OF FIGURES | 17 |

No P030 findings referenced List of Tables in this run. Detected LoT coverage was a
single page (page 14).

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

**Overall:** P030 produced **0 findings on four of five evaluated PDFs** and **3 findings
on one file** (Yin H 4th compressed).

**Zero-finding files do not prove compliance.** In three EF-commented PDFs, the shared
TOC/List heading detector found no qualifying pages, so P030 had no section context to
evaluate. That may reflect compressed/flattened PDF text layers, heading layout differences,
or genuinely single-page front-matter lists — not necessarily correct continued headings.

**Yin H 4th findings appear structurally plausible** based on metadata alone: consecutive
TOC pages 11–13 and consecutive LoF pages 17–18 were detected, and continuation pages 12,
13, and 18 showed base headings without a `(Continued)` variant in the heading preview
fields. This aligns with the rule intent for Q048/Q062/Q071 partial coverage, but
precision/recall against human review is **not measured** here.

**Sebastian Fine clean baseline:** each TOC/List section occupied one detected page, so
P030 correctly remained silent. Useful as a **no-noise** check on single-page sections.

**Usefulness vs noise:** On this small dataset, P030 appears **low-noise** (no findings on
the clean baseline or on files where sections were not detected) and **potentially useful**
where multi-page TOC/LoF sections are detectable. Sample size is too small for strong
claims.

## 6. Limitations

- Heuristic PDF-only partial coverage for Q048, Q062, Q071; does not verify bold/centering.
- Depends on the same TOC/List heading detection as P018/P024; undetected sections are skipped.
- Non-consecutive section pages are not flagged; page 15 LoF was not paired with pages 17–18.
- Three EF PDFs had no detected TOC/List pages in this run; P030 cannot assess them.
- No EF-comment overlap metrics for continued headings (flattened/non-extractable comments).
- Sebastian Fine PDF was extracted locally from the tracked ZIP; not committed.
- Generated summary JSON lives under gitignored `data/evaluation/generated/p030_evaluation/`.

## 7. Related docs

- Synthetic validation: `docs/evaluation/p030_toc_continued_heading_synthetic_validation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
- Prior full auditor snapshot (pre-P030): `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`
