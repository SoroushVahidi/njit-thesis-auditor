# Current Status

> **Canonical, current-only status.** This file replaces
> `current_project_state_and_next_steps.md` as the entry point for "what's true right now."
> That file's most recent snapshot (PR #407/#408) is over 100 commits stale as of this
> writing; it is kept for historical/forensic context only — see the banner at its top.
>
> This file is intentionally short. Do not append dated snapshots here — open a new dated
> report under `docs/status/` instead and link it from the relevant section below.

_Last verified: 2026-08-25, after the local R011/R015 Esther-feedback checkpoints._

## Main branch

| Field | Value |
|---|---|
| Integration base SHA | `989746a120f6e1bd865c17aa5f6380eafde7ccd2` (short `989746a`, current `origin/main`) |
| Local HEAD SHA | `a23f7093a6c4365539200d0f807a522046a80e7a` (short `a23f709`) |
| Local unpushed checkpoints | `7090b824` R011/P011 Esther false-positive fix; `a23f7093` R015/P015 Esther false-positive fix |
| Last merged PR | [#530](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/530) — Pin Ruff version for reproducible CI |
| CI (`.github/workflows/ci.yml`) | not re-checked remotely for local unpushed checkpoints |
| `ruff check .` | clean |
| `mypy src` | clean, 113 source files |
| `python -m pytest -q` | **3157 passed**, 3 warnings |
| Rule coverage | P001–P084 implemented (including P075 and P084 inventory detectors; no remaining non-inventory project task IDs; next new rule ID is **P085**) |

Numbers above were measured directly on `main` at `a23f7093`, which is 2 commits ahead of
`origin/main` and has not been pushed. If you're reading this later, re-run the validation
commands yourself before trusting the counts.

## Recent local checkpoints

- R011/P011 correction completed and committed as
  `7090b824a8c69e042ced2cb6240d51fbc559cdce`
  (`fix(p011): incorporate Esther R011 false-positive feedback`). Esther reviewed 7 R011
  findings and classified all 7 as false positives. The correction is documented in
  `docs/status/p011_r011_batch_2026_08_false_positive_fix.md`.
- R015/P015 correction completed and committed as
  `a23f7093a6c4365539200d0f807a522046a80e7a`
  (`fix(p015): incorporate Esther R015 false-positive feedback`). Esther reviewed 3 R015
  findings and classified all 3 as false positives. The correction is documented in
  `docs/status/p015_r015_esther_feedback_false_positive_fix_20260825.md`.
- No R016 or later detector tuning has been performed from the all-rules feedback workbook:
  current local artifacts contain candidate findings for later rules, but no Esther
  correctness/false-positive judgments for R016+.

## Active open PRs (as of this audit)

None. Source PRs [#499](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/499),
[#500](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/500),
[#502](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/502),
[#504](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/504), and
[#483](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/483) were closed after #505
merged. Branches for #499/#500/#502/#504 were deleted; #483's remote branch was left intact
because its documentation commit is not an ancestor of `main`.

Reconstruction details: `docs/status/pr505_reduction_after_pr508_20260714.md`.
Old #505 head backup tag: `backup/pr505-e772f5f-before-reduction-20260714`.

## Stale remote branches

Many remote branches remain from already-merged PRs (repo does not auto-delete on merge).
#505 reduction deleted only the closed source-PR branches listed above. Full historical list
and further deletion candidates remain in
`docs/status/repository_polish_and_organization_20260713.md`.

## Live deployment status

**Not deployed and not verified against the running service in this pass** — port 8000 /
systemd / nginx / Caddy / firewall / VPN / DNS were not touched.

Repository-derived lower bound only: the dedicated deploy worktree
(`archives/njit-thesis-auditor-deploy`) was previously observed at `c4d4065` and will be further
behind after #505/#508. Confirm with `GET /version` per `docs/DEPLOYMENT.md` before relying on
UI behavior matching `main`.

## Current evaluation corpus

- `ester_sample_a` / `ester_sample_b` / `ester_sample_c` / `ester_sample_d` — private, EF-reviewed
  dissertation PDFs under `data/raw/ester/` and `data/evaluation/generated/`. Never referenced by
  filename/content in runtime `src/` conditionals (see anti-overfitting check in
  `docs/status/repository_polish_and_organization_20260713.md`).
- Synthetic fixtures under `tests/fixtures/web_demo/` (`clean_minimal.pdf`, `issues_pdf.pdf`,
  `demo_project.zip`) — safe for the public web UI demo and CI.
- Full inventory: `docs/EVALUATION_DATA.md` and the older
  `docs/status/evaluation_data_manifest.md` / `docs/status/data_inventory_and_evaluation_sources.md`.

## Unresolved engineering tasks

- Delete additional stale merged-PR remote branches (see polish report) when explicitly
  authorized.
- Private evaluation binaries under `data/raw/ester/` include both Git LFS pointers and full Git
  blobs; filenames often contain personal names. Keep the repo private; plan a later coordinated
  history/LFS migration — do not rewrite history casually.
- `scripts/ester_rule_consistency_audit.py` requires local, untracked, generated
  `results/ester_feedback_raw/*.xlsx` input and cannot run in a fresh clone or CI.
- Optional remaining-time work: privacy-safe duplicate-candidate aggregate audit; typed evaluation
  labeling schema; lightweight CURRENT_STATUS drift prevention tests.

## Unresolved Esther-policy questions

Still unresolved (do **not** implement without Esther's explicit sign-off):

- Footer-zone P011 body-text policy (Sample A cluster).
- R011/P011 recurring single-line bottom-margin cases around 9.2 pt, just beyond the new
  9.0 pt confirmed-false-positive tolerance.
- R011/P011 reference-list overflow beyond the bounded reference allowance, especially
  Patrick reference entries around 10.2-18.0 pt.
- R015/P015 Youra physical page 101, printed page 84: run-in-heading-adjacent paragraph
  boundary question surfaced after the row-remnant fix.
- P011 non-text-element (image/drawing) margin coverage.
- Unreviewed Sample B medium-confidence P011 pages.
- A possible new TOC-entry sentence-case rule.
- Whether any duplicate-warning candidates should ever auto-suppress (tooling remains
  diagnostic-only).

## Immediate recommended next actions

1. Deploy only after an explicit maintainer decision (out of scope for the #505 overnight pass).
2. Decide the Esther-policy questions above with Esther directly.
3. Optionally run the privacy-safe duplicate-candidate aggregate audit and/or small labeling /
   status-drift infrastructure PRs.
