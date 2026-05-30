# P031 Current Dataset Evaluation

- **Date:** 2026-05-30
- **Baseline commit:** `e0ebbd324f6c620ad57375466e887ce858c368e2`
- **Auditor scope:** P001–P031 (P031 only reported here)
- **Generated artifacts (gitignored):** `data/evaluation/generated/p031_evaluation/`

## 1. Purpose and scope

Evaluate the conservative P031 List of Tables/Figures column-header rule on the
repository’s documented evaluation PDF set identified in
`data/processed/evaluation_data_manifest.json`.

This run reports **aggregate P031 counts and structural metadata only**. No dissertation
body text is quoted. No generated audit JSON/Markdown outputs are committed.

Evaluated inputs match the five-PDF full-evaluation set documented in
`docs/evaluation/current_auditor_after_p014_p029_evaluation.md`, excluding the rule-matrix
XLSX and archive-only materials not verified locally.

## 2. Evaluated files

| File label | Availability | LoT/LoF pages detected | P031 count | Pages | Issue types | Notes |
|---|---|---:|---:|---|---|---|
| Cibaku Elson 1st review | tracked | 0 | 0 | — | — | No LoT/LoF pages detected |
| Yin H 2nd review (flattened) | tracked | 0 | 0 | — | — | No LoT/LoF pages detected |
| Yin Haotian 2nd review | tracked | 0 | 0 | — | — | No LoT/LoF pages detected |
| Yin H 4th review (compressed) | tracked | 4 | 0 | — | — | LoT p.14; LoF pp.15,17,18 — headers not flagged |
| Sebastian Fine clean baseline | archive-contained (local ZIP extract) | 2 | 2 | 11 | missing_left_column_header; missing_page_column_header | LoT p.11 flagged; LoF p.12 detected, no P031 |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

## 3. P031 detail summary (Sebastian Fine clean baseline only)

Both findings are on **page 11** (`section_type: list_of_tables`), `confidence: high`.

| Page | Issue type | Expected left label | Expected page label | Observed header labels |
|---:|---|---|---|---|
| 11 | missing_left_column_header | Table | Page | (none detected) |
| 11 | missing_page_column_header | Table | Page | (none detected) |

No short header-row tokens were detected in the header band below the List of Tables heading.

## 4. Structural context (privacy-safe)

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

## 5. Interpretation

**Overall:** P031 produced **0 findings on four of five evaluated PDFs** and **2 findings
on one file** (Sebastian Fine clean baseline, both on page 11).

**No LoT/LoF pages detected (3 files):** P031 had no qualifying pages to evaluate. This
does not prove compliance; it may reflect compressed/flattened text layers, heading layout
differences, or list sections not recognized by shared page-type detection.

**LoT/LoF detected, zero P031 findings (Yin H 4th compressed):** Four list pages were
detected (LoT page 14; LoF pages 15, 17, 18) with no P031 warnings. That suggests either
extractable header-row labels were present in expected regions, or header text is formatted
in a way the conservative rule accepts. Precision/recall against human review is **not
measured**.

**Sebastian Fine clean baseline:** List of Tables page 11 triggered missing **Table** and
**Page** header warnings with no observed short header tokens. List of Figures page 12 was
detected but not flagged (headers may be present or entries/header band did not meet flag
thresholds). These findings are **structurally plausible** for a missing header row in the
PDF text layer, but could include false positives if labels are embedded in non-extractable
or non-short-line layout.

**Usefulness vs noise:** On this dataset P031 is **mostly silent** except on the clean
baseline LoT page. That supports conservative behavior on Yin H 4th (where list pages were
detected) but the Sebastian Fine LoT warnings need manual confirmation before treating as
true formatting defects.

## 6. Limitations

- Heuristic PDF-only partial coverage for Q063, Q064, Q072, Q073; no bold/exact alignment checks.
- Depends on shared LoT/LoF page detection and extractable list entries below headings.
- Header-band search may miss labels split across spans or rendered without separate short lines.
- Three EF PDFs had no detected LoT/LoF pages; P031 cannot assess them.
- Small sample; no EF-comment overlap for column-header labels.
- Sebastian Fine PDF extracted locally from tracked ZIP; not committed.
- Generated summary JSON under gitignored `data/evaluation/generated/p031_evaluation/`.

## 7. Related docs

- Synthetic validation: `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md`
- P030 current-dataset evaluation: `docs/evaluation/p030_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
