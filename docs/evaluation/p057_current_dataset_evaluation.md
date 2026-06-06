# P057 Current-Dataset Evaluation — LoT/LoF Page-Number Ordering

- **Date:** 2026-06-05
- **Rule:** P057 — LoT/LoF page-number ordering check
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_page_number_ordering.py`
- **Status:** **Not run** — only 4/5 evaluation PDFs directly accessible

---

## Summary

The P057 current-dataset audit has not been run. Only 4 of the 5 canonical evaluation PDFs
are directly accessible in the workspace. The canonical five-PDF aggregate (generated at
commit `00b9c2d`, 1,446 total findings) is preserved unchanged.

P057 findings will be counted in a future rerun when all five evaluation PDFs are accessible.

---

## When to rerun

Run `python -m njit_auditor pdf <path>` on each of the five canonical evaluation PDFs and
collect findings with `rule_id == "P057"`. Record counts per file without quoting entry text,
titles, or any private student content.
