# P033 Current Dataset Evaluation

- **Date:** 2026-06-01 (refreshed after PR #63)
- **Current baseline commit:** `0addb84` (post–PR #63 below-heading recall refinement)
- **Auditor scope:** P001–P033 (P033 only reported here)
- **Generated artifacts (gitignored):**
  - Initial run (PR #62): `data/evaluation/generated/p033_evaluation/`
  - Post–PR #63 refresh: `data/evaluation/generated/p033_evaluation_after_recall_refinement/`

## 1. Purpose and scope

Evaluate the conservative P033 cross-page front-matter title consistency rule on the
repository’s documented evaluation PDF set identified in
`data/processed/evaluation_data_manifest.json`.

This document tracks **two evaluation snapshots**:

1. **Before PR #63** (commits through PR #62, `5f27b0b`) — comparison never ran on any file.
2. **After PR #63** (commit `0addb84`) — below-heading title extraction fallback; rerun confirms
   comparison on two files.

Reporting is **aggregate-only**. No dissertation title text, title previews, author names,
committee names, or body text is quoted. No generated audit outputs are committed.

Evaluated inputs match the five-PDF full-evaluation set used for P030–P032, excluding the
rule-matrix XLSX and archive-only materials not verified locally.

## 2. Evaluation history

| Milestone | Commit | Comparison ran (any file) | P033 findings | Outcome |
|---|---|---:|---:|---|
| PR #62 initial evaluation | `5f27b0b` | **No** (0/5 files) | 0 | Documented in this file (pre-PR #63 sections) |
| PR #63 recall investigation | `0addb84` | — | — | Below-heading fallback; see investigation doc |
| PR #63 post-fix rerun | `0addb84` | **Yes** (2/5 files) | **0** | Confirmed by re-run (this refresh) |

See `docs/evaluation/p033_candidate_extraction_recall_investigation.md` for the structural
explanation (titles below ABSTRACT/APPROVAL headings, not above).

## 3. Current results (after PR #63)

| File label | Roles present | Unique hashes before PR #63 | Unique hashes after PR #63 | Comparison after PR #63 | P033 after PR #63 | Notes |
|---|---|---:|---:|---:|---:|---|
| Cibaku Elson 1st review | title_page, abstract | 1 | 1 | no | 0 | One candidate; abstract below-heading deduplicated with title_page |
| Yin H 2nd review (flattened) | title_page, abstract | 1 | 1 | no | 0 | Same dedup pattern |
| Yin Haotian 2nd review | title_page, abstract | 1 | 1 | no | 0 | Same dedup pattern |
| Yin H 4th review (compressed) | title_page, abstract, approval_page | 1 | **2** | **yes** | 0 | Approval below-heading adds second hash; sim ≈0.96 |
| Sebastian Fine clean baseline | title_page, abstract, approval_page | 1 | **2** | **yes** | 0 | Approval below-heading adds second hash; sim ≈0.95 |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

**Total P033 findings after PR #63:** **0** across all five evaluated PDFs.

**Comparison ran on 2 of 5 files** (Yin H 4th, Sebastian Fine clean baseline).

### Similarity ranges (when comparison ran)

| File label | Min similarity to title_page reference | Material mismatch (threshold 0.92) |
|---|---:|---|
| Yin H 4th review (compressed) | 0.959 | no |
| Sebastian Fine clean baseline | 0.954 | no |

## 4. Extraction detail after PR #63 (privacy-safe)

P033 requires **≥2 unique high-confidence title hashes** before comparison runs. Below-heading
extraction applies when above-heading extraction is empty.

| File label | Role | Page | Above-heading extract | Below-heading extract | In candidate set |
|---|---|---:|:---:|:---:|:---:|
| Cibaku Elson 1st review | title_page | 1 | — | — | yes |
| Cibaku Elson 1st review | abstract | 1 | no | yes | no (hash dedup) |
| Yin H 2nd review (flattened) | title_page | 1 | — | — | yes |
| Yin H 2nd review (flattened) | abstract | 1 | no | yes | no (hash dedup) |
| Yin Haotian 2nd review | title_page | 1 | — | — | yes |
| Yin Haotian 2nd review | abstract | 1 | no | yes | no (hash dedup) |
| Yin H 4th review (compressed) | title_page | 1 | — | — | yes |
| Yin H 4th review (compressed) | abstract | 1 | no | yes | no (hash dedup) |
| Yin H 4th review (compressed) | approval_page | 5 | no | yes | yes |
| Sebastian Fine clean baseline | title_page | 1 | — | — | yes |
| Sebastian Fine clean baseline | abstract | 1 | no | yes | no (hash dedup) |
| Sebastian Fine clean baseline | approval_page | 5 | no | yes | yes |

Title hashes and word counts are in gitignored `p033_summary.json` only.

## 5. Structural context (privacy-safe)

| File label | Pages | ABSTRACT page | APPROVAL PAGE page |
|---|---:|---:|---:|
| Cibaku Elson 1st review | 99 | 1 | — |
| Yin H 2nd review (flattened) | 108 | 1 | — |
| Yin Haotian 2nd review | 108 | 1 | — |
| Yin H 4th review (compressed) | 137 | 1 | 5 |
| Sebastian Fine clean baseline | 29 | 1 | 5 |

On all five PDFs, ABSTRACT appears on **page 1**. After PR #63, title-like text **below**
the ABSTRACT heading is considered; when it matches the title-page hash, the abstract role is
deduplicated. Approval-page titles on page 5 use the same below-heading band on Yin H 4th and
Sebastian.

## 6. Interpretation (current behavior)

**Overall:** After PR #63, P033 still reports **0 findings** on all five PDFs, but
**cross-page comparison now runs on two files** (Yin H 4th and Sebastian). This is a
meaningful recall improvement over PR #62, where comparison never ran.

**Zero findings do not prove title consistency** across the dissertation.

| Outcome category | Files (after PR #63) |
|---|---:|
| Comparison skipped (&lt;2 unique hashes) | 3 |
| Compared, no material mismatch | 2 |
| P033 warning emitted | 0 |

**Why three files still skip comparison:** Below-heading abstract title blocks match the
title-page hash and are deduplicated, leaving one unique hash.

**Usefulness vs noise:** On this dataset, P033 remains **silent** (no false-positive
mismatches) and is now **partially evaluative** — it can compare title_page vs approval_page
on two files. Precision/recall against human review is still not measured.

## 7. Prior state (before PR #63 only)

Before PR #63, every file had **one** confident title candidate (title_page only). Comparison
was skipped on all files because above-heading extraction found no title block on abstract or
approval pages (ABSTRACT/APPROVAL PAGE headings sit at the top of the page with no lines
above). **0 P033 findings** in that run reflected non-comparison, not verified consistency.

## 8. Limitations

- PDF text-layer extraction only; image-only titles remain skipped.
- Hash deduplication suppresses a second candidate when abstract below-heading text matches
  title_page on page 1.
- Below-heading band uses strict line/word/gap caps; unusual layouts may still be missed.
- Similarity threshold (0.92) not validated against human review on this dataset.
- Sebastian Fine PDF extracted locally from the tracked ZIP; not committed.
- Pre–PR #63 counts reflect above-heading-only behavior; current behavior is defined by the
  post–PR #63 rerun at commit `0addb84`.

## 9. Related docs

- Recall investigation: `docs/evaluation/p033_candidate_extraction_recall_investigation.md`
- Synthetic validation: `docs/evaluation/p033_title_consistency_synthetic_validation.md`
- P032 current-dataset evaluation: `docs/evaluation/p032_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
