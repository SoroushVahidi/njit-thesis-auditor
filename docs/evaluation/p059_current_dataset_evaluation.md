# P059 Current-Dataset Evaluation — LoT/LoF Entry-Number Ordering Check

- **Rule:** P059 — LoT/LoF entry-number ordering check
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_entry_number_ordering.py`
- **Status:** Not run — only 4/5 evaluation PDFs directly accessible

## Why not run

The canonical five-PDF evaluation set requires all five PDFs to be accessible.
Currently only four of the five PDFs are directly accessible; the fifth (a student
dissertation) requires manual retrieval from the EF archive. A full rerun will
be performed when all five PDFs are available.

## Synthetic validation

All 12 synthetic tests pass. See
`docs/evaluation/p059_lot_lof_entry_number_ordering_synthetic_validation.md`.

## When to rerun

When all five evaluation PDFs are accessible, run:

```
python -m njit_auditor audit <pdf_path>
```

for each PDF and compare P059 finding counts against the canonical 1,446-finding
aggregate baseline. P059 findings (if any) are additive — the pre-P035 canonical
count of 1,446 does not include P059 findings.
