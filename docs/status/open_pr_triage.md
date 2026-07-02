# Open PR Triage (2026-07-02, PR #406 merged — cleanup still paused)

> **Canonical open-PR index.** Pair with
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
> for baseline `main`, validation, and next actions.

**Baseline inspected:** `main` @ `811838c4` (squash-merge of PR #406, folding in #405's `7e17232`)  
**Live server (2026-07-02):** restarted on `main` @ `811838c4` — no longer dependent on an unmerged branch  
**Open PR count:** **6**

## PR #406 merged (2026-07-02)

**#406 is merged.** Live false-positive and highlight-page regressions are resolved on `main`; verified
with a fresh post-merge live audit. **PR cleanup remains paused** — not because of the live regression
(resolved) but because a separate warning-legitimacy review is still in progress. Do not resume
#311/#349/#362/#375/#376/#385 review until that review concludes.

| Finding | Cause | Action |
|---|---|---|
| User-visible false positives | Live server was **stale** at `fbefbb6` (PR #400 merge); 10 commits behind `main`; old audit job URLs may also show pre-#405 results | Restarted server; run **fresh** audits only |
| Broken “Open highlighted PDF page” | Single-page artifact route from `9ca99c0` was **never merged** to `main`; links opened full PDF + `#page=` | Emergency fix PR restores `/highlighted-page.pdf` |
| Current `main` detector regression? | **No P026 reintroduction** vs `3b4043c`; #405 slightly **reduces** P020 noise (−6 on five-PDF eval) | Do **not** port old #388/#389–#393 detector stacks without strict proof |

**Emergency fix PR:** `fix/live-false-positive-and-highlight-regression` → `main` (highlight-page restore; no detector threshold changes).

## Recent cleanup (2026-07-02)

| Action | Item | Reason |
|---|---|---|
| **Closed** | [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389)–[#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) | Stale presentation stack; no code merged; regression-risk vs landed #400/#402/#405 |
| **Deleted remote branches** | presentation stack branches (top → bottom) | PRs closed; not bases of remaining open PRs |
| **Merged** | [#405](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/405) | Clean #388 replacement — Digital Commons wrapper filtering, P018/P020/P028 FP reductions, page identity enrichment |
| **Closed** | [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) | Superseded by #405 — would reintroduce +298 P026 false positives |
| **Closed** | [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) | Superseded by #398 — CM/LM accepted with no P026A warning |

Earlier same-day cleanup: #394/#395 closed; merged #397–#400/#402/#401; deleted merged prep branches.

## Quick verdict table

| PR | Branch → base | Mergeable | Verdict |
|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | DIRTY | **Paused** — do not touch until live regression resolved |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | DIRTY | **Paused** — docs-only |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | DIRTY | **Paused** — rebase after live fix merges |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | UNSTABLE | **Paused** — docs-only |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | UNSTABLE | **Paused** |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | DIRTY | **Paused** — pending warning-legitimacy review |
| ~~#406~~ | `fix/live-false-positive-and-highlight-regression` → `main` | **MERGED** | Squash-merged at `811838c4`; branch deleted; live server restarted on `main` |

**Closed (2026-07-02):** [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389)–[#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) presentation stack — no code merged.

## Dependency graph (open stacks)

```
main (811838c4 / includes merged #406 + #405)
 └── Independent PRs (paused pending warning-legitimacy review): #311, #349, #362, #375, #376, #385
```

**Ester alignment stack on `main` (complete):** #397 → #398 (P026) → #399 (P018 parser) → #400 (P015) → #402 (P018 public cards) → #405 (wrapper FP reductions). **#388 closed** — would reintroduce P026 false positives. **#389–#393 closed** — stale presentation stack.

## Recommended next development sequence

1. ~~Merge #406 and restart live server at merged `main` SHA; confirm fresh audits + highlight-page UI.~~ **Done (2026-07-02).**
2. Resume review of **#375**, **#376**, **#385**, **#362**, **#349**, **#311** only after the warning-legitimacy review concludes (no auto-port of old detector stacks).

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
