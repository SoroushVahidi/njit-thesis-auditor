# Web UI Manual QA Checklist

- **Date:** 2026-06-07
- **Baseline commit:** `4f3a70e` (post PR #216)
- **Scope:** Manual browser verification of the FastAPI web UI (PDF, TeX, ZIP uploads; JSON/Markdown downloads; triage panels; privacy controls)
- **Related:** `docs/web_gui_mvp.md` (setup and operations), `docs/planning/synthetic_web_demo_fixtures.md` (planned demo fixtures), `docs/planning/gui_scope_and_design.md` (design reference)

---

## 1. Purpose and Scope

This checklist is for manual testers who want to verify the end-to-end behavior of the
NJIT Thesis Auditor web UI in a real browser. It covers:

- Upload flows for all three supported input types (PDF, TeX, ZIP)
- Rejection of unsupported, corrupt, and unsafe inputs
- JSON and Markdown download correctness
- Report rendering: status banner, summary cards, triage panels, findings table, filters
- Job TTL and expiration behavior
- Privacy controls: what must not appear in web exports or the UI

This checklist does **not** test CLI behavior. CLI paths are unaffected by web export
sanitization and are not verified here.

---

## 2. Preconditions

1. **Local install only.** Run the web UI on your own machine with a local Python environment.
   Never process real dissertation files on a shared or public server during QA.

2. **Install the package:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Use only synthetic or explicitly approved files.** Do not upload real dissertation PDFs,
   real TeX source files, or any document containing real student names, committee names, or
   private thesis content. See Section 3 for the privacy warning and Section 4 for how to
   create safe test inputs.

4. **Browser requirements:** Any modern browser (Chrome, Firefox, Edge, Safari). JavaScript
   must be enabled for auto-refresh polling and client-side filters.

5. **No external network required** for file-upload QA. URL-fetch testing requires
   outbound HTTPS.

---

## 3. Privacy Warning

**CRITICAL: Use ONLY synthetic or explicitly approved files for all QA.**

The web UI is a local research prototype. During testing:

- Do NOT upload real dissertation PDF files.
- Do NOT upload real `.tex` source files that contain student names, committee names,
  thesis titles, bibliography entries, or any private academic content.
- Do NOT upload real ZIP archives containing real thesis content.
- Do NOT use the "Audit a built-in sample PDF" feature on any shared or networked server
  without explicit authorization from the dissertation author.
- Do NOT take screenshots of results from real dissertation files.

All synthetic test inputs used in QA must follow the same privacy rules as the project's
automated tests: generic placeholder text only (e.g., "This is a sample chapter." or
Lorem Ipsum), no real names, no real institutional affiliations, no real thesis content.

See `docs/planning/synthetic_web_demo_fixtures.md` for a plan to create standardized
safe demo fixtures.

---

## 4. Starting the Web UI Locally

```bash
# From the repository root, with the virtualenv active:
python -m uvicorn njit_auditor.web_app:app --host 127.0.0.1 --port 8000
```

Then open `http://localhost:8000` in a browser.

Alternatively, use the helper script (binds to 0.0.0.0 by default — localhost access only for QA):

```bash
./scripts/run_web_gui.sh 127.0.0.1   # binds to localhost only
```

Environment variables for QA tuning (optional):

| Variable | Default | Notes for QA |
|---|---|---|
| `NJIT_AUDITOR_WEB_RUNTIME_DIR` | `.runtime/web_audits` | Set to a temp dir if you want clean isolation |
| `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` | `50` | Lower to test size-limit rejection |
| `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` | `86400` | Set to `10` to test TTL expiration quickly |

To stop the server: press `Ctrl+C` in the terminal where uvicorn is running.

---

## 5. Creating Synthetic Test Inputs

Until `tests/fixtures/web_demo/` is populated (see `docs/planning/synthetic_web_demo_fixtures.md`),
create minimal synthetic inputs by hand:

**Minimal synthetic PDF (clean):**
Use PyMuPDF (`fitz`) or any PDF writer to create a single-page document with a line of
generic text. No real dissertation content.

**Minimal synthetic TeX:**
```latex
\documentclass{report}
\begin{document}
This is a sample chapter.
\end{document}
```

**Minimal synthetic ZIP:**
Create a ZIP archive containing only the TeX file above as `main.tex`.

**Unsafe ZIP (path traversal — for rejection testing only):**
Create programmatically at test time; do not commit to the repository. The archive should
contain an entry named `../evil.tex` to verify the server rejects it.

All synthetic inputs used in QA must not contain any real dissertation text, real names,
real labels, or real bibliographic content.

---

## 6. Test Matrix

For each scenario, the "Expected result" column describes what a tester should observe in
the browser. Where "must not appear" is specified, verify by inspecting page source and
downloaded files.

### 6.1 Upload page

| Check | Steps | Expected result |
|---|---|---|
| Upload page loads | Open `http://localhost:8000` | HTTP 200; "NJIT Thesis Auditor" heading visible; three input panels (file, URL, built-in sample) |
| File input accepts PDF/TeX/ZIP | Inspect the file input element | `accept=".pdf,.tex,.zip"` attribute present |
| Privacy note visible | Read the info banner on the upload page | "Privacy-safe processing" banner present; mentions no repository commit |
| Supported format descriptions | Read the bullet list under the file upload card | PDF → "P011–P061"; TeX → "P001–P010"; ZIP → "safe extract … P001–P010"; "no compilation" stated |
| Upload page copy | Read the URL form card | States PDF only; mentions private/internal URLs are blocked |
| Built-in sample card | Read the sample card | If no samples configured: "No built-in samples are available on this server"; if samples present: dropdown visible |

### 6.2 PDF upload (valid synthetic PDF)

| Check | Steps | Expected result |
|---|---|---|
| Upload accepted | Select a valid minimal synthetic PDF; click "Start audit" | Redirect to `/audits/{job_id}`; spinning status banner "Processing audit…" |
| Polling auto-refresh | Wait on job page | Page auto-refreshes every ~2 seconds while pending/running; no manual reload needed |
| Completion banner | Wait for completion | Status banner changes to green "Audit complete" style; shows file name and job ID prefix |
| Summary cards | Inspect results after completion | Cards show: total findings, WARNING count, FAIL count, category breakdown |
| Findings table | Inspect the findings table | Columns: Rule, Category, Page, Severity, Issue Type, Comment; at least header row visible |
| Triage panels | If any P011/P013/P026 findings present | Triage panels appear above the raw findings table with structured rollup counts |
| JSON download | Click "Download JSON" | Download completes; file is valid JSON; `metadata`, `findings`, `grouped_summary` keys present |
| Markdown download | Click "Download Markdown" | Download completes; file contains "##" headings, rule IDs, finding counts |
| No server path in JSON | Open downloaded JSON; search for absolute path strings | `metadata.file` or equivalent fields show basename only (e.g., `upload.pdf`), not a full server path |
| No stack trace on completion | Inspect results page | No Python tracebacks visible |

### 6.3 TeX upload (valid synthetic .tex)

| Check | Steps | Expected result |
|---|---|---|
| TeX upload accepted | Select a valid synthetic `.tex` file; click "Start audit" | Redirect to job page; status shows "TeX source audit" scope label |
| Source rules fire | Inspect findings after completion | Rule IDs are P001–P010 (or Q004–Q006); no P011+ PDF rules appear |
| JSON download | Download JSON | Valid JSON; `findings` present; `metadata.file` shows basename `.tex` only |
| Markdown download | Download Markdown | Valid Markdown; no raw LaTeX label names, ref names, or caption text in download |
| Privacy: no label names | Open downloaded JSON; search for `label`, `ref`, `caption` keys in finding details | These keys must not appear in any finding's `details` object in the web download |
| Privacy: sanitized messages | Inspect finding `message` fields in JSON | Messages are generic structural descriptions (e.g., "Structural issue detected"); not raw audit messages that may embed `\label{fig:something}` |
| No server path in JSON | Open downloaded JSON | File fields are basename-only |

### 6.4 ZIP upload (valid synthetic .zip with main .tex)

| Check | Steps | Expected result |
|---|---|---|
| ZIP upload accepted | Select a valid synthetic `.zip` containing `main.tex`; click "Start audit" | Redirect to job page; "ZIP" or "source audit" visible in scope label |
| Source rules fire | Inspect findings | Same as TeX: P001–P010 rules only |
| Extraction transparent | No intermediate extraction artifacts shown | Page shows results as if a single `.tex` was uploaded |
| JSON/Markdown downloads | Download both | Same privacy behavior as TeX upload (sanitized messages, no private keys, basename paths) |

### 6.5 Unsupported file upload (e.g., .docx)

| Check | Steps | Expected result |
|---|---|---|
| Rejection with clear error | Select a `.docx` file; click "Start audit" | HTTP 400 response or redirect back to upload page with error message; no job created |
| Error message is safe | Read the error | No stack trace; no internal server path; user-friendly message about unsupported format |

### 6.6 Corrupt or empty PDF

| Check | Steps | Expected result |
|---|---|---|
| Corrupt PDF rejected | Upload a file named `.pdf` that does not start with `%PDF` bytes | HTTP 400 or job `failed` state with safe error message |
| Empty PDF rejected | Upload a zero-byte file with `.pdf` extension | Validation error before job creation; clear user-facing message |
| Failed job page | If job reaches `failed` state | Status banner shows "Audit could not complete"; safe error message; "Try another file" link present; no stack trace |

### 6.7 Unsafe ZIP (path traversal attempt)

| Check | Steps | Expected result |
|---|---|---|
| Path traversal rejected | Upload a ZIP containing an entry named `../evil.tex` | Server rejects with HTTP 400 or job `failed`; no files written outside the job directory |
| File bomb (too many files) | Upload a ZIP with > 500 entries | Server rejects with appropriate error; no extraction attempt |
| Error is safe | Read the error message | No internal path disclosure; user-facing message only |

### 6.8 JSON download

| Check | Steps | Expected result |
|---|---|---|
| Download link present | On a completed job page | "Download JSON" button/link visible |
| File is valid JSON | Download and parse | JSON parses without error; top-level keys: `metadata`, `findings`, `grouped_summary` |
| Metadata keys | Inspect `metadata` | `total_findings`, `counts_by_severity`, `counts_by_rule_id`, `counts_by_category`, `generated_at`, `note` present |
| Findings array | Inspect `findings` | Each finding has `rule_id`, `severity`, `message`, `page` (or `location` for source), `details` |
| No absolute paths | Search JSON for the server's absolute path | Must not appear; only basename (e.g., `upload.pdf`) |
| Source audit: no private keys | For TeX/ZIP uploads: inspect each finding's `details` object | Keys `label`, `ref`, `caption`, `title`, `author`, `body`, `text` must not appear |

### 6.9 Markdown download

| Check | Steps | Expected result |
|---|---|---|
| Download link present | On a completed job page | "Download Markdown" button/link visible |
| File is valid Markdown | Open downloaded `.md` file | Readable headings, table rows, rule IDs; no binary content |
| Triage sections | For PDF uploads with P011/P013/P026 findings | Markdown includes "### P011 Triage" / "### P013 Triage" / "### P026 Font Triage" sections when rollups present |
| Privacy: source messages | For TeX/ZIP uploads | Raw LaTeX label names and `\ref{}` keys must not appear in the Markdown download |
| Summary table | Top of Markdown | Summary table with severity counts; "Heuristic signal" or equivalent disclaimer |

### 6.10 Job expiration and TTL behavior

| Check | Steps | Expected result |
|---|---|---|
| TTL variable respected | Start server with `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS=10`; complete an audit; wait >10 seconds; trigger another request | Expired job's runtime directory is removed from disk; accessing the old job URL returns a 404 or "job not found" response |
| Active jobs not evicted | A job in `pending` or `running` state must never be evicted | Even with very short TTL, in-progress jobs are preserved |
| In-memory state on restart | Restart the server; navigate to a previously completed job URL | Job not found (expected: in-memory state is lost on restart; on-disk files remain until next TTL sweep) |
| Runtime dir cleanup | After TTL expiry: check `.runtime/web_audits/` | Job subdirectory for expired job is removed |

### 6.11 Source report rendering (TeX/ZIP results)

| Check | Steps | Expected result |
|---|---|---|
| File:line location | Inspect findings table for a TeX/ZIP audit | Location column shows `filename:lineno` format; filename is basename only |
| Rule IDs | Inspect findings | Only P001–P010 (and Q004–Q006) appear |
| No raw TeX content | Inspect all visible finding comments/messages in the browser UI | No literal `\label{...}`, `\ref{...}`, or `\caption{...}` content visible |
| Polished comments | Inspect the "Comment" column | Structural descriptions like "Review needed: …"; no dissertation body text |

### 6.12 PDF report rendering

| Check | Steps | Expected result |
|---|---|---|
| Page numbers in findings | Inspect findings table | "Page" column shows integer page numbers (or "—" for source audits) |
| Triage-first panels | For PDF uploads with high-volume rules | P011/P013/P026 panels appear above the raw findings table; show counts and page ranges; no page content reproduced |
| Client-side filters | Use the "Rule", "Severity", "Category", "Page" filter dropdowns | Findings table updates without page reload; filter count label updates |
| Filter reset | Click "Reset" or equivalent | All filters cleared; full findings table visible |
| Grouped summary | If any rule has 5+ findings | "Grouped Summary" section lists high-volume rules with counts |
| Polished comments | Inspect "Comment" column | Heuristic language ("Review needed:"); no dissertation body text |

### 6.13 Privacy checks (what must NOT appear anywhere in web outputs)

The following must not appear in the web UI, downloaded JSON, or downloaded Markdown under any circumstances:

| Prohibited content | Where to check |
|---|---|
| Absolute server paths (e.g., `/home/user/...`) | Downloaded JSON `metadata.file`; finding `details.file` |
| Raw source lines from TeX files | Finding `message` fields in web JSON/Markdown downloads |
| LaTeX label names (e.g., `fig:demo_label`) | Finding `details.label` — key must be absent |
| LaTeX ref names | Finding `details.ref` — key must be absent |
| Caption text | Finding `details.caption` — key must be absent |
| Author names | Finding `details.author` — key must be absent |
| Dissertation body text | Any field in web-exported findings |
| Python stack traces | Error message area in the browser |
| Internal server error details | HTTP 5xx responses must show safe message only |

---

## 7. Browser and Visual Checklist

These checks do not require synthetic files — they verify page copy and layout.

| Item | Check | Pass criteria |
|---|---|---|
| Upload page heading | Open `http://localhost:8000` | "NJIT Thesis Auditor" visible in `<h1>` |
| Privacy info banner | Read the banner on the upload page | Mentions local/temporary processing; no repository commit |
| File input label | Read the label for the file input | "Select PDF, TeX, or ZIP" or equivalent |
| Format hint text | Read the small text under the file input | Lists accepted formats; mentions max upload size |
| Start audit button | Read the submit button | "Start audit" label |
| URL form | Second panel on the upload page | "Audit a public PDF URL" heading; URL input field; "Audit PDF URL" button |
| Status banner states | Observe job page while pending | Spinner and "Processing audit…" text |
| Status banner: failed | Upload a corrupt file | "Audit could not complete" banner; error message; "Try another file" link |
| Status banner: complete | Upload a valid file and wait | Success banner; job ID prefix and file name visible |
| Summary cards | After completion | Cards visible for total, WARNING, FAIL counts |
| Findings table headers | Inspect completed job page | Rule, Category, Page, Severity, Issue Type, Comment column headers |
| Filter controls | Inspect completed job page with findings | Rule/Severity/Category/Page dropdowns visible; count label updates on filter |
| Download buttons | Inspect completed job page | "Download JSON" and "Download Markdown" links/buttons present |
| Privacy note on results | Read the results page footer or note | Note about heuristic signals; disclaimer that manual review is required |
| Back link | Inspect completed or failed job page | Link to upload page ("Try another file" or similar) |

---

## 8. Known Limitations

These limitations are expected and do not constitute test failures:

| Limitation | Notes |
|---|---|
| No PDF annotation overlays | Findings are listed in a table; no visual page overlay exists yet (Phase 4+ in roadmap) |
| No LaTeX compilation | TeX/ZIP uploads run P001–P010 source checks only; a compiled PDF is not produced or audited |
| No authentication or rate limiting | Default bind is `0.0.0.0`; no login required; only use on localhost for QA |
| In-memory state lost on restart | Job list is cleared when the server restarts; old job URLs return 404 after restart |
| Web exports are privacy-reduced, not fully anonymized | `sanitize_report_for_web_export()` removes known private-content keys; it does not guarantee perfect anonymization for all possible future field values |
| CLI exports are not sanitized | The web sanitizer applies only to web JSON/Markdown downloads; CLI `--json-out` output is unchanged |
| Sanitizer key list requires maintenance | If future source rules (P001–P010 scope) add new private-content detail fields, `_UNSAFE_SOURCE_DETAIL_KEYS` in `report_outputs.py` must be updated |
| URL fetch requires outbound access | The "Audit a public PDF URL" form requires internet access; skip this flow in offline environments |
| Built-in samples expose private evaluation PDFs | The sample dropdown must not be exposed on any shared server without explicit authorization |
| chktex/lacheck are optional | P009/P010 findings only appear if these binaries are installed; gracefully skipped if absent |

---

## 9. Reporting Issues

When filing a bug from this checklist, include:

1. Which checklist item failed (section and row).
2. The browser used and version.
3. The server startup command used.
4. A description of what was observed vs. expected.
5. Any relevant server log output (from the uvicorn terminal).

Do **not** include real dissertation content, real file names from private documents, or
personal information in bug reports.
