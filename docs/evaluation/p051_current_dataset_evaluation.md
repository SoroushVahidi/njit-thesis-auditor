# P051 Current Dataset Evaluation (see gap-fill for five-PDF results)

> **Gap-fill evaluation (2026-06-09, commit `85a1326`):** Full five-PDF current-dataset audit now complete.
> P051 total: **3** findings (`copyright_year_not_found`: 1 each on Cibaku, Yin H flat, Yin Haotian; 0 on Yin H 4th and Sebastian Fine).
> See `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`.

- **Rule:** P051 — PDF copyright page year-format refinement (Q010 improvement)
- **Date:** 2026-06-04
- **Status:** Not run — only 4/5 evaluation PDFs are directly accessible

---

## Evaluation status

No canonical audit run was performed for P051. The five-PDF canonical aggregate remains
**1,446** (generated for commit `00b9c2d`).

P051 is a low-confidence advisory (triage_tier: low) that fires only when the copyright
page is detected but contains no year token anywhere. Based on P034 current-dataset
analysis (0 copyright_year_mismatch findings on 5/5 PDFs), copyright pages in the current
dataset successfully expose year tokens, so P051 is expected to produce 0 findings on the
current dataset. No rerun is claimed.

---

## Access constraints

- 4/5 evaluation PDFs are directly accessible in the workspace.
- The fifth PDF (`250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf`) is
  referenced but not verified as a standalone tracked path.
- A canonical five-PDF P051 rerun requires all five PDFs to be directly accessible.

---

## Privacy note

If P051 is run locally, findings must contain only structural metadata — no copyright
line text, author names, title text, or private content. Generated outputs must remain
under `data/evaluation/generated/` (gitignored) and must not be committed.
