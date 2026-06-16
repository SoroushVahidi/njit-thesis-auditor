# Repository Stabilization After PR #318

- **Date:** 2026-06-16
- **Stabilization branch:** `chore/post-p318-stabilization`
- **Parity PR merged on main:** `9e54b7b` (`Fix mobile desktop UI parity (#318)`)

## 1. Baseline and Scope

This stabilization pass focused on repository cleanliness, documentation accuracy, validation,
runtime/process freshness, and live smoke confidence before any new feature work.

No detector logic, rule semantics, or raw guideline/data files were changed.

## 2. Unrelated Local Changes Set Aside

Before stabilization work, unrelated local changes were removed from the working tree and saved in:

- `stash@{0}` — `pre-stabilization unrelated local changes`

Files set aside:

- `docs/planning/full_repo_status_audit_after_p317.md`
- `src/njit_auditor/polished_comments.py`
- `src/njit_auditor/report_view.py`
- `src/njit_auditor/rules/pdf_body_spacing.py`
- `src/njit_auditor/rules/pdf_font_compliance.py`
- `tests/test_pdf_rules.py`
- `tests/test_report_view.py`

They were not mixed into the stabilization changes.

## 3. PR #318 Status

- **PR:** `#318` — <https://github.com/SoroushVahidi/njit-thesis-auditor/pull/318>
- **Status:** merged
- **Merge commit:** `9e54b7bfc437cb1a39b760f537b3918a52230e07`
- **Merged at:** `2026-06-16T21:19:05Z`

Pre-merge review result:

- Scope was limited to mobile/desktop parity fixes, PDF-link consistency, tests, and audit docs.
- The branch initially failed CI because two helpers used by the PR were only present as unstaged local edits.
- Those helpers were restored and committed in `730f73c` (`Restore web parity report view helpers`).
- After that fix, PR #318 CI passed and the PR was merged safely.

## 4. Documentation Updated

Updated to match the current stable public web behavior:

- `README.md`
- `docs/web_gui_mvp.md`
- `docs/web_ui_demo_guide.md`
- `docs/web_ui_manual_qa_checklist.md`
- `docs/status/current_project_state_and_next_steps.md`
- `docs/planning/mobile_desktop_consistency_audit.md`
- `docs/planning/gui_scope_and_design.md`
- `docs/planning/synthetic_web_demo_fixtures.md`
- `docs/status/full_repository_audit_after_p063.md`
- `docs/status/project_closeout.md`

Key doc corrections:

- public web UI is clearly documented as **PDF-only**
- CLI/source-audit support is documented as separate
- mobile and desktop are expected to show the same substantive results/actions
- PDF routes are documented as inline-serving where possible
- browser-native PDF behavior is documented as still partly browser/device-controlled
- uvicorn/tmux restart requirement is documented explicitly
- P082 remains experimental/opt-in
- P083 did not justify starting P084
- no new detector rule is currently being started

## 5. Runtime / Repository Hygiene

Checks performed:

- `git clean -nd` — no untracked cleanup candidates in the stabilization branch
- `.runtime/` confirmed gitignored
- `git ls-files .runtime` previously confirmed empty

Live-runtime cleanup performed before restart:

```bash
rm -rf .runtime/web_audits/*
```

## 6. Validation

Exact commands and results:

- `python -m pip install -e ".[dev]"` — passed
- `ruff check .` — passed (`All checks passed!`)
- `mypy src` — passed (`Success: no issues found in 91 source files`)
- `python -m pytest` — passed (`1319 passed, 1 warning in 8.87s`)

Final automated test count:

- `1319`

Remaining warning:

- `tests/test_upload_handling.py::test_duplicate_member_paths_rejected`
  emitted `zipfile`'s duplicate-member warning while intentionally building a malformed ZIP
  fixture for a rejection-path test. This is expected and harmless.

## 7. Live Restart and Smoke Test

The pre-existing live tmux/uvicorn process was stale:

- old tmux session start: `Tue Jun 16 15:23:47 2026`
- old uvicorn process start: same stale `15:23` launch window as the pre-restart tmux session

Fresh restart performed:

- tmux session killed
- stale uvicorn processes killed
- `.runtime/web_audits/*` cleared
- tmux service restarted with `./scripts/run_web_gui.sh 0.0.0.0 8000`

New live process:

