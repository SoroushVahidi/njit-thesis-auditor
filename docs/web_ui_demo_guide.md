# Web UI Demo Guide

- **Date:** 2026-06-16
- **Scope:** Current public PDF-only web UI
- **Recommended viewport checks:** `390x844` (mobile) and `1440x900` (desktop)

## 1. Use Only Safe Demo Inputs

For browser demos, screenshots, and shared documentation, use only the synthetic PDF fixtures:

- `tests/fixtures/web_demo/clean_minimal.pdf`
- `tests/fixtures/web_demo/issues_pdf.pdf`

Do not use real dissertation files in demos or screenshots.

The repository also contains synthetic `.tex` and `.zip` fixtures, but those are no longer part
of the public browser-upload flow. They remain for CLI/internal source-audit coverage only.

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

Open `http://localhost:8000`.

If you changed routes, Jinja globals/filters, startup configuration, or environment-dependent
behavior, restart the uvicorn/tmux process before the demo. Template auto-reload alone is not enough.

## 3. Home Page Check

Verify `/` shows:

- PDF upload form
- public PDF URL form
- built-in sample PDF section
- wording that the public site is PDF-only
- privacy/local-processing wording
- links to `/help` and `/rules`

## 4. Demo Flow

### Step 1: Upload `clean_minimal.pdf`

1. Upload `tests/fixtures/web_demo/clean_minimal.pdf`.
2. Confirm redirect to `/audits/{job_id}`.
3. Wait for completion.
4. Verify the completed page shows:
   - summary cards
   - grouped problems
   - access to individual findings
   - polished comments
   - suggested fixes
   - issue-type labels
   - JSON and Markdown download links
   - PDF-opening links

### Step 2: Upload `issues_pdf.pdf`

1. Return to `/`.
2. Upload `tests/fixtures/web_demo/issues_pdf.pdf`.
3. Verify the result shows repeated/grouped findings and PDF links that open the relevant page.
4. Open at least one grouped problem and one individual finding path.

### Step 3: Test URL Audit

1. On `/`, use the built-in example URL helper.
2. Submit the public PDF URL audit.
3. Verify the resulting job behaves like a local PDF upload and reaches a normal result page.

### Step 4: Test Built-In Sample Audit

If built-in samples are available on the server:

1. Choose a sample from the dropdown.
2. Submit it.
3. Verify it reaches the same result UI and action set as a normal PDF upload.

## 5. Result-Page Checks

For at least one completed job, verify:

- the same totals and rule/category counts appear on mobile and desktop
- grouped problems and individual findings are both reachable
- issue-type explanations are visible on both viewports
- JSON/Markdown downloads are present on both viewports
- PDF links are present on both viewports
- the privacy note is present

Responsive layout may differ, but no substantive action or explanation should disappear.

## 6. Problem-Page Checks

Open:

- `/audits/{job_id}/problems/category/{category}`
- `/audits/{job_id}/problems/rule/{rule_id}`

Verify both include:

- group title
- examples
- issue-type explanation
- back link
- PDF links

## 7. PDF Route Checks

From the result and problem pages, open:

- `/audits/{job_id}/pdf`
- `/audits/{job_id}/pdf#page=N`
- `/audits/{job_id}/pdf/highlighted?...`

Expected:

- no 500 responses
- inline PDF serving where the app can provide it
- browser/device behavior may still vary for final preview vs download

## 8. Help and Rules

Verify `/help` and `/rules` load and describe the current PDF-only web UI.

The rules page should not present TeX/ZIP source-only checks as part of the public upload experience.

## 9. Known Caveats

- Browser-native PDF handling can still vary by browser settings or installed viewers.
- Automated parity coverage in this repo uses `TestClient`, so it proves content/action parity more than pixel-exact layout parity.
