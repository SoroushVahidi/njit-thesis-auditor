# Web UI Demo Guide

- **Date:** 2026-06-07
- **Scope:** P001–P061 implemented; Web UI accepts PDF (P011–P061), TeX (P001–P010), and ZIP (P001–P010)
- **Related:** `docs/web_gui_mvp.md` (full setup and operations), `docs/web_ui_manual_qa_checklist.md` (manual browser QA checklist), `docs/planning/synthetic_web_demo_fixtures.md` (fixture details)

---

## 1. Purpose and Audience

This guide is for developers, contributors, and reviewers who want to run a quick end-to-end
demo of the NJIT Thesis Auditor web UI using the committed synthetic fixtures. It covers:

- How to install and start the web UI locally.
- Which synthetic fixture files to use and in what order.
- What to look for on each results page.
- How to verify JSON and Markdown downloads.
- Privacy protections that apply to web-generated exports.
- Known caveats and limitations.

This guide is **not** a comprehensive QA checklist. For detailed test scenarios, edge-case
coverage, and browser-specific checks, see `docs/web_ui_manual_qa_checklist.md`.

---

## 2. Privacy Statement

**Use ONLY the synthetic fixtures in `tests/fixtures/web_demo/` for public demos, screenshots,
and shared documentation.**

All content in those files is synthetic placeholder text — no real student names, no real
committee names, no real thesis titles, no real dissertation body text, and no real
bibliographic content. They are safe for public screenshots and demo write-ups.

The following rules apply whenever the web UI is used for demo or documentation purposes:

- Do **not** upload real dissertation PDF files.
- Do **not** upload real `.tex` source files containing student names, committee names,
  thesis titles, bibliography entries, or any private academic content.
- Do **not** upload real ZIP archives containing real thesis content.
- Do **not** take screenshots of audit results from real dissertation files.
- Do **not** commit screenshots to the repository without explicit review and approval.
- Do **not** expose the "Audit a built-in sample PDF" dropdown on any shared or networked
  server without explicit authorization from the dissertation author.

See Section 8 for the screenshot policy.

---

## 3. Install

From the repository root with a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## 4. Starting the Web UI Locally

### Option A: helper script (recommended)

The `scripts/run_web_gui.sh` script sets sensible defaults and can be run from any directory:

```bash
# binds to 0.0.0.0:8000 (all interfaces — localhost access for demos)
./scripts/run_web_gui.sh

# restrict to localhost only (recommended for demos on a shared machine)
./scripts/run_web_gui.sh 127.0.0.1

# alternate port
./scripts/run_web_gui.sh 127.0.0.1 8001
```

The script prints the resolved host, port, and runtime directory before starting uvicorn.
Press `Ctrl-C` to stop.

### Option B: uvicorn directly

```bash
python -m uvicorn njit_auditor.web_app:app --host 127.0.0.1 --port 8000
```

### Open the UI

After starting, open `http://localhost:8000` in a browser. The upload page loads immediately.

### Persistent always-on session (optional)

For a long-running demo server, use tmux:

```bash
tmux new -d -s thesis-auditor-web \
  'cd /path/to/njit-thesis-auditor && ./scripts/run_web_gui.sh 127.0.0.1'
```

---

## 5. Environment Variables

All environment variables are optional. The defaults are appropriate for a local demo.

| Variable | Default | Notes |
|---|---|---|
| `NJIT_AUDITOR_WEB_HOST` | `0.0.0.0` | Override via first arg to `run_web_gui.sh`; use `127.0.0.1` for localhost-only demos |
| `NJIT_AUDITOR_WEB_PORT` | `8000` | Override via second arg to `run_web_gui.sh` |
| `NJIT_AUDITOR_WEB_RUNTIME_DIR` | `.runtime/web_audits` | Where uploaded files and job results are stored; set to a temp dir for clean isolation |
| `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` | `50` | Maximum upload size; lower to test size-limit rejection |
| `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` | `86400` | Completed job retention in seconds (default 24 h); set to `10` to test TTL expiration quickly |

---

## 6. Demo Fixture Table

All fixtures are committed in `tests/fixtures/web_demo/`. All content is synthetic
placeholder text only — no real dissertation content.

