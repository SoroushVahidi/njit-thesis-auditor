# Current Status

> **Canonical, current-only status.** This is the entry point for "what is true
> right now." Older dated reports remain historical/forensic records under
> `docs/status/`.

_Last updated: 2026-09-19, during the R036 final integration-readiness pass on
`fix/r036-production-page-relative-suppression-20260916`._

## Main and R036 Branch

| Field | Value |
|---|---|
| Current `origin/main` SHA | `e5105018960aa9b478ad87e1c51e70d749dcaa16` |
| R036 production branch | `fix/r036-production-page-relative-suppression-20260916` |
| R036 audited base | `e5105018960aa9b478ad87e1c51e70d749dcaa16` |
| R036 pre-documentation-sync HEAD | `14a0d68daa446c4bd23147c9560c9213d52ef050` |
| R036 implementation/privacy-audited HEAD | `b277f34fe8ec7e01a32c83a1a23af82d5f7f8556`; superseded only by final documentation reconciliation |
| R036 relation to `origin/main` after final documentation reconciliation | 8 commits ahead, 0 behind |
| Deployment | Not updated by this pass |
| Manifest status snapshot | `336b28c`; **3192 passed** |
| R036 final-pass validation | `ruff check .` clean; `mypy src` clean; `python -m pytest`: **3544 passed**, 3 warnings |
| Rule inventory | P001–P085 implemented; no remaining non-inventory project task IDs; next new internal rule ID is P086 |

## Current Evaluation Corpus

The current human-validation corpus is seven private dissertation PDFs: Youra,
Anthony, Muyeed, Philip, Praneeth, Sebastian, and Patrick. Elbert is excluded.
These files remain local under `data/evaluation/private/`, ignored by Git, and
must not be quoted, uploaded, or committed.

## R036 Current State

R036/P036 covers inter-entry spacing between distinct entries on Table of
Contents, List of Tables, and List of Figures pages. Ester's authoritative
policy is:

- Separate TOC/List entries should be double spaced.
- Wrapped physical lines belonging to the same long title may be single spaced.

As of the September 14 and September 16, 2026 reviewer feedback, there are 24
known Ester-confirmed R036 false positives and 0 Ester-confirmed R036 true
positives. The production branch therefore intentionally uses a conservative
page-relative policy with three internal outcomes:

- `SUPPRESS`: the candidate matches normal local page rhythm.
- `ABSTAIN`: the context is too sparse, structurally reconstructed, or otherwise
  unreliable.
- `REPORT`: reserved for a future strong positive gate, currently disabled
  because no real R036 true positive has been reviewed.

The retired fixed `1.6` spacing ratio remains only for compatibility; it must
not control production reporting. Expected production behavior on the
seven-dissertation corpus is zero reported R036 findings: 448 candidates, 345
suppressed, 103 abstained, 0 reported. All 24 known Ester-confirmed false
positives must remain `SUPPRESS` or `ABSTAIN`, never `REPORT`.

Primary R036 records:

- `docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md`
- `docs/status/r036_split_section_number_recovery_20260914.md`
- `docs/status/r036_page_relative_spacing_experiment_20260916.md`
- `docs/status/r036_patrick_lof_anomaly_resolution_20260916.md`
- `docs/status/r036_production_page_relative_suppression_design_20260916.md`
- `data/evaluation/r036_ester_false_positive_ground_truth_20260916.json`

## Feedback-Cycle Rule State

Use human-facing `Rxxx` identifiers in reviewer/project-progress prose. Use
internal `Pxxx` identifiers only when describing implementation files, tests, or
rule registry entries.

| State | Rules |
|---|---|
| Closed or conservative after Ester-adjudicated false-positive review | R011, R015, R016, R017, R018, R019/R028, R020, R023, R024, R026 except Latin Modern alias, R033, R035, R036, R055 |
| Closed, engineering-confirmed genuine violation | R085 |
| Open policy question | R018 alignment note for sections 1.3.3/1.3.4/1.3.5 |
| Genuinely unresolved | R034, Latin Modern font-alias expansion |
| No current selected finding/action | R012-R014, R022, R025, R027, R029-R032 |
| Not yet reviewed this cycle | R037 onward, except separately handled R055/R085 |

## Next Work Sequence

After R036 is merged, the next engineering task should be the newly
Ester-adjudicated R011 targeted follow-up cases. Do not start R011 from the
R036 production branch.

## Repository Hygiene Notes

- Known historical LFS hygiene debt remains: some tracked binaries match current
  LFS patterns but exist as ordinary Git objects. No history rewrite has been
  performed.
- Private evaluation dissertations stay local and ignored. Do not commit
  reviewer packages or dissertation content unless a task explicitly requires a
  redacted/synthetic artifact.
- `scripts/ester_rule_consistency_audit.py` still requires local, untracked
  `results/ester_feedback_raw/*.xlsx` input and is not fresh-clone/CI runnable
  without a redacted or synthetic stand-in.
