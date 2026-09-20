# R066 Ester Degree-Order Follow-Up (2026-09-20)

## Reviewer Ground Truth

Ester confirmed the Anthony R066 finding as a false positive. Anthony's degree
entries are already in reverse chronological order. No Ester-confirmed R066
true-positive example is available in the tracked workbook or feedback PDF.

## Canonical Scope

R066/P066 implements Q025's structural degree-ordering portion only. It scans
the Biographical Sketch's explicit education subsection, from most recent to
oldest, and does not implement Q023 birthplace/date checks, Q024 work-history
checks, or the Q025 "NJIT first" institution-name requirement.

The detector compares one 4-digit year per short candidate line. It uses
year-only precision, requires at least three candidates, treats a later-listed
year more than two years newer as an inversion, and skips date ranges,
fragmented or missing date associations, ambiguous sections, and same-year
ties. Month names do not add precision. Both Publications and Presentations
heading orders are recognized as the education-zone stop boundary.

## Root Cause and Fix

Anthony's pre-fix candidate years were structurally `[2026, 1993, 2026, 2019,
2016, 2013]`. The `1993` was a pre-education biographical date; the actual
education sequence was `[2026, 2019, 2016, 2013]`. Other pre-fix findings also
included publication years because the PDF text layer compacted or reversed
the publication heading words.

The R066-local fix requires an explicit education subsection and recognizes
compact PDF labels plus both publication-heading word orders. Shared PDF
tokenization and other Biographical Sketch rules were not changed.

## Seven-Document Audit

| Dissertation | Before | After | Change |
|---|---:|---:|---:|
| Youra | 1 | 0 | -1 |
| Anthony | 1 | 0 | -1 |
| Muyeed | 1 | 0 | -1 |
| Philip | 1 | 0 | -1 |
| Praneeth | 0 | 0 | 0 |
| Sebastian | 0 | 0 | 0 |
| Patrick | 1 | 0 | -1 |
| **Total** | **5** | **0** | **-5** |

All five removals are explained by pre-education dates or publication-year
contamination. The reviewed Anthony case is therefore non-reported without
weakening synthetic out-of-order detection.

## Validation and Privacy

- Synthetic coverage includes correct and incorrect order, ranges, month/year,
  expected/current labels, fragmented dates, irrelevant pre-section numbers,
  same-year ties, publication boundaries, and privacy-safe findings.
- No private PDFs or dissertation text are committed.
- R068 and `LEADER_PLACEMENT_RULE_GAP` remain separate and untouched.
