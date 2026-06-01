# P011 Reporting Actionability Refinement

- **Date:** 2026-06-01
- **Baseline snapshot:** `docs/evaluation/current_auditor_after_p034_evaluation.md` (PR #70)
- **Scope:** **reporting and triage only** — margin detection logic unchanged

## Motivation

From the P034-era full auditor snapshot on five evaluation PDFs:

| Metric | Value |
|--------|------:|
| Grand total findings | 1,446 |
| **P011 findings** | **169** (third-largest single rule after P013/P026) |
| **margin_or_overflow category** | **169** (matches P011 on this snapshot) |

P011 emits one warning per `(page, margin_side)` when grouped text lines cross the
1.5"/1" margin rectangle beyond tolerance. Without a dedicated rollup, reviewers see many
per-page warnings without side-level page ranges or overflow summaries.

## What changed

### Finding metadata (`pdf_margins.py`)

- Warnings include `issue_type=margin_boundary_violation` and `triage_tier=informational`.
- PASS findings unchanged (no triage fields).

### Report outputs (`report_outputs.py`)

- New `build_p011_margin_triage_summary()` rollup in `grouped_summary.p011_margin_triage`:
  - raw / affected-page counts and compact page list
  - margin **side** counts and confidence distribution
  - **max** and **median** overflow (pt) by side
  - **margin-side page ranges** (e.g. `right_margin: 19-137`)
  - pages with multiple margin sides on one page
  - dominant margin side and total affected line count (sum)
  - triage note (includes compressed-PDF coordinate-shift caveat)
- Markdown reports add **P011 Margin/Overflow Triage** (before P013/P026 triage sections).

### Tests

- `tests/test_report_outputs.py`: P011 triage rollup, ranges, overflow summary, raw preservation, Markdown, coexistence with P013/P026.
- `tests/test_pdf_rules.py`: `triage_tier` and `issue_type` on warnings.

## What did not change

- `run_pdf_margin_rule()` geometry, artifact guard, and per-(page, side) grouping.
- Raw P011 count on the five-PDF set (see verification below).
- Severity levels (warnings remain WARNING).

## Privacy model

- Rollups use margin sides, overflow distances, line counts, page numbers, and confidence only.
- Generated audit JSON/Markdown under `data/evaluation/generated/` remain gitignored.

## Post-change verification (five-PDF set)

| Metric | Before refinement | After refinement |
|--------|------------------:|-----------------:|
| Grand total findings | 1,446 | 1,446 (unchanged) |
| P011 raw warnings | 169 | 169 (unchanged) |

Generated path: `data/evaluation/generated/current_auditor_after_p034_p011_triage/`

Example pattern (Yin H 4th compressed, aggregate only): dominant `right_margin` (43 of 70 P011 warnings on that file); side page ranges appear in `p011_margin_triage`.

## Expected effect

- **Better triage/actionability:** reviewers see margin-side page ranges and overflow stats before per-page P011 lines.
- **Not fewer raw findings:** summary-layer improvement only.

## Limitations

- Does not prove NJIT margin compliance; heuristic warnings only.
- Artifact guard suppresses some groups before emission; triage reflects emitted warnings only.
- Does not change P013/P026 triage or detection.
- Compressed PDFs (especially Yin H 4th) may show coordinate-shift patterns — manual review still required.

## Related docs

- P034 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`
- P013/P026 reporting precedents: `docs/evaluation/p013_reporting_actionability_refinement.md`, `docs/evaluation/p026_reporting_actionability_refinement.md`
