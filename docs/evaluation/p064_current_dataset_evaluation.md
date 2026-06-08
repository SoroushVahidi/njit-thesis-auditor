# P064 — References/Citations Structural Check: Current-Dataset Evaluation

- **Date:** 2026-06-08
- **Rule:** P064 — References/Citations Structural Check
- **Module:** `src/njit_auditor/rules/pdf_references_citations_structural.py`
- **Status:** PENDING — current-dataset evaluation not yet run

---

## Summary

The current-dataset evaluation against the five evaluation PDFs has not been run.
Only 4 of the 5 evaluation PDFs are directly accessible (the Sebastian Fine clean
baseline is in a ZIP archive).

## Evaluation Steps (when available)

1. Run `njit-audit pdf` with P064 enabled on all five evaluation PDFs.
2. Collect per-file P064 finding counts by issue type.
3. Compare with EF `references_citations` annotation counts (Cibaku: 5, Yin Haotian: 4)
   at the page/category level only.
4. Report aggregate counts only; no reference entry text, author names, or citation
   content to be quoted.

## Expected Behavior

P064 is likely to fire on 1–3 of the 5 evaluation PDFs, depending on whether the
references sections have extractable text-layer geometry and whether heading or
spacing inconsistencies exist. The two PDFs with compressed or flattened text layers
may trigger skip conditions (image-only pages or high x-variance).

## Privacy Constraints

All evaluation outputs go under `data/evaluation/generated/p064_evaluation/`
(gitignored) and must not be committed. This document will be updated with
aggregate counts only — no reference entry text, EF annotation text, author names,
page-number lists, or dissertation content.

## Cross-References

- Synthetic validation: `docs/evaluation/p064_references_citations_structural_synthetic_validation.md`
- EF overlap analysis: `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- Scope doc: `docs/planning/p064_references_citations_structural_check_scope_and_design.md`
- P063-era five-PDF snapshot: `docs/evaluation/current_auditor_after_p063_evaluation.md`
