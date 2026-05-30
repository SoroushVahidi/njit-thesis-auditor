# P031 LoT/LoF Column Header — Synthetic Validation

- **Date:** 2026-05-30
- **Rule:** P031 — List of Tables/Figures column header label checks
- **Q-rule basis:** partial heuristic coverage for Q063, Q064, Q072, Q073

## Scope

P031 checks confidently identified List of Tables and List of Figures pages for short
header-row labels: **Table** or **Figure** near the entry column and **Page** near the
page-number column. Table of Contents pages are excluded.

This validation doc covers **synthetic tests only**. No real dissertation PDFs were used.

## Synthetic scenarios covered

| Scenario | Expected P031 behavior |
|---|---|
| LoT with Table + Page headers | No finding |
| LoT missing Table header | `missing_left_column_header` |
| LoT missing Page header | `missing_page_column_header` |
| LoF with Figure + Page headers | No finding |
| LoF missing Figure header | `missing_left_column_header` |
| LoF missing Page header | `missing_page_column_header` |
| TOC page with Table/Page text | Not checked (TOC excluded) |
| Page without LoT/LoF heading | Not flagged |
| Finding details | Short header tokens only; no long entry/body text |

## Limitations

- Does not verify bold styling or exact visual alignment required by the rule matrix.
- Requires LoT/LoF page detection and at least one extractable list entry.
- Coarse x-position heuristics only; may miss subtle layout issues or over-flag edge cases.
- Does not use OCR.

## Tests

See `tests/test_pdf_rules.py` (P031 section) and `tests/test_rule_inventory.py`.
