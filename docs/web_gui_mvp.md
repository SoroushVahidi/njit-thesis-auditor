# Web Upload UI Operations Guide

This guide describes the public FastAPI website and local development. Use the
[deployment runbook](DEPLOYMENT.md) for live service operations and rollback,
and [dated status](status/CURRENT_STATUS.md) for the last verified deployment.

The original UI parity baseline was PR #318 at `9e54b7b` on 2026-06-16.

## 1. Current Stable Scope

The public web UI is **PDF-only**.

It supports:

- uploading a local PDF
- downloading a generated synthetic sample or following the public example link,
  then uploading the PDF manually

It does **not** currently expose TeX, ZIP, or DOCX inputs in the public browser UI.
Those workflows remain separate CLI or internal tooling paths.

For the same uploaded PDF/job, mobile and desktop should show the same substantive content
and the same available actions. Responsive differences are limited to layout changes such as
stacking, wrapping, spacing, and column count.

## 2. Running Locally

From a development worktree, activate its environment using the
[local setup guide](REPRODUCIBILITY.md#checkout-and-dependencies). Pick a free
loopback port and a runtime directory inside that worktree:

```bash
NJIT_AUDITOR_WEB_RUNTIME_DIR="$PWD/.runtime/web_audits_dev" \
  ./scripts/run_web_gui.sh 127.0.0.1 8001
```

Open `http://127.0.0.1:8001`. Stop the local process with Ctrl-C.

## 3. Production supervision

The live website runs under the user systemd unit `thesis-auditor-web.service`
from a dedicated deployment worktree. Earlier development sessions used tmux.
Their supervision instructions are historical.

On the production host these read-only commands verify the service and the
running version:

```bash
systemctl --user is-active thesis-auditor-web.service
curl --fail --silent --show-error http://127.0.0.1:8000/healthz
curl --fail --silent --show-error http://127.0.0.1:8000/version
```

Health reports whether the service responds successfully. Version reports the
running commit, environment, and process start time. Compare its commit with the
deployment record. Follow the [clean-worktree deployment procedure](DEPLOYMENT.md#clean-worktree-requirement)
and [rollback procedure](DEPLOYMENT.md#rollback) for authorized service changes.

## 4. Reloading local changes

Restart the local Uvicorn process after changing:

- routes
- Jinja globals
- Jinja filters
- template helper registrations
- startup-time configuration
- environment-dependent behavior

Python route tables and Jinja registrations are created at import time.
Template auto-reload only updates templates.

## 5. Environment Variables

| Variable | Default | Meaning |
|---|---|---|
| `NJIT_AUDITOR_WEB_RUNTIME_DIR` | `.runtime/web_audits` | Runtime job directory |
| `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` | `50` | Maximum PDF upload size |
| `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` | `86400` | Retention window for completed/failed jobs |
| `NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS` | `300` | How often the background sweeper deletes expired jobs, independent of requests |
| `NJIT_AUDITOR_WEB_HOST` | `0.0.0.0` | Helper-script bind host |
| `NJIT_AUDITOR_WEB_PORT` | `8000` | Helper-script bind port |
| `NJIT_AUDITOR_WEB_ENVIRONMENT` | `local-dev` | Environment label reported by `/version`. The live service reports `production`. |

## 6. Routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Upload page |
| `GET` | `/healthz` | Service health |
| `GET` | `/version` | Running commit, environment, and process start time |
| `POST` | `/audits` | Start a PDF upload audit |
| `POST` | `/audits/url` | Reject legacy shortcut; 303 to upload-required error page |
| `POST` | `/audits/sample` | Reject legacy shortcut; 303 to upload-required error page |
| `GET` | `/sample.pdf` | Download synthetic PDF; no audit starts |
| `GET` | `/audits/url` | Guard redirect back to `/` |
| `GET` | `/audits/sample` | Guard redirect back to `/` |
| `GET` | `/audits/{job_id}` | Pending/running/completed/failed job page |
| `GET` | `/audits/{job_id}/status` | JSON polling endpoint |
| `GET` | `/audits/{job_id}/download/json` | JSON report download |
| `GET` | `/audits/{job_id}/download/markdown` | Markdown report download |
| `GET` | `/audits/{job_id}/download/text` | Page-ordered student text download |
| `GET` | `/audits/{job_id}/download/student-report.pdf` | Complete thesis and appended student PDF report download |
| `GET` | `/audits/{job_id}/problems/category/{category}` | Category problem page |
| `GET` | `/audits/{job_id}/problems/rule/{rule_id}` | Rule problem page |
| `GET` | `/audits/{job_id}/pdf` | Original PDF route |
| `GET` | `/audits/{job_id}/pdf/highlighted?...` | Highlighted PDF route |
| `GET` | `/help` | Help page |
| `GET` | `/rules` | Student-facing PDF rule reference |
| `GET` | `/about` | About the project |

## 7. User-Facing Behavior

### Upload page

The home page includes:

- PDF upload form
- sample PDF download link (save, then upload)
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
- Uploads and generated reports are deleted by a background sweeper once older than the TTL
  (startup sweep plus one every `NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS`).
- A student's own report may quote short document excerpts (TOC, list, and heading entries,
  flagged words); the UI says so and does not claim otherwise.
- JSON/Markdown downloads use basename-only paths.
- Document-URL submissions are rejected without network access or worker creation, including
  legacy fields on `/audits` and requests containing both a file and a nonempty URL.
- Rejections use a 303 redirect to a stable GET error page with upload instructions.
- The Sample Documents section offers the generated synthetic PDF and links directly to
  Christopher Anson's public-domain thesis on Wikimedia Commons. Visitors save either PDF
  and upload it manually. The real example is hosted by Commons; no copy is bundled.
  Historical Ester-annotated evaluation PDFs remain private. Listing or hosting them
  would require explicit publication approval from the relevant rights holders and
  confirmation that annotations and student content may be released.

The service runbook governs retention and maintenance of the live runtime directory.

## 10. Validation and QA

See the [dated mobile and desktop parity audit](planning/mobile_desktop_consistency_audit.md).

Use:

- [Web UI demo guide](web_ui_demo_guide.md) for a concise end-to-end demo
- [Manual QA checklist](web_ui_manual_qa_checklist.md) for browser smoke checks
- [Browser validation](REPRODUCIBILITY.md#browser-checks-with-synthetic-local-services) for automated Chromium checks

Representative viewport profiles for parity checks:

- mobile: `390x844`
- desktop: `1440x900`

## 11. Known Limits

- Browser PDF preview/download behavior is not fully app-controlled.
- Request-level parity tests use `TestClient`. Browser checks cover layout and
  navigation separately.
