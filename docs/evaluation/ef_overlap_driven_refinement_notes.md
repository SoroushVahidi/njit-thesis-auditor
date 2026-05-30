# EF Overlap-Driven Refinement Notes

- Date: 2026-05-29
- Selected target: **P013 (page-number candidate detector) noise reduction via per-page grouping metadata**

## Evidence from EF overlap comparison

- The current EF comparison identifies `page_numbering` as one of the largest high-volume tool categories, while category overlap with EF comments is limited.
- Per-file totals in `docs/evaluation/current_ef_comment_vs_tool_comparison.md` show substantial tool-only coverage and high page-numbering volume:
  - Cibaku: `page_numbering=115`
  - Yin Haotian: `page_numbering=128`
- The comparison recommends noise-reduction/grouping for high-volume categories (`page_numbering`, `font_format`) as the next highest-value refinement.

## Affected rules/modules

- Primary rule: `P013` in `src/njit_auditor/rules/pdf_page_numbers.py`
- Reporting impact: grouped summary/readability in JSON/Markdown outputs (existing grouped summary consumes finding details).

## Planned refinement

- Keep P013 as a conservative detector (do not remove coverage).
- Reduce repetitive output by grouping candidate detections to one warning per page, instead of one warning per candidate line.
- Add structured detail fields to improve triage:
  - `issue_type`
  - `candidate_count_on_page`
  - representative candidate/position/style summary
  - confidence hint (`low`/`medium`) for manual review prioritization

## Expected improvement

- Fewer redundant P013 warning entries on pages with multiple candidate lines.
- Better grouped-summary usefulness (issue type + compact context) without reducing core detection coverage.
- Improved reviewer actionability while preserving privacy-safe reporting.

## Risk / noise considerations

- Risk is low: this is a presentation/aggregation refinement for P013 warnings, not a removal of candidate detection logic.
- P019 and other rules that depend on raw candidate extraction continue using the underlying candidate detector unchanged.
