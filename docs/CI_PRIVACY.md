# Hosted CI and private local validation

Hosted Actions must not download or process confidential dissertations. Passing
hosted checks does not replace the private accuracy gate on the exact integration
candidate. The default local `python -m pytest` command and all existing test
assertions remain unchanged.

## Hosted jobs

`CI` runs on pushes and pull requests. Its Python 3.10–3.12 matrix runs Ruff,
mypy, boundary regression tests, and the explicit synthetic/nonconfidential
selection in [tests.json](../.github/ci/tests.json). The separate Python 3.12
browser job runs four explicit targets with generated PDFs and loopback services;
zero tests or any browser skip fails that job.

The inventory initially classifies 203 hosted modules and 16 local-only modules.
The latter include private replay/correctness/geometry tests, mixed modules with
private cases, reviewer spreadsheets, a public guideline PDF, and four modules
using authorized synthetic web-demo binaries stored in LFS. Those binaries are
kept local too: hosted CI downloads **no LFS objects**, including public ones.
Each excluded module has an individual reason in the inventory. Synthetic tests
within mixed modules remain part of complete local validation; they are not
silently counted as hosted coverage. New modules and helpers (including
`conftest.py`) must be classified before hosted collection can proceed.

Hosted coverage includes synthetic detector/rule tests, reports, highlighting,
privacy sanitization, CLI, upload limits, desktop lifecycle/security, packaging,
and browser behavior. The pinned desktop reference archive is synthetic evidence
verified without network access by `scripts/desktop_reference.py`. Rule JSON and
specification metadata are application resources, not dissertation fixtures.
Optional browser/native-Windows tests in the Linux matrix may skip; the dedicated
browser job requires its full coverage. Private test exclusions are reported
separately from pytest skips.

Every checkout uses `lfs: false`, `GIT_LFS_SKIP_SMUDGE=1`, no persisted credentials,
one-commit history, and sparse exclusions for `data/raw/`, `data/evaluation/` and
`results/`. Before executing tests, jobs remove the checkout remote and set
`lfs.fetchexclude=*`. The boundary checker rejects private roots, replay manifest
environment variables, materialized LFS files, enabled smudging, remotes, and an
incomplete test inventory. It prints generic failures rather than private paths
or payloads. No secret or private manifest is passed to hosted test jobs.

The CI workflow grants only `contents: read`, has no artifact upload, and disables
pip caching. Pytest's cache provider is disabled. JUnit files stay in ephemeral
runner storage. No dependency/workspace cache is restored or saved by the workflow.
The boundary regression tests exercise both accepted and rejected checkouts with
synthetic sentinels; no private fixture is needed for them.

`Windows desktop beta build` already avoided LFS and persisted credentials. It now
uses the same sparse exclusions, shallow history, fetch exclusion and preflight.
Its explicit native test targets and smoke PDF are synthetic. Its existing artifact
allowlist contains installer files, checksums, test XML and synthetic smoke logs,
not fixture directories; it uses no Actions cache. Its build job runs only for
`release/windows-beta-publish-*` PRs or explicit workflow dispatch. Updating #653
or the CI privacy PR triggers the path-filtered workflow but skips that build job.
This correction does not authorize a native build or publication.

These controls protect the reviewed workflow from accidental fixture fetching or
test inclusion. They are not a sandbox for malicious changes to workflows/code.
Workflow edits still require review. The source repository remains private;
sparse checkout and this change do not authorize publishing its Git history.

## Reproducing the hosted selection locally

Use a separate disposable clone, not a checkout holding private evidence. Set
`GIT_LFS_SKIP_SMUDGE=1` **before cloning**, clone with `--no-checkout --depth 1`,
then use the sparse patterns shown in `.github/workflows/ci.yml` before checkout.
Remove `origin` and set `git config --local lfs.fetchexclude '*'` only in that
disposable clone. Install `.[dev]` in an isolated environment, then run:

```bash
export GIT_LFS_SKIP_SMUDGE=1
python .github/ci/hosted_tests.py check
python -m unittest discover -s .github/ci -p 'test_*.py'
python .github/ci/hosted_tests.py test --collect-only
python .github/ci/hosted_tests.py test
```

For browser coverage install `.[dev,browser]` and matching Chromium, then run
`python .github/ci/hosted_tests.py browser`. The runner accepts `--shard N --shards M`
for bounded local validation; shards partition the same explicit module list.
It clears extra pytest arguments/plugins and uses this checkout's `src` path.
Do not interpret local sharded results as hosted Python-version matrix results.

## Private local accuracy gate

Use the existing authorized private checkout, environment and fixtures. Do not
apply the sparse exclusions or hosted runner to that checkout. Run the complete
`python -m pytest` suite with the existing private inputs, historical replay,
finding comparisons, controls and liveness evidence described in
[REPRODUCIBILITY.md](REPRODUCIBILITY.md) and
[ester_judgment_replay.md](ester_judgment_replay.md). Record the exact SHA,
passes/failures/skips and missing prerequisites. Keep inputs, full logs, findings
and manuscript-derived artifacts local. No private assertion, detector rule,
threshold, or report-generation code is changed by this separation.

When integrating with #653, retain this workflow and classify its added test
modules explicitly: synthetic corrections/R027/deferred-R036 tests may join
hosted coverage after review; manifest-dependent private cases stay local.
Revalidate the resulting integration SHA; the earlier local candidate and older
GitHub checks do not certify that new commit.
