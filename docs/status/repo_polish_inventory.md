# Repository Polish Inventory

> **Purpose:** Document the current repository cleanup/polish state — baseline,
> what is already clean, known organization issues, and a recommended
> sequence for future low-risk cleanup PRs. This document is
> **documentation-only**. It does not implement any code, docs-content
> rewrite, worktree deletion, branch deletion, or reorganization beyond a
> single pointer line in `docs/status/README.md`.
>
> **Recorded:** 2026-07-03 (base `origin/main` @ `07db2fa30b457006cf7524309c8eabcca6ff64c8`,
> merge of PR #433)
>
> **Related:** [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md) ·
> [open_pr_triage.md](open_pr_triage.md) ·
> [live_deployment_checklist.md](live_deployment_checklist.md) ·
> [ester_current_consistency_audit.md](ester_current_consistency_audit.md)

---

## Current baseline

| Item | Value |
|---|---|
| Current `origin/main` SHA | `07db2fa30b457006cf7524309c8eabcca6ff64c8` (merge of PR #433, `fix/ester-safe-consistency-fixes`) |
| Validation on this SHA (clean worktree, this session) | `ruff check .` — all checks passed; `mypy src` — no issues in 105 source files; `python -m pytest` — **2512 passed**, 1 warning (pre-existing duplicate-zip-member warning in upload tests) |
| Live server (`GET /version`, this session, read-only check) | `commit=425f14442a4dca3701676b4c66db368d7aab46c1` (PR #430 merge), `branch=HEAD`, `process_start_time=2026-07-03T03:12:28Z` — running under tmux session `thesis-auditor-web`. **This is 3 merges behind current `origin/main`** (PRs #431 confidence-badge drill-down fix, #432 consistency audit docs, #433 stale dead-code cleanup all postdate this live process). Not restarted by this inventory pass. |
| Open PRs (`gh pr list --state open`) | 6, all pre-existing paused items: **#385** (rule-reference card declutter), **#376** (P014 frontmatter centering false positive), **#375** (clean_minimal demo fixture docs), **#362** (Review needed prefix policy), **#349** (autonomous policy + Ester feedback audit), **#311** (sub-page location labels). No new PRs opened by this inventory. |
| Dirty WIP worktree | `/home/soroush/njit-thesis-auditor/main`, branch `main`, **28 uncommitted changes**, local branch **50 commits behind `origin/main`** (per `git branch -vv`: `[origin/main: behind 50]`). Untouched by this session — not staged, stashed, cleaned, pulled, or reset. |
| LFS pointer / worktree artifact pattern | Every fresh `git worktree add` from `origin/main` reports the same **17 files** "should have been pointers, but weren't" (6 files under `data/raw/ester/`, 8 under `data/raw/guidelines/`, 3 under `tests/fixtures/web_demo/`). This is a known, repeat, environment-level LFS/worktree checkout quirk (also seen and reported in PRs #432 and #433) — not something this or prior sessions introduced, and not fixed by this document. |
| Total worktrees registered (`git worktree list`) | **60**, spanning `archives/`, `njit-thesis-auditor-clean-worktrees/` (29), `worktrees/` (23), and 5 ad hoc `/tmp/*` review/eval worktrees (2 marked `prunable`). |
| Local branches (`git branch -vv`) | **~115** local branches. A large fraction show `[origin/...: gone]` (remote already deleted after merge, local copy remains) or no upstream at all — these are branch-cleanup candidates for a **future**, separately-scoped PR; **none deleted by this document** per the hard constraint against deletions in this task. |

---

## What is already clean

- **PR #407** (Ester-reviewed warning-precision fixes: P044 continuation-line FP reduction, P027 bold-heading gate, P037 LoT Roman FP reduction, P011 margin-overrun presentation, P024/P040 LoF presentation, P025 Digital Commons wrapper notice) — merged, behavior preserved through every subsequent PR inspected in this session.
- **PR #408** (confidence sorting of grouped problem cards) — merged; grouping keys and detector output unchanged.
- **PRs #411–#433** (Ester source-of-truth docs, language/wording audits, Slices 1–6 wording alignment, P021/P026 policy-review doc, broad-split planning docs, presentation-cleanup plan, highlight-quality plan, page-order sorting, confidence-label normalization, P011 highlight-union fix, highlight-baseline tests, the Ester consistency audit, and the confidence-badge drill-down fix) — all merged and verified present on current `main` in this session.
- **Page-order sorting** (`SORT_MODE_PAGE` / `"page_order"`) — confirmed present in `report_view.py`.
- **Public confidence labels normalized** — confirmed only "High confidence" / "Medium confidence" / "Low confidence" render; "Needs review"/"Mixed confidence" strings removed (PR #427), and the drill-down-page gap is now also closed (PR #431).
- **P011 highlight coverage** — confirmed `pdf_margins.py` now unions all violating lines' boxes, not just the worst one (PR #430).
- **Stale P025 graduation-month presentation entries removed** — confirmed absent from `finding_explanations.py`, `polished_comments.py`, `issue_type_explanations.py` as of PR #433; P074 remains the sole, correct owner.
- **Ester consistency audit exists** and is current as of PR #432/#433 (`docs/status/ester_current_consistency_audit.md`), itself linked from `docs/status/README.md`.
- **`.gitignore` already covers generated/private artifacts** appropriately: `data/evaluation/generated/`, `data/evaluation/private/`, `.runtime/`, `var/web_audits/`, and the demo-extraction directory are all excluded — no gap found here.

---

## Current repo organization issues

1. **`current_project_state_and_next_steps.md` (the docs/status "Start here" doc) is stale relative to current `main`.** Its "Current Status" section is still dated 2026-07-02, records baseline `921d0df` / behavior baseline `70dcd95` (PR #409), and lists **2486/2506 pytest passed** — a full day and **24 merged PRs** (#409 → #433) out of date. It is the single most load-bearing doc in `docs/status/` (linked as "Start here" from `docs/status/README.md` and directly from the top-level `README.md`), so this is the highest-value stale-doc fix identified.
2. **`live_deployment_checklist.md` and `open_pr_triage.md` are similarly stale**, both anchored to the same `70dcd95`/`921d0df`/`811838c4` SHAs from the PR #406–#409 era. `open_pr_triage.md` in particular still frames #406/#407/#408 as the "recent" merges and does not reflect the current Ester-alignment PR stream (#411–#433).
3. **Top-level `README.md` line 223** repeats the same stale "2506 pytest passed... at `70dcd95`" figure, which will read as inconsistent with `docs/status/ester_current_consistency_audit.md`'s more recent validation numbers (2503/2512) once a reader cross-references both.
4. **Live server is 3 merges behind `origin/main`** (confirmed by `GET /version` in this session, see baseline table above). This is exactly the caveat the project's own `[[deploy_restart_after_merge]]`-style guidance anticipates, but the checklist doc that should record it is itself stale.
5. **`docs/status/` has 34 files with several overlapping "audit"/"checkpoint"/"snapshot" naming patterns** (e.g. `full_repository_audit_20260619.md`, `full_repository_audit_after_p063.md`, `full_repository_audit_after_p071.md`, `full_repository_audit_after_p079.md` alongside `rule_coverage_audit.md`, `source_to_implementation_coverage_after_p029.md`, `q_rule_coverage_after_p044.md` — four "full repository audit" snapshots and three separate coverage-audit snapshots, none visually distinguished as historical vs. current in the `docs/status/README.md` index itself, only in prose inside `current_project_state_and_next_steps.md`).
6. **`docs/status/README.md` is a flat, ungrouped table of 18 links** with no section headers — as the Ester-alignment work has grown (10+ of those 18 entries are Ester-specific), the index has become harder to scan for "what's current" vs. "what's historical planning."
7. **Old clean worktrees with branches still checked out cause local branch-delete failures.** This session and the two prior sessions in this conversation each hit `failed to delete local branch ... used by worktree at ...` when merging PRs with `--delete-branch` (for `fix/confidence-badge-every-card`, `docs/ester-current-consistency-audit`, and `fix/ester-safe-consistency-fixes`). The remote branch deletion still succeeds; only the local artifact lingers. This is a recurring, minor friction point worth a documented convention, not a code fix.
8. **LFS pointer artifacts appear "modified" in every fresh clean worktree** (17 files, itemized in the baseline table). This is reported correctly by prior sessions' PRs but is not itself documented anywhere as an expected, ignorable condition for whoever runs the next `git worktree add` — a short note in a worktree-hygiene doc would save re-diagnosis time.
9. **Dirty WIP worktree at `/home/soroush/njit-thesis-auditor/main` is 50 commits behind `origin/main`** and carries 28 uncommitted changes untouched across at least three prior sessions in this conversation. It remains correctly isolated (per hard constraints, never touched), but its existence and growing staleness is not recorded in any status doc — a future session without this conversation's context could mistake it for the working checkout.
10. **Old paused PRs (#311, #349, #362, #375, #376, #385) remain open** with `mergeStateStatus: UNKNOWN` (GitHub has not recomputed conflict status recently, likely because they are far behind `main`). They are correctly left untouched per standing policy, but `open_pr_triage.md`'s per-PR detail (rebase targets, conflict notes) predates the current `main` by dozens of commits and would need a fresh look before any of them could safely be revived.
11. **~115 local branches, many `[origin/...: gone]`** (remote already deleted, local copy orphaned) — a natural candidate for a future `git branch -d` sweep, but explicitly **not attempted here** per the no-deletion constraint on this task.
12. **Two differently-named "Ester" source docs**: `docs/sources/ester_materials.md` (older, attributes the shared archive to "**Ester Farfan**," describes `data/raw/guidelines/` and an `ai-formatting-project.rar` bundle) vs. the `docs/status/ester_*` family (attributes the same collaborator as "**Ester Flaim**," describes `data/raw/ester/` and the Google Sheet/Excel matrix). Both appear to refer to the same NJIT Graduate Studies contact; the name discrepancy has not been reconciled in any doc found in this inventory. Flagged for a human check, not resolved here — this is a naming/provenance question, not a technical one.

---

## Recommended docs/status organization

**Proposed grouping for `docs/status/README.md`** (recommendation only — **not implemented in this PR**, since even a same-file regrouping edit touches every line of a document that many other docs link into by section, and the task scope calls for the smallest safe pointer update):

| Group | Docs |
|---|---|
| **Current state** | `current_project_state_and_next_steps.md` (needs refresh — see below), `repo_polish_inventory.md` (this document) |
| **Deployment / live server** | `live_deployment_checklist.md` |
| **Ester source-of-truth and consistency** | `ester_feedback_source_of_truth.md`, `ester_current_consistency_audit.md`, `ester_q_p_rule_public_rule_mapping.md` |
| **Completed Ester wording slices** | `ester_language_alignment_audit.md`, `ester_current_wording_inventory.md`, `ester_next_wording_slice_plan.md`, `ester_wording_alignment_checkpoint.md` |
| **Presentation cleanup** | `student_facing_presentation_cleanup_plan.md`, `ester_broad_presentation_split_plan.md`, `ester_broad_rule_atomic_mapping.md` |
| **Highlight cleanup** | `highlight_quality_improvement_plan.md` |
| **Policy review** | `ester_policy_review_p021_p026.md` |
| **PR / branch triage** | `open_pr_triage.md` (needs refresh — see below) |
| **Evaluation / data manifests** | `evaluation_data_manifest.md`, `data_inventory_and_evaluation_sources.md` |
| **Historical snapshots** | `ester_feedback_implementation_audit_20260619.md`, `full_repository_audit_20260619.md`, `full_repository_audit_after_p063.md`, `full_repository_audit_after_p071.md`, `full_repository_audit_after_p079.md`, `phase1_milestone_summary.md`, `phase1_tex_finalization_status.md`, `phase2_pdf_milestone_summary.md`, `post_p072_backlog_and_data_strategy.md`, `pr_and_stash_triage_20260619.md`, `pr_description_integrate_rules_and_tex_auditor.md`, `project_closeout.md`, `q_rule_coverage_after_p044.md`, `rule_coverage_audit.md`, `source_to_implementation_coverage_after_p029.md`, `stale_docs_cleanup_20260619.md`, `warning_actionability_audit_20260622.md`, `current_capabilities_for_graduate_studies.md` |

This split is a **content-neutral regrouping** of the existing 18-row table (plus the two files this session adds) — no file moves, no deletions, no rewritten prose, just section headers over the existing rows.

**Do not move files in this PR.** Filenames stay in `docs/status/`; only a future PR should apply the grouping above to `docs/status/README.md` itself.

---

## Recommended cleanup sequence

1. **Reorganize `docs/status/README.md` into the grouped sections above.** Lowest-risk next docs PR — pure regrouping of existing links, no content rewrite.
2. **Update `current_project_state_and_next_steps.md` to current `main`/lifecycle status** — replace the 2026-07-02/PR #409 "Current Status" section with a fresh snapshot at `07db2fa` (PRs #431–#433), moving the existing "Current Status" section down into the historical stack per its own established convention (each snapshot already says "Superseded by ... above").
3. **Refresh `docs/status/live_deployment_checklist.md`** with the clean live-worktree path, the current live `/version` reading (`425f144`, 3 behind `main`), and the detached-HEAD/staleness caveat recorded in this document's baseline table.
4. **Add a worktree/branch cleanup checklist** (e.g. `docs/status/worktree_branch_hygiene.md`) documenting: the known 17-file LFS/worktree quirk and that it is safe to ignore/not stage; the `--delete-branch` failure pattern when a branch is still checked out elsewhere; and a proposed (not executed) list of `[origin/...: gone]` branches for a future, explicitly-scoped deletion PR. **Do not delete anything in that future PR without explicit instruction** — inventory and propose only, same as this document.
5. **Add `.gitignore` guidance only if a future audit finds an actual gap** — this session found none; `.runtime/`, `var/web_audits/`, and `data/evaluation/{generated,private}/` already cover the known generated/private-artifact surface.
6. **Archive or clearly label old status docs as historical** (e.g. a one-line "historical — superseded, do not read as current" banner at the top of each of the 17 docs listed under "Historical snapshots" above) — without deleting them. Low-risk, mechanical, one-line-per-file change.
7. **Only after the documentation cleanup above**, consider low-risk code-organization/refactor tasks (e.g. consolidating the three near-duplicate `_ISSUE_TEMPLATES`-style dicts' key-ordering conventions, or the `docs/planning/p0NN_scope_and_design.md` per-rule file pattern) — explicitly **not scoped or started by this document**.

---

## Do-not-touch list

- Dirty WIP worktree at `/home/soroush/njit-thesis-auditor/main` (28 uncommitted changes; never staged, stashed, cleaned, pulled, reset, or committed by this session).
- **P084** — out of scope, not started.
- **TOC-leader WIP** — not touched.
- **P021/P026** policy items — deferred pending human/Ester policy confirmation (`ester_policy_review_p021_p026.md`).
- **Broad presentation splits** (P014/P015/P017/P018/P019/P020/P024/P025/P027) — planned in detail, not implemented.
- **Old paused PRs** (#311, #349, #362, #375, #376, #385) — left open, not merged or rebased.
- **Private `data/raw/` files** — not committed, not modified, not moved.
- **Live-server process** — not restarted (the staleness noted above is descriptive only).
- **Worktrees, branches, and LFS files** — inventoried only in this document; **none deleted, pruned, or modified**.

---

## Recommended next PR

**`docs: organize status README and current project state`**

Scope: (1) apply the grouped-section regrouping above to `docs/status/README.md`, and (2) refresh `current_project_state_and_next_steps.md`'s "Current Status" section to `main` @ `07db2fa` (or whatever SHA is current when that PR starts), following its own existing "supersede and push down into history" convention. Both are docs-only, additive-history-preserving changes with no code, template, or test impact.

If a smaller first step is preferred, **`docs: update live deployment and worktree hygiene notes`** (items 3 and 4 above) is an even lower-risk alternative that does not touch the two most heavily cross-referenced docs.

**This document does not implement either PR.**

---

## Non-goals

This document does **not**:

- change `src/`, templates, tests, detector behavior, thresholds, detector constants, rule IDs, issue types, grouping keys, confidence labels, sorting behavior, highlight behavior, or report JSON schema;
- delete, prune, or modify any worktree, branch, or LFS file;
- reorganize `docs/status/README.md` beyond the single pointer line added in this PR;
- rewrite `current_project_state_and_next_steps.md`, `live_deployment_checklist.md`, or `open_pr_triage.md` (their staleness is recorded here, not fixed here);
- implement P021, P026, broad presentation splits, P084, or TOC-leader WIP;
- touch the dirty WIP worktree;
- merge or rebase any open PR;
- commit private student documents, generated reports, screenshots, or highlighted PDFs;
- restart the live server.