- tmux session start: `Tue Jun 16 17:28:21 2026`
- uvicorn process start: `Tue Jun 16 17:28:21 2026`

This restart happened after PR #318 was merged. The stabilization branch itself contained only
documentation/README updates, so the executable web-app code used for the restart matched `main`.

Live routes checked:

- `/` — `200`
- `/help` — `200`
- `/rules` — `200`
- `GET /audits/sample` — `302` redirect to `/`

Fresh live upload smoke:

- uploaded `tests/fixtures/web_demo/issues_pdf.pdf`
- new live job: `Sr2_19CIoDMqhWXAxEHSYg`
- job status endpoint returned `state: complete`
- result page loaded successfully
- JSON and Markdown downloads returned `200`
- category problem page loaded
- rule problem page loaded
- rendered PDF links were requested directly and none returned `500`
- PDF responses did not force `attachment`

Mobile/desktop live verification:

- same job page was fetched with mobile and desktop user-agent profiles
- representative profiles matched the parity audit targets: `390x844` and `1440x900`
- key result tokens were present in both
- rendered link sets were identical between the two HTML responses
- category/rule problem pages and PDF links remained reachable from both

## 8. Routes Covered

Automated parity coverage:

- `/`
- `POST /audits`
- `/audits/{job_id}`
- `/audits/{job_id}/problems/category/{category}`
- `/audits/{job_id}/problems/rule/{rule_id}`
- `/audits/{job_id}/pdf`
- `/audits/{job_id}/pdf#page=N`
- `/audits/{job_id}/pdf/highlighted?...`
- `/help`
- `/rules`

Live HTTP smoke coverage in this stabilization pass:

- `/`
- `/help`
- `/rules`
- `GET /audits/sample`
- `POST /audits`
- `/audits/{job_id}`
- `/audits/{job_id}/status`
- `/audits/{job_id}/download/json`
- `/audits/{job_id}/download/markdown`
- `/audits/{job_id}/problems/category/{category}`
- `/audits/{job_id}/problems/rule/{rule_id}`
- `/audits/{job_id}/pdf`
- rendered `/audits/{job_id}/pdf#page=N` links
- rendered `/audits/{job_id}/pdf/highlighted?...` links

## 9. Open PR / Branch Audit

Open PRs at the end of this pass:

| PR | Title | Status | Action | Reason |
|---|---|---|---|---|
| `#312` | Clarify expired audit result message | Open, clean, mergeable | Retained | Active PR with passing CI and unique work |
| `#311` | Add sub-page location labels for PDF findings | Open, conflicting | Retained | Contains unresolved unmerged work; not safe to close/delete automatically |
| `#305` | Add example NJIT thesis URL to web upload page | Open, conflicting | Retained | Appears stale/redundant because an example URL is already on `main`, but the PR branch is conflicting; not auto-closed without manual review |

Branch cleanup actions:

| Branch | Status | Action | Reason |
|---|---|---|---|
| `fix/audits-sample-get-guard` | PR `#317` merged | Deleted local + remote | Safe merged branch cleanup |
| `fix/student-facing-comment-wording` | PR `#318` merged | Remote already absent after merge | No further action needed |
| `backup/*` branches | Local only, uncertain | Retained | Not safe to delete blindly |
| `feature/example-thesis-url` | Head of open PR `#305` | Retained | Open PR head |
| `feature/subpage-location-labels` | Head of open PR `#311` | Retained | Open PR head |
| `ux/expired-job-message` | Head of open PR `#312` | Retained | Open PR head |

## 10. Remaining Risks

- True browser pixel-level parity still is not formally proven because automated parity uses `TestClient`, not Playwright or another real layout engine.
- Browser-native PDF preview behavior can still vary by local browser settings, extensions, or installed viewers.
- There is still no dedicated `/version` or `/healthz` endpoint for deployment-state verification.
- The stale-process risk is reduced by documentation and restart discipline, but it still exists if code changes are made without restarting uvicorn/tmux.

## 11. Recommended Next Step

Do not start P084 or any new detector rule yet.

Recommended next work:

1. Review and decide PR `#312`.
2. Do a small deployment-hardening PR for `/healthz` or `/version`.
3. If presentation confidence is still a concern, add a lightweight real-browser responsive smoke pass on top of the current `TestClient` parity tests.
