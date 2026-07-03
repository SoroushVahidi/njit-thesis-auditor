# Open PR Triage (2026-07-03, PR #433 merged — 4 new PRs open, older cleanup still paused)

> **Canonical open-PR index.** Pair with
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
> for baseline `main`, validation, and next actions.
>
> **Superseded:** the 2026-07-02 snapshot below (baseline `70dcd95`, PR #407/#408) is preserved as
> historical context only — see the "Historical" sections further down. Everything above that
> point is current.

**Baseline inspected:** `main` @ `07db2fa30b457006cf7524309c8eabcca6ff64c8` (merge of PR
[#433](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/433); short SHA `07db2fa`)  
**Live server:** last confirmed at `425f144` (PR #430) — **3 merges behind** current `main`;
confirm `GET /version` before assuming #431–#433 behavior is live  
**Open PR count:** **10** (4 new, mergeable; 6 older, paused)

## Current open PRs (2026-07-03)

| PR | Title | Kind | `mergeStateStatus` | Verdict |
|---|---|---|---|---|
| [#434](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/434) | `docs: inventory repository polish tasks` | docs-only | CLEAN | **Safe to merge first** — no code/template/test changes |
| [#435](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/435) | `fix: ignore statistical notation in title-case checks` | detector fix (P020/P024/P027 shared helper) | CLEAN | **Safe candidate** — narrow, tested false-positive fix; no threshold/rule-ID/schema change |
| [#436](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/436) | `fix: highlight affected list entries for punctuation warnings` | presentation/evidence fix (P040/P053/P054) | CLEAN | **Safe candidate** — additive `bbox` metadata only, no detector semantics change |
| [#437](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/437) | `fix: polish P011 margin warning evidence` | presentation/evidence fix (P011) | CLEAN | **Safe candidate** — additive highlight/guide metadata + wording only; thresholds/strictness unchanged |

All four are independent of each other and of the older paused PRs below — they can be reviewed
and merged in any order, though **#434 first** is lowest-risk since it touches no source files.

**Not touched by this triage refresh (policy judgment, not implementation):**

| Item | Why it's a policy question, not a PR |
|---|---|
| P021 abstract word-count limits | Ester sheet (200/400) conflicts with current detector constants (150/350) — needs a human/Ester decision, recorded in `ester_policy_review_p021_p026.md`, before any PR is opened |
| P026 accepted font families | Detector accepts more families (Latin Modern, serif aliases) than Ester's literal 3-name list — same policy-review doc, same "confirm before changing" status |

## Older open PRs — unchanged, still paused

| PR | Branch → base | Mergeable | Kind | Verdict |
|---|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | DIRTY | presentation | **Paused** — do not touch without explicit instruction |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | DIRTY | docs-only | **Paused** — do not touch without explicit instruction |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | DIRTY | wording/policy | **Paused** — open product-policy question |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | UNSTABLE | docs-only | **Paused** — do not touch without explicit instruction |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | UNSTABLE | detector fix | **Paused** — do not touch without explicit instruction |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | DIRTY | presentation | **Paused** — pending warning-legitimacy review |

These six PRs predate the current Ester wording/presentation/highlight work (PRs #411–#437) and
have not been re-triaged against the current `main`. **Do not merge, close, rebase, or delete any
of them without explicit human instruction** — several are likely stale against current `main` and
need a fresh conflict/relevance check before any action, not just a rebase.

## Current cleanup queue (recommended order)

1. **#434** (docs-only inventory) — merge first, zero behavior risk.
2. **#435, #436, #437** (independent detector/presentation fixes) — review and merge in any order;
   each has its own passing test suite and does not depend on the others.
3. **P021/P026 policy resolution** — not a PR yet; send the drafted questions in
   `ester_policy_review_p021_p026.md` to Ester/a policy owner. Only after an answer should a
   wording-or-detector PR be scoped.
4. **Older paused PRs (#311/#349/#362/#375/#376/#385)** — re-triage only after explicit human
   instruction to resume that review; expect most to need a fresh rebase/conflict check against
   `main` @ `07db2fa` given how far they now trail.
5. **P084** — remains out of scope; do not start without explicit instruction.

---

## Historical — 2026-07-02 (baseline `70dcd95`, PR #407/#408 merged)

> **Superseded** by the 2026-07-03 sections above. The "Quick verdict table" and "Recommended
> next development sequence" below reflect the 6-PR, `70dcd95`-baseline world and do **not**
> include #434–#437 — use the "Current open PRs" and "Current cleanup queue" sections above
> instead. Preserved here for historical context only.

## PR #407 and PR #408 merged (2026-07-02)

**#407** and **#408** are merged on `main` after the older PR #406 status snapshot. **PR cleanup
remains paused** — not because of detector regressions on `70dcd95`, but because a separate
warning-legitimacy review is still in progress and no human instruction has resumed open-PR
review. Do not touch #311/#349/#362/#375/#376/#385 until that review concludes (or explicit
instruction).

| PR | Summary | Regression guard |
|---|---|---|
| **#407** | Ester-reviewed warning precision: P044 continuation lines; P027 bold-heading requirement; P037 LoT Roman numeral; P011 margin overrun presentation; P024/P040 LoF presentation; P025 DC wrapper **notice** (not problem) | No threshold / rule-ID / schema changes outside scoped presentation fixes |
| **#408** | Web UI sort grouped problem cards by confidence (`?sort=`); display order only | Grouping keys, problem numbers, detector output unchanged |

**Preserved fixes (do not regress when resuming cleanup):** single-page `highlighted-page.pdf`
(#406); Digital Commons wrapper filtering (#405); P015/P018/P026 ester stack (#400–#402).

## PR #406 merged (2026-07-02) — historical context

**#406** resolved live false-positive diagnosis (stale server) and restored single-page highlight
artifacts. Superseded as the status baseline by #407/#408 above; fixes remain on `main`.

| Finding | Cause | Action |
|---|---|---|
| User-visible false positives | Live server was **stale** at `fbefbb6` (PR #400 merge); 10 commits behind `main`; old audit job URLs may also show pre-#405 results | Restarted server; run **fresh** audits only |
| Broken “Open highlighted PDF page” | Single-page artifact route from `9ca99c0` was **never merged** to `main`; links opened full PDF + `#page=` | #406 restores `/highlighted-page.pdf` |
| Current `main` detector regression? | **No P026 reintroduction** vs `3b4043c`; #405 slightly **reduces** P020 noise (−6 on five-PDF eval) | Do **not** port old #388/#389–#393 detector stacks without strict proof |

## Recent cleanup (2026-07-02)

| Action | Item | Reason |
|---|---|---|
| **Merged** | [#408](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/408) | Confidence sort for grouped problem cards (UI only) |
| **Merged** | [#407](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/407) | Ester-reviewed warning-precision and presentation fixes |
| **Merged** | [#406](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/406) | Single-page highlighted PDF + live regression diagnosis docs |
| **Closed** | [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389)–[#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) | Stale presentation stack; no code merged; regression-risk vs landed #400/#402/#405 |
| **Deleted remote branches** | presentation stack branches (top → bottom) | PRs closed; not bases of remaining open PRs |
| **Merged** | [#405](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/405) | Clean #388 replacement — Digital Commons wrapper filtering, P018/P020/P028 FP reductions, page identity enrichment |
| **Closed** | [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) | Superseded by #405 — would reintroduce +298 P026 false positives |
| **Closed** | [#386](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/386) | Superseded by #398 — CM/LM accepted with no P026A warning |

Earlier same-day cleanup: #394/#395 closed; merged #397–#400/#402/#401; deleted merged prep branches.

## Quick verdict table

| PR | Branch → base | Mergeable | Verdict |
|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` → `main` | DIRTY | **Paused** — do not touch |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` → `main` | DIRTY | **Paused** — docs-only |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` → `main` | DIRTY | **Paused** |
| [#375](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/375) | `docs/fix-clean-minimal-demo-baseline` → `main` | UNSTABLE | **Paused** — docs-only |
| [#376](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/376) | `fix/p014-frontmatter-centering-false-positive` → `main` | UNSTABLE | **Paused** |
| [#385](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/385) | `ux/rule-reference-card-declutter` → `main` | DIRTY | **Paused** — pending warning-legitimacy review |
| ~~#407~~ | `fix/ester-reviewed-warning-precision` → `main` | **MERGED** | Squash-merged at `1827d8c1` |
| ~~#408~~ | `feat/sort-problems-by-confidence` → `main` | **MERGED** | Squash-merged at `70dcd95` |
| ~~#406~~ | `fix/live-false-positive-and-highlight-regression` → `main` | **MERGED** | Squash-merged at `811838c4`; branch deleted |

**Closed (2026-07-02):** [#389](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/389)–[#393](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/393) presentation stack — no code merged.

## Dependency graph (open stacks)

```
main (70dcd95 / includes merged #408 + #407 + #406 + #405)
 └── Independent PRs (paused): #311, #349, #362, #375, #376, #385
```

**Ester alignment stack on `main` (complete):** #397 → #398 (P026) → #399 (P018 parser) → #400 (P015) → #402 (P018 public cards) → #405 (wrapper FP reductions) → **#407** (Ester-reviewed precision/presentation). **#388 closed** — would reintroduce P026 false positives. **#389–#393 closed** — stale presentation stack.

## Recommended next development sequence

1. Confirm live server at `70dcd95` (or restart) so #407/#408 UI behavior matches local `main`.
2. Resume review of **#375**, **#376**, **#385**, **#362**, **#349**, **#311** only after the
   warning-legitimacy review concludes (or explicit human instruction; no auto-port of old detector
   stacks).

## PRs requiring explicit confirmation before close

| PR | Reason |
|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | Superseded in spirit by geometry-driven location labels on `main` |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | Policy docs — may still carry unique content |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | Open product-policy question on "Review needed" prefix |

## Cleanup guardrails

- Do **not** start **P084** as part of PR cleanup.
- Do **not** merge/rebase #311, #349, #362, #375, #376, or #385 without explicit instruction.

## Historical triage

- [pr_and_stash_triage_20260619.md](pr_and_stash_triage_20260619.md) — pre-#372 PR #311 / #305 record
- Superseded bullets inside [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
