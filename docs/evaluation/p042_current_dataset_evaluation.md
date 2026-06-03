# P042 Current Dataset Evaluation (Not Run)

- **Date:** 2026-06-03
- **Implementation commit:** `21f521a` (PR #112 — P042 TOC appendix entry format checks)
- **Auditor scope:** P001–P042 (P042 only reported here)
- **Evaluation type:** **Not performed** — evaluation PDFs unavailable in workspace

## 1. Purpose and scope

Document that **no local or current-dataset P042 audit** was run after implementation.
The five evaluation dissertation PDFs referenced in project docs are not present as
standalone files in this workspace at refresh time.

Reporting remains **aggregate/metadata-only**. No dissertation body text, title text,
author names, TOC entry text, appendix title text, or other private content is quoted.

Generated JSON/MD under `data/evaluation/generated/` were **not** committed.

## 2. Current-dataset status

| Item | Status |
|---|---|
| Evaluation PDFs available locally | **No** (not in workspace) |
| P042 per-file counts | **Not available** |
| P042 issue-type mix | **Not available** |
| Local subset audit performed? | **No** |

## 3. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035/P036/P037/P038/P039/P040/P041/P042) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| Full canonical P001–P042 rerun performed? | **No** |
| P042 increment to canonical total | **None documented** |

Do **not** update the **1,446** canonical total until a full five-PDF P001–P042 audit
is rerun locally when evaluation PDFs are available.

## 4. P042 v1 known limitations

| Limitation | Notes |
|---|---|
| All-caps APPENDIX (1 word) filtered | `_likely_entry_line` treats short all-caps lines as heading-like and skips them; Q058 check fires only on mixed-case entries |
| Roman numeral appendices | "APPENDIX I", "APPENDIX II" would trigger `multiple_appendix_missing_letter` (not a single letter A-Z) |
| TOC-only | LoT and LoF pages excluded by design |
| Compressed/flattened PDFs | Text extraction may miss entries entirely |

## 5. Related docs

- Synthetic validation: `docs/evaluation/p042_toc_appendix_format_synthetic_validation.md`
- Design: `docs/planning/p042_scope_and_design.md`
- P041 current-dataset (also not run): `docs/evaluation/p041_current_dataset_evaluation.md`
- Canonical pre-P035/.../P042 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`

## 6. Future rerun guidance

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set.
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p042/`.
3. Update a privacy-safe current-dataset doc with aggregate P042 counts only.
4. Do not quote TOC entry text, appendix titles, or any dissertation prose.
5. Do not change `generated_for_commit` unless a deliberate canonical baseline refresh is agreed.
