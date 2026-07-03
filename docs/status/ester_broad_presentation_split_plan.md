# Ester Broad Presentation-Split Plan

> **Purpose:** Plan how to make broad/multi-issue rules consistent with
> Ester's Excel style — **one warning = one binary question = one issue =
> one direct remediation** — without changing detector behavior.
>
> This plan is **documentation-only**. It does not implement any split.
>
> **Recorded:** 2026-07-03 (post–PR #422 merge; main @ `11396d12c2de5bc68539301e98616c393378efb8`)
>
> **Related:** [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) ·
> [ester_language_alignment_audit.md](ester_language_alignment_audit.md) ·
> [ester_current_wording_inventory.md](ester_current_wording_inventory.md) ·
> [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md) ·
> [ester_policy_review_p021_p026.md](ester_policy_review_p021_p026.md)

---

## Why broad-rule splitting is needed

- Ester's Excel/Google Sheet style expects **strict binary (YES/NO)
  questions** — one row, one question, one pass/fail outcome.
- Several current rules are **broad umbrella checks**, or use one rule_id
  to cover multiple distinct issues (multiple pages, multiple heading
  levels, multiple sub-cases) that map to several separate rows in Ester's
  matrix.
- Broad warnings are **harder for students to understand** (which of
  several sub-cases actually applies to them?) and **harder for Ester to
  review** against her own row-by-row matrix.
- The goal is to **keep detector behavior stable** while improving how
  findings are presented — students already get a specific `issue_type`
  from most of these detectors today; the umbrella-ness is largely a
  **presentation-layer** problem, not a detection gap.
- Future implementation should **prefer presentation-layer splits first**,
  not detector rewrites. The existing `P018A`–`P018Q` public-card mechanism
  and the `P015A`/`P015B` / `P026A`/`P026B` delegation pattern in
  `web_app.py` (`_public_rule_reference_id()`,
  `_PUBLIC_RULE_ISSUE_REFERENCE`, `_P018_PUBLIC_CARD_SPECS`) already prove
  this pattern works: a `(rule_id, issue_type[, details])` tuple is mapped
  to a display-only atomic card ID with its own binary title and
  remediation, while the finding's actual stored `rule_id` and `issue_type`
  are untouched. This is the template every rule below should follow where
  possible.

---

## Broad-rule inventory

| Rule | Current broad issue | Ester-style atomic targets | Likely implementation path | Behavior risk | Notes |
|---|---|---|---|---|---|
| **P014** | Single catalog question covers all named front-matter heading format checks (all-caps, bold, centered, top) across 6 different pages. | One binary per page: Approval Page, Bio Sketch, Acknowledgements, TOC, List of Tables, List of Figures heading format (Q013, Q021, Q036, Q047, Q061, Q070). | presentation-split-only | low | Findings already carry `source_q_rule_id` per page. No `P014A`–`F` public cards exist yet (unlike P018/P015) — this is the main gap. |
| **P015** | Umbrella catalog question for "body-text paragraph indentation," even though public cards P015A/B already exist and Abstract/Acknowledgements are already split out to P044/P043. | Already close to atomic via P015A (first paragraph flush-left) / P015B (later paragraphs indented) on `/rules`. Remaining gap: audit job cards (not `/rules`) may still surface the parent P015 rule_id/question instead of routing through the same P015A/B labels. | presentation-split-only | low | **Do not casually change P015** — P043/P044 wording was already aligned in Slice 6 (PR #420) and explicitly excluded P015 from that slice. Any P015 work should only extend the existing P015A/B display routing to job cards, not touch detection. |
| **P017** | One catalog question combines figure-description rules (sentence case + terminal punctuation) with table-title rules (title case + no period) into a single sentence. | Split into: figure-description sentence case (Q074), figure-description terminal punctuation (Q075), table-title case (Q065a), table-title no final period (Q065b). Spacing/bold sub-checks are already routed through P032/P050/P055/P056 per the catalog notes. | presentation-split-only | low | `issue_type` values are already distinct in the detector (per LoT vs. LoF context); PR #407's LoF word-naming fix must be preserved in any comment rewrite. |
| **P018** | Internal umbrella rule_id for TOC/LoT/LoF formatting; **already has the most complete atomic split** (P018A–P018Q public cards, Q049–Q059/Q067–Q069/Q077–Q079). | The atomic targets already exist as card specs. Remaining gap is consistency: some audit **job cards** (not `/rules`) may still show the umbrella P018/P024/P032/P036/P039/P042/P046/P048 rule_id/question instead of the delegated atomic label. | presentation-split-only | medium | Highest-impact target precisely because it's the closest to done — the risk is entirely in job-card consistency, not building new atomics. Already-wording-aligned siblings: P031, P032, P036, P039, P040, P046, P048, P049, P050, P053, P054, P055. Preserve PR #407 grouping behavior. |
| **P019** | "Do page-number candidates show obvious sequence, style, or position inconsistencies?" — one internal umbrella question with vague ("candidates", "obvious") catalog wording covering front-matter and body pagination together. | Split into: no visible page number on Abstract/Title/Copyright (→ already P022), front-matter uses lowercase Roman numerals (→ already P028), front-matter Roman numerals sequential (→ already P029), body uses Arabic numerals (→ already P028's body-page branch), body Arabic numbering starts at 1 in Chapter 1 (needs a dedicated atomic — not confirmed to exist today), page numbers bottom-center (→ already P013). | presentation-split-only for the parts with existing atomics; needs-new-atomic-detector for "body numbering starts at 1 in Chapter 1" if no current issue_type covers it | high | Already-wording-aligned siblings: P013 (Slice 1), P028/P029 (Slice 5). **P037 is sensitive** (PR #407 dynamic Roman-numeral logic) — do not fold P037's per-section fixed-template checks into a generic P019 split without preserving that distinction. Confirm during implementation whether a "body starts at 1" issue_type already exists before assuming new detector work is required. |
| **P020** | Single rule_id/question for title-case violations across all title-like PDF lines, without separating by heading level. | Separate binary per applicable context: Level 2 heading title case, table-title title case (already effectively P017's table-title target — avoid duplicating), and any other bold-heading-like line title case. Level 3+ (sentence case) is explicitly **out of scope** for P020 already (handled by P027). | presentation-split-only | medium | **Overlaps P027** for numbered headings — a split must not create two cards asking the same question about the same heading. PR #407's bold-heading gate (a line must be bold before being classified as a heading candidate) must be preserved in any rewrite. |
| **P024** | Broad TOC/LoT/LoF capitalization and punctuation question bundling 4 distinct issue types into one catalog sentence. | Already-distinct `issue_type` values: `toc_level_capitalization`, `list_of_tables_title_case`, `list_of_figures_sentence_case`, `unexpected_terminal_punctuation`. Split target: one atomic public card per issue_type, consistent with the existing partial delegation to P018A–C. | presentation-split-only | low | Partially delegated already (P018A–C cover TOC-level capitalization). Remaining `list_of_tables_title_case` / `list_of_figures_sentence_case` / `unexpected_terminal_punctuation` still need their own atomic routing so job cards don't show the bundled P024 rule_id. Preserve PR #407's P024/P040 page-relative index and flagged-word presentation. |
| **P025** | One rule_id covers 4 distinct structural checks across different front-matter pages (Abstract body presence, title-page degree/institution, Approval-page sparseness, Abstract-before-TOC ordering) — plus a 5th, `digital_commons_wrapper_pages_detected`, that must stay a **notice**, not a problem. | Page-level binaries: Abstract has body text; Title Page has degree phrase; Title Page has institution name; Approval Page has non-sparse committee content; Abstract appears before Table of Contents. (Ester's fuller front-matter structural list — birth date/place, work experience, degree/publication order, dedication centering/italics, acknowledgements content — is **already covered by other, already-atomic rules**: P041, P042, P045, P047, P066, P067, P068, P074, P078, not by P025 itself.) | presentation-split-only | medium | **`digital_commons_wrapper_pages_detected` must keep its PR #407 notice framing** — it is not a defect and must never be presented as one during any split. |
| **P027** | Single rule_id/question covering heading-level style (Level 2 Title Case; Level 3 Sentence case; Level 4/5 Sentence case + period) even though `issue_type` values are already per-level. | Separate binary per level: Level 2 title case, Level 3 sentence case (bold), Level 4 sentence case + period, Level 5 sentence case + period. `issue_type` values (`level1_not_all_caps`, `level2_title_case_issue`, `level3_sentence_case_issue`, `level4_sentence_case_or_punctuation_issue`, `level5_sentence_case_or_punctuation_issue`) already support this split directly. | presentation-split-only | low | **PR #407 added the requirement that a numbered line must be bold before being classified as a heading** — this false-positive fix, and the associated location-label behavior, must be preserved exactly. Do not change detection while splitting presentation. |

---

## Recommended implementation sequence

1. **Documentation-only mapping** from current issue types to proposed
   Ester-style atomic warning cards — one dedicated PR
   (`docs/status/ester_broad_rule_atomic_mapping.md`, see below) that lists,
   for every rule in the table above, the exact `(rule_id, issue_type)` →
   proposed atomic card ID, binary title, and remediation text. No source
   changes.
2. **Presentation-only split** for the broad rules where existing detector
   metadata already supports honest atomic display without any new
   detection — this covers most of P014, P017, P018, P020, P024, P025,
   P027, following the `_public_rule_reference_id()` /
   `_PUBLIC_RULE_ISSUE_REFERENCE` / `_P018_PUBLIC_CARD_SPECS` pattern
   already proven for P015A/B, P026A/B, and P018A–Q.
3. **Wording-only update** for any broad rule (or sub-case) that cannot yet
   be split because its `issue_type` granularity doesn't support an atomic
   card — apply the same conservative, direct-remediation style used in
   Slices 1–6 to the umbrella question/remediation text as an interim step.
4. **New detector work** only where current metadata cannot support an
   Ester-style atomic question at all (e.g., the P019 "body Arabic
   numbering starts at 1 in Chapter 1" sub-case, if no existing issue_type
   covers it — to be confirmed during the mapping PR, not assumed here).
5. **Golden-output comparison** before any detector behavior change —
   before/after finding counts and fields on the canonical evaluation set,
   as already required by [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md)'s
   safety rules.

---

## Guardrails for implementation

- **Do not change detectors while doing presentation splits.** A
  presentation split re-labels and re-routes existing findings for
  display; it must not add, remove, or alter what the detector emits.
- **Preserve rule IDs and existing issue types** unless a separate schema
  migration is planned and reviewed — the split lives in the display layer
  (`web_app.py` reference-ID maps, `report_view.py` routing), not in
  `AuditFinding.rule_id`/`issue_type` on stored findings.
- **Presentation splits may create multiple cards from one detector
  finding only if anchors/grouping/highlights remain stable** — a split
  must not cause a finding to disappear, duplicate, or move to a different
  page/highlight than before.
- **Do not overstate what the detector verifies.** Use "appears to,"
  "detected," or "may need" for heuristic findings, matching the
  conservative style already used across Slices 1–6.
- **Preserve PR #407 and PR #408 behavior** — specifically (from the
  checkpoint doc and this plan): P011 margin-overrun presentation, P024/P040
  LoF presentation, P025 `digital_commons_wrapper_pages_detected` notice
  framing, P027's bold-heading gate, P037's dynamic Roman-numeral
  computation, P044's Abstract continuation-line handling, and PR #408's
  confidence-sort baseline.
- **Do not touch P021/P026** until the policy review recorded in
  [ester_policy_review_p021_p026.md](ester_policy_review_p021_p026.md) is
  resolved by Ester or a human policy owner.
- **Do not use private student documents or generated reports** anywhere in
  planning, fixtures, or examples.

---

## Recommended next PR after this plan

The next PR should be a **documentation-only mapping PR**:

```
docs/status/ester_broad_rule_atomic_mapping.md
```

Its job is to map every current `(rule_id, issue_type)` pair and detector
metadata field, for each rule in the inventory above, to a proposed atomic
Ester-style card: binary title, direct remediation, and (where relevant)
the `source_q_rule_id` it corresponds to in Ester's matrix — **before any
source implementation**. This is the direct analogue of what already
exists implicitly for P018 (`_P018_PUBLIC_CARD_SPECS`) and P015/P026
(`_PUBLIC_RULE_ISSUE_REFERENCE`), made explicit and complete for the
remaining seven rules.

**Do not implement that mapping in this PR** — this plan only recommends it
as the next step.
