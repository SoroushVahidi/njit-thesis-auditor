# Current Status

> **Canonical, current-only status.** This is the entry point for "what is true
> right now." Older dated reports remain historical/forensic records under
> `docs/status/`.

_Last updated: 2026-09-19, on the R040 Ester LoF terminal-punctuation
follow-up branch._

## Main and R036 Branch

| Field | Value |
|---|---|
| Current `origin/main` SHA | `26e38e60f12b67e3c1f0fbc9d4a1aea01b9e5dec` |
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

## R015 Current State

R015/P015 covers body paragraph indentation. The current follow-up branch is
merged on current main by PR #540.

Ester's latest adjudication says the Youra physical-page-101 R015 candidate was
reported on the wrong line: the following continuation line should not be
reported, but the actual paragraph-start line immediately above is a real R015
missing-indent violation and should be reported. Earlier adjudicated false
positives on Youra physical page 86, Muyeed physical page 144, and Philip
physical page 17 must remain non-reported because they are continuation/math
fragmentation cases rather than true paragraph starts.

The selected policy keeps the existing geometry-based paragraph grouping and
math/special-character reassembly, but separates run-in paragraphs from heading
exemptions:

- bold run-in phrase plus same-row regular continuation remains one paragraph;
- the bold run-in line is the paragraph-start/report anchor for R015;
- run-in paragraphs are not heading-exempt from `missing_later_indent`;
- run-in paragraphs are still excluded from page-style baseline estimation so
  they do not distort unrelated page confidence gates.

The separate unnumbered-bold-heading issue Ester noted is not implemented in
R015. No existing P020/P027/P026 rule currently owns it; it is recorded as a
future rule gap.

Current seven-dissertation R015 branch audit: Youra 1, Anthony 0, Muyeed 1,
Philip 6, Praneeth 0, Sebastian 0, Patrick 0; total 8. Relative to the
pre-follow-up behavior, the only material change is the intended Youra
page-101 correct-line recovery.

Post-merge validation passed: `ruff check .` clean, `mypy src` clean,
`python -m pytest` with 3544 passed and 3 warnings, targeted R015 with 77
passed, shared regressions with 145 passed and 643 deselected, and the
seven-document R015 corpus audit.

Primary R015 records:

- `docs/status/p015_r015_esther_feedback_false_positive_fix_20260825.md`
- `docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md`
- `tests/test_p015_esther_r015_batch_2026_08.py`
- `tests/test_p015_r015_ester_run_in_heading_20260831.py`

## R053 Current State

R053/P053 covers List of Tables entries that should not end with a terminal
period. The R053 follow-up is merged on current main by PR #541.

Ester's latest R053 adjudication says the Praneeth physical-page-14 /
printed-page-xi List of Tables finding is a false positive. The apparent
terminal periods are leader dots between the title and the page number, not
punctuation belonging to the semantic title.

The selected policy remains local to P053:

- keep the existing page-number and legacy ASCII leader stripping behavior;
- additionally strip trailing visual dot leaders made from ASCII periods,
  Unicode ellipses, or middle-dot characters;
- preserve an isolated title-ending period before separated leaders, so genuine
  semantic terminal periods still report;
- avoid student-, page-, title-, or dissertation-specific exceptions.

Current seven-dissertation R053 branch audit: Youra 0, Anthony 0, Muyeed 1,
Philip 0, Praneeth 0, Sebastian 0, Patrick 0; total 1. Relative to the
pre-follow-up behavior, the only material changes are two Praneeth List of
Tables leader-dot artifacts removed, including the reviewed false positive.

Post-merge validation passed: `ruff check .` clean, `mypy src` clean,
`python -m pytest` with 3545 passed, 5 skipped, and 3 warnings, targeted R053
with 19 passed and 770 deselected, P040/P053/P054 slice with 44 passed and 745
deselected, and the seven-document R053 corpus audit.

Primary R053 records:

- `docs/status/p053_r053_leader_dot_terminal_period_followup_20260918.md`
- `tests/test_pdf_rules.py`

## R054 Current State

R054/P054 covers Table of Contents entries that should not end with a terminal
period. The R054 follow-up is merged on current main by PR #542.

