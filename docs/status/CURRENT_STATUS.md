# Current Status

> **Canonical, current-only status.** This is the entry point for "what is true
> right now." Older dated reports remain historical/forensic records.
>
> This file is intentionally short. Do not append long dated narratives here;
> write detailed records under `docs/status/` and link them from this file.

_Last verified: 2026-09-07, on the `research/ester-feedback-through-r033-20260901` branch,
after the R036 wrapped-entry false-positive fix. `main`'s own last verified state
below is still 2026-09-01; the research branch is the current engineering
front and has not yet been integrated back into `main` (see Research Branch
section)._

## Main Branch

| Field | Value |
|---|---|
| Current `main` SHA | `336b28c6e894a6414247357a3f93f188e5150f75` (short `336b28c`) |
| `origin/main` | same SHA; ahead/behind `0 / 0` |
| Latest commit | `fix(p017): handle wrapped captions and inline references` |
| CI | GitHub Actions run `33518881868`, green on Python 3.10 / 3.11 / 3.12 |
| `ruff check .` | clean |
| `mypy src` | clean, 113 source files |
| `python -m pytest` | **3192 passed**, 3 warnings |
| Live deployment worktree | detached at `7232305d89e97c233002bf0c8077bad01e9e3f44`; not updated by this pass |
| Rule inventory | P001–P085 implemented; no remaining non-inventory project task IDs; next new internal rule ID remains P086 |
| Uncommitted work | `pdf_title_capitalization.py` / `pdf_toc_list_formatting.py` / `tests/test_pdf_rules.py` — proactive P024 false-positive hardening (hyphenated-fragment title-case skip; parenthetical proper-noun exclusion from sentence-case scoring), not yet Ester-reviewed, tests pass (713/713), not yet ported to the research branch. Left in place; not destructive to touch. |

## Research Branch (current engineering front, 2026-09-07)

