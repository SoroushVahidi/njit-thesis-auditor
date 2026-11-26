# Reproducibility and validation

This guide describes what a checkout can validate and what requires private
evaluation material. Use [current status](status/CURRENT_STATUS.md) for dated
results; a prior pass count is not a promise about a new checkout.

## Checkout and dependencies

Python **3.10 or newer** is declared in `pyproject.toml`. GitHub Actions tests
3.10, 3.11, and 3.12; other versions are not part of that CI matrix. Use a
private, authorized clone for the tracked Ester sources. Install Git LFS and
materialize the tracked binary fixtures before running tests that use them:

```bash
git lfs install
git lfs pull
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Do not copy dissertation PDFs or private outputs into a public checkout. A
clean clone does not contain ignored `data/evaluation/private/`,
`data/evaluation/generated/`, local `results/`, private replay manifests,
review ledgers, or the separate 19-PDF run outputs.

Synthetic fixtures and their tests provide shareable engineering checks. The
repository is currently private, and access to its tracked LFS files is not
public. The 136-case reviewer replay and 19-PDF evaluation additionally
depend on authorized private inputs and cannot be reproduced from a public
source snapshot or ordinary CI alone.

For checkout roles, saved path dependencies and output retention, start with the
[development guide](DEVELOPMENT.md). Keep environment installation confined to
your development worktree; do not reinstall into a production or saved validation
environment. Documentation-only work does not require materializing private LFS
inputs or running the full application suite.

## Standard checks and exact commits

From an approved fixture-free checkout, create a fresh virtual environment,
install with `python -m pip install -e ".[dev]"`, and run
`python -m pip check`. For the minimum reviewer checks, install with
`-c .github/ci/minimum-multipart.txt` and run the same two modules as the
minimum hosted job with `NJIT_TEST_MINIMUM_MULTIPART=1`.
The constraints and tests check the actual FastAPI, Starlette, and
python-multipart versions. Record the resolved packages per Python version
for a release rehearsal.

From the repository root, record the commit and tree being checked before
comparing results:

```bash
git status --porcelain=v1
git rev-parse HEAD
git rev-parse HEAD^{tree}
ruff check .
mypy src
python -m pytest -q
```

A clean `git status` is required for an exact-tree claim. For a proposed
deployment, also compare `git ls-remote origin refs/heads/main`, the detached
deploy worktree's `git rev-parse HEAD`, and live `GET /version`; follow
[deployment](DEPLOYMENT.md) for the actual gates and rollback procedure.

The default suite may skip tests whose private PDFs are absent. Report passes,
skips, SHA, and environment separately. The six skips on the PR #610 merge
commit were private-PDF-dependent and were subsequently run and passed as a
separate six-test job on that exact commit. Do not add those runs into one
invented full-suite result. GitHub Actions runs Ruff, mypy and an explicit
synthetic/nonconfidential selection on Python 3.10–3.12 without downloading LFS
objects. See [CI privacy and test separation](CI_PRIVACY.md) for the inventory,
checkout boundary and local reproduction. Hosted results do not replace the
complete private local gate.

## Browser checks with synthetic local services

The `browser` extra pins Playwright **1.64.1** and psutil **7.2.2**, separate from
runtime dependencies. Use Python 3.12 for the browser CI job. From a private
checkout on Ubuntu:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,browser]"
python -m playwright install --with-deps chromium
python -m playwright --version
python -m pytest -q tests/test_about_browser.py tests/test_ui_help_mobile_overflow.py tests/test_windows_download.py::test_browser_layout_and_keyboard tests/test_browser_audit_workflow.py --junitxml=.runtime/browser-ci.xml
```

`--with-deps` installs OS packages and may need administrator privileges locally;
on an already prepared workstation, `python -m playwright install chromium`
installs only the matching browser. Pinning Playwright selects its matching browser
revision. Record the actual Chromium version printed by CI's launch preflight.
Use `.venv/` and `.runtime/`, already ignored, for local environment and scratch data.

The additive **Synthetic browser checks (3.12)** job in the existing CI workflow
checks out without LFS payloads, installs these prerequisites, launches Chromium
and rejects skipped tests. It reuses About navigation, local desktop rendering,
Help overflow and Windows-button layout/gating tests. The new workflow test holds
the actual synthetic audit at a file gate, checks worker identity and one submission
across refresh/navigation, releases it, refreshes the completed report and follows
actual original/highlighted PDF and complete-report links. It uses generated PDFs
and loopback services; external browser requests are blocked. It never downloads a
public installer or contacts production. This tests current source on Ubuntu,
not native Windows or the published rc.3 executable.

The Python 3.10–3.12 matrix uses the reviewed hosted inventory for every branch;
private and LFS-dependent tests remain in the complete local suite. In a default
environment without the `browser` extra,
optional browser tests may skip; those skips are not browser coverage. CI and local
counts are separate evidence. The manifest's dated snapshot belongs to its recorded
source SHA: use `NJITA_STRICT_STATUS_DRIFT=1` only when intentionally comparing a
fresh collection with a matching snapshot/environment, not to reinterpret an older
baseline's counts as tests of a later documentation/test tree.

## Private Ester regression and visual evidence

The [judgment replay guide](ester_judgment_replay.md) documents the private
136-case manifest and command. A complete run needs authorized source PDFs,
the private manifest, a baseline output directory, and detector-liveness
counts. The replay checks reviewed target presence or absence, required
student-card links and highlights, liveness, and unexpected removals. A
cached replay checks saved reports; it does not rerun the PDFs.

The prior merge's liveness counts came from a local `liveness_plugin` supplied
outside this repository. With that authorized plugin available, set
`PYTHONPATH` to its directory plus `src`, set `LIVENESS_OUT` to a private JSON
path, and run `python -m pytest -q -p liveness_plugin` on the exact candidate
tree. Supply that JSON to replay with `--liveness`. A clean clone cannot
recreate this private gate without the plugin and private inputs; ordinary CI
does not run it.

For code changes affecting highlights, run relevant synthetic tests such as
`tests/test_highlight_target_baseline.py` and
`tests/test_highlight_pdf_student_routes.py`, then visually inspect the
rendered evidence for any private reviewer package. A passing synthetic test
does not establish that every real-document highlight is correct. The completed
19-PDF run is a separate evaluation whose findings still need deduplication
against historical feedback; do not treat its exit code as reviewer approval.

## Wheel installation boundary

The established deployment installs from a checkout and sets `PYTHONPATH` to
its `src/` directory. An isolated non-editable wheel built from this tree on
2026-10-12 contained Python modules but **no** `data/processed/` or
`data/specs/` JSON and **no** `njit_auditor/templates/*.html`. For example,
`report_text.py`, `polished_comments.py`, and `ester_warning_wording.py` read
repository-relative JSON, while `web_app.py` loads templates beside its source
module. A wheel-only installation therefore cannot be claimed to provide the
same rule metadata and web UI as a checkout. Fixing package data, resource
lookup, and isolated-install coverage belongs in a separate engineering PR.
