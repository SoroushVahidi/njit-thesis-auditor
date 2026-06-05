# Web Upload UI — MVP Guide

The NJIT Thesis Auditor includes a FastAPI web application that lets users upload a PDF
dissertation and receive a formatted audit report in the browser — no CLI or Python knowledge required.

---

## Running locally

```bash
python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in a browser.

### Keeping it running in tmux

```bash
tmux new -s thesis-auditor-web
cd /path/to/njit-thesis-auditor
python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
# Detach with Ctrl-B D
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NJIT_AUDITOR_WEB_RUNTIME_DIR` | `.runtime/web_audits` | Directory where uploaded PDFs and reports are written. Must be gitignored. |
| `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` | `50` | Maximum upload file size in MB. |

---

## API routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Upload form |
| `POST` | `/audits` | Accept PDF upload; validate; start background audit; redirect to job page |
| `GET` | `/audits/{job_id}` | Job status page; auto-refreshes while running; shows findings when complete |
| `GET` | `/audits/{job_id}/status` | JSON polling endpoint (`state`, `finding_count`, timestamps) |
| `GET` | `/audits/{job_id}/download/json` | Download structured JSON report |
| `GET` | `/audits/{job_id}/download/markdown` | Download Markdown report |

---

## UX flow

1. User opens `/` and selects a PDF.
2. User clicks **Audit PDF**.
3. Server validates the file (extension, magic bytes, size limit) and starts a background job.
4. User is redirected to `/audits/{job_id}`, which polls every 2 seconds.
5. When complete, the page shows:
   - finding count by severity
   - grouped summary table (rules with 5+ findings)
   - full findings table (rule, page, severity, issue type, message)
   - copyable Markdown preview
   - download links for JSON and Markdown reports
6. If the audit fails, a clean error message is shown — no stack traces.

---

## Privacy and safety

- Uploaded PDFs are saved only under the runtime directory (gitignored).
- Generated JSON/Markdown reports are saved only under the runtime directory.
- No uploaded content is committed to the repository.
- Findings contain structural metadata only (page numbers, rule IDs, coordinates) — no
  dissertation body text, author names, or other private content.
- Runtime files are never committed: `.runtime/` is in `.gitignore`.

---

## Runtime storage

Each job creates a directory under `NJIT_AUDITOR_WEB_RUNTIME_DIR`:

```
.runtime/web_audits/
  {job_id}/
    upload.pdf     ← original uploaded file
    report.json    ← structured JSON audit report
    report.md      ← Markdown audit report
```

Job state is held in memory while the server runs. Restarting the server clears in-memory
state; existing on-disk reports remain accessible if you re-implement persistence.

---

## Deployment note

This MVP provides app-level functionality without production hardening. For public access:

- Put nginx or Caddy in front (reverse proxy + TLS).
- Add a firewall rule to restrict port 8000 from direct public access.
- Consider adding authentication if the server handles sensitive dissertation PDFs.
- For persistent job storage across restarts, replace the in-memory `_jobs` dict with a
  database or file-backed store.

---

## Running tests

```bash
python -m pytest tests/test_web_app.py -v
```

Tests use `fastapi.testclient.TestClient` with monkeypatching of the audit runner;
no real PDF audit is needed for the web route tests.
