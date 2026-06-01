# P036 Current Dataset Evaluation (Not Run)

- **Date:** 2026-06-01
- **Implementation commit:** `e4840aa` (PR #87 — P036 TOC/List inter-entry spacing)
- **Auditor scope:** P001–P036 (P036 only reported here)
- **Evaluation type:** **Not performed** — evaluation PDFs unavailable in workspace

## 1. Purpose and scope

Document that **no local or current-dataset P036 audit** was run after implementation.
The five evaluation dissertation PDFs referenced in project docs are not present as
standalone files in this workspace at refresh time (privacy-sensitive materials may
exist only on local machines or inside tracked archives).

Reporting remains **aggregate/metadata-only**. No TOC/List entry text, dissertation
body text, title text, or author names are quoted.

Generated JSON/MD under `data/evaluation/generated/` were **not** committed.

## 2. Current-dataset status

| Item | Status |
|---|---|
| Evaluation PDFs available locally | **No** (not in workspace) |
| P036 per-file counts | **Not available** |
| P036 issue-type mix | **Not available** |
| Local subset audit performed? | **No** |

## 3. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035/P036) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| Full canonical P001–P036 rerun performed? | **No** |
| P036 increment to canonical total | **None documented** |

Do **not** update the **1,446** canonical total until a full five-PDF P001–P036 audit is
rerun locally when evaluation PDFs are available, documented in a privacy-safe evaluation
note, and (if appropriate) written to a new gitignored generated path (e.g.
`data/evaluation/generated/current_auditor_after_p036/`).

## 4. Related docs

- Synthetic validation: `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md`
- Design: `docs/planning/p036_scope_and_design.md`
- P035 local subset (separate, non-canonical): `docs/evaluation/p035_current_dataset_evaluation.md`
- Canonical pre-P035 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`

## 5. Future rerun guidance

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set (or available subset).
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p036/`.
3. Update a privacy-safe current-dataset doc with aggregate P036 counts and issue-type mix only.
4. Do not change `generated_for_commit` unless a deliberate canonical baseline refresh is agreed.
