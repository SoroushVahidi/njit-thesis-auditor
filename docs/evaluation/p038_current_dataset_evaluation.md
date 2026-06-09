# P038 Current Dataset Evaluation (Not Run — see gap-fill below)

> **Gap-fill evaluation (2026-06-09, commit `85a1326`):** Five-PDF current-dataset audit now complete.
> P038 total: **16** findings on all five files (`required_heading_missing`: 14, `heading_phrase_not_exact`: 2).
> See `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`.

- **Date:** 2026-06-03
- **Implementation commit:** `cb0f4e0` (PR #96 — P038 front-matter heading phrase and missing-section checks)
- **Auditor scope:** P001–P038 (P038 only reported here)
- **Evaluation type:** **Not performed** — evaluation PDFs unavailable in workspace

## 1. Purpose and scope

Document that **no local or current-dataset P038 audit** was run after implementation.
The five evaluation dissertation PDFs referenced in project docs are not present as
standalone files in this workspace at refresh time (privacy-sensitive materials may
exist only on local machines or inside tracked archives).

Reporting remains **aggregate/metadata-only**. No dissertation body text, title text,
author names, biographical content, front-matter prose, or heading-adjacent private
text is quoted.

Generated JSON/MD under `data/evaluation/generated/` were **not** committed.

## 2. Current-dataset status

| Item | Status |
|---|---|
| Evaluation PDFs available locally | **No** (not in workspace) |
| P038 per-file counts | **Not available** |
| P038 issue-type mix | **Not available** |
| Local subset audit performed? | **No** |

## 3. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035/P036/P037/P038) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| Full canonical P001–P038 rerun performed? | **No** |
| P038 increment to canonical total | **None documented** |

Do **not** update the **1,446** canonical total until a full five-PDF P001–P038 audit
is rerun locally when evaluation PDFs are available, documented in a privacy-safe
evaluation note, and (if appropriate) written to a new gitignored generated path
(e.g. `data/evaluation/generated/current_auditor_after_p038/`).

## 4. P038 v1 known limitations

| Limitation | Notes |
|---|---|
| Flattened / compressed PDFs | No P038 findings emitted when no front-matter headings are detected (conservative gate) |
| Curated variant list | Only a small set of known safe spelling variants is checked; novel misspellings are not flagged |
| LIST OF TABLES / LIST OF FIGURES | Never flagged as missing (optional sections); only phrase-variant detection applies |
| DEDICATION | Optional heading; never flagged as missing; only phrase-variant detection applies |

## 5. Related docs

- Synthetic validation: `docs/evaluation/p038_frontmatter_headings_synthetic_validation.md`
- Design: `docs/planning/p038_scope_and_design.md`
- P037 current-dataset (also not run): `docs/evaluation/p037_current_dataset_evaluation.md`
- P036 current-dataset (also not run): `docs/evaluation/p036_current_dataset_evaluation.md`
- P035 local subset (separate, non-canonical): `docs/evaluation/p035_current_dataset_evaluation.md`
- Canonical pre-P035/P036/P037/P038 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`

## 6. Future rerun guidance

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set (or available subset).
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p038/`.
3. Update a privacy-safe current-dataset doc with aggregate P038 counts and issue-type mix only.
4. Do not quote heading text, author names, front-matter prose, or any private content.
5. Do not change `generated_for_commit` unless a deliberate canonical baseline refresh is agreed.
