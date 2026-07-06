# Open PR Triage (2026-07-05, #16: unambiguous Ester-consistency wording fixes)

> **Canonical open-PR index.** Pair with
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md).

**Baseline inspected:** `main` @ `69ef2f7184965045d0f4fd4c08c989fd60429269`. Short SHA: `69ef2f7`.  
**Live server:** serving `c0d1199` — **untouched**.  
**Open PR count:** **0** until unambiguous Ester-consistency PR merges.

## What happened in this pass (2026-07-05, #16)

Narrow wording/catalog fixes aligned with existing Ester source data and implemented behavior — no detector, threshold, or deployment changes.

| Item | Detail |
|---|---|
| **Branch** | `fix/unambiguous-ester-consistency` |
| **Fixed** | P037 catalog/README (dynamic LoT after TOC, Q060); P019 catalog + `_RULE_FALLBACKS` (remove internal candidate language); `ester_rule_consistency_audit.py` matrix path + JSON fallback |
| **Deferred** | P011 remediation/thresholds; P013/P019 hiding; P021/P026; umbrella cards; P035; P068; references citation-style |
| **Tests** | `test_ester_unambiguous_wording_fixes.py` + audit-script loader tests (**2601 pytest** total) |
| **Esther email/packet** | Not prepared |
| **Live deployment** | Untouched |

### Branches retained (4 — unchanged)

| Branch | Recommendation |
|---|---|
| `fix/confidence-grouping-sorting` | Cherry-pick later — broadest WIP tip |
| `fix/p015-equation-continuation-indent` | Cherry-pick later |
| `fix/p035-table-centering-presentation` | Cherry-pick later |
| `fix/page-numbering-false-positives` | Cherry-pick later — aligns with P013/P019 audit findings |

## Historical — what happened in the previous pass (2026-07-05, #15)

Ester source-of-truth consistency audit (docs-only).

