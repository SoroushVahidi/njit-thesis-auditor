# Live Deployment Checklist

Use this checklist whenever the live web UI needs to be (re)started from a freshly merged
`main`. It assumes the persistent `tmux` session convention already used on this host
(session name `web`; README's documented convention is `thesis-auditor-web`, but the
session actually running on this machine is named `web` — use whichever session already
exists rather than creating a duplicate). Confirmed against this host's actual state on
2026-06-19: the `web` tmux session exists but its `uvicorn` process had been terminated
(no process listening on port 8000, `curl http://localhost:8000/` returns no response).

## 1. Confirm the commit being deployed

```bash
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Record this SHA — it is what `/version` must report after restart, and what the final
report's "live commit matches main" field is checked against.

## 2. Confirm validation is green on this exact commit

```bash
ruff check .
mypy src
python -m pytest -q
```

Do not restart the live server on a commit that has not passed all three gates.

## 3. Stop any existing server process

```bash
tmux capture-pane -t web -p | tail -20   # see what's currently running, if anything
```

If a `uvicorn` process is running in the session, stop it from inside the session
(`tmux send-keys -t web C-c`) rather than killing it externally by PID, so the session's
shell stays usable for the next start command.

## 4. Clear stale runtime artifacts

```bash
rm -rf .runtime/web_audits/*
```

This removes completed/expired job directories and uploaded-file temp data from prior
runs. Do not remove `.runtime/` itself (other tooling, e.g. `web_demo_smoke.sh`, expects
the directory to exist) — only its contents.

## 5. Start the server in the existing tmux session

```bash
tmux send-keys -t web "cd $(pwd) && python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000 2>&1 | tee -a .runtime/uvicorn-8000.log" Enter
```

Using `tmux send-keys` (not a new detached session) preserves the existing persistent
session that other tooling/operators already expect to find.

## 6. Confirm the process came up

```bash
sleep 2
tmux capture-pane -t web -p | tail -10
ps aux | grep -i uvicorn | grep -v grep
```

Expect `INFO: Uvicorn running on http://0.0.0.0:8000` in the pane and a live PID in the
process list. Record the PID and the wall-clock start time for the final report.

## 7. Verify `/healthz`

```bash
curl -s http://localhost:8000/healthz
```

Expect HTTP 200 and `{"ok": true, "app": "njit-thesis-auditor", "status": "healthy"}`
(field order may vary). This must succeed even with zero audit jobs in the runtime
directory.

## 8. Verify `/version` matches the deployed commit

```bash
curl -s http://localhost:8000/version
```

Expect HTTP 200 with `commit` equal to the SHA recorded in step 1, plus `branch`,
`process_start_time`, `python_version`, and `environment` fields. If `commit` is
`"unknown"`, treat that as a deployment-verification failure, not a pass — it usually
means the process was started from a working directory without `.git`, not that git
metadata is genuinely unavailable.

## 9. Verify core routes and behavior

- `GET /` — upload page loads (200).
- `GET /help` — loads (200).
- `GET /rules` — loads; "What it checks" is collapsed by default behind a `<details>`
  toggle; "How to correct it" is visible without expanding anything.
- `POST /audits/sample` — submits a built-in sample PDF; follow the redirect to the job
  page.
- Job/result page — status banner, summary cards, grouped problems, and individual
  findings render with no 500s.
- A category page, a rule page, and an issue-type page each load for the same job.
- `GET /audits/{id}/report.json` and `GET /audits/{id}/report.md` — both return 200.
- `GET /audits/{id}/pdf` (and the page-anchored variant) — serves inline where possible.
- For at least one finding with a drawable bounding box, confirm a real visible highlight
  renders on the PDF page (not just a page jump). For at least one finding without a
  drawable bbox, confirm it renders as explanation-only — no page-only action button.
- Spot-check that mobile and desktop viewports show the same substantive result
  content/actions for the same job (mobile/desktop parity).

## 10. Record results for the final report

Capture: final `main` SHA, PID, process start time, `/healthz` response, `/version`
response (and whether `commit` matches the SHA from step 1), and a pass/fail note for
each route checked in step 9. Any failure here should be fixed and re-verified before the
deployment is considered complete — do not report success with an unresolved 500 or a
`commit` mismatch.
