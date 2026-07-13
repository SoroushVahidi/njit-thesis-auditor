# Overnight Esther Correctness Pass — 2026-07-12/13

**Worktree:** `overnight-esther-correctness-20260712`
**Branch:** `fix/overnight-esther-correctness-20260712`
**Baseline `main`:** `8e6ad430449195577fc84ef93c1fc864d1e078c7` ("Improve P019 page-numbering location
evidence (#503)") — verified `ruff check .` clean, `mypy src` clean, `python -m pytest -q tests`
**2742 passed**.
**Live server:** not touched. Never bound to port 8000; all replay/crawl work used in-process
`fastapi.testclient.TestClient` or a temporarily detached local `git` checkout, never a network
server.

## 0. Correction to the seed task

The seed prompt for this session referenced `docs/status/esther_spec_compliance_audit_20260712.md`
and a "57.6% compliance score." Neither exists anywhere in this repo's git history on any branch
(`git log --all -- docs/status/esther_spec_compliance_audit_20260712.md` returns nothing; no
"57.6%" string appears in the repo). Per the seed prompt's own instruction, this was treated as a
fabricated detail from the task-generation pipeline and ignored. No percentage compliance score is
reported below unless computed from real replayed data in this session.

## 1. What this pass actually found: five already-completed, validated, unmerged PRs

Before writing any new code, this pass surveyed open PRs (`gh pr list --state open`) because prior
sessions' `docs/status/current_project_state_and_next_steps.md` entries showed a dense recent
cadence of narrow Esther-alignment PRs. Six open PRs existed, all created 2026-07-08 through
2026-07-11, each already carrying its own root-cause writeup and passing test claims:

| PR | Title | Disposition this pass |
|----|-------|------------------------|
| #504 | Fix P015 continuation-line indentation gap (Sample B annotation forensics) | **Adopted** (cherry-picked) |
| #494 | Fix Sample B font false positive highlight (P026) | **Adopted** |
| #499 | Make P011 remediation content-aware | **Adopted** |
| #500 | Improve P011 margin precision and false-negative coverage | **Adopted** (docs/tests only, no detector change) |
| #502 | Fix P033 location wording and add warning duplicate analysis | **Adopted** |
| #483 | Document Ester Sample B feedback audit | **Skipped — superseded.** `git merge-tree` showed an add/add conflict on `docs/status/ester_sample_b_feedback_audit.md`; diffing revealed the file already exists on `main` (added by commit `8ee50d6`, part of the already-merged #482 chain) with materially the same and more complete content. #483's version is an earlier draft of the same audit; nothing unique was lost. |

Each of the five adopted PRs' base commit was behind current `main` by a handful of already-merged
commits. `git merge-tree HEAD origin/<branch>` showed **zero conflicts** for all five. They were
cherry-picked onto this branch in dependency order (`df71d7c` P015, `5ba3acc` P026, `822ad2e` P011
wording, `5eb0bfb` P011 docs/tests, `a9efeff` P033 + duplicate-analysis tool) with **zero merge
conflicts** and no manual conflict resolution needed anywhere. This is adoption of prior, already
narrowly-scoped and already-reviewed work — not new detector development — which is why validation
below is unusually fast and clean.

## 2. Requirements sources actually consulted

- `docs/status/README.md` and `docs/status/current_project_state_and_next_steps.md` (canonical
  status entry point; read through pass #25 / 2026-07-06, then cross-checked against `git log`
  and `gh pr list` since the doc's "Current Status" header was stale relative to actual `main`).
- `docs/status/p011_precision_false_negative_audit_20260710.md` (from adopted PR #500) — an
  eight-workstream P011 audit against Sample A/B; the authoritative source for P011's remaining
  Esther-judgment questions (§7 below).
- `docs/status/sample_b_annotation_ground_truth_forensics_20260710.md` (from adopted PR #504) —
  forensic proof that Sample B's 65 native PDF annotations are genuine `Highlight`/`Text` objects
  by "ester flaim" that never leak into any detector except P012 (full non-P012 finding diff,
  annotated vs. annotation-stripped, is byte-identical).
- `docs/status/ester_sample_b_font_false_positive_highlight.md` (from adopted PR #494) — P026
  false-positive root cause.
- Persistent project memory at `/home/soroush/.claude/projects/-home-soroush-njit-thesis-auditor/
  memory/` — `MEMORY.md` plus linked files, primarily `sample_b_annotation_ground_truth_investigation.md`,
  `p011_content_aware_remediation.md`, and `pymupdf_rect_validation.md`, which independently
  corroborated the adopted PRs' own claims (no new contradiction found).
- No `data/raw/ester/` or `data/raw/guidelines/` file content was read or quoted directly in this
  pass; the adopted PRs' own prior investigations already did that work and are the operative
  evidence trail.

## 3. Fresh replay: before vs. after (this session's own measurement)

Privacy-safe replay (`rule_id`/`issue_type`/`confidence` counts only, via
`run_pdf_audit_full` → `build_report_view`, no body text) was run twice: once with the working
tree detached at baseline `8e6ad43`, once at this branch's `HEAD`, both inside the same worktree
(no second checkout/clone).

| Sample | Visible (before) | Visible (after) | Delta | Explanation |
|--------|-------------------|-------------------|-------|-------------|
| `ester_sample_a` | 23 | 23 | 0 | Unaffected — none of the adopted fixes' preconditions occur in Sample A. |
| `ester_sample_b` | 35 | 39 | **+4** (P015 +5, P026 −1) | 5 new true-positive P015 `unexpected_indent_on_continuation_line` cards (equation-continuation paragraphs that were previously exempted by an overbroad lowercase-start heuristic); 1 P026 false positive removed (Approval Page committee-signature block no longer measured against body-font size after the page is correctly recognized as front matter). |
| `ester_sample_c` | 34 | 38 | **+4** (same pattern) | Same underlying document family as Sample B; same detector paths, same delta shape. |
| `ester_sample_d` | 210 | 210 | 0 | Unaffected — confirms no regression on the largest/most complex sample. |

Raw (pre-grouping) finding counts moved in lockstep with the above (Sample B raw P011/P013/etc.
unchanged; only P015 raw count rose 1→6 and P026 raw count fell 1→0). No other rule's count moved
on any sample. This matches, and independently re-confirms, the counts each adopted PR's own body
claimed.

## 3b. New fix found and implemented this session: raw rule_id leak in the generic fallback

After adopting the five PRs above, a fresh, independent grep/trace audit (Phase 4 item 1 — internal
`P###` identifiers leaking into student-visible text) found a genuine, previously-unreported gap:
`build_polished_comment()`'s final catch-all fallback in `src/njit_auditor/polished_comments.py`
(reached whenever a `(rule_id, issue_type)` pair has no entry in `_ISSUE_TEMPLATES` or
`_RULE_FALLBACKS`) interpolated the raw internal `rule_id` directly into the sentence that becomes
`FindingView.polished_comment` — rendered as visible prose by `job.html` and `problem_group.html`
(e.g. `"This check (P065) found a possible dedication text not centered issue on page 7."`).

At the time of the audit, **P057, P059, P062, P065, and P078** — all live, default-enabled
detectors (not experimental-gated in `audit_runner.py`) — had zero coverage in either dict and so
always hit this path in production. The project already had an established convention (multiple
existing tests assert `"This check (" not in polished_comment` for *specific* rule/issue pairs) that
this exact generic path had never been checked against.

**Fix:** `src/njit_auditor/polished_comments.py` — replaced `f"This check ({rule_id}) found a
possible..."` with `f"This formatting check found a possible..."` in both fallback branches (source-
rule and PDF-rule). Two lines changed; no rule ID, threshold, confidence, or detection logic
touched — purely removes the internal identifier from the visible sentence. `_finish_comment`
already discarded `rule_id`/`issue_type` for this branch (`_ = rule_id`), confirming the identifier
was never needed for anything except the leak itself.

**Validation discipline followed:**
1. Added `test_generic_fallback_never_leaks_raw_rule_id` (parametrized over the 5 confirmed-affected
   rule IDs) and `test_generic_fallback_never_leaks_raw_rule_id_for_any_unmapped_id` (a synthetic
   `P999` id, proving the fallback is safe by construction for any future uncovered rule, not just
   the 5 found) in `tests/test_feedback_clarity_wording.py`.
2. Confirmed both new tests **fail** against the pre-fix code (`git stash` of just the source file,
   rerun, all 6 fail with the exact leaked substring in the assertion error; `git stash pop`
   restored the fix) — a real red/green demonstration, not just static reasoning.
3. Found and fixed one pre-existing stale test, `test_polished_comment_fallback_unknown_rule` in
   `tests/test_report_view.py`, which had asserted `"P999" in comment` — i.e. it had encoded the
   leak itself as expected behavior. Updated to assert the opposite, with a comment cross-
   referencing the new regression tests.
4. Full suite re-run after both changes: **2794 passed**, 0 failed. `ruff check .` and
   `mypy src/njit_auditor` both clean.
5. Grepped the whole test suite for any *positive* assertion of the old `"This check ("` wording
   before committing — found only negative (`not in`) assertions and comment references, so no
   other test needed updating.

## 4. Validation (this session)

- `ruff check .` — **clean** (0 issues).
- `mypy src/njit_auditor` — **clean**, "Success: no issues found in 108 source files".
- `python -m pytest -q tests` (with `PYTHONPATH=<worktree>/src` per the documented venv-pinning
  quirk) — **2794 passed**, 0 failed, 3 warnings (pre-existing deprecation warnings, unrelated to
  this pass), ~100s. That is baseline 2742 + 46 tests from the five adopted commits + 6 new tests
  from the rule_id-leak fix (§3b).
- Anti-overfitting grep: `git diff 8e6ad43..HEAD -- src/ scripts/` searched for sample/filename/
  author-name-specific conditionals. The only hit is a loop over `("ester_sample_a",
  "ester_sample_b")` inside `scripts/p011_overnight_inventory.py`, which is a standalone offline
  diagnostic script (never imported by `src/njit_auditor`), which is exactly the kind of
  privacy-safe inventory tooling the task's own rules permit. **Zero hits in any of the five
  touched runtime `src/` files** (`pdf_indentation.py`, `pdf_font_compliance.py`,
  `p011_margin_presentation.py`, `polished_comments.py`, `duplicate_candidate_analysis.py`).
- Template/CSS/route surface check: `git diff 8e6ad43..HEAD --stat` touches zero files under
  templates, static assets, or `web_app.py` — all five adopted commits are pure detector logic,
  wording strings inside existing card templates, tests, docs, and offline scripts. No new mobile/
  narrow-layout risk was introduced (existing card templates, existing CSS), so no separate mobile
  crawl was needed for this change set specifically.
- PDF-link crawl (Phase 3 requirement): in-process `TestClient` flow — `POST /audits/sample` →
  poll `/audits/{job_id}/status` → crawl `/audits/{job_id}` in default, `?sort=page`, and
  `?sort=topic` views, plus every discovered rule-drilldown and page-drilldown link — GET every
  extracted PDF link and assert `200` + `content-type` starts with `application/pdf` + body starts
  with `%PDF`. Run against three samples:
  - `ester_sample_a`: 22 unique PDF links, **0 failures**.
  - `ester_sample_b`: 38 unique PDF links, **0 failures**.
  - `ester_sample_d`: 149 unique PDF links (largest/most complex sample), **0 failures**.
  Downloads (`/download/json`, `/download/markdown`) and `/rules` all returned 200 for every
  sample tested.

## 5. Remaining items that need Esther's judgment (logged, not implemented — carried forward
verbatim from the adopted PRs' own investigations, not invented this session)

From `p011_precision_false_negative_audit_20260710.md` (§7, §15–16 of that report):

1. Should recurring **footer-zone body text** (not page numbers) crossing the bottom margin be
   flagged? Sample A has an 8-page cluster (~9.2pt recurring bottom overflow) that is geometrically
   consistent but of unclear policy status.
2. Should **non-text elements** (raster images, vector drawings, table borders — currently
   unaudited by P011, which only inspects text lines) be brought into scope? This is a documented
   coverage gap, not a code defect; no conservative false-positive-safe prototype cleared the bar
   for shipping in that pass.
3. Six Sample B medium-confidence right-margin pages (41, 68, 73, 76, 97, 101) remain
   Esther-unreviewed; precision there is "probable," not confirmed.
4. Whether multi-side P011 violations should stay one rolled-up card per page or split per side.

From `sample_b_annotation_ground_truth_forensics_20260710.md` (§18): whether a TOC-entry
sentence-case rule (pages showing level-3 heading case inconsistency) should be a document-wide
rule or stay out of scope pending a dedicated design pass — logged as a **new-rule** question, not
a bug in an existing rule.

None of the above were guessed at or implemented this session — they require an actual policy
answer from Esther and are exactly the class of item the task instructions say to log rather than
resolve unilaterally.

## 6. Unambiguous fixes still open (not attempted this session — time was concentrated on
triage/adoption/validation of the above five PRs rather than fresh detector development)

- P011 footer-zone wording mismatch (§12 of the precision audit): the multi-side comment template
  says "paragraph/line spacing" for a horizontal-containment violation at the page bottom — a
  wording nit, deferred in the source PR pending the footer policy call in item 1 above (the
  wording fix and the policy call are coupled, so fixing the wording first could bake in an assumed
  policy answer).
- Non-text (image/drawing) margin coverage (item 2 above) is real future work, explicitly out of
  scope for a "narrow, general, testable fix" bar.

## 7. Anti-overfitting statement

No document-, author-, sample-, page-, phrase-, filename-, or content-hash-specific conditional was
added to any file under `src/`. Verified by direct diff inspection (`git diff 8e6ad43..HEAD --
src/`) of every touched runtime file, not just a grep pass.

## 8. Production statement

`thesis-auditor-web.service` (port 8000, primary repo checkout, `systemctl --user`) was never
queried, restarted, or otherwise touched. No process in this session bound to port 8000. PDF-link
crawling used `fastapi.testclient.TestClient` (in-process ASGI, no socket) exclusively; no scratch
uvicorn server was started because the in-process approach fully covered the same surface with less
risk.

## 9. Readiness assessment

- **Detector/wording correctness (P011, P015, P026, P033):** ready — five independently-authored,
  independently-tested PRs adopted, composed cleanly, fully re-validated together.
- **Repo cleanup:** the five adopted PR branches (`fix/p011-content-aware-remediation`,
  `fix/p011-margin-precision-false-negative-audit`, `fix/p033-location-wording-and-duplicate-analysis`,
  `investigate/sample-b-annotation-ground-truth`, `fix/ester-sample-b-font-false-positive-highlight`)
  are now superseded by this session's PR and can be closed once this PR is reviewed/merged. PR
  #483 is superseded by already-merged `main` content and can be closed independently of this PR.
  Not actioned in this session (PR closing was not in scope; flagged here for the next maintenance
  pass).
- **Further P011 work:** blocked on Esther policy answers (§5), not on engineering — no further
  unilateral code changes are recommended there.