Ester's latest R054 adjudication says the Praneeth physical-page-11 /
printed-page-viii Table of Contents finding is a false positive. The apparent
terminal periods are leader dots between the TOC title and the page number,
not punctuation belonging to the semantic title.

The selected policy remains local to P054:

- keep the existing page-number, legacy ASCII leader, and hyphen/underscore
  leader stripping behavior;
- additionally strip trailing visual dot leaders made from ASCII periods,
  Unicode ellipses, or middle-dot characters;
- repeat stripping when PDF extraction leaves multiple trailing leader
  fragments on the same entry;
- preserve an isolated title-ending period before separated Unicode leaders,
  so genuine semantic terminal periods still report;
- avoid student-, page-, title-, or dissertation-specific exceptions.

Current seven-dissertation R054 branch audit: Youra 1, Anthony 0, Muyeed 1,
Philip 2, Praneeth 0, Sebastian 0, Patrick 0; total 4. Relative to the
pre-follow-up behavior, the only material changes are six Praneeth Table of
Contents leader-dot artifacts removed, including the reviewed false positive.

R053 regression remains unchanged: Youra 0, Anthony 0, Muyeed 1, Philip 0,
Praneeth 0, Sebastian 0, Patrick 0; total 1. R040/P040 output did not change
on the R054 branch and is handled by the separate R040 follow-up below.

Primary R054 records:

- `docs/status/p054_r054_leader_dot_terminal_period_followup_20260918.md`
- `tests/test_pdf_rules.py`

## R040 Current Follow-Up State

R040/P040 covers List of Figures entries that should end with terminal
punctuation. The current follow-up branch is
`fix/r040-ester-lof-terminal-punctuation-followup-20260919`; it is not merged.

Ester's latest R040 adjudication says the Anthony and Praneeth reviewed List of
Figures findings are false positives. Sebastian's reviewed case is a real
formatting issue, but Ester's explanation is leader placement: the leader dots
should start right after the last letter of the title. R040 remains a
punctuation rule, not a leader-placement rule.

The selected policy remains local to P040:

- reconstruct the semantic LoF description after page-number removal;
- strip trailing visual leaders made from ASCII periods, Unicode ellipses, or
  middle-dot characters;
- preserve terminal punctuation before or at the start of a visual leader run,
  so leader-placement defects are not mislabeled as missing punctuation;
- keep genuine missing-punctuation cases reportable;
- avoid student-, page-, title-, or dissertation-specific exceptions.

Current seven-dissertation R040 branch audit: Youra 3, Anthony 0, Muyeed 5,
Philip 3, Praneeth 7, Sebastian 0, Patrick 25; total 43. Relative to the
pre-follow-up behavior, the total changes from 179 to 43. The reviewed Anthony
false positive is removed, the reviewed Praneeth false positive is removed, and
Sebastian no longer receives a wrong R040 punctuation explanation.

No current rule owns LoF/LoT leader dots beginning immediately after the
semantic title. The R040 follow-up records this as **LEADER_PLACEMENT_RULE_GAP**
without implementing a new unrelated rule.

R053 regression remains unchanged at total 1. R054 regression remains
unchanged at total 4.

Primary R040 records:

- `docs/status/p040_r040_ester_lof_terminal_punctuation_followup_20260919.md`
- `tests/test_pdf_rules.py`

## Feedback-Cycle Rule State

Use human-facing `Rxxx` identifiers in reviewer/project-progress prose. Use
internal `Pxxx` identifiers only when describing implementation files, tests, or
rule registry entries.

| State | Rules |
|---|---|
| Closed or conservative after Ester-adjudicated false-positive review | R011, R015, R016, R017, R018, R019/R028, R020, R023, R024, R026 except Latin Modern alias, R033, R035, R036, R053, R055 |
| Closed, engineering-confirmed genuine violation | R085 |
| Open policy question | R018 alignment note for sections 1.3.3/1.3.4/1.3.5 |
| Genuinely unresolved | R034, Latin Modern font-alias expansion |
| No current selected finding/action | R012-R014, R022, R025, R027, R029-R032 |
| In current follow-up branch | R054 |
| Not yet reviewed this cycle | R037 onward, except separately handled R053/R054/R055/R085 |

## Next Work Sequence

After review and merge of the R054 PR, begin the separate Ester-adjudicated
R040 follow-up.

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
