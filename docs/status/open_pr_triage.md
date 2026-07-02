# Open PR Triage (2026-07-02, post-#402)

> **Canonical open-PR index.** Pair with
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
> for baseline `main`, validation, and next actions.

**Baseline inspected:** `main` @ `31c2aa6` (PR #403, 2026-07-02)  
**Open PR count:** 12

## Recent cleanup (2026-07-02)

| Action | Item | Reason |
|---|---|---|
| **Closed** | [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) | Superseded by #398 — CM/LM accepted with no P026A warning; advisory `latex_cm` path would add noise |
| **Deleted remote branch** | `fix/ester-p026-font-policy` | #386 closed; not a base of any open PR |
| **Merged** | [#401](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/401) | PR/branch cleanup status refresh |
| **Merged** | [#402](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/402) | Clean main-based P018 public rule-reference split |
| **Closed** | [#396](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/396) | Superseded by #402 (stacked P018 on obsolete #395 base) |
| **Deleted remote branches** | `fix/p018-toc-list-rule-reference-split`, `fix/p015-body-indent-ester-split` | Superseded; no remaining open PR dependencies |

Earlier same-day cleanup: #394/#395 closed; merged #397–#400; deleted merged P026/P015 prep branches.

## Quick verdict table

| PR | Branch → base | Mergeable | Verdict |
|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | DIRTY | **Likely superseded** — close only after explicit confirmation |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | DIRTY | **Docs-only** — review; may overlap content already on `main` |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | DIRTY | **Valuable** — rebase after `main` / #388 |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | UNSTABLE | **Ready** — docs-only demo fixture alignment |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | UNSTABLE | **Ready** — may overlap stacked P014 work (#391) |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | DIRTY | **Valuable** — rebase; `/rules` changed again with #402 |
| [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) | `fix/ester-q-matrix-coverage` → `main` | DIRTY | **Ready for review** — false-positive fixes, confidence labels |
| [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389) | `fix/p023-body-spacing-highlight-table-exclusion` → `fix/confidence-grouping-sorting` | UNSTABLE | **Stacked** — presentation stack |
| [#390](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/390) | `fix/wrapper-detection-preprocessing-notice` → `fix/p023-body-spacing-highlight-table-exclusion` | UNSTABLE | **Stacked** |
| [#391](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/391) | `fix/p014-frontmatter-heading-centering-evidence` → `fix/wrapper-detection-preprocessing-notice` | UNSTABLE | **Stacked** |
| [#392](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/392) | `fix/p011-toc-margin-warning-presentation` → `fix/p014-frontmatter-heading-centering-evidence` | UNSTABLE | **Stacked** |
| [#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) | `fix/p015-wrapped-continuation-lines` → `fix/p011-toc-margin-warning-presentation` | UNSTABLE | **Stacked** — compare P015 overlap with landed #400 |

## Dependency graph (open stacks)

```
main (31c2aa6)
 ├── Independent PRs: #311, #349, #362, #375, #376, #385, #388
 │
 └── Presentation stack
      fix/confidence-grouping-sorting
       └── #389 → #390 → #391 → #392 → #393
```

**Ester alignment stack on `main` (complete):** #397 → #398 (P026) → #399 (P018 parser) → #400 (P015) → #402 (P018 public cards). **#386 closed** — LaTeX CM advisory superseded by #398 accept-list.

## Recommended next development sequence

1. **#388** — review/merge independently after rebase on `31c2aa6`.
2. Presentation stack **#389–#393** — merge as a unit or cherry-pick after comparing with #400/#402.
3. Rebase UX/docs PRs **#385**, **#362**, **#349** after `main` stabilizes.

## PRs requiring explicit confirmation before close

| PR | Reason |
|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Superseded in spirit by geometry-driven location labels on `main` |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | Policy docs — may still carry unique content |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | Open product-policy question on "Review needed" prefix |

## Cleanup guardrails

- Do **not** start **P084** as part of PR cleanup.

## Historical triage

- [pr_and_stash_triage_20260619.md](pr_and_stash_triage_20260619.md) — pre-#372 PR #311 / #305 record
- Superseded bullets inside [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
