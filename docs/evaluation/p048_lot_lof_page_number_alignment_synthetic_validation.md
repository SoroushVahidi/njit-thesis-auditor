# P048 LoT/LoF Page-Number Alignment Synthetic Validation

- **Date:** 2026-06-03
- **Scope:** Synthetic validation only
- **Rule:** P048 — LoT/LoF page-number right-column alignment
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_page_number_alignment.py`

## Summary

P048 implements a conservative, geometry-only check for List of Tables and List of Figures page-number right-column alignment. It reuses TOC/List page detection and entry extraction helpers, then checks complete LoT/LoF entries with detected page-number right edges.

## Synthetic Coverage

Focused tests in `tests/test_pdf_rules.py` cover:

- no LoT/LoF page detected → no P048 finding
- aligned List of Tables page-number positions → no finding
- misaligned List of Tables page-number position → `lot_page_number_column_misaligned`
- aligned List of Figures page-number positions → no finding
- misaligned List of Figures page-number position → `lof_page_number_column_misaligned`
- wrapped continuation lines without page numbers are skipped
- column header labels are not counted as entries
- sparse pages with fewer than 3 complete entries are skipped
- finding metadata contains only geometry/Q-rule metadata

## Privacy

Findings contain page number, section type, entry index, page-number x-coordinate geometry, thresholds, count, triage tier, and source Q-rule ID only. They do not include LoT/LoF entry text, table/figure titles, captions, page-number-adjacent text, names, or arbitrary extracted text.

## Current Dataset

No canonical current-dataset audit was run for P048. Only 4/5 evaluation PDFs are directly accessible in the local environment, so the canonical five-PDF aggregate remains unchanged at 1,446 until all five PDFs are available and a full P001–P048 rerun is performed.
