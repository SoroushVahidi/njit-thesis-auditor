# Open PR Triage (2026-07-01)

> **Canonical open-PR index.** Pair with
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
> for baseline `main`, validation, and next actions.
>
> **Guardrail:** Do **not** close, merge, or rebase these PRs during routine cleanup unless
> explicitly requested.

**Baseline inspected:** `main` @ `cdc99ea` (PR #387, 2026-06-30)  
**Open PR count:** 16

## Quick verdict table

| PR | Branch → base | Mergeable | Verdict |
|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | CONFLICTING | **Likely superseded** — close only after explicit confirmation |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | MERGEABLE | **Docs-only** — review; may overlap content already on `main` |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | CONFLICTING | **Valuable** — rebase after `main` / #388 confidence-label work |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | MERGEABLE | **Ready** — docs-only demo fixture alignment |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | MERGEABLE | **Ready** — may overlap stacked P014 work (#391); compare before merge |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | CONFLICTING | **Valuable** — rebase; rule-reference page changed on `main` / in-flight PRs |
| [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) | `fix/ester-p026-font-policy` → `main` | MERGEABLE | **Review vs #394** — both touch P026 Ester font policy; avoid double-merge |
| [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) | `fix/ester-q-matrix-coverage` → `main` | MERGEABLE | **Ready for review** — false-positive fixes, confidence labels, Q partial tier |
| [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389) | `fix/p023-body-spacing-highlight-table-exclusion` → `fix/confidence-grouping-sorting` | MERGEABLE | **Stacked** — see presentation stack below |
| [#390](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/390) | `fix/wrapper-detection-preprocessing-notice` → `fix/p023-body-spacing-highlight-table-exclusion` | MERGEABLE | **Stacked** |
| [#391](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/391) | `fix/p014-frontmatter-heading-centering-evidence` → `fix/wrapper-detection-preprocessing-notice` | MERGEABLE | **Stacked** — fork point for Ester stack |
| [#392](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/392) | `fix/p011-toc-margin-warning-presentation` → `fix/p014-frontmatter-heading-centering-evidence` | MERGEABLE | **Stacked** (presentation fork) |
| [#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) | `fix/p015-wrapped-continuation-lines` → `fix/p011-toc-margin-warning-presentation` | MERGEABLE | **Stacked** (presentation fork terminus) |
| [#394](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/394) | `fix/p026-font-policy-ester-consistency` → `fix/p014-frontmatter-heading-centering-evidence` | MERGEABLE | **Stacked — Ester fork** — merge before #395 |
| [#395](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/395) | `fix/p015-body-indent-ester-split` → `fix/p026-font-policy-ester-consistency` | MERGEABLE | **Stacked — Ester fork** — merge before #396 |
| [#396](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/396) | `fix/p018-toc-list-rule-reference-split` → `fix/p015-body-indent-ester-split` | CONFLICTING | **Stacked — Ester fork** — rebase onto #395 after it merges |

## Recommended merge order

### A. Independent merge candidates (each rebased on current `main`)

Review and land in any order after human review — **watch for overlap**:

1. [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) — broad false-positive / confidence / Q-coverage work (large; good standalone merge)
2. [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) — docs-only
3. [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) — compare with #391 before merging both
4. [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) — **hold** if planning to merge #394 (same P026 theme)
5. [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) — docs-only policy audit

### B. Ester alignment stack (P026 / P015 / P018) — **#394 → #395 → #396**

This is the highest-priority ordered stack for Ester Q-rule / public rule-card splits:

```
main
 └── #388 (optional first — touches overlapping presentation files)
 └── [shared ancestor: fix/p014-frontmatter-heading-centering-evidence via #391 chain]
      └── #394  fix/p026-font-policy-ester-consistency
           └── #395  fix/p015-body-indent-ester-split
                └── #396  fix/p018-toc-list-rule-reference-split  ← CONFLICTING; rebase last
```

**Safest sequence:**

1. Merge or rebase **#391** (P014 evidence) — or ensure its commits are on `main` via the presentation stack.
2. Merge **#394** (P026 font policy / Ester consistency).
3. Merge **#395** (P015 body-indent Ester split).
4. Rebase **#396** onto updated #395, resolve conflicts, then merge (P018 TOC/list rule-reference split).

Do **not** merge #396 before #395. Do **not** merge #386 and #394 without checking for duplicate P026 logic.

### C. Presentation / false-positive stack — **#389 → #390 → #391 → #392 → #393**

Parallel fork from the same P014 evidence ancestor (wrapper filtering, margin presentation, wrapped-line P015 fix):

```
fix/confidence-grouping-sorting
 └── #389  P023 table-text exclusion
      └── #390  wrapper preprocessing notice
           └── #391  P014 centering evidence
                ├── #392 → #393  (P011 margin presentation → P015 wrapped lines)
                └── #394 → #395 → #396  (Ester fork — see above)
```

Merge **#389–#393** as a unit **or** cherry-pick commits onto `main` after #388 if file overlap is heavy. This stack and the Ester stack share **#391** as a common ancestor — coordinate so P014 evidence lands once.

### D. Conflicting PRs — rebase before merge

| PR | Why conflicting | Suggested action |
|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `report_view.py`, templates vs years of location-label work on `main` | Confirm superseded; close only with explicit approval |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | Confidence badge / prefix policy drift | Rebase after #388 merges |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `/rules` page structure changed | Rebase after #388 / Ester stack |
| [#396](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/396) | Stacked branch behind #395 | Rebase onto #395 head after #395 merges |

## PRs requiring explicit confirmation before close

| PR | Reason |
|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Superseded in spirit by geometry-driven location labels on `main`; still **do not close** without maintainer sign-off |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | Policy docs — may still carry unique AGENTS.md / audit content |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | Open product-policy question on "Review needed" prefix |

## Historical triage

- [pr_and_stash_triage_20260619.md](pr_and_stash_triage_20260619.md) — pre-#372 PR #311 / #305 record
- Superseded 2026-06-25 triage bullets inside [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)

## Cleanup guardrails (unchanged)

- Do **not** close, merge, rebase, or delete open PRs during hygiene passes unless explicitly requested.
- Do **not** delete head branches without an explicit decision.
- Do **not** start **P084** as part of PR cleanup.
