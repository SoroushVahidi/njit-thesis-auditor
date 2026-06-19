# Full Repository Audit — 2026-06-19

Read-only audit. No code changes, no commits, no deployment actions, no stash
applied, no branches deleted, no PRs merged/created as part of producing this
report.

## 1. Executive Summary

Main is healthy and up to date. The branch `fix/page-number-actionability`
described in the audit request has already been **merged to main** as PR
**#324** (squash-merged as commit `b4cb8cd`, 2026-06-18T18:40:49Z) and its
remote branch was auto-deleted. CI passed on all three Python versions
(3.10/3.11/3.12). Local `main` (`b4cb8cd`) matches `origin/main` exactly —
nothing to pull, nothing to push, working tree clean, no untracked files.

`ruff check .`, `mypy src`, and `python -m pytest` all pass locally
(1545 passed, 1 warning — identical to the count reported in the PR #324
description). Detector inventory covers P001–P074, P076–P083 (P075 is a
non-detector evaluation task); P084 is correctly **not implemented** anywhere
in `src/` — it only appears in planning/status docs as the deliberately
unstarted next rule ID.

The strict PDF highlight policy, no-highlight explanation-only behavior,
page-number/margin/font actionability, and Ester YES/NO matrix wording
alignment are all implemented and tested. Two open PRs remain: **#311**
(sub-page location labels — now in real conflict with main due to later
actionability work) and **#305** (example-URL UI tweak — has minor conflicts
in docs/tests, isolated low-risk diff). One unrelated stash exists from an
older branch (`fix/student-facing-comment-wording`) and was not touched.

