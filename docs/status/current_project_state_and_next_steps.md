# Current Project State and Next Steps

> **Canonical status entry point.** Start here for current `main`, validation, open PRs,
> Q-rule coverage, and recommended next actions. Related indexes:
> [open PR triage](open_pr_triage.md) ·
> [Ester Q / P / public rule mapping](ester_q_p_rule_public_rule_mapping.md) ·
> [live deployment checklist](live_deployment_checklist.md) ·
> [evaluation data manifest](evaluation_data_manifest.md)

## Current Status — 2026-07-05, #8 (#376 P014 centering false-positive fix merged)

This section is the authoritative current snapshot. Everything below it (including the 2026-07-05
#7 snapshot, the 2026-07-05 #6 snapshot, the 2026-07-05 #5 snapshot, the 2026-07-05 #4 snapshot,
the 2026-07-05 #3 snapshot, the 2026-07-05 #2 snapshot, the 2026-07-05 #1 branch-cleanup snapshot,
the 2026-07-04 #435/#439 reconciliation snapshot, the earlier 2026-07-04 post-merge-cleanup
snapshot, 2026-07-03/PR #433 snapshot, 2026-07-02 PR #409 snapshot, PR #407/#408 behavior
snapshot, PR #406 merge snapshot, live regression diagnosis / cleanup-paused snapshot,
post-#405-merge snapshot, post-#388-closure snapshot, post-#386-closure snapshot, P018 public-cards
snapshot, earlier 2026-07-02 cleanup, 2026-07-01, 2026-06-25, and earlier dated bullets) is
preserved as historical context and should not be read as current.

- **Code baseline `main`:** `72b8736` (squash-merge of PR
  [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376), `Fix P014 frontmatter
  heading centering false positive`, on top of `#375`/`#460` stack ending at `1b6f8d5`). Short SHA:
  `72b8736`.
- **Reviewed, rebased, and merged #376** (narrow P014 centering false-positive fix only):
  - `_line_centering()` now accepts headings within existing tolerance of **either** text-area
    midpoint or physical page midpoint (asymmetric NJIT margins: 18pt offset between the two on
    letter paper).
  - `CENTER_TOLERANCE_PT` (18pt) and `BORDERLINE_CENTER_TOLERANCE_PT` (26pt) **unchanged** — not a
    broad policy loosening.
  - Page-centered `BIOGRAPHICAL SKETCH` no longer warns; flush-left still warns.
  - Validation: `ruff check .` — passed; `mypy src` — no issues in 105 files; `python -m pytest` —
    **2585 passed**; GitHub CI — passed.
  - Remote branch `fix/p014-frontmatter-centering-false-positive` deleted at merge time.
- **Live server:** serving `b6cc8db` (#460) — **not** updated in this pass (no deployment action
  taken); `72b8736` will be picked up by a future deploy pass.
- **Open PR count:** **0** — no remaining open PRs.

### Next recommended work

1. Deploy `72b8736` to the live server when ready (not done in this pass).
2. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-05, #7 (#375 confirmed merged — no action required)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `b6cc8dbc6fb2b2a2f96a84bf59c648322161dfa4` (squash-merge of PR
  [#460](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/460), on top of `#375` at
  `d89f4ce`). Short SHA: `b6cc8db`.
- **#375 final state:** **Merged** (`d89f4cef082bafc71a0e8dcb18fc37f05e53fed8`, 2026-07-05).
  Re-triaged this pass — all changes confirmed present on `main`; no further action required.
  Docs/test-only: aligns `clean_minimal.pdf` demo baseline with residual P011/P013/P027 outputs.
- **Live server:** serving `b6cc8db` — **not** updated in this pass (no deployment action taken).
- **Open PR count:** **1** — [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376)
  only.

### Next recommended work

1. Review **#376** (P014 frontmatter centering false positive) after a fresh rebase and CI run.
2. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-05, #6 (#375 clean_minimal demo baseline docs merged)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `d89f4cef082bafc71a0e8dcb18fc37f05e53fed8` (squash-merge of PR
  [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375), `Align clean_minimal demo
  docs and tests with actual audit output`, on top of `#459` at `95e3aa5`). Short SHA: `d89f4ce`.
- **Reviewed, rebased, and merged #375** (docs/test-only demo-baseline alignment — no detector,
  threshold, rule-ID, UI, or export changes):
  - Corrected stale documentation that described `tests/fixtures/web_demo/clean_minimal.pdf` as a
    zero-finding / "passes all checks" baseline. The fixture is a minimal web-demo input with known
    residual outputs: **P011** (WARNING), **P013** (PASS), **P027** (WARNING).
  - Updated `docs/planning/synthetic_web_demo_fixtures.md` §3.1, `docs/web_ui_demo_guide.md`,
    `scripts/web_demo_smoke.sh`, and `README.md`; added
    `test_clean_minimal_pdf_produces_expected_residual_findings` in
    `tests/test_web_demo_fixtures.py`.
  - Prior CI was failing on a stale branch (~122 commits behind current `main`); rebased via
    cherry-pick onto `95e3aa5` (LFS smudge-filter artifact blocked `git rebase` in worktrees).
  - Validation: `ruff check .` — passed; `mypy src` — no issues in 105 source files; `python -m
    pytest` — **2580 passed**.
  - Remote branch `docs/fix-clean-minimal-demo-baseline` deleted at merge time.
- **Live server:** still serving `95e3aa5` (#459) — **not** updated in this pass (no deployment
  action taken, per task scope); `d89f4ce` will be picked up by a future deploy pass.
- **Open PR count:** **1** — #376 only. #375 is no longer open.

### Next recommended work

1. Review **#376** (P014 frontmatter centering false positive) on its own merits after a fresh
   rebase and CI run.
2. Optionally deploy `d89f4ce` to the live server when ready (not done in this pass).
3. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-05, #5 (#437 P011 margin visual polish merged)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `d883e9e49fa02fe73f7fd18849265d628f5453a1` (squash-merge of PR
  [#437](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/437), `fix: polish P011 margin
  warning evidence`, on top of `#457` at `77f4f46`). Short SHA: `d883e9e`.
- **Reviewed, rebased, and merged #437** (P011 margin-warning visual evidence/clarity polish only —
  strictness, thresholds, rule ID, issue type, confidence, sorting, and export schema all confirmed
  unchanged):
  - `pdf_margins.py`: each violating line now carries its `line_index` (position in the page's
    top-to-bottom block/line enumeration order). Same-side violations are grouped into tight
    highlight boxes only when no other line (violating or not) separates them in that order —
    separated violations now draw as separate boxes instead of one union spanning unrelated clean
    content between them. A new `margin_boundary_bbox` detail field draws a thin guide rectangle at
    the exact required margin boundary (vertical for left/right, horizontal for top/bottom), scoped
    to the affected region. The pre-existing `bbox` union field is unchanged (kept as a
    backward-compatible fallback); `OVERFLOW_TOLERANCE_PT`, `ARTIFACT_GUARD_*`, and the four margin
    constants are untouched.
  - `highlight_targeting.py`: `parse_highlight_bboxes_from_details()` returns the new precise
    per-group boxes plus the boundary guide for P011 findings (`rule_id == "P011"` and
    `issue_type == "margin_boundary_violation"`), instead of falling back to the single union
    `bbox`. The existing per-page aggregation in `web_app._highlight_boxes_by_page` already handles
    multiple boxes per finding with no further changes needed, so a mixed-side page (e.g. top +
    right) automatically gets separate box+guide pairs per side.
  - `p011_student_preview.py`: `P011PagePresentationStats` gained an additive `side_stats` field; the
    combined-card (mixed-side) comment now appends a concrete "Side detail: right margin (~X pt
    over, N line(s) affected); ..." breakdown instead of only a vague count.
  - `polished_comments.py`: the single-side P011 comment (Markdown/export pipeline) now states the
    rule is strict and applies "even by a small amount" — wording only, no behavior change.
  - **Known limitation (not a regression):** the adjacency grouping uses PDF content-stream
    block/line order as a proxy for visual top-to-bottom position. For a typical born-digital
    dissertation PDF (single-column, text emitted in reading order) this holds and produces tight,
    correctly separated highlight boxes. In a synthetic adversarial case built during this review
    (violating lines emitted out of visual order in the content stream), the grouping fell back to
    unioning across intervening clean content — but this is never worse than pre-PR behavior, which
    always unioned every same-side violation into one box regardless of position. Documented here
    rather than blocking the merge.
  - **Rebase:** the PR's remote branch was based on an older `main` (`07db2fa`, ~22 commits behind
    the merge baseline); rebasing via `git rebase` was blocked by a pre-existing, repo-wide git-LFS
    smudge-filter artifact (pointer/binary mismatch on `data/raw/**` and `tests/fixtures/web_demo/**`
    files, present in every worktree checked, unrelated to this PR and never committed). Worked
    around by creating a new branch directly from `origin/main` and cherry-picking the PR's single
    commit onto it (`git cherry-pick`, not `git rebase`) — applied with zero conflicts; diff stat
    identical to the original PR. Force-pushed the result to the PR branch (explicitly authorized by
    the task's own "Rebase/update #437 onto latest origin/main if needed" instruction).
  - **Manual verification:** ran the app on a scratch port (`127.0.0.1:8917`, not the live systemd
    service) with `PYTHONPATH` pointing at the review worktree, uploaded a synthetic PDF with two
    separated right-margin overflow lines, confirmed via the real `/audits/{id}/highlighted-page.pdf`
    endpoint that the two violating lines get separate tight highlight boxes plus one thin vertical
    boundary guide at the right-margin line — clean intervening body text is not highlighted.
    Confirmed JSON export is additive (`bbox` unchanged, `highlight_bboxes`/`margin_boundary_bbox`
    new). Confirmed original-PDF and Markdown/JSON download endpoints all return 200. Rendered the
    report page in headless Chromium (Playwright) at a 390px viewport: no horizontal overflow
    (`scrollWidth == clientWidth == 390`), P011 card renders cleanly.
  - Validation: `ruff check .` — passed; `mypy src` — no issues in 105 source files; `python -m
    pytest` — **2568 passed** (2512 pre-PR baseline claimed by the PR + 22 commits' worth of tests
    added to `main` since + 8 new P011 tests). Re-confirmed on the merged `main` commit itself.
  - Remote branch `fix/p011-margin-visual-polish` deleted at merge time.
- **Live server:** still serving pre-`d883e9e` code — **not** updated in this pass (no deployment
  action taken, per task scope); `d883e9e` will be picked up by a future deploy pass.
- **Open PR count:** **2** — #375, #376 (both stale, need rebase + fresh CI before any merge
  decision). #437 is no longer open.

### Next recommended work

1. Resume review of **#375**/**#376** only after a fresh rebase and CI run; both are stale relative
   to current `main`.
2. Optionally restart the live server after merging so `/version.commit` matches current `main`
   (not done in this pass).
3. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-05, #4 (#436 list-entry highlight/bbox fix merged)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `5c37a115a1313028225b28faa9765bb615eeb2ad` (squash-merge of PR
  [#436](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/436), `fix: highlight affected
  list entries for punctuation warnings`, on top of `#454` at `3fba82e`). Short SHA: `5c37a11`.
- **Reviewed and confirmed #436** (evidence/highlight-only, no detector/threshold/rule-ID/export
  change): P040 (List of Figures missing terminal punctuation), P053 (List of Tables entry ends
  with a period), and P054 (Table of Contents entry ends with a period) findings previously stored
  no `bbox`, so `highlight_targeting.resolve_primary_highlight_bbox()` had nothing to work with and
  the UI fell back to "Open original PDF page" instead of a highlighted page, even though the
  offending entry's line geometry (`entry.line.bbox`) was already computed internally.
  - Added `details["bbox"] = format_bbox_detail(entry.line.bbox)` to all three rules — no new
    geometry, just exposing what each detector already computed.
  - Added `details["page_type"] = "list_of_figures"` to P040 only, so the shared `report_view`
    location-label helper resolves "List of Figures" instead of the generic "list" fallback. P053/
    P054 already set `section_type` and needed no equivalent change.
  - Deliberately did **not** add full entry-text reproduction (`affected_entry_preview`, used by
    P018/P046): existing tests (`test_p040_findings_metadata_no_private_content`,
    `test_p053_finding_metadata_privacy_safe`) assert no LoF/LoT/TOC entry text may appear in
    `details` — a stricter privacy contract than P018/P046. Location clarity comes from
    `page_type`/`section_type` + `page_entry_index` only.
  - Verified directly from the diff (6 files, +205/−51): `pdf_lof_terminal_punctuation.py`,
    `pdf_lot_terminal_period.py`, `pdf_toc_terminal_period.py`, `tests/test_pdf_rules.py`, and two
    `docs/status/*` files — no rule ID, issue type, threshold, grouping key, confidence label,
    sorting behavior, or JSON/Markdown export schema changed; finding counts unchanged.
  - New regression tests confirm: bbox present and resolves to a visible highlight
    (`has_visible_highlight`) for all three rules; only the truly offending entry is flagged
    (others on the same page stay clean); the P040 location label reads "List of Figures" (not the
    generic fallback); rule ID/issue type/finding count are unchanged by the fix.
  - Remote branch `fix/list-entry-highlight-polish` already deleted at merge time.
- **Live server:** still serving pre-`013c836` code — **not** updated in this pass (no deployment
  action taken); `5c37a11` will be picked up by a future deploy pass.
- **Open PR count:** **3** — #437 (P011 margin visual polish, detector/highlight fix awaiting
  human/Ester review), #375, #376 (stale, need rebase + fresh CI before any merge decision). #436
  is no longer open.
