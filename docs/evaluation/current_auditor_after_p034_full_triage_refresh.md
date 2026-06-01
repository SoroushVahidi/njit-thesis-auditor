# Current Auditor Full Triage Refresh (P011 + P013 + P026)

- **Date:** 2026-06-01
- **Baseline commit:** `ae61e16` (after PR #74 P011 margin triage)
- **Auditor scope:** P001–P034 implemented (PDF audit P011–P034)
- **Purpose:** Single canonical local five-PDF rerun with all high-volume reporting triage rollups

## Canonical generated-output path (gitignored, not committed)

**Use this path for the latest full audit reports:**

`data/evaluation/generated/current_auditor_after_p034_p011_triage/`

| Artifact | Description |
|---|---|
| `aggregate_summary.json` | Cross-file totals |
| `*_report.json` / `*_report.md` | Per-file audit outputs with triage sections |
| `sebastian_fine_clean_baseline.pdf` | Local ZIP extract only |

Each JSON report includes `grouped_summary.p011_margin_triage`, `p013_triage`, and
`p026_font_triage` when those rules have warnings. Markdown reports include the
P011, P013, and P026 triage sections before **Findings by Rule**.

## Aggregate counts (unchanged from P034 snapshot)

| Metric | Value |
|--------|------:|
| Grand total findings | **1,446** |
| P011 warnings | **169** |
| P013 raw findings | **461** |
| P026 warnings | **415** |

Reporting triage does not change detection; only JSON/Markdown structure and summaries.

## Historical / superseded generated folders

These local folders are from incremental reporting refreshes and remain valid for history:

| Folder | Superseded by | Notes |
|---|---|---|
| `current_auditor_after_p034/` | Full triage path above | Pre–triage JSON only (no `*_triage` rollups) |
| `current_auditor_after_p034_p013_triage/` | Full triage path | Post–PR #71 P013 only |
| `current_auditor_after_p034_p026_triage/` | Full triage path | Post–PR #73 P026 only |

Do not commit any path under `data/evaluation/generated/`.

## Related committed docs

- Aggregate snapshot (counts): `docs/evaluation/current_auditor_after_p034_evaluation.md`
- P011 triage: `docs/evaluation/p011_reporting_actionability_refinement.md`
- P013 triage: `docs/evaluation/p013_reporting_actionability_refinement.md`
- P026 triage: `docs/evaluation/p026_reporting_actionability_refinement.md`
- P013-only refresh note: `docs/evaluation/current_auditor_after_p034_p013_triage_refresh.md`

## Privacy

Aggregate counts and pattern labels only in committed documentation. No dissertation body text.
