# Codex managed CI

This optional workflow and local runner verify one full commit SHA on x86_64 Linux
with Python 3.10, 3.11, or 3.12. The existing `CI` workflow and its check names
remain in place. The new workflow can be called by another workflow or started
manually after the workflow reaches the default branch and GitHub Actions is
available. It uses read-only repository access,
does not fetch Git LFS, and uploads its machine-readable manifest and logs.

For a local run, use a fresh private output directory outside the checkout:

```bash
python scripts/codex_managed_ci.py \
  --repo /path/to/repository-or-worktree \
  --sha FULL_40_CHARACTER_COMMIT_SHA \
  --python /path/to/python3.12 \
  --output-dir /private/path/ci-py312
```

Repeat for each available interpreter. The runner archives the exact commit,
omits `data/raw/ester` and `data/evaluation/private`, installs dependencies into
a new venv from the version-specific hashed lock, and runs Ruff, mypy, and
pytest. The 46 exact private-reading test cases identified in the reviewed
integration are deselected; a missing exclusion fails collection. The test child
also rejects Python and PyMuPDF file opens under known private-document roots.
The manifest records the commit, tree, Python version, hashes of the runner,
locks, exclusions, and step logs, plus exact deselection counts and pytest
outcomes. A step failure
returns a nonzero exit and leaves the manifest marked `FAILED`.

The locks are specific to x86_64 Linux. Regenerate them only after deliberate
dependency review, using `uv pip compile pyproject.toml
ci/build-requirements.in --extra dev --python-version 3.X --python-platform
x86_64-unknown-linux-gnu --generate-hashes --output-file
ci/requirements-py3XX-linux.txt`. The optional GitHub workflow pins the `uv`
version but does not hash the resolver wheel or pin Actions to immutable commit
IDs, so those bootstrap components remain supply-chain limitations. The local
runner's candidate archive is exact, but its controller and lock come from the
current CI branch; their hashes in the manifest make that distinction explicit.
The file-open guard is defense in depth for the reviewed suite, not an operating
system sandbox for arbitrary subprocesses. Do not run unreviewed tests on a host
with private documents mounted.

`scripts/codex_ci_publisher.py` accepts the three manifests, verifies their
SHA, tree, step logs, privacy counts, and three PDF logging regression cases,
then writes an **unpublished** proposal. It never reads credentials or calls
GitHub. A local result is evidence, not a GitHub required check.

Before any authoritative GitHub publication, the repository owner must install
a dedicated GitHub App on this repository only, grant `Contents: read` and
`Checks: write` (or `Commit statuses: write` for a status publisher), run the
signer on a trusted machine that accepts only protected, immutable manifests,
verify the current PR head SHA immediately before publication, and restrict the
new required check to that App as its expected source. Keep the existing CI
checks required. The App private key and installation token must stay outside
PR jobs and local developer shells. No publisher with these credentials is
implemented here because the trusted signer and App do not yet exist.

The current branch protection API returns no protection object and no evaluated
main rules. This is an observed repository state, not permission to merge.
