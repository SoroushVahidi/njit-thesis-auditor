# Atomic Presentation Inventory (2026-07-16)

> **Purpose:** Classify every active, default-enabled `(rule_id, issue_type)`
> pair by whether its student-facing comment and explanation are already
> atomic (one issue type → one specific title/question → one explanation →
> one remediation), or still fall through to wording shared with unrelated
> siblings. This document is **diagnostic only** — it does not change any
> runtime finding, threshold, confidence calculation, or rule ID.
>
> **Recorded:** 2026-07-16, on a worktree branched from origin/main @
> `1f8cb16` (PR #512), as part of the "Ester atomic presentation audit" pass.
> **Related (different axis, larger/deferred scope — see "Related work"
> below):** [ester_broad_rule_atomic_mapping.md](ester_broad_rule_atomic_mapping.md) ·
> [ester_broad_presentation_split_plan.md](ester_broad_presentation_split_plan.md)

## Methodology

Two complementary sources of ground truth were used, matching the two tools
this pass added:

1. **Mechanical scan** — `scripts/atomic_presentation_inventory.py`, built on
   `src/njit_auditor/rule_source_scan.py` (a static AST scan of every
   `AuditFinding(...)` call site in `src/njit_auditor/rules/*.py`, unioned
   with `data/processed/rules/project_added_rules.json`'s `issue_types`
   field). For each pair it calls the real `build_polished_comment()` and
   `explain_issue_type()` and checks whether either falls to its generic
   fallback sentence. This method is regenerable (`python
   scripts/atomic_presentation_inventory.py`) but structurally can only prove
   coverage for pairs it can statically discover — **72 of the true ~140
   active pairs** (see below), because many issue types are built through
   control flow more complex than a simple `name = "literal"` assignment
   (e.g. per-section lookup dicts) and the catalog's `issue_types` field is
   populated for only 26 of 82 rows.
2. **Deep manual audit** (this pass) — every `AuditFinding(...)` call site in
   all 68 rule files was traced by hand (not just grepped for string
   literals), cross-referenced against `polished_comments.py`'s
   `_ISSUE_TEMPLATES`/`_RULE_FALLBACKS`/dispatch branches and
   `issue_type_explanations.py`'s `_RULE_ISSUE_EXPLANATIONS`/dispatch
   branches, by actually calling the functions rather than only reading dict
   keys. This found the true universe: **140 distinct (rule_id, issue_type)
   pairs** across P001–P068, P074, P078 (P001–P010 are the separate TeX-source
   pipeline; P069–P073/P076/P077/P079/P081 are reporting-only with no
   standalone issue type; P082 is experimental/opt-in; P083 is an evaluation
   task with no runtime findings — none of these are counted as "active
   default-enabled" pairs).

The mechanical scan's 72-pair subset is a true subset of the manually-audited
140 — nothing it flags is a false positive, it simply cannot yet discover
every pair on its own. Closing that gap fully would mean either a real
data-flow analysis (higher effort/risk) or hand-encoding all 140 pairs into
the script (a maintenance burden, and it would drift from detector source the
same way the catalog's `issue_types` field already has). Recording both
methods' results here, rather than papering over the gap, is intentional.

## Result: all 140 pairs are atomic as of this pass

Before this pass, the deep manual audit found **25 of the 140 pairs** were
not fully atomic:

| Gap class | Pairs | Fixed this pass |
|---|---|---|
| Comment falls to generic fallback, with a real grammar bug ("...issue issue...") | P014 × 2 | Yes — dedicated `_p014_heading_comment()` dispatch branch |
| Comment falls to generic fallback, explanation already specific | P057 × 2, P059 × 2, P062 × 1, P065 × 2, P078 × 2 (9 pairs) | Yes — 9 new `_ISSUE_TEMPLATES` entries |
| Comment references a template field (`{page_range}`) its own detector never populates, rendering the literal fallback text "listed pages" | P061 × 2 | Yes — reworded to use `{page}`, which the detector does set |
| Comment shares generic rule-level fallback across logically different issue types | P034 × 2 (`copyright_top_margin_header_text`, `copyright_author_mismatch`) | Yes — split into 2 dedicated templates |
| Explanation falls to the generic "This issue type (X) was flagged..." sentence (a softer leak of the internal issue-type name), comment already specific | P057 × 2, P059 × 2, P061 × 2, P062 × 1 (7 pairs) | Yes — 7 new `_RULE_ISSUE_EXPLANATIONS` entries |
| Orphaned dict entries — a stale `(rule_id, issue_type)` string that no detector has ever emitted (confirmed by grepping every detector module) | `("P030","toc_missing_continued_heading")`, `("P033","title_page_mismatch")`, `("P033","title_consistency_mismatch")` — present in 2–3 files each | Yes — removed (dead code, zero behavior change) |
| Explanation not wired for the TeX-source pipeline (P001–P010) | 10 pairs | **Not fixed — see "Deliberately not fixed" below** |
| Dispatch-handled pairs miscounted as gaps by the old dict-membership-only ratchet (P066, P067) | 2 pairs | N/A — these were never actually broken; the ratchet's blind spot was fixed instead (see below) |

After these fixes: **0 of the 140 manually-audited pairs, and 0 of the 72
mechanically-discoverable pairs, fall to a generic fallback anywhere.**
`scripts/atomic_presentation_inventory.py`'s own run confirms this for its
72-pair subset:

```
72 active (rule_id, issue_type) pairs classified.
  ATOMIC: 72
  PRESENTATION_SHOULD_BE_REFINED: 0
```

**Potentially requires detector restructuring: 0.** A spot-check of the ~19
rules with the most fragmented issue-type sets (P019, P027, P025, P034,
P031/46/48/49/50, P057/59/62/65/78) against each rule's catalog `question`
field found no case where a shared public question is genuinely ambiguous
across its sibling issue types — none were force-fit into this bucket.

## Deliberately not fixed (out of scope for this pass)

- **P001–P010 explanation coverage** (the TeX-source pipeline). Traced
  end-to-end: `explain_issue_type()` (the function these gaps live in) is
  only ever called from `web_app.py` and `report_view.py`, both of which are
  reachable exclusively from the PDF/web pipeline. The TeX CLI path
  (`report_outputs.py`, `cli.py`) never calls it. This gap therefore has zero
  live exposure surface today — fixing it would be safe but not
  presentation-visible to any current user, so it was deprioritized in favor
  of the 25 pairs that are actually rendered to students.
- **A more granular per-metadata-value split** (e.g. splitting P014's 2
  issue types further into 6 separate per-heading public questions, keyed by
  `details["heading"]`, as proposed in
  [ester_broad_rule_atomic_mapping.md](ester_broad_rule_atomic_mapping.md)).
  That document's proposal is a **larger, more speculative future step**
  operating on a different axis (metadata-value atomicity, not issue_type
  atomicity) than this pass's explicit scope. The task that produced this
  document explicitly asks for one-issue-type-to-one-card atomicity and
  explicitly forbids splitting detectors "merely for architectural purity" —
  a 6-way per-heading question split is additive content work, not a bug fix,
  and was left untouched.
- Any of the explicitly Esther-policy-dependent items (P011 footer-zone
  margin policy, non-text-element margins, Sample B medium-confidence P011
  review, a possible new TOC sentence-case rule, P084) — see the final report
  for this pass.

## Regenerating this inventory

```
python scripts/atomic_presentation_inventory.py --md-out docs/status/atomic_presentation_inventory_<date>.md
```

The script is safe to re-run at any time — it only reads `build_polished_comment()`
and `explain_issue_type()` output and the rule catalog; it never touches a PDF,
a detector, or runtime findings.
