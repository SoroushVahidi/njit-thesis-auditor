# Open PR and Stash Triage — 2026-06-19

> **Historical / superseded** for open PR status. Current triage:
> [open_pr_triage.md](open_pr_triage.md).

This document records the status of the two open pull requests and the one local stash
as of the repository stabilization work landing on `main` at/after `b4cb8cd` (PR #324).
It is a **triage record only** — no code in PR #311, PR #305, or the stash was changed,
rebased, applied, or popped while writing this document. All findings below were
verified directly (`gh pr view`, `gh pr diff`, `git stash show -p`, and read-only
`git merge-tree <main> <pr-head>` conflict checks), not assumed from memory.

## Summary

| Item | Status | Conflicts with main? | Risk | Recommendation |
|---|---|---|---|---|
| PR #311 — sub-page location labels | SUPERSEDED (see update below) | Yes (2 files) | Medium — real feature, needed careful rebase | Reimplemented from scratch on current main; original PR to be closed, not merged |
| PR #305 — example thesis URL | OPEN | Yes (3 files, core UI change is clean) | Low | Rebase candidate, likely quick |
| Stash (`fix/student-facing-comment-wording`) | Uncommitted, untouched | N/A (not a PR) | Low — mostly superseded | Inspect on a throwaway branch only; do not pop onto main |

## PR #311 — "Add sub-page location labels for PDF findings"

> **Update (2026-06-19, post-stabilization):** the "sub-page location label" concept
> described below has been **salvaged and reimplemented from scratch** against current
> `main`, rather than rebased — see
> `docs/planning/sub_page_location_labels_rebase_audit.md` for the full audit and design.
> The new implementation is geometry-driven (`sub_page_location_label()` in
> `pdf_highlight.py`, derived purely from `(bbox, page_size)` quadrant math) and does not
> reuse any of PR #311's rule-specific text-snippet extraction (`_build_pdf_sublocation`),
> which would have exposed raw document text (captions/headings/TOC strings) and violated
> the no-body-text privacy invariant. PR #311 itself should be **closed without merging**
> once the replacement lands on `main` — its branch and diff remain useful as a historical
> reference for the original idea, but its code is not reused. The analysis below reflects
> the state of PR #311 as it stood on 2026-06-19, before this replacement existed.

- **Branch:** `feature/subpage-location-labels` → `main`
- **Opened:** 2026-06-15
- **Files changed:** `src/njit_auditor/report_view.py`, `src/njit_auditor/rules/pdf_captions.py`,
  `src/njit_auditor/templates/job.html`, `tests/test_location_label.py`
- **What it does:** adds a `_build_pdf_sublocation()` helper that renders a sub-page
  location string (e.g. a caption number for P017 findings) and displays it next to the
  page link as "page → label" in the job results table.
- **Mergeable state (GitHub):** `CONFLICTING` / `dirty`
- **Conflict cause (verified via `git merge-tree origin/main <pr-head>`):** real content
  conflicts in `src/njit_auditor/report_view.py` and `src/njit_auditor/templates/job.html`.
  Both files were substantially modified after this PR branched, by the now-merged
  finding-actionability stack (PR #320 actionability/drill-down, PR #321 strict highlight
  policy, PR #324 page-number/margin/font actionability) — `FindingView` gained `bbox` and
  `has_highlight` fields and the job template gained highlight-link rendering logic that
  PR #311's diff does not know about.
- **Redundancy check:** this is **not** redundant with the merged actionability work — a
  sub-page location label (e.g. "Figure 3") is a distinct piece of information from a
  drawable highlight/page link, and no equivalent currently exists on `main`.
- **Recommendation:** worth keeping, but the rebase is not mechanical — `report_view.py`'s
  `FindingView` shape and rendering branches have moved. Whoever rebases this should
  re-verify how the sub-location label should read alongside the new highlight-eligible
  links (e.g. "p. 5 → Figure 3" vs. just "Figure 3") before merging, and re-run the full
  suite. Left untouched in this stabilization task per explicit instruction.

## PR #305 — "Add example NJIT thesis URL to web upload page"

- **Branch:** `feature/example-thesis-url` → `main`
- **Opened:** 2026-06-13
- **Files changed:** `docs/web_ui_demo_guide.md`, `docs/web_ui_manual_qa_checklist.md`,
  `src/njit_auditor/templates/index.html`, `tests/test_web_app.py`
- **What it does:** adds a "Try an example" box on the upload page with a one-click button
  that fills the URL-audit form with a public `digitalcommons.njit.edu` thesis URL (a
  publicly accessible Digital Commons record, not private or unpublished dissertation
  content).
- **Mergeable state (GitHub):** `CONFLICTING` / `dirty`
- **Conflict cause (verified via `git merge-tree origin/main <pr-head>`):** the actual UI
  change, `src/njit_auditor/templates/index.html`, **merges cleanly with no conflict**.
  The reported conflicts are confined to two documentation files
  (`docs/web_ui_demo_guide.md`, `docs/web_ui_manual_qa_checklist.md`) and one test file
  (`tests/test_web_app.py`), where unrelated edits landed on `main` since this PR branched
  on 2026-06-13.
- **Redundancy check:** no equivalent feature exists on `main`; not superseded by any
  recent merge.
- **Recommendation:** lower risk than PR #311 — the substantive change is already
  conflict-free, so a rebase mainly involves re-applying small additions to the two docs
  files and the test file. Confirms the prior assessment that this PR is a good rebase
  candidate. Left untouched in this stabilization task per explicit instruction (rebase to
  be done in a future, explicitly-requested task).

## Stash — `stash@{0}: On fix/student-facing-comment-wording: pre-stabilization unrelated local changes`

- **Created on branch:** `fix/student-facing-comment-wording`
- **Files touched:** `src/njit_auditor/polished_comments.py`, `src/njit_auditor/report_view.py`,
  `src/njit_auditor/rules/pdf_body_spacing.py`, `src/njit_auditor/rules/pdf_font_compliance.py`,
  `tests/test_pdf_rules.py`, `tests/test_report_view.py` (6 files, +157/−10 per
  `git stash show --stat`)
- **What it contains:** a `bbox`/highlight-eligibility extraction path in `report_view.py`
  (`_parse_bbox_from_details`, gated on `pdf_highlight.is_drawable_bbox`), a
  `sanitize_suggested_fix_for_web()` helper plus `_REMEDIATION_OVERRIDES` in
  `polished_comments.py` for P023/P026/P028, and direct edits to the raw `suggested_fix`
  text inside the `pdf_body_spacing.py` and `pdf_font_compliance.py` detectors themselves
  (replacing LaTeX-only wording such as `\doublespacing` / `\usepackage{mathptmx}` with
  word-processor-only phrasing at the detector level).
- **Redundancy check (verified by reading current `main`):** the bbox/highlight-eligibility
  logic and the `sanitize_suggested_fix_for_web()` / `_REMEDIATION_OVERRIDES` mechanism are
  **already implemented on `main`**, more completely, as part of the merged PR #320–#324
  actionability stack — `report_view.py` already imports `sanitize_suggested_fix_for_web`
  and already has `bbox`/`has_highlight` fields on `FindingView`, and
  `polished_comments.py` already has `_REMEDIATION_OVERRIDES` covering the same rule IDs.
  Applying this stash now would conflict with code that has since evolved past it.
- **One part not mirrored on `main`:** the stash edits the raw `suggested_fix` string
  inside the detector modules (`pdf_body_spacing.py`, `pdf_font_compliance.py`) directly.
  `main` deliberately leaves that raw detector wording untouched (it still contains
  `\doublespacing` / `\usepackage{mathptmx}`) and instead sanitizes it at the presentation
  layer via `sanitize_suggested_fix_for_web()`. The stash's detector-level edit conflicts
  with this now-established convention of not rewriting canonical/raw rule wording in the
  detector source.
- **Possibly salvageable nugget:** the stash's three tests
  (`test_p023_suggested_fix_has_no_raw_latex_syntax`,
  `test_p026_suggested_fix_has_no_raw_latex_syntax`,
  `test_polished_comments_have_no_raw_latex_syntax`) assert that the web-facing
  `suggested_fix`/polished comment never leaks raw LaTeX syntax. No test with an
  equivalent name or assertion currently exists on `main` — this is a small, real test
  coverage gap, separate from the (already-superseded) implementation changes.
- **Recommendation:** do **not** pop or apply this stash onto `main` as-is — most of its
  logic is superseded, and its detector-level wording edit conflicts with the established
  sanitize-at-render convention. If kept, it should only be inspected on a disposable
  throwaway branch; at most, the three missing test assertions are worth re-authoring
  fresh against current `main` in a small, separate test-only PR. Left untouched (not
  popped, not applied, not dropped) in this stabilization task per explicit instruction.

## What was and was not done while writing this document

- Read `gh pr view`/`gh pr diff` output for PR #311 and PR #305.
- Ran read-only `git merge-tree origin/main <pr-head>` for both PRs (no working-tree or
  index mutation; this is the same mechanism used in the prior full repository audit).
  Fetched each PR head into a scratch ref (`refs/tmp/pr311`, `refs/tmp/pr305`) for the
  comparison, then deleted both scratch refs immediately after — no branch, tag, or
  remote-tracking ref was left behind.
- Ran `git stash show --stat` and `git stash show -p` to read the stash's diff.
- Did **not** run `git stash pop` or `git stash apply`.
- Did **not** rebase, push to, or modify PR #311 or PR #305 in any way.
- Did **not** delete the stash or any branch.
