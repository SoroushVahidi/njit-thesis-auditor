# Live Deployment Checklist

## Current supervision: systemd user service (as of 2026-07-04)

The live web UI is supervised by a **user-level systemd service**, not a manual `nohup`
process or a tmux session anyone has to keep alive. This replaced a manual `nohup uvicorn ...`
process launched inside a `thesis-auditor-web` tmux session, which caused an outage on
2026-07-04: the process received a clean `SIGTERM`, exited gracefully, and nothing restarted
it — the site was down until an operator noticed and manually relaunched it.

- **Service name:** `thesis-auditor-web.service` (user unit — do not confuse with a system-wide
  unit; it is only visible via `systemctl --user`, not `systemctl`/`sudo systemctl`).
- **Unit file:** `~/.config/systemd/user/thesis-auditor-web.service` (host-specific, not
  committed to this repo — see "Generic unit template" below for a version to adapt on a new
  host).
- **Live worktree it serves from:** the dedicated deployment worktree (a
  `njit-thesis-auditor-clean-worktrees/live-current-main`-style checkout), *not* the `main`
  working copy any engineer might have open for day-to-day development. Keeping deploy and
  dev checkouts separate avoids the live server picking up someone else's in-progress edits.
- **Reboot persistence:** requires `loginctl enable-linger <user>` (already enabled on this
  host) so the user's systemd instance — and this service — starts at boot without requiring
  an interactive login.

### Check status

```bash
systemctl --user status thesis-auditor-web.service
journalctl --user -u thesis-auditor-web.service -n 100 --no-pager   # recent logs
curl -s http://127.0.0.1:8000/version
```

### Restart (intentional maintenance)

```bash
systemctl --user restart thesis-auditor-web.service
sleep 3
curl -s http://127.0.0.1:8000/version   # confirm commit + fresh process_start_time
```

### Stop / start

```bash
systemctl --user stop thesis-auditor-web.service
systemctl --user start thesis-auditor-web.service
```

`systemctl --user stop` is the only way to intentionally take the service down without it
restarting itself — a bare `kill -TERM <pid>` on the worker process will **not** stay down;
the unit's `Restart=always` policy relaunches it (bounded by `StartLimitBurst=5` per
`StartLimitIntervalSec=60` to avoid an infinite crash loop if the app is genuinely broken).

### Update the deployed worktree safely

1. In the live worktree, fetch and check out the new target commit (fast-forward only;
   confirm `ruff check .`, `mypy src`, and `python -m pytest` are green on that exact SHA
   first — see the validation checklist further down this file).
2. `systemctl --user restart thesis-auditor-web.service`.
3. Confirm `/version` reports the new SHA on both `127.0.0.1:8000` and the LAN address.

Do not edit files inside the live worktree directly to "hotfix" something — merge the fix to
`main` through a normal PR, then update the worktree to that merged commit and restart.

### Avoiding orphan/manual uvicorn processes

- Never start the app with a bare `nohup ... &` or inside a tmux pane "just for now" — that
  process has no supervisor, and killing/losing it (a `SIGTERM`, a host reboot, a closed
  terminal) will silently take the site down with nothing to bring it back.
- Before starting anything manually for local debugging, always check
  `systemctl --user status thesis-auditor-web.service` and `ss -ltnp | grep 8000` first —
  if the service already owns port 8000, do not launch a second process on it.
- If you must run an ad hoc instance for testing, use a different port and a scratch
  `NJIT_AUDITOR_WEB_RUNTIME_DIR`, never port 8000.

### Generic unit template

The host-specific unit at `~/.config/systemd/user/thesis-auditor-web.service` follows this
shape (substitute the absolute paths for the live worktree and venv on your host; nothing
here is secret):

```ini
[Unit]
Description=NJIT Thesis Auditor Web GUI
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/path/to/live-worktree
Environment=PYTHONPATH=/path/to/live-worktree/src
Environment=NJIT_AUDITOR_WEB_RUNTIME_DIR=/path/to/live-worktree/.runtime/web_audits
ExecStart=/path/to/venv/bin/python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5

[Install]
WantedBy=default.target
```

After creating or editing this file: `systemctl --user daemon-reload`, then
`systemctl --user enable --now thesis-auditor-web.service`, then
`loginctl enable-linger <user>` for reboot persistence.

**Why `Restart=always` and not `Restart=on-failure`:** `on-failure` does not restart a
service that exits on `SIGTERM` — systemd treats `SIGTERM` as its own default graceful-stop
signal, so a clean `SIGTERM` exit looks identical to an intentional `systemctl stop`, whether
or not that's what actually happened. This was verified directly on this host: sending a bare
`SIGTERM` to the worker PID under `Restart=on-failure` left the service `inactive (dead)`
with the port free, reproducing the original outage. Switching to `Restart=always` (which
still respects an explicit `systemctl stop`) restarted the service within `RestartSec` after
the same test.

## Manual / tmux fallback (historical, superseded by the systemd service above)

The steps below describe the previous manual tmux-based process. They are kept for hosts
where a user-level systemd instance is not available (see the incident-response task that
introduced the service above for the `systemctl --user status` / `loginctl` checks to run
first). Prefer the systemd service on any host where it's already set up.