**Baseline inspected:** `main` @ `668aa1bf265ca4fdff74c4ddd59e0b145d9c2300`. Short SHA: `668aa1b`.  
**Live server:** serving `c0d1199` — untouched (may lag `main`).  
**Open PR count:** **0** (Ester audit docs PR #469 merged).

| Item | Detail |
|---|---|
| **New doc** | [ester_source_consistency_audit_current.md](ester_source_consistency_audit_current.md) |
| **Sources used** | `260330_YESNO_audit_logic_matrix.xlsx`, `ester_q_matrix.json`, `ester_p_rule_feedback.json`, prior Ester status audits, `ester_feedback_examples.json`, implementation/wording layers |
| **Sources missing** | Live Google Sheet, Gmail threads, `results/ester_feedback_raw/formatting_rules.xlsx` |
| **Focus areas** | P011 post–PR #467, page numbering (P013/P019/P037), broad-rule presentation, P021/P026 policy, references, P068, P035 |
| **Top findings** | P021/P026 policy conflicts; P013 noise; umbrella cards; P011 pt-level strictness; references citation-style gap |
| **Live deployment** | Untouched |

### Branches retained (4 — unchanged)

| Branch | Recommendation |
|---|---|
| `fix/confidence-grouping-sorting` | Cherry-pick later — broadest WIP tip |
| `fix/p015-equation-continuation-indent` | Cherry-pick later |
| `fix/p035-table-centering-presentation` | Cherry-pick later |
| `fix/page-numbering-false-positives` | Cherry-pick later — aligns with P013/P019 audit findings |

## Historical — what happened in the previous pass (2026-07-05, #14)

Isolated P011 presentation work from retained `fix/p011-margin-warning-presentation`.

**Baseline inspected:** `main` @ `454fd13dee5a453b8216261b6361c10c00943ace`. Short SHA: `454fd13`.  
**Live server:** serving `c0d1199` — untouched in this pass.  
**Open PR count:** **0** (P011 presentation PR #467 merged).

| Item | Detail |
|---|---|
| **Branch inspected** | `fix/p011-margin-warning-presentation` — 12 unique commits, 39 files in full diff |
| **P011-relevant commits** | `4c8c541` + `adbb034`; rest stacked Jun-2026 WIP |
| **Narrow slice merged** | PR [#467](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/467) |
| **Old branch action** | **Deleted** `fix/p011-margin-warning-presentation` |

### Branches retained after #14 (4)

| Branch | Recommendation |
|---|---|
| `fix/confidence-grouping-sorting` | Cherry-pick later |
| `fix/p015-equation-continuation-indent` | Cherry-pick later |
| `fix/p035-table-centering-presentation` | Cherry-pick later |
| `fix/page-numbering-false-positives` | Cherry-pick later |

## Historical — what happened in the previous pass (2026-07-05, #13)

Finalized the retained docs-only branch `docs/pdf-finding-location-clarity-audit`.

- **Inspection:** 1 unique commit; single file `docs/planning/pdf_finding_location_clarity_audit.md`
  (341 lines); docs-only; no private PDFs, raw guidelines, or sensitive content.
- **Verdict:** **Still useful** as historical planning reference — rule-by-rule privacy matrix and
  Phase 2 detector-metadata gaps remain relevant. Phase 1 pipeline/UI statements are baseline
  (2026-06-15); subsequent PR #326+ location-label work largely implemented that phase.
- **Action:** imported to `main` with a historical header note; merged via docs-only PR; deleted
  remote branch `docs/pdf-finding-location-clarity-audit`.
- **Remote branches remaining:** **6** (all stacked Jun-2026 `fix/*` detector WIP — unchanged).
- **Live deployment:** untouched.

### Branches retained (6 — detector WIP, unchanged)

| Branch | Risk | Recommendation |
|---|---|---|
| `fix/confidence-grouping-sorting` | High | Cherry-pick later — broadest WIP tip |
| `fix/p011-margin-warning-presentation` | High | Cherry-pick later — P011 presentation |
| `fix/p015-equation-continuation-indent` | High | Cherry-pick later — P015 policy-sensitive |
| `fix/p035-table-centering-presentation` | High | Cherry-pick later — P035 presentation |
| `fix/p068-approval-page-thesis-advisor` | High | Cherry-pick later — P068 Thesis Advisor |
| `fix/page-numbering-false-positives` | High | Cherry-pick later — P013/P019/P037 FP bundle |

## Historical — what happened in the previous pass (2026-07-05, #11)

Triage of the **13** remote branches retained after the #10 cleanup. **6** were deleted as clearly
superseded; **7** remain for future narrow work or docs import.

### Branches deleted in this pass (6 — superseded by current `main`)

| Branch | Unique commits | Verdict | Action |
|---|---|---|---|
| `feature/example-thesis-url` | 1 | **Superseded** — closed PR #305; example NJIT thesis URL UI already on `main` (`index.html`); branch also predates PDF-only public UI | **Deleted** |
| `implement-frontmatter-no-visible-page-number` | 1 | **Superseded** — early P022 implementation; P022 fully present and evolved on `main` (`pdf_frontmatter_no_page_number.py`) | **Deleted** |
| `phase2-pdf-apa-title-capitalization` | 1 | **Superseded** — early P020; `pdf_title_capitalization.py` on `main` is substantially newer | **Deleted** |
| `refine-p020-font-size-fallback` | 1 | **Superseded** — P020 font-size fallback refinements absorbed/evolved on `main` | **Deleted** |
| `phase1-tex-source-auditor` | 2 | **Superseded** — early TeX auditor MVP (May 2025); full P001–P010 TeX surface on `main` | **Deleted** |
| `organize-ester-materials` | 1 | **Superseded** — early Ester import/rule-loader prototype; `rule_loader.py` and current `data/raw/ester/` layout on `main` | **Deleted** |

### Branches retained (7)

| Branch | Unique commits | File areas | Risk | Recommendation | Action |
|---|---|---|---|---|---|
| `docs/pdf-finding-location-clarity-audit` | 1 | `docs/planning/pdf_finding_location_clarity_audit.md` only | **Low** | **Future docs PR** — planning audit not on `main`; no detector/UI impact | **Retained** |
| `fix/confidence-grouping-sorting` | 16 | 13 detector rules, UI (`web_app`, templates), 21 tests, presentation helpers | **High** | **Keep + cherry-pick later** — stacked Jun-2026 WIP tip; includes confidence grouping/sorting plus P011/P015/P035/P068/P013 changes; conflicts with post-cleanup UI; do not merge whole branch | **Retained** |
| `fix/p011-margin-warning-presentation` | 12 | 9 detector rules, UI, 13 tests | **High** | **Keep + cherry-pick later** — P011 margin wording/highlights/confidence + related stack commits; subset of confidence-grouping branch | **Retained** |
| `fix/p015-equation-continuation-indent` | 15 | 13 detector rules, UI, 19 tests | **High** | **Keep + cherry-pick later** — P015 post-equation indent suppression; detector threshold/policy change needs explicit approval | **Retained** |
| `fix/p035-table-centering-presentation` | 10 | 8 detector rules, UI, 9 tests | **High** | **Keep + cherry-pick later** — P035 table-centering highlight/remediation presentation; rebase against current highlight/UI stack first | **Retained** |
| `fix/p068-approval-page-thesis-advisor` | 14 | 13 detector rules incl. P068, UI, 18 tests | **High** | **Keep + cherry-pick later** — “Thesis Advisor” recognition not present on `main`; useful but needs isolated PR + eval | **Retained** |
| `fix/page-numbering-false-positives` | 13 | 12 detector rules (P013/P019/P037), UI, 14 tests | **High** | **Keep + cherry-pick later** — page-number FP suppression bundle; detector-policy sensitive | **Retained** |

**Stack note:** the six `fix/*` branches share a common 2026-06-30 WIP stack (`fix/p035-*` is an ancestor of several others; `fix/confidence-grouping-sorting` is the broadest tip). Treat as **one forked effort**, not six independent merge candidates.

- **Live deployment:** untouched (no systemd restart).
- **Open PR count:** still **0**.

## Historical — what happened in the previous pass (2026-07-05, #10)

Safe stale remote-branch cleanup after help/docs deploy (#462 live at `bdfbbc4`).

- **Inspected:** 102 remote branches (excluding `origin/main`).
- **Deleted:** **89** branches — each either fully merged into `origin/main`, an ancestor of
  `origin/main` (squash-merge), or the head of a **merged** GitHub PR with no open-PR conflict.
- **Retained:** **13** branches with unique commits not in `main` and/or no merged PR — manual review
  recommended before any future deletion:
  - `docs/pdf-finding-location-clarity-audit` (1 unique commit, no PR)
  - `feature/example-thesis-url` (closed PR #305, 1 unique commit)
  - `fix/confidence-grouping-sorting` (16 unique commits, no PR)
  - `fix/p011-margin-warning-presentation` (12 unique commits, no PR)
  - `fix/p015-equation-continuation-indent` (15 unique commits, no PR)
  - `fix/p035-table-centering-presentation` (10 unique commits, no PR)
  - `fix/p068-approval-page-thesis-advisor` (14 unique commits, no PR)
  - `fix/page-numbering-false-positives` (13 unique commits, no PR)
  - `implement-frontmatter-no-visible-page-number` (1 unique commit, no PR)
  - `organize-ester-materials` (1 unique commit, no PR)
  - `phase1-tex-source-auditor` (2 unique commits, no PR)
  - `phase2-pdf-apa-title-capitalization` (1 unique commit, no PR)
  - `refine-p020-font-size-fallback` (1 unique commit, no PR)
- **Not deleted:** any branch with ambiguous purpose, unique unmerged work, or possible WIP value.
- **Live deployment:** untouched in this pass (branch housekeeping + docs only).
- **Open PR count:** still **0**.

## Historical — what happened in the previous pass (2026-07-05, #9)

Final health/status-consistency pass after the full cleanup cycle (#375–#376, #459–#460, live deploy).

- **GitHub:** `gh pr list --state open` → 0 open PRs; `git fetch --prune` removed stale remote heads
  for already-deleted merged branches (e.g. `fix/p014-frontmatter-centering-false-positive`,
  `refactor/simplify-individual-findings-table`, `docs/fix-clean-minimal-demo-baseline`).
- **Live deployment:** confirmed `GET /version` → `cd2771a` on localhost and LAN; systemd service
  `thesis-auditor-web.service` active; sample audit smoke-test passes current UI structure.
- **Docs updated:** canonical status entries now record live SHA, zero open PRs, and current report
  flow (no Most common issues, no grouped/individual toggle, no Severity filter/column in main
  findings, compact cards, Advanced sections collapsed after Downloads).
- **Validation on `cd2771a`:** ruff/mypy/pytest green (**2585 passed**).
- No code/detector/UI changes in this pass; no live restart (already current).

## Historical — what happened in the previous pass (2026-07-05, #8)

Reviewed, rebased, and merged **#376** (`Fix P014 frontmatter heading centering false positive`):
narrow P014 detector fix for asymmetric NJIT margins.

- **Root cause:** `_line_centering()` compared heading center only against the text-area midpoint.
  With 1.5" left / 1" right margins, page center and text-area center differ by 18pt on letter
  paper — visually page-centered front-matter headings (e.g. `BIOGRAPHICAL SKETCH`) could fail
  even when centered on the page face.
- **Fix:** accept either text-area center **or** physical page center when within the existing
  18pt/26pt tolerances (`CENTER_TOLERANCE_PT` / `BORDERLINE_CENTER_TOLERANCE_PT` unchanged).
  `page_width` passed only from P014 front-matter heading paths (`pdf_headings.py`,
  `pdf_frontmatter_heading_gate.py`).
- **Diff scope (3 files, +104/−6):** `pdf_headings.py`, `pdf_frontmatter_heading_gate.py`,
  `tests/test_web_audit_warning_fixes_batch3.py`. No rule-ID/threshold/UI/export/grouping changes.
- **Prior CI failure (historical):** stale branch ~122 commits behind `main`; fresh CI after
  cherry-pick onto `1b6f8d5` — all matrix jobs passed.
- **Rebase:** cherry-picked onto `origin/main` @ `1b6f8d5` (LFS smudge-filter artifact blocked
  `git rebase` in worktrees); force-pushed to PR branch.
- **Regression tests added:** page-centered `BIOGRAPHICAL SKETCH` geometry passes; flush-left still
  warns; optional live-sample skip-if-missing test preserved.
- **Validation:** `ruff check .` — passed; `mypy src` — no issues in 105 files; `python -m pytest`
  — **2585 passed** locally; GitHub CI — passed (3.10/3.11/3.12).
- Merged with squash (`72b8736`); deleted remote branch `fix/p014-frontmatter-centering-false-positive`.
- No live deployment/systemd action taken in this pass.

## Historical — what happened in the previous pass (2026-07-05, #7)

Re-triaged **#375** per explicit instruction. **No merge, rebase, or close action was needed** — the
PR was already squash-merged to `main` on 2026-07-05 (`d89f4cef082bafc71a0e8dcb18fc37f05e53fed8`).

- **Confirmed on current `main`:** all five #375 files/changes are present, including
  `test_clean_minimal_pdf_produces_expected_residual_findings` and updated
  `docs/planning/synthetic_web_demo_fixtures.md` §3.1 (residual P011/P013/P027 outputs, not
  zero-finding baseline).
- **Still useful / not superseded:** documentation and test alignment remain correct; later #459/#460
  UI work did not replace this demo-fixture baseline cleanup.
- **Prior CI failure (historical):** stale branch ~122 commits behind `main`; not a defect in the
  narrow docs/test diff (original 2026-06-26 CI logs expired).
- **Validation re-run on `b6cc8db`:** `ruff check .` — passed; `mypy src` — no issues in 105 files;
  `test_clean_minimal_pdf_produces_expected_residual_findings` — passed.
- **#376** left open and untouched.
- No live deployment/systemd action taken in this pass.

## Historical — what happened in the previous pass (2026-07-05, #6)

Reviewed and merged **#375** (`Align clean_minimal demo fixture docs with actual audit output`):
docs/test-only cleanup aligning `clean_minimal.pdf` documentation and smoke-test expectations with
the fixture's actual residual audit outputs (P011/P013/P027), not a zero-finding baseline.

- **Still needed:** `main` still described `clean_minimal.pdf` as "passes all checks" / zero findings
  in `docs/planning/synthetic_web_demo_fixtures.md` §3.1; not superseded by later demo/status work.
- **Diff scope (5 files, +44/−14):** `README.md`, `docs/planning/synthetic_web_demo_fixtures.md`,
  `docs/web_ui_demo_guide.md`, `scripts/web_demo_smoke.sh`, `tests/test_web_demo_fixtures.py` (new
  `test_clean_minimal_pdf_produces_expected_residual_findings`). No detector/rule/threshold/UI/export
  changes; no PDF/binary/LFS fixture changes.
- **Prior CI failure root cause:** branch was stale (~122 commits behind `main` at rebase time;
  original CI logs from 2026-06-26 have expired). Failure was almost certainly stale-base drift, not
  a defect in the PR's narrow docs/test diff.
- **Rebase:** `git rebase` blocked by the repo-wide git-LFS smudge-filter artifact (pointer/binary
  mismatch on `data/raw/**` and `tests/fixtures/web_demo/**`, present in every worktree checked,
  unrelated to this PR). Worked around by cherry-picking the PR's single commit onto `origin/main` @
  `95e3aa5` — applied cleanly with zero conflicts; force-pushed to the PR branch.
- **Validation:** `ruff check .` — passed; `mypy src` — no issues in 105 files; `python -m pytest` —
  **2580 passed** (2579 pre-merge + 1 new fixture test).
- Merged with squash (`d89f4ce`); deleted the remote branch `docs/fix-clean-minimal-demo-baseline`.
- No live deployment/systemd action taken in this pass.
- **#376** left open and untouched.

## Historical — what happened in the previous pass (2026-07-05, #5)

Inspected **#437** (`fix: polish P011 margin warning evidence`) against the task's evidence/visual
scope: separates non-adjacent same-side margin violations into distinct tight highlight boxes
(instead of one union spanning unrelated clean content between them), adds a thin
`margin_boundary_bbox` guide rectangle at the exact required margin line, adds a per-side breakdown
to the mixed-side rollup comment, and states the margin rule is strict ("even by a small amount")
in the single-side comment. Confirmed via diff: `OVERFLOW_TOLERANCE_PT`, `ARTIFACT_GUARD_*`, all
four margin-boundary constants, rule ID, issue type, confidence logic, and sorting are byte-for-byte
unchanged — only new additive `details` keys (`highlight_bboxes`, `margin_boundary_bbox`) alongside
the untouched `bbox` union fallback, plus wording/highlight-selection changes in the presentation
layer.

- **Rebase:** the PR branch (`fix/p011-margin-visual-polish`, head `d5a3f21`) was based on `main` @
  `07db2fa`, ~22 commits behind the current tip — two of the PR's files
  (`highlight_targeting.py`, `polished_comments.py`) had also changed on `main` since (unrelated
  regions: a whole-word-match helper and a P016 wording fix, respectively). `git rebase` was blocked
  by a pre-existing, repo-wide git-LFS smudge-filter artifact affecting `data/raw/**` and
  `tests/fixtures/web_demo/**` (pointer/binary mismatch present in every worktree checked, not
  caused by this review and never intended to be committed) — worked around by branching directly
  from `origin/main` and `git cherry-pick`-ing the PR's single commit instead of `git rebase`.
  Applied cleanly with zero conflicts; resulting diff stat identical to the original PR (8 files,
  +551/−44). Force-pushed to the PR branch (explicitly authorized by the task's own
  "Rebase/update #437 onto latest origin/main if needed" instruction).
- **Regression coverage confirmed:** the PR's 8 new tests (`tests/test_p011_margin_visual_polish.py`)
  cover small-overflow-still-flags, single-line precision preserved, non-adjacent
  left/right-margin lines drawn as separate boxes, adjacent lines merged without extra content, a
  horizontal top-margin guide, a mixed top+right rolled-up card with per-side detail and 4 separate
  boxes reaching the highlight layer, and strict wording without downgrading. Two existing
  `tests/test_highlight_target_baseline.py` assertions were updated from "exactly 1 box" to
  "2 boxes" (line/group box + new boundary guide) — the deliberate, documented change.
- **Manual/browser verification:** started the app on a scratch port (`127.0.0.1:8917`, not the
  live systemd service) with `PYTHONPATH` set to the review worktree. Built a synthetic PDF with two
  right-margin violations separated by 6 clean body lines and submitted it through the real
  `/audits` upload endpoint. Fetched the real `/audits/{id}/highlighted-page.pdf` output and
  rendered it to an image: the two violating lines get separate tight yellow highlight boxes, and a
  thin vertical guide line marks the right-margin boundary running between them — the clean lines in
  between are not highlighted. Confirmed the JSON export is additive (`bbox` unchanged;
  `highlight_bboxes`/`margin_boundary_bbox` new) and that original-PDF/JSON/Markdown downloads all
  return 200. Rendered the report page in headless Chromium (Playwright) at a 390px viewport: no
  horizontal overflow, P011 card renders cleanly (this PR touches zero template files — confirmed
  via `git diff -- templates`, so mobile risk was inherently low).
- **Known limitation, documented not fixed:** the non-adjacent-grouping logic uses PDF
  content-stream block/line enumeration order as a proxy for visual top-to-bottom position. This
  holds for normal born-digital dissertation PDFs (single-column, reading-order text emission) but
  is not guaranteed in general. Verified with an adversarial synthetic fixture (violating lines
  emitted out of visual order in the content stream) that the fallback in that case reproduces
  exactly the pre-PR behavior (one union box) — never worse than before, just not improved for that
  edge case. Recorded in `current_project_state_and_next_steps.md`; not a blocker.
- **Re-validated from a fresh worktree** (cherry-pick branch, then again after merge on latest
  `main`): `ruff check .` — passed; `mypy src` — no issues in 105 files; `python -m pytest` —
  **2568 passed** both before and after merge.
- No detector-threshold or policy change introduced; P021/P026 untouched; P084 not started; no
  template/CSS files touched.
- Merged with squash (`d883e9e`); deleted the remote branch `fix/p011-margin-visual-polish`.
- No live deployment/systemd action taken in this pass.

## Historical — what happened in the previous pass (2026-07-05, #4)

Inspected **#436** (`fix: highlight affected list entries for punctuation warnings`) against the
task's evidence/highlight-only scope for P040/P053/P054 and confirmed it was already merged to
`main` (squash-merge `5c37a11`, merged by `SoroushVahidi`) with the remote branch already deleted —
no further merge action was needed. Re-verified the merged diff and re-ran full validation from a
clean worktree to confirm the merge was safe:

- **Diff scope (6 files, +205/−51):** `pdf_lof_terminal_punctuation.py`, `pdf_lot_terminal_period.py`,
  `pdf_toc_terminal_period.py` each gained exactly one behavior: `details["bbox"] =
  format_bbox_detail(entry.line.bbox)` (P040 also gained `details["page_type"] =
  "list_of_figures"`). No condition, threshold, rule ID, issue type, grouping key, confidence
  label, sorting, or export-schema change anywhere in the diff. `tests/test_pdf_rules.py` (+150/−4)
  and two `docs/status/*` files (`ester_current_consistency_audit.md`,
  `highlight_quality_improvement_plan.md`, both already correctly updated) round out the diff.
- **Regression coverage confirmed:** new tests assert (a) each rule's finding now carries a `bbox`
  that resolves to a visible highlight via `has_visible_highlight`; (b) only the truly offending
  entry is flagged on a mixed-content page, not neighboring clean entries; (c) P040's location
  label now reads "List of Figures" instead of the generic "list" fallback; (d) rule ID, issue
  type, and finding counts are unchanged by the fix. Existing privacy tests
  (`test_p040_findings_metadata_no_private_content`, `test_p053_finding_metadata_privacy_safe`)
  were updated only to allow `page_type`'s category-label value (not entry text) through the
  no-entry-text-leak assertion.
- **Re-validated from a fresh worktree** (not the shared `main` checkout, which had unrelated
  in-progress uncommitted changes from other work — left untouched): `ruff check .` passed; `mypy
  src` — no issues in 105 files; `python -m pytest` — **2557 passed** (2550 at `013c836` + 7 new
  P040/P053/P054 tests).
- No detector-threshold or policy change introduced; P021/P026 untouched; P084 not started.
- No live deployment/systemd action taken in this pass.

## Historical — what happened in the previous pass (2026-07-05, #3)

Reviewed and merged **#454** (`refactor: simplify findings filters and default to page order`),
opened earlier this same pass: removed the student-facing **Severity** filter dropdown from the
Findings control bar (redundant with the per-card status badge; most findings are review signals,
not confirmed defects) and made **page order** the default grouped-problem sort (earliest affected
page; matches front-to-back dissertation review instead of arbitrary insertion order). Renamed the
sort dropdown's default option from "Default order" to "Page order," folding the now-redundant
standalone `page_order` option into it (`?sort=page_order` still resolves identically).

- Confirmed the diff was narrow and presentation-only: 7 files (`report_view.py`,
  `templates/job.html`, `web_app.py`, 4 test files), no `src/njit_auditor/rules/*.py` touched, no
  rule-ID/threshold/grouping-key/confidence-logic/export changes.
- Confirmed no unused JS, empty layout columns, or stale context variables were left behind: the
  `filter-severity` JS filtering branches, `data-severity` dataset attributes, and the
  `filter_severities` web_app.py context variable were all removed together with the dropdown.
- Confirmed severity badges (Fail/Review/Info) still render on grouped-problem cards via a new
  regression test (`test_grouped_problem_cards_still_show_severity_badge`).
- Confirmed origin/main had not moved since the PR was branched (`b3e7ae1`, unchanged) — no rebase
  needed.
- Manually verified mobile behavior: started the app locally on a scratch port with `PYTHONPATH`
  exported first (this repo's shared venv otherwise silently resolves `njit_auditor` from a
  different worktree — caught and corrected this exact issue mid-pass), ran a real audit against
  `tests/fixtures/web_demo/issues_pdf.pdf`, and inspected the rendered page in headless Chromium at
  390px width: filter bar height dropped from ~304px to ~243px, no horizontal overflow
  (`scrollWidth == clientWidth == 390`), "Page order" selected by default, severity badge still
  visible on cards.
- **Also, separately, an accidental shared-resource side effect was caught and reverted:** running
  `pip install -e ".[dev]"` (the first step of this repo's default validation workflow) inside this
  feature worktree repointed the **shared** modal-venv's editable install
  (`__editable__.njit_thesis_auditor-0.1.0.pth`) from `main/src` to this worktree's `src` — which
  would have silently broken every other worktree/session relying on that shared venv. Reverted the
  `.pth` file back to `main/src` immediately; all subsequent validation in this pass used an
  explicit `PYTHONPATH` export instead of relying on the shared editable install.
- Merged with squash (`013c836`); deleted the remote branch
  `refactor/findings-controls-page-order`.

Validation on the merged commit (`013c836`): `ruff check .` — passed; `mypy src` — no issues in
105 files; `python -m pytest` — **2550 passed**.

**No live deployment change** — the live server remains on pre-`a5f6c74` code; a future deploy pass
will pick up `013c836`.

---

## Historical — 2026-07-05, #2 (#440 P016/P023 non-body-spacing fix reviewed and merged)

> **Superseded** by the section above. Preserved here for historical context only.

**Baseline inspected:** `main` @ `a5f6c7428f5de1b6afb8311f737a0b9de691bd3f` (merge of PR
[#440](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/440)). Short SHA: `a5f6c74`.  
**Live server:** still serving `55149ac` (unchanged — this pass did not touch the live
deployment/systemd service; `a5f6c74` is not yet deployed)  
**Open PR count:** **4** (2 detector-behavior fixes awaiting human/Ester review, 2 stale/CI-failing
needing a fresh rebase before any merge decision)

## What happened in this pass (2026-07-05, #2)

Reviewed, rebased, and merged **#440** (`fix(P016,P023): stop flagging non-body content as body
spacing`) after manual review found P016/P023 treating non-body content (front-matter template
layout, table cells, references entries) as ordinary body text:

- **P016** (`pdf_spacing.py`): skips `BIOGRAPHICAL SKETCH`/`APPROVAL PAGE` pages (special-layout
  front-matter templates whose large author/degree/date or committee-signature gaps are
  intentional) from the ordinary heading-blank-gap/paragraph-gap checks. Corrected student-facing
  wording from "before a heading" to "after a heading" in `polished_comments.py`,
  `finding_explanations.py`, and `issue_type_explanations.py` (the detector always measured the
  gap *after* the heading; only the wording was wrong). `ABSTRACT`/`ACKNOWLEDGEMENTS` pages remain
  fully checked — this rule is scoped to front matter only, and the exclusion only covers the two
  pages with a genuinely different, intentional template layout.
- **P023** (`pdf_body_spacing.py`): excludes captioned table regions (a new caption-anchored
  band — reuses the existing `detect_caption_lines()` utility — spanning the caption plus the
  contiguous run of tightly packed rows) and the entire References/Bibliography section including
  continuation pages that don't repeat the heading (via a new public
  `references_section_page_numbers()` helper in `pdf_references_citations_structural.py`, purely
  additive, reuses existing private heading-localization logic). Findings now carry a `bbox`
  covering the measured body-text region plus `measured_body_line_count`/`measured_gap_count`
  detail fields, so evidence points at the actual measured lines.
- Verified narrow scope directly from the diff: no rule IDs changed, no existing threshold
  constants modified (only two new constants added for table-band detection), no grouping/
  sorting/confidence/export code touched (`report_view.py`, `web_app.py`, `report_outputs.py` not
  in the diff). Table detection uses real table captions only (not figure captions), so
  figure-caption pages are unaffected. Confirmed empirically that table borders (graphic strokes)
  were never part of the text-line measurement in the first place — nothing to fix there
  structurally, but the new tests assert it explicitly.
- Rebased cleanly from its original base (`c8a1043`, ~40 commits behind) onto `main` @ `5835ca6`
  with zero conflicts; force-pushed the rebase to the PR branch.
- All 7 of the PR's new regression tests pass (biosketch/approval P016 suppression, after-heading
  wording + position detail, table-only suppression, table borders as non-evidence, table+body
  measuring only the body region, references continuation-page suppression) alongside the full
  2542-test baseline (2549 total).
- Merged with squash (`a5f6c74`) and deleted the remote branch
  `fix/p016-p023-nonbody-spacing`. (A local, non-rebased copy of this branch remains checked out
  in an unrelated pre-existing worktree, `wt-spacing`, on the host — left untouched; deleting the
  remote branch does not affect it.)

Validation on the merged commit (`a5f6c74`): `ruff check .` — passed; `mypy src` — no issues in
105 files; `python -m pytest` — **2549 passed**.

**No live deployment change** — the live server remains on `55149ac`; a future deploy pass will
pick up `a5f6c74`.

---

## Previous pass (2026-07-05, #1) — #439/#435 branches deleted; live server confirmed at 55149ac

Narrow docs/branch cleanup pass — no code or deployment changes:

- Re-confirmed #439 (`fix/p020-stat-notation-capitalization`) is **MERGED** and #435
  (`fix/titlecase-technical-notation`) is **CLOSED**, and neither branch is the head of any open
  PR (both had been left undeleted since the 2026-07-04 reconciliation pass below, pending
  explicit authorization to delete).
- **Deleted both remote branches:** `fix/p020-stat-notation-capitalization` and
  `fix/titlecase-technical-notation`.
- Confirmed the live server (systemd-supervised `thesis-auditor-web.service`) is already serving
  `55149ac` (`GET /version` on both `127.0.0.1:8000` and the LAN address) — current with `main`,
  no restart was needed or performed in this pass.
- Remaining **5 open PRs** are unchanged from the previous pass's 6 (now 5 now that #435/#439 are
  resolved): #436, #437, #440 (detector/highlight fixes awaiting human/Ester review), #375, #376
  (stale, need rebase + fresh CI before any merge decision) — see the table in the previous pass
  below, still accurate.

No `ruff`/`mypy`/`pytest` run was required for this pass beyond the docs update itself, since no
source files changed.

---

## Previous pass (2026-07-04, #2) — #435/#439 statistical-notation title-case fix reconciled

Reconciled the two overlapping statistical-notation title-case PRs flagged in the previous triage
pass. Both fixed the same `(n = 97)` false positive in `check_apa_title_case_phrase()`
(P020/P024/P027's shared helper), so they were compared empirically (a probe script run against
both branches, not just inspection) against the required-behavior list from manual review:

- Both preserve the strict `Comparison with Prior Studies` → `With` policy and still flag real
  lowercase words inside parentheses (`pilot` in `(pilot study)`).
- **#435** only exempted a single letter immediately followed by a relational operator. It still
  flagged bare abbreviations without an adjacent operator (`t` in "Test Statistic t Value", `df`
  in "Degrees of Freedom df"), and never touched the suggested-fix substring-replacement
  mechanism, so the `Linear`→`LiNear`-style corruption bug remained latent for other short flagged
  words.
- **#439** exempts a fixed statistical-abbreviation set (`n, p, r, r², b, se, sd, df, t, f, m,
  ci`) case-insensitively (correctly handles bare `t`/`df`/`SE`/`F`), makes suggested-fix
  generation token/span-safe via whole-word regex matching (verified: `LiNear` never appears),
  and adds the required P027 exact sentence-case "Change X to Y" replacement.

**Merged #439** (rebased onto `main` first). **Closed #435** as superseded, with a comment citing
the specific gaps above — no piece of #435 was worth cherry-picking separately since #439 is a
strict superset. Neither branch was deleted (not authorized this round; report branch status,
don't delete).

Validation on final `main` (`82f2d90`): `ruff check .` — passed; `mypy src` — no issues in 105
files; `python -m pytest` — **2538 passed**.

---

## Previous pass (2026-07-04, #1) — full backlog triage, stacked UI PRs #441-#444 merged, 4 stale PRs closed

**Baseline inspected then:** `main` @ `991e683e87f51b3032be0bcab71f7f611c0be394` (merge of PR
[#445](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/445), docs-only; short SHA
`991e683`)  
**Live server:** restarted and confirmed serving `991e683` via `/version` — no longer behind
`main`  
**Branch cleanup:** the 10 remote branches behind the merged/closed PRs listed below (#441–#445
merged set, #311/#349/#362/#385 closed set) have been deleted; the 7 branches for still-open PRs
were left untouched  
**Open PR count then:** **7** (5 detector-behavior fixes awaiting human/Ester review, 2
stale/CI-failing needing a fresh rebase before any merge decision)

## What happened in this pass (2026-07-04)

Full open-PR/branch backlog triage. Merged the four stacked student-facing UI PRs in dependency
order — each was rebased onto the new `main` after its predecessor merged (since each predecessor
was squash-merged, the base had to be retargeted and the branch rebased, not just fast-forwarded):

1. [#441](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/441) — declutter summary sections into root-cause cards
2. [#442](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/442) — mobile-safe findings cards
3. [#443](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/443) — simplified summary counts (Items to review / Needs fixing)
4. [#444](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/444) — simplified nav chips (Advanced details / Advanced candidates)

Also merged [#434](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/434) (docs-only repo
polish inventory).

Closed four PRs confirmed superseded by later mainline work, each with a comment citing the
specific current-`main` evidence (no branches deleted):

| PR | Why closed |
|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Sub-page location labels — `main` has since grown a far more complete per-rule location-label system (`enriched_pdf_location_label` + per-rule student-preview modules) |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | Both of its changes (AGENTS.md autonomous-policy section, Ester feedback audit doc) are already on `main`; the audit doc is marked "Historical / superseded" there |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | "Review needed:" prefix policy — `main` deliberately kept the unconditional prefix plus one global automated-review caveat instead (see #443's summary note) |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | Rule-reference card declutter — `main`'s `rules.html` cards are already simpler than what this PR proposes |

## Remaining 6 open PRs (2026-07-04, updated)

| PR | Title | Kind | CI | Verdict |
|---|---|---|---|---|
| [#436](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/436) | `fix: highlight affected list entries for punctuation warnings` | detector/highlight fix (P040/P053/P054) | passing | **Needs human/Ester review** — touches rule files |
| [#437](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/437) | `fix: polish P011 margin warning evidence` | detector/highlight fix (P011) | passing | **Needs human/Ester review** — touches rule files |
| [#440](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/440) | `fix(P016,P023): stop flagging non-body content as body spacing` | detector fix (P016/P023) | passing | **Needs human/Ester review** — touches rule files |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `Align clean_minimal demo fixture docs with actual audit output` | docs/test only | **failing** | **Stale** — needs rebase + fresh CI run before any merge decision; not clearly superseded, so left open rather than closed |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `Fix P014 frontmatter heading centering false positive` | detector fix (P014) | **failing** | **Needs human/Ester review** (detector change) **and** a rebase — CI is failing |

**#435 and #439 (statistical-notation title-case fix) — resolved this pass:** #439 merged, #435
closed as superseded. See "What happened in this pass" above.
**Update (2026-07-05, #2 pass, above):** #440 has since been reviewed, rebased, and merged
(`a5f6c74`) — the "needs human/Ester review" verdict below no longer applies to it.

**Why #436, #437, #440 weren't auto-merged despite passing CI (at the time of this pass):** all three touch
`src/njit_auditor/rules/*.py` — real detector-behavior changes (false-positive suppressions,
highlight/evidence polish), not presentation-only. This project's own culture (Ester wording/policy
review, the P021/P026 policy doc) treats any change to what gets flagged as requiring human
sign-off, not a blind agent merge, even when the fix looks correct and well-tested.

## Cleanup guardrails (unchanged)

- Do **not** start **P084**.
- Do **not** merge #436, #437, or #440 without explicit human/Ester sign-off — they change what
  gets flagged. **Update (2026-07-05, #2 pass, above):** #440 was explicitly reviewed and merged
  per direct task instruction; this bullet no longer applies to it.
- Do **not** merge #375 or #376 as-is — rebase and get a clean CI run first.
- No remote branches were deleted in this pass (merged and closed PRs' branches all still exist,
  including `fix/p020-stat-notation-capitalization` (#439, merged) and
  `fix/titlecase-technical-notation` (#435, closed) — deletion wasn't authorized this round).
  **Update (2026-07-05 pass, above):** both branches have since been deleted.

---

## Historical — 2026-07-03 (baseline `07db2fa`, PR #433 merged)

> **Superseded** by the 2026-07-04 sections above. Preserved here for historical context only.

**Baseline inspected:** `main` @ `07db2fa30b457006cf7524309c8eabcca6ff64c8` (merge of PR
[#433](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/433); short SHA `07db2fa`)  
**Live server:** last confirmed at `425f144` (PR #430) — **3 merges behind** current `main`;
confirm `GET /version` before assuming #431–#433 behavior is live  
**Open PR count:** **10** (4 new, mergeable; 6 older, paused)

## Current open PRs (2026-07-03)

| PR | Title | Kind | `mergeStateStatus` | Verdict |
|---|---|---|---|---|
| [#434](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/434) | `docs: inventory repository polish tasks` | docs-only | CLEAN | **Safe to merge first** — no code/template/test changes |
| [#435](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/435) | `fix: ignore statistical notation in title-case checks` | detector fix (P020/P024/P027 shared helper) | CLEAN | **Safe candidate** — narrow, tested false-positive fix; no threshold/rule-ID/schema change |
| [#436](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/436) | `fix: highlight affected list entries for punctuation warnings` | presentation/evidence fix (P040/P053/P054) | CLEAN | **Safe candidate** — additive `bbox` metadata only, no detector semantics change |
| [#437](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/437) | `fix: polish P011 margin warning evidence` | presentation/evidence fix (P011) | CLEAN | **Safe candidate** — additive highlight/guide metadata + wording only; thresholds/strictness unchanged |

All four are independent of each other and of the older paused PRs below — they can be reviewed
and merged in any order, though **#434 first** is lowest-risk since it touches no source files.

**Not touched by this triage refresh (policy judgment, not implementation):**

| Item | Why it's a policy question, not a PR |
|---|---|
| P021 abstract word-count limits | Ester sheet (200/400) conflicts with current detector constants (150/350) — needs a human/Ester decision, recorded in `ester_policy_review_p021_p026.md`, before any PR is opened |
| P026 accepted font families | Detector accepts more families (Latin Modern, serif aliases) than Ester's literal 3-name list — same policy-review doc, same "confirm before changing" status |

## Older open PRs — unchanged, still paused

| PR | Branch → base | Mergeable | Kind | Verdict |
|---|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | DIRTY | presentation | **Paused** — do not touch without explicit instruction |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | DIRTY | docs-only | **Paused** — do not touch without explicit instruction |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | DIRTY | wording/policy | **Paused** — open product-policy question |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | UNSTABLE | docs-only | **Paused** — do not touch without explicit instruction |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | UNSTABLE | detector fix | **Paused** — do not touch without explicit instruction |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | DIRTY | presentation | **Paused** — pending warning-legitimacy review |

These six PRs predate the current Ester wording/presentation/highlight work (PRs #411–#437) and
have not been re-triaged against the current `main`. **Do not merge, close, rebase, or delete any
of them without explicit human instruction** — several are likely stale against current `main` and
need a fresh conflict/relevance check before any action, not just a rebase.

## Current cleanup queue (recommended order)

1. **#434** (docs-only inventory) — merge first, zero behavior risk.
2. **#435, #436, #437** (independent detector/presentation fixes) — review and merge in any order;
   each has its own passing test suite and does not depend on the others.
3. **P021/P026 policy resolution** — not a PR yet; send the drafted questions in
   `ester_policy_review_p021_p026.md` to Ester/a policy owner. Only after an answer should a
   wording-or-detector PR be scoped.
4. **Older paused PRs (#311/#349/#362/#375/#376/#385)** — re-triage only after explicit human
   instruction to resume that review; expect most to need a fresh rebase/conflict check against
   `main` @ `07db2fa` given how far they now trail.
5. **P084** — remains out of scope; do not start without explicit instruction.

---

## Historical — 2026-07-02 (baseline `70dcd95`, PR #407/#408 merged)

> **Superseded** by the 2026-07-03 sections above. The "Quick verdict table" and "Recommended
> next development sequence" below reflect the 6-PR, `70dcd95`-baseline world and do **not**
> include #434–#437 — use the "Current open PRs" and "Current cleanup queue" sections above
> instead. Preserved here for historical context only.

## PR #407 and PR #408 merged (2026-07-02)

**#407** and **#408** are merged on `main` after the older PR #406 status snapshot. **PR cleanup
remains paused** — not because of detector regressions on `70dcd95`, but because a separate
warning-legitimacy review is still in progress and no human instruction has resumed open-PR
review. Do not touch #311/#349/#362/#375/#376/#385 until that review concludes (or explicit
instruction).

| PR | Summary | Regression guard |
|---|---|---|
| **#407** | Ester-reviewed warning precision: P044 continuation lines; P027 bold-heading requirement; P037 LoT Roman numeral; P011 margin overrun presentation; P024/P040 LoF presentation; P025 DC wrapper **notice** (not problem) | No threshold / rule-ID / schema changes outside scoped presentation fixes |
| **#408** | Web UI sort grouped problem cards by confidence (`?sort=`); display order only | Grouping keys, problem numbers, detector output unchanged |

**Preserved fixes (do not regress when resuming cleanup):** single-page `highlighted-page.pdf`
(#406); Digital Commons wrapper filtering (#405); P015/P018/P026 ester stack (#400–#402).

## PR #406 merged (2026-07-02) — historical context

**#406** resolved live false-positive diagnosis (stale server) and restored single-page highlight
artifacts. Superseded as the status baseline by #407/#408 above; fixes remain on `main`.

| Finding | Cause | Action |
|---|---|---|
| User-visible false positives | Live server was **stale** at `fbefbb6` (PR #400 merge); 10 commits behind `main`; old audit job URLs may also show pre-#405 results | Restarted server; run **fresh** audits only |
| Broken “Open highlighted PDF page” | Single-page artifact route from `9ca99c0` was **never merged** to `main`; links opened full PDF + `#page=` | #406 restores `/highlighted-page.pdf` |
| Current `main` detector regression? | **No P026 reintroduction** vs `3b4043c`; #405 slightly **reduces** P020 noise (−6 on five-PDF eval) | Do **not** port old #388/#389–#393 detector stacks without strict proof |

## Recent cleanup (2026-07-02)

| Action | Item | Reason |
|---|---|---|
| **Merged** | [#408](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/408) | Confidence sort for grouped problem cards (UI only) |
| **Merged** | [#407](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/407) | Ester-reviewed warning-precision and presentation fixes |
| **Merged** | [#406](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/406) | Single-page highlighted PDF + live regression diagnosis docs |
| **Closed** | [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389)–[#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) | Stale presentation stack; no code merged; regression-risk vs landed #400/#402/#405 |
| **Deleted remote branches** | presentation stack branches (top → bottom) | PRs closed; not bases of remaining open PRs |
| **Merged** | [#405](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/405) | Clean #388 replacement — Digital Commons wrapper filtering, P018/P020/P028 FP reductions, page identity enrichment |
| **Closed** | [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) | Superseded by #405 — would reintroduce +298 P026 false positives |
| **Closed** | [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) | Superseded by #398 — CM/LM accepted with no P026A warning |

Earlier same-day cleanup: #394/#395 closed; merged #397–#400/#402/#401; deleted merged prep branches.

## Quick verdict table

| PR | Branch → base | Mergeable | Verdict |
|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | DIRTY | **Paused** — do not touch |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | DIRTY | **Paused** — docs-only |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | DIRTY | **Paused** |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | UNSTABLE | **Paused** — docs-only |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | UNSTABLE | **Paused** |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | DIRTY | **Paused** — pending warning-legitimacy review |
| ~~#407~~ | `fix/ester-reviewed-warning-precision` → `main` | **MERGED** | Squash-merged at `1827d8c1` |
| ~~#408~~ | `feat/sort-problems-by-confidence` → `main` | **MERGED** | Squash-merged at `70dcd95` |
| ~~#406~~ | `fix/live-false-positive-and-highlight-regression` → `main` | **MERGED** | Squash-merged at `811838c4`; branch deleted |

**Closed (2026-07-02):** [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389)–[#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) presentation stack — no code merged.

## Dependency graph (open stacks)

```
main (70dcd95 / includes merged #408 + #407 + #406 + #405)
 └── Independent PRs (paused): #311, #349, #362, #375, #376, #385
```

**Ester alignment stack on `main` (complete):** #397 → #398 (P026) → #399 (P018 parser) → #400 (P015) → #402 (P018 public cards) → #405 (wrapper FP reductions) → **#407** (Ester-reviewed precision/presentation). **#388 closed** — would reintroduce P026 false positives. **#389–#393 closed** — stale presentation stack.

## Recommended next development sequence

1. Confirm live server at `70dcd95` (or restart) so #407/#408 UI behavior matches local `main`.
2. Resume review of **#375**, **#376**, **#385**, **#362**, **#349**, **#311** only after the
   warning-legitimacy review concludes (or explicit human instruction; no auto-port of old detector
   stacks).

## PRs requiring explicit confirmation before close

| PR | Reason |
|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Superseded in spirit by geometry-driven location labels on `main` |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | Policy docs — may still carry unique content |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | Open product-policy question on "Review needed" prefix |

## Cleanup guardrails

- Do **not** start **P084** as part of PR cleanup.
- Do **not** merge/rebase #311, #349, #362, #375, #376, or #385 without explicit instruction.

## Historical triage

- [pr_and_stash_triage_20260619.md](pr_and_stash_triage_20260619.md) — pre-#372 PR #311 / #305 record
- Superseded bullets inside [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
