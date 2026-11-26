# Reproducibility and validation

This guide describes what a checkout can validate and what requires private
evaluation material. Use [current status](status/CURRENT_STATUS.md) for dated
results; a prior pass count is not a promise about a new checkout.

## Checkout and dependencies

Use a source checkout approved for your role. Set `GIT_LFS_SKIP_SMUDGE=1`
before checkout, use the [hosted CI sparse patterns](CI_PRIVACY.md) for routine
validation, and leave protected sources unmaterialized. The source repository
is public. Neither a Git filename nor a Git LFS pointer provides confidentiality
or permission to retrieve the payload.

```bash
export GIT_LFS_SKIP_SMUDGE=1
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip check
```

Use generated fixtures for shared tests. Keep private review ledgers, replay
manifests, manuscript PDFs, case-level findings, and outputs in approved
restricted storage. Use approved private fixtures only in a separately
authorized local run. Record any independently verified data scope in the
private evidence index.

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
runtime dependencies. Use Python 3.12 on Ubuntu in a fixture-free checkout
configured as described in [CI privacy](CI_PRIVACY.md).

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,browser]"
python -m playwright install --with-deps chromium
python -m playwright --version
python .github/ci/hosted_tests.py browser
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

The online service currently runs from a checkout. The wheel also packages
the runtime rule data, web templates, and report font. The source distribution
includes the inputs required to build those resources.

For release qualification, build the wheel and source distribution from a
fixture-free checkout. In a fresh environment outside the source directory,
install the wheel, run `python -m pip check`, and verify the packaged resources
with a synthetic audit and web report smoke. Inspect both package inventories
for excluded manuscripts, reviewer evidence, and local output before
distributing either artifact. Keep installed-wheel verification separate from
checks that import the repository's `src/` directly.
