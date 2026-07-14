# Current Status

> **Canonical, current-only status.** This file replaces
> `current_project_state_and_next_steps.md` as the entry point for "what's true right now."
> That file's most recent snapshot (PR #407/#408) is over 100 commits stale as of this
> writing; it is kept for historical/forensic context only — see the banner at its top.
>
> This file is intentionally short. Do not append dated snapshots here — open a new dated
> report under `docs/status/` instead and link it from the relevant section below.

_Last verified: 2026-07-14, after reduced PR #505 merged (`docs/status/pr505_reduction_after_pr508_20260714.md`)._

## Main branch

| Field | Value |
|---|---|
| `origin/main` SHA | `3d31ce9bff97b650aa81346834dcbd18b8ed5c88` (short `3d31ce9`) |
| Last merged PR | [#505](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/505) — finalize P015/P011/P033 correctness work after repository normalization |
| CI (`.github/workflows/ci.yml`) | passing on `main` (post-merge run `29303438713`) |
| `ruff check .` | clean |
| `mypy src` | clean, 108 source files |
| `python -m pytest -q tests` | **2821 passed** (measured on fresh `origin/main` @ `3d31ce9`) |
| Rule coverage | P001–P083 implemented (P075 is a documented non-inventory project task; next new rule ID is **P084**, not started) |

Numbers above were measured directly on a fresh `origin/main` checkout after the reduced #505
merge — not copied from an older doc. If you're reading this later, re-run the three validation
commands yourself before trusting the counts.

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

Still unresolved after #505 (do **not** implement without Esther's explicit sign-off):

- Footer-zone P011 body-text policy (Sample A cluster).
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
