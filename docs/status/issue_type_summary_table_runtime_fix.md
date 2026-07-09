# Issue Type Summary Table — Runtime Visibility Fix

**Date:** 2026-07-09
**Baseline:** `origin/main` @ `c68dcfe18907117c5f0876389af8edd8d35b37aa` (PR #490 merge)
**Branch:** `fix/issue-type-summary-table-visible-runtime`

## Symptom

PR #490 ("Restore compact issue type summary table") merged as `c68dcfe`, and its own
tests passed. Soroush still did not see the "Findings by topic" table after auditing a
document in the browser.

## Root cause: the code was correct, the live process was stale

`src/njit_auditor/templates/job.html` on `origin/main` at `c68dcfe` already renders the
table exactly as intended:

- A plain `<section id="section-topics" class="section" aria-label="Findings by
  topic">` — **not** inside a `<details>` element.
- A compact 3-column table (`Topic` / `Findings` / a "Review all" link), populated from
  `category_summary` in `src/njit_auditor/web_app.py` (`_job_page_context`), which is
  built from `report_view["counts_by_category"]` for every completed job.
- Positioned after "Findings in page order" and before "Downloads", matching the
  intended layout.
- Labels come from `humanize_cat` (e.g. `"margin-or-overflow"` → `"Margins /
  overflow"`), never a raw `P0xx` rule ID.

`tests/test_web_app.py` already had (from PR #490 itself) `TestClient`-based tests
asserting the table is visible, sorted, uses clean labels, and links to a working
category drilldown — all of which passed, correctly, because they exercise the source
tree directly.

**The gap TestClient-style tests cannot cover: which code the long-running production
process actually has loaded.** The live server is a systemd user service
(`thesis-auditor-web.service`) that runs `uvicorn` out of a dedicated worktree,
`njit-thesis-auditor-clean-worktrees/live-current-main`, from a process that is started
once and kept running (`Restart=always` only restarts on crash, not on new commits).
Per the existing deploy convention ([[deploy_restart_after_merge]] in this repo's
project memory), that worktree is supposed to be a **detached-HEAD checkout, updated by
`git fetch && git checkout origin/main --detach`, and never edited or committed to
directly.**

Investigation found that convention had been violated:

- The worktree was on a **named branch**, `fix/ester-student-facing-alignment-pass`,
  checked out at `2f4b0d74` (PR #480, merged 2026-07-06) — **22 commits behind**
  `origin/main`, from *before* PR #490 existed.
- It had **15 files of uncommitted, unrelated WIP changes** directly in that
  worktree (wording-alignment work touching `report_view.py`, `job.html`,
  `polished_comments.py`, etc.), plus 2 untracked new files — work that had never been
  committed or pushed anywhere else.
- `systemctl --user status` confirmed the running process had started 2026-07-06
  15:04:48, hours before PR #490 was even opened, and had never been restarted since.

So the process serving Soroush's browser had (a) never had PR #490's commit in its
working tree at all, and (b) had a different, unrelated, uncommitted template edit to
`job.html` layered on top of that stale base. No amount of re-reviewing PR #490's diff
or test suite could have shown this — the defect was entirely in what was deployed, not
in what was merged.

## Fix applied

1. Rescued the uncommitted WIP with `git stash push -u -m "..."` inside
   `live-current-main` (nothing was discarded; recoverable via `git stash list` on that
   worktree, `stash@{0}`).
2. Restored the deploy convention: `git fetch origin && git checkout origin/main
   --detach`, landing the worktree on `c68dcfe` with a clean working tree.
3. Validated with `PYTHONPATH=.../live-current-main/src python -c "from njit_auditor
   import web_app"` and a targeted pytest run before touching the live process.
4. `systemctl --user restart thesis-auditor-web.service`, then confirmed via `GET
   /version` that the running process now reports commit `c68dcfe`.
5. Reproduced end-to-end against the restarted live server: uploaded
   `tests/fixtures/web_demo/issues_pdf.pdf` through the real HTTP API, fetched the
   rendered `/audits/{job_id}` page, and confirmed `#section-topics` renders as a
   visible table (`Margins / overflow` label, count, "Review all" link) between
   "Findings in page order" and "Downloads", with no `<details>` wrapper.

## Test added

`tests/test_web_app.py::test_findings_by_topic_section_always_visible_not_collapsed`
asserts, at the route level: the table section exists, is not nested inside any open
`<details>` ancestor, and sits after "Findings in page order" and before "Downloads".
This closes the one specific assertion gap in PR #490's own test suite (which checked
table content and ordering relative to "Findings in page order," but never explicitly
asserted "not wrapped in `<details>`" — the literal shape of Soroush's original
worry).

No test in this suite (or any suite) can detect "the systemd service is running old
code" — that is a property of the deployed process, not the source tree. The existing
`GET /version` endpoint (added for PR #436's deploy verification) is the correct tool
for that check and was used manually here, per
[[deploy_restart_after_merge]]. No template/CSS/JS change was needed; nothing hides
`#section-topics`.

## Why this could recur

The systemd unit does not auto-restart on new commits, and nothing currently enforces
that `live-current-main` stays on a clean, detached `origin/main`. If someone edits
files directly in that worktree again (as happened here), the "always restart after
merge" step alone will not fix a subsequent divergence — the stray commit/WIP has to be
stashed or moved out first. Consider, as a follow-up (not done in this PR, to keep scope
to the reported bug): a pre-restart check in the deploy script that fails loudly if
`live-current-main` is not a clean detached HEAD matching `origin/main`.