The biggest concrete gaps: **no `/healthz` or `/version` endpoint exists**,
**the live demo server is currently not running** (no process on port 8000
despite a tmux session named `web` existing), and the flagship status doc
`docs/status/current_project_state_and_next_steps.md` is now stale (predates
PRs #320–#324).

## 2. Current Git State

| Item | Value |
|---|---|
| `pwd` | `/home/soroush/njit-thesis-auditor` |
| `git remote -v` | `origin` → `https://github.com/SoroushVahidi/njit-thesis-auditor.git` (fetch+push) |
| Current local branch | `main` |
| Current local HEAD | `b4cb8cd6e1e1f674f09bac273e5c54a3fe1fc572` |
| Latest `origin/main` | `b4cb8cd6e1e1f674f09bac273e5c54a3fe1fc572` (identical — up to date) |
| Working tree | Clean, no untracked files (`git status --short` empty) |
| `fix/page-number-actionability` | **Does not exist** locally or remotely. `git fetch --all --prune` reported `- [deleted] (none) -> origin/fix/page-number-actionability` — it was merged (squash) via PR #324 and the remote branch auto-deleted post-merge. The SHAs quoted in the task brief (`38cf633`, `2281715...`) were intermediate commits on that now-gone branch; squash merge produced the single commit `b4cb8cd` on main. |
| Stash | 1 entry: `stash@{0}: On fix/student-facing-comment-wording: pre-stabilization unrelated local changes`. **Not applied/popped.** Touches `polished_comments.py`, `report_view.py`, `pdf_body_spacing.py`, `pdf_font_compliance.py`, `test_pdf_rules.py`, `test_report_view.py` — adds P023/P026/P028 remediation-text overrides. The branch it was stashed from no longer exists (its underlying PR #318 already merged a parity fix under a similar name, so this stash predates/diverges from that merge — needs manual diff review before any future use, not a blind pop). |

Local branches with tracking refs (`git branch -vv`): only `main` is
checked out; the rest are local copies of remote feature/fix/docs branches
(`backup/pr297-before-split`, `backup/pr298-before-browser-qa`,
`backup/pr298-before-rebase`, `backup/pr299-before-rebase`,
`docs/pdf-finding-location-clarity-audit`, `feature/example-thesis-url`,
`feature/subpage-location-labels`, `fix/finding-actionability-drilldowns`,
`fix/p023-p016-issue-type-mismatch`, `fix/yesno-matrix-remediation-alignment`,
`ux/pdf-only-web-ui`, `ux/simplify-pdf-only-website`) — none are ahead of
their remotes, none need pushing.

`git branch -r` lists ~38 remote branches. Cross-checking with
`git branch -r --merged origin/main` vs `--no-merged`:

- **Already merged into main** (safe historical refs): `fix/p023-p016-issue-type-mismatch` (#323), `fix/yesno-matrix-remediation-alignment` (#322), `rules/p064-references-citations-structural-check`, and several `docs/*` audit branches.
- **Not an ancestor of main, but PR already squash-merged** (stale leftover refs, no action needed): `ux/pdf-only-web-ui` (#313), `ux/simplify-pdf-only-website` (#314), `fix/finding-actionability-drilldowns` (#320), `ux/expired-job-message` (#312). Squash-merge means the branch tip is never a literal ancestor, so these show as "unmerged" by ancestry despite being fully incorporated.
- **Genuinely open, unmerged work**: `feature/subpage-location-labels` (PR #311, open), `feature/example-thesis-url` (PR #305, open).
- **No associated PR found at all** (checked `gh pr list --state closed` back through PR #293 — none of these appear): `phase1-tex-source-auditor`, `phase2-pdf-apa-title-capitalization`, `organize-ester-materials`, `implement-frontmatter-no-visible-page-number`, `refine-p020-font-size-fallback`, `rules/p043-acknowledgements-indentation`, `rules/p063-appendix-body-heading-labels`, `web/audit-by-public-pdf-url`, `web/source-export-privacy-hardening`, `tests/web-demo-fixtures`, and several `docs/post-*`/`docs/scope-*` branches. Rule-coverage audit (Section 7) confirms P043 and P063 detectors already exist on main, so the matching branches here are almost certainly superseded/abandoned dev branches, not outstanding work. No deletion performed — flagged for later cleanup only.

## 3. PR / Branch Status

**Open PRs:**

| PR | Title | Branch | CI | Mergeable | Classification |
|---|---|---|---|---|---|
| #311 | Add sub-page location labels for PDF findings | `feature/subpage-location-labels` | Green (as of 2026-06-15, stale) | `mergeStateStatus: DIRTY`, `mergeable: CONFLICTING` | **Needs rebase** — touches `report_view.py`, `templates/job.html`, `tests/test_web_app.py`, all of which PRs #320/#323/#324 also rewrote afterward. Confirmed via `git merge-tree`-equivalent (GitHub's own conflict check) that it now conflicts directly. Before rebasing, worth checking whether the actionability work in #320–#324 already subsumes the sub-page-label goal — partial redundancy is likely, not just a mechanical conflict. |
| #305 | Add example NJIT thesis URL to web upload page | `feature/example-thesis-url` | Green (as of 2026-06-13) | `mergeable: UNKNOWN` (GitHub hadn't recomputed); local `git merge-tree origin/main origin/feature/example-thesis-url` shows real conflicts in `docs/web_ui_demo_guide.md`, `docs/web_ui_manual_qa_checklist.md`, `tests/test_web_app.py`. `templates/index.html` (the actual feature change) auto-merges cleanly. | **Stale but useful** — conflicts are only in docs/test churn from later doc-stabilization PRs, not in the feature code itself. Low-risk rebase. |

**Recently merged (most recent 15, newest first):** #324 (page-number/margin/font actionability), #323 (P023/P016 issue_type mismatch fix), #322 (YES/NO matrix wording alignment), #321 (strict PDF highlight eligibility policy), #320 (finding actionability + drill-down UI), #319 (docs/release-notes stabilization), #318 (mobile/desktop parity), #317 (GET /audits/sample guard), #316 (clickable problem-group pages), #315 (PDF-only rule reference), #314/#313 (PDF-only web UI), #312 (expired-job message), #310 (results page polish), #309 (ZIP upload hardening).

**PR #324 confirmation:** body explicitly states "no detector thresholds
changed; no rule IDs changed; no canonical rule JSON or raw guideline files
changed; no page-only PDF actions reintroduced; highlight policy remains
strict" and reports `ruff check .` passed, `mypy src` passed,
`python -m pytest` → `1545 passed, 1 warning, 0 failures`. Includes **both**
page-number actionability (`pdf_page_numbers.py`, `pdf_page_numbering_regime.py`,
`pdf_roman_*`, `pdf_frontmatter_no_page_number.py`) **and** margin/font
actionability (via `finding_explanations.py`, `issue_type_explanations.py`,
`polished_comments.py`, `report_view.py`). CI green on 3.10/3.11/3.12, merged
clean. **Already merged — no action needed.**

No PR found related to `/healthz` or `/version` (neither endpoint exists —
see Section 4/12). No PR or code reference to P084 outside docs/planning.

## 4. Implemented Features

| Item | Status | Key files | Tests |
|---|---|---|---|
| PDF-only public web UI | Implemented | `templates/index.html`, `web_app.py` (`_PDF_ONLY_ERROR`, POST `/audits` ext check) | `test_mobile_desktop_consistency.py` (asserts no "TeX"/".zip" anywhere) |
| Upload flow + ZIP hardening | Implemented | `web_app.py` POST `/audits`, `upload_handling.py::safe_extract_zip` (path-traversal, symlink, dup-member, size-cap, count-cap checks) | `test_upload_handling.py` |
| Audit job storage/runtime | Implemented | `web_app.py`: in-memory `_jobs` dict + `.runtime/web_audits` on disk, `JOB_TTL_SECONDS` (default 24h), startup + periodic cleanup | `test_web_app.py` |
| Sample audit route | Implemented | `web_app.py` POST `/audits/sample` (load) + GET guard redirecting to `/` (PR #317) | `test_web_app.py::test_get_audits_sample_redirects_to_index` |
| `/rules` page | Implemented | `web_app.py::_build_rule_catalog` (filters to PDF/student rules, excludes TeX-only and infra rules), `templates/rules.html` | `test_mobile_desktop_consistency.py` |
| Category pages | Implemented | `GET /audits/{job_id}/problems/category/{category_slug}`, `templates/problem_group.html` | `test_web_app.py`, `test_mobile_desktop_consistency.py` |
| Rule pages | Implemented | `GET /audits/{job_id}/problems/rule/{rule_id}` | `test_web_app.py` |
| Issue-type pages | Implemented | `GET /audits/{job_id}/problems/rule/{rule_id}/issue-type/{issue_type_slug}` | `test_web_app.py`, `test_problem_drilldown.py` |
| Result page | Implemented | `templates/job.html`, `web_app.py::_job_page_context` | `test_web_app.py`, `test_mobile_desktop_consistency.py` |
| JSON/Markdown downloads | Implemented | `GET /audits/{job_id}/download/json`, `/download/markdown` | `test_web_app.py` |
| Highlighted PDF generation | Implemented | `GET /audits/{job_id}/pdf/highlighted` (web_app.py), `pdf_highlight.py::build_highlighted_pdf` | `test_pdf_highlight.py`, `test_finding_actionability.py` |
| Strict highlight policy | Implemented | `pdf_highlight.py::is_drawable_bbox` / `has_visible_highlight`, `finding_explanations.py::get_action_kind` (only `"highlight"` or `"explanation"`, **no page-only kind**), wired through `report_view.py` | `test_pdf_highlight.py` (12 unit tests), `test_finding_actionability.py` (incl. 8-case parametrized invalid-bbox sweep) |
| No-highlight explanation-only | Implemented | `templates/problem_group.html`/`job.html` conditional on `has_highlight`; `get_no_highlight_reason()` | `test_finding_actionability.py::test_page_known_no_bbox_finding_renders_explanation_only` |
| Mobile/desktop parity | Implemented | Responsive CSS in `templates/base.html` (no mobile-only/desktop-only hidden content) | `test_mobile_desktop_consistency.py` (8 parity tests) |
| Ester YES/NO matrix alignment | Implemented (PR #322, merged) | `finding_explanations.py`, `issue_type_explanations.py`, `polished_comments.py` | `test_finding_actionability.py`, `test_issue_type_explanations.py` |
| Page-number actionability | Implemented (PR #324, merged) | `pdf_page_numbers.py`, `pdf_page_numbering_regime.py`, `pdf_roman_sequence.py`, `pdf_roman_section_anchors.py`, `pdf_frontmatter_no_page_number.py` | `tests/test_page_number_actionability.py` |
| Margin actionability (P011) | Implemented (PR #324, merged) | `polished_comments.py::_p011_margin_comment` (states which side, observed vs expected) | `tests/test_margin_font_actionability.py` |
| Font actionability (P026) | Implemented (PR #324, merged) | `polished_comments.py::_p026_font_comment` (distinguishes family vs size, lists accepted aliases) | `tests/test_margin_font_actionability.py` |
| P063 appendix wording | Implemented | `pdf_appendix_body_headings.py`, dedicated issue-type templates | `test_p063_appendix_body_headings.py` (11 tests) |

## 5. Partially Implemented Features

| Item | Status | Notes |
|---|---|---|
| Deployment freshness detection | Partial | No `/version`/`/healthz` to verify a *running* deployment's commit. README documents a manual restart procedure and recommends a tmux session named `thesis-auditor-web`, but provides no automated way to confirm the live process matches a given git SHA. |
| Documentation coverage | Partial | Recent planning docs (`page_number_actionability_audit.md`, `pdf_highlight_debug_audit.md`) are current and accurate. The flagship status doc is stale (Section 11). |
| P013 / P019 / P022 / P028 wording specificity | Partial-by-design | P013 is intentionally framed as "candidate, not confirmed defect" (correct design, not a bug) — counted as a limitation, not a gap, since it's suppressed from problem counts unless a real defect signal (P019/P022/P028) fires on top of it. |

## 6. Not Implemented Features

| Item | Status | Notes |
|---|---|---|
| `/healthz` endpoint | **Not implemented** | No route in `web_app.py`; no health-check middleware. Flagged as high-priority next task per the audit brief. |
| `/version` endpoint | **Not implemented** | `__version__ = "0.1.0"` exists in `src/njit_auditor/__init__.py` but is never serialized to any HTTP response. No commit hash exposed anywhere (footer, headers, or routes). |
| P084 (and beyond) | **Not started** — by design | Confirmed absent from all of `src/`; appears only in `docs/planning/` and `docs/status/` as the deliberately-deferred next rule ID. Correct current state — do not start per the audit brief. |

## 7. Rule Coverage Summary

Full detector inventory spans P001–P074 and P076–P083 (P075 is a pure
evaluation/non-detector task; P082 is experimental/opt-in, disabled by
default). Spot-audit of the rules called out as high-volume/recently
problematic:

| Rule | Detector | Wording | Issue-type expl. | Polished comment | Tests | Specificity |
|---|---|---|---|---|---|---|
| P011 (margins) | `pdf_margins.py` | Yes | Yes | Custom builder, names violated side | High | High |
| P012 (annotations) | `pdf_annotations.py` | Yes | Yes | Generic fallback | High | High |
| P013 (page-number candidates) | `pdf_page_numbers.py` | Yes, candidate-framed | Yes | Custom + suppressed-duplicate override | Very high | High (explicitly disclaims "not a confirmed defect") |
| P019 (page-number sequence/style) | `pdf_page_numbers.py` | Per-issue-type variants | Yes (5 variants) | Per-issue-type templates | High | High |
| P020 (title capitalization) | `pdf_title_capitalization.py` | Yes | Yes | Custom builder | Medium | High |
| P022 (no-number front matter) | `pdf_frontmatter_no_page_number.py` | Yes | Yes | Template + fallback | High | High |
| P023 (body spacing) | `pdf_body_spacing.py` | Yes | Yes | Template + LaTeX/Word remediation override | High | High |
| P025 (front-matter structure) | `pdf_frontmatter_structure.py` (4 sub-checks) | Per-issue-type | Yes (4 labels) | Per-issue-type templates | Medium | High |
| P026 (fonts) | `pdf_font_compliance.py` | Yes | Yes (family/size split) | Custom builder | Very high | High |
| P027 (heading levels) | `pdf_heading_levels.py` | Per-level (L1–L5) | Yes | Per-level templates | Medium | High |
| P028 (page-numbering regime) | `pdf_page_numbering_regime.py` | Per-issue-type | Yes (4 labels) | Templates + LaTeX-specific override | High | High |
| P038 (required heading missing) | `pdf_frontmatter_headings.py` | Yes | Yes | Per-issue-type templates | Medium | High |
| P063 (appendix labeling) | `pdf_appendix_body_headings.py` | Yes | Yes (4 variants) | Privacy-safe (no body text) | Very high (11 dedicated tests) | High |

**P084: confirmed not implemented anywhere in `src/`.** Only appears in
`data/processed/evaluation_data_manifest.json` and docs/planning/docs/status
files as "next inventory entry," with explicit "do not start" notes in
`docs/planning/repo_stabilization_after_p318.md` and
`docs/status/current_project_state_and_next_steps.md`.

## 8. Student-Facing Wording Status

Grep sweep of templates and presentation-layer Python for "candidate",
"manual verification", "possible issue", "review needed", "automated
finding", "Open PDF"/"Open PDF page"/"Open first example page", etc. found:

- **"Candidate"** is used consistently and only for unconfirmed P013 signals,
  never blended with confirmed-defect language (P019/P022/P028 use
  different, definitive wording). Acceptable.
- **"Review needed:" / "automated finding ... verify against NJIT
  guidelines"** appear as prefixes/suffixes always followed by a specific
  observed/expected statement, not standing alone as the entire message.
  Acceptable.
- **"Open first example page"** appears only inside a code comment
  (`web_app.py`) documenting what the strict highlight policy *forbids* —
  it does not render to students. Verified: no template renders this string.
- No occurrences of bare "possible issue", "flagged issue type", or
  "formatting check" used as a stand-alone, non-specific message in any
  student-facing template.

No fixes recommended in this area at this time.

## 9. Highlight/PDF Action Policy Status

Verified end-to-end:

1. **Decision point**: `finding_explanations.py::get_action_kind()` returns
   only `"highlight"` or `"explanation"` — there is no "page-only" kind by
   construction.
2. **Validation before claiming a highlight**: `pdf_highlight.py::is_drawable_bbox`
   (rejects non-finite/NaN/inverted/zero-area boxes) and `clip_box_to_page`
   (rejects off-page or sub-2pt-visible boxes) are invoked before any bbox is
   trusted, in both `report_view.py` and `web_app.py::_coerce_bbox`.
3. **Route robustness**: `GET /audits/{job_id}/pdf/highlighted` wraps
   highlight generation in try/except; any failure, empty box set, or
   zero-highlight result falls back to serving the plain PDF — never a 500.
4. **Visual modification verified by test**: `test_pdf_highlight.py` and
   `test_finding_actionability.py` assert annotation count > 0 and that
   response bytes differ from the original upload when a highlight is
   claimed.
5. **No-highlight is explanation-only, tested**: parametrized 8-case sweep
   (`zero_area`, `inverted`, `nan`, `infinity`, `outside_page_bounds`,
   `too_tiny`, `malformed_string`, `normalized_coordinates`) all confirm no
   PDF button renders and no 500 occurs.

No outstanding risk identified in this area.

## 10. Test/CI Status

```
ruff check .         → All checks passed!
mypy src             → Success: no issues found in 93 source files
python -m pytest -q  → 1545 passed, 1 warning in 14.92s
```

The 1 warning is a benign `UserWarning: Duplicate name: 'main.tex'` from
`zipfile` inside `test_upload_handling.py::test_duplicate_member_paths_rejected`
(it's intentionally constructing a malicious duplicate-member ZIP to test the
rejection path). Exactly matches the count PR #324 reported, confirming
local state == merged main state.

Confirmed test coverage exists for: page-number actionability
(`test_page_number_actionability.py`), margin/font actionability
(`test_margin_font_actionability.py`), Ester YES/NO alignment
(`test_finding_actionability.py`, `test_issue_type_explanations.py`), strict
highlight policy (`test_pdf_highlight.py`, `test_finding_actionability.py`),
mobile/desktop parity (`test_mobile_desktop_consistency.py`). **No coverage
for `/healthz` or `/version`, because neither endpoint exists.** No
dedicated generic "crawl every route, assert no 500" test found as a single
suite, though route-specific no-500 assertions exist scattered across
`test_web_app.py` and `test_finding_actionability.py`.

## 11. Documentation Status

| Doc | Verdict |
|---|---|
| `README.md` | Current — accurately describes PDF-only scope, rule range, restart requirements; correctly silent/absent on `/healthz`/`/version` |
| `AGENTS.md` | Current — generic autonomous-workflow instructions, not behavior-specific, nothing to go stale |
| `docs/web_gui_mvp.md` | Current — explicitly notes no `/version`/`/healthz` exists yet |
| `docs/web_ui_manual_qa_checklist.md` | Current |
| `docs/web_ui_demo_guide.md` | Current |
| `docs/planning/page_number_actionability_audit.md` (2026-06-18) | Current, authoritative for PR #324 |
| `docs/planning/pdf_highlight_debug_audit.md` (2026-06-17) | Current, authoritative for PR #321 |
| `docs/planning/problem_drilldown_audit.md`, `problem_page_actionability_audit.md` | Current, accurate for PR #320 |
| `docs/planning/repo_stabilization_after_p318.md` | Partially stale — its "no detector logic changed" framing needs an implicit "through #318" qualifier; its `/healthz`/`/version` recommendation was never acted on |
| **`docs/status/current_project_state_and_next_steps.md`** | **Stale** — predates PRs #320–#324; omits all of the actionability/highlight-policy/wording-alignment work. Highest-priority doc to refresh. |
| `docs/status/full_repository_audit_after_p063.md` | Stale (historical snapshot, correctly scoped to its own era — not misleading, just superseded) |
| `docs/status/project_closeout.md` | Current — explicitly self-labeled as a historical P082 snapshot pointing readers to the (stale) "current state" doc |

## 12. Deployment/Live-Server Status

- A tmux session named `web` exists (note: README's documented convention is
  `thesis-auditor-web` — naming drift, not a functional problem).
- `tmux capture-pane` (read-only) shows uvicorn was started, served traffic
  (visible hits on `/audits/.../pdf/highlighted`, `/rules`, `/audits/sample`,
  download routes), and was then **terminated**. The pane is currently
  sitting at a bare shell prompt.
- `ps aux` / `ss -ltnp` confirm: **no uvicorn/python process is running, and
  nothing is listening on port 8000 right now.** The live demo is currently
  down.
- `.runtime/uvicorn-8000.log` is a 0-byte file — no current log output to
  inspect for the last run's exit reason.
- No `/healthz` or `/version` means there is no way to query a *running*
  instance and learn which commit it's serving, even once restarted.
- Deployment instructions in `README.md` / `docs/web_gui_mvp.md` are
  reliable and complete (env vars, tmux pattern, reverse-proxy notes,
  restart-after-Python-changes warning). They were not exercised as part of
  this audit (no restart performed, per the read-only constraint).

**Safe restart sequence for later** (not executed): confirm `git log -1`
matches the intended commit, `tmux attach -t web` (or new session), run
`./scripts/run_web_gui.sh`, smoke-test `/`, `/audits/sample`, and one
highlighted-PDF link, then detach.

## 13. Risks

1. **Live demo is currently offline** — anyone hitting the public URL right now gets nothing. Highest-visibility risk.
2. **No `/healthz` or `/version`** — once restarted, there's no cheap way to confirm the live process matches a specific commit, or to monitor uptime externally.
3. **PR #311 is in real conflict with main**, not just stale — `report_view.py`/`job.html` were rewritten three times since it was opened (#320, #323, #324). Rebasing naively risks silently reintroducing the page-only-action pattern that #321 explicitly removed; needs a careful re-implementation against current `report_view.py`, not a mechanical conflict resolution.
4. **`docs/status/current_project_state_and_next_steps.md` is stale** and is the most likely doc a future contributor (human or agent) reads first — it currently undersells how much actionability/highlight-policy work has landed.
5. **Leftover stash and ~20 branches with no associated PR** are low-risk clutter today, but the stash in particular contains unreviewed P023/P026/P028 remediation-text changes that diverge from what actually shipped — if anyone pops it later without diffing against current `polished_comments.py`, it could silently reintroduce already-superseded wording.

## 14. Recommended Next Actions (priority order)

1. Restart the live server on current `main` (`b4cb8cd`) and smoke-test `/`, sample audit, a highlighted-PDF link, and a download route — the demo is currently down.
2. Add `/healthz` (process liveness) and `/version` (expose `__version__` + ideally short git SHA) — small, high-value, currently the single biggest "should exist but doesn't" gap.
3. Refresh `docs/status/current_project_state_and_next_steps.md` to a post-#324 snapshot (or add a clearly-dated addendum section covering #320–#324) so it stops underselling current capability.
4. Review PR #311 for redundancy with #320/#323/#324 before investing in a rebase — the sub-page-label goal may already be substantially achieved by the merged actionability work; if a real gap remains, re-implement against current `report_view.py` rather than force-resolving the conflict.
5. Rebase PR #305 — conflicts are confined to docs/test churn, not the actual `index.html` feature change, so this should be a quick, low-risk rebase once prioritized.
6. Review the stash (`stash@{0}`) by diffing it against current `polished_comments.py`/`report_view.py` before ever applying it — it predates several wording-alignment PRs and may already be superseded.
7. Only after 1–3 are done, consider cleaning up the ~20 no-open-PR stale branches (do not delete without a final check that none represent unmerged unique work — P043/P063-named branches in particular look superseded but weren't diffed line-by-line in this pass).
8. Do not start P084 — current docs and this audit agree the right call is continued stabilization, not new detector work.

---
*Generated by a read-only audit pass on 2026-06-19. No files modified, no commits created, no deployment or stash actions taken.*
