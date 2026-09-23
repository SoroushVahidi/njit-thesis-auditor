# Current Status

> **Canonical, current-only status.** This is the entry point for "what is true
> right now." Older dated reports remain historical/forensic records under
> `docs/status/`.

_Last updated: 2026-09-23. All rule work through R086/P086 is merged to
`main`. Ester has now answered the final three open reviewer questions
(R018, R026 Latin Modern, leader placement). Their implementation was merged
to `main` via PR #553 (squash commit `72c8e1f`); R026 needed no detector
change. Repository merge does not imply production deployment — see
`docs/status/ester_final_three_clarifications_20260923.md`._

## Main and R036 Branch

| Field | Value |
|---|---|
| Current `origin/main` SHA | `72c8e1f82316fd25979eac88d5bc25d1652c0441` (merged through PR #553) |
| R036 production branch | `fix/r036-production-page-relative-suppression-20260916` (merged by PR #538) |
| R036 audited base | `e5105018960aa9b478ad87e1c51e70d749dcaa16` |
| R036 pre-documentation-sync HEAD | `14a0d68daa446c4bd23147c9560c9213d52ef050` |
| R036 implementation/privacy-audited HEAD | `b277f34fe8ec7e01a32c83a1a23af82d5f7f8556`; superseded only by final documentation/privacy reconciliation |
| R036 relation to `origin/main` after final documentation/privacy reconciliation | Merged |
| Deployment | Not updated: PR #553 (`web_app.py` public cards R018R/R018S included) is merged to `main`, but no live service restart/deployment has been performed |
| Manifest status snapshot | `336b28c`; **3192 passed** |
| R036 final-pass validation | `ruff check .` clean; `mypy src` clean; `python -m pytest`: **3539 passed**, 5 skipped, 3 warnings |
| Rule inventory | P001–P086 implemented and formally registered (`data/processed/rules/project_added_rules.json`); no remaining non-inventory project task IDs; next unused internal rule ID is P087 (see "R086 Current State" below for provenance; verified free: no existing source file or reference) |

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
punctuation. The follow-up branch
`fix/r040-ester-lof-terminal-punctuation-followup-20260919` is merged to
`main` (PR #543).

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

R040 still does not own leader placement. The former
**LEADER_PLACEMENT_RULE_GAP** is now reviewer-resolved (Ester, 2026-09-23:
TOC + List of Tables + List of Figures; leaders after the final title line;
one space allowed) and implemented under P018, merged via PR #553 — see "Ester Final
Three Clarifications" below.

R053 regression remains unchanged at total 1. R054 regression remains
unchanged at total 4.

Primary R040 records:

- `docs/status/p040_r040_ester_lof_terminal_punctuation_followup_20260919.md`
- `tests/test_pdf_rules.py`

## R046 Current Follow-Up State

R046/P046 covers List of Tables and List of Figures entry-number left-column
alignment. It checks whether the table/figure entry numbers align vertically in
one left column; it does not govern title text, hanging continuation indentation,
or right-column page-number alignment. The follow-up is merged on current main
by PR #544.

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
edges and retains the existing 10 pt tolerance. The follow-up is merged on
current main by PR #545.

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
outside scope. The follow-up is merged on current main by PR #546.

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
The follow-up (plus its 2026-09-21 boundary repair) is merged on current main
by PR #547.

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
role labels and signature/date blocks); Q015–Q020 remain manual-only. The
follow-up is merged on current main by PR #548. Ester confirmed the Anthony,
Praneeth, and Sebastian `approval_page_
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

Leader placement is handled separately under P018 (see "Ester Final Three
Clarifications" below), not by R046.

Primary R046 records:

- `docs/status/p046_r046_ester_left_column_alignment_followup_20260919.md`
- `docs/evaluation/p046_current_dataset_evaluation.md`
- `tests/test_pdf_rules.py`

## R021 Current State

R021/P021 covers the abstract word-count limit for the detected degree
type. Ester's live NJIT Thesis Auditor Formatting Rules sheet explicitly
states MS thesis abstracts must be 200 words or fewer and PhD dissertation
abstracts must be 400 words or fewer. The detector previously used stale
`MS_WORD_LIMIT=150`/`PHD_WORD_LIMIT=350` constants — a real constants
conflict against her own already-stated policy, not an open question, so
no new Ester input was needed to fix it.

`PHD_WORD_LIMIT`/`MS_WORD_LIMIT` in `latex_abstract.py` (shared by both the
LaTeX-source and PDF paths) are now 400/200, and every dependent piece of
student-facing wording plus the live `ester_warning_wording_map.json`
remediation text were updated to match. Degree-type inference and
unknown-degree fallback behavior are unchanged. Zero live findings on the
current seven-document corpus before or after this change.

Primary R021 record: PR #550 (`fix/p021-ester-abstract-word-limits-20260922`).

## R086 Current State

R086/P086 (new rule) covers a bold run-in phrase that reads as a de facto
section heading but carries no section number.

- **Policy authority:** during the R015 follow-up review, Ester separately
  observed this on Youra's document (physical page 101) and stated bold
  should be reserved for numbered heading levels 1-4. No existing rule
  owned this — P020/P026/P027 were already audited and ruled out.
- **Implementation:** a mandatory design gate
  (`docs/status/p086_unnumbered_bold_heading_design_20260922.md`) was run
  before any implementation and passed on a narrow, structural reading
  only: the detector fires only on a bold lead sharing a physical row with
  regular-styled continuation text (reusing R015's own already-validated
  run-in-heading detection), passing P027's own qualifying-heading-text
  filter, with no section number and no recognized heading name. It does
  **not** treat "bold reserved for headings" as a blanket rule against all
  other bold text — captions, table/figure column headers, bullets, inline
  emphasis, and short labels are all structurally excluded. Merged by
  PR #551 (`fix/unnumbered-bold-heading-ester-followup-20260922`).
- **Formal inventory registration:** merged by PR #552
  (`fix/p086-register-rule-inventory-20260922`), which added P086 to
  `project_added_rules.json` and `evaluation_data_manifest.json`. This is
  engineering bookkeeping only — it adds no new reviewer authority beyond
  what Ester already confirmed above.
- **Reviewer confirmation:** seven-document corpus audit found 9 live
  findings (Youra physical pages 89, 91, 94, 101, 105; Muyeed physical
  pages 69, 79, 117, 188). Only Youra physical page 101 is the actual
  Ester-adjudicated case. Page 105 is a strong structural sibling (same
  phrase template, different scenario number) but was never itself
  reviewed. The remaining 7 are **unreviewed candidates**, not
  reviewer-confirmed violations.

## Feedback-Cycle Rule State

Use human-facing `Rxxx` identifiers in reviewer/project-progress prose. Use
internal `Pxxx` identifiers only when describing implementation files, tests, or
rule registry entries.

| State | Rules |
|---|---|
| Closed or conservative after Ester-adjudicated false-positive review | R011, R015, R016, R017, R018, R019/R028, R020, R023, R024, R026, R033, R035, R036, R040, R046, R048, R053, R054, R055, R066, R068, R078 |
| Closed, engineering-confirmed genuine violation | R085, R086 (Youra physical page 101 case; other corpus findings unreviewed) |
| Closed, engineering fix to match already-explicit Ester policy | R021 (MS/PhD word limits corrected to 200/400 per her sheet; not a new Ester decision) |
| Reviewer policy resolved 2026-09-23 (`REVIEWER_POLICY_RESOLVED`) | R018 wrapped-title alignment (`ENGINEERING_IMPLEMENTATION_COMPLETE`, merged via PR #553); R026 Latin Modern (`ENGINEERING_IMPLEMENTATION_COMPLETE` — detector already accepted it before #553, which added explicit regression coverage); leader placement for TOC/LoT/LoF (`ENGINEERING_IMPLEMENTATION_COMPLETE`, merged via PR #553) |
| Open policy question | None |
| Already resolved / no action needed | R034 (implementation is conservative and well-tested; currently zero live findings on the seven-document corpus, nothing to send Ester) |
| No current selected finding/action | R012-R014, R022, R025, R027, R029-R032 |
| Not yet reviewed this cycle | R037 onward, except separately handled R021/R040/R046/R048/R053/R054/R055/R066/R068/R078/R085/R086 |

## Ester Final Three Clarifications

Ester answered all three questions from the pre-email backlog audit on
2026-09-23; none remains an open reviewer question.

- **R018:** a wrapped TOC title's second line aligns with the first line's
  title text, not the section number (her examples: Praneeth 1.3.3, 1.3.4,
  1.3.5). New P018 issue type `wrapped_title_continuation_misaligned`, TOC
  only, checked symmetrically (NJIT's model TOC hangs wrapped lines exactly
  under the title text). Detects the reviewer-identified entries (Praneeth
  physical page 11); other Praneeth entries of the same shape are unreviewed
  candidates, and three LaTeX-built TOCs (Philip, Muyeed, Youra) show a
  borderline, unreviewed one-em hanging indent past the title text.
  Public card R018R.
- **R026:** Latin Modern is explicitly accepted as part of the Computer
  Modern allowance. Already the detector's behavior; regression test added.
- **Leader placement:** applies to TOC, List of Tables, and List of Figures;
  leaders begin after the final line of a wrapped title; one space is
  allowed. New P018 issue types `title_to_leader_gap_too_wide` and
  `leader_dots_before_final_title_line` (public card R018S). The one-space
  allowance adds a grid-phase term only on pages whose leaders are measured
  to be grid-aligned. Sebastian's confirmed List of Figures case is detected;
  Sebastian's List of Tables page is an unreviewed structural sibling.

Engineering status: all three `ENGINEERING_IMPLEMENTATION_COMPLETE` on `main`.
R018 and leader placement were merged via PR #553 (squash commit `72c8e1f`,
from CI-tested head `a2e843c` with an identical tree); public cards R018R and
R018S are live in `main`. R026 was already accepted by the detector before
#553, which pinned the policy with regression tests. Not deployed. Primary
record:
`docs/status/ester_final_three_clarifications_20260923.md`.

## Next Work Sequence

All rule work through R086/P086 is merged and formally catalogued. The
three reviewer questions from
`docs/status/pre_ester_email_unresolved_backlog_audit_20260922.md` are
answered and implemented (PR #553). No rule work is pending from them. The
separate legacy Times-clone font-alias authority question (R026, zero corpus
impact) remains an optional future policy task.

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
