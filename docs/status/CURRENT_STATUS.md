# Current Status

> **Canonical, current-only status.** This is the entry point for "what is true
> right now." Older dated reports remain historical/forensic records.
>
> This file is intentionally short. Do not append long dated narratives here;
> write detailed records under `docs/status/` and link them from this file.

_Last verified: 2026-09-01, after the R017/P017 wrapped-caption and inline-reference fix._

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
| Rule inventory | P001–P084 implemented; no remaining non-inventory project task IDs; next new internal rule ID remains P085 |

## Current Evaluation Corpus

The current human-validation corpus is seven private dissertation PDFs: Youra,
Anthony, Muyeed, Philip, Praneeth, Sebastian, and Patrick. Elbert is excluded.
These files remain local under `data/evaluation/private/`, ignored by Git, and
must not be quoted, uploaded, or committed.

## Feedback-Cycle Rule State

| State | Rules |
|---|---|
| Closed | R011, R015, R017 |
| Waiting on Ester | R019 |
| Ready for engineering | R024, R027, R030 |
| Friday discussion / frozen for tuning | R016, R018, R020, R023, R026, R028, R033 |
| No current selected finding/action | R012-R014, R022, R025, R029, R031, R032 |
| Not yet reviewed this cycle | R034 onward |

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

R019 is not closed. The evidence-generation problem for document-level
page-number-transition findings was repaired at
`ff5a78f23cef1de2b693448d920d6161e9d8317f` without tuning P019 detector
semantics. The repaired 23-page PDF was uploaded and the live R019 Sheet link
was repointed to:

- Drive file ID: `1uYHqjiihCCshMaEK0X7teZUwYIZrmsNh`
- Filename: `R019_Ester_Auditor_Feedback_REPAIRED_20260901.pdf`
- Size: `1,476,119` bytes
- Folder: `16w3qZgNRz965rPlgxlUiDDFBZexG97rG`

Ester has been notified. Current state: awaiting Ester's human judgment. The
old 10,758-byte placeholder Drive file
`1CWOYO4Hy4ULjbE6YTdXzBkRmgorwpTko` remains historical/obsolete and was not
deleted.

## Next Work Sequence

**NEXT ENGINEERING TASK: R024.**

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
