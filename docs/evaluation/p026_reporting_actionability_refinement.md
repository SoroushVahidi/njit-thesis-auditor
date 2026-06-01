# P026 Reporting Actionability Refinement

- **Date:** 2026-06-01
- **Baseline snapshot:** `docs/evaluation/current_auditor_after_p034_evaluation.md` (PR #70, commit `f8daccf`)
- **Scope:** **reporting and triage only** — body-font detection logic unchanged

## Motivation

From the P034-era full auditor snapshot on five evaluation PDFs:

| Metric | Value |
|--------|------:|
| Grand total findings | 1,446 |
| **P026 findings** | **415** (second-largest single rule after P013) |
| **font_format category** | **415** (matches P026 exactly on this snapshot) |

P026 emits one warning per `(page, issue_type)` when a majority of body-text spans on that page
show repeated font-family or font-size issues. Without a dedicated rollup, reviewers see many
similar per-page warnings and only a generic high-volume table row with a short
`observed_summary` sample.

## What changed

### Finding metadata (`pdf_font_compliance.py`)

- Page-level P026 findings include `triage_tier=informational` (severity remains WARNING).

### Report outputs (`report_outputs.py`)

- New `build_p026_font_triage_summary()` rollup in `grouped_summary.p026_font_triage`:
  - raw and affected-page counts with compact page list
  - issue-type counts (family vs size)
  - dominant font-label counts (family issues) and size-label counts (size issues)
  - pages with both issue types on the same page
  - **pattern page ranges** keyed by `issue_type/observed_summary` (e.g. `possible_body_font_family_issue/CMR12: 1-44`)
  - triage note explaining informational nature
- Markdown reports add **P026 Body Font Compliance Triage** (after P013 triage when present, before Findings by Rule).

### Tests

- `tests/test_report_outputs.py`: P026 triage rollup, pattern ranges, font-label counts, raw preservation, Markdown section, coexistence with `p013_triage`.
- `tests/test_pdf_rules.py`: `triage_tier` on synthetic family-issue finding.

## What did not change

- `check_pdf_font_compliance()` thresholds and per-page emission (one finding per page per issue type).
- Raw finding count for P026 on the five-PDF set (see post-change verification below).
- Severity levels (remain WARNING).

## Privacy model

- Rollups use issue types, font **labels** (PDF font names), size summaries, and page numbers only — not dissertation body text.
- Generated audit JSON/Markdown under `data/evaluation/generated/` remains gitignored.

## Post-change verification (five-PDF set)

Optional rerun after reporting change (gitignored outputs):

| Metric | Before refinement | After refinement |
|--------|------------------:|-----------------:|
| Grand total findings | 1,446 | 1,446 (unchanged) |
| P026 raw findings | 415 | 415 (unchanged) |

Markdown/JSON reports now include `grouped_summary.p026_font_triage` and the dedicated P026 triage section.

Generated path: `data/evaluation/generated/current_auditor_after_p034_p026_triage/` (all five files:
`p026_font_triage` in JSON and P026 Markdown triage section confirmed; Sebastian has 0 P026 so
no P026 triage block on that file).

## Expected effect

- **Better triage/actionability:** reviewers see dominant font labels and pattern page ranges before scrolling per-page P026 warnings.
- **Not fewer raw findings:** noise reduction is in the summary layer, not detection.

## Limitations

- P026 remains high-volume on LaTeX/Computer Modern PDFs; this does not validate NJIT font compliance.
- Pattern grouping uses `observed_summary` font/size labels, not span text content.
- Documents without P026 findings omit `p026_font_triage`.
- Does not change P013 triage or other rule behavior.

## Related docs

- P034 aggregate snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`
- P013 reporting refinement (precedent): `docs/evaluation/p013_reporting_actionability_refinement.md`
- Post–P013 triage output refresh: `docs/evaluation/current_auditor_after_p034_p013_triage_refresh.md`
