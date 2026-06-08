# Synthetic Web Demo Fixtures

- **Date:** 2026-06-07
- **Baseline commit:** `4f3a70e` (post PR #216)
- **Status:** Implemented — all five fixtures committed in `tests/fixtures/web_demo/` (PR #218)
- **Related:** `docs/web_ui_manual_qa_checklist.md`, `docs/web_gui_mvp.md`, `docs/planning/gui_scope_and_design.md`

## Committed Fixture Paths

| Fixture | Path | Size | Notes |
|---|---|---|---|
| Clean minimal PDF | `tests/fixtures/web_demo/clean_minimal.pdf` | ~2 KB | Generated with PyMuPDF; synthetic text only |
| Issues PDF | `tests/fixtures/web_demo/issues_pdf.pdf` | ~2.4 KB | Triggers P011 (margin overflow) and P013; synthetic text only |
| Clean minimal TeX | `tests/fixtures/web_demo/clean_minimal.tex` | ~400 B | Minimal TeX; no risky commands; few/no source findings |
| Issues TeX | `tests/fixtures/web_demo/issues_tex.tex` | ~900 B | Triggers P001, P002, P004, P005, P007, P008; synthetic only |
| Demo ZIP | `tests/fixtures/web_demo/demo_project.zip` | ~350 B | ZIP with `main.tex`; safe extraction; produces source report |

All fixtures are covered by 21 automated tests in `tests/test_web_demo_fixtures.py`.

---

## 1. Goal

Create a set of safe, committed demo inputs that:

- Enable manual QA of the web UI without any real dissertation content.
- Can be used for public screenshots and demo documentation.
- Serve as deterministic inputs for automated web smoke tests.
- Never contain real student names, committee names, real thesis titles, or private
  dissertation body text.

These fixtures are the implementation target for the next QA/documentation sprint.

---

## 2. Privacy Policy for All Fixtures

Every synthetic fixture file must comply with the following rules:

- **No real dissertation text.** All body text must be generic placeholder content only
  (e.g., "This is a sample chapter.", Lorem Ipsum equivalents, or clearly fictional prose).
- **No real student names.** Do not use any real person's name as an author or committee member.
  Use placeholders like "A. Demo Author" or "Jane Sample" (clearly fictional).
- **No real committee names.** Use "Professor Example", "Dr. Placeholder", etc.
- **No real thesis titles.** Titles must be generic (e.g., "Sample Dissertation Title",
  "A Study of Synthetic Formatting Examples").
- **No real institutional affiliations beyond NJIT.** Using "New Jersey Institute of Technology"
  as the institution name is acceptable since it is public; all other details must be generic.
- **No real bibliographic content.** Use placeholder citation entries.
- **No real label or ref names that could identify a real document.** Use names like
  `fig:demo_label`, `tab:demo_table`, `sec:intro_example`.

These rules apply to both committed fixtures and dynamically generated test fixtures.

---

## 3. Proposed Fixtures

### 3.1 Clean minimal PDF (passes all checks)

- **Purpose:** Baseline "no findings expected" demo; shows a clean audit result page.
- **Description:** A minimal multi-page PDF with generic text, correct margins (1.5" left,
  1" right, top/bottom 1"), Times New Roman 12pt body text, double-spacing, correct front-matter
  heading order, lowercase Roman numerals on front-matter pages, Arabic page numbers on body pages.
- **Expected audit outcome:** Zero or very few findings; demonstrates a healthy result page.
- **Fixture path:** `tests/fixtures/web_demo/clean_minimal.pdf`
- **Commit:** Safe to commit — no private content.
- **Generation:** Create with PyMuPDF (`fitz`) using a helper script or test fixture factory.
  No real dissertation content; use "This is a sample chapter for demonstration purposes."

### 3.2 PDF with obvious synthetic issues

- **Purpose:** Demo input that produces visible P011/P013/P026 findings for screenshot
  documentation and triage panel testing.
- **Description:** A multi-page PDF with:
  - Text blocks intentionally placed outside the 1.5" left margin (triggers P011).
  - Page-number-like tokens at multiple positions on the same page (triggers P013).
  - Body text in a non-compliant font family (triggers P026 if font metadata available).
  - Generic placeholder body text only; no real content.
- **Expected audit outcome:** Several warnings across P011, P013, P026; triage panels appear.
- **Fixture path:** `tests/fixtures/web_demo/issues_pdf.pdf`
- **Commit:** Safe to commit — all content is synthetic and non-private.
- **Generation:** Create with PyMuPDF; annotate page geometry explicitly to produce
  synthetic margin overflow and page-number candidate patterns.

### 3.3 Minimal clean .tex (no issues)

- **Purpose:** Baseline TeX upload that produces zero findings; demonstrates a clean TeX result.
- **Description:** A minimal valid TeX document:
  ```latex
  \documentclass[12pt]{report}
  \usepackage{setspace}
  \begin{document}
  \doublespacing
  \chapter{Introduction}
  This is a sample chapter for demonstration purposes.
  \end{document}
  ```
- **Expected audit outcome:** Zero or very few findings (no risky commands, no duplicate
  labels, no missing captions).
- **Fixture path:** `tests/fixtures/web_demo/clean_minimal.tex`
- **Commit:** Safe to commit.

### 3.4 .tex with synthetic issues

- **Purpose:** Demo input that exercises P001–P010 checks visibly.
- **Description:** A TeX document containing:
  - A risky formatting command such as `\vspace{1cm}` (triggers P001).
  - A duplicate `\label{fig:demo_label}` (triggers P002).
  - A `\ref{tab:demo_table}` with no matching `\label{tab:demo_table}` (triggers P004).
  - A figure environment missing `\caption` (triggers P005).
  - A caption that does not end with a period (triggers P007).
  - All label and ref names use clearly synthetic identifiers: `fig:demo_label`,
    `tab:demo_table`, `sec:intro_example` — never real thesis identifiers.
  - Generic body text only; no real thesis content.
- **Expected audit outcome:** Findings for P001, P002, P004, P005, P007; demonstrates
  the TeX source audit report with a non-empty findings table and sanitized web download.
- **Fixture path:** `tests/fixtures/web_demo/issues_tex.tex`
- **Commit:** Safe to commit — all label names are obviously synthetic.

### 3.5 Safe ZIP containing main .tex

- **Purpose:** Demo input for the ZIP upload path.
- **Description:** A ZIP archive containing `main.tex` (the clean or issues version)
  and optionally a `figures/` subdirectory with a placeholder image. No real content.
  Main `.tex` must have a `\documentclass` declaration so automatic detection works.
- **Expected audit outcome:** Same as the embedded `.tex` file.
- **Fixture path:** `tests/fixtures/web_demo/demo_project.zip`
- **Commit:** Safe to commit if the archive contains only safe synthetic content.
  Keep the archive small (< 100 KB).

### 3.6 Unsafe ZIP fixtures (path traversal — test-only, never committed)

- **Purpose:** Verify the server rejects path-traversal ZIP entries.
- **Description:** A ZIP archive containing an entry with a `../` path component
  (e.g., `../evil.tex`) or an absolute path (e.g., `/tmp/evil.tex`).
- **Expected audit outcome:** Server returns HTTP 400 or job reaches `failed` state;
  no file is written outside the job directory.
- **Fixture path:** Generated dynamically at test runtime using `tmp_path` or `conftest.py`
  helpers. **Never committed to the repository.**
- **How to generate in tests:**
  ```python
  import zipfile
  from pathlib import Path

  def make_traversal_zip(path: Path) -> None:
      with zipfile.ZipFile(path, "w") as zf:
          info = zipfile.ZipInfo("../evil.tex")
          zf.writestr(info, b"\\documentclass{report}\n")
  ```

---

## 4. Where Fixtures Should Live

| Fixture | Path | Safe to commit? |
|---|---|---|
| Clean minimal PDF | `tests/fixtures/web_demo/clean_minimal.pdf` | Yes |
| Issues PDF | `tests/fixtures/web_demo/issues_pdf.pdf` | Yes |
| Clean minimal .tex | `tests/fixtures/web_demo/clean_minimal.tex` | Yes |
| Issues .tex | `tests/fixtures/web_demo/issues_tex.tex` | Yes |
| Demo ZIP | `tests/fixtures/web_demo/demo_project.zip` | Yes |
| Traversal ZIP | Generated in `tmp_path` at test time | Never committed |
| File-bomb ZIP | Generated in `tmp_path` at test time | Never committed |

The `tests/fixtures/web_demo/` directory does not yet exist. It should be created as part
of the fixture implementation PR. The directory itself (with a placeholder or the fixtures)
should be committed; the `.gitignore` should remain unchanged (it does not currently match
`tests/fixtures/`).

---

## 5. How Fixtures Should Be Used

### 5.1 Automated tests

Committed fixtures can be loaded directly in pytest tests:

```python
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "web_demo"

def test_clean_pdf_upload_completes(client):
    pdf_bytes = (FIXTURES / "clean_minimal.pdf").read_bytes()
    # ... upload via TestClient ...
```

Dynamically generated fixtures (unsafe ZIPs, oversized files) should be created in
`tmp_path` inside test functions or in `conftest.py` helpers.

### 5.2 Manual QA

During manual browser QA (see `docs/web_ui_manual_qa_checklist.md`):

1. Open `http://localhost:8000`.
2. Use the committed fixtures from `tests/fixtures/web_demo/` as upload inputs.
3. Verify the expected findings and UI behavior described in the checklist.
4. Use `issues_tex.tex` or `issues_pdf.pdf` to exercise the triage panels and download links.

### 5.3 Screenshots and demo documentation

When creating screenshots for README or documentation:

- Always use the committed synthetic fixtures in `tests/fixtures/web_demo/`.
- Never use real dissertation files for screenshots.
- Crop screenshots to exclude any absolute server paths (use basename-only display,
  which the web UI already provides).
- Label screenshots clearly as "synthetic demo input".

### 5.4 README demo

The README already points to `examples/latex/` for CLI demos. Once `tests/fixtures/web_demo/`
is populated, a short "Web UI demo" section can be added to the README pointing to those
fixtures and referencing the manual QA checklist.

---

## 6. Acceptance Criteria (Implemented — PR #218; Demo Guide Added — PR #219)

For the end-to-end demo workflow using these fixtures, see
[`docs/web_ui_demo_guide.md`](../web_ui_demo_guide.md) — it covers install, run commands,
step-by-step upload flow for all five fixtures, privacy invariant verification, and
`scripts/web_demo_smoke.sh` (the quick smoke check).

A PR implementing these fixtures is ready to merge when all of the following are true:

1. `tests/fixtures/web_demo/` directory exists with at least:
   - `clean_minimal.pdf`
   - `issues_pdf.pdf`
   - `clean_minimal.tex`
   - `issues_tex.tex`
   - `demo_project.zip`

2. No fixture file contains real dissertation text, real student names, real committee names,
   real thesis titles, or real bibliographic content.

3. Each committed fixture is verified to produce the expected audit outcome described in
   Section 3 (clean fixtures produce zero/near-zero findings; issues fixtures produce
   the expected rule IDs).

4. At least one new automated test in `tests/test_web_app.py` or a new
   `tests/test_web_demo_fixtures.py` uses the committed fixtures via `TestClient`
   and asserts basic correctness (job completes, finding counts match expectation,
   JSON schema valid).

5. Dynamically generated unsafe fixtures (traversal ZIP, file-bomb ZIP) are created
   only in `tmp_path` and never appear in the committed fixture directory.

6. `ruff check .`, `mypy src`, and `python -m pytest` all pass.

7. The PR description notes that all fixture content is synthetic and privacy-safe.

---

## 7. Future Extension

Once the basic committed fixtures are in place, additional fixtures may be added for:

- A PDF that triggers specifically P014 (heading style), P022 (page number on no-number page),
  or P028 (page-numbering regime mismatch).
- A multi-file ZIP project (multiple `.tex` files with `\input{}` includes) to exercise
  the recursive loader path.
- A TeX file with abstract word count violations (Q004/Q005) and a graduation month issue (Q006).

All future fixtures must follow the same privacy policy in Section 2.
