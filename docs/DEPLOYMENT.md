# Deployment

This is the canonical, consolidated deployment doc. The older
`docs/status/live_deployment_checklist.md` has the full historical detail (including a
superseded manual-tmux fallback procedure and dated verification snapshots) and is kept for
reference, but this file is what to follow.

**This audit (2026-07-13) did not touch the live server or port 8000** — that was an explicit
constraint of the task that produced this document. Nothing below was executed as part of this
pass; it is a cleaned-up transcription of already-established, working procedure.

## Supervision model

The live web UI runs as a **user-level systemd service**, not a manual process:

- **Service name:** `thesis-auditor-web.service` — a *user* unit. Always use
  `systemctl --user ...`, never `sudo systemctl ...`.
- **Unit file:** `~/.config/systemd/user/thesis-auditor-web.service` (host-specific, not
  committed to this repo — template below).
- **Serves from a dedicated deploy worktree**, never from a developer's day-to-day `main`
  checkout. Keeping deploy and dev checkouts separate means the live server never picks up
  someone else's uncommitted in-progress edits.
- **`Restart=always`** (not `on-failure`): systemd treats a clean `SIGTERM` the same whether it
  was an intentional stop or something else, so `on-failure` would leave the service down after
  an unintended `SIGTERM`. This was verified directly on the host that manages this deployment;
  `Restart=always` still respects an explicit `systemctl --user stop`.
- **Reboot persistence** requires `loginctl enable-linger <user>` so the user systemd instance
  (and this service) starts at boot without an interactive login.

## Clean-worktree requirement

**Never deploy from a dirty or stale worktree.** Before pointing the service at a new commit:

1. The deploy worktree must have `git status --short` produce no output (nothing uncommitted,
   nothing untracked left behind by a prior debugging session).
2. The commit being deployed must be an ancestor of `origin/main` (normally `origin/main` itself,
   fast-forwarded) — not a local-only commit, not a rebase in progress.
3. All three validation gates below must be green **on that exact commit**, not "close enough."

```bash
cd <deploy-worktree>
git fetch origin
git status --short          # must be empty
git checkout main
git pull --ff-only origin main
git rev-parse HEAD          # this is the SHA that must show up in /version after restart
ruff check .
mypy src
python -m pytest -q
```

Do not restart the live server on a commit that fails any of these.

## Restart procedure

```bash
systemctl --user restart thesis-auditor-web.service
sleep 3
curl -s http://127.0.0.1:8000/version   # confirm commit + a fresh process_start_time
```

## Status / logs

```bash
systemctl --user status thesis-auditor-web.service
journalctl --user -u thesis-auditor-web.service -n 100 --no-pager
```

## Stop / start (intentional maintenance)

```bash
systemctl --user stop thesis-auditor-web.service     # the only clean way to keep it down
systemctl --user start thesis-auditor-web.service
```

A bare `kill -TERM <pid>` will **not** stay down — `Restart=always` relaunches it (bounded by
`StartLimitBurst=5` / `StartLimitIntervalSec=60`).

## Smoke test after restart

1. `GET /healthz` → `200`, `{"ok": true, ...}`.
2. `GET /version` → `commit` equals the SHA from step 1 of the clean-worktree checklist above.
   If `commit` is `"unknown"`, the process was started outside the git checkout — treat as a
   failed deploy.
3. `GET /` and `GET /rules` → `200`.
4. Run one built-in sample audit (`POST /audits/sample` with a known `sample_id`) and confirm the
   job page loads and produces findings — this catches import-time/route-table regressions that a
   bare `/healthz` won't.

## Rollback

If the smoke test fails: `git checkout <previous-known-good-SHA>` in the deploy worktree, confirm
`git status --short` is empty, then repeat the restart + smoke-test steps above against that SHA.
Do not attempt a partial/manual file-level rollback inside the deploy worktree.

## Never do this

- Never edit files directly inside the deploy worktree to "hotfix" something — merge through a
  normal PR to `main`, then update the deploy worktree to that merged commit and restart.
- Never start a bare `nohup uvicorn ...` or an ad hoc tmux process against port 8000 "just for
  now" — it has no supervisor and a lost terminal/reboot/`SIGTERM` will silently take the site
  down. If you need an ad hoc instance for local debugging, use a different port and a scratch
  `NJIT_AUDITOR_WEB_RUNTIME_DIR`.
- Never restart after only "Python route tables / Jinja registrations are created at import
  time" — template auto-reload is not sufficient for route, Jinja-global, filter, or
  startup-config changes; a restart is required.

## Generic systemd unit template

Substitute the absolute paths for the deploy worktree and its venv on the target host — nothing
here is secret.

```ini
[Unit]
Description=NJIT Thesis Auditor Web GUI
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/path/to/deploy-worktree
Environment=PYTHONPATH=/path/to/deploy-worktree/src
Environment=NJIT_AUDITOR_WEB_RUNTIME_DIR=/path/to/deploy-worktree/.runtime/web_audits
ExecStart=/path/to/venv/bin/python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5

[Install]
WantedBy=default.target
```

After creating/editing: `systemctl --user daemon-reload`, then
`systemctl --user enable --now thesis-auditor-web.service`, then
`loginctl enable-linger <user>`.

## Full historical detail

`docs/status/live_deployment_checklist.md` retains the manual-tmux fallback procedure (for hosts
without a user systemd instance) and dated verification snapshots. Treat any SHA/PR/test-count
numbers in that file as historical, not current — see `docs/status/CURRENT_STATUS.md` instead.
