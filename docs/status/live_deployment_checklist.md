# Live Deployment Checklist

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
