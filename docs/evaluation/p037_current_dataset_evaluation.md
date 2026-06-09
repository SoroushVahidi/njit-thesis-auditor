# P037 Current Dataset Evaluation (Not Run — see gap-fill below)

> **Gap-fill evaluation (2026-06-09, commit `85a1326`):** Five-PDF current-dataset audit now complete.
> P037 total: **3** findings (`roman_section_wrong_value`: 2 on Yin H 4th, `roman_bio_sketch_not_iv`: 1 on Sebastian Fine).
> See `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`.

- **Date:** 2026-06-02
- **Implementation commit:** `c3c7911` (PR #92 — P037 section-anchored Roman numerals)
- **Auditor scope:** P001–P037 (P037 only reported here)
- **Evaluation type:** **Not performed** — evaluation PDFs unavailable in workspace

## 1. Purpose and scope

Document that **no local or current-dataset P037 audit** was run after implementation.
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
| P037 per-file counts | **Not available** |
| P037 issue-type mix | **Not available** |
| Local subset audit performed? | **No** |

## 3. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035/P036/P037) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| Full canonical P001–P037 rerun performed? | **No** |
| P037 increment to canonical total | **None documented** |

Do **not** update the **1,446** canonical total until a full five-PDF P001–P037 audit
is rerun locally when evaluation PDFs are available, documented in a privacy-safe
evaluation note, and (if appropriate) written to a new gitignored generated path
(e.g. `data/evaluation/generated/current_auditor_after_p037/`).

## 4. P037 v1 known limitations

| Limitation | Notes |
|---|---|
| DEDICATION detection | Requires verbatim heading text "DEDICATION"; pages with alternate headings or no heading are treated as absent |
| Compressed PDFs | Mis-extracted page-number coordinates may cause false negatives (no candidate found → skip) |
| LOF anchor | List of Figures anchor deferred to v2 per scope doc |
| Gate condition | Emits nothing if BIOGRAPHICAL SKETCH heading is not detected |

## 5. Related docs

- Synthetic validation: `docs/evaluation/p037_roman_section_anchors_synthetic_validation.md`
- Design: `docs/planning/p037_scope_and_design.md`
- P036 current-dataset (also not run): `docs/evaluation/p036_current_dataset_evaluation.md`
- P035 local subset (separate, non-canonical): `docs/evaluation/p035_current_dataset_evaluation.md`
- Canonical pre-P035/P036/P037 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`

## 6. Future rerun guidance

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set (or available subset).
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p037/`.
3. Update a privacy-safe current-dataset doc with aggregate P037 counts and issue-type mix only.
4. Do not quote page numbers that correspond to named section headings (they carry no private content, but err on the side of aggregate reporting).
5. Do not change `generated_for_commit` unless a deliberate canonical baseline refresh is agreed.
