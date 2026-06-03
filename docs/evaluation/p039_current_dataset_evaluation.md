# P039 Current Dataset Evaluation (Not Run)

- **Date:** 2026-06-03
- **Implementation commit:** `db842d6` (PR #100 — P039 TOC entry hierarchy checks)
- **Auditor scope:** P001–P039 (P039 only reported here)
- **Evaluation type:** **Not performed** — evaluation PDFs unavailable in workspace

## 1. Purpose and scope

Document that **no local or current-dataset P039 audit** was run after implementation.
The five evaluation dissertation PDFs referenced in project docs are not present as
standalone files in this workspace at refresh time (privacy-sensitive materials may
exist only on local machines or inside tracked archives).

Reporting remains **aggregate/metadata-only**. No dissertation body text, title text,
author names, TOC entry text, or other private content is quoted.

Generated JSON/MD under `data/evaluation/generated/` were **not** committed.

## 2. Current-dataset status

| Item | Status |
|---|---|
| Evaluation PDFs available locally | **No** (not in workspace) |
| P039 per-file counts | **Not available** |
| P039 issue-type mix | **Not available** |
| Local subset audit performed? | **No** |

## 3. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035/P036/P037/P038/P039) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| Full canonical P001–P039 rerun performed? | **No** |
| P039 increment to canonical total | **None documented** |

Do **not** update the **1,446** canonical total until a full five-PDF P001–P039 audit
is rerun locally when evaluation PDFs are available, documented in a privacy-safe
evaluation note, and (if appropriate) written to a new gitignored generated path
(e.g. `data/evaluation/generated/current_auditor_after_p039/`).

## 4. P039 v1 known limitations

| Limitation | Notes |
|---|---|
| Text-pattern level detection | Entries without CHAPTER/APPENDIX prefix (L1) or X.Y numeric prefix (L2/L3) are classified as ambiguous and excluded |
| Gate: ≥2 child entries required | Pages with fewer than 2 L2 (or L3) entries are skipped |
| Gate: parent level required | Pages without both parent and child levels present are skipped |
| TOC-only | LoT and LoF pages are excluded by design |
| Compressed PDFs | Coordinate extraction may be unreliable; 6pt minimum threshold mitigates noise |

## 5. Related docs

- Synthetic validation: `docs/evaluation/p039_toc_entry_hierarchy_synthetic_validation.md`
- Design: `docs/planning/p039_scope_and_design.md`
- P038 current-dataset (also not run): `docs/evaluation/p038_current_dataset_evaluation.md`
- P037 current-dataset (also not run): `docs/evaluation/p037_current_dataset_evaluation.md`
- P036 current-dataset (also not run): `docs/evaluation/p036_current_dataset_evaluation.md`
- P035 local subset (separate, non-canonical): `docs/evaluation/p035_current_dataset_evaluation.md`
- Canonical pre-P035/P036/P037/P038/P039 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`

## 6. Future rerun guidance

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set (or available subset).
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p039/`.
3. Update a privacy-safe current-dataset doc with aggregate P039 counts and issue-type mix only.
4. Do not quote TOC entry text, chapter titles, section titles, or any dissertation prose.
5. Do not change `generated_for_commit` unless a deliberate canonical baseline refresh is agreed.
