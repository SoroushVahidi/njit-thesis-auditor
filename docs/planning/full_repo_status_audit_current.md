# Full Repository Status Audit

> **Historical/superseded.** Despite the filename, this is a dated point-in-time
> snapshot (2026-06-16, baseline `802350d`/PR #319), not the current status. For the
> current status, see `docs/status/current_project_state_and_next_steps.md`
> (the "Current Status" section at the top).

- **Date:** 2026-06-16
- **Auditor:** Claude Code (automated)
- **Baseline:** `main` at `802350d` (PR #319 — Stabilize web UI docs and release notes)
- **Test count at time of audit:** 1455 passed, 1 warning, 0 failures

---

## 1. Executive Summary

The repository is in a healthy but **not-yet-committed** state. A large body of
feature work (Phase 2: issue-type explanations; Phase 3: problem drill-down) is
fully implemented, fully tested, and passing locally — but has not been committed
or pushed to any branch.

**The live server is currently in a broken mixed state** because:
- Jinja2 templates were modified on disk after the server process started.
- Python code (`web_app.py`) was also modified but has NOT been reloaded.
- Templates reference a `issue_type_slug` Jinja2 filter and a `category_summary`
  context variable that do not exist in the currently running process.
- Any request to `/audits/{job_id}` (an audit result page) will return a 500 error.
- **The live server must be restarted before it can serve audit results.**

Three pull requests are open: #312 (mergeable), #311 and #305 (both conflicting
with main). One stash exists with pre-stabilization work on overlapping files.

Safe to proceed? **Not yet.** The server must be restarted, and the working-tree
work must be committed before any further feature work or live testing.

---

## 2. Current Git State

| Field | Value |
|---|---|
| Branch | `main` |
| HEAD | `802350d` |
| Remote `origin/main` | `802350d` (in sync) |
| Working tree | **DIRTY** — 10 modified tracked files + 8 untracked files |
| Stash | 1 stash (`stash@{0}`) |
| Remote | `https://github.com/SoroushVahidi/njit-thesis-auditor.git` |

### Recent commits (origin/main)

```
802350d Stabilize web UI docs and release notes (#319)
9e54b7b Fix mobile desktop UI parity (#318)
84de98c Guard GET /audits/sample route (#317)
8095cc6 Add clickable problem-group pages (#316)
604c095 Show only PDF web rules in rule reference (#315)
115d748 Simplify PDF-only website wording (#314)
c6e437c Make web interface PDF-only (#313)
c5dd824 Polish results page wording and mobile summary layout (#310)
a8c619a Harden ZIP upload extraction checks (#309)
da761df Add footer attribution and contact email (#308)
```

### Working tree — modified tracked files (10)

All 10 files are Phase 2 + Phase 3 feature work, committed nowhere:

| File | Change |
|---|---|
| `src/njit_auditor/web_app.py` | +104/−21: new route, `issue_type_slug` filter, `_issue_type_from_slug`, `category_summary` context, serialization of new DTO fields |
| `src/njit_auditor/report_view.py` | +66/−1: `issue_type_label` + `issue_type_explanation` fields on `FindingView` and `GroupedProblemView` |
| `src/njit_auditor/templates/job.html` | +79/−4: "Summary by problem type" table, issue-type `<details>` blocks, "View all" drill-down links |
| `src/njit_auditor/templates/problem_group.html` | +36/−2: issue-type `<details>` blocks, "View all" link |
| `src/njit_auditor/polished_comments.py` | +4: specific P012 `pdf_annotation_detected` comment template |
| `docs/planning/mobile_desktop_consistency_audit.md` | +23: issue-type/actionability parity notes |
| `docs/web_ui_manual_qa_checklist.md` | +21: issue-type/highlight/drill-down checks |
| `tests/test_mobile_desktop_consistency.py` | +2/−2: PDF link regex tightened |
| `tests/test_results_page_wording.py` | +1/−1: section-note assertion updated |
| `tests/test_web_app.py` | +6/−6: PDF link regex tightened (3 locations) |

### Working tree — untracked new files (8)

| File | Description |
|---|---|
| `src/njit_auditor/finding_explanations.py` | Action kind/label/no_highlight_reason + detailed explanations (Phase 2) |
| `src/njit_auditor/issue_type_explanations.py` | `humanize_issue_type()` + `explain_issue_type()` with 50+ explicit mappings |
| `tests/test_finding_actionability.py` | 38 tests: PDF highlighting, action kinds, page fallback, crawl non-500 |
| `tests/test_issue_type_explanations.py` | 52 tests: humanization, explanation, fallback, no-LaTeX-leak |
| `tests/test_problem_drilldown.py` | 46 tests: category/rule/issue-type drill-down routes |
| `docs/planning/finding_actionability_and_highlight_audit.md` | Pre-Phase-2 state audit |
| `docs/planning/finding_actionability_matrix.md` | Rule-by-rule action kind matrix |
| `docs/planning/problem_drilldown_audit.md` | Pre/post Phase 3 drill-down state |

### Stash

```
stash@{0}: On fix/student-facing-comment-wording: pre-stabilization unrelated local changes
```

This stash was saved during the PR #319 stabilization pass. It contains:
- `src/njit_auditor/polished_comments.py`
- `src/njit_auditor/report_view.py`
- `src/njit_auditor/rules/pdf_body_spacing.py`
- `src/njit_auditor/rules/pdf_font_compliance.py`
- `tests/test_pdf_rules.py`
- `tests/test_report_view.py`

**Risk:** `polished_comments.py` and `report_view.py` in the stash overlap with current
working tree modifications. Applying the stash now would cause merge conflicts. The stash
should be inspected and resolved after the current working tree is committed.

---

## 3. Validation Results

| Check | Result |
|---|---|
| `pip install -e ".[dev]"` | Passed |
| `ruff check .` | All checks passed |
| `mypy src` | Success: no issues found in 93 source files |
| `pytest` | **1455 passed, 1 warning, 0 failures** |

Note: the 1455 count includes 136 tests from the 3 new untracked test files
(38 + 52 + 46). These cover Phase 2+3 code that exists only in the working tree.

Remaining warning (expected, harmless):
```
tests/test_upload_handling.py::test_duplicate_member_paths_rejected
  UserWarning: Duplicate name: 'main.tex'  [zipfile internal]
```

---

## 4. Current Web UI Capabilities

### A. PDF-only public upload

- Upload form accepts only PDF.
- TeX/ZIP/source-audit wording does not appear in the public web UI.
- CLI/source-audit support remains in the codebase, separate from the web UI.
- `/audits/sample` GET is guarded: redirects to `/` (confirmed live: 302 → 200).

### B. Mobile/desktop parity

- Same substantive content (summary counts, findings, PDF links, issue-type labels,
  drill-down links) rendered for both viewport profiles.
- Responsive differences are CSS layout-only; no `display:none` content branches.
- 20+ automated parity tests in `tests/test_mobile_desktop_consistency.py`.

### C. PDF open/highlight behavior

- Plain PDF route (`/audits/{job_id}/pdf`) serves inline (not attachment).
- Highlighted PDF route (`/audits/{job_id}/pdf/highlighted?...`) exists.
- Invalid/degenerate bbox is validated before `add_rect_annot`; falls back to plain PDF.
- Invalid page numbers fall back safely.
- Original uploaded PDF is never modified.
- No plain PDF route returns 500 (regression-tested).

### D. Issue-type explanations (Phase 2 — uncommitted)

- Internal issue types humanized: e.g., `pdf_annotation_detected` → "PDF annotation detected".
- Visible issue types show a `<details class="issue-type-help">` expandable block.
- Explicit student-facing explanations for P012, P026, P011, P023, P013, P028, P021, etc.
- Unknown issue types have a generic safe fallback.
- No raw LaTeX leak in rendered output (52 tests verify this).
- **Status: implemented locally, 52 tests passing, not yet committed.**

### E. Problem drill-down / actionability (Phase 3 — uncommitted)

- Every summary count is now actionable:
  - "Summary by problem type" table with "View all" links to category drill-downs.
  - "Summary by rule" table with "View all" buttons to rule drill-downs.
  - Issue-type `<details>` blocks include "View all findings of this type →" link.
- New route: `GET /audits/{job_id}/problems/rule/{rule_id}/issue-type/{issue_type_slug}`.
- Issue-type slug uses hyphens (`pdf-annotation-detected`).
- 404 returned when no matching findings exist.
- `group_kind = "issue_type"` added to `_problem_group_context`.
- **Status: implemented locally, 46 tests passing, not yet committed.**

### F. Privacy / no-leak status

- No raw LaTeX commands/packages in rendered web output.
- No dissertation body text in rendered web output.
- No awkward fallback phrases like "flagged issue type 'pdf_annotation_detected'" in rendered output
  (P012-specific polished comment template added in `polished_comments.py`).
- Internal-only wording ("heuristic", private file paths) does not appear in templates.

---

## 5. Open PR / Branch Status

### Open PRs

| PR | Title | Branch | Base | Mergeable | Commits ahead |
|---|---|---|---|---|---|
| #312 | Clarify expired audit result message | `ux/expired-job-message` | main | **MERGEABLE** | 1 |
| #311 | Add sub-page location labels for PDF findings | `feature/subpage-location-labels` | main | **CONFLICTING** | 1 |
| #305 | Add example NJIT thesis URL to web upload page | `feature/example-thesis-url` | main | **CONFLICTING** | 1 |

**PR #312** — Safe to merge as-is. Changes `index.html`, `web_app.py` (expired-job
wording), and `test_web_app.py` (90 tests). No overlap with Phase 2+3 working tree.

