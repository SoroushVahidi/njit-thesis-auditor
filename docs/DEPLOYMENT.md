# Deployment

The homepage Windows installer link defaults to disabled. See
[Windows beta publication](PUBLIC_WINDOWS_RELEASE.md) for hosted build/smoke checks,
HTTPS artifact verification and release metadata. Installer lifecycle qualification
is not a beta publication gate. Full NJIT rule distribution
is authorized; keep the source repository private.
Do not enable the link merely because the web implementation passes tests.

This is the canonical, consolidated deployment doc. The older
`docs/status/live_deployment_checklist.md` has the full historical detail (including a
superseded manual-tmux fallback procedure and dated verification snapshots) and is kept for
reference, but this file is what to follow.

**Historical provenance:** the 2026-07-13 documentation audit transcribed the
established procedure without touching the live server or port 8000. That dated
statement is not evidence of the current deployment. Use the checks below when
performing an authorized deployment; documentation edits or passing checks alone
do not authorize a restart or release. For isolated development and checkout roles,
see the [development guide](DEVELOPMENT.md).

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
git branch --show-current   # must print nothing: the live worktree stays detached
git switch --detach <merged-origin-main-sha>   # the exact squash-merge SHA, never a branch
git rev-parse HEAD          # this is the SHA that must show up in /version after restart
# Hydrate the four approved historical website samples from Git LFS before validation.
git lfs pull --include='data/raw/ester/250218 Cibaku Elson First Review.pdf,data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf,data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf,data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf' --exclude=''
PYTHONPATH=src python -c 'from njit_auditor.web_samples import get_public_sample; [get_public_sample(f"ester_sample_{letter}") for letter in "abcd"]'
# If runtime dependencies changed, sync the service venv as shown below before gates.
ruff check .
mypy src
python -m pytest -q
```

Do not restart the live server on a commit that fails any of these.

Deployment never touches the shared review ledger
(`main/data/evaluation/private/ester_review_ledger`). Authority replays run
against a scratch copy with `--ledger-root <scratch>`, never `--shared-ledger`.

When the deployed commit changes runtime dependencies in `pyproject.toml`, sync
the **service's venv** after checking out the exact commit and before running
the gates or restarting. For the combined student PDF report, this installs
`reportlab>=4.0.0`, which is required at web-app import time:

```bash
<service-venv>/bin/python -m pip install -e .
<service-venv>/bin/python -c "import reportlab; import njit_auditor.student_pdf_report"
```

The deployment uses a worktree and `PYTHONPATH` pointing at its `src/` directory.
An isolated non-editable wheel from this tree lacks repository rule/spec JSON
and web HTML templates. It does not provide an equivalent standalone web
installation. Keep the established worktree layout; see
[reproducibility](REPRODUCIBILITY.md) for the verified packaging boundary.

## Restart procedure

```bash
systemctl --user restart thesis-auditor-web.service
sleep 3
curl -s http://127.0.0.1:8000/version   # confirm commit + a fresh process_start_time
```

## Reviewer and administrator HTTPS

Use a dedicated HTTPS hostname with a browser-trusted certificate. If reviewers already have
tailnet access and the web host can use a tag-based identity, an approved
[Tailscale HTTPS Service](https://tailscale.com/docs/features/tailscale-services) can terminate
TLS on the web host and proxy to `http://127.0.0.1:8000`. Use the Service's own hostname so its
cookies are scoped separately from other apps on the host.

- Preserve the browser-facing `Host` header and have the TLS proxy set `X-Forwarded-Proto` to
  `https`. For the same-host proxy, run Uvicorn with
  `--proxy-headers --forwarded-allow-ips=127.0.0.1`. Trust only the proxy's connection address.
- In the service environment file, set `NJIT_AUDITOR_REVIEWER_HTTPS_ENABLED=1` and unset
  `NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED`. The plaintext listener can still serve public pages.
  Preserve `NJIT_AUDITOR_ADMIN_DB_PATH` and `NJIT_AUDITOR_ADMIN_SESSION_KEY`. Reviewer accounts and
  stored sessions keep their existing format. Reviewers sign in again on the new hostname so
  the browser receives a Secure session cookie there.
- Once HTTPS is verified, set `NJIT_AUDITOR_ADMIN_ENABLED=1` and
  `NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED=1` for administrator access. Allow a general feedback
  request of at least 4 MiB plus 16 KiB through the proxy. The application creates the feedback
  table in the existing SQLite database and stores attachments there.
- Before sharing the URL, use synthetic accounts and files to check reviewer sign-in, a feedback
  submission, history after sign-in, and administrator attachment retrieval on the deployed
  HTTPS endpoint.

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
   `environment` should be `"production"`; `"local-dev"` means the unit does not set
   `NJIT_AUDITOR_WEB_ENVIRONMENT` (see the unit template below). Changing the unit requires
   `systemctl --user daemon-reload` and a restart, so do it in a planned maintenance step.
   As verified on 2026-10-12, the live unit sets this variable and `/version` reports
   `"production"`.
3. `GET /` and `GET /rules` → `200`.
4. Download `/sample.pdf`, then upload it with `POST /audits` and confirm the job completes
   and reports download. Confirm legacy URL/sample POSTs and mixed file/URL submissions redirect
   to the upload-required error page without creating a job. Check Help, Rules, About, and the
   unchanged published Windows installer link.

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
# Label reported by /version; without it /version says "local-dev".
Environment=NJIT_AUDITOR_WEB_ENVIRONMENT=production
Environment=PYTHONPATH=/path/to/deploy-worktree/src
Environment=NJIT_AUDITOR_WEB_RUNTIME_DIR=/path/to/deploy-worktree/.runtime/web_audits
# Optional: retention window (default 86400) and sweep interval (default 300).
# Environment=NJIT_AUDITOR_WEB_JOB_TTL_SECONDS=3600
# Environment=NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS=300
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
