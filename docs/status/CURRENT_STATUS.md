# Current Status

> **Canonical, current-only status.** This is the entry point for "what is true
> right now." Older dated reports remain historical/forensic records under
> `docs/status/`.

_Last updated: 2026-09-21, on the R066 Ester degree-order follow-up/repair
branch. The `origin/main` SHA below was corrected on 2026-09-21 — it was
stale (pre-PR #546) as of the prior 2026-09-19 update._

## Main and R036 Branch

| Field | Value |
|---|---|
| Current `origin/main` SHA | `fce5868e07f731a55da12ca15b3ce869eda8890b` (merged through PR #546) |
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

## R046 Current Follow-Up State

R046/P046 covers List of Tables and List of Figures entry-number left-column
alignment. It checks whether the table/figure entry numbers align vertically in
one left column; it does not govern title text, hanging continuation indentation,
or right-column page-number alignment.

Ester's latest R046 adjudication says the reviewed Anthony and Praneeth cases
are false positives. No Ester-confirmed R046 true positive is available.

The selected policy remains local to P046:

- measure only rows that begin with a recognizable labeled or dotted
  table/figure entry-number token;
- exclude title continuation fragments, including fragments that carry leaders
  and page numbers;
- compare measured entry-number x positions against the median entry-number
  column using the existing 6 pt tolerance;
- keep synthetic strong left-column misalignment reportable;
- avoid student-, page-, title-, or dissertation-specific exceptions.

Current seven-dissertation R046 branch audit: Youra 0, Anthony 0, Muyeed 0,
Philip 0, Praneeth 0, Sebastian 0, Patrick 0; total 0. Relative to branch-start
behavior, the total changes from 6 to 0. All six removals are explained by
hanging-continuation/title fragments that were previously measured as
entry-number rows.

## R048 Current Follow-Up State

R048/P048 covers Q069/Q079: List of Tables and List of Figures page-number
alignment in the visual right column. The rule compares page-number token right
edges and retains the existing 10 pt tolerance.

Ester's reviewed Praneeth R048 case is a false positive because the page
numbers are consistently aligned. No Ester-confirmed R048 true positive is
available.

The root cause was P048 accepting the shared parser's page-number signal for
invalid Roman-looking title fragments such as `LC`. Canonical Roman numeral
validation is now applied locally when P048 selects complete entries, so those
fragments do not become P048 page-number entries. The shared parser, right-edge
anchor, and tolerance were not changed.

Current seven-dissertation R048 audit: Youra 1, Anthony 0, Muyeed 2, Philip 1,
Praneeth 0, Sebastian 0, Patrick 1; total 5, down from 6. Only the reviewed
Praneeth false positive changed. R046 remains total 0; R040 remains 43, R053
remains 1, and R054 remains 4.

Primary R048 record:

- `docs/status/p048_r048_ester_right_column_alignment_followup_20260919.md`
- `tests/test_pdf_rules.py`

## R078 Current Follow-Up State

R078/P078 covers Q005 first-person pronoun detection in the Abstract body only.
The documented set is standalone capital `I` plus `me`, `my`, `mine`, `we`,
`us`, `our`, and `ours`; references, chapters, headings, and other sections are
outside scope.

Ester adjudicated the Muyeed lowercase `i` in `i.e.` case as a false positive
and the Praneeth `we` case as a true positive. The detector now treats only
capital standalone `I` as the singular form while preserving the documented
case-insensitive plural/possessive forms. Shared text tokenization is unchanged.

Current seven-dissertation R078 audit: Youra 0, Anthony 0, Muyeed 0, Philip 0,
Praneeth 1, Sebastian 0, Patrick 0; total 1, down from 2. The reviewed Muyeed
false positive is removed and the reviewed Praneeth true positive remains.

Primary R078 record:

- `docs/status/p078_r078_ester_first_person_language_followup_20260919.md`
- `tests/test_p078_pdf_abstract_keywords.py`

## R066 Current Follow-Up State

R066/P066 covers Q025 degree ordering in the Biographical Sketch education
section. Ester confirmed Anthony's finding as a false positive: the degree
entries are already reverse chronological. The pre-fix detector mixed a
pre-education birth year and publication years into the degree-year stream.

The detector now requires an explicit education subsection, recognizes a
publication/presentation boundary in singular, plural, qualified/prefixed
(e.g. "Selected Publications"), compact PDF-extracted, and reversed-compact
heading forms, compares one year-only token per short entry line, and
conservatively skips ranges, fragmented dates, same-year ties, and ambiguous
sections. No shared tokenizer or Biographical Sketch parser changed. No
Ester-confirmed R066 true positive is available.

A 2026-09-21 repair (PR #547) fixed a Codex-reviewed regression: an earlier
version of this fix matched the publication/presentation boundary only
against an exact four-label set, which lost recall for singular and
qualified heading forms recognized before that change. The boundary check
now uses a general substring match instead, restoring that recall while
keeping compact/reversed-compact support. All five previously-removed
real-corpus findings (Youra, Anthony, Muyeed, Philip, Patrick) were
individually re-audited under the repaired detector and confirmed as
non-violations; see the full per-case table in the primary R066 record below.

Seven-document R066 audit: Youra 0, Anthony 0, Muyeed 0, Philip 0, Praneeth 0,
Sebastian 0, Patrick 0; total 0, down from 5. All removals are explained by
non-education or publication-year contamination. The 2026-09-21 boundary
repair does not change any of these seven counts.

Primary R066 record:

- `docs/status/r066_ester_degree_order_followup_20260920.md`
- `tests/test_p066_biosketch_degree_ordering.py`

## R068 Current Follow-Up State

R068/P068 covers a structural extension beyond Q013 (Approval Page committee
role labels and signature/date blocks); Q015–Q020 remain manual-only. Ester
confirmed the Anthony, Praneeth, and Sebastian `approval_page_
signature_blocks_sparse` findings as false positives: committee-block layout
depends on committee size and how many lines each entry occupies, not a
fixed indicator-count ratio. Structural inspection confirmed the underlying
signal is unreliable across templates — all three false positives had
correctly-detected role labels and advisor labels but zero text-extractable
date/signature/blank indicator lines, consistent with signature lines being
rendered as non-text graphics or differently-worded labels in those
templates, not missing blocks.

`approval_page_signature_blocks_sparse` reporting is retired (gated off via
`_SIGNATURE_BLOCKS_SPARSE_REPORTING_ENABLED = False`), following the same
pattern used for R036's retired fixed-1.6 threshold. The counting logic is
retained for compatibility/future re-validation but no longer controls
whether a finding is emitted. `approval_page_advisor_role_label_missing` is
unaffected and remains active — it never fired on the seven-document corpus
and has no adverse reviewer evidence.

Seven-document R068 audit: Youra 0, Anthony 0, Muyeed 0, Philip 0, Praneeth 0,
Sebastian 0, Patrick 0; total 0, down from 3. No Ester-confirmed R068 true
positive is available.

Primary R068 record:

- `docs/status/r068_ester_approval_committee_spacing_followup_20260921.md`
- `tests/test_p068_approval_page_committee_blocks.py`

`LEADER_PLACEMENT_RULE_GAP` remains separate and unimplemented.

Primary R046 records:

- `docs/status/p046_r046_ester_left_column_alignment_followup_20260919.md`
- `docs/evaluation/p046_current_dataset_evaluation.md`
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
