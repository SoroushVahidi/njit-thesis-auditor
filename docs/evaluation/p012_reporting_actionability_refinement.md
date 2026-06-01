# P012 Reporting Actionability Refinement

- **Date:** 2026-06-01
- **Baseline snapshot:** `docs/evaluation/current_auditor_after_p034_evaluation.md`
- **Scope:** **reporting and triage only** — annotation detection logic unchanged

## Motivation

From the P034-era full auditor snapshot on five evaluation PDFs:

| Metric | Value |
|--------|------:|
| Grand total findings | 1,446 |
| **P012 findings** | **143** (fourth-largest single rule; annotations category) |
| **annotations category** | **143** (matches P012 on this snapshot) |

P012 emits one warning per embedded PDF annotation object. On EF-commented evaluation
PDFs, these warnings are expected reviewer markup rather than NJIT formatting defects.
Without a dedicated rollup, reviewers see long per-annotation lists without page ranges
or annotation-type summaries.

## What changed

### Finding metadata (`pdf_annotations.py`)

- Warnings include `issue_type=pdf_annotation_detected` and `triage_tier=informational`.
- Per-finding `content` remains in raw findings (truncated) for manual review; triage
  rollups never copy annotation text.

### Report outputs (`report_outputs.py`)

- New `build_p012_annotation_triage_summary()` rollup in
  `grouped_summary.p012_annotation_triage`:
  - raw / affected-page counts and compact page list
  - **annotation type** counts and type-specific page ranges
  - pages with multiple annotations on one page
  - max annotations per page and dominant annotation type
  - triage note and recommended cleanup action (privacy-safe)
- Markdown reports add **P012 Annotation/Comment Triage** (after P011/P013/P026 triage
  sections).

### Tests

- `tests/test_report_outputs.py`: P012 triage rollup, ranges, privacy (no content in
  triage), raw preservation, Markdown section, coexistence with other triage rollups.
- `tests/test_pdf_rules.py`: `triage_tier` and `issue_type` on P012 warnings.

## What did not change

- `run_pdf_annotation_rule()` detection (one finding per annotation object).
- Raw P012 count on the five-PDF set (expected unchanged at **143**).
- Severity levels (warnings remain WARNING).

## Privacy model

- Rollups use annotation types, page numbers, and counts only.
- Triage JSON/Markdown sections do not quote annotation `content` or dissertation text.
- Generated audit JSON/Markdown under `data/evaluation/generated/` remain gitignored.

## Post-change verification (five-PDF set)

| Metric | Before refinement | After refinement |
|--------|------------------:|-----------------:|
| Grand total findings | 1,446 | 1,446 (expected unchanged) |
| P012 raw warnings | 143 | 143 (expected unchanged) |

After local rerun, use a new gitignored folder (for example
`current_auditor_after_p034_p012_triage/`) or extend the canonical
`current_auditor_after_p034_p011_triage/` outputs only if explicitly refreshing all
triage reports together.

## Expected effect

- **Better triage/actionability:** reviewers see annotation-type page ranges before
  per-annotation P012 lines.
- **Not fewer raw findings:** summary-layer improvement only.

## Limitations

- Does not remove or validate annotation resolution; manual cleanup still required.
- Does not change P011/P013/P026 triage or detection.
- Raw findings may still include truncated annotation text in `details.content` for
  reviewer context — triage sections intentionally omit it.

## Related docs

- `docs/evaluation/current_auditor_after_p034_evaluation.md`
- `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md`
- `docs/evaluation/p011_reporting_actionability_refinement.md`
