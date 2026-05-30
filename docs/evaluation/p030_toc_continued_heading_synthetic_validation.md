# P030 TOC/List Continued Heading — Synthetic Validation

- **Date:** 2026-05-30
- **Rule:** P030 — multi-page TOC/LoT/LoF continued-heading checks
- **Q-rule basis:** partial heuristic coverage for Q048, Q062, Q071

## Scope

P030 flags consecutive continuation pages of the same TOC/List section when the page
lacks a continued-heading variant such as `TABLE OF CONTENTS (Continued)`.

This validation doc covers **synthetic tests only**. No real dissertation PDFs were
audited for this note.

## Synthetic scenarios covered

| Scenario | Expected P030 behavior |
|---|---|
| Single-page TOC | No finding |
| Two-page TOC with continued heading on page 2 | No finding |
| Two-page TOC without continued heading on page 2 | Warning on page 2 |
| Two-page List of Tables with continued heading | No finding |
| Two-page List of Figures without continued heading | Warning on page 2 |
| Trailing punctuation and `(CONTINUED)` suffix variants | Accepted as continued heading |
| Non-consecutive TOC pages | No finding |
| Finding details | Heading preview only; no long body text |

## Limitations

- Does not verify bold, centering, or exact typography of continued headings.
- Requires consecutive pages of the same section type.
- Requires at least one list entry below the heading on continuation pages.
- Does not use OCR or scanned-PDF assumptions.

## Tests

See `tests/test_pdf_rules.py` (P030 section) and `tests/test_rule_inventory.py`.
