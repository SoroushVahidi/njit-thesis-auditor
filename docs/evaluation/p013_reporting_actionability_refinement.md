# P013 Reporting Actionability Refinement

- Date: 2026-06-01
- Baseline snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md` (PR #70, commit `f8daccf`)
- Scope: **reporting and triage only** — candidate detection logic unchanged

## Motivation

From the P034-era full auditor snapshot on five evaluation PDFs:

| Metric | Value |
|--------|------:|
| Grand total findings | 1,446 |
| **P013 findings** | **461** (largest single rule) |
| page_numbering category | 556 (largest category) |

P013 is intentionally high-volume: it flags heuristic page-number **candidates** for manual NJIT verification, not confirmed defects. Without a dedicated rollup, reviewers see hundreds of near-identical per-page warnings and a generic high-volume table row with limited position/style context.

## What changed

### Finding metadata (`pdf_page_numbers.py`)

- Document-level P013 overview now uses `issue_type=p013_document_overview` (was empty), separating it from page-level `page_number_candidate` in grouped summaries.
- Page-level and overview findings include `triage_tier=informational` to signal triage-only warnings without changing severity levels.

### Report outputs (`report_outputs.py`)

- New `build_p013_triage_summary()` rollup in `grouped_summary.p013_triage`:
  - raw / page-level / document overview counts
  - affected page count and compact page ranges
  - issue-type, position-type, number-style, and confidence counts
  - pages with multiple candidates (count + compact range)
  - position/style **pattern page ranges** (e.g. `bottom_center/arabic: 6-50`)
  - triage note explaining informational nature
- Markdown reports add **P013 Page-Number Candidate Triage** section (between Repeated Findings Summary and Findings by Rule) when P013 is present.

### Tests

- `tests/test_report_outputs.py`: P013 triage rollup, consecutive-page pattern ranges, raw findings preserved, Markdown section, non-P013 rules unaffected.
- `tests/test_pdf_rules.py`: document overview `issue_type` and `triage_tier` on page findings.

## What did not change

- `detect_page_number_candidates()` and per-page emission logic (one warning per page with candidates).
- P019 sequence/style checks (still use raw candidates internally).
- Raw finding count for P013 on the five-PDF set (see post-change verification below).
- Severity levels (remain WARNING; no demotion to PASS).

## Privacy model

- Committed docs use aggregate counts and pattern labels only (no dissertation body text, author names, or titles).
- Generated audit JSON/Markdown under `data/evaluation/generated/` remains gitignored.

## Post-change verification (five-PDF set)

Optional rerun after reporting change (gitignored outputs):

| Metric | Before refinement | After refinement |
|--------|------------------:|-----------------:|
| P013 raw findings (aggregate) | 461 | 461 (unchanged) |
| Page-level P013 warnings | 456 | 456 (unchanged) |
| Document overview | 5 | 5 (unchanged) |

Markdown/JSON reports now include `grouped_summary.p013_triage` and the dedicated P013 triage section for faster review.

## Expected effect

- **Better triage/actionability**: reviewers see pattern-level page ranges and multi-candidate pages first.
- **Not fewer raw findings**: noise reduction is in the summary layer, not detection.
- Generic `high_volume_rules` row for P013 now splits `p013_document_overview` vs `page_number_candidate` issue types.

## Limitations

- P013 remains high-volume by design; this does not validate NJIT page-number compliance.
- Pattern ranges group by `observed_summary` (position/style), not by candidate text content (privacy-safe).
- Documents without P013 findings omit `p013_triage`.
- Does not change EF-comment overlap metrics or P019 behavior.
