# P055 Current Dataset Evaluation

- **Rule:** P055 — LoT/LoF cross-type entry check (Q063/Q072 extension)
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_entry_type.py`
- **Date:** 2026-06-05
- **Status:** Not run — only 4/5 evaluation PDFs directly accessible

## Summary

A current-dataset audit was not run for P055. Only 4 of the 5 canonical evaluation PDFs are directly accessible; the fifth is available only as a ZIP archive. A canonical five-PDF aggregate rerun is not possible without full access.

- `generated_for_commit`: `00b9c2d` (unchanged)
- `canonical aggregate`: `1,446` (unchanged)

The synthetic validation (10 tests) confirms correct behavior. See `docs/evaluation/p055_lot_lof_entry_type_synthetic_validation.md`.

## When to rerun

Run when all five evaluation PDFs are directly accessible. The rerun threshold is P001–P058. Do not add P055 findings to the 1,446 canonical aggregate without a full five-PDF rerun.
