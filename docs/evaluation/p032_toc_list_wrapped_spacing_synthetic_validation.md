# P032 TOC/List Wrapped-Entry Spacing — Synthetic Validation

- **Rule:** P032 — wrapped-entry internal spacing checks for TOC, List of Tables, and List of Figures
- **Date:** 2026-05-30
- **Scope:** Conservative partial PDF heuristic for Q053–Q055, Q066–Q067, and Q076–Q078

## Intent

P032 flags likely wrapped TOC/List entries where the vertical gap between the first line
and its continuation line clearly exceeds single-spacing relative to local line height or
font size. It does not attempt full visual compliance with spacing between separate entries.

## Synthetic scenarios

| Scenario | Expected P032 behavior |
|----------|------------------------|
| TOC wrapped entry with normal single-spaced continuation | No finding |
| TOC wrapped entry with excessive internal gap | Warning with `wrapped_entry_internal_spacing` |
| List of Tables wrapped entry with normal continuation | No finding |
| List of Tables wrapped entry with excessive internal gap | Warning |
| List of Figures wrapped entry with excessive internal gap | Warning |
| Separate entries with larger inter-entry spacing | No finding |
| Page with only single-line entries | No finding |
| Ambiguous continuation (different indent) | No finding |
| Privacy-safe finding details | No long entry/body text in message or details |

## Limitations

- Wrap grouping is structural/heuristic only; ambiguous pairs are skipped.
- Gaps above ~4× local line height are treated as separate entries and skipped.
- Does not verify leader dots, bold styling, or spacing policy between distinct entries.
- Does not use OCR and does not read dissertation body text into findings.

## Test references

See `tests/test_pdf_rules.py` (P032 section) and `tests/test_rule_inventory.py`.
