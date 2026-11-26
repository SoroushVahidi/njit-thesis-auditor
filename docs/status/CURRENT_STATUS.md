# Current Status

> Each snapshot records what was observed on its stated date. Verify the
> advertised GitHub main and the live `/version` before using these values for
> development or release work.

## Source and production snapshot — 2026-11-26

| Role | Verified observation |
| --- | --- |
| Remote main | `dc40ec37e4d9dfb9df1205683cf75ecd2434fdd9`, tree `12159560e9ffc9193d36c4bb3eef7c06f1e6a9a8`. All seven [exact-checkout main CI jobs](https://github.com/SoroushVahidi/njit-thesis-auditor/actions/runs/45882403376) passed. |
| Running website | `380ccb78f7fa146c8100a0fda0333fb70029feba`. Public and loopback health passed after the rollback. |
| Release disposition | The smoke gate detected a job marked complete before terminal metadata was published. The service restored the prior revision. The latest feedback corrections on main await a successful qualified release. |
| Configuration | Production aggregate analytics remains disabled. Future access and publication changes require institutional authorization. |

## Historical snapshot — 2026-11-22

| Role | Observation |
| --- | --- |
| GitHub main | `7e49954c06b1734cff1b2842dd289316f7675ef1`, the PR #684 squash merge. Its tree `92cbd0f5e894bb2658332400da16a283082140f8` matches the validated PR tree. |
| Deployed website | `47bb4b97e384546e31fea749adb5c05fc5f9b2a3`. The user systemd service was active, `/healthz` returned OK, and `/version` reported `production`. |
| Merged changes awaiting a deployment decision | PRs #681–#684 are in main and absent from the running website revision. No production deployment or restart was scheduled by this maintenance pass. Use the [deployment runbook](../DEPLOYMENT.md) for any authorized rollout or rollback. |
| Published Windows desktop | The distribution repository lists [0.2.0-rc.3](https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/tag/desktop-v0.2.0-rc.3) as its published beta prerelease. Follow the [immutable release record](../releases/windows-0.2.0-rc.3.md) for its source and checksum, and the [release procedure](../PUBLIC_WINDOWS_RELEASE.md) for historical rc.2 and native qualification limits. |
| Local validation | The #684 tree recorded 12,723 Python 3.12 pytest passes, 36 skips and one unauthorized fixture deselected. Ruff, mypy and 17 Chromium tests passed. The same tree recorded 437 focused passes after squash merge. |
| Hosted validation | The [main run](https://github.com/SoroushVahidi/njit-thesis-auditor/actions/runs/45063874204) recorded zero steps across seven jobs because of account billing or spending limits. See [CI and private validation](../CI_PRIVACY.md) for coverage boundaries. |

### Recent merge and regression index

| Work | Disposition | Tracked regression or evidence |
| --- | --- | --- |
| R055 List of Tables | [#681](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/681) merged | [List entry evidence](../../tests/test_r055_evidence.py) |
| R063 N02 appendix ownership | [#682](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/682) merged | [Appendix ownership tests](../../tests/test_p063_appendix_body_headings.py) |
| R063 N01 appendix subsection prefixes | [#683](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/683) merged | [Subsection tests](../../tests/test_p063_appendix_subsections.py) |
| R057 P075 leader-cell capacity | [#684](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/684) merged | [Leader tests](../../tests/test_r057_toc_leader_gaps.py) and [synthetic PDF and TeX fixtures](../../tests/fixtures/r057_leader_cells/) |
| F29A table continuation metadata | [#680](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/680) merged | [Table continuation tests](../../tests/test_f29_table_continuations.py) |
| F30 figure caption continuation | [#678](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/678) merged | [F30 scope and validation](f30_cross_page_figure_descriptions_20261120.md) |

R054 attached title punctuation (E03) and R018 justified leader spacing (S04)
remain separate feedback tasks. Reviewer reconciliation and authorized comparison
evidence stay in the private workspace. Follow the
[development guide](../DEVELOPMENT.md#source-outputs-and-retention) and
[evaluation data policy](../EVALUATION_DATA.md) for retention and access.

## Verified baseline — 2026-11-04

| Field | Observed evidence |
|---|---|
| Remote main and production at inspection | `5576e3bf5b633e0b0e19ccf23487755921b2292c` (PR #647); detached clean deployment worktree and live `/version` agreed |
| Production | User service `thesis-auditor-web.service` active; `/healthz`, upload, Help, Rule Reference and About returned 200; environment `production` |
| Baseline validation | **5002 passed, 7 skipped**, full local suite on the reviewed PR #647 tree; its squash-merge tree was identical. The focused 91-test suite, Ruff and mypy were repeated on `5576e3b`. These are separate runs, not added counts. |
| CI at that baseline | Branch/PR and post-merge CI passed on Python 3.10–3.12; [post-merge run 41769820136](https://github.com/SoroushVahidi/njit-thesis-auditor/actions/runs/41769820136). Browser tools were not installed by the normal matrix; local browser results are separate evidence. |
| Unresolved PRs at inspection | 25 pre-existing open PRs, including #640–643; none were closed or merged by this organization task |
| Rule inventory | P001–P087 registered; P082 remains opt-in. Next unused internal ID P088; no new detector work is authorized by this snapshot. |

The manifest snapshot fields refer to this **observed baseline** (`5576e3b`,
5002 passed, 7 skipped), not a predicted maintenance merge SHA or test count.
The new focused browser CI is described in [reproducibility](../REPRODUCIBILITY.md).
A documentation/test-only merge can advance main while production remains at this
runtime-equivalent baseline; no production restart is required for those changes.

### Current website and shared source

PR #645 introduced evidence-supported checklist answers and simpler human-readable
reports; unknown answers remain under **Check yourself**. PR #646 added bundled
About Us and navigation; PR #647 corrected the acknowledgment to “Professor
Ioannis Koutis, for early project discussions.” Live navigation, a synthetic audit,
PDF report download and an anonymous click of the Windows button passed at the
baseline. Source-template and simulated frozen-bundle tests are Ubuntu source
checks, not native tests of an already-published Windows executable.

### Published Windows rc.3

The [immutable release record](../releases/windows-0.2.0-rc.3.md) identifies the
installer built from `b83c7c81cf4043a17eb45f7b4b2042e55bbe947a`, **41,326,578 bytes**,
SHA-256 `70713e44f18aaac32d5cc244aee3c82c7badbd8ce9d9dbf3b1dffe919a05f690`.
Its hosted Windows Server native regressions and packaged smoke passed. It includes
local Help/Rule Reference, active-audit recovery and the pre-#645 report UI.
The public desktop repository hosts downloads/releases; private source stays private.

### Awaiting another desktop installer

PR #645 wording/checklist changes, PR #646 About Us, and PR #647 acknowledgment
correction are in shared source and the website, **not in rc.3**. They need a new
installer version and checksum. No Windows build or published asset replacement is
part of this organization work. See [wording](../STUDENT_WORDING_USABILITY.md) and
[About provenance](../ABOUT_US_CONTENT.md).

### Qualification and unresolved work

- Clean Windows 11 x64 qualification, installer/uninstaller lifecycle and broader
  native manual checks remain unperformed for rc.3. Hosted Windows Server smoke
  and Ubuntu source checks do not establish those results. The
  [native checklist](../implementation/offline_desktop_windows_smoke.md) records
  the broader procedure; it is not a new publication approval gate.
- Wheel runtime resources remain the separate open PR #643. Production continues
  to use a worktree, not a wheel-only installation.
- The historical 19-PDF output/reviewer-triage status and detector limitations below
  were not re-audited here. Do not infer completed reviews or new detector priorities
  from this maintenance snapshot. No remaining non-inventory project task IDs are
  introduced; the registered range remains P001–P087.

## Historical snapshot — 2026-10-12

This snapshot records checks made on 2026-10-12. It does not claim continuous
production monitoring or completion of reviewer triage. The source of truth for
the current live process remains `/version` and the deployment worktree.

| Field | Verified state |
|---|---|
| `origin/main`, detached production worktree, live `/version` | `14856250ce2aaf7a38610a086e8f5250a92655bf` (PR #610 squash merge); aligned on 2026-10-12 |
| Production health at inspection | `thesis-auditor-web.service` active; `/version` returned HTTP 200, the expected commit, and `environment: production` |
| PR #610 | Merged 2026-10-11 and deployed at the SHA above; P015 historical-continuation false-positive correction |
| Open PR at inspection | #523 (`ops/tcp8000-diagnostics`); no repository-refresh PR has been opened |
| Reviewed PR tree validation | 4725 passed, 0 skipped with detector liveness; performed before merge on the reviewed tree |
| Exact post-merge commit validation | 4719 passed, 6 skipped (4725 collected); all six private-PDF-dependent tests then passed separately on that same merge commit |
| Historical Ester judgment regression gate | 136/136 case checks passed at the merge commit, with no unexpected removals or liveness errors; this is prior reviewer evidence, not a review of the new 19-PDF output |
| Expanded Ester run | Completed successfully on 2026-10-11: 19 authorized PDFs, 63 applicable R rules, exit code 0 at the deployed SHA; finding review and deduplication remain pending |
| Maintenance-branch checks | Phase 1 ran 173 targeted tests; Phase 2 ran 188 targeted status, manifest, registry, deployment, and stale-doc tests on `chore/repository-refresh-20261012`. Neither is a full suite result for the documentation branch. |
| Rule inventory | P001–P087 registered; next unused internal ID P088. P082 remains opt-in. |

The two full-suite counts above came from **different runs and trees**. The six
private tests were run separately after the post-merge suite; their passing
result is not a single 4,725-test post-merge run. CI and local validation are
separate evidence sources; see [reproducibility](../REPRODUCIBILITY.md).

### Immediate evaluation priority

Review the completed 19-PDF output against Ester's prior judgments, previous
feedback, and the private review ledger. Deduplicate equivalent or previously
answered cases before preparing a package containing only genuinely new
questions. The completed audit is evidence generation, not a completed review
package. Do not contact Ester or create a workbook until that analysis is done.

### Known limitations and unresolved work

- The earlier B2 reading-frame ambiguity and content-turned portrait 90/270
  page-number cases remain open; P082 is experimental and opt-in. The legacy
  CLI page-number path is separate from the web path.
- Q030 citation-format consistency remains unimplemented; other historical
  authority and detector questions require case-by-case review, not inference
  from the 19-PDF run alone.
- A non-editable wheel omits repository-level rule/spec JSON and web templates;
  the established deployment runs from a worktree. See
  [reproducibility](../REPRODUCIBILITY.md) for the exact packaging boundary.
- Some tests require private PDFs absent from a clean checkout. Their skips
  must be reported separately from ordinary test passes.

## Historical snapshot — 2026-10-08

This and all later dated sections preserve earlier state and decisions. Their
SHAs, deployment notes, and pending statements are historical.

### Snapshot

| Field | Value |
|---|---|
| Code baseline (`origin/main`, production checkout, live `/version`) | `a9bca5349b84e1a790e126057fd2625f1921a06d` (`a9bca53`, PR #583), all aligned |
| Manifest status snapshot | `a9bca53`; **4482 passed**, 6 skipped (skips need private fixtures absent from a clean worktree) |
| Quality gates at the snapshot | `ruff check .` clean, `mypy src` clean, `git diff --check` clean |
| Seven-document corpus (Youra, Anthony, Muyeed, Philip, Praneeth, Sebastian, Patrick) | 1495 raw findings, 623 actionable, 623 numbered student cards, 0 numbered PASS rows |
| Samples A–D | 1052 raw, 362 actionable, 362 cards, 0 PASS; visible R011 cards A 0 / B 20 / C 20 / D 50; Sample D raw R011 57 |
| Direct review-ledger replay (`--ledger-root <scratch copy>`) | 46 reviewed false positives (0 remaining), 4 reviewed true positives (0 missing), 0 unresolved, 0 ambiguous |
| Local `/Rotate` inventory | 2,217 corpus pages, 0 with non-zero `/Rotate`: all rotation work below is synthetic-tested and has zero real-document delta |
| Rule inventory | P001–P087 implemented and formally registered (`data/processed/rules/project_added_rules.json`); no remaining non-inventory project task IDs; next unused internal rule ID is P088 |

The replay figures cover only the cases stored in the direct review ledger.
They do not mean every policy question in the guidelines is settled.

### Reviewer workflow: stopped

- Packet: NONE. Substitute: NONE. Outreach: stopped.
- Reason: the authority-equivalence work through 2026-10-07 found no
  genuinely novel reviewer case. Candidate questions were already answered
  by prior adjudications or were materially equivalent to them.
- Before any future question to Ester, search prior emails, the Sheets and
  Excel workbooks, the annotated dissertations, the authority matrices,
  previous adjudications and the Drive templates and examples. Do not ask
  something already answered or materially equivalent.
- Keep the authority classes separate:
  - **DIRECT_ESTER_AUTHORITY:** Ester's own adjudications.
  - **DERIVED_ENGINEERING_AUTHORITY:** rules reasoned from those adjudications.
  - **ENGINEERING_EQUIVALENCE:** materially the same case as a reviewed one.
  - **UNREVIEWED_ENGINEERING_DEBT:** findings or questions nobody has reviewed.

  For example, R035 has exactly two direct adjudications, Anthony p60 and
  Praneeth p29, both false positives. Praneeth p67 is authority reuse,
  p69 was fixed, p72 was an engineering bug and p100 is unreviewed (see
  `r035_praneeth_text_fallback_fix_20260907.md`).

### PDF rotation architecture

Accepted design: [`docs/architecture/pdf_rotation_frames_adr.md`](../architecture/pdf_rotation_frames_adr.md).

- Extracted geometry stays in unrotated, CropBox-relative box space.
- Detectors judge in the content (reading) frame.
- A viewer-only `/Rotate` keeps the `/Rotate 0` verdict when the frame is inferred as 0.
- Content-turned pages, including pdflscape, are judged as they read.
- Presentation may use display semantics.
- Global extraction normalization is rejected.
- The shared detector object is `pdf_models.PdfReadingFrame`. Its production consumers are R035, R011 and P013/P019 page-number classification.

Completed, all merged and deployed:

| PR | Work |
|---|---|
| #577 | P013/P019 pdflscape 90/270 page-number geometry |
| #578 | Rotated highlight clipping and location labels |
| #579 | R035 pdflscape decision geometry |
| #580 | Rotation-frame ADR |
| #581 | R035 viewer-only rotation (B1) on `PdfReadingFrame` |
| #582 | R011 margins in the reading frame (pdflscape 90/270 sides, bottom-only allowances never on a binding edge) |
| #583 | P013/P019 content-turned `/Rotate 180` positions (readable-bottom folio is `bottom_center`) |

### Remaining debt (prioritized; none started)

1. **B2: reading-frame confidence and ambiguity.**
   - The character-weighted inference can choose the wrong frame when rotated or object text narrowly outweighs the main content.
   - Pinned exposures: R011 viewer-only 90 (`test_b2_near_tie_is_a_known_deferred_limitation`) and P013 viewer-only 180 (`test_b2_upside_down_majority_is_a_known_deferred_limitation`).
   - No confidence threshold or abstention policy has been chosen.
2. **Content-turned portrait 90/270 page numbers.**
   - These are still classified in box space (`right_center`/`left_center`).
   - A displayed bottom-right folio there still gives a false P019 `missing_page_number`.
3. **P082** (experimental, opt-in, not in the web flow). It recomputes positions in display space and is not migrated.
4. **Legacy CLI page numbers** (`rules/page_numbers.py`). This is a separate older implementation outside the web flow.

Other known debt, carried forward from project tracking:
- Sample D merged-span References-label false positives.
- P013 no-page-number PASS semantics.
- Q030 citation-format consistency (established authority, unimplemented).
- Philip p117 R015.
- The non-editable wheel lacks some repository `data/` files.
- A deprecation warning from httpx through `TestClient`.
- A deeper R011 final-line exception, only if a concrete case appears.
- P001–P010 TeX-source rules.

### Next recommended task

A **read-only investigation** of B2: measure where the inference is close
to a tie on real and synthetic pages, then propose a confidence signal and
an abstention policy for review. Do not implement thresholds before that
evidence exists.

### Do not redo

- #577–#583 (above).
- The R011 landscape, reference-label, References-continuity and binding-bottom tolerance fixes (#572–#576).
- The R035 provenance correction (#569).

### Local layout

- **Development checkout:** `/home/soroush/njit-thesis-auditor/main`, on branch `main`.
- **Production:** the detached worktree `njit-thesis-auditor-clean-worktrees/live-current-main`, deployed per `docs/DEPLOYMENT.md`.
- **Preserved worktrees and branches:** only those with commits not on `main`.
- **Private QA** (synthetic rotation matrices, corpus dumps, scratch-ledger replays) lives in the untracked `notes/` directory beside the repository, one dated folder per task. It is never committed.
- **Shared review ledger:** `main/data/evaluation/private/ester_review_ledger`. Read it through scratch copies only.

## Historical authority update — 2026-10-06

Baseline `origin/main`, deployment checkout, and live `/version` were all
`817f093bf199d10225ad6eee2317c0b0684dff67` before this branch. The
R037 detector already continued Roman numerals from Biographical Sketch iv;
its student-facing fixed-slot wording was stale and is corrected on
`fix/r037-q029-q074-authority-consistency-20261006`. The branch is not
deployed. Q029's historical mandatory hanging-indent text is superseded by
Ester's optional rule; Q074's historical sentence-case text is superseded by
the title-case R024E rule. Q030 citation-format consistency is established
but remains unimplemented. See
[`r037_q029_q074_authority_consistency_20261006.md`](r037_q029_q074_authority_consistency_20261006.md)
for the current effective authority and historical trace limit.

The entries below are retained as dated snapshots; their older SHA,
deployment, and open-question statements do not describe the 2026-10-06
baseline.

_Last updated: 2026-10-03. Historical Ester reconciliation is complete and
merged to `main` via PR #558 at `1002a99a493363f4b164bea77f964d3156dc9f74`.
Running production still reports `38415c3ed76ee28eb1c46c2cd83a6ed439242db7`
from `/version`; deployment of the PR #558 changes is pending. The live-service
worktree is at the merged main commit on disk, but the service has not been
redeployed. Earlier rule decisions and deployment history remain below._

## Historical Repository and Production Snapshot (2026-10-03)

| Field | Value |
|---|---|
| `main` and `origin/main` at this status snapshot | `1002a99a493363f4b164bea77f964d3156dc9f74` (PR #558, merged by squash) |
| Latest status-recorded implementation merge | PR #558, squash commit `1002a99a493363f4b164bea77f964d3156dc9f74` |
| Running production `/version` | `38415c3ed76ee28eb1c46c2cd83a6ed439242db7` |
| Live-service worktree on disk | `1002a99a493363f4b164bea77f964d3156dc9f74`; service not restarted for PR #558 |
| R036 production branch | `fix/r036-production-page-relative-suppression-20260916` (merged by PR #538) |
| R036 audited base | `e5105018960aa9b478ad87e1c51e70d749dcaa16` |
| R036 pre-documentation-sync HEAD | `14a0d68daa446c4bd23147c9560c9213d52ef050` |
| R036 implementation/privacy-audited HEAD | `b277f34fe8ec7e01a32c83a1a23af82d5f7f8556`; superseded only by final documentation/privacy reconciliation |
| R036 relation to `origin/main` after final documentation/privacy reconciliation | Merged |
| Deployment | Pending for PR #558; repository and running service are at different commits. No production deployment was performed as part of PR #558 or this status update |
| Manifest status snapshot | `1002a99`; **3708 passed**, 0 failed (pre-merge full pytest result) |
| R036 final-pass validation | `ruff check .` clean; `mypy src` clean; `python -m pytest`: **3539 passed**, 5 skipped, 3 warnings |
| Rule inventory | P001–P087 implemented and formally registered (`data/processed/rules/project_added_rules.json`); no remaining non-inventory project task IDs; next unused internal rule ID is P088 (see "R086 Current State" below for provenance; verified free: no existing source file or reference) |

## Historical evaluation corpus

At that snapshot, the human-validation corpus was seven private dissertation
PDFs: Youra, Anthony, Muyeed, Philip, Praneeth, Sebastian, and Patrick.
Elbert was excluded.
These files remain local under `data/evaluation/private/`, ignored by Git, and
must not be quoted, uploaded, or committed.

This seven-document corpus is separate from the 19-document historical Ester
reconciliation corpus summarized below; the latter did not replace it.

## Historical Ester Reconciliation (PR #558)

PR #558 merged the completed historical reconciliation into `main`. All **195**
selected cases were classified using aggregate, privacy-safe categories:

| Class | Meaning | Cases |
|---|---|---:|
| A | Genuinely new review needed | 91 |
| B | Previously answered exact | 7 |
| C | Previously answered same failure mode | 7 |
| D | Known false-positive regression | 53 |
| E | Known true pattern | 33 |
| F | Ambiguous relationship | 4 |
| **Total** | | **195** |

The final reviewer package has **83 active Ester review requests**, **68**
“No new review needed” rows, and **457** “No current finding” rows. Its evidence
set contains **21 PDFs** and **83 evidence pages**. The package and private case
materials remain local and are not part of this status update.

Before merge, candidate validation passed **13 reconciliation tests**, **352**
other Ester regression tests, and **278** targeted PDF-rule tests; Ruff and
Mypy passed. The full pytest run reported **3708 passed, 0 failed**.

For the tested TOC-wide missing-leader consistency case, **R075** owns the
genuine finding. **R018** retains its distinct alignment, continuation, and
leader-placement responsibilities. The tested case is not reported twice.

## Historical R036 state

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

## Historical R011 state

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

## Historical R015 state

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

## Historical R053 state

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

## Historical R054 state

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

## Historical R040 follow-up state

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

## Historical R046 follow-up state

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

## Historical R048 follow-up state

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

## Historical R078 follow-up state

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

## Historical R066 follow-up state

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

## Historical R068 follow-up state

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

## Historical R021 state

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

## Historical R086 state

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

## Historical feedback-cycle rule state

Use human-facing `Rxxx` identifiers in reviewer/project-progress prose. Use
internal `Pxxx` identifiers only when describing implementation files, tests, or
rule registry entries.

| State | Rules |
|---|---|
| Closed or conservative after Ester-adjudicated false-positive review | R011, R015, R016, R017, R018, R019/R028, R020, R023, R024, R026, R033, R035, R036, R040, R046, R048, R053, R054, R055, R066, R068, R078 |
| Closed, engineering-confirmed genuine violation | R085, R086 (Youra physical page 101 case; other corpus findings unreviewed) |
| Closed, engineering fix to match already-explicit Ester policy | R021 (MS/PhD word limits corrected to 200/400 per her sheet; not a new Ester decision) |
| Reviewer policy resolved 2026-09-23 (`REVIEWER_POLICY_RESOLVED`) | R018 wrapped-title alignment (`ENGINEERING_IMPLEMENTATION_COMPLETE`, merged via PR #553); R026 Latin Modern (`ENGINEERING_IMPLEMENTATION_COMPLETE` — detector already accepted it before #553, which added explicit regression coverage); leader placement for TOC/LoT/LoF (`ENGINEERING_IMPLEMENTATION_COMPLETE`, merged via PR #553) |
| Open policy question | R011 final-line allowance beyond references pages (see "Ester Feedback Round 2026-10-05"). R045 numbering was resolved on 2026-10-06 (entries must not be numbered). |
| Already resolved / no action needed | R034 (implementation is conservative and well-tested; currently zero live findings on the seven-document corpus, nothing to send Ester) |
| No current selected finding/action | R012-R014, R022, R025, R027, R029-R032 |
| Not yet reviewed this cycle | R037 onward, except separately handled R021/R040/R046/R048/R053/R054/R055/R066/R068/R078/R085/R086 |

## Historical Ester final three clarifications

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
#553, which pinned the policy with regression tests. Deployed to production
on 2026-09-23 at commit `153e819`; R018R and R018S verified live (see the
Deployment row above). Primary record:
`docs/status/ester_final_three_clarifications_20260923.md`.

## Ester Feedback Round 2026-10-05

Ester answered the five single-case questions from the 2026-10-04 round:
R011 Sebastian p28 not a violation; R018 Patrick p11, R024 Muyeed p16, and
R040 Philip p15 true violations; R045 hanging indent optional, single
spacing mandatory. Branch `fix/ester-feedback-round-20261005` (PR pending
review, not merged or deployed) adds a narrow R011 references-page
final-line allowance, maps P024 findings to R024D/R024E, fixes the R040
gap-separated leader case, and reworks R045 to enforce Q028 spacing without
requiring a hanging indent. Three clarifications were pending: R045
numbering, R011 beyond references pages, and List of Figures sentence case.

Follow-up branch `fix/ester-20261005-r024-r045-reconciliation` (not merged
or deployed) applies Ester's R024 answer: List of Tables (R024D) and List of
Figures (R024E) titles both use title case, with distinct codes. The List of
Figures sentence-case reading is superseded. On the seven-document corpus
this produced 198 R024E findings (an earlier "about 229" was a counting
error); a read-only audit found no entry-level false positives, because the
corpus uses sentence case. Wrapped List of Figures rows are now grouped
into one entry, which removes 17 duplicate continuation findings: 181
R024E findings remain, one per violating entry.
R045 stays as implemented (single spacing mandatory, hanging indent
optional); numbering remains open. Pending clarifications: R045 numbering
and R011 beyond references pages.
Review workbooks follow the format in
`docs/evaluation/ESTER_REVIEW_DATA_MODEL.md` ("Reviewer workbook format").
Primary record: `docs/status/ester_feedback_round_20261005.md`.

## Closed-Rule Integrity Audit (2026-10-06)

Branch `audit/closed-rule-integrity-overnight-20261005`, based on the
reconciliation branch head `6b70aae`, replayed every replayable stored Ester
adjudication with structural identity (rule, issue type, side, page, and
entry/line geometry; page-only matches were not accepted). Results: review
ledger 51 cases (46 false positives still absent, 4 true violations still
reported, 1 needs-clarification case not replayable); historical
reconciliation classes B-F 104 cases (59 false positives absent, 41 true
patterns reported, 4 class-F relationships still ambiguous); 45 further
direct cases recorded only in status documents (38 absent, 7 reported).
No regression was found.

The per-rule seven-document counts in the sections above are snapshots taken
when each follow-up merged. Later merges changed several of them on purpose
(PR #558 historical reconciliation, PR #560 R011, PR #561-#563 R018/R024/R040,
and the 2026-10-05 Ester round). Current student-visible counts on the audit
base (Youra, Anthony, Muyeed, Philip, Praneeth, Sebastian, Patrick):

| Rule | Counts | Total |
|---|---|---:|
| R011 | 0, 38, 15, 17, 58, 3, 2 | 133 |
| R015 | 1, 0, 0, 6, 0, 0, 0 | 7 |
| R040 | 0, 0, 1, 1, 7, 0, 0 | 9 |
| R036, R046, R048, R053, R054, R066, R068 | all zero | 0 |
| R078 | Praneeth 1 | 1 |
| R085 | Patrick 1 | 1 |
| R086 | Youra 5, Muyeed 4 | 9 |
| R024D / R024E | Muyeed 9 / 43, 10, 46, 17, 17, 1, 47 | 9 / 181 |
| R055 | 46, 13, 97, 15, 29, 0, 57 | 257 |

Student-facing wording fixes from this audit: the R055 card and suggested fix
now describe the literal "Table"/"Figure" prefix requirement (Ester,
2026-09-04) that the detector already enforces; the R017 card no longer
claims List of Figures sentence-case checking (superseded by R024E title
case, 2026-10-05); the R068 card no longer describes the retired
signature-block check. Detector behavior and finding counts are unchanged.

## Pre-R045 Safe Stack (2026-10-06)

_Status 2026-10-08: merged in PR #565 and deployed._

Branch `integration/pre-r045-safe-stack-20261006` (not merged or deployed at the time)
stacks the policy-independent work on top of the reconciliation head
`6b70aae`: location-aware review-ledger matching, the reviewer workbook
format, fresh-clone consistency-audit fallbacks, the closed-rule audit
wording fixes above, and the public-card/canonical/Q-coverage chain.

- Table of Contents page-number column and missing-page-number findings link
  to R075 (Q052); List of Tables/List of Figures page-number columns link to
  R018N/R018Q. A list-page missing page number and the R015
  continuation-line indent stay without a card pending authority.
- R028 Patrick p13 is resolved by Ester's own comment (the defect is the
  missing CHAPTER 1 heading, R085); no question is needed.
- `data/specs/q_rule_coverage_report.json` is regenerated with
  `python -m njit_auditor.specs.q_rule_coverage --generated YYYY-MM-DD` and a
  freshness test guards it. Structured `source_q_rule_ids` are authoritative;
  notes count only as a fallback and never when they negate coverage.
  Coverage: 62 implemented, 12 manual-only, 5 automatable but unimplemented
  (Q015, Q020, Q024, Q029, Q030).
- Detector output is unchanged: seven-document raw findings are identical to
  the reconciliation head. R045 numbering and R011 beyond references pages
  stay frozen pending Ester.

Records: `docs/status/public_card_ownership_and_r028_authority_20261006.md`,
`p018_p075_canonical_sync_20261006.md`,
`p071_p024_q_metadata_reconciliation_20261006.md`,
`p071_q028_q029_metadata_cleanup_20261006.md`.

## Ester Answer 2026-10-06 (R045 numbering resolved)

Ester confirmed the R024D/R024E split and answered the R045 question:
Biographical Sketch publications MUST NOT BE NUMBERED. They are listed in
reverse chronological order and use the same citation format as the
References section, without the number in front. Hanging indent stays
optional and single spacing mandatory (2026-10-05).

_Status 2026-10-08: merged in PR #565 and deployed._

Branch `fix/r045-no-numbering-final-20261006` (not merged or deployed at the time) adds
the `biosketch_publication_entry_numbered` check to R045. On the
seven-document corpus it adds one finding (Patrick physical page 5); nothing
else changes. Reverse chronology was already checked by R067 (Q027); the
citation-format match (Q030) remains unimplemented. Record:
`docs/status/r045_no_numbering_ester_20261006.md`.

## Next Work Sequence (historical, 2026-10-03)

_Superseded: see "Current state and handoff — 2026-10-08" at the top._

All rule work through R086/P086 is merged and formally catalogued. The
three reviewer questions from
`docs/status/pre_ester_email_unresolved_backlog_audit_20260922.md` are
answered and implemented (PR #553). No rule work is pending from them. The
separate legacy Times-clone font-alias authority question (R026, zero corpus
impact) remains an optional future policy task. Historical reconciliation is
complete (PR #558); the 83 active requests in its final reviewer package await
review. Production deployment of the merged changes remains pending.

## Historical repository hygiene notes

- Known historical LFS hygiene debt remains: some tracked binaries match current
  LFS patterns but exist as ordinary Git objects. No history rewrite has been
  performed.
- Private evaluation dissertations stay local and ignored. Do not commit
  reviewer packages or dissertation content unless a task explicitly requires a
  redacted/synthetic artifact.
- `scripts/ester_rule_consistency_audit.py` uses the tracked YES/NO matrix
  XLSX when available and falls back to checked-in
  `data/specs/ester_q_matrix.json`; P-rule feedback falls back to
  `data/specs/ester_p_rule_feedback.json`. Local original XLSX files remain
  usable for forensic checks, but no private workbook is needed in a clean
  clone. Run `python scripts/ester_rule_consistency_audit.py` to generate an
  ignored local report under `results/`.

## Batch B (F08) — 2026-11-14

P088 detects malformed concatenated body figure numbers (for example `Figure 4.204.1`) and per-chapter duplicate or out-of-order well-formed `chapter.sequence` labels. F29/F30 cross-page float splitting remains out of scope for this batch.

As of the F08 integration candidate on 2026-11-18 (draft PR #668; not yet
merged), the project-added rule inventory covers **P001–P088**, with **P089**
as the next unused internal rule ID. Earlier dated inventory snapshots above
remain historical and are intentionally not rewritten.
