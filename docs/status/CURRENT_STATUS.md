# Current Status

> **Canonical, current-only status.** This is the entry point for "what is true
> right now." Older dated reports remain historical/forensic records under
> `docs/status/`.

_Last updated: 2026-09-19, after the R036 merge and post-merge R011 targeted
follow-up validation._

## Main and R036 Branch

| Field | Value |
|---|---|
| Current `origin/main` SHA | `88ffe32043fa0c909b4568e380cb2d6aac72fc1e` |
| R036 production branch | `fix/r036-production-page-relative-suppression-20260916` (merged by PR #538) |
| R036 audited base | `e5105018960aa9b478ad87e1c51e70d749dcaa16` |
| R036 pre-documentation-sync HEAD | `14a0d68daa446c4bd23147c9560c9213d52ef050` |
| R036 implementation/privacy-audited HEAD | `b277f34fe8ec7e01a32c83a1a23af82d5f7f8556`; superseded only by final documentation/privacy reconciliation |
| R036 relation to `origin/main` after final documentation/privacy reconciliation | Merged |
| Deployment | Not updated by this pass |
| Manifest status snapshot | `336b28c`; **3192 passed** |
| R036 final-pass validation | `ruff check .` clean; `mypy src` clean; `python -m pytest`: **3539 passed**, 5 skipped, 3 warnings |
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

## R011 Current State

R011/P011 covers text crossing the required margin rectangle: 1.5 inches on
the left and 1 inch on the top, right, and bottom. The current implementation
is `src/njit_auditor/rules/pdf_margins.py`; student-facing wording and
classification helpers live in `src/njit_auditor/p011_margin_presentation.py`.

The Ester-adjudicated R011 follow-up is already incorporated on current main:

- The Muyeed physical-page-36 / printed-page-15 bottom-margin case is a
  confirmed false positive and must not be reported.
- The Patrick physical-page-88 / printed-page-76 right-margin reference-entry
  case is a confirmed true violation and must remain reported.
- The implemented policy keeps the normal 3.0 pt tolerance for left/top/right,
  keeps the bounded reference-list allowance at 6.0 extra pt, and uses a
  9.3 pt bottom-margin tolerance for the confirmed template/line-box variation
  cluster. The policy is geometry-based, not dissertation-, page-, text-, or
  authoring-tool-specific.

Fresh post-R036 validation on the seven private dissertations produced these
R011 counts: Youra 1, Anthony 38, Muyeed 18, Philip 53, Praneeth 70,
Sebastian 6, Patrick 5; total 191. Relative to the pre-follow-up baseline at
`368d14f4271048a82b5cd2d27f00b5e6375a4ce1`, the net change is 223 to 191,
all page/side removals are bottom-margin findings in the 9.2-9.3 pt template
variation cluster, and Patrick's 18.0 pt right-margin finding remains present.

Primary R011 records:

- `docs/status/p011_r011_batch_2026_08_false_positive_fix.md`
- `docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md`
- `tests/test_p011_esther_r011_batch_2026_08.py`
- `tests/test_p011_bottom_margin_synthetic.py`

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

After review and merge of any R011 post-R036 status/validation PR, the next
engineering task should be the Ester-adjudicated R015 follow-up. Do not begin
R015 until the R011 task is closed.

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