**PR #311** — 1 commit, adds sub-page location labels (`report_view.py`, `pdf_captions.py`,
`job.html`, `test_location_label.py`). Conflicts with current main because the working tree
has heavy modifications to `report_view.py` and `job.html`. Needs rebase after Phase 2+3 is committed.

**PR #305** — 1 commit, adds example NJIT thesis URL to upload page (`index.html`,
`web_ui_demo_guide.md`, `web_ui_manual_qa_checklist.md`, `test_web_app.py`). Conflicts
because `web_ui_manual_qa_checklist.md` is modified in the working tree. Needs rebase.

### Local branches (unique-commit classification)

| Branch | Commits ahead of main | Classification |
|---|---|---|
| `backup/pr297-before-split` | 4 | Backup only — all content merged into main via PRs #297–#299; **safe to delete** |
| `backup/pr298-before-browser-qa` | — | Backup only; **safe to delete** |
| `backup/pr298-before-rebase` | — | Backup only; **safe to delete** |
| `backup/pr299-before-rebase` | — | Backup only; **safe to delete** |
| `docs/pdf-finding-location-clarity-audit` | 1 | Doc-only audit file; not on remote; **inspect before deleting** |
| `feature/example-thesis-url` | 1 | Head of open PR #305; **retain** |
| `feature/subpage-location-labels` | 1 | Head of open PR #311; **retain** |
| `ux/expired-job-message` | 1 | Head of open PR #312; **retain** |
| `ux/pdf-only-web-ui` | 1 | "Make web interface PDF-only" — content merged as c6e437c (PR #313); **safe to delete** |
| `ux/simplify-pdf-only-website` | 1 | "Simplify PDF-only website wording" — content merged as 115d748 (PR #314); **safe to delete** |

---

## 6. Documentation Status

| Doc | Status |
|---|---|
| `README.md` | Current. PDF-only, CLI separation, restart requirement, P082 experimental, P083 evaluation-only. |
| `docs/web_gui_mvp.md` | Not inspected in detail; assumed current from PR #319 stabilization. |
| `docs/web_ui_demo_guide.md` | Current for PR #319 baseline. Phase 2+3 not yet reflected (issue-type expansions, drill-down table). Will need update after commit. |
| `docs/web_ui_manual_qa_checklist.md` | Modified in working tree. Includes issue-type and highlight checks. Current for Phase 2+3. |
| `docs/status/current_project_state_and_next_steps.md` | Reflects P083, PR #318 merge. Does not mention Phase 2+3 web work. Will need update after commit. |
| `docs/planning/mobile_desktop_consistency_audit.md` | Modified in working tree. Includes Phase 2+3 parity scope (actionability, issue-type, drill-down links). |
| `docs/planning/repo_stabilization_after_p318.md` | Current and accurate. Records PR #319 stabilization pass, live restart at 17:28. |
| `docs/planning/problem_drilldown_audit.md` | Untracked new file. Pre/post Phase 3 drill-down state. |
| `docs/planning/finding_actionability_and_highlight_audit.md` | Untracked new file. |
| `docs/planning/finding_actionability_matrix.md` | Untracked new file. |

**Accurate claims across all docs:**
- Public web UI is PDF-only ✓
- CLI/source-audit is separate ✓
- Mobile/desktop parity is expected ✓
- PDF routes serve inline where possible ✓
- Browser-native PDF behavior is partly browser-controlled ✓
- Restart requirement is documented ✓
- P082 remains experimental/opt-in ✓
- P083 did not justify starting P084 ✓
- No new detector rule currently in progress ✓

**Stale claims:**
- `/healthz` or `/version` endpoint — still absent; documented as a gap in stabilization doc but not yet addressed.
- Phase 2+3 web features (issue-type explanations, drill-down routes) — not yet reflected in `web_ui_demo_guide.md` or `current_project_state_and_next_steps.md`.

---

## 7. Live Deployment Status

**Server process:**
- Host: `10.196.93.210:8000`
- Process: `python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000`
- PID: 47671
- Started: `Tue Jun 16 17:28:21 2026` (after PR #319 merge and restart from stabilization)
- Working directory: `/home/soroush/njit-thesis-auditor`

**Live route status:**

| Route | Status |
|---|---|
| `GET /` | 200 ✓ |
| `GET /rules` | 200 ✓ |
| `GET /help` | 200 ✓ |
| `GET /audits/sample` | 302 → / ✓ |
| `GET /healthz` | **404** (endpoint does not exist) |
| `GET /audits/{job_id}` | **BROKEN — will 500** (see below) |

**Critical broken state — templates vs. Python mismatch:**

The Jinja2 templates (`job.html`, `problem_group.html`) were modified on disk at
18:18–18:19 (Phase 2+3 changes). The uvicorn process loaded `web_app.py` at 17:28
and has NOT been reloaded. Jinja2 auto-reloads templates from disk but does NOT
reload Python filter registrations or route handlers.

Result:
- The running process does NOT have `issue_type_slug` registered as a Jinja2 filter.
- The running process does NOT populate `category_summary` in the template context.
- The running process does NOT have the new `issue_type_problem_page` route.
- Rendering any audit result page will raise `TemplateRuntimeError: No filter named 'issue_type_slug'`, producing a 500 response.

**Action required:** restart the uvicorn/tmux process after committing (or at minimum
after verifying the working tree is importable). Do NOT restart against only partially
applied changes.

**No version/commit endpoint:** the live server has no `/healthz` or `/version` route
to confirm which code revision is running. This remains an unaddressed hardening gap.

---

## 8. Test Coverage Summary

| Area | Files | Notes |
|---|---|---|
| Upload validation (type, size, path) | `test_upload_handling.py` | ✓ |
| URL audit / SSRF protection | `test_url_audit.py` | ✓ |
| PDF-only web UI | `test_web_app.py` | ✓ |
| Runtime cleanup / job expiry | `test_web_app.py` | ✓ |
| PDF inline serving | `test_web_app.py` | ✓ |
| Highlighted PDF safety / invalid bbox | `test_web_app.py` | ✓ |
| PDF link crawl non-500 | `test_finding_actionability.py` (untracked), `test_web_app.py` | ✓ |
| Mobile/desktop parity | `test_mobile_desktop_consistency.py` | ✓ |
| Action kinds / highlight fallback | `test_finding_actionability.py` (untracked) | ✓ |
| Issue-type humanization / explanation | `test_issue_type_explanations.py` (untracked) | ✓ |
| Category/rule/issue-type drill-down | `test_problem_drilldown.py` (untracked) | ✓ |
| Report view rendering | `test_report_view.py` | ✓ |
| Privacy-safe comments | `test_polished_comments.py` | ✓ |
| No raw LaTeX leak | `test_issue_type_explanations.py` (untracked) | ✓ |
| CLI/report export | `test_cli.py`, `test_report_outputs.py` | ✓ |
| Detector rules P001–P083 | `test_pdf_rules.py`, `test_p0XX_*.py` | ✓ |
| Results-page wording | `test_results_page_wording.py` | ✓ |

**Gaps (unchanged from PR #318 stabilization):**
- No Playwright / browser-engine responsive layout tests.
- Browser-native PDF preview/download behavior is not fully controllable in tests.
- No deployment/version endpoint, so CI cannot assert the live server's running revision.
- Stash content (`pdf_body_spacing.py`, `pdf_font_compliance.py` changes) has not been
  reviewed or tested since it was stashed.

---

## 9. Remaining Risks

| Risk | Severity | Status |
|---|---|---|
| Live server 500s on audit result pages | **Critical** | Server must be restarted after committing |
| Phase 2+3 work uncommitted | **High** | 10 modified files + 8 new files, 1455 tests passing locally |
| Stash overlaps with working tree | **Medium** | `polished_comments.py` and `report_view.py` in both; conflicts if applied now |
| PR #311 and #305 conflicting | **Medium** | Need rebase after Phase 2+3 is committed |
| No `/healthz` or `/version` endpoint | **Low** | Cannot confirm live revision programmatically |
| No Playwright tests | **Low** | CSS layout parity on real browsers is untested |
| `docs/pdf-finding-location-clarity-audit` branch | **Low** | 1 local-only doc commit; unknown if still relevant |
| Stale local backup branches | **Low** | `backup/*`, `ux/pdf-only-web-ui`, `ux/simplify-pdf-only-website` — safe to delete but not urgent |

---

## 10. Recommended Next Actions (Priority Order)

### Immediate (before any live testing)

1. **Restart the live server** — the current process is serving broken mixed-state templates.
   After committing (step 2) or confirming all Phase 2+3 files are in place:
   ```bash
   # in tmux or screen:
   python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
   ```

### Short-term (before new feature work)

2. **Commit and push Phase 2+3 work** — stage all 10 modified files and 8 new files,
   create a descriptive commit (or two: one for Phase 2, one for Phase 3), and push
   as a PR (e.g., PR #320 or #321).

3. **Merge PR #312** (expired audit message) — it is MERGEABLE, unrelated to Phase 2+3,
   and has 90 new tests.

4. **Rebase PR #311 and PR #305** onto the updated main (after Phase 2+3 is merged).
   Both are single-commit PRs and should rebase cleanly against the new main.

5. **Inspect stash** — review `stash@{0}` contents carefully. The `pdf_body_spacing.py`
   and `pdf_font_compliance.py` changes are not in the current working tree and may
   represent unreleased detector refinements. Decide whether to apply, discard, or
   create a separate branch.

### Medium-term

6. **Add `/healthz` endpoint** — a simple `{"status": "ok", "commit": GIT_HASH}` response
   would allow live-server verification without shell access.

7. **Clean up stale local branches** — delete `ux/pdf-only-web-ui`,
   `ux/simplify-pdf-only-website`, and the `backup/*` branches. Inspect
   `docs/pdf-finding-location-clarity-audit` first.

8. **Update `web_ui_demo_guide.md` and `current_project_state_and_next_steps.md`**
   to document Phase 2+3 features after commit.

### Longer-term

9. **Playwright/browser parity tests** — server-rendered HTML parity is tested; visual/CSS
   layout on real device sizes is not.

10. **Do not start P084** until the above steps are complete and the repository is clean.

---

## 11. Safe to Proceed?

**No — not yet.**

The live server is currently returning 500 errors on audit result pages due to the
template/Python mismatch. This must be fixed (server restart) before any live testing.

The Phase 2+3 feature work is complete and passing all 1455 tests, but it exists only
in the uncommitted working tree. Committing it, restarting the server, and verifying
the live result page renders correctly are the next three required steps before the
repository is in a clean, shippable state.

Once those three steps are done and PR #312 is merged:

- Tests: 1455 passing ✓ (will stay green)
- Live server: operational ✓ (after restart)
- All features tested and documented ✓
- No uncommitted critical work ✓
- Safe to start the next PR cycle ✓