| Fixture path | Upload type | Intended behavior | Expected high-level result |
|---|---|---|---|
| `tests/fixtures/web_demo/clean_minimal.pdf` | PDF | Baseline "few findings" demo | Audit completes; 3 structural advisories (P013/P027); no triage panels needed; green-ish result |
| `tests/fixtures/web_demo/issues_pdf.pdf` | PDF | Triggers P011 margin and P013 findings | P011 margin warnings and P013 findings appear; triage panel visible if counts are high enough |
| `tests/fixtures/web_demo/clean_minimal.tex` | TeX | Baseline TeX audit; few/no source findings | Source audit completes; "TeX source audit" scope label; zero or very few findings |
| `tests/fixtures/web_demo/issues_tex.tex` | TeX | Triggers P001/P002/P004/P005/P007 | Source findings appear; sanitized web JSON (no raw label/ref names in download) |
| `tests/fixtures/web_demo/demo_project.zip` | ZIP | ZIP extracted; `main.tex` detected; source report produced | Same source findings as the embedded `.tex`; no LaTeX compilation |

These fixtures are also used by 21 automated smoke tests in `tests/test_web_demo_fixtures.py`.

---

## 7. Step-by-Step Demo Flow

Complete these steps in order for a full end-to-end demo.

### Step 1 — Open the web UI

1. Start the server (see Section 4).
2. Open `http://localhost:8000` in a browser.
3. Verify the upload page loads: "NJIT Thesis Auditor" heading visible; three input panels
   (file upload, public URL, built-in sample); privacy info banner present.

### Step 2 — Upload `clean_minimal.pdf`

1. On the upload page, click "Select PDF, TeX, or ZIP" and choose
   `tests/fixtures/web_demo/clean_minimal.pdf`.
2. Click "Start audit".
3. The page redirects to a job page (`/audits/{job_id}`) with a spinner.
4. After ~1–2 seconds the page auto-refreshes to show the completed result.
5. **What to look for:**
   - Status banner: "Audit complete" (green/success style).
   - Summary cards showing finding counts by severity.
   - Findings table present (columns: Rule, Category, Page, Severity, Issue Type, Comment).
   - No triage panels needed for a near-clean result.
   - "Download JSON" and "Download Markdown" links visible.

> **Known caveat:** `clean_minimal.pdf` produces 3 structural advisories (P013/P027 class),
> not zero findings. This is expected — the synthetic fixture is minimal, not a fully
> compliant dissertation.

### Step 3 — Upload `issues_pdf.pdf` and verify P011 finding

1. Return to `http://localhost:8000`.
2. Upload `tests/fixtures/web_demo/issues_pdf.pdf`.
3. **What to look for:**
   - P011 (Margins) warning appears in the findings table.
   - P013 (Page numbers) finding appears.
   - Triage panel may appear above the findings table for high-volume rules.
   - Summary cards show WARNING count > 0.
   - All finding comments are structural heuristic descriptions; no dissertation body text
     should appear.

### Step 4 — Upload `clean_minimal.tex` and check source report

1. Return to `http://localhost:8000`.
2. Upload `tests/fixtures/web_demo/clean_minimal.tex`.
3. **What to look for:**
   - Status banner shows "TeX source audit" scope label (or similar indicator).
   - Rule IDs in findings are P001–P010 (or Q004–Q006 only); no P011+ PDF rules appear.
   - Zero or very few findings for the clean fixture.
   - Location column shows `filename:lineno` format; filename is basename only (no full path).

### Step 5 — Upload `issues_tex.tex` and verify source findings

1. Return to `http://localhost:8000`.
2. Upload `tests/fixtures/web_demo/issues_tex.tex`.
3. **What to look for on the results page:**
   - Findings for one or more of: P001 (risky commands), P002 (duplicate label), P004
     (unresolved ref), P005 (missing caption), P007 (caption punctuation).
   - Finding comments are structural descriptions; no raw `\label{...}` or `\ref{...}`
     content should be visible in the browser UI.
4. **What to verify in the downloaded JSON:**
   - Click "Download JSON".
   - Open the file and confirm `metadata.file` shows the basename only (e.g., `issues_tex.tex`),
     not an absolute server path.
   - Confirm finding `details` objects do not contain keys `label`, `ref`, `caption`, `title`,
     `author`, `body`, or `text`.
   - Confirm finding `message` fields are generic structural descriptions, not raw LaTeX lines.

### Step 6 — Upload `demo_project.zip` and verify ZIP extraction and source report

1. Return to `http://localhost:8000`.
2. Upload `tests/fixtures/web_demo/demo_project.zip`.
3. **What to look for:**
   - The job completes and shows a source audit result (P001–P010 rules; no P011+ PDF rules).
   - No intermediate extraction artifacts shown; results look like a `.tex` upload.
   - Location column shows `main.tex:lineno` (basename only).
4. Confirm no error about compilation failure — ZIP source audits do not compile LaTeX.

### Step 7 — Check JSON and Markdown downloads

For at least one fixture result (e.g., `issues_tex.tex`):

