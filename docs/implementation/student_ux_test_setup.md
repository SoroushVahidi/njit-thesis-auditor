# Student correction and browser test setup

Use an isolated environment; package installation does not install browser binaries:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m playwright install chromium
# Linux hosts without browser libraries may also need:
# python -m playwright install-deps chromium
NJIT_REQUIRE_BROWSER=1 python -m pytest tests/test_student_ux_browser.py -q
```

The dev extra declares the Python Playwright API. Browser binaries are a separate,
explicit download. Ordinary tests skip browser cases when the API or Chromium is
absent; `NJIT_REQUIRE_BROWSER=1` makes missing prerequisites fail the student UX
browser checks. A browser that exists but cannot launch fails those checks. The
older card browser test retains its optional runtime behavior. For an offline run,
install dependencies and binaries ahead of time. Browser fixtures use synthetic
PDFs, isolated temporary storage, and a loopback server.

PyMuPDF's supported minimum is 1.28.2; no unproven upper bound is added.
The October 26 corrections validate 1.28.2 and 2.0 with the geometry tests and
fixed-document cross-version comparisons. This is evidence for those versions,
not certification of every intervening or future release. The former declared
minimum, 1.25.0, passed 165 geometry/highlight cases but failed both strict
rotated-highlight pixel-equivalence cases, also on the previous branch. That
observed validation limit motivates the new minimum; no parser regression or
incorrect finding geometry is established by those pixel differences. Use 1.28.2
for the review's reference environment (`python -m pip install 'pymupdf==1.28.2'`), record
`python -m pip freeze`, and rerun the safe suite plus geometry/highlight tests
when qualifying another runtime. Production dependency changes remain a separate
release decision.

The portrait geometry fixture now supplies a 26:24 image for a 260:240 rectangle.
Its image bounds no longer depend on version-specific treatment of a square
image in a non-square rectangle. The review found matching findings and pixels
when both libraries parsed the same PDF: this was a fixture-generation difference,
not a confirmed PDF-parsing regression. Detector geometry and thresholds are
unchanged.

The safe full-suite selection must exclude tests requiring private/historical
material. Use the independent review's individually classified selectors rather
than fetching private dissertations. Its five recoverable exclusions can run
with the review's synthetic authority plugin; workbook-routing coverage does not
establish original private-workbook parity.
