# P040 Current Dataset Evaluation (Not Run — see gap-fill below)

> **Gap-fill evaluation (2026-06-09, commit `85a1326`):** Five-PDF current-dataset audit now complete.
> P040 total: **1** finding (`lof_entry_missing_terminal_punctuation`: 1 on Sebastian Fine).
> See `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`.

- **Date:** 2026-06-03
- **Implementation commit:** `f331dde` (PR #104 — P040 LoF terminal punctuation checks)
- **Auditor scope:** P001–P040 (P040 only reported here)
- **Evaluation type:** **Not performed** — evaluation PDFs unavailable in workspace

## 1. Purpose and scope

Document that **no local or current-dataset P040 audit** was run after implementation.
The five evaluation dissertation PDFs referenced in project docs are not present as
standalone files in this workspace at refresh time (privacy-sensitive materials may
exist only on local machines or inside tracked archives).

Reporting remains **aggregate/metadata-only**. No dissertation body text, title text,
author names, List of Figures entry text, or other private content is quoted.

Generated JSON/MD under `data/evaluation/generated/` were **not** committed.

## 2. Current-dataset status

| Item | Status |
|---|---|
| Evaluation PDFs available locally | **No** (not in workspace) |
| P040 per-file counts | **Not available** |
| P040 issue-type mix | **Not available** |
| Local subset audit performed? | **No** |

## 3. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035/P036/P037/P038/P039/P040) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| Full canonical P001–P040 rerun performed? | **No** |
| P040 increment to canonical total | **None documented** |

Do **not** update the **1,446** canonical total until a full five-PDF P001–P040 audit
is rerun locally when evaluation PDFs are available, documented in a privacy-safe
evaluation note, and (if appropriate) written to a new gitignored generated path
(e.g. `data/evaluation/generated/current_auditor_after_p040/`).

## 4. P040 v1 known limitations

| Limitation | Notes |
|---|---|
| Page-number-token filter | Only entries with `page_number_token is not None` are checked; wrap-continuation lines are skipped |
| Minimum text length | Entries shorter than 10 characters after prefix and leader/page-number stripping are skipped |
| LoF-only | TOC and LoT pages are excluded by design |
| Figure prefix stripping | Only "Figure N." / "Fig. N." prefixes are stripped; unusual numbering formats may leave prefix in the description |
| Compressed PDFs | Text and coordinate extraction may be unreliable on compressed/flattened PDFs |

## 5. Related docs

- Synthetic validation: `docs/evaluation/p040_lof_terminal_punctuation_synthetic_validation.md`
- Design: `docs/planning/p040_scope_and_design.md`
- P039 current-dataset (also not run): `docs/evaluation/p039_current_dataset_evaluation.md`
- P038 current-dataset (also not run): `docs/evaluation/p038_current_dataset_evaluation.md`
- P035 local subset (separate, non-canonical): `docs/evaluation/p035_current_dataset_evaluation.md`
- Canonical pre-P035/P036/P037/P038/P039/P040 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`

## 6. Future rerun guidance

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set (or available subset).
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p040/`.
3. Update a privacy-safe current-dataset doc with aggregate P040 counts and issue-type mix only.
4. Do not quote LoF entry text, figure descriptions, or any dissertation prose.
5. Do not change `generated_for_commit` unless a deliberate canonical baseline refresh is agreed.
