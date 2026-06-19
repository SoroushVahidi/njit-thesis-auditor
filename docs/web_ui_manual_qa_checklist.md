# Web UI Manual QA Checklist

- **Date:** 2026-06-16
- **Scope:** Manual browser verification of the current public PDF-only FastAPI web UI
- **Recommended browser profiles:** phone-sized (`390x844`) and laptop-sized (`1440x900`)

## 1. Preconditions

1. Use only synthetic or explicitly approved PDF files.
2. Start the app locally or from the intended server revision.
3. If routes, Jinja globals/filters, startup configuration, or environment-dependent behavior changed, restart the uvicorn/tmux process before QA.
4. Prefer checking both a mobile browser/device and a desktop browser/device against the same job URL.

## 2. Start the App

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
./scripts/run_web_gui.sh 127.0.0.1
```

Or:

```bash
python -m uvicorn njit_auditor.web_app:app --host 127.0.0.1 --port 8000
```

## 3. Home Page

Verify `/` includes all of the following on both mobile and desktop:

- PDF upload form
- public PDF URL form
- built-in sample PDF form or a clear "no built-in samples" message
- wording that the public UI is PDF-only
- privacy/local-processing note
- reachable links to `/help` and `/rules`

## 4. Upload Flow

### Local PDF

Use `tests/fixtures/web_demo/clean_minimal.pdf` or `tests/fixtures/web_demo/issues_pdf.pdf`.

Verify:

- the file picker accepts `.pdf`
- upload starts successfully
- `POST /audits` redirects to `/audits/{job_id}`
- pending/running state renders without errors
- completed jobs show a normal result page
- failed jobs show a safe, user-facing error message without stack traces

### Public PDF URL

Verify:

- the form accepts a direct public PDF URL
- internal/private URL targets are rejected safely
- successful submissions reach the same result-page UI shape as local uploads

### Built-In Sample

If samples exist:

- the sample form submits successfully
- accidental `GET /audits/sample` returns to `/` instead of a confusing job-not-found page

## 5. Result Page

For the same completed job on mobile and desktop, verify both show the same:

- job status
- total finding count
- warning/error-style counts
- rules flagged
- categories represented
- summary cards
- grouped problem cards
- individual findings
- filters
- polished comments
- suggested fixes
- issue-type labels/explanations
- PDF links
- JSON/Markdown download links
- privacy note

Responsive layout differences are acceptable only if all actions remain reachable.

### 5a. Actionability Checks (added PR #320)

For each finding card on the result page:

- Every card has an action button (never empty).
- Cards with exact highlight coordinates (`P012` annotations) show **"Open highlighted PDF page"** and link to `/pdf/highlighted?...`.
- Cards with page but no bbox show **"Open original PDF page"** and link to `/audits/{job_id}/pdf#page=N`.
- Cards with no page at all show **"Open PDF"** and a note that the finding is document-level.
- Every grouped card shows a **"What does this mean?"** expandable details section.
- Expanding "What does this mean?" shows a student-facing explanation (not internal rule jargon).
- Abstract length findings (P021) show the observed word count, allowed maximum, and over-by amount in the explanation.
- Font findings (P026) mention Times New Roman 12pt in the explanation.
- Page numbering findings (P013/P019/P028) mention Roman/Arabic numeral requirements.
- Annotation findings (P012) mention accepting/rejecting reviewer comments.
- No-highlight notes appear only when highlight is not available.
- No-highlight guidance is honest and specific: page-known/no-highlight findings point to the original PDF page and explain what region to inspect; document-level findings remain explanation-only.

## 6. Problem Pages

Open both:

- `/audits/{job_id}/problems/category/{category}`
- `/audits/{job_id}/problems/rule/{rule_id}`

Verify on both mobile and desktop:

- title/group label
- examples
- issue-type explanation
- PDF links
- back link
- **"What does this mean?"** expandable explanation on every example card
- Action button label matches action kind (highlighted vs. page vs. PDF)
- No-highlight note appears when relevant

## 7. PDF Routes

From the UI, follow links to:

- `/audits/{job_id}/pdf`
- `/audits/{job_id}/pdf#page=N`
- `/audits/{job_id}/pdf/highlighted?...`

Verify:

- no 500 responses
- original PDF route serves inline where possible
- highlighted route is safe on normal linked inputs
- desktop is not forced to download when inline serving is available
- highlighted route falls back to plain PDF when no valid bbox exists (zero-area or missing)

Final preview-vs-download behavior may still vary by browser settings or installed PDF viewers.

## 8. Help and Rules

Verify `/help` and `/rules` load and stay aligned with the current public site:

- PDF-only wording
- no source-only upload instructions for the public browser UI
- clear explanation that P082 is experimental/opt-in and not enabled by default

## 9. Hidden-Content Regression Checks

While testing both viewports, confirm there is no viewport where any of the following disappears entirely:

- summary cards
- grouped/individual findings access
- polished comments
- suggested fixes
- issue explanations
- PDF links
- download links

Collapsed menus or wrapped buttons are acceptable if the same actions remain reachable.

## 10. Runtime and Cleanup

Recommended cleanup before a live restart:

```bash
rm -rf .runtime/web_audits/*
```

Also verify:

- `.runtime/` remains gitignored
- completed jobs age out according to `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS`

## 11. Record the QA Result

For each QA run, record:

- commit SHA tested
- device/browser used
- whether mobile and desktop showed the same substantive content/actions
- any PDF preview/download quirks caused by browser settings
- any route returning non-200 or 500 unexpectedly
