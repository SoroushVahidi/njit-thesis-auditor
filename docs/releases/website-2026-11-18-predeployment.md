# Website deployment plan: November 18, 2026

This is a preparation record, not deployment authorization. The verified target is
`35ed4e01cf09cab9fafeb179a5cecaa71c0d736b`. Production currently serves
`1838fc5214be2d8d93a4af9e989b3489742cc71a` from the clean, detached
`njit-thesis-auditor-clean-worktrees/live-current-main` worktree under the active
user service `thesis-auditor-web.service`. `/healthz`, `/version`, `/`, `/rules`
and `/sample.pdf` responded successfully during this read-only assessment.

Only PRs #665 and #666 separate this deployed revision from the target. They
change shared audit rules, explanations, reports, and tests. `pyproject.toml`,
service configuration, database schema, and installer-link configuration do not
change. The target tree is identical to the locally validated combined PR head:
12,185 nonconfidential Python 3.12 tests passed, one skipped; focused Python
3.10/3.11, browser, Ruff, mypy, hosted privacy and private finding comparisons
passed. Oscar yielded 442 findings and Chao 306, with no unexplained changes.

## Predeployment gate and rollback checkpoint

On the deployment host, immediately before a separately authorized deployment:

1. Confirm `origin/main` still resolves to the target, both PRs are merged, and
   the target tree still matches the validated tree. Revalidate if it does not.
2. Confirm `/version` still reports the previous SHA and `/healthz` is healthy.
   Confirm `systemctl --user show thesis-auditor-web.service -p ActiveState
   -p WorkingDirectory` identifies the dedicated worktree. Ensure no active
   audit would be interrupted by the planned restart.
3. In the deploy worktree, confirm `git status --short` is empty and HEAD is
   detached. Record the previous SHA, unit state and current `/version` response
   in protected local deployment notes. Preserve `.runtime/web_audits`; it may
   contain student uploads. Do not copy it into Git, CI or release artifacts.
4. Confirm the service Python is 3.12 and
   `/home/soroush/njit-thesis-auditor-venv/bin/python -m pip check` succeeds.
   No dependency install or database migration is expected for this delta.
5. Check that analytics remains unconfigured and the current Windows installer
   link retains its existing state. Do not activate either as part of this deploy.

## Deployment commands, only after authorization

```bash
cd /home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/live-current-main
git fetch origin main
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor HEAD 35ed4e01cf09cab9fafeb179a5cecaa71c0d736b
git switch --detach 35ed4e01cf09cab9fafeb179a5cecaa71c0d736b
git status --short
git rev-parse HEAD
systemctl --user restart thesis-auditor-web.service
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/version
```

Stop if any precondition fails. The checkout and restart commands above were
**not** run while preparing this plan. The service venv needs no update when
`pyproject.toml` remains unchanged; if that premise changes, follow
`docs/DEPLOYMENT.md` and repeat exact-source validation first.

## Postrestart smoke and rollback

Require `/healthz` healthy, `/version.commit` equal to the target, and
`/version.environment` equal to `production`. Require HTTP 200 on `/`, `/rules`,
`/help`, `/about`, and `/sample.pdf`. Use only the generated synthetic sample
for a fresh upload. Confirm completion, finding cards, JSON, Markdown, text,
student PDF, original and highlighted PDF downloads, and an expected error for
an invalid upload. Check that Windows download presentation and analytics remain
in their predeployment state. Do not upload a dissertation for this smoke test.

Rollback triggers include failed health/version checks, failed synthetic audit
or export, unexpected detector changes, privacy leakage, or service instability.
Use the recorded previous SHA (currently `1838fc5214be2d8d93a4af9e989b3489742cc71a`):

```bash
cd /home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/live-current-main
git status --short
git switch --detach 1838fc5214be2d8d93a4af9e989b3489742cc71a
systemctl --user restart thesis-auditor-web.service
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/version
```

Confirm the live SHA again after rollback. Leave runtime audit data untouched.
Follow `docs/DEPLOYMENT.md` for the canonical service procedure.
