# Web Upload UI Operations Guide

- **Date:** 2026-06-16
- **Baseline commit:** `9e54b7b` (PR #318 — mobile/desktop parity fixes)
- **Scope:** Current public FastAPI web UI behavior and operations
- **Current public input surface:** PDF upload, public PDF URL audit, built-in sample PDF audit

## 1. Current Stable Scope

The public web UI is **PDF-only**.

It supports:

- uploading a local PDF
- auditing a direct public PDF URL
- auditing a built-in sample PDF when samples are configured on the server

It does **not** currently expose TeX, ZIP, or DOCX inputs in the public browser UI.
Those workflows remain separate CLI or internal tooling paths.

For the same uploaded PDF/job, mobile and desktop should show the same substantive content
and the same available actions. Responsive differences are limited to layout changes such as
stacking, wrapping, spacing, and column count.

## 2. Running Locally

```bash
./scripts/run_web_gui.sh
# or
python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`.

For localhost-only use:

```bash
./scripts/run_web_gui.sh 127.0.0.1
```

## 3. Persistent tmux Service

Start:

```bash
tmux new -d -s thesis-auditor-web \
  'cd /home/soroush/njit-thesis-auditor && ./scripts/run_web_gui.sh'
```

Inspect logs:

```bash
tmux capture-pane -t thesis-auditor-web -p -S -200
tmux attach -t thesis-auditor-web
```

Restart:

```bash
tmux kill-session -t thesis-auditor-web 2>/dev/null || true
tmux new -d -s thesis-auditor-web \
  'cd /home/soroush/njit-thesis-auditor && ./scripts/run_web_gui.sh'
```

Stop:

```bash
tmux kill-session -t thesis-auditor-web
```

## 4. Critical Restart Rule

After changing any of the following, restart the uvicorn/tmux process:

- routes
- Jinja globals
- Jinja filters
- template helper registrations
- startup-time configuration
- environment-dependent behavior

Template auto-reload alone is **not** sufficient for those changes because Python route tables
and Jinja registrations are created at import time.

## 5. Environment Variables

| Variable | Default | Meaning |
|---|---|---|
| `NJIT_AUDITOR_WEB_RUNTIME_DIR` | `.runtime/web_audits` | Runtime job directory |
| `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` | `50` | Maximum PDF upload size |
| `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` | `86400` | Retention window for completed/failed jobs |
| `NJIT_AUDITOR_WEB_HOST` | `0.0.0.0` | Helper-script bind host |
| `NJIT_AUDITOR_WEB_PORT` | `8000` | Helper-script bind port |

## 6. Routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Upload page |
| `POST` | `/audits` | Start a PDF upload audit |
| `POST` | `/audits/url` | Start a public PDF URL audit |
| `POST` | `/audits/sample` | Start a built-in sample PDF audit |
| `GET` | `/audits/sample` | Guard redirect back to `/` |
| `GET` | `/audits/{job_id}` | Pending/running/completed/failed job page |
| `GET` | `/audits/{job_id}/status` | JSON polling endpoint |
| `GET` | `/audits/{job_id}/download/json` | JSON report download |
| `GET` | `/audits/{job_id}/download/markdown` | Markdown report download |
| `GET` | `/audits/{job_id}/problems/category/{category}` | Category problem page |
| `GET` | `/audits/{job_id}/problems/rule/{rule_id}` | Rule problem page |
| `GET` | `/audits/{job_id}/pdf` | Original PDF route |
| `GET` | `/audits/{job_id}/pdf/highlighted?...` | Highlighted PDF route |
| `GET` | `/help` | Help page |
| `GET` | `/rules` | Student-facing PDF rule reference |

## 7. User-Facing Behavior

### Upload page

The home page includes:

- PDF upload form
- public PDF URL form
- built-in sample PDF form
- supported-input wording that states the site is PDF-only
- privacy/local-processing wording
- navigation to `/help` and `/rules`

### Results page

Completed results include:

- status banner
- summary cards
- grouped problems
- individual findings
- filters
- polished comments
- suggested fixes
- issue-type labels/explanations
- `Open PDF page` or highlighted PDF links
- JSON/Markdown download links
- privacy note

Problem pages preserve the same substantive issue metadata and provide:

- examples
- issue-type explanation
- PDF links
- back links to the result page

## 8. PDF Route Behavior

The app serves PDF routes with inline `Content-Disposition` where possible.

Expected behavior:

- `/audits/{job_id}/pdf` should return the uploaded PDF without forcing `attachment`
- `#page=N` fragments should be safe to use in links
- `/audits/{job_id}/pdf/highlighted?...` should not 500 on normal linked inputs
- result/problem-page PDF links should open in a new tab where appropriate

Browser-native preview behavior can still vary by device, browser, extension, or local PDF settings.

## 9. Privacy and Safety

- Uploaded files live only under the runtime directory.
- `.runtime/` must remain gitignored.
- The web UI shows structural metadata only by default.
- JSON/Markdown downloads use basename-only paths.
- Public URL fetches are SSRF-guarded.
- Built-in samples should not be exposed publicly unless authorized.

Recommended cleanup before a live restart:

```bash
rm -rf .runtime/web_audits/*
```

## 10. Validation and QA

Automated parity coverage is documented in
`docs/planning/mobile_desktop_consistency_audit.md`.

Use:

- `docs/web_ui_demo_guide.md` for a concise end-to-end demo
- `docs/web_ui_manual_qa_checklist.md` for browser smoke checks

Representative viewport profiles for parity checks:

- mobile: `390x844`
- desktop: `1440x900`

## 11. Known Limits

- Browser PDF preview/download behavior is not fully app-controlled.
- Current automated parity tests use `TestClient`, not a real layout engine.
- No dedicated `/version` or `/healthz` endpoint is documented yet.
