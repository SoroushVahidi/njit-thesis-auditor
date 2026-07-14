# Current Status

> **Canonical, current-only status.** This file replaces
> `current_project_state_and_next_steps.md` as the entry point for "what's true right now."
> That file's most recent snapshot (PR #407/#408) is over 100 commits stale as of this
> writing; it is kept for historical/forensic context only — see the banner at its top.
>
> This file is intentionally short. Do not append dated snapshots here — open a new dated
> report under `docs/status/` instead and link it from the relevant section below.

_Last verified: 2026-07-13, by the repository-polish audit (`docs/status/repository_polish_and_organization_20260713.md`)._

## Main branch

| Field | Value |
|---|---|
| `origin/main` SHA | `dcadd61c7688a9e244d56d84cf39dca469f55006` (short `dcadd61`) |
| Last merged PR | [#507](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/507) — fix `ester_rule_consistency_audit.py` attribute bugs |
| CI (`.github/workflows/ci.yml`) | passing on `main` |
| `ruff check .` | clean |
| `mypy src` | clean, 107 source files |
| `python -m pytest -q tests` | **2734 passed, 2 skipped** |
| Rule coverage | P001–P083 implemented (P075 is a documented non-inventory project task; next new rule ID is **P084**, not started) |

Numbers above were measured directly on a fresh `origin/main` checkout as part of this audit —
not copied from an older doc. If you're reading this later, re-run the three validation
commands yourself before trusting the counts.

## Active open PRs (as of this audit)

| PR | Branch | Status |
|---|---|---|
| [#505](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/505) | `fix/overnight-esther-correctness-20260712` | Open, `MERGEABLE`/`CLEAN`. Adopts P015/P011/P033 fixes cherry-picked from #499/#500/#502/#504. Its P026 hunk is now a byte-identical no-op against `main` — PR [#506](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/506) merged an equivalent (more general) P026 concatenated-heading fix independently on 2026-07-13. Merging #505 is still safe; review it as "P015 continuation-indent + P011 remediation wording + P033 wording fix + docs", not as a font-compliance change. |
| [#504](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/504) | `investigate/sample-b-annotation-ground-truth` | Superseded — cherry-picked into #505. Close once #505 is merged. |
| [#502](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/502) | `fix/p033-location-wording-and-duplicate-analysis` | Superseded — cherry-picked into #505. Close once #505 is merged. |
| [#500](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/500) | `fix/p011-margin-precision-false-negative-audit` | Superseded — cherry-picked into #505. Close once #505 is merged. |
| [#499](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/499) | `fix/p011-content-aware-remediation` | Superseded — cherry-picked into #505. Close once #505 is merged. |
| [#483](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/483) | `audit/ester-sample-b-feedback` | `CONFLICTING`. Per #505's own description, its content was already superseded by #482 (merged 2026-07-09) and was **not** adopted. Recommend closing without merging. |

This assessment was made by inspecting `gh pr list`/`gh pr view`/`gh pr diff` output and diffing
the overlapping file (`src/njit_auditor/rules/pdf_font_compliance.py`) between #505 and #506
directly — not by trusting any prior status doc.

## Stale remote branches

30 remote branches exist; only the 6 above correspond to open PRs. The other ~24 correspond to
already-merged PRs and were left over because this repo does not auto-delete branches on merge.
None were deleted by this audit (branch deletion requires explicit human authorization per the
task constraints this report was produced under). Full list and recommended deletions are in
`docs/status/repository_polish_and_organization_20260713.md`.

## Live deployment status

**Not independently verified against the running service in this pass** — the task that produced
this document explicitly prohibited restarting the live server or making requests to port 8000.

The only repository-derived evidence available: the dedicated deploy worktree
(`archives/njit-thesis-auditor-deploy` on the host that manages it) is checked out at `c4d4065`
(the PR #493 merge commit), which is **8 commits behind** `origin/main`'s `dcadd61`. This is a
lower bound on staleness as of this audit, not a live-verified fact — confirm with `GET /version`
per `docs/DEPLOYMENT.md` before relying on current UI behavior matching `main`.

## Current evaluation corpus

- `ester_sample_a` / `ester_sample_b` / `ester_sample_c` / `ester_sample_d` — private, EF-reviewed
  dissertation PDFs under `data/raw/ester/` and `data/evaluation/generated/`. Never referenced by
  filename/content in runtime `src/` conditionals (see anti-overfitting check in
  `docs/status/repository_polish_and_organization_20260713.md`).
- Synthetic fixtures under `tests/fixtures/web_demo/` (`clean_minimal.pdf`, `issues_pdf.pdf`,
  `demo_project.zip`) — safe for the public web UI demo and CI.
- Full inventory: `docs/EVALUATION_DATA.md` (new, this audit) and the older
  `docs/status/evaluation_data_manifest.md` / `docs/status/data_inventory_and_evaluation_sources.md`.

## Unresolved engineering tasks

- Rebase/merge #505, then close #499/#500/#502/#504/#483 (see table above).
- Delete stale merged-PR remote branches (list in the full audit report).
- `results/` (script scratch output) is not gitignored — see repository-polish audit, Phase 5.
- `scripts/ester_rule_consistency_audit.py` requires local, untracked, generated
  `results/ester_feedback_raw/*.xlsx` input and cannot run in a fresh clone or CI; it is not
  wired into `docs/RULE_ARCHITECTURE.md`'s consistency-test story for that reason. Making it
  CI-runnable (e.g. by committing a redacted fixture) is deferred — needs Esther/maintainer
  input on what's safe to commit from her raw spreadsheets.

## Unresolved Esther-policy questions

Carried forward from PR #505's own "Remaining Esther-judgment items" list (still unresolved as of
this audit):

- Footer-zone P011 body-text policy (Sample A 8-page cluster).
- P011 non-text-element (image/drawing) margin coverage.
- 6 unreviewed Sample B medium-confidence P011 pages.
- A possible new TOC-entry sentence-case rule.

Do not implement any of these without Esther's explicit sign-off — they are formatting-policy
judgment calls, not engineering bugs.

## Immediate recommended next actions

1. Review and merge PR #505 (or rebase it if #506/#507 caused drift beyond the confirmed no-op).
2. Close #499/#500/#502/#504/#483 as superseded.
3. Delete the ~24 stale merged-PR remote branches.
4. Restart the live deployment once a maintainer confirms `main` is in the desired state (out of
   scope for this audit).
5. Decide the 4 open Esther-policy questions above with Esther directly.
