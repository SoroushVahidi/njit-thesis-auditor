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

## Standard checks and exact commits

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
invented full-suite result. GitHub Actions checks out LFS objects and runs
Ruff, mypy, and pytest on Python 3.10–3.12; its result is CI evidence, not a
record of a locally run private gate.

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
