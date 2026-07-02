# Open PR Triage (2026-07-02)

> **Canonical open-PR index.** Pair with
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
> for baseline `main`, validation, and next actions.

**Baseline inspected:** `main` @ `fbefbb6` (PR #400, 2026-07-02)  
**Open PR count:** 14 (was 16 before 2026-07-02 cleanup)

## Recent cleanup (2026-07-02)

| Action | Item | Reason |
|---|---|---|
| **Merged** | [#397](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/397) | Docs/status refresh |
| **Merged** | [#398](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/398) | Clean main-based P026 replacement |
| **Merged** | [#399](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/399) | P018 List row page-number association fix |
| **Merged** | [#400](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/400) | Clean main-based P015 replacement |
| **Closed** | [#394](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/394) | Superseded by #398 (stacked P026 on old branch) |
| **Closed** | [#395](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/395) | Superseded by #400 (stacked P015 + unrelated web commits) |
| **Deleted remote branches** | `fix/p026-ester-consistency-mainprep`, `chore/repo-cleanup-status-refresh-20260701`, `fix/p026-font-policy-ester-consistency` | Merged or superseded; not bases of open PRs |

**Branches kept intentionally:** `fix/p015-body-indent-ester-split` (base of open #396), presentation-stack branches (#389–#393), and all open PR head branches.

## Quick verdict table

| PR | Branch → base | Mergeable | Verdict |
|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | DIRTY | **Likely superseded** — close only after explicit confirmation |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | DIRTY | **Docs-only** — review; may overlap content already on `main` |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | DIRTY | **Valuable** — rebase after `main` / #388 confidence-label work |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | UNSTABLE | **Ready** — docs-only demo fixture alignment |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | UNSTABLE | **Ready** — may overlap stacked P014 work (#391); compare before merge |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | DIRTY | **Valuable** — rebase; rule-reference page changed on `main` |
| [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) | `fix/ester-p026-font-policy` → `main` | DIRTY | **Uncertain — keep open** — LaTeX origin-aware advisory P026 behavior not in #398; decide before merge |
| [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) | `fix/ester-q-matrix-coverage` → `main` | DIRTY | **Ready for review** — false-positive fixes, confidence labels, Q partial tier |
| [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389) | `fix/p023-body-spacing-highlight-table-exclusion` → `fix/confidence-grouping-sorting` | UNSTABLE | **Stacked** — presentation stack |
| [#390](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/390) | `fix/wrapper-detection-preprocessing-notice` → `fix/p023-body-spacing-highlight-table-exclusion` | UNSTABLE | **Stacked** |
| [#391](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/391) | `fix/p014-frontmatter-heading-centering-evidence` → `fix/wrapper-detection-preprocessing-notice` | UNSTABLE | **Stacked** |
| [#392](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/392) | `fix/p011-toc-margin-warning-presentation` → `fix/p014-frontmatter-heading-centering-evidence` | UNSTABLE | **Stacked** |
| [#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) | `fix/p015-wrapped-continuation-lines` → `fix/p011-toc-margin-warning-presentation` | UNSTABLE | **Stacked** — may overlap #400 P015 detector work; compare before merge |
| [#396](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/396) | `fix/p018-toc-list-rule-reference-split` → `fix/p015-body-indent-ester-split` | DIRTY | **Needs clean main-based replacement** — do not merge stacked branch as-is |

## Dependency graph (open stacks)

```
main (fbefbb6)
 ├── Independent PRs: #311, #349, #362, #375, #376, #385, #386, #388
 │
 ├── Presentation stack
 │    fix/confidence-grouping-sorting
 │     └── #389 → #390 → #391 → #392 → #393
 │
 └── Legacy Ester P018 stack (superseded for P026/P015)
      fix/p015-body-indent-ester-split  ← base branch kept for #396 reference only
       └── #396  fix/p018-toc-list-rule-reference-split  (needs clean replacement from main)
```

**Land on `main` today (already done):** #397 → #398 (P026) → #399 (P018 parser fix) → #400 (P015).

## Recommended next development sequence

1. **#388** — review/merge independently if still valuable after rebase on `fbefbb6`.
2. **#386** — decide whether LaTeX origin-aware P026 advisories should be ported onto `main` separately from #398.
3. **Clean main-based replacement for #396** (P018 TOC/LoT/LoF public rule-reference split) — do **not** rebase the stacked #396 branch onto obsolete #395.
4. Presentation stack **#389–#393** — merge as a unit or cherry-pick after comparing with landed #400 P015 work.
5. Rebase UX/docs PRs **#385**, **#362** after `main` stabilizes.

## PRs requiring explicit confirmation before close

| PR | Reason |
|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Superseded in spirit by geometry-driven location labels on `main` |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | Policy docs — may still carry unique content |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | Open product-policy question on "Review needed" prefix |
| [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) | Distinct LaTeX-origin P026 advisory path — not redundant with #398 without review |

## Cleanup guardrails

- Do **not** delete `fix/p015-body-indent-ester-split` while #396 remains open (it is #396's base branch).
- Do **not** start **P084** as part of PR cleanup.
- Do **not** close **#396** until a clean main-based replacement is ready or explicitly abandoned.

## Historical triage

- [pr_and_stash_triage_20260619.md](pr_and_stash_triage_20260619.md) — pre-#372 PR #311 / #305 record
- Superseded 2026-06-25 / 2026-07-01 bullets inside [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
