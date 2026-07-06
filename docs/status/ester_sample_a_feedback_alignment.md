# Sample A Feedback Alignment Status

**Recorded:** 2026-07-06  
**Baseline `main`:** `1b5fd306764c197450e26596d162cece3fc7546a` (before this PR)  
**Ester claim:** only **1 of 39** comments on Sample A (Cibaku first review) was correct.

## Source document access

| Document | URL | Accessible in coding environment? | Fallback used |
|---|---|---|---|
| NJIT Thesis Auditor Formatting Rules (Google Sheet) | [Sheet](https://docs.google.com/spreadsheets/d/1IohAmbslfX1orMDr7gx6oJyGGTqAV_AAtF31GP-57Gc/edit) | **No** (Google sign-in required) | `data/specs/ester_p_rule_feedback.json` + `data/specs/ester_warning_wording_map.json` (extracted 2026-07-06) + P011 example from Ester's latest email |
| Sample A feedback (Google Doc) | [Doc](https://docs.google.com/document/d/1h-Jq_tAN4I3q-97qv5MKk9L1tff9Mmgq/edit) | **No** (Google sign-in required) | Built-in `ester_sample_a` audit metadata, `docs/status/warning_clarity_location_actionability_audit.md`, and `data/processed/ef_comment_coverage.json` (privacy-safe summaries only) |

Do not treat repo mirrors as live unless re-verified against Drive originals.

## Built-in Sample A (`ester_sample_a`) — tool output snapshot

From prior audits on current detectors (39 problem findings):

| Rule families present | P011, P013, P015, P016, P020, P027, P028, P044, P051 |
|---|---|

This pass did **not** re-run Sample A for detector counts (wording/UI-only scope).

## Alignment taxonomy (per Ester feedback item class)

Because the live Google Doc was inaccessible, items below are grouped by **known mismatch classes** documented in prior evaluation work and Ester's 1/39 correctness claim. Individual comment text is **not** quoted (privacy).

| Issue class | Typical Sample A symptom | Classification | Fixed in this PR? | Deferred |
|---|---|---|---|---|
| Vague yes/no question / internal label ("Margin boundary violation") | Student sees engineer label, not Ester Column C question | **wording/remediation mismatch** | **Yes** for P011 and mapped priority rules via `ester_warning_wording_map.json` | Remaining rules without clear Column C/E |
| Vague P011 remediation without inch values first | "Adjust paragraph/text wrapping..." without 1.5"/1" | **wording/remediation mismatch** | **Yes** — Ester remediation leads; context-specific guidance is secondary | — |
| UI workflow: topic table before page-order cards | Students edit front-to-back but topic index appeared first | **UI duplication/confusion** | **Yes** — page order section moved before topic index; topic table collapsed | Broader single-surface simplification |
| P011 duplicate cards on same pages (e.g. pages 92, 98) | Same page under multiple margin cards | **UI duplication/confusion** | No | Grouping/merge-by-page UI |
| P013 false positives / body-text IDs | Comments on non-page-number text | **detector false positive** | No (P013 body-ID fix was separate PR #476) | Further P013/P019 tuning |
| P015/P016 spacing location precision | Page-level only, no paragraph pointer | **detector false positive / geometry** | No | Highlight geometry |
| P020/P027 heading case mismatches vs Ester manual review | Tool flags differ from EF annotations | **detector false positive / policy mismatch** | No | Golden comparison per rule |
| P044 abstract indentation | Partial vs Ester atomic Q002/Q003 | **policy mismatch / needs split** | No | P014/P015 atomic split |
| P051 copyright year advisory | Wording OK; detection may disagree with EF | **detector false positive** | No | Detector review |
| Broad rules (P014, P017, P018) | One card bundles many matrix questions | **wording/remediation mismatch** | No | Atomic split project |
| P025 Digital Commons wrapper | Not in Sample A | n/a | n/a | — |
| Confidence tier emphasis | Ester: not the main issue | **UI duplication/confusion** | No confidence work (explicit guardrail) | — |

## What this PR fixed (presentation only)

1. **Column C/E source-of-truth map** — `data/specs/ester_warning_wording_map.json` for P011, P012, P013, P019, P021, P026, P035, P036, P040, P053, P054, P068.
2. **P011** — yes/no question includes tables/figures; remediation leads with 1.5" left and 1" other margins.
3. **Student-facing card titles** — mapped rules use Ester questions instead of internal issue-type labels where available.
4. **UI order** — Findings in page order before Findings by topic; topic index collapsed as secondary.

## What remains deferred (detector / policy)

- Sample A **correctness rate** toward Ester's 1/39 benchmark — requires item-by-item EF comment ingestion when the Google Doc is accessible.
- P011 merge-by-page / cross-link duplicate cards on the same page.
- P014, P015, P017, P018 atomic question splits per Ester sheet.
- P021/P026 policy limits (wording-only alignment done; thresholds unchanged).
- P084 — out of scope.
- Table/figure **image** margin detection (text-layer limitation).

## Validation note

Warning counts, detector logic, confidence logic, rule IDs, and JSON export schema were unchanged in this PR.