| Field | Value |
|---|---|
| Branch | `research/ester-feedback-through-r033-20260901` |
| HEAD | `2a0289d` (local == origin at time of writing minus this session's 2 unpushed commits: `aea0e81` fix(r036) wrap-continuation FP, `2a0289d` R036 package regen) |
| CI | green through `1d24080` (the commit immediately before this session's work) |
| `python -m pytest` | 3330 passed, 2 skipped (clean venv, PyMuPDF 1.28.2) |
| **Environment hazard** | The box's ambient/default `python3` venv has PyMuPDF 1.24.6, **below** the `>=1.25.0` floor `pyproject.toml` requires. Running the auditor or its evaluation tooling under that venv silently produces materially different (wrong) geometry results — confirmed directly (P036 counts differed by 4x between the two venvs on identical PDFs). Always use a venv with PyMuPDF `>=1.25.0` for any private-corpus evaluation. A correct one already exists at `/tmp/njit-auditor-final-gate-20260907105625`. |

## Current Evaluation Corpus

The current human-validation corpus is seven private dissertation PDFs: Youra,
Anthony, Muyeed, Philip, Praneeth, Sebastian, and Patrick. Elbert is excluded.
These files remain local under `data/evaluation/private/`, ignored by Git, and
must not be quoted, uploaded, or committed.

## Feedback-Cycle Rule State

_Updated 2026-09-07 — the table below was stale as of 2026-09-01: R016, R018,
R020, R023, R026, R028, R033 were already resolved by
`docs/status/ester_authority_matrix_20260902.md` the very next day, and
R035/R036/R055/R085 have since been implemented and regression-tested. See
`docs/status/ester_authority_matrix.md` for the current pointer and known
deltas._

| State | Rules |
|---|---|
| Closed, Ester-adjudicated, regression-tested against fresh audit | R011, R015, R016, R017, R019/R028 (page-number ownership split), R020, R023, R026 (except Latin Modern alias, still unresolved), R033, R036, R055 |
| Closed, engineering-confirmed genuine violation | R085 (Patrick's missing literal CHAPTER 1) |
| Implemented but one case needs Ester clarification | R035 (Anthony's reviewed false positives confirmed gone; Praneeth still produces 4 live centering findings and this repo has no record of whether those match what Ester reviewed — see authority matrix pointer) |
| Needs one more finding-level verification pass before calling closed | R018 (structural evidence-selection fix present and tests pass; have not independently confirmed the surviving Anthony/Praneeth findings are the retained genuine 1.3.3/1.3.4/1.3.5 misalignment rather than a reintroduced instance of a suppressed pattern) |
| Genuinely unresolved — no Ester decision exists | R024, R034, Latin Modern font-alias expansion (R026 sub-issue) |
| No current selected finding/action | R012-R014, R022, R025, R027, R029-R032 |
| Not yet reviewed this cycle | R037 onward |

Use human-facing `Rxxx` identifiers in reviewer/project-progress prose. Use
internal `Pxxx` identifiers only when describing implementation files, tests, or
rule registry entries.

## Closed Work

- **R011 / P011 closed.** Latest relevant commit:
  `090779ed84433dd8541d972eb9ba8037e38c1960`. Ester's feedback on the
  bottom-margin boundary and reference-list right-margin cases has been
  incorporated. Status records:
  `docs/status/p011_r011_batch_2026_08_false_positive_fix.md` and
  `docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md`.
- **R015 / P015 closed.** Latest relevant commits include
  `a23f7093a6c4365539200d0f807a522046a80e7a` and
  `9dce0079358045995a5f3743b9cb884dbfea86b6`. The wrapped/run-in paragraph
  attribution issue is resolved. A separate observation about unnumbered bold
  text remains an ownership question, not an R015 defect.
- **R017 / P017 closed.** Commit
  `336b28c6e894a6414247357a3f93f188e5150f75`; CI green; full suite
  `3192 passed`, 3 warnings. P017 now checks terminal punctuation against the
  complete logical wrapped caption and no longer treats mixed digit/letter
  subfigure references such as `3.2d` / `3.5c` as caption starts. Final
  seven-document R017 counts: Youra 0, Anthony 0, Muyeed 0, Philip 0,
  Praneeth 1, Sebastian 0, Patrick 0. The remaining Praneeth physical page 102
  finding is an engineering-audited genuine caption candidate lacking terminal
  punctuation; it has not been independently labeled by Ester.

## R019 Current State

_Update 2026-09-07: this section's 2026-09-01 "awaiting Ester's human
judgment" claim is stale. `docs/status/ester_authority_matrix_20260902.md`
(the next day) already records an EXPLICIT decision for R019 (Roman
front-matter-through-CHAPTER-1 boundary expected; missing literal CHAPTER 1
owned by R028/P028, not a P019 symptom), and the ownership-split
implementation (commit `c309af6`) is confirmed present and correct against
the fresh seven-document audit (P019=0, P028=0 everywhere except Patrick's
genuine R085 case). Retaining the original repair record below for history._

The evidence-generation problem for document-level page-number-transition
findings was repaired at `ff5a78f23cef1de2b693448d920d6161e9d8317f` without
tuning P019 detector semantics. The repaired 23-page PDF was uploaded and the
live R019 Sheet link was repointed to:

- Drive file ID: `1uYHqjiihCCshMaEK0X7teZUwYIZrmsNh`
- Filename: `R019_Ester_Auditor_Feedback_REPAIRED_20260901.pdf`
- Size: `1,476,119` bytes
- Folder: `16w3qZgNRz965rPlgxlUiDDFBZexG97rG`

The old 10,758-byte placeholder Drive file
`1CWOYO4Hy4ULjbE6YTdXzBkRmgorwpTko` remains historical/obsolete and was not
deleted.

## Next Work Sequence

_Update 2026-09-07: superseded by the actual state above — R016/R018/R019/
R020/R023/R026/R028/R033/R035/R036/R055/R085 are past the "next work" stage
described below. Retaining for history; do not treat as the current queue._

**NEXT ENGINEERING TASK (as of 2026-09-01): R024.**

1. Wait for Ester's R019 judgment.
2. R024 audit/fix/validate.
3. R027 audit/fix/validate.
4. R030 audit/fix/validate, plus a separate ownership audit for chapter-title
   spacing.
5. Prepare discussion evidence for R016/R018/R020/R023/R026/R028/R033.
6. Capture Ester's decisions as authoritative ground truth.
7. Tune discussion rules one at a time after the meeting.
8. Continue with R034+ as Ester reviews them.
9. Run a final global human-feedback regression audit.
10. Deploy only after the feedback cycle stabilizes and CI is green.

**Actual current queue (2026-09-07):** R024 and R034 remain genuinely
unresolved (no Ester decision exists for either); R018's surviving
Anthony/Praneeth findings need one finding-level verification pass; R035's
Praneeth findings need confirmation against Ester's actual Sep-4 response
before being called either closed or regressed; the uncommitted `main` P024
hardening needs porting to this branch once R024 engineering resumes; R037
onward have not been reviewed this cycle.

## Repository Hygiene Notes

- Known historical LFS hygiene debt: `git lfs fsck` reports 17 tracked binaries
  that match current LFS patterns but exist as ordinary Git objects. No
  migration was performed because correcting historical storage would require
  history-sensitive work. Address separately only if needed.
- Local branch clutter remains. Query 2 may delete only local branches that are
  fully merged, have no unique commits, are not protected/preserved/live, and
  are not checked out in any worktree. Remote branch deletion requires separate
  explicit authorization.
- `scripts/ester_rule_consistency_audit.py` still requires local, untracked
  `results/ester_feedback_raw/*.xlsx` input and is not fresh-clone/CI runnable
  without a redacted or synthetic stand-in.
