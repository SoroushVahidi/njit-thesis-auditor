# Phase 2 P015 Indentation Check Evaluation

- Date: 2026-05-22
- Source filename: `clean_without_annotations.pdf`
- Source path: `data/evaluation/generated/ester_yin_second_review/clean_without_annotations.pdf`

## Result Summary

- Previous `P015` finding count: `136`
- New `P015` finding count: `36`
- Reduction: `100` findings (`73.5%` reduction)

## What Was Filtered in Refinement

- Restricted opening-paragraph check to pages with named front-matter heading context (`ABSTRACT`).
- Added references/bibliography page exclusion.
- Added caption exclusion for lines beginning with `Figure`/`Table`.
- Added bullet/list-like paragraph exclusion.
- Added short/numeric/math-heavy line exclusion.
- Added low-confidence paragraph exclusion (for weak grouping patterns).
- Grouped repeated same-page `P015` warnings to at most one finding per page per issue type.
- Ignored strong negative-indent artifacts for missing-indent warnings.

## High-Level Remaining Issue Types

- `missing_later_indent` findings on pages where paragraph patterns suggest inconsistent first-line indentation.

## Caveat

- `P015` remains heuristic and conservative; findings are for review prioritization, not final compliance verdicts.

## Privacy and Scope Notes

- Counts and high-level issue summaries only.
- No dissertation body text is included.