1. Click "Download JSON" and open the file.
   - Top-level keys present: `metadata`, `findings`, `grouped_summary`.
   - `metadata` contains: `total_findings`, `counts_by_severity`, `counts_by_rule_id`,
     `counts_by_category`, `generated_at`, `note`.
   - Each finding has: `rule_id`, `severity`, `message`, `page` (or `location` for source).
2. Click "Download Markdown" and open the file.
   - Readable `##` headings, rule IDs, finding counts.
   - Summary table with severity counts at the top.
   - No raw LaTeX label names or `\ref{}` keys in the Markdown body.

### Step 8 — Verify privacy invariants

After completing Steps 3–7, confirm the following invariants hold in all downloaded files:

| Invariant | Where to check |
|---|---|
| No absolute server paths | `metadata.file` in JSON; finding `details.file` |
| No raw LaTeX label names (e.g., `fig:demo_label`) | Finding `details.label` key must be absent |
| No raw LaTeX ref names | Finding `details.ref` key must be absent |
| No caption text | Finding `details.caption` key must be absent |
| No dissertation body text | Any field in web-exported findings |
| No Python stack traces | Error message area in the browser |

---

## 8. Expected UI Elements

After a successful upload and completed audit, the results page should show:

| UI element | Description |
|---|---|
| Status banner | "Audit complete" (green) or "Audit could not complete" (red/failed) with file name and job ID prefix |
| Summary cards | Total findings, WARNING count, FAIL count, category breakdown |
| Triage panels | Structured rollup for high-volume rules (P011/P013/P026) when counts are sufficient; appear above the raw findings table |
| Findings table | Columns: Rule, Category, Page, Severity, Issue Type, Comment; filterable client-side |
| Client-side filters | Rule, Severity, Category, Page dropdowns; filter count label; Reset button |
| Polished comments | "Review needed: …" style structural descriptions; no dissertation body text |
| Source filename:line labels | For TeX/ZIP audits: `filename:lineno` in the location column; basename only |
| Download links | "Download JSON" and "Download Markdown" buttons |
| Privacy note | Disclaimer that findings are heuristic signals requiring manual review |
| Back link | "Try another file" or upload page link |

---

## 9. Known Caveats and Limitations

| Caveat | Notes |
|---|---|
| `clean_minimal.pdf` produces 3 structural advisories | P013 (page-number candidate detection) and P027 (heading style) emit advisories on the synthetic minimal PDF; this is expected — "clean" means few findings, not zero |
| No PDF annotation overlays | Findings are listed in a table only; no visual page-overlay or bounding-box view exists yet (roadmap Phase 4+) |
| ZIP source audit does not compile LaTeX | TeX/ZIP uploads run P001–P010 source checks only; a compiled PDF is not produced or audited; PDF rules (P011–P061) do not fire for ZIP uploads |
| No authentication or rate limiting by default | The web app binds to `0.0.0.0` by default; for any shared or public deployment, add a reverse proxy, TLS, authentication, and rate limiting (see `docs/web_gui_mvp.md`) |
| In-memory job state is lost on server restart | Navigating to an old job URL after a server restart returns 404; on-disk files remain until TTL cleanup |
| Web exports are privacy-reduced, not fully anonymized | `sanitize_report_for_web_export()` removes known private-content keys and replaces raw source messages; it does not guarantee perfect anonymization for all possible future field values |
| CLI exports are not sanitized | `njit-audit tex --json-out` and `--md-out` outputs are not sanitized; the web sanitizer applies only to web JSON/Markdown downloads |
| chktex/lacheck are optional | P009/P010 findings appear only if these binaries are installed; they are gracefully skipped if absent |
| URL audit requires outbound HTTPS | The "Audit a public PDF URL" form requires internet access; skip this flow in offline environments |

---

## 10. Smoke Check (Automated)

To verify all five fixtures load correctly and produce the expected audit outcomes without
starting a server, run:

```bash
python -m pytest tests/test_web_demo_fixtures.py -q
```

This runs 21 smoke tests covering upload success, findings detection, JSON/Markdown downloads,
path redaction, and privacy sanitization for all five committed fixtures.

A convenience script is also available:

```bash
./scripts/web_demo_smoke.sh
```

The smoke script prints the fixture paths and suggested manual upload order, then runs the
pytest smoke suite. It does **not** start a long-running server.

---

## 11. Screenshot Policy

- Screenshots for README, documentation, or presentations must use **only** the synthetic
  fixtures in `tests/fixtures/web_demo/`.
- Never use real dissertation files for screenshots.
- Crop screenshots to exclude any visible absolute server paths. The web UI already displays
  basename-only filenames, so this is usually automatic.
- Label screenshots clearly as "synthetic demo input" in any documentation or slides.
- Do **not** commit screenshot files to the repository without explicit review and approval
  from the project lead.
