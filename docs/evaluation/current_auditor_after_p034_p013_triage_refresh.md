# Current Auditor Refresh After P013 Triage Reporting (PR #71)

- **Date:** 2026-06-01
- **Baseline commit:** `0cf537a` (post–PR #71 P013 reporting/actionability refinement)
- **Auditor scope:** P001–P034 implemented (PDF layout audit P011–P034)
- **Purpose:** Regenerate full five-PDF audit outputs so JSON/Markdown reports include the new `p013_triage` rollup and **P013 Page-Number Candidate Triage** section. Detection logic is unchanged from the P034-era snapshot in `docs/evaluation/current_auditor_after_p034_evaluation.md`.

## Generated outputs (gitignored, not committed)

All artifacts live under:

`data/evaluation/generated/current_auditor_after_p034_p013_triage/`

| Artifact | Description |
|---|---|
| `aggregate_summary.json` | Cross-file totals and P013 verification flags |
| `*_report.json` | Per-file audit JSON (includes `grouped_summary.p013_triage`) |
| `*_report.md` | Per-file Markdown (includes P013 triage section) |
| `sebastian_fine_clean_baseline.pdf` | Local ZIP extract only |

Pre–PR #71 outputs remain in `data/evaluation/generated/current_auditor_after_p034/` (no `p013_triage`).

## Aggregate results (unchanged from P034 snapshot)

| Metric | Value |
|--------|------:|
| **Grand total findings** | **1,446** |
| **P013 raw findings** | **461** |
| P031–P034 findings | 0 |

Per-file totals match the historical P034 snapshot (317 + 275 + 340 + 464 + 50 = 1,446). P013 per file: 95 + 104 + 104 + 133 + 25 = 461.

## P013 triage verification

On all five PDFs:

| Check | Result |
|---|---|
| JSON `grouped_summary.p013_triage` present | Yes (all five) |
| Markdown **P013 Page-Number Candidate Triage** section | Yes (all five) |
| Raw P013 findings in JSON `findings` array | Yes (preserved) |
| Raw P013 count vs pre-refresh snapshot | **461** (unchanged) |

Example triage fields (aggregate labels only; Yin H 4th compressed): `pattern_page_ranges` includes `bottom_center/arabic: 19-137` and `bottom_center/roman_lower: 6-18`; `affected_page_count` 132 on 133 raw P013 findings (one document-level overview).

## What changed vs pre–PR #71 generated outputs

- **Reporting only:** reviewers can use pattern page ranges, issue-type counts, multi-candidate page lists, and informational `triage_tier` before scrolling per-page P013 warnings.
- **Detection unchanged:** same rules, same raw finding counts and severities.

## Actionability improvement

The P034-era snapshot doc (`current_auditor_after_p034_evaluation.md`) noted that P013 was the largest single rule (461 findings) but generated JSON lacked `p013_triage`. This refresh confirms the post–PR #71 report pipeline on real evaluation PDFs without altering the historical aggregate counts documented there.

## Privacy

- Committed documentation uses file labels, rule IDs, page numbers, and counts only.
- No dissertation body text, titles, author names, or committee names are quoted.
- Generated JSON/Markdown remain gitignored.

## Limitations

- TeX audit (P001–P010) not included.
- Does not re-measure precision/recall vs EF comments.
- Sebastian PDF extracted locally from the tracked ZIP; not committed.
- If future code changes detection, rerun this path or a successor; this refresh is tied to commit `0cf537a`.

## Related docs

- P034 aggregate snapshot (historical counts): `docs/evaluation/current_auditor_after_p034_evaluation.md`
- P013 reporting refinement: `docs/evaluation/p013_reporting_actionability_refinement.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
