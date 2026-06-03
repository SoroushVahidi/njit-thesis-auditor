# P041 Current Dataset Evaluation (Not Run)

- **Date:** 2026-06-03
- **Implementation commit:** `4de13ab` (PR #108 — P041 Dedication page header check)
- **Auditor scope:** P001–P041 (P041 only reported here)
- **Evaluation type:** **Not performed** — evaluation PDFs unavailable in workspace

## 1. Purpose and scope

Document that **no local or current-dataset P041 audit** was run after implementation.
The five evaluation dissertation PDFs referenced in project docs are not present as
standalone files in this workspace at refresh time (privacy-sensitive materials may
exist only on local machines or inside tracked archives).

Reporting remains **aggregate/metadata-only**. No dissertation body text, title text,
author names, dedication text, or other private content is quoted.

Generated JSON/MD under `data/evaluation/generated/` were **not** committed.

## 2. Current-dataset status

| Item | Status |
|---|---|
| Evaluation PDFs available locally | **No** (not in workspace) |
| P041 per-file counts | **Not available** |
| P041 issue-type mix | **Not available** |
| Local subset audit performed? | **No** |

## 3. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035/P036/P037/P038/P039/P040/P041) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| Full canonical P001–P041 rerun performed? | **No** |
| P041 increment to canonical total | **None documented** |

Do **not** update the **1,446** canonical total until a full five-PDF P001–P041 audit
is rerun locally when evaluation PDFs are available, documented in a privacy-safe
evaluation note, and written to a new gitignored generated path
(e.g. `data/evaluation/generated/current_auditor_after_p041/`).

## 4. P041 v1 known limitations

| Limitation | Notes |
|---|---|
| DEDICATION heading detection | Requires verbatim "DEDICATION" text in the text layer; stylized headings or image-only dedications are silently skipped |
| Scan range | First 15 pages only; DEDICATION pages beyond page 15 would be missed |
| At most one finding per page | Only the first flagged top-margin line is reported |
| Compressed/flattened PDFs | Text extraction may fail; gate skips silently |
| Top zone threshold | Fixed at 15% of page height |

## 5. Related docs

- Synthetic validation: `docs/evaluation/p041_dedication_page_synthetic_validation.md`
- Design: `docs/planning/p041_scope_and_design.md`
- P040 current-dataset (also not run): `docs/evaluation/p040_current_dataset_evaluation.md`
- P039 current-dataset (also not run): `docs/evaluation/p039_current_dataset_evaluation.md`
- P035 local subset (separate, non-canonical): `docs/evaluation/p035_current_dataset_evaluation.md`
- Canonical pre-P035/.../P041 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`

## 6. Future rerun guidance

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set.
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p041/`.
3. Update a privacy-safe current-dataset doc with aggregate P041 counts only.
4. Do not quote dedication text, header text, or any dissertation prose.
5. Do not change `generated_for_commit` unless a deliberate canonical baseline refresh is agreed.