- Validation re-run on `5c37a11` in a fresh worktree (not the shared `main` checkout, which had
  unrelated in-progress uncommitted changes left by other work): `ruff check .` — passed; `mypy
  src` — no issues in 105 source files; `python -m pytest` — **2557 passed** (7 more than the
  2550 recorded at `013c836`, matching the 7 new P040/P053/P054 regression tests added by #436).
  Does not touch P021, P026, rule IDs, or detector/threshold behavior; P084 not started.

### Next recommended work

1. Review **#437** (P011 margin visual polish) on its own merits — unrelated to #436, no shared
   files.
2. Resume review of **#375**/**#376** only after a fresh rebase and CI run; both are stale relative
   to current `main`.
3. Optionally restart the live server after merging so `/version.commit` matches current `main`
   (not done in this pass).
4. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-05, #3 (#454 findings-controls simplification merged)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `013c836103d635e26375d85b7ce4ef9363a5d684` (squash merge of PR
  [#454](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/454), `refactor: simplify
  findings controls and default to page order`). Short SHA: `013c836`.
- **Reviewed and merged #454** (presentation/sorting-only, no detector/threshold/rule-ID/export
  change):
  - Removed the student-facing **Severity** filter dropdown from the Findings control bar
    (`job.html`) — severity was already redundant with the per-card status badge, and most
    findings are review signals rather than confirmed defects. Removed the now-unused
    `filter-severity` JS filtering logic, `data-severity` dataset attributes, and the
    `filter_severities` context variable in `web_app.py`. Severity badges (Fail/Review/Info) on
    finding cards are unchanged.
  - Made **page order** the default grouped-problem order: `sort_grouped_problems()`'s `"default"`
    mode now sorts by earliest affected page (same output as the existing `"page_order"` value),
    matching front-to-back dissertation review instead of an arbitrary insertion order. Multi-page
    cards sort by their minimum affected page; pageless findings sort last; same-page cards keep
    stable relative order.
  - Renamed the "Sort problems" dropdown's default option from "Default order" to **"Page order"**
    and folded the now-redundant standalone `page_order` `<option>` into it — an explicit
    `?sort=page_order` query string still resolves identically.
  - Kept Rule, Category, Page, and Confidence filters and Reset filters unchanged; no JSON/Markdown
    export, grouping-key, or confidence-logic change.
  - Verified directly from the diff (7 files, +92/−54): `report_view.py`, `templates/job.html`,
    `web_app.py`, and four test files only — no `src/njit_auditor/rules/*.py` touched.
  - Manually verified mobile behavior: started the app locally on a scratch port (not the live
    systemd/tmux service), ran a real audit against
    `tests/fixtures/web_demo/issues_pdf.pdf`, and inspected the rendered results page in headless
    Chromium at 390px width — filter bar height dropped from ~304px to ~243px (less crowded), no
    horizontal overflow (`scrollWidth == clientWidth == 390`), "Page order" selected by default,
    severity badge still rendered on cards.
  - Merged with squash (`013c836`); deleted the remote branch
    `refactor/findings-controls-page-order`.
- **Live server:** still serving `55149ac`/`a5f6c74`-era code — **not** updated in this pass (no
  deployment action taken); `013c836` will be picked up by a future deploy pass.
- **Open PR count:** **4**, unchanged — #436, #437 (detector/highlight fixes awaiting
  human/Ester review), #375, #376 (stale, need rebase + fresh CI before any merge decision). #454
  was not one of the tracked open-PR-triage items (opened and merged within this same pass).
- Validation on the merged commit (`013c836`): `ruff check .` — passed; `mypy src` — no issues in
  105 files; `python -m pytest` — **2550 passed**. Does not touch P021, P026, rule IDs, or
  detector/threshold behavior; P084 not started.

---

## Historical — 2026-07-05, #2 (#440 P016/P023 non-body-spacing fix reviewed and merged)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `a5f6c7428f5de1b6afb8311f737a0b9de691bd3f` (merge of PR
  [#440](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/440), P016/P023 non-body-content
  spacing false-positive fix). Short SHA: `a5f6c74`.
- **Reviewed, rebased, and merged #440** (`fix(P016,P023): stop flagging non-body content as body
  spacing`) after manual review found both rules treating non-body content as ordinary body text:
  - **P016:** skips `BIOGRAPHICAL SKETCH`/`APPROVAL PAGE` special-layout front-matter pages (their
    large author/degree/date or committee-signature gaps are intentional template layout);
    `ABSTRACT`/`ACKNOWLEDGEMENTS` remain fully checked. Corrected wording from "before a heading"
    to "after a heading" (the detector always measured the gap after the heading; only the wording
    was wrong).
  - **P023:** excludes captioned table regions (caption-anchored band spanning the caption plus
    contiguous tightly packed rows, via the existing `detect_caption_lines()` utility) and the
    entire References/Bibliography section including continuation pages (via a new, purely
    additive `references_section_page_numbers()` helper). Findings now carry a `bbox` plus
    `measured_body_line_count`/`measured_gap_count` so evidence points at the actual measured
    lines.
  - Verified directly from the diff: no rule IDs changed, no existing threshold constants
    modified, no grouping/sorting/confidence/export code touched. Table detection uses real table
    captions only, so figure-caption pages are unaffected; table borders were never part of the
    text-line measurement (graphic strokes, not text).
  - Rebased cleanly (zero conflicts) from its original stale base (`c8a1043`) onto `main` @
    `5835ca6`; force-pushed to the PR branch.
  - All 7 of the PR's regression tests pass alongside the full 2542-test baseline (2549 total).
  - Merged with squash (`a5f6c74`); deleted the remote branch `fix/p016-p023-nonbody-spacing`. (A
    local, non-rebased copy remains checked out in an unrelated pre-existing worktree
    (`wt-spacing`) on the host — left untouched; this doesn't affect that worktree.)
- **Live server:** still serving `55149ac` — **not** updated in this pass (no deployment action
  taken); `a5f6c74` will be picked up by a future deploy pass.
- **Open PR count:** **4** — #436, #437 (detector/highlight fixes awaiting human/Ester review),
  #375, #376 (stale, need rebase + fresh CI before any merge decision). Down from 5 now that #440
  is resolved.
- Validation on the merged commit (`a5f6c74`): `ruff check .` — passed; `mypy src` — no issues in
  105 files; `python -m pytest` — **2549 passed**. Does not touch P021, P026, rule IDs, unrelated
  thresholds, or unrelated capitalization/margin/font/page-numbering/TOC/title-page behavior.

---

## Historical — 2026-07-05, #1 (#439/#435 branches deleted; live server confirmed at `55149ac`)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `55149ac2b662c455a67c636489239e6af4a60062` (merge of PR
  [#451](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/451), removal of the redundant
  "Most common issues" section — presentation-only, no detector change). Short SHA: `55149ac`.
- **Live server:** confirmed serving `55149ac` via `GET /version` on both `127.0.0.1:8000` and the
  host's external LAN address (`10.196.93.210:8000`) — current with `main`. The UI-decluttering
  PRs #448 (restore "Findings by topic" table), #450 (simplify it to a compact 3-column table:
  Topic/Findings/Review all), and #451 (remove the now-redundant "Most common issues" section)
  were deployed across prior passes; this pass made **no** deployment or code change, docs/branch
  cleanup only.
- **Branch cleanup:** re-confirmed #439 (`fix/p020-stat-notation-capitalization`) is `MERGED` and
  #435 (`fix/titlecase-technical-notation`) is `CLOSED`, and neither branch is the head of any open
  PR (both had been deliberately left undeleted since the 2026-07-04 reconciliation pass below,
  pending explicit authorization). **Deleted both remote branches** in this pass.
- **Open PR count:** **5** — #436, #437, #440 (detector/highlight fixes awaiting human/Ester
  review), #375, #376 (stale, need rebase + fresh CI before any merge decision). Unchanged from the
  previous pass other than the count dropping from 6 now that #435 is resolved.
- No `ruff`/`mypy`/`pytest` run was required for this pass beyond the docs update itself, since no
  source files changed. No detector logic, rule IDs, thresholds, P021/P026, or UI behavior were
  touched.

---

## Historical — 2026-07-04 (reconciled #435/#439 statistical-notation title-case fixes — #439 merged, #435 closed)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `82f2d901bd20a52231088f861f9d75a4e9105fc6` (merge of PR
  [#439](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/439)). Short SHA: `82f2d90`.
- **Resolved the overlapping #435/#439 statistical-notation title-case PRs.** Both fixed the same
  false positive (lowercase `n` in `(n = 97)` flagged as a capitalization violation in
  `check_apa_title_case_phrase()`, shared by P020/P024/P027), but differed in completeness — verified
  empirically with a probe script run against both branches, not just by inspection:
  - Both correctly preserve the strict `Comparison with Prior Studies` → `With` policy and still
    flag real lowercase words inside parentheses (e.g. `pilot` in `(pilot study)`).
  - **#435** only exempted a single letter immediately followed by a relational operator (`n =`,
    `p <`, ...). Empirically, it still flagged bare statistical abbreviations without an adjacent
    operator — e.g. `t` in "Test Statistic t Value" and `df` in "Degrees of Freedom df" — and it
    never touched the suggested-fix substring-replacement mechanism, so the underlying
    `Linear`→`LiNear`-style corruption bug remained latent for any other short flagged word.
  - **#439** exempts a fixed set of statistical abbreviations (`n, p, r, r², b, se, sd, df, t, f,
    m, ci`) case-insensitively, correctly leaving bare `t`/`df`/`SE`/`F` unflagged; makes
    suggested-fix generation token/span-safe via whole-word regex matching in
    `title_case_student_preview.py` and `highlight_targeting.py` (verified: `LiNear` never
    appears); and adds the required P027 exact sentence-case "Change X to Y" replacement (e.g.
    `4.4.1 Scatterplots Of Relationships With Readiness` → `4.4.1 Scatterplots of relationships
    with readiness`).
  - **Merged #439** (rebased onto `main` first — its branch predated the #441–#446 UI stack).
    **Closed #435** as superseded, with a comment citing the specific empirical gaps above. No
    piece of #435 was worth cherry-picking separately since #439 is a strict superset. Neither
    branch was deleted (not authorized this round).
  - Validation on final `main` (`82f2d90`): `ruff check .` — passed; `mypy src` — no issues in 105
    files; `python -m pytest` — **2538 passed**. Does not touch P021, P026, rule IDs, thresholds
    beyond the narrow statistical-notation exemption, or unrelated spacing/margin/font/
    page-numbering/TOC/title-page behavior.

---

## Historical — 2026-07-04 (post-merge cleanup — branches deleted, live server restarted on `991e683`)

> **Superseded** by the section above. Preserved here for historical context only.

- **Code baseline `main`:** `991e683e87f51b3032be0bcab71f7f611c0be394` (merge of PR
  [#445](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/445), the docs-only triage
  write-up — no behavior change since `b17cbb6`/#444). Short SHA: `991e683`.
- **Post-merge branch cleanup (this pass):** deleted the 10 remote branches behind the merged/closed
  PRs from the previous triage pass — verified each PR was `MERGED`/`CLOSED`, not the head of any
  open PR, before deleting:
  - Merged: `feature/student-summary-declutter` (#441), `fix/findings-cards-mobile-safe` (#442),
    `refactor/simplify-summary-counts` (#443), `refactor/simplify-nav-chips` (#444),
    `docs/repo-polish-inventory` (#434), `docs/pr-triage-status-update` (#445).
  - Closed/superseded: `feature/subpage-location-labels` (#311),
    `docs/protect-autonomous-policy-and-ester-status` (#349), `ux/review-needed-prefix-policy`
    (#362), `ux/rule-reference-card-declutter` (#385).
  - Branches for the 7 still-open PRs (#435–#437, #439, #440, #375, #376) were left untouched.
- **Live server:** updated and restarted — now serving `991e683` (confirmed via `/version` on both
  `127.0.0.1:8000` and the host's external address). Previously stale at `425f144` (PR #430). The
  old process had been orphaned (reparented to init, detached from its original tmux shell) rather
  than a live job of the `thesis-auditor-web` tmux session; it was stopped with `SIGTERM` and the
  replacement was started fresh inside that same tmux session so it's supervisable again.
  Post-restart smoke test (Playwright, real sample audit): "Items to review" card present, no
  "Problems found"/"Worth checking" summary cards, nav chips show the primary flow first with
  "Advanced details"/"Advanced candidates" demoted, rule-by-rule table confirmed collapsed under
  `<details>`, and mobile `document.body.scrollWidth` stayed at exactly 390px (no overflow) at a
  390px viewport.
- **Merged this pass (5 PRs, in dependency order):**
  - **#441** — decluttered the student-facing report summary: merged "Summary by problem type" and
    "Most common issues" into one set of root-cause cards, collapsed the rule-by-rule table behind
    an "Advanced" `<details>`, de-emphasized informational-only counts, cleaned category labels.
  - **#442** — fixed a real mobile horizontal-overflow bug in the Findings section's grouped-problem
    cards (`min-width: 0` on the CSS grid item + a new wrapping `.detail-cell` class instead of
    reusing the nowrap `.meta-cell` for sentence-length text).
  - **#443** — simplified the top Summary cards: "Problems found" → "Items to review", dropped the
    always-redundant "Worth checking" card, "Needs fixing" only renders when there's a real
    fail-level finding.
  - **#444** — simplified the nav chips: primary chips (Summary/Review order/Most common
    issues/Findings/Downloads) grouped first, the rule-by-rule table and detected-candidates chips
    renamed "Advanced details"/"Advanced candidates" and visually demoted.
  - **#434** — docs-only repository polish inventory.
  - Each PR after #441 was rebased onto the new `main` (not just fast-forwarded) since every merge
    was a squash, and re-validated (`ruff`, `mypy`, `pytest`) before merging the next one. No
    detector logic, rule IDs, thresholds, JSON/Markdown export, or highlight generation changed in
    any of the four — presentation-layer only.
- **Closed this pass (4 PRs, all confirmed superseded by direct comparison against current `main`,
  not just because they were old; no branches deleted):**
  - **#311** (sub-page location labels) — `main` already has a far more complete per-rule
    location-label system.
  - **#349** (autonomous policy + Ester audit doc) — both changes already on `main`; the audit doc
    is explicitly marked historical there.
  - **#362** ("Review needed:" prefix policy) — `main` took the opposite, already-implemented
    direction (unconditional prefix + one global caveat, not per-rule removal).
  - **#385** (rule-reference card declutter) — `main`'s cards are already simpler than this PR's
    proposed end state.
- **Still open (7 PRs) — left for human/Ester review, not merged:**
  - **#435, #436, #437, #439, #440** — all touch `src/njit_auditor/rules/*.py` (real
    detector-behavior changes: false-positive suppressions, highlight/evidence polish). CI passes
    on all five, but this project treats any change to what gets flagged as a human/Ester sign-off
    decision, not a blind agent merge. **#435 and #439 overlap** — both fix the same `(n = 97)`
    statistical-notation false positive in `pdf_title_capitalization.py` via different techniques;
    commented on both cross-linking the conflict rather than picking a winner.
  - **#375, #376** — CI is currently **failing** on both (stale against current `main`); left open
    rather than closed since neither is clearly superseded, but both need a rebase and a fresh CI
    run before anyone merges them.
- **P021/P026 policy:** still unresolved — see `ester_policy_review_p021_p026.md`. Not touched.
- **P084:** not started. Not touched.
- **Validation on final `main` (`991e683`):** `ruff check .` — all checks passed; `mypy src` — no
  issues in 105 files; `python -m pytest` — **2529 passed**.

---

## Historical — 2026-07-03 (PR #433 merged — Ester wording/presentation/highlight stack landed; 4 new PRs open)

> **Superseded** by the 2026-07-04 section above. Preserved here for historical context only.

- **Code baseline `main`:** `07db2fa30b457006cf7524309c8eabcca6ff64c8` (merge of PR
  [#433](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/433)). Short SHA: `07db2fa`.
- **Merged since the 2026-07-02/PR #409 snapshot below (24 PRs, #410→#433):**
  - **#410** — live deployment verification after #409 (docs only).
  - **#411–#413** — Ester feedback source-of-truth snapshot, language alignment audit, current
    wording inventory (docs/planning only, no behavior change).
  - **#414–#420** — Ester wording alignment **Slices 1–6**: wording/remediation text only for 29
    rules (P011, P013, P023, P028–P032, P036, P039–P050, P053–P055, P066–P068, P074, P078). No
    detector thresholds, rule IDs, issue types, grouping keys, or report schema changed in any
    slice.
  - **#421** — wording alignment checkpoint (docs).
  - **#422** — P021/P026 policy-review questions recorded (docs only; **P021/P026 policy remains
    unresolved and unimplemented** — word-count limits and accepted font families still need a
    human/Ester decision before any detector change).
  - **#423–#424** — broad Ester-style presentation-split plan and atomic issue_type→card mapping
    for P014/P015/P017/P018/P019/P020/P024/P025/P027 (docs/planning only; **no splits
    implemented**).
  - **#425** — student-facing presentation cleanup plan (docs/planning).
  - **#426** — **feat:** page-order sorting for audit problems (additive `?sort=page` mode;
    existing confidence-sort default preserved).
  - **#427** — **chore:** confidence display simplified to exactly High/Medium/Low; "Priority"
    filter label renamed to "Severity" to stop conflating it with the confidence badge.
  - **#428** — highlight quality improvement plan (docs/planning).
  - **#429** — highlight-target baseline tests (test-only, pins pre-change highlight geometry).
  - **#430** — **fix:** P011 highlight now unions every violating line's box (not just the worst
    offender) for multi-line same-side violations.
  - **#431** — **fix:** confidence badge now renders on every problem card, including the
    category/rule/issue-type drill-down pages that previously showed none.
  - **#432** — Ester current-consistency audit vs. latest available Ester source files (docs).
  - **#433** — **chore:** removed stale unreachable `("P025", "title_page_graduation_month_invalid")`
    dict entries (P074 is the only rule that actually emits this issue_type).
- **Open PRs awaiting review/merge (all `mergeStateStatus: CLEAN` as of this snapshot):**
  - **#434** `docs: inventory repository polish tasks` — repository baseline/cleanup inventory
    (docs only).
  - **#435** `fix: ignore statistical notation in title-case checks` — P020/P024/P027 shared
    title-case helper no longer flags single-letter statistical notation (e.g. `n` in `(n = 97)`);
    real lowercase-major-word violations still flag.
  - **#436** `fix: highlight affected list entries for punctuation warnings` — P040/P053/P054 now
    store a `bbox` for the offending entry line so the highlighted-PDF button works; no entry text
    added to details (existing privacy-safe contract preserved).
  - **#437** `fix: polish P011 margin warning evidence` — separated same-side violations get
    distinct tight highlight boxes instead of one union spanning unaffected lines; a margin
    boundary guide line is drawn; mixed-side pages keep one rolled-up card but gain a per-side
    overflow/line-count breakdown.
  - See [open_pr_triage.md](open_pr_triage.md) for the full triage, including the still-paused
    older PRs.
- **Old paused PRs — unchanged, still paused:** #311, #349, #362, #375, #376, #385. **Do not**
  merge, close, rebase, or delete these without explicit instruction.
- **P021/P026 policy:** still unresolved (word-count limits, accepted font families). Not
  implemented by any PR in this range.
- **P084:** not started; out of scope unless explicitly requested.
- **Live server:** last confirmed at `commit=425f14442a4dca3701676b4c66db368d7aab46c1` (PR #430) —
  **3 merges behind** current `main` (`07db2fa`, PR #433). Not restarted by this status refresh
  (this is a documentation-only pass); see [live_deployment_checklist.md](live_deployment_checklist.md)
  for the restart procedure when next doing behavior-affecting work.
- **Full validation on `main` @ `07db2fa` (2026-07-03, clean worktree, no local WIP):**
  `ruff check .` clean; `mypy src` clean (105 source files); `python -m pytest` → **2512 pytest
  passed**, 1 warning (pre-existing duplicate-zip-member warning in upload tests).

### Next recommended work

1. Review and merge the docs-only PR **#434** first (lowest risk), then the three detector/
   presentation fix PRs **#435**, **#436**, **#437** independently once each is reviewed — they
   are unrelated to each other and can merge in any order.
2. Optionally restart the live server after merging so `/version.commit` matches current `main`.
3. Resume review of the older paused PRs (#311, #349, #362, #375, #376, #385) only after explicit
   human instruction — they are unrelated to the current cleanup and carry their own review
   history (see [open_pr_triage.md](open_pr_triage.md)).
4. **P021/P026 policy resolution** — send the drafted policy-confirmation questions
   (`docs/status/ester_policy_review_p021_p026.md`) to Ester/a policy owner before any detector
   change to word-count limits or accepted font families.
5. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-02 (PR #409 merged — status docs synced on main)

> **Superseded** by the 2026-07-03 snapshot above. Everything below this point (including the
> PR #407/#408 behavior snapshot, PR #406 merge snapshot, live regression diagnosis /
> cleanup-paused snapshot, post-#405-merge snapshot, post-#388-closure snapshot,
> post-#386-closure snapshot, P018 public-cards snapshot, earlier 2026-07-02 cleanup, 2026-07-01,
> 2026-06-25, and earlier dated bullets) is preserved as historical context only.

- **Code baseline `main`:** `921d0df0dd0507ea816d57851d27f3d1b849762a` (merge of PR
  [#409](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/409) docs/status sync on top of
  behavior baseline `70dcd952871c993814437edf1dcf1f2280b47dc7`). Short SHA: `921d0df`.
- **Behavior baseline (unchanged by #409):** `70dcd95` — PR [#408](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/408)
  on PR [#407](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/407). PR #409 changed
  documentation and manifest pointers only.
- **Merged in #407 (behavior, preserved):** Ester-reviewed warning-precision fixes: P044 abstract
  continuation-line false positives reduced; P027 bold-heading requirement; P037 List of Tables
  Roman-number false-positive reduction; P011 margin overrun presentation without grouping
  breakage; P024/P040 List of Figures presentation fixes; P025 Digital Commons wrapper notice
  behavior (notice, not problem).
- **Merged in #408 (UI display only, preserved):** confidence sorting of grouped problem cards
  (`?sort=` query param); grouping keys and detector output unchanged.
- **Merged in #409 (docs only):** status documentation and `evaluation_data_manifest.json` pointers
  aligned to `70dcd95` / 2506 tracked pytest; open-PR cleanup remains paused; P084 out of scope.
- **Live server (verified 2026-07-02, post–#409 merge):** `GET /version` on
  `127.0.0.1:8000` / `localhost:8000` / `10.196.93.210:8000` reports
  `commit=70dcd952871c993814437edf1dcf1f2280b47dc7`, `branch=main`,
  `process_start_time=2026-07-02T18:03:41.571263+00:00`; `/healthz` OK. Process cwd:
  `/home/soroush/njit-thesis-auditor/main`. **Not** yet reporting merged docs tip `921d0df` (restart
  optional — #409 has no runtime code changes). Fresh built-in sample audit **not run** in this
  verification pass. See [live_deployment_checklist.md](live_deployment_checklist.md).
- **PR cleanup:** **still paused** — do not touch #311/#349/#362/#375/#376/#385 unless a separate
  human instruction says otherwise.
- **Full validation on `main` @ `921d0df` (2026-07-02, clean worktree):** `ruff check .` clean;
  `mypy src` clean; `python -m pytest` → **2486 passed**, 1 warning (clean worktree without local
  WIP). **Status snapshot validation** on merged tracked `main` @ `70dcd95`: **2506 pytest passed**,
  1 warning (per manifest).

### Next recommended work

1. Optionally restart live server so `/version.commit` matches `921d0df` (behavior already at
   `70dcd95`).
2. Resume PR cleanup only after the warning-legitimacy review concludes (or explicit human
   instruction).
3. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-02 (PR #407 and PR #408 merged on main)

> **Superseded** by the PR #409 merge snapshot above.

> **Superseded** by the PR #407/#408 merge snapshot above.

- **Code baseline `main`:** `811838c4a260977e290f24138b0c60665f676684` (squash-merge of PR
  [#406](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/406), which folded in #405's
  `7e17232a` Digital Commons wrapper fixes plus the single-page `highlighted-page.pdf` fix and a
  ruff import-order/unused-import cleanup in 9 test files). `fix/live-false-positive-and-highlight-regression`
  branch deleted after merge.
- **Live server:** restarted against `main` at `811838c4`; `/version` confirms `commit=811838c4...`,
  `branch=main` (no longer dependent on the unmerged #406 branch). `/healthz` OK.
- **Fresh post-merge live audit (Digital Commons sample, new job, not a cached URL):** 141 findings,
  matches local `main` exactly. Wrapper pages 1–3 detected (`P025 digital_commons_wrapper_pages_detected`);
  P020 = 2 (both on real manuscript pages, none on wrapper pages); P018 = 0; P026 = 0. Highlighted-page
  route re-verified: 1-page artifact with annotation when a bbox exists, 1-page artifact (no annotation)
  when it doesn't — never the full multi-page document.
- **PR cleanup:** **still paused** — do not touch #311/#349/#362/#375/#376/#385; warning-legitimacy
  review continues separately from this merge.
- **Protected regression tests:** 88 passed (P026, P018 row association, P015 split, P018 public cards,
  ester rule consistency), re-run before and after the merge.
- **Full validation on merged `main`:** `ruff check .` clean, `mypy src` clean, `pytest` 2454 passed
  (ignoring the two known untracked P084 / TOC-leader-consistency WIP files, which are not part of
  any merged branch).

### Next recommended work

1. Resume PR cleanup only after the warning-legitimacy review concludes.
2. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-02 (live regression diagnosis — cleanup paused)

> **Superseded** by the PR #406 merge snapshot above.

- **Code baseline `main`:** `7e17232a` (PR [#405](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/405)); docs tip `28a4797`.
- **Live server before fix:** `fbefbb6432364edec07566c6bec4e744a87be7bd` (PR #400 merge) — **10 commits behind** `main`; process started `2026-07-02T03:38:34Z`.
- **Live server after restart (2026-07-02):** `3fa862048445186d74b635e346a6ffabc660c1fa` on branch `fix/live-false-positive-and-highlight-regression` (emergency fix pending merge as [#406](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/406)); `http://10.196.93.210:8000/version`.
- **PR cleanup:** **paused** — do not touch #311/#349/#362/#375/#376/#385 until live regressions confirmed fixed on merged `main`.
- **Protected regression tests (2026-07-02):** 88 passed (P026, P018 row association, P015 split, P018 public cards, ester rule consistency).

### Live regression diagnosis (aggregate-only)

| Comparison | Total (4 built-in samples) | P026 | P018 | P020 | Notes |
|---|---:|---:|---:|---:|---|
| `3b4043c` (pre-#405 baseline) | 1,111 | 117 | 10 | 34 | Protected P018 LoT row tests pass |
| `fbefbb6` (stale live server) | 1,111 | 117 | 10 | 34 | Same detector output as `3b4043c` on built-in samples |
| `28a4797` / fix branch (`3fa8620`) | 1,109 | 117 | 11 | 31 | **No P026 reintroduction**; P020 −3 vs baseline; fresh `ester_sample_d` audit: P018 `missing_page_number` = 0 |

**False-positive user report:** primarily **stale live server** (`fbefbb6`) and/or **old audit job URLs**, not a detector regression on current `main`. Five-PDF eval (from earlier session) shows `main` at 1,161 total vs `3b4043c` at 1,166 (−5); #405 reduces P020 (−6) without reintroducing P026 (+298) that #388 would have caused.

**Highlight-page regression:** commit `9ca99c0` (single-page `highlighted-page.pdf` artifacts) was never merged to `main`. Links used `/pdf/highlighted` + `#page=` (full PDF). **#406** restores single-page artifacts; verified: endpoint returns 1-page PDF with highlight annotations.

### Open PRs

**6** independent PRs paused + **#406** emergency fix. Full triage: [open_pr_triage.md](open_pr_triage.md).

### Next recommended work

1. **Merge #406** → restart live at merged `main`; fresh audit + UI check for highlight links.
2. Resume PR cleanup only after live confirmation.
3. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-02 (post-#405 merge)

> **Superseded** by the live regression diagnosis snapshot above.

- **Baseline main for this status snapshot:** `7e17232a` (PR [#405](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/405) — Digital Commons wrapper false-positive reductions, clean #388 port).
- **Short SHA:** `7e17232`.
- **Status snapshot validation (tracked tests, 2026-07-02):** `ruff check .` clean; `mypy src` clean (107 source files); `python -m pytest --ignore=tests/test_p084_biosketch_birth_information.py --ignore=tests/test_pdf_toc_leader_consistency.py` → **2450 pytest passed**, 1 warning.
- **Merged (2026-07-02):** [#405](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/405) — ports useful #388 behavior (wrapper page filtering, manuscript/PDF page identity, P018/P020/P028 false-positive reductions) without Q-matrix tiers or obsolete atomic web refactor.
- **Closed as superseded (2026-07-02):** [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) → replaced by #405.
- **Remote branch deleted:** `fix/ester-q-matrix-coverage` (#388 head).
- **Open PRs:** **11** as of 2026-07-02. Full triage: [open_pr_triage.md](open_pr_triage.md).

### Open PR situation (summary)

| Category | PRs | Maintainer note |
|---|---|---|
| **Ready for review** | [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375), [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | Rebase on `7e17232` before merge |
| **Stacked presentation** | [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389) → … → [#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) | Compare with landed #400/#402/#405; #390 wrapper notice may overlap |
| **Conflicting but valuable** | [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385), [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | Rebase after `7e17232` |
| **Likely superseded / confirm** | [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Close only after explicit confirmation |

### Next recommended work

1. Presentation stack **#389–#393** — merge as a unit or cherry-pick; watch #390 vs #405 wrapper notice overlap.
2. Rebase UX/docs PRs **#385**, **#362**, **#349**.
3. **P084 remains out of scope** unless explicitly requested.

---

## Historical — 2026-07-02 (post-#388 closure, #405 pending merge)

> **Superseded** by the post-#405-merge snapshot above.

- **Baseline main:** `3b4043c` (PR #404); #405 open for merge.
- **Open PRs at that time:** 11; #388 closed.

---

## Historical — 2026-07-02 (post-#386 closure, pre-#388)

> **Superseded** by the post-#388-closure snapshot above.

- **Baseline main:** `31c2aa6` (PR #403).
- **Open PRs at that time:** 12; #388 still open for review.

---

## Historical — 2026-07-02 (P018 public cards through PR #402)

> **Superseded** by the post-#386-closure snapshot above.

- **Baseline main:** `fd29574` (PR #402).
- **Open PRs at that time:** 13; #386 still under LaTeX-advisory review.

---

## Historical — 2026-07-02 early (PR/branch cleanup through PR #401)

> **Superseded** by the post-#402 snapshot above.

- **Baseline main:** `4ea7f8692ddf9f2136e265ff3370b7150162fb74` (PR #401).
- **Open PRs at that time:** 14; #396 still needed clean replacement (now done via #402).

---

## Historical — 2026-07-02 (PR/branch cleanup through PR #400)

> **Superseded** by the 2026-07-02 snapshot above.

- **Audited baseline main:** `cdc99ea7216d95281042c358a8b27934e69e62b8` (PR [#387](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/387)).
- **Open PRs at that time:** 16, including stacked **#394 → #395 → #396** (all superseded or replaced by 2026-07-02 cleanup except #396).

---

## Historical — 2026-06-25 (warning-clarity completion through PR #372)

> **Superseded** by the 2026-07-01 snapshot above. Preserved for the #367–#372 warning-clarity
> milestone record only.

- **Baseline main:** `2a7f216d2d01cbc0268661d30f4a385287506805` (PR #372 — Suppress timestamp-like TOC false positives).
- **Baseline main for this status snapshot:** `2a7f216` (short SHA for manifest alignment).
- **Status snapshot validation:** `ruff check .` clean; `mypy src` clean (100 source files); `python -m pytest` → **2147 pytest passed**, 1 warning (pre-existing duplicate-zip-member `UserWarning` in upload tests).
- **Live website:** `http://10.196.93.210:8000/` serves current `main` (`2a7f216`) via tmux session `web`, uvicorn on port 8000, repo checkout `/home/soroush/njit-thesis-auditor`. Confirm with `GET /version`.
- **Sample audit regression:** built-in `ester_sample_d` (`POST /audits/sample`) — timestamp-like TOC false positives (e.g. `2026-04-30 12:45:08`) **gone** after #372; #371 live-review card fixes **still pass** on fresh audits.
- **Rule inventory:** P001–P083 implemented (82 inventory entries; P075 documented non-inventory project task); **P084** not started (per standing instruction).
- **CI:** GitHub Actions may still fail on billing/spending limits; local validation is green at `2a7f216`.

### Recently merged warning-clarity work (#367–#372)

| PR | Summary |
|---|---|
| [#367](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/367) | P012 annotation page rollup for dense warnings |
| [#368](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/368) | P012 document-level summary for high-volume annotation warnings |
| [#369](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/369) | P026 font warning rollups |
| [#370](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/370) | Final warning clarity sweep (P011/P024/P026/P036/P044/P046 grouped locations) |
| [#371](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/371) | P018/P020/P036 live-review fixes: shorter main cards, P020 dedup, P036 leader-dot cleanup, P018 highlights, CHAPTER structural-label suppression |
| [#372](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/372) | Skip export timestamp metadata lines in TOC/list entry parsing (e.g. `YYYY-MM-DD HH:MM:SS`) |

### Student-facing warning behavior now live

- P012: page rollup + document summary for high-volume annotation warnings.
- P026: font warning rollups with clearer student labels.
- P011 / P024 / P026 / P036 / P044 / P046: grouped warning location clarity (#370).
- P018 / P020 / P036: shorter main cards; no repeated suggested-fix text in P036 main card (#371).
- P020: duplicate suppression for same-heading/same-word cards (#371).
- P036: leader-dot stripping in snippets; gap metrics only in detailed explanations (#371).
- P018: affected-entry highlights when bbox exists; CHAPTER/PAGE/TITLE structural labels suppressed (#371).
- P018: timestamp/export metadata lines not treated as TOC entries (#372).

### Open PR triage

See `docs/status/open_pr_triage.md`. **Do not** close/merge/rebase #311, #349, or #362 during cleanup unless explicitly requested.

### Maintainer docs added/updated in this era

- Live deployment: `docs/status/live_deployment_checklist.md`
- Student-preview architecture: `docs/architecture/student_warning_preview_helpers.md`
- Open PR triage: `docs/status/open_pr_triage.md`

### Next recommended work (post-#372)

1. Resolve GitHub Actions billing if CI should gate merges again.
2. Review open PRs #362, #349, #311 per `docs/status/open_pr_triage.md`.
3. Optional Query 3: stale branch/worktree inventory and safe log rotation (not user audit history).
4. P084 remains out of scope unless explicitly requested.

---

## Historical — 2026-06-23 (repo audit, doc cleanup, and PR triage)

> **Superseded** by the 2026-07-01 snapshot above.

- **Baseline main for this snapshot:** `14a2df1` (PR #357 — Clarify P018 and P046 list entry locations), the latest merged PR as of this audit.
- **Rule inventory:** **P001–P083 implemented** (82 `project_added_rules.json` entries, all `implementation_status: implemented`; `P075` remains a documented non-inventory project task, not a rule entry). **P084 does not exist yet** — no detector module, no inventory entry, no rule ID reserved beyond the existing "next ID is P084" guard note. Per explicit standing instruction, do not start P084 implementation work without an explicit request.
- **Validation as of this snapshot:** `ruff check .` clean; `mypy src` clean (93 source files); `python -m pytest` → **1972 passed, 1 warning** (one pre-existing `UserWarning` from a duplicate-zip-member test fixture, not a regression).
- **Test runner fix:** added `[tool.pytest.ini_options]` `pythonpath = ["src"]` to `pyproject.toml` so `pytest` resolves `njit_auditor` from this checkout's `src/` regardless of which worktree last ran `pip install -e .`. The shared `modal-venv` editable install previously pinned import resolution to whichever worktree last installed, which could produce false-positive failures when testing from a different worktree without manually exporting `PYTHONPATH`.
- **Deployment health:** `GET /healthz` and `GET /version` are present and working in `src/njit_auditor/web_app.py` (added 2026-06-19, unchanged since). Any doc claiming these endpoints are missing is stale.
- **CI status:** GitHub Actions is failing on every recent push to `main`, including merged PRs #353–#357. Root cause confirmed via `gh run view --log`: **"recent account payments have failed or your spending limit needs to be increased"** — the test jobs never start. This is a billing/account issue, not a code regression; local `ruff`/`mypy`/`pytest` all pass clean at the same commits.
- **Known limitation — LFS pointer drift:** `.gitattributes` declares LFS filters for `*.pdf`/`*.docx`/`*.xlsx`/`*.pptx`/`*.zip`/`*.rar`, but at least 17 files under private evaluation data are committed as full git blobs rather than LFS pointers (surfaced as warnings when creating a diagnostic `git worktree`). The repository is private (`gh repo view` → `isPrivate: true`), which limits exposure, but the LFS migration is incomplete. Not fixed in this pass — repairing it would require rewriting git history for the affected blobs, which is out of scope without explicit instruction.
- **Open PR triage (2026-06-23):** see the table below. No PRs were merged, closed, or rebased as part of this audit — this is a documentation-only record.

| PR | Title | Verdict | Why |
|---|---|---|---|
| [#351](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/351) | Reduce duplicate page-number warning cards | **Mergeable as-is** | Clean merge via `git merge-tree`; verified by actually merging into a disposable worktree and re-running full validation (1977 passed, 1 warning; ruff/mypy clean). Pure presentation-layer change, no rule ID/threshold change. CI red is the billing issue, not a real failure. |
| [#352](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/352) | Add warning actionability audit | **Worth refreshing before merge** | Docs-only (single file), clean merge, no code touched. But its baseline (`fd508cd`) predates 5 merged PRs (#353–#357) that already fix a meaningful fraction of its own findings — e.g. `resolve_suggested_fix_for_display()`/`finalize_student_facing_comment_and_fix()` (PR #353) directly address its "missing Suggested fix line" findings for P016/P017/P018/P020/P024/P030/P033/P035/P036/P040/P046/P051/P053; PR #354 adds the high-volume pattern-note clarification it recommended; PR #356/#357 fix the exact P024/P018/P046 location-precision gaps it flagged; this audit branch's own commit adds a `_high_volume_pattern_note()` sentence explaining the P020 confidence-band card split (see below). Merging it unmodified would present a stale "current state" table. Recommend re-validating its Section 4 rule-by-rule table and Section 13 task list against this branch's head before merging, not closing it outright — the remaining surviving findings (P036/P026/P012 high-volume row repetition without per-row differentiation, `Review needed:` prefix ambiguity) still look open. |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | Preserve autonomous policy and Ester feedback audit | **Effectively absorbed** | Docs-only (`AGENTS.md` guardrails + dated audit doc), clean merge, byte-identical to content this audit branch already carries forward (see commit `dbf43f9` on `chore/repo-audit-status-and-pr-triage-20260623`). Once this branch merges, PR #349 becomes a no-op diff and can be closed as redundant; alternatively merge #349 directly instead — just avoid doing both, to avoid confusing duplicate history. |
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Add sub-page location labels for PDF findings | **Superseded — recommend closing** | Confirmed via `git merge-tree --write-tree`: real conflicts in `report_view.py`, `pdf_captions.py`, and `job.html` against current `main`. Independently corroborated by the repo's own `docs/status/pr_and_stash_triage_20260619.md`, written before this audit, which reached the same conclusion: the location-label idea was reimplemented from scratch as the geometry-driven `sub_page_location_label()`/`enriched_pdf_location_label()` system (no raw text-snippet extraction, unlike PR #311's `_build_pdf_sublocation()`) and has since grown into the full location-clarity chain through PR #357. Nothing in PR #311 is worth salvaging. |

- **Next recommended work**, in rough priority order:
  1. Resolve the GitHub Actions billing/spending-limit issue so CI goes green again (account-level action, not a code change).
  2. Decide on PR #352: regenerate/annotate it against `14a2df1` (cheap — its method is a script-driven sample audit) before merging, so the merged doc doesn't read as current when several items are already fixed.
  3. Address PR #352's remaining open items: P036/P026/P012 high-volume occurrence-row repetition without per-row differentiation, and the `Review needed:` prefix's overlap with the confidence badge system. (Re-verified 2026-06-23 via `TestClient` on all four built-in samples: the Markdown export's generic fallback-caveat residue item is **already fixed** — `please verify against NJIT guidelines manually` now appears 0 times in any sample's Markdown export; only one global "Automated finding" note remains per report, as intended. The P020 confidence-band card split item is also now **fixed** as a UI-clarity item: confirmed via direct testing on `ester_sample_d` that P020 genuinely does render as multiple separate cards on one report — e.g. 15 + 8 + 4 occurrences — because `possible_title_capitalization_issue` findings group by capitalization reason text, which correlates 1:1 with confidence level (`first_word_requires_capital`/`word_after_separator_requires_capital` → high, `major_word_requires_capital` → medium, in `pdf_title_capitalization.py`). This is intentional grouping behavior, not a bug, so it was left unchanged; `_high_volume_pattern_note()`'s existing P020 branch in `report_outputs.py` now adds one explanatory sentence — *"This card only groups findings that share the same capitalization reason and confidence level -- a separate P020 card covering a different reason ... is not a duplicate."* — so the split no longer reads as an unexplained duplicate-warning bug, in both the HTML grouped-card view and the Markdown "Why this repeats" line. This was PR #352's audit Section 14 "Safe Quick Win" item 3, implemented as presentation-only with no grouping/threshold/rule-ID change.)
  4. Decide the fate of PR #349 (merge directly vs. let this audit branch supersede it) and PR #311 (close, per two independent triage passes reaching the same conclusion).
  5. Plan the LFS pointer migration for private evaluation data as a separate, explicitly-scoped history-rewrite task — not bundled into routine feature work.

---

- **Date:** 2026-06-19 (repository stabilization and deployment-health refresh; prior snapshot from 2026-06-16 preserved below) — **superseded by the 2026-06-23 snapshot above; preserved for history only.**
- **Baseline main for this status snapshot:** `b4cb8cd` (PR #324 — Make page-number, margin, and font findings actionable); prior baseline: `67c31b9` (PR #296 — Fix post-P083 live status doc references)
- **Finding actionability stack (PR #320–#324, plus later page-action refinement):** finding actionability/drill-down (PR #320), strict PDF highlight-eligibility policy (PR #321) — fake highlights remain forbidden and `pdf_highlight.py` still decides highlight eligibility — Ester YES/NO matrix remediation alignment (PR #322), P023/P016 issue-type mismatch fix in the finding presentation layer (PR #323), page-number/margin/font findings made actionable with real visible highlights (PR #324), and later presentation-layer refinement allowing `Open original PDF page` when a finding has a known page but no valid highlight. Current action kinds are: real `highlight`, page-known `original_page`, and document-level `explanation`.
- **Deployment health endpoints:** `GET /healthz` (liveness probe, minimal `{ok, app, status}` body, no job required) and `GET /version` (app name, git commit/branch, process start time, Python version, environment name) added as part of the repository stabilization work; both verified to leak no runtime paths, filenames, or environment-variable names.
- **Web stability status:** PR #317, #318, and the PR #320–#324 actionability stack are merged. The public web UI is PDF-only, `/audits/sample` GET is guarded, mobile and desktop render the same substantive result content/actions for the same job, PDF links are served inline where possible, and the `/rules` page uses a collapsible `<details>/<summary>` for "What it checks" while "How to correct it" remains visible outside the toggle.
- **Open PR / stash triage:** see `docs/status/pr_and_stash_triage_20260619.md` for the current status of PR #311, PR #305, and the pre-existing stash (all left untouched by the stabilization work).
- **P073 status:** P019 page-numbering triage rollup **fully implemented** (v1 docs-only triage rollup + v2 code rollup complete); triage metadata on P019 findings; `build_p019_page_numbering_triage_summary()` in JSON/Markdown reports; 17 new tests; see `docs/evaluation/p073_p019_page_numbering_triage_rollup.md`, `docs/evaluation/p073_v2_p019_triage_code_rollup_validation.md`, and `docs/planning/p073_p019_page_numbering_triage_rollup_scope_and_design.md`
- **Evaluation gap-fill status:** P036–P063 five-PDF current-dataset evaluation **complete** (PR #266); 27 rules; 88 total findings; see `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`
- **Data acquisition status:** Sebastian Fine EF archive recovery **BLOCKED** (Retry 2: 2026-06-09, baseline `42e10fb`) — `data/evaluation/private/` absent; no new archives found in workspace or home directory; comparison set remains 2 extractable files (143 EF annotations); see `docs/evaluation/sebastian_fine_ef_archive_recovery.md`
- **Expanded Ester dataset:** imported through **PR #285** (2026-06-09); expanded local evaluation inventory established before the DOCX extraction/evaluation follow-up chain; no detector behavior change
- **P080 status:** completed through **PR #286**; reporting/infrastructure-only DOCX comment and tracked-change extraction via `njit-audit docx-comments extract`; no PDF/TeX detector logic change; raw findings unchanged; canonical aggregate unchanged at 1,543
- **Post-P080 DOCX+PDF evaluation:** completed through **PR #287**; P080 extractor applied to both Ester DOCX files (52 comments total: 22 Sebastian Fine 3rd, 30 Aguado Alvaro 3rd; 0 tracked changes in either); combined PDF+DOCX picture: 614 EF comments across 14 files; strongest signal: P013/P026 over-warning consistent across Yin Haotian 4-version chain; new gap: landscape page number orientation (Aguado Alvaro: 3 comments, no PDF-side coverage); see `docs/evaluation/post_p080_docx_pdf_overlap_evaluation.md`
- **P081 status:** completed through **PR #288**; reporting-only refinement in `src/njit_auditor/report_outputs.py`; extends `p013_triage` and `p026_font_triage` with dominant-pattern labels, calibration buckets, and compact page-range summaries for routine-vs-outlier manual triage; detector logic unchanged; raw finding counts unchanged; canonical aggregate unchanged at 1,543
- **P083 status:** implemented (2026-06-10) as a pure evaluation_task — EF-comment coverage taxonomy and in-scope gap register; classifies 52 EF reviewer comments (from 2 DOCX dissertation drafts via P080) against SIM/SIP/SMI/SBL/SEM/PRF/AMB taxonomy; output: `data/processed/ef_comment_coverage.json` (52 rows; 3 SIM, 34 SIP, 10 SMI, 3 SBL, 2 SEM; covered_or_partial_rate 0.74); 3 new schema tests in `tests/test_p083_coverage_schema.py`; no source code changes; no detector changes; canonical aggregate unchanged at 1,543; see `docs/planning/p083_ef_comment_coverage_taxonomy_scope_and_design.md` and `docs/evaluation/ef_comment_coverage_analysis.md`
- **P082 status:** implemented (2026-06-09) as experimental opt-in landscape page-number orientation advisory in `src/njit_auditor/rules/pdf_landscape_page_number_orientation.py`; disabled by default via `AuditOptions` / `--enable-experimental P082`; warning/manual-review only; observational over existing P013 page-number candidates; uses PyMuPDF `line_dir`, `wmode`, and `page_rotation` metadata; 18 synthetic tests; default-mode canonical aggregate unchanged at 1,543; see `docs/planning/p082_landscape_page_number_orientation_scope_and_design.md` and `docs/evaluation/p082_landscape_page_number_orientation_synthetic_validation.md`
- **Recommendation:** P083 did not justify starting P084. No new detector rule is currently being started; stabilization, validation, and operational hardening take priority.
- **P079 status:** P044 Abstract paragraph indentation triage rollup **implemented** (2026-06-09, branch `rules/p079-p044-abstract-indentation-triage`); grouped JSON key `p044_abstract_indentation_triage` and Markdown section `P044 Abstract Indentation Triage` added in `src/njit_auditor/report_outputs.py`; aggregates P044 findings by issue type (abstract_first_paragraph_indented / abstract_subsequent_paragraph_not_indented), source Q-rule (Q002 / Q003), triage tier, paragraph index, and page ranges; reporting-only; no P044 detection behavior change; no standalone issue types; canonical aggregate unchanged at 1,543
- **P078 status:** PDF Abstract forbidden-term and pronoun check **implemented** (2026-06-09, branch `rules/p078-q004-q005-pdf-abstract-keywords`); emits `abstract_pdf_forbidden_term` (Q004) for paper/papers/article/articles and `abstract_pdf_first_person_pronoun` (Q005) for i/me/my/mine/we/us/our/ours on the Abstract page body text only; privacy-safe token-only findings; 14 synthetic tests in `tests/test_p078_pdf_abstract_keywords.py`; 0 findings on current five-PDF dataset; canonical aggregate unchanged at 1,543
- **P077 status:** P038 front-matter heading triage rollup **fully implemented** (PR #280, 2026-06-09); grouped JSON key `p038_frontmatter_heading_triage` and Markdown section `P038 Front-Matter Heading Triage` added in `src/njit_auditor/report_outputs.py`; reporting-only; no P038 detection behavior change; no standalone issue types; canonical aggregate unchanged at 1,543
- **P076 status:** P036 TOC/LoT/LoF inter-entry spacing triage rollup **fully implemented and merged** (PR #278, 2026-06-09); grouped JSON key `p036_toc_list_spacing_triage` and Markdown section `P036 TOC/List Spacing Triage` added in `src/njit_auditor/report_outputs.py`; reporting-only; no P036 detection behavior change; no standalone issue types; canonical aggregate unchanged at 1,543; **current-dataset evaluation complete:** see `docs/evaluation/p076_p036_toc_list_spacing_triage_current_dataset_evaluation.md`
- **P074 status:** title-page graduation month check **implemented** (PR #272, 2026-06-09); PDF heuristic for Q006; emits `title_page_graduation_month_invalid` when detected month is not August, December, or May; 0 findings on current five-PDF dataset; P073 inventory drift also repaired (P073 entry added to `project_added_rules.json`); see `src/njit_auditor/rules/pdf_frontmatter_structure.py`
- **P075 status:** inventory consistency guard tests **implemented** (PR #274, 2026-06-09); test-only hygiene: P075 remains a documented non-inventory project task and is not added to `project_added_rules.json`; the inventory guard allows only documented skipped P-IDs, currently `P075`; no detection behavior change; canonical aggregate unchanged at 1,543
- **Status snapshot validation (2026-06-16):** repository progress **P001–P083**; project-added rule inventory **P001–P074 plus P076–P083** (82 implemented entries spanning `P001–P083`, with `P075` documented as the non-inventory skip); **1138 pytest passed** when this snapshot was generated; canonical five-PDF aggregate **1,543** (unchanged). A newer full validation pass after PR #318 is recorded separately in `docs/planning/repo_stabilization_after_p318.md`.
- **Status snapshot validation (2026-06-19, repository stabilization):** ruff and mypy clean; **1554 pytest passed, 1 warning** (includes 9 new tests for `/healthz` and `/version`); no detector, rule-ID, or threshold change — endpoint and documentation work only. P084 has not been started.
- **Historical P082 closeout snapshot:** `docs/status/project_closeout.md`
- **Full repository audit (P079 era):** `docs/status/full_repository_audit_after_p079.md`
- **Full repository audit (P071 era):** `docs/status/full_repository_audit_after_p071.md`

## Historical Milestone Archive

Use the summary bullets above and `data/processed/evaluation_data_manifest.json` for live/current
values. The archived milestone notes below intentionally preserve older point-in-time snapshots,
including superseded "not run" states from before later gap-fill evaluations.
- **P072 post-implementation evaluation:** **complete** — full five-PDF current-dataset eval (commit `1476a51`): structural fallback found 0 candidates on all 3 non-detecting PDFs (Cibaku, Yin H 2nd flattened, Yin Haotian 2nd) — all eligible pages return noise-only text, confirming image-embedded approval pages; P068 reach 2/5 unchanged; aggregate 1,543 unchanged; **EF-overlap refresh after P072 complete:** `committee_approval_page` gap unchanged (5 EF, 0 tool); total tool findings on comparison PDFs 671 (unchanged); see `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md` and `docs/evaluation/ef_overlap_after_p072_evaluation.md`
- **P072:** **implemented** — approval-page heading-gate recall refinement (infrastructure companion to P068); structural role-label fallback when heading text absent; no new issue types; 14 synthetic tests; see `docs/planning/p072_approval_page_heading_gate_recall_refinement_scope_and_design.md`, `docs/evaluation/p072_approval_page_heading_gate_recall_synthetic_validation.md`, and `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md`
- **P071:** **implemented** — references section localization recall refinement (`pdf_references_citations_structural.py`); infrastructure-only; 12 synthetic tests; five-PDF eval: P064 reach 2/5→5/5; aggregate unchanged at 1,543; **EF overlap refresh complete:** P064 now reaches 2/2 comparison PDFs but `references_citations` gap unchanged (9 EF, 0 tool); see `docs/evaluation/p071_references_section_localization_recall_synthetic_validation.md`, `docs/evaluation/p071_references_section_localization_recall_current_dataset_evaluation.md`, and `docs/evaluation/ef_overlap_after_p071_evaluation.md`
- **P070:** **implemented** — TOC/LoT/LoF entry parser recall refinement (`pdf_toc_alignment.py`); infrastructure-only; 12 synthetic tests; **current-dataset evaluation complete** — all 5 PDFs accessible; parser entries 185→167 (pre-P070 comparator); post-P070 aggregate 1,543; see `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_synthetic_validation.md`, `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md`, and `docs/evaluation/current_auditor_after_p070_evaluation.md`
- **P069:** **implemented** — front-matter heading gate recall refinement (shared infrastructure); see `src/njit_auditor/rules/pdf_frontmatter_heading_gate.py`, `docs/evaluation/p069_frontmatter_heading_gate_recall_synthetic_validation.md`, and `docs/evaluation/p069_frontmatter_heading_gate_recall_current_dataset_evaluation.md`; no standalone issue types; ACKNOWLEDGEMENTS variant recall +4 on five-PDF set; P065–P068 finding totals unchanged on current dataset
- **P068:** **implemented** — `src/njit_auditor/rules/pdf_approval_page_committee_blocks.py`; Approval Page committee/signature-block structural check; Q013 structural extension; issue types: `approval_page_advisor_role_label_missing`, `approval_page_signature_blocks_sparse`; detects unique `APPROVAL PAGE`, counts curated role-label phrases and date/signature/underscore-blank indicators; skips sparse/noisy/image-only/ambiguous pages; 13 synthetic tests in `tests/test_p068_approval_page_committee_blocks.py`; see `docs/planning/p068_approval_page_committee_block_structural_scope_and_design.md` and `docs/evaluation/p068_approval_page_committee_blocks_synthetic_validation.md`; **current-dataset evaluation:** complete — 3 P068 findings on 2/5 files (3/5 skipped at `APPROVAL PAGE` detection gate); see `docs/evaluation/p068_current_dataset_evaluation.md`
- **P067:** **implemented** — `src/njit_auditor/rules/pdf_biosketch_publication_ordering.py`; Bio Sketch publication/presentation reverse-chronology check for Q027; issue type: `biosketch_publication_order_suspicious`; detects a unique `BIOGRAPHICAL SKETCH` page, requires a clear Publications/Presentations subsection boundary, groups citation-like entries, extracts one representative year per comparable entry, and warns on descending-order inversions with >1-year tolerance; skips ambiguous multi-year entries, DOI/URL-heavy entries, image-only pages, missing boundaries, and sparse/nonstandard layouts; 13 synthetic tests in `tests/test_p067_biosketch_publication_ordering.py`; see `docs/planning/p067_biosketch_publication_date_ordering_scope_and_design.md` and `docs/evaluation/p067_biosketch_publication_ordering_synthetic_validation.md`; **current-dataset evaluation:** complete — 0 P067 findings; 3/5 files skipped at heading detection; 2/5 reached Bio Sketch detection but 0/5 reached a qualifying Publications boundary; **aggregate snapshot:** complete — post-P067 full five-PDF rerun remains 1,587 findings with 0 P067 findings; see `docs/evaluation/p067_current_dataset_evaluation.md` and `docs/evaluation/current_auditor_after_p067_evaluation.md`
- **P066:** **implemented** (PR #236) — `src/njit_auditor/rules/pdf_biosketch_degree_ordering.py`; bio-sketch degree ordering check; Q025 (degrees most-recent-first); issue type: `biosketch_degree_order_suspicious`; detects year tokens in education-section candidate lines and checks non-increasing order; gates: ≥3 year-bearing lines; year inversion > 2-year gap; skip if image-only, ambiguous heading, or candidates all in Publications zone; Q023/Q024 deferred (content-reading/NLP required); "NJIT first" sub-requirement of Q025 deferred; 12 synthetic tests in `tests/test_p066_biosketch_degree_ordering.py`; see `docs/planning/p066_biosketch_structural_ordering_scope_and_design.md`, `docs/evaluation/p066_biosketch_degree_ordering_synthetic_validation.md`, and `docs/evaluation/p066_current_dataset_evaluation.md`; **current-dataset evaluation:** complete — 0 P066 findings; 3/5 files skipped (heading not detected); 2/5 detected and passed (years non-increasing); zero findings do not prove compliance
- **P065:** **implemented** (PR #232) — `src/njit_auditor/rules/pdf_dedication_centering_italic.py`; dedication page centering/italic formatting check; Q033 (centering) + Q034 (italic); issue types: `dedication_text_not_centered`, `dedication_text_not_italic`; gates: ≥2 text lines for centering; ≥3 spans for italic; all-None font skips italic; skip if no unique DEDICATION heading in first 15 pages; 15 synthetic tests in `tests/test_p065_dedication_centering_italic.py`; see `docs/planning/p065_dedication_centering_italic_scope_and_design.md` and `docs/evaluation/p065_dedication_centering_italic_synthetic_validation.md`; **current-dataset evaluation:** complete — see `docs/evaluation/p065_current_dataset_evaluation.md`; all 5 evaluation PDFs accessible; 0 P065 findings; all 5 skipped by detection gate — no machine-readable standalone DEDICATION heading found in first 15 pages of any file; Cibaku/Yin PDFs: no DEDICATION text in first 15 pages; Sebastian Fine: "DEDICATION" appears only in body prose (not a heading), char_length=82; P041 also finds no dedication page on these files — shared detection limitation; zero findings do not indicate compliance
- **P064:** **implemented** (PR #228) — `src/njit_auditor/rules/pdf_references_citations_structural.py`; references/citations structural check; emits `references_section_heading_not_detected` for long documents (≥5 body pages) with no REFERENCES, BIBLIOGRAPHY, WORKS CITED, or LITERATURE CITED heading; emits `references_entry_indentation_inconsistent` when multi-line entries show mixed hanging-indent patterns; emits `references_entry_spacing_inconsistent` when inter-entry gaps are highly irregular; gates: body region detection required; ≥5 entry candidates for B/C; ≥3 multi-line entries for B; x-variance < 50 pt; no multi-column layout; 21 synthetic tests in `tests/test_p064_references_citations_structural.py`; guideline basis: Self-Assessment Sheet p.4 ("consistently formatted"), Formatting Guidelines para 138 (references heading), Front Matter Lorem Ipsum p.9 (REFERENCES in TOC), Q028/Q029 analogy; privacy-safe: no entry text, author names, DOIs, URLs in findings; does NOT enforce citation style (APA/IEEE/etc.); **current-dataset evaluation:** complete — see `docs/evaluation/p064_current_dataset_evaluation.md`; all 5 evaluation PDFs accessible (Sebastian Fine via ZIP extraction); 0 P064 findings total; 3 of 5 files skipped by conservative gates (Cibaku: high x-variance from EF annotation artifacts; Yin H 2nd flat + Yin Haotian 2nd: body-start detection fails due to collapsed inter-word spacing in text layer); 2 of 5 files reached entry checks and passed (Yin H 4th: 52 entries / 5 section pages; Sebastian Fine: 24 entries / 3 section pages); zero findings do not prove compliance on skipped files
- **EF overlap after P063:** `docs/evaluation/ef_overlap_after_p063_evaluation.md` — refreshed EF comment-vs-tool category comparison for P001–P063; samples: Cibaku (78 EF comments, 325 tool findings) and Yin Haotian (65 EF comments, 346 tool findings); key findings: EF-only pages = 0 on both; references_citations (9 EF comments) and committee_approval_page (5 EF comments) remain at 0 tool coverage; heading_title improved (+7 findings from P038); list_of_tables_figures_toc still 0 on comparison PDFs despite 23 new rules; P064 recommended: references/citations structural check (scope first)
- **P064 scope doc:** `docs/planning/p064_references_citations_structural_check_scope_and_design.md` — implemented (PR #228); baseline commit `8cd9abd`; v1 checks: `references_section_heading_not_detected`, `references_entry_indentation_inconsistent`, `references_entry_spacing_inconsistent`; guideline basis: Self-Assessment Sheet p.4, Formatting Guidelines para 138 and 69, Front Matter Lorem Ipsum p.9, Q028/Q029 analogy
- **Evaluation readiness doc:** `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md` — full data inventory table, raw/commented pair table, extractability table, overlap-readiness table, recommended evaluation cadence, and next actions (added PR #221)
- **Web UI demo guide:** `docs/web_ui_demo_guide.md` — end-to-end demo guide using committed synthetic fixtures; covers install, run commands, environment variables, fixture table, step-by-step upload flow, privacy invariant checks, expected UI elements, and known caveats; `scripts/web_demo_smoke.sh` added as a convenience smoke check (prints fixture paths, runs `pytest tests/test_web_demo_fixtures.py -q`; does not start a server)
- **Synthetic web demo fixtures:** Implemented (PR #218) — `tests/fixtures/web_demo/` contains committed safe fixtures. The public web UI currently uses the PDF fixtures (`clean_minimal.pdf`, `issues_pdf.pdf`); the TeX/ZIP fixtures remain for CLI/internal source-audit coverage and historical tests only. All content is synthetic placeholder text only; see `docs/planning/synthetic_web_demo_fixtures.md`
- **P063:** **implemented** (PR #222) — `src/njit_auditor/rules/pdf_appendix_body_headings.py`; body-page appendix heading label check (Q058/Q059 body-page extension; companion to P042 TOC-side); emits `single_appendix_uses_letter_label` when a single appendix body heading uses a letter suffix (APPENDIX A instead of APPENDIX); emits `multiple_appendix_missing_letter` when multiple appendices lack a letter identifier; emits `appendix_letter_sequence_gap` and `appendix_letter_sequence_repeat` for non-consecutive or repeated letter identifiers; gate: body region must be detected (CHAPTER or APPENDIX body heading required) before scanning; skips documents with no body start detected; triage_tier: medium; 13 synthetic tests in `tests/test_p063_appendix_body_headings.py`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible; guideline basis: Self-Assessment Sheet p.4 ("If there is one appendix it is called APPENDIX; if there are multiple appendices, they are named APPENDIX A, B, C + the appendix title") and Q058/Q059
- **P062:** **implemented** (PR #220) — `src/njit_auditor/rules/pdf_toc_cross_page_entry_ordering.py`; TOC cross-page section-number ordering check (Q056/Q057 extension; cross-page companion to P060); emits `toc_cross_page_entry_numbers_not_nondecreasing` when consecutive TABLE OF CONTENTS pages have a combined section-number sequence that is not non-decreasing; gates: ≥2 consecutive TOC pages, ≥3 combined comparable entries, ≥2 inversions; word-prefix entries (CHAPTER, APPENDIX, ABSTRACT) skipped; non-consecutive pages not combined; triage_tier: medium; 12 synthetic tests in `tests/test_p062_toc_cross_page_entry_ordering.py`; see `docs/planning/p062_scope_and_design.md`; **formal current-dataset evaluation (2026-06-07, commit 36373c9): 0 P062 findings on five-PDF set — no qualifying cross-page TOC numeric sequence detected on this dataset; does not prove compliance — see `docs/evaluation/current_auditor_after_p062_evaluation.md`**
- **Status/metadata cleanup:** complete through PR #215; P061 implemented in PR #202; formal P061 evaluation in `docs/evaluation/p061_current_dataset_evaluation.md`
- **P059:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_entry_number_ordering.py` (new module); LoT/LoF entry-number ordering check (Q063/Q072 refinement); emits `lot_entry_numbers_not_nondecreasing` / `lof_entry_numbers_not_nondecreasing` when entry numbers (numeric token following "Table"/"Figure" label) are not non-decreasing; gates: ≥3 entries with parseable entry numbers, ≥2 inversions; mixed sequential+chapter-based pages skipped; appendix/letter-prefixed entries skipped; TOC excluded; triage_tier: medium; 12 synthetic tests added; see `docs/planning/p059_scope_and_design.md` and `docs/evaluation/p059_lot_lof_entry_number_ordering_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P060:** **implemented** — `src/njit_auditor/rules/pdf_toc_entry_number_ordering.py` (new module); TOC section-number ordering check (Q056/Q057 implied); emits `toc_entry_numbers_not_nondecreasing` when parseable numeric section entries in TABLE OF CONTENTS are not non-decreasing; gates: ≥3 entries with parseable section numbers, ≥2 inversions; word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) skipped; LoT/LoF excluded; triage_tier: medium; 12 synthetic tests added; see `docs/planning/p060_scope_and_design.md` and `docs/evaluation/p060_toc_entry_number_ordering_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P058:** **implemented** — `src/njit_auditor/rules/pdf_toc_page_number_ordering.py` (new module); TOC page-number ordering check (Q057 refinement); emits `toc_page_numbers_not_nondecreasing` when TABLE OF CONTENTS entries have page numbers that are not non-decreasing; gates: ≥3 entries with integer page numbers, ≥2 inversions; non-integer (roman numeral) tokens skipped; LoT/LoF excluded; triage_tier: medium; 10 synthetic tests added; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P057:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_page_number_ordering.py` (new module); LoT/LoF page-number ordering check (Q069/Q079 refinement); emits `lot_page_numbers_not_nondecreasing` / `lof_page_numbers_not_nondecreasing` when listed page numbers are not non-decreasing; gates: ≥3 entries with integer page numbers, ≥2 inversions; non-integer (roman numeral) tokens skipped; TOC excluded; triage_tier: medium; 12 synthetic tests added; see `docs/planning/p057_scope_and_design.md` and `docs/evaluation/p057_lot_lof_page_number_ordering_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P056:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_number_format.py` (new module); LoT/LoF entry numbering format consistency check (Q063/Q072 extension); emits `lot_mixed_numbering_format` / `lof_mixed_numbering_format` when a section contains both chapter-based (X.Y) and sequential (N) entry numbering; gates: ≥2 entries of each format type, page_number_token present, ≥10 chars; appendix-prefixed entries skipped; triage_tier: low; 13 synthetic tests added; see `docs/planning/p056_scope_and_design.md` and `docs/evaluation/p056_lot_lof_number_format_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P055:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_entry_type.py` (new module); LoT/LoF cross-type entry check (Q063/Q072 extension); emits `lot_entry_is_figure` when complete LoT entry starts with "Figure", `lof_entry_is_table` when complete LoF entry starts with "Table"; gates: ≥2 entries, page_number_token present, ≥10 chars, prefix must match `^figure\s+\d` or `^table\s+\d`; 10 synthetic tests added; see `docs/planning/p055_scope_and_design.md` and `docs/evaluation/p055_lot_lof_entry_type_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P054:** **implemented** — `src/njit_auditor/rules/pdf_toc_terminal_period.py` (already listed below)
- **P053:** **implemented** — `src/njit_auditor/rules/pdf_lot_terminal_period.py` (new module); LoT entry terminal-period check (Q065 refinement); symmetric counterpart to P040; emits `lot_entry_has_terminal_period` warning when complete LoT entries end with `.`; gates: ≥2 entries, page_number_token present, ≥10 chars after stripping; 9 synthetic tests added; see `docs/planning/p053_scope_and_design.md` and `docs/evaluation/p053_lot_terminal_period_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P052:** **implemented** — `src/njit_auditor/rules/pdf_copyright_page.py` (extended); copyright page author-format refinement; emits `copyright_author_not_found` advisory when copyright page + year detected but no author extractable; adds `_extract_copyright_author_adjacent_lines` helper; 9 synthetic tests added; see `docs/planning/p052_scope_and_design.md` and `docs/evaluation/p052_copyright_author_format_refinement_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P051:** **implemented** — `src/njit_auditor/rules/pdf_copyright_page.py` (extended); copyright page year-format refinement; emits `copyright_year_not_found` advisory when copyright page detected but no year token found; adds `_extract_copyright_year_adjacent_lines` helper for adjacent-line year patterns; 9 synthetic tests added; see `docs/planning/p051_scope_and_design.md` and `docs/evaluation/p051_copyright_year_format_refinement_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P050:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py` (extended); LoT/LoF left-column header ("Table"/"Figure") bold-style check (Q063/Q072); 9 synthetic tests added; see `docs/planning/p050_scope_and_design.md` and `docs/evaluation/p050_lot_lof_left_column_header_bold_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P049:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py`; LoT/LoF Page-column header right-alignment and bold-style refinement (Q064/Q073); 12 synthetic tests added; see `docs/planning/p049_scope_and_design.md` and `docs/evaluation/p049_lot_lof_column_header_refinement_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P048:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_page_number_alignment.py`; LoT/LoF page-number right-column alignment check (Q069/Q079); 9 synthetic tests added; see `docs/planning/p048_scope_and_design.md`, `docs/evaluation/p048_lot_lof_page_number_alignment_synthetic_validation.md`, and `docs/evaluation/p048_current_dataset_evaluation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P047:** **implemented** — `src/njit_auditor/rules/pdf_biosketch_bullet_spacing.py`; Bio Sketch bullet/list section single-spacing check (Q026); 6 synthetic tests added; see `docs/planning/p047_scope_and_design.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P046:** **implemented** — `src/njit_auditor/rules/pdf_lot_lof_entry_number_alignment.py`; LoT/LoF entry number left-column alignment check (Q068/Q078); 9 synthetic tests added; see `docs/planning/p046_scope_and_design.md` and `docs/evaluation/p046_lot_lof_entry_number_alignment_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **P045:** **implemented** — `src/njit_auditor/rules/pdf_biosketch_publication_layout.py`; Bio Sketch publication paragraph layout check (Q028/Q029); 8 synthetic tests added; see `docs/planning/p045_scope_and_design.md` and `docs/evaluation/p045_biosketch_publication_layout_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible; Sebastian Fine is ZIP-only; v1 covers Q029 (hanging indent) and Q028 (inter-entry spacing); Q026 (within-entry spacing) deferred to v2
- **P044:** **implemented** — `src/njit_auditor/rules/pdf_abstract_indentation.py`; Abstract page paragraph indentation check (Q002/Q003); 9 synthetic tests added; see `docs/planning/p044_scope_and_design.md`, `docs/evaluation/p044_abstract_indentation_synthetic_validation.md`, and `docs/evaluation/p044_current_dataset_evaluation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible; Sebastian Fine is ZIP-only; v1 limitations: Q003 gate skips single-paragraph abstracts; compressed/flattened PDFs skipped
- **P043:** **implemented** — `src/njit_auditor/rules/pdf_acknowledgements_indentation.py`; Acknowledgements paragraph indentation check (Q044/Q045); 7 synthetic tests added; see `docs/planning/p043_scope_and_design.md` and `docs/evaluation/p043_current_dataset_evaluation.md`; **current-dataset audit not run** — evaluation PDFs unavailable
- **P042:** **implemented** — `src/njit_auditor/rules/pdf_toc_appendix_format.py`; TOC appendix entry format check (Q058/Q059); 9 synthetic tests added; see `docs/planning/p042_scope_and_design.md` and `docs/evaluation/p042_toc_appendix_format_synthetic_validation.md`; **current-dataset audit not run** — evaluation PDFs unavailable
- **P041:** **implemented** — `src/njit_auditor/rules/pdf_dedication_page.py`; Dedication page top-margin header check (Q032); 8 synthetic tests added; see `docs/planning/p041_scope_and_design.md` and `docs/evaluation/p041_dedication_page_synthetic_validation.md`; **current-dataset audit not run** — evaluation PDFs unavailable
- **P040:** **implemented** — `src/njit_auditor/rules/pdf_lof_terminal_punctuation.py`; LoF entry terminal punctuation check (Q075); 9 synthetic tests added; see `docs/planning/p040_scope_and_design.md` and `docs/evaluation/p040_lof_terminal_punctuation_synthetic_validation.md`; **current-dataset audit not run** — evaluation PDFs unavailable
- **P054:** **implemented** — `src/njit_auditor/rules/pdf_toc_terminal_period.py` (new module); TOC entry terminal-period absence check (Q049/Q050/Q051 refinement); emits `toc_entry_has_terminal_period` warning when complete TOC entries end with `.`; gates: ≥2 entries, page_number_token present, ≥10 chars after stripping; symmetric counterpart to P053 (LoT no terminal period) for TOC pages; 9 synthetic tests added; see `docs/planning/p054_scope_and_design.md` and `docs/evaluation/p054_toc_terminal_period_synthetic_validation.md`; **current-dataset audit not run** — only 4/5 evaluation PDFs directly accessible
- **Web UI:** FastAPI web application present — `src/njit_auditor/web_app.py`; the public site accepts **PDF uploads only**, plus public PDF URLs (`POST /audits/url`) and built-in sample PDFs (`POST /audits/sample`). The web/reporting stack covers the implemented PDF audit surface through **P082** (P082 remains experimental/opt-in via CLI/API only and is disabled by default): P011–P068 plus P074 and P078 standalone PDF checks, with P069–P073 and P076/P077/P079/P081 as reporting/infrastructure refinements. Companion CLI support remains separate for TeX source audits (`P001–P010`) and P080 DOCX comment/tracked-change extraction. **Reports:** JSON/Markdown/report-view; **display:** `report_view.py` + polished Jinja results; **job TTL cleanup:** `cleanup_expired_jobs()` with `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` (default 24 h); **web export privacy:** basename-only paths in web-generated JSON/Markdown; **mobile/desktop parity:** same substantive results/actions across responsive layouts; **PDF routes:** served inline where possible, with browser-native preview behavior still dependent on local browser settings; **operations:** restart uvicorn/tmux after route, Jinja-global/filter, startup, or environment changes because template auto-reload alone is not sufficient. See `docs/web_gui_mvp.md`, `docs/planning/mobile_desktop_consistency_audit.md`, and `docs/planning/gui_scope_and_design.md`
- **Validation:** ruff, mypy, **1138 pytest** passed
- **P061:** **implemented** (PR #202) — `src/njit_auditor/rules/pdf_lot_lof_cross_page_entry_ordering.py`; LoT/LoF cross-page entry-number ordering (Q063/Q072 extension); 15 synthetic tests in `tests/test_p061_lot_lof_cross_page_entry_ordering.py`; see `docs/planning/p061_scope_and_design.md`; **formal current-dataset evaluation** (PR #204): **0** findings on five PDFs — sparse comparable LoT/LoF entries; does not prove compliance — see `docs/evaluation/p061_current_dataset_evaluation.md`
- **Auditor scope:** P001–P083 implemented; full Q001–Q079 / guideline source coverage is **not** complete
- **P039:** **implemented** — `src/njit_auditor/rules/pdf_toc_entry_hierarchy.py`; TOC level indentation hierarchy check (Q056); 9 synthetic tests added; see `docs/planning/p039_scope_and_design.md` and `docs/evaluation/p039_toc_entry_hierarchy_synthetic_validation.md`; **current-dataset audit not run** — evaluation PDFs unavailable
- **Five-PDF aggregate (P070-era full rerun, 2026-06-08):** **1,543** total — P070 parser refinement; `list_of_tables_figures_toc` 84 (−46 vs P069-era); deltas on Yin H 4th only among list-page files; see `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md`
- **Five-PDF aggregate (P069-era full rerun, 2026-06-08):** **1,590** total — unchanged vs P068-era; P069 infrastructure-only (0 standalone findings); P065–P068 counts unchanged; see `docs/evaluation/current_auditor_after_p069_evaluation.md`
- **Five-PDF aggregate (P068-era full rerun, 2026-06-08):** **1,590** total — P013 **461**, P026 **415**, P011 **169**, P012 **143**, P036 **77**; P068 **3** (3/5 files skipped at APPROVAL PAGE detection gate; 2/5 reached structural checks); see `docs/evaluation/current_auditor_after_p068_evaluation.md`
- **Five-PDF aggregate (P067-era full rerun, 2026-06-08):** **1,587** total — P013 **461**, P026 **415**, P011 **169**, P012 **143**, P036 **77**; P067 **0** (3/5 files skipped at BIOGRAPHICAL SKETCH heading detection; 2/5 reached BIOGRAPHICAL SKETCH but 0/5 reached a qualifying Publications boundary); see `docs/evaluation/current_auditor_after_p067_evaluation.md`
- **Five-PDF aggregate (P066-era full rerun, 2026-06-08):** **1,587** total — P013 **461**, P026 **415**, P011 **169**, P012 **143**, P036 **77**; P066 **0** (3/5 files skipped at BIOGRAPHICAL SKETCH heading detection; 2/5 reached year-ordering checks and passed); see `docs/evaluation/current_auditor_after_p066_evaluation.md`
- **Five-PDF aggregate (P065-era full rerun, 2026-06-08):** **1,587** total — P013 **461**, P026 **415**, P011 **169**, P012 **143**, P036 **77**; P065 **0** (no machine-readable DEDICATION heading on dataset); see `docs/evaluation/current_auditor_after_p065_evaluation.md`
- **Five-PDF aggregate (P063-era full rerun, 2026-06-07):** **1,587** total — P013 **461**, P026 **415**, P011 **169**, P012 **143**, P036 **77**; P063 **0** (no qualifying body-region appendix heading sequence on dataset); see `docs/evaluation/current_auditor_after_p063_evaluation.md`
- **Five-PDF aggregate (P062-era full rerun, 2026-06-07):** **1,587** total — P013 **461**, P026 **415**, P011 **169**, P012 **143**, P036 **77**; P062 **0** (no qualifying cross-page TOC sequence on dataset); see `docs/evaluation/current_auditor_after_p062_evaluation.md`
- **Five-PDF aggregate (P061-era full rerun, historical):** **1,587** total — P013 **461**, P026 **415**, P011 **169**, P012 **143**, P036 **77**; P061 **0**; see `docs/evaluation/current_auditor_after_p061_evaluation.md`
- **Five-PDF aggregate (historical pre-P035 baseline):** 1,446 total — P011–P034 only; `generated_for_commit: 00b9c2d`
- **P035 local subset (4 available PDFs, not canonical):** **13** findings — Yin H 4th compressed only; see `docs/evaluation/p035_current_dataset_evaluation.md`
- **P036 current-dataset audit:** **not run** — evaluation PDFs unavailable in workspace; see `docs/evaluation/p036_current_dataset_evaluation.md`
- **P-rules:** **68/68** implemented (`P001`–`P068`); P012 triage is a **reporting refinement** on existing P012 (not a new rule)
- **Q-rules (updated inventory):** **79** in `njit_rule_inventory.json` — **2** `implemented`, **56** `partially_implemented`, **21** `not_implemented` (9 manual-only, 12 automatable gaps; see `docs/status/q_rule_coverage_after_p044.md`)
- **Status/metadata cleanup:** complete through PR #89; P036 implemented — see `docs/planning/p036_scope_and_design.md`, `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md`, `docs/evaluation/p036_current_dataset_evaluation.md`; P035 docs in `docs/planning/p035_scope_and_design.md`, `docs/evaluation/p035_current_dataset_evaluation.md`
- **P037:** **implemented** — `src/njit_auditor/rules/pdf_roman_section_anchors.py`; section-anchored front-matter Roman numerals (Q022, Q031, Q035, Q046, Q060); 12 synthetic tests added; see `docs/planning/p037_scope_and_design.md` and `docs/evaluation/p037_roman_section_anchors_synthetic_validation.md`; **current-dataset audit not run** — evaluation PDFs unavailable; see `docs/evaluation/p037_current_dataset_evaluation.md`; v1 limitations: DEDICATION detection requires verbatim heading; compressed PDFs may produce false negatives; LOF anchor deferred to v2
- **Reusable-tooling audit:** **complete** — see `docs/planning/reusable_tooling_audit.md`; no external tool suitable for direct dependency; YAML spec concept from `AndrewGreenbaum/thesis-compliance` noted as future inspiration
- **P038:** **implemented** — `src/njit_auditor/rules/pdf_frontmatter_headings.py`; required front-matter heading presence and phrase-variant checks (Q013, Q021, Q036, Q047, Q061, Q070); 12 synthetic tests added; see `docs/planning/p038_scope_and_design.md` and `docs/evaluation/p038_frontmatter_headings_synthetic_validation.md`; **current-dataset audit not run** — evaluation PDFs unavailable
- **Five-PDF eval/manifest baseline:** `00b9c2d` (`generated_for_commit`; intentional — last substantive code/eval baseline before docs-only refreshes)

- **Q-rule coverage audit (after P044):** `docs/status/q_rule_coverage_after_p044.md` — full Q001–Q079 table, 17 remaining automatable gaps, P045 recommendation
- Strict coverage audit (historical baseline P029; updates through P036): `docs/status/source_to_implementation_coverage_after_p029.md`
- Data inventory: `docs/status/data_inventory_and_evaluation_sources.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
- **Current full-auditor snapshot (P070-era, still canonical):** `docs/evaluation/current_auditor_after_p070_evaluation.md` (**1,543** findings across five PDFs; P011–P070 at snapshot time; P071 infra-only with unchanged total; commit `b0ec5e4`)
- **Prior full-auditor snapshot (P069-era):** `docs/evaluation/current_auditor_after_p069_evaluation.md` (**1,590** findings across five PDFs; P011–P069; P069 infrastructure-only; delta 0 vs P068-era; commit `e045817`)
- **Full-auditor snapshot (P068-era, historical):** `docs/evaluation/current_auditor_after_p068_evaluation.md` (**1,590** findings; P068 adds 3; commit `5d8ebaf`)
- **Prior full-auditor snapshot (P067-era):** `docs/evaluation/current_auditor_after_p067_evaluation.md` (**1,587** findings across five PDFs; P011–P067; P067 adds 0; 3/5 files skipped at heading detection and 2/5 reached BIOGRAPHICAL SKETCH without a qualifying Publications boundary; commit `afe4ef6`)
- **Prior full-auditor snapshot (P066-era):** `docs/evaluation/current_auditor_after_p066_evaluation.md` (**1,587** findings across five PDFs; P011–P066; commit `e5caace`; P066 adds 0)
- **Prior full-auditor snapshot (P065-era):** `docs/evaluation/current_auditor_after_p065_evaluation.md` (**1,587** findings across five PDFs; P011–P065; commit `b233f3b`; P065 adds 0)
- **Prior full-auditor snapshot (P062-era):** `docs/evaluation/current_auditor_after_p062_evaluation.md` (**1,587** findings across five PDFs; P011–P062; commit `36373c9`; P062 adds 0)
- **Prior full-auditor snapshot (P061-era):** `docs/evaluation/current_auditor_after_p061_evaluation.md` (**1,587** findings across five PDFs; P011–P061; commit `ffea4e3`)
- **Historical full-auditor snapshot (pre-P035 canonical):** `docs/evaluation/current_auditor_after_p034_evaluation.md` (1,446 findings across five PDFs; baseline `00b9c2d`)
- **P036 current-dataset evaluation (not run):** `docs/evaluation/p036_current_dataset_evaluation.md` — no local audit; evaluation PDFs unavailable
- **P037 current-dataset evaluation (not run):** `docs/evaluation/p037_current_dataset_evaluation.md` — no local audit; evaluation PDFs unavailable
- **P038 current-dataset evaluation (not run):** `docs/evaluation/p038_current_dataset_evaluation.md` — no local audit; evaluation PDFs unavailable
- **P035 current-dataset subset (local, 4 PDFs):** `docs/evaluation/p035_current_dataset_evaluation.md` — 13 P035 findings on Yin H 4th only; not a new canonical aggregate
- **P013 reporting triage:** `docs/evaluation/p013_reporting_actionability_refinement.md` — dedicated `p013_triage` rollup + Markdown section (raw P013 counts unchanged)
- **P026 reporting triage:** `docs/evaluation/p026_reporting_actionability_refinement.md` — `p026_font_triage` rollup + Markdown section (raw P026 counts unchanged; 415 on five-PDF snapshot)
- **P081 P013/P026 calibration rollup:** reporting-only extension of the existing `p013_triage` and `p026_font_triage` summaries with dominant-pattern labels, calibration buckets, and compact outlier/routine page ranges (raw P013/P026 counts unchanged; canonical aggregate still 1,543)
- **P011 reporting triage:** `docs/evaluation/p011_reporting_actionability_refinement.md` — `p011_margin_triage` rollup + Markdown section (raw P011 counts unchanged; 169 on five-PDF snapshot)
- **P012 reporting triage:** `docs/evaluation/p012_reporting_actionability_refinement.md` — `p012_annotation_triage` rollup + Markdown section (raw P012 counts unchanged; 143 on five-PDF snapshot)
- **Canonical full-triage generated outputs:** `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md` — gitignored `data/evaluation/generated/current_auditor_after_p034_p011_triage/` (P011+P012+P013+P026 triage rollups; 1,446 total unchanged; regenerate locally to include `p012_annotation_triage` after PR #79)
- **P013 triage refresh (historical):** `docs/evaluation/current_auditor_after_p034_p013_triage_refresh.md` — superseded by canonical path above for full reports
- Historical full-auditor snapshot (P001–P029): `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`
- **Real-thesis pairing and EF overlap readiness (P068-era refresh):** `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md` — data inventory, raw/commented pair table, extractability table, overlap-readiness table, recommended evaluation cadence, next actions (refreshed 2026-06-08 after P068 aggregate)
- **Full repository audit after P071:** `docs/status/full_repository_audit_after_p071.md` — post-P071 comprehensive audit; canonical aggregate 1,543; EF overlap current through PR #257
- **EF overlap after P071 (comparison PDFs):** `docs/evaluation/ef_overlap_after_p071_evaluation.md` — post-P071 refresh on 2 extractable-comment PDFs; P064 now reaches both comparison PDFs (localization fixed) but `references_citations` EF gap unchanged (9 EF, 0 tool); total tool findings still 671; `committee_approval_page` and `list_of_tables_figures_toc` gaps unchanged
- **EF overlap after P068 (comparison PDFs):** `docs/evaluation/ef_overlap_after_p068_evaluation.md` — page/category overlap refresh on 2 extractable-comment PDFs; P064–P068 added 0 findings on comparison set; historical baseline before P071 localization fix
- Historical EF overlap study (P001–P029 scope): `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- EF-overlap refinement notes: `docs/evaluation/ef_overlap_driven_refinement_notes.md`
- EF-overlap refinement evaluation: `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`
- EF-overlap round2 notes: `docs/evaluation/ef_overlap_refinement_round2_notes.md`
- EF-overlap round2 evaluation: `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
- P030 synthetic validation: `docs/evaluation/p030_toc_continued_heading_synthetic_validation.md`
- P030 current-dataset evaluation: `docs/evaluation/p030_current_dataset_evaluation.md`
- P031 synthetic validation: `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md`
- P031 current-dataset evaluation: `docs/evaluation/p031_current_dataset_evaluation.md`
- P031 Sebastian clean-baseline investigation: `docs/evaluation/p031_sebastian_clean_baseline_investigation.md`
- P032 synthetic validation: `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md`
- P032 current-dataset evaluation: `docs/evaluation/p032_current_dataset_evaluation.md` (refreshed after PR #59; 0 P032 on all evaluated PDFs)
- P032 Yin H 4th page-15 investigation: `docs/evaluation/p032_yin_h_4th_page15_investigation.md`
- P033 synthetic validation: `docs/evaluation/p033_title_consistency_synthetic_validation.md`
- P033 current-dataset evaluation: `docs/evaluation/p033_current_dataset_evaluation.md` (refreshed after PR #63; 0 P033 findings; comparison runs on 2/5 files)
- P033 candidate-extraction recall investigation: `docs/evaluation/p033_candidate_extraction_recall_investigation.md`
- P034 synthetic validation: `docs/evaluation/p034_copyright_page_synthetic_validation.md`
- P034 current-dataset evaluation: `docs/evaluation/p034_current_dataset_evaluation.md` (refreshed after PR #67; 0 P034 findings on 5/5 files)
- P034 author-mismatch investigation: `docs/evaluation/p034_author_mismatch_investigation.md`
- P035 synthetic validation: `docs/evaluation/p035_figure_table_layout_synthetic_validation.md`
- P035 current-dataset evaluation (local 4-PDF subset): `docs/evaluation/p035_current_dataset_evaluation.md` — 13 P035 findings on Yin H 4th only; not canonical five-PDF aggregate
- P036 synthetic validation: `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md`
- P036 current-dataset evaluation (not run): `docs/evaluation/p036_current_dataset_evaluation.md` — no P036 counts; evaluation PDFs unavailable
- P037 synthetic validation: `docs/evaluation/p037_roman_section_anchors_synthetic_validation.md`
- P038 synthetic validation: `docs/evaluation/p038_frontmatter_headings_synthetic_validation.md`
- P038 current-dataset evaluation (not run): `docs/evaluation/p038_current_dataset_evaluation.md` — no P038 counts; evaluation PDFs unavailable
- P039 synthetic validation: `docs/evaluation/p039_toc_entry_hierarchy_synthetic_validation.md`
- P039 current-dataset evaluation (not run): `docs/evaluation/p039_current_dataset_evaluation.md` — no P039 counts; evaluation PDFs unavailable
- P040 synthetic validation: `docs/evaluation/p040_lof_terminal_punctuation_synthetic_validation.md`
- P040 current-dataset evaluation (not run): `docs/evaluation/p040_current_dataset_evaluation.md` — no P040 counts; evaluation PDFs unavailable
- P041 synthetic validation: `docs/evaluation/p041_dedication_page_synthetic_validation.md`
- P041 current-dataset evaluation (not run): `docs/evaluation/p041_current_dataset_evaluation.md` — no P041 counts; evaluation PDFs unavailable
- P042 synthetic validation: `docs/evaluation/p042_toc_appendix_format_synthetic_validation.md`
- P042 current-dataset evaluation (not run): `docs/evaluation/p042_current_dataset_evaluation.md` — no P042 counts; evaluation PDFs unavailable
- P043 current-dataset evaluation (not run): `docs/evaluation/p043_current_dataset_evaluation.md` — no P043 counts; evaluation PDFs unavailable
- P048 current-dataset evaluation (not run): `docs/evaluation/p048_current_dataset_evaluation.md` — no P048 counts; only 4/5 evaluation PDFs directly accessible
- P051 synthetic validation: `docs/evaluation/p051_copyright_year_format_refinement_synthetic_validation.md`
- P051 current-dataset evaluation (not run): `docs/evaluation/p051_current_dataset_evaluation.md` — no P051 counts; only 4/5 evaluation PDFs directly accessible
- P052 synthetic validation: `docs/evaluation/p052_copyright_author_format_refinement_synthetic_validation.md`
- P052 current-dataset evaluation (not run): `docs/evaluation/p052_current_dataset_evaluation.md` — no P052 counts; only 4/5 evaluation PDFs directly accessible
- P053 synthetic validation: `docs/evaluation/p053_lot_terminal_period_synthetic_validation.md`
- P053 current-dataset evaluation (not run): `docs/evaluation/p053_current_dataset_evaluation.md` — no P053 counts; only 4/5 evaluation PDFs directly accessible
- P055 synthetic validation: `docs/evaluation/p055_lot_lof_entry_type_synthetic_validation.md`
- P055 current-dataset evaluation (not run): `docs/evaluation/p055_current_dataset_evaluation.md` — no P055 counts; only 4/5 evaluation PDFs directly accessible
- P056 synthetic validation: `docs/evaluation/p056_lot_lof_number_format_synthetic_validation.md`
- P056 current-dataset evaluation (not run): `docs/evaluation/p056_current_dataset_evaluation.md` — no P056 counts; only 4/5 evaluation PDFs directly accessible
- P057 synthetic validation: `docs/evaluation/p057_lot_lof_page_number_ordering_synthetic_validation.md`
- P057 current-dataset evaluation (not run): `docs/evaluation/p057_current_dataset_evaluation.md` — no P057 counts; only 4/5 evaluation PDFs directly accessible

### P030–P039 evaluation docs (chronological)

| Order | Doc | Type |
|---:|---|---|
| 1 | `docs/evaluation/p030_toc_continued_heading_synthetic_validation.md` | Synthetic |
| 2 | `docs/evaluation/p030_current_dataset_evaluation.md` | Current dataset |
| 3 | `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md` | Synthetic |
| 4 | `docs/evaluation/p031_current_dataset_evaluation.md` | Current dataset |
| 5 | `docs/evaluation/p031_sebastian_clean_baseline_investigation.md` | Investigation |
| 6 | `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md` | Synthetic |
| 7 | `docs/evaluation/p032_current_dataset_evaluation.md` | Current dataset |
| 8 | `docs/evaluation/p032_yin_h_4th_page15_investigation.md` | Investigation |
| 9 | `docs/evaluation/p033_title_consistency_synthetic_validation.md` | Synthetic |
| 10 | `docs/evaluation/p033_current_dataset_evaluation.md` | Current dataset |
| 11 | `docs/evaluation/p033_candidate_extraction_recall_investigation.md` | Investigation |
| 12 | `docs/evaluation/p034_copyright_page_synthetic_validation.md` | Synthetic |
| 13 | `docs/evaluation/p034_current_dataset_evaluation.md` | Current dataset |
| 14 | `docs/evaluation/p034_author_mismatch_investigation.md` | Investigation |
| 15 | `docs/evaluation/p035_figure_table_layout_synthetic_validation.md` | Synthetic |
| 16 | `docs/evaluation/p035_current_dataset_evaluation.md` | Current dataset (local 4-PDF subset) |
| 17 | `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md` | Synthetic |
| 18 | `docs/evaluation/p036_current_dataset_evaluation.md` | Current dataset (not run) |
| 19 | `docs/evaluation/p037_roman_section_anchors_synthetic_validation.md` | Synthetic |
| 20 | `docs/evaluation/p037_current_dataset_evaluation.md` | Current dataset (not run) |
| 21 | `docs/evaluation/p038_frontmatter_headings_synthetic_validation.md` | Synthetic |
| 22 | `docs/evaluation/p038_current_dataset_evaluation.md` | Current dataset (not run) |
| 23 | `docs/evaluation/p039_toc_entry_hierarchy_synthetic_validation.md` | Synthetic |
| 24 | `docs/evaluation/p039_current_dataset_evaluation.md` | Current dataset (not run) |
| 25 | `docs/evaluation/p040_lof_terminal_punctuation_synthetic_validation.md` | Synthetic |
| 26 | `docs/evaluation/p040_current_dataset_evaluation.md` | Current dataset (not run) |
| 27 | `docs/evaluation/p041_dedication_page_synthetic_validation.md` | Synthetic |
| 28 | `docs/evaluation/p041_current_dataset_evaluation.md` | Current dataset (not run) |
| 29 | `docs/evaluation/p042_toc_appendix_format_synthetic_validation.md` | Synthetic |
| 30 | `docs/evaluation/p042_current_dataset_evaluation.md` | Current dataset (not run) |
| 31 | `docs/evaluation/p043_current_dataset_evaluation.md` | Current dataset (not run) |

**Privacy:** All evaluation docs are aggregate-only. Do not quote dissertation body text, title text, or author names. Generated audit JSON/MD outputs stay under gitignored `data/evaluation/generated/`.

---

## 1. Implemented Feature Summary

### TeX Source Audit (P001–P010)

| Module | Rule(s) | What It Does |
|--------|---------|-------------|
| `latex_risky_commands.py` | P001 | Detects risky manual formatting commands (`\vspace`, `\setlength`, etc.) |
| `latex_labels.py` | P002–P004 | Duplicate `\label`, whitespace in label names, unresolved `\ref`/`\eqref` |
| `latex_figures_tables.py` | P005–P007 | Missing `\caption`, missing `\label`, caption terminal punctuation |
| `latex_structure.py` | P008 | Required document structure commands present (TOC, abstract, LOT/LOF) |
| `latex_linters.py` | P009–P010 | chktex and lacheck integration (graceful skip if not installed) |
| `latex_abstract.py` | Q004–Q005 | Abstract forbidden words ("paper"/"article") and first-person pronouns |
| `latex_metadata.py` | Q006 | Graduation month validation (Aug/Dec/May) |
| `abstract.py` | P021 (TeX) | Abstract word count (PhD ≤350, MS ≤150) |

### PDF Layout Audit (P011–P067)

| Module | Rule(s) | What It Does |
|--------|---------|-------------|
| `pdf_margins.py` | P011 | Text crossing 1.5"/1" margin boundaries |
| `pdf_annotations.py` | P012 | Embedded PDF annotation objects |
| `pdf_page_numbers.py` | P013, P019 | Page-number candidate detection; sequence/style consistency |
| `pdf_headings.py` | P014 | Named front-matter heading layout (bold/all-caps/centered/near-top) for 7 headings |
| `pdf_indentation.py` | P015 | First paragraph flush-left; subsequent paragraphs indented |
| `pdf_spacing.py` | P016 | Spacing/blank-line gap checks (front-matter focused) |
| `pdf_captions.py` | P017 | Caption terminal punctuation; table-title no-period signal |
| `pdf_toc_alignment.py` | P018 | TOC/list entry alignment (leaders, page-number column, indentation hierarchy) |
| `pdf_abstract.py` | P021 (PDF) | Abstract word count via PDF text layer |
| `pdf_frontmatter_no_page_number.py` | P022 | No visible page number on Abstract, Title, Approval, Copyright pages |
| `pdf_body_spacing.py` | P023 | Body text double-spacing (line spacing ≥ 1.55× font size, conservative threshold) |
| `pdf_font_compliance.py` | P026 | Body font size ≈12pt and Times New Roman (or accepted equivalent) |
| `pdf_heading_levels.py` | P027 | Numbered heading level-specific style (L1 ALL CAPS, L2 Title Case, L3-5 Sentence case) |
| `pdf_page_numbering_regime.py` | P028 | Front-matter Roman / body Arabic page-numbering regime check |
| `pdf_roman_sequence.py` | P029 | Front-matter lowercase Roman numeral ordering (i, ii, iii...) |
| `pdf_toc_continued_headings.py` | P030 | Multi-page TOC/LoT/LoF continued-heading checks |
| `pdf_lot_lof_column_headers.py` | P031 | LoT/LoF column header label checks |
| `pdf_toc_list_wrapped_spacing.py` | P032 | Wrapped TOC/LoT/LoF entry internal spacing checks |
| `pdf_title_consistency.py` | P033 | Cross-page front-matter title consistency checks |
| `pdf_copyright_page.py` | P034 | Copyright Page top-margin header; year/author consistency with Title Page |
| `pdf_figure_table_layout.py` | P035 | Body-page figure/table centering and caption placement (text-layer bodies) |
| `pdf_toc_list_entry_spacing.py` | P036 | TOC/LoT/LoF inter-entry double spacing (distinct entries; complements P032) |
| `pdf_toc_list_formatting.py` | P024 | TOC L1 (ALL CAPS), L2 (title case), LoT (title case, no period), LoF (sentence case) |
| `pdf_frontmatter_structure.py` | P025 | Abstract body presence, title-page degree/institution, approval-page content, front-matter order |
| `pdf_title_capitalization.py` | P020 | L2 heading and table-title title-case via bold font metadata |
| `pdf_toc_entry_hierarchy.py` | P039 | TOC level indentation hierarchy: L2 entries indented relative to L1, L3 relative to L2 (Q056) |
| `pdf_lof_terminal_punctuation.py` | P040 | LoF entry terminal punctuation: complete entries must end with `.`/`?`/`!`; skips wrap continuations (Q075) |
| `pdf_dedication_page.py` | P041 | Dedication page top-margin header: no running header text in top 15% of page; gate: skip if DEDICATION not detected (Q032) |
| `pdf_toc_appendix_format.py` | P042 | TOC appendix entry format: single appendix → APPENDIX + title; multiple appendices → each APPENDIX + letter; TOC-only (Q058/Q059) |
| `pdf_acknowledgements_indentation.py` | P043 | Acknowledgements page paragraph indentation: first paragraph flush-left (Q044); subsequent paragraphs indented (Q045); Acknowledgements-page-only complement to P015 |
| `pdf_abstract_indentation.py` | P044 | Abstract page paragraph indentation: first paragraph flush-left (Q002); subsequent paragraphs indented (Q003); Abstract-page-only complement to P015 |
| `pdf_biosketch_publication_layout.py` | P045 | Bio Sketch publication layout: hanging indent (Q029), inter-entry double spacing (Q028), and wrapped-line single spacing (Q026); geometry-only metadata |
| `pdf_lot_lof_entry_number_alignment.py` | P046 | LoT/LoF entry number left-column alignment: table/figure entry numbers align at a consistent x-position (Q068/Q078); privacy-safe geometry metadata |
| `pdf_biosketch_bullet_spacing.py` | P047 | Bio Sketch bullet/list section single-spacing: non-hanging-indent multi-line blocks checked for excessive internal gaps (Q026); privacy-safe geometry metadata |
| `pdf_biosketch_publication_ordering.py` | P067 | Bio Sketch publication/presentation reverse-chronology check: grouped citation-like entry years must be non-increasing below a Publications/Presentations boundary (Q027); privacy-safe counts/year metadata only |
| `pdf_lot_lof_page_number_alignment.py` | P048 | LoT/LoF page-number right-column alignment: table/figure page numbers align at a consistent right-column x-position (Q069/Q079); privacy-safe geometry metadata |
| `pdf_lot_lof_column_header_style_alignment.py` | P049 | LoT/LoF Page-column header right-alignment and bold-style refinement: 'Page' header right-edge alignment and bold style (Q064/Q073); privacy-safe style/geometry metadata |
| `pdf_lot_lof_column_header_style_alignment.py` | P050 | LoT/LoF left-column header bold-style check: 'Table'/'Figure' header labels bold when font metadata is reliable (Q063/Q072); gate: skip if header absent or fewer than 3 complete entries; privacy-safe style metadata only |
| `pdf_copyright_page.py` | P051 | Copyright page year-format refinement: advisory when copyright page detected but no year token present (Q010); adjacent-line year extraction; conservative skip when year present but unextractable; privacy-safe metadata only |
| `pdf_copyright_page.py` | P052 | Copyright page author-format refinement: advisory when copyright page + year detected but no author extractable (Q011); adjacent-line author extraction; only fires when year is confirmed; hash-only privacy-safe metadata |
| `pdf_lot_terminal_period.py` | P053 | List of Tables entry terminal-period check: emits warning when complete LoT entry ends with `.` (Q065); symmetric counterpart to P040 (LoF must have terminal punct; LoT must not); gates: ≥2 entries, page_number_token present, ≥10 chars; privacy-safe metadata only (no entry text, table titles) |
| `pdf_toc_terminal_period.py` | P054 | TOC entry terminal-period absence check: emits warning when complete TOC entry ends with `.` (Q049/Q050/Q051 refinement); symmetric counterpart to P053 for TABLE OF CONTENTS pages; gates: ≥2 entries, page_number_token present, ≥10 chars; privacy-safe metadata only (no TOC entry text, chapter titles) |
| `pdf_lot_lof_entry_type.py` | P055 | LoT/LoF cross-type entry check: emits warning when complete LoT entry starts with "Figure" (`lot_entry_is_figure`) or complete LoF entry starts with "Table" (`lof_entry_is_table`) (Q063/Q072 extension); gates: ≥2 entries, page_number_token present, ≥10 chars, prefix must match `^figure\s+\d` or `^table\s+\d`; privacy-safe metadata only (no entry text, figure/table titles) |
| `pdf_lot_lof_number_format.py` | P056 | LoT/LoF entry numbering format consistency check: emits advisory when a section mixes chapter-based (X.Y) and sequential (N) entry numbering (Q063/Q072 extension); gates: ≥2 entries of each format type, page_number_token present, ≥10 chars; appendix-prefixed entries (e.g. "Table A.1") skipped; triage_tier: low; privacy-safe metadata only |
| `pdf_lot_lof_page_number_ordering.py` | P057 | LoT/LoF page-number ordering check: emits advisory when a List of Tables or List of Figures page has complete entries whose page numbers are not non-decreasing (Q069/Q079 refinement); gates: ≥3 comparable integer entries, ≥2 inversions; non-integer tokens (roman numerals) skipped; TOC excluded; triage_tier: medium; privacy-safe metadata only |
| `pdf_toc_page_number_ordering.py` | P058 | TOC page-number ordering check: emits advisory when TABLE OF CONTENTS entries have page numbers that are not non-decreasing (Q057 refinement); gates: ≥3 comparable integer entries, ≥2 inversions; non-integer tokens (roman numerals) skipped; LoT/LoF excluded; triage_tier: medium; privacy-safe metadata only |
| `pdf_lot_lof_entry_number_ordering.py` | P059 | LoT/LoF entry-number ordering check: emits warning when List of Tables or List of Figures entries have entry numbers (numeric token following "Table"/"Figure" label) that are not non-decreasing (Q063/Q072 refinement); gates: ≥3 comparable entries, ≥2 inversions; mixed sequential+chapter-based pages skipped; appendix/letter-prefixed entries skipped; TOC excluded; triage_tier: medium; privacy-safe metadata only |
| `pdf_toc_entry_number_ordering.py` | P060 | TOC section-number ordering check: emits warning when parseable numeric section entries in TABLE OF CONTENTS (entries starting with a bare number, e.g. "1 Introduction", "1.1 Background") are not in non-decreasing order (Q056/Q057 implied); gates: ≥3 comparable entries, ≥2 inversions; word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) skipped; LoT/LoF excluded; triage_tier: medium; privacy-safe metadata only |
| `pdf_lot_lof_cross_page_entry_ordering.py` | P061 | LoT/LoF cross-page entry-number ordering check: emits warning when consecutive same-type LoT or LoF pages span multiple pages and combined entry numbers are not non-decreasing (Q063/Q072 extension); gates: ≥2 consecutive pages, ≥3 combined comparable entries, ≥2 inversions; mixed-format runs skipped; cross-page companion to P059; triage_tier: medium; privacy-safe metadata only |
| `pdf_toc_cross_page_entry_ordering.py` | P062 | TOC cross-page section-number ordering check: emits warning when consecutive TABLE OF CONTENTS pages have a combined section-number sequence that is not non-decreasing (Q056/Q057 extension); gates: ≥2 consecutive TOC pages, ≥3 combined comparable entries, ≥2 inversions; word-prefix entries skipped; cross-page companion to P060 and symmetric counterpart to P061; triage_tier: medium; privacy-safe metadata only |
| `pdf_appendix_body_headings.py` | P063 | Body-page appendix heading label check: emits warnings when body-page APPENDIX headings do not follow NJIT label conventions — single appendix must use APPENDIX (no letter); multiple appendices must use APPENDIX A/B/C with consecutive letters (Q058/Q059 body-page extension; companion to P042); triage_tier: medium; privacy-safe metadata only |

### Infrastructure

| Module | Purpose |
|--------|---------|
| `audit_runner.py` | Shared PDF API: `run_pdf_audit_full()` / `collect_pdf_layout_findings()` — P011–P067; used by CLI and web app |
| `web_app.py` | FastAPI web application: upload form, background audit task, JSON/Markdown download |
| `templates/` | Jinja2 HTML templates for the web UI (base, index, job) |
| `report_outputs.py` | JSON/Markdown report generation; `build_grouped_summary`, `compact_page_list` added for triage summaries |
| `cli.py` | CLI entry point for both TeX and PDF audit modes |
| `pdf_layout.py` / `pdf_loader.py` | PDF geometry extraction (pdfplumber) |
| `pdf_models.py` | Typed data models for pages, blocks, spans |
| `models.py` | `Finding` model (rule_id, severity, detail, page, location) |
| `report_outputs.py` | JSON and Markdown report generation |
| `report.py` | Report aggregation |
| `comment_analysis.py` | EF comment keyword categorization |
| `evaluation.py` | EF comment vs. tool-finding comparison helpers |
| `pdf_comments.py` | PDF annotation extraction and cleaning |
| `rule_loader.py` | Load and validate rule inventory JSON files |

---

## 2. Rule Coverage Summary

| Category | Total | Implemented | Partial | Not Implemented | Manual-Only |
|----------|------:|:-----------:|:-------:|:--------------:|:-----------:|
| Q-rules (Q001–Q079) | 79 | 2 (Q004, Q005) | ~38 | ~17 | ~22 |
| P-rules (P001–P071) | 71 | 71 | — | — | — |

### Q-Rule Not-Implemented Clusters (automatable)

- **TOC/list internal formatting**: wrapping spacing partially covered by P032 (Q053–Q055, Q066–Q067, Q076–Q078); inter-entry double spacing partially covered by **P036** (Q057, Q067, Q077); "(Continued)" headers (Q048, Q062, Q071) partially covered by P030; column headers bold/aligned (Q063–Q064, Q072–Q073) partially covered by P031 and P049
- **Front-matter visual checks**: copyright page (Q009–Q011) partially covered by P034; dedication centering/italic (Q033–Q034), bio-sketch content (Q023–Q025, Q027–Q029)
- **Heading level distinctions**: L3/L4/L5 partially addressed by P027; bold/italic enforcement still missing
- **Page-number sequence correctness**: Roman numeral value sequence (Q022, Q031, Q035, Q046, Q060 partially covered by P028 regime check, P029 relative ordering, and **P037** section-anchored values; LOF anchor and remaining gaps not yet validated)
- **Figure/table body checks**: figure centering, table placement (above/below detection)
- **Cross-page title consistency**: partially covered by P033 (heuristic; skips ambiguous/image-only cases)

---

## 3. Evaluation Summary

**EF PDFs tested (4 files):**

| File | Extractable Comments | Notes |
|------|:-------------------:|-------|
| `250218 Cibaku Elson First Review.pdf` | Yes (78 highlights) | Best overlap with heading/capitalization signals |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | Yes (65 highlights) | Best for indentation/spacing comparison |
| `260415 Yin H _2nd_review with EF Comments.pdf` | No (flattened) | Identical audit counts to Yin Haotian (same doc) |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | No (flattened) | Highest finding count — compression artifacts inflate P011 |

**Full evaluation (post P020 refinement):** See `docs/evaluation/after_p020_refinement_current_snapshot.md` for the current snapshot after PR #37 (CMBX heading detection). Prior full baseline: `docs/evaluation/current_auditor_after_p028_evaluation.md`.

**Summary counts across 4 EF PDFs (Yin H 4th compressed — highest volume):**

| Rule | Count | Notes |
|------|------:|-------|
| P011 | 150 | Inflated by compression artifacts on compressed PDF |
| P013 | 149 | Candidate detector; high volume by design |
| P026 | 117 | Font family violations (Georgia/Arial — real noncompliance) |
| P023 | 0 | Double-spacing appears correct in body |
| P025 | 0 | Front-matter structure correct |
| P022 | 0 | No stray page numbers on no-number pages |
| P028 | 8 | Mixed page-numbering regime (Arabic on front-matter, Roman on body) |
| P027 | 2 | Two L1 chapter headings not ALL CAPS |
| P024 | 12 | TOC/LoT/LoF capitalization/punctuation |

**Current EF comment-vs-tool overlap (extractable PDFs only):**
- Compared files: Cibaku Elson 1st review (78 comments), Yin Haotian 2nd review (65 comments)
- Page overlap: all EF-comment pages also have tool findings (Cibaku 42/42, Yin 44/44)
- Category overlap is narrow: Yin shows overlap in `indentation` (2 pages) and `margin_or_overflow` (1 page); Cibaku shows no positive overlap in the shared category set
- Major uncaptured EF areas remain `references_citations`, `committee_approval_page`, and semantic/manual feedback (`unclear_or_other`)

**Biggest current noise sources:**
- P013 (page-number candidates): always very high-volume by design
- P011 (margins): 70 findings on compressed PDF (down from 150 with artifact guard); 21–33 on normal PDFs
- P026 (font family): 92–117 warnings per document — real noncompliance but high volume

**Latest EF-overlap-driven refinement (P013 grouping):**
- P013 now emits one warning per page with candidates (instead of one per candidate line) and adds structured triage details (`issue_type`, candidate count/sample, style/position, confidence).
- Focused comparison-set impact:
  - Cibaku: P013 `99 → 95` (page coverage unchanged: 94 pages)
  - Yin Haotian: P013 `113 → 104` (page coverage unchanged: 103 pages)
  - Sebastian clean baseline: P013 `27 → 25`
- EF-overlap effect for P013 pages is unchanged on extractable-comment PDFs; refinement reduces repeated noise without narrowing coverage.

**Round 2 EF-overlap-driven refinement (P018/P024 heading variants):**
- Expanded TOC/List heading detection to include trailing punctuation and `(CONTINUED)`/`CONTINUED` suffix variants.
- Synthetic regression tests added for:
  - `TABLE OF CONTENTS.` handling (P018 path)
  - `LIST OF TABLES (CONTINUED)` handling (P024 path)
- Focused dataset impact was neutral (no count shifts on extractable-comment PDFs), but baseline behavior stayed stable (no added noise on Sebastian).

**Biggest coverage gaps relative to EF feedback:**
- P020 (title capitalization): fires 0 on 3 of 4 PDFs — bold metadata absent in most PDFs; font-size fallback still needed
- Cross-page title consistency: partial PDF heuristic via P033; manual review still required for edge layouts
- TOC "(Continued)" headers: multi-page TOC not handled

**Clean baseline:** Sebastian Fine Revision 3 (archive-contained) is in the five-PDF current-dataset evaluation set; used for P014/P031/P034 investigations and false-positive analysis.

**Per-rule current-dataset status (P030–P034):** All report **0** findings on the five-PDF set after respective refinements (see evaluation index above). This does not prove full guideline compliance.

---

## 4. Remaining Gaps After P061 (Prioritized)

### A. Automatable / partial (not yet fully covered)

| Priority | Gap | Type | Notes |
|----------|-----|------|-------|
| 🟢 Done | Full five-PDF P001–P068 aggregate snapshot | Data/eval | `docs/evaluation/current_auditor_after_p068_evaluation.md` now records the reproducible five-PDF aggregate at 1,590 findings; rerun only when audit behavior changes |
| 🟡 High | Figure/table centering and placement | **Partial (P035)** | Text-layer bodies only; image-only floats are skipped in v1 |
| 🟢 Done | P061 cross-page LoT/LoF ordering | **Implemented + evaluated** | PR #202 implementation; PR #204 formal eval — **0** findings (sparse comparable entries) — `docs/planning/p061_scope_and_design.md`, `docs/evaluation/p061_current_dataset_evaluation.md` |
| 🟡 Med | Heading bold/italic enforcement beyond P027/P049/P050 | Partial | Still constrained by PDF font-style metadata quality |
| 🟡 Med | Front-matter dedication/bio-sketch semantics (Q023–Q030, Q033–Q034) | Partial/manual | Content, chronology, centering, and italics remain incomplete |
| 🟡 Med | Approval/Acknowledgements semantics (Q015–Q020, Q037–Q043) | Manual/partial | Committee rank/order and paragraph-intent checks remain manual-only |
| 🟡 Low | Evaluation-set expansion | Data/eval | More extractable EF-comment PDFs from archive |
| 🟡 Low | EF category ↔ rule mapping at scale | Eval | Page/category precision/recall vs human comments |

### B. Recently addressed (P030–P034 — historical)

| Rule | Status |
|------|--------|
| P030 continued TOC/LoT/LoF headings | ✅ Implemented; 0 current-dataset findings |
| P031 LoT/LoF column headers | ✅ Implemented; false positives fixed (PR #55) |
| P032 wrapped-entry spacing | ✅ Implemented; Yin H 4th false positives fixed (PR #59) |
| P033 cross-page title consistency | ✅ Implemented; comparison on 2/5 files; 0 findings |
| P034 copyright page Q009–Q011 | ✅ Implemented; author false positives fixed (PR #67) |

### C. Partial rules still needing refinement

| Rule | Issue | Suggested direction |
|------|-------|---------------------|
| P020 | Bold metadata absent in many PDFs; low recall | Font-size fallback (historical note) |
| P013 | High volume by design | Further triage/grouping if needed |
| P016 | Front-matter-focused | Extend to body chapters conservatively |
| P025 | Limited degree/institution patterns | Extend nospace/abbreviation fallbacks |
| P033 | Comparison only 2/5 files | More candidate extraction paths (privacy-safe) |
| P034 | Year/author extraction skipped on 3/5 | ©-line and title-page pattern expansion |

### D. Manual-only / process-only (not automatable without semantic AI)

Approval Page committee semantics (Q015–Q020), Acknowledgements intent (Q037–Q042), administrative approval workflows, and many visual-layout judgments remain **manual-only** per the strict coverage audit.

### E. Evaluation / data tasks

- ~~Refresh a full P001–P034 aggregate snapshot~~ — done: `docs/evaluation/current_auditor_after_p034_evaluation.md`
- Expand EF overlap to additional extractable archive PDFs when available locally
- Per-category precision/recall vs EF comments (aggregate only)

---

## 5. Recommended Next Implementation Bundles

### Bundle 1 (DONE): P022 — Page-Number Absence on Named Pages
### Bundle 2 (DONE): P026 — Font Compliance
### Bundle 3 (DONE): P027 — Heading Level Style
### Bundle 4 (DONE): P028 — Page-Numbering Regime

### Bundle 5 (DONE): P020 CMBX/Font-Size Heading Detection Refinement
CMBX (Computer Modern Bold) now recognized as bold at layout extraction layer.
Font-size fallback added for non-bold large-font headings.
See `docs/evaluation/phase2_p020_heading_detection_refinement_evaluation.md`.

### Bundle 6: Roman Numeral Sequence Ordering (P029) — IMPLEMENTED
**Summary:** P029 was added to conservatively validate visible lowercase Roman numeral ordering across front-matter pages. It flags repeats, decreases, and non-consecutive visible numerals while excluding recognized no-number pages (ABSTRACT, APPROVAL PAGE, etc.).
**Q-rule basis:** Q022, Q031, Q035, Q046, Q060
**Files changed:** `src/njit_auditor/rules/pdf_roman_sequence.py`, CLI integration, inventory and tests
**Risk:** Medium — heuristic, conservative checks; does not replace manual review.

### Bundle 7: P011 Compression Artifact Guard — IMPLEMENTED
**Summary:** Added a group-level artifact guard to P011. Groups with ≥5 lines all within 8pt of
the margin are suppressed as compression-coordinate artifacts. Reduced P011 from 150 → 70 on
the compressed Yin H 4th PDF while leaving all normal-PDF counts unchanged (21–33).
Added `confidence` (low/medium/high) to P011 finding details.
**Files changed:** `src/njit_auditor/rules/pdf_margins.py`, tests, evaluation and status docs.
**Risk:** Low — conservative threshold; does not affect normal PDFs.

### Bundle 8: P014 Clean-Baseline Investigation — IMPLEMENTED
**Summary:** Investigated 6 P014 false positives on Sebastian Fine clean baseline. Root cause:
P014 compared heading center against page center (306pt) instead of text-area center (324pt).
NJIT's asymmetric margins (1.5" left, 1" right) shift the text area center 18pt right of page
center. Fixed `_line_centered` to compare against text-area center. Before/after: Sebastian
Fine 6→0, Cibaku 1→0, Yin Haotian 1→0, Yin H 4th 10→0 — all false positives removed.
**Files changed:** `src/njit_auditor/rules/pdf_headings.py`, tests, evaluation docs.
**Risk:** Low — fix narrows false positives; off-center headings still flagged.

### Bundle 9: Current Evaluation Snapshot (after P011/P014/P029 refinements) — DONE
**Summary:** Full evaluation snapshot at commit `6a0baaf` across all 5 dissertation PDFs.
Total: 1,485 findings (down from 1,572). Key changes: P011 compressed 150→70; P014 0 everywhere;
P029 adds 12+2 findings. See `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`.

### Bundle 10: P029 Boundary Guard — IMPLEMENTED
**Summary:** P029 false positives on Sebastian Fine clean baseline (expected values 901/1001)
were caused by TOC entries "m" (1000) and "cm" (900) being included in the front-matter
Roman sequence. Added `_MAX_PLAUSIBLE_FRONTMATTER_ROMAN = 50` to exclude implausible
large-value candidates. Result: Sebastian Fine 2→0; Yin H 4th 12→12 (preserved).
**Files changed:** `src/njit_auditor/rules/pdf_roman_sequence.py`, tests, evaluation docs.
**Risk:** Low — only excludes candidates with Roman value > 50; all real front-matter sequences unaffected.

### Bundle 11: Reporting triage (P011/P012/P013/P026) — DONE

**Summary:** High-volume rules now have dedicated JSON triage rollups and Markdown triage
sections while preserving raw findings (P012 added for embedded annotations/comments).
Canonical five-PDF rerun:
`data/evaluation/generated/current_auditor_after_p034_p011_triage/` (gitignored).
See `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md`.

---

### P040 at a glance

| Item | Notes |
|------|--------|
| Scope | LoF entry terminal punctuation: entries must end with `.`, `?`, or `!` |
| Gate | Only entries with `page_number_token is not None` (complete entries / last wrapped line) |
| Pages checked | LIST OF FIGURES only; TOC and LoT excluded |
| Issue types | `lof_entry_missing_terminal_punctuation` |
| v1 skips | Wrap-continuation lines; entries shorter than 10 characters |
| Current-dataset eval | **Not run** — evaluation PDFs unavailable; see `docs/evaluation/p040_lof_terminal_punctuation_synthetic_validation.md` |

### P054 at a glance

| Item | Notes |
|------|--------|
| Scope | TOC entry terminal-period check: complete entries must NOT end with `.` (symmetric to P053) |
| Gate | Only entries with `page_number_token is not None`; ≥2 entries on page; entry text ≥10 chars after stripping |
| Pages checked | TABLE OF CONTENTS only; LoT and LoF excluded |
| Issue types | `toc_entry_has_terminal_period` |
| v1 skips | Wrap-continuation lines (no page_number_token); short entries; sparse pages; ALL-CAPS ≤4-word headings (filtered by shared infrastructure) |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible; see `docs/evaluation/p054_current_dataset_evaluation.md` |

### P056 at a glance

| Item | Notes |
|------|--------|
| Scope | LoT/LoF entry numbering format consistency: emits advisory when section mixes chapter-based (X.Y) and sequential (N) numbering (Q063/Q072 extension) |
| Gate | Only entries with `page_number_token is not None`; entry text ≥10 chars; ≥2 entries of each format type required before flagging |
| Pages checked | LIST OF TABLES and LIST OF FIGURES only; TOC excluded |
| Issue types | `lot_mixed_numbering_format`, `lof_mixed_numbering_format` |
| v1 skips | Wrap-continuation lines (no page_number_token); short entries; letter-prefixed entries (e.g. "Table A.1"); sections with < 2 of each format type |
| triage_tier | `low` (advisory only) |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible; see `docs/evaluation/p056_current_dataset_evaluation.md` |

### P060 at a glance

| Item | Notes |
|------|--------|
| Scope | TOC section-number ordering check: emits warning when parseable numeric section entries in TABLE OF CONTENTS are not non-decreasing (Q056/Q057 implied) |
| Gate | Only entries with `page_number_token is not None`; entry text ≥10 chars; section number parseable (bare numeric prefix: "1", "1.1", "1.2.3"); ≥3 comparable entries; ≥2 inversions before flagging |
| Pages checked | TABLE OF CONTENTS only; LoT and LoF excluded |
| Issue types | `toc_entry_numbers_not_nondecreasing` |
| v1 skips | Word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.); wrap-continuation lines (no page_number_token); short entries; sparse pages (< 3 comparable); single-inversion pages |
| triage_tier | `medium` |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible; see `docs/evaluation/p060_current_dataset_evaluation.md` |

### P059 at a glance

| Item | Notes |
|------|--------|
| Scope | LoT/LoF entry-number ordering check: emits warning when List of Tables or List of Figures entries have entry numbers that are not non-decreasing (Q063/Q072 refinement) |
| Gate | Only entries with `page_number_token is not None`; entry text ≥10 chars; entry number parseable (numeric token after "Table"/"Figure"); ≥3 comparable entries; ≥2 inversions before flagging |
| Pages checked | LIST OF TABLES and LIST OF FIGURES only; TOC excluded |
| Issue types | `lot_entry_numbers_not_nondecreasing`, `lof_entry_numbers_not_nondecreasing` |
| v1 skips | Wrap-continuation lines (no page_number_token); short entries; appendix/letter-prefixed entries; mixed sequential+chapter-based format pages; sparse pages (< 3 comparable); single-inversion pages |
| triage_tier | `medium` |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible; see `docs/evaluation/p059_current_dataset_evaluation.md` |

### P058 at a glance

| Item | Notes |
|------|--------|
| Scope | TOC page-number ordering check: emits advisory when TABLE OF CONTENTS entries have page numbers that are not non-decreasing (Q057 refinement) |
| Gate | Only entries with `page_number_token is not None`; entry text ≥10 chars; page token must parse to a positive integer; ≥3 comparable entries; ≥2 inversions before flagging |
| Pages checked | TABLE OF CONTENTS only; LoT and LoF excluded |
| Issue types | `toc_page_numbers_not_nondecreasing` |
| v1 skips | Wrap-continuation lines (no page_number_token); short entries; non-integer page tokens (roman numerals, letter-prefixed); sparse pages (< 3 comparable); single-inversion pages |
| triage_tier | `medium` |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible |

### P057 at a glance

| Item | Notes |
|------|--------|
| Scope | LoT/LoF page-number ordering check: emits advisory when complete entries have page numbers that are not non-decreasing (Q069/Q079 refinement) |
| Gate | Only entries with `page_number_token is not None`; entry text ≥10 chars; page token must parse to a positive integer; ≥3 comparable entries; ≥2 inversions before flagging |
| Pages checked | LIST OF TABLES and LIST OF FIGURES only; TOC excluded |
| Issue types | `lot_page_numbers_not_nondecreasing`, `lof_page_numbers_not_nondecreasing` |
| v1 skips | Wrap-continuation lines (no page_number_token); short entries; non-integer page tokens (roman numerals, letter-prefixed); sparse pages (< 3 comparable); single-inversion pages |
| triage_tier | `medium` |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible; see `docs/evaluation/p057_current_dataset_evaluation.md` |

### P055 at a glance

| Item | Notes |
|------|--------|
| Scope | LoT/LoF cross-type entry check: LoT entries must start with "Table"; LoF entries must start with "Figure" (Q063/Q072 extension) |
| Gate | Only entries with `page_number_token is not None`; ≥2 entries on page; entry text ≥10 chars; prefix must match `^figure\s+\d` or `^table\s+\d` |
| Pages checked | LIST OF TABLES and LIST OF FIGURES only; TOC excluded |
| Issue types | `lot_entry_is_figure`, `lof_entry_is_table` |
| v1 skips | Wrap-continuation lines (no page_number_token); short entries; sparse pages; ambiguous prefixes |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible; see `docs/evaluation/p055_current_dataset_evaluation.md` |

### P053 at a glance

| Item | Notes |
|------|--------|
| Scope | LoT entry terminal-period check: complete entries must NOT end with `.` (symmetric to P040) |
| Gate | Only entries with `page_number_token is not None`; ≥2 entries on page; entry text ≥10 chars after stripping |
| Pages checked | LIST OF TABLES only; LoF and TOC excluded |
| Issue types | `lot_entry_has_terminal_period` |
| v1 skips | Wrap-continuation lines (no page_number_token); short entries; sparse pages |
| Current-dataset eval | **Not run** — only 4/5 evaluation PDFs directly accessible; see `docs/evaluation/p053_current_dataset_evaluation.md` |

## 6. Current Validation Status (post PR #222)

| Check | Result |
|-------|--------|
| `ruff check .` | ✅ All checks passed |
| `mypy src` | ✅ No issues in source files |
| `python -m pytest` | ✅ **889 passed** (876 pre-PR #222 + 13 new P063 synthetic tests) |

### P038 at a glance

| Item | Notes |
|------|--------|
| Scope | Front-matter required heading presence and known phrase-variant detection |
| Required headings | APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS |
| Optional headings | DEDICATION, LIST OF TABLES, LIST OF FIGURES (phrase variants checked; missing not flagged) |
| Gate condition | No findings if no front-matter headings detected (flattened-PDF guard) |
| v1 skips | Flattened/compressed PDFs; heading phrase variants not in curated map |
| Issue types | `required_heading_missing`, `heading_phrase_not_exact` |
| Current-dataset eval | **Not run** — evaluation PDFs unavailable; see `docs/evaluation/p038_current_dataset_evaluation.md` |

### P037 at a glance

| Item | Notes |
|------|--------|
| Scope | Front-matter section-anchored Roman numerals; BIOGRAPHICAL SKETCH must be iv |
| Template values | bio=iv(4), ded=v(5, optional slot), ack=vi(6), toc=vii(7), lot=viii(8) |
| Gate condition | No findings if BIOGRAPHICAL SKETCH heading absent |
| v1 skips | Pages with no confident roman_lower candidate; LOF anchor deferred |
| Issue types | `roman_bio_sketch_not_iv`, `roman_section_wrong_value` |
| Current-dataset eval | **Not run** — evaluation PDFs unavailable; see `docs/evaluation/p037_current_dataset_evaluation.md` |

### P036 at a glance

| Item | Notes |
|------|--------|
| Scope | Inter-entry spacing on TOC/LoT/LoF pages only |
| Threshold | Gap ratio `< 1.4×` local line height between distinct entries |
| v1 skips | Wrapped internal continuations (P032); sparse/ambiguous pages |
| Issue types | `toc_inter_entry_spacing_too_tight`, `lot_inter_entry_spacing_too_tight`, `lof_inter_entry_spacing_too_tight` |

### P039 at a glance

| Item | Notes |
|------|--------|
| Scope | TOC level indentation hierarchy: L2 entries indented relative to L1; L3 relative to L2 |
| Gate | Requires ≥2 child entries and both parent+child levels present on the same page |
| Pages checked | TABLE OF CONTENTS only; LoT and LoF excluded |
| Min indent delta | 6pt |
| Issue types | `toc_l2_not_indented_relative_to_l1`, `toc_l3_not_indented_relative_to_l2` |
| v1 skips | Pages with fewer than 2 child entries; pages without confirmed parent level; unnumbered TOC entries (no CHAPTER/X.Y pattern) |
| Current-dataset eval | **Not run** — evaluation PDFs unavailable; see `docs/evaluation/p039_toc_entry_hierarchy_synthetic_validation.md` |

### P035 at a glance (local four-PDF subset)

| Item | Notes |
|------|--------|
| Scope | Text-layer bodies; caption placement + centering on body pages |
| v1 skips | Image-only floats; ambiguous multi-cluster pages; same-page only |
| Subset counts | 0 / 0 / 0 / **13** (Cibaku, Yin H 2nd flat, Yin Haotian 2nd, Yin H 4th comp) |
| Issue mix | `figure_caption_not_below_body` 7; `table_caption_not_above_body` 5; `table_body_not_centered` 1 |

### P030–P034 at a glance (five-PDF canonical snapshot)

| Rule | Role | Snapshot notes |
|------|------|----------------|
| P030 | TOC/LoT/LoF continued headings | 3 findings (Yin H 4th only) |
| P031 | LoT/LoF column headers | 0 after PR #55 header-band fix |
| P032 | Wrapped entry internal spacing | 0 after PR #59 split page-number guard |
| P033 | Cross-page title consistency | 0; comparison on 2/5 files |
| P034 | Copyright page | 0 after PR #67 middle-initial tolerance |

### P061 at a glance

| Item | Notes |
|------|--------|
| Scope | Cross-page LoT/LoF entry-number ordering across consecutive same-type page runs |
| Gate | ≥2 consecutive pages; ≥3 combined comparable entries; ≥2 inversions; mixed sequential+chapter-based runs skipped |
| Issue types | `lot_cross_page_entry_numbers_not_nondecreasing`, `lof_cross_page_entry_numbers_not_nondecreasing` |
| Formal current-dataset eval | **0** findings on five PDFs (PR #204); sparse comparable entries on evaluation PDFs — does not prove compliance |
| Design / eval docs | `docs/planning/p061_scope_and_design.md`, `docs/evaluation/p061_current_dataset_evaluation.md` |

**New documentation (PR #216):**

- `docs/web_ui_manual_qa_checklist.md` — Manual browser QA checklist for the current PDF-only web UI, downloads, PDF routes, parity checks, and known limitations
- `docs/planning/synthetic_web_demo_fixtures.md` — Plan for safe demo fixtures in `tests/fixtures/web_demo/`; privacy policy; acceptance criteria for future fixture implementation PR

**Next recommended work (after PR #216):**

| Priority | Task | Rationale |
|----------|------|-----------|
| 🟡 High | Maintain synthetic demo fixtures (`tests/fixtures/web_demo/`) | Use `clean_minimal.pdf` and `issues_pdf.pdf` for public web demos; keep TeX/ZIP fixtures only for CLI/internal source-audit coverage |
| 🟡 High | Full web smoke / manual QA using committed fixtures | Execute `docs/web_ui_manual_qa_checklist.md` with synthetic PDF fixtures; verify upload, result, problem-page, PDF-route, and mobile/desktop parity behavior |
| 🟡 Med | Add Playwright/Selenium or lightweight browser smoke tests (optional) | Automate key checklist scenarios end-to-end; complement the existing `TestClient`-based tests |
| 🟡 Med | Create screenshots/demo documentation from synthetic fixtures only | No private dissertation content; use `tests/fixtures/web_demo/` once implemented; add a web UI demo section to README |
| 🟡 Med | Maintain the five-PDF P001–P068 aggregate snapshot | Re-run the full five-PDF aggregate only when detector behavior changes; keep `00b9c2d` as the historical pre-P035 baseline and `5d8ebaf` as the current post-P068 aggregate baseline |
| 🟡 Med | Improve LoT/LoF entry extraction recall | P059/P060/P061 share sparse comparable-entry signal on compressed PDFs; P061 formal eval found 0 comparable entries on Yin H 4th multi-page LoF run |
| ✅ Done | **P069 front-matter heading gate recall** | Implemented — shared resolver wired into P041, P044–P047, P065–P068; see current-dataset eval doc |
| ✅ Done | **P070 TOC/LoT/LoF entry parser recall** | Implemented — shared `extract_toc_entry_lines()` refinement; synthetic validation complete; five-PDF parser-reach eval pending |
| 🟡 Med | Shared P059/P060/P061 extraction diagnostics | Subsumed by P070 scope — parser reach eval planned post-implementation |
| 🟡 Med | Extend P035 to image-heavy pages | Reduce skipped figure/table pages caused by text-layer-only detection |
| 🟡 Med | Expand EF overlap on extractable PDFs only | Improve actionability without committing raw generated outputs |
| 🟡 Low | Optional server-side filter/search endpoint | HTMX or JSON endpoint; complement to existing client-side filters |
| 🟡 Low | Optional PDF page preview / annotation overlay | Phase 4+ in GUI roadmap; privacy-safe geometry markers only |
| 🟡 Low | Optional public deployment hardening | Reverse proxy, TLS, authentication, rate limiting; document in `docs/web_gui_mvp.md` |
| 🟡 Low | Optional synthetic demo dataset | Committed synthetic PDF/TeX with known-bad formatting for live demo |
| 🟡 Low | Sanitizer key-list maintenance | If future source rules add private fields, update `_UNSAFE_SOURCE_DETAIL_KEYS` in `report_outputs.py` |
| 🟢 Done | P062 TOC cross-page ordering | Implemented in PR #220 — see `docs/planning/p062_scope_and_design.md` |
| 🟢 Done | P063 appendix body heading labels | Implemented in PR #222 — body-page companion to P042 (TOC-side); Q058/Q059 extension; see `src/njit_auditor/rules/pdf_appendix_body_headings.py` |

Do **not** treat the local four-PDF P035 subset (+13) as an updated canonical grand total.
P061 formal local subset: **0** findings. Most P036–P060 per-rule current-dataset audits remain not run.
Full pre-P035 five-PDF aggregate evaluation remains at
`docs/evaluation/current_auditor_after_p034_evaluation.md` (1,446 findings).

---

## 7. Remaining Caveats (post PR #215)

| Caveat | Notes |
|--------|-------|
| No LaTeX compilation | TeX/ZIP audits run P001–P010 source checks only; compiled PDF output is not generated |
| Optional tools depend on local install | `chktex` and `lacheck` (P009/P010) require the respective binaries to be installed and reachable on `PATH`; gracefully skipped if absent |
| No PDF annotation overlays | Finding markers on PDF page images are not yet implemented (GUI Phase 4+) |
| No authentication or rate limiting by default | The web app binds to `0.0.0.0` by default; public deployments require a reverse proxy, TLS, authentication, and rate limiting |
| In-memory job state lost on restart | Job records exist only in-process; a server restart clears the job list; on-disk files remain until TTL cleanup |
| Sanitizer key list requires maintenance | `_UNSAFE_SOURCE_DETAIL_KEYS` in `report_outputs.py` must be updated if future source rules (P001–P010 scope) add new private-content detail fields |
| Web exports are privacy-reduced, not fully anonymized | `sanitize_report_for_web_export()` removes known private keys and replaces source messages for P001–P010; it does not guarantee perfect anonymization of all possible future field values |
| CLI behavior unchanged by web sanitizer | `sanitize_report_for_web_export()` is applied only on the web JSON/Markdown download path; CLI `--json-out` / `--md-out` output is not sanitized |
| Local/runtime processing only | No external API calls during audit by default; URL fetch (`POST /audits/url`) is the sole optional network operation and is SSRF-guarded |