Use this checklist whenever the live web UI needs to be (re)started from a freshly merged
`main`. On this host the persistent tmux session is named **`web`** (README also documents
`thesis-auditor-web` as an alternate convention — use whichever session already exists;
do not create a duplicate listener on port 8000).

**Last verified against host state:** 2026-07-02 (`main` at `921d0df` after PR #409 merge; live
`/version` still reports `70dcd95` — behavior baseline from PR #408, docs-only delta in #409).

### 2026-07-02 verification snapshot (post–PR #409 merge)

| Check | Result |
|---|---|
| Merged `main` SHA | `921d0df0dd0507ea816d57851d27f3d1b849762a` (PR [#409](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/409) docs sync) |
| `GET /version` (`127.0.0.1:8000`, `localhost:8000`, `10.196.93.210:8000`) | `commit=70dcd952871c993814437edf1dcf1f2280b47dc7`, `branch=main`, `process_start_time=2026-07-02T18:03:41.571263+00:00` |
| `GET /healthz` | `{"ok":true,"app":"njit-thesis-auditor","status":"healthy"}` |
| Running process cwd | `/home/soroush/njit-thesis-auditor/main` |
| Fresh built-in sample audit | **Not run** in this verification pass |
| Interpretation | Live runtime matches the **behavior baseline** (`70dcd95`, PR #408). PR #409 changed docs/manifest only, so no behavior regression is expected, but `/version` will not show `921d0df` until the next restart/redeploy. |

**Next required action (optional for behavior, recommended for SHA parity):** restart per steps below so
`/version.commit` equals merged `main` (`921d0df`).

## 1. Confirm the commit being deployed

```bash
cd /home/soroush/njit-thesis-auditor
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Record this SHA — it is what `/version` must report after restart.

## 2. Confirm validation is green on this exact commit

```bash
ruff check .
mypy src
python -m pytest -q
```

Do not restart the live server on a commit that has not passed all three gates.

## 3. Inspect the existing server process

```bash
pgrep -af 'python -m uvicorn njit_auditor.web_app'
curl -s http://10.196.93.210:8000/version
readlink -f /proc/$(pgrep -f 'python -m uvicorn njit_auditor.web_app' | head -1)/cwd
```

Expect:

- command: `python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000`
- working directory: `/home/soroush/njit-thesis-auditor`
- `commit` in `/version` equal to step 1 SHA when already current

If already serving the target SHA, **skip restart**.

## 4. Stop the existing server (only the app process)

```bash
tmux capture-pane -t web -p | tail -20   # see what's currently running
```

Stop uvicorn from inside the session (`tmux send-keys -t web C-c`) rather than killing
unrelated processes by PID.

**Do not** delete user audit history:

- **Preserve** `.runtime/web_audits/` job directories unless an operator explicitly
  requests cleanup.
- Completed jobs also expire via `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` (default 24 h).

## 5. Start the server in the existing tmux session

```bash
tmux send-keys -t web "cd /home/soroush/njit-thesis-auditor && export PYTHONPATH=/home/soroush/njit-thesis-auditor/src NJIT_AUDITOR_WEB_RUNTIME_DIR=/home/soroush/njit-thesis-auditor/.runtime/web_audits && python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000 2>&1 | tee -a .runtime/uvicorn-8000.log" Enter
```

`PYTHONPATH` must point at this checkout's `src/` so code changes take effect without a
stale editable-install worktree.

## 6. Confirm the process came up

```bash
sleep 2
tmux capture-pane -t web -p | tail -10
pgrep -af 'python -m uvicorn njit_auditor.web_app'
```

Expect `INFO: Uvicorn running on http://0.0.0.0:8000` and a live PID.

## 7. Verify `/healthz` and `/version`

```bash
curl -s http://10.196.93.210:8000/healthz
curl -s http://10.196.93.210:8000/version
```

Expect HTTP 200; `commit` must equal the SHA from step 1. If `commit` is `"unknown"`,
the process was likely started outside the git checkout — treat as a deployment failure.

## 8. Verify core routes

- `GET /` — upload page (200)
- `GET /help`, `GET /rules` — load (200)
- `POST /audits/sample` with `sample_id=ester_sample_d` — redirects to a job page

Manual check URL: **http://10.196.93.210:8000/**

Runtime directory: `/home/soroush/njit-thesis-auditor/.runtime/web_audits`

## 9. Post-restart sample-audit verification

After warning-clarity deploys (#371–#372), spot-check `ester_sample_d`:

| Check | Expected |
|---|---|
| HTTP 200 on `/` and job page | Pass |
| `/version.commit` equals `main` | Pass |
| No P018 cards for `2026-04-30 12:45:08` timestamps | Gone (#372) |
| No P018 CHAPTER structural-label missing-page cards | Gone (#371) |
| P036 main cards short (no gap measurements in main comment) | Yes (#371) |
| P018 entry cards highlight when bbox exists | Yes (#371) |
| Legitimate P018/P036 TOC warnings on real entries | Still present |

Job JSON is at `.runtime/web_audits/{job_id}/report.json` (gitignored; not committed).

## 10. Record results

Capture: deployed SHA, PID, `/version` response, sample-audit pass/fail notes, and any
route failures. Fix and re-verify before reporting deployment complete.
