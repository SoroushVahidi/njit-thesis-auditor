# Ester Current Consistency Audit

> **Purpose:** Documentation-only audit of how the current auditor (both
> student-facing wording and actual detector/display behavior) compares
> against the latest available Ester Flaim source materials. This audit
> does **not** implement any fix, wording change, detector change, or
> presentation split.
>
> **Recorded:** 2026-07-03 (base `origin/main` @ `425f14442a4dca3701676b4c66db368d7aab46c1`,
> merge of PR #430; **updated 2026-07-03 after PR #431 merged**, `origin/main` @
> `ad9ddada7a82fd1552c97f3e4e9bd9d6b16c1728`)
>
> **Related:** [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) ·
> [ester_language_alignment_audit.md](ester_language_alignment_audit.md) ·
> [ester_current_wording_inventory.md](ester_current_wording_inventory.md) ·
> [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md) ·
> [ester_policy_review_p021_p026.md](ester_policy_review_p021_p026.md) ·
> [ester_broad_presentation_split_plan.md](ester_broad_presentation_split_plan.md) ·
> [ester_broad_rule_atomic_mapping.md](ester_broad_rule_atomic_mapping.md) ·
> [student_facing_presentation_cleanup_plan.md](student_facing_presentation_cleanup_plan.md) ·
> [highlight_quality_improvement_plan.md](highlight_quality_improvement_plan.md)

---

## Source materials and freshness

| Source | Identifier | Latest Drive access this session? | Notes |
|---|---|---|---|
| Google Sheet — NJIT Thesis Auditor Formatting Rules | Spreadsheet ID `1IohAmbslfX1orMDr7gx6oJyGGTqAV_AAtF31GP-57Gc` | **No** | Public CSV export returned HTTP 401; no OAuth session available in this environment. |
| Excel/Drive — `260330 YESNO audit logic matrix.xlsx` | Drive/file ID `188x75m0ST3EWX9eiXcI2tBHn-plmeV6S` | **No** | Drive API `files.get` call using the local `gcloud` application-default credential returned HTTP 403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT` (that credential belongs to an unrelated GCP/Vertex project, not a Drive-scoped user session). |
| Repo mirror — `data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx` | Git LFS object `sha256:72587b86...` | Tracked in repo | Last committed 2026-05-21 22:03:06 -0400. This is the freshest concrete artifact available in this environment and was used as the practical stand-in for the Excel matrix. |
| Gmail feedback threads | — | Not committed, not accessible | No local mirror exists; all Gmail-derived content in the repo comes secondhand through the docs below. |
| `docs/status/ester_feedback_source_of_truth.md` | — | Repo doc | Primary transcription of Ester's sheet language; last recorded 2026-07-02. |
| `docs/status/ester_language_alignment_audit.md`, `ester_current_wording_inventory.md`, `ester_wording_alignment_checkpoint.md` | — | Repo docs | Wording-layer audits/checkpoints for Slices 1–6 (PRs #414–#420). |
| `docs/status/ester_policy_review_p021_p026.md` | — | Repo doc | P021/P026 policy conflict record (recorded post–PR #421, 2026-07-03). |
| `docs/status/ester_broad_presentation_split_plan.md`, `ester_broad_rule_atomic_mapping.md` | — | Repo docs | Broad-rule (P014/P015/P017/P018/P019/P020/P024/P025/P027) split planning (PRs #423–#424). |
| `docs/status/student_facing_presentation_cleanup_plan.md` | — | Repo doc | Sorting/confidence/priority/highlight planning (PR #425). |
| `docs/status/highlight_quality_improvement_plan.md` | — | Repo doc | Highlight-region planning (PR #428). |

### Source-freshness limitation

**Latest Drive version was not directly accessible from this environment.**
Both the Google Sheet export URL and the Google Drive API were probed
read-only (no writes, no auth changes) and both failed for lack of a
Drive-scoped credential — this is an environment limitation, not a
decision to skip verification. This audit therefore uses the **latest
repo-available Ester source-of-truth docs and the tracked local raw Ester
files** (`data/raw/ester/`, including the tracked `260330_YESNO_audit_logic_matrix.xlsx`
LFS object) as the best available proxy for "latest." Any finding below
that depends on the Excel/Sheet content (chiefly P021 and P026) should be
read as **"per the repo's existing transcription of Ester's sheet,"** not
as independently re-verified against a live Drive fetch today.

---

## Part A — Open PR status

**Update (2026-07-03):** PR #431 (`fix: show confidence badge on every
problem card`) was CI-clean, was confirmed to touch only display-layer
files (`src/njit_auditor/web_app.py`, `src/njit_auditor/templates/job.html`,
`src/njit_auditor/templates/problem_group.html`,
`src/njit_auditor/templates/_macros.html` (new),
`tests/test_problem_drilldown.py` — no `src/njit_auditor/rules/`, no
detector constants, no thresholds, no sorting/highlight-selection logic),
and was **merged** (merge commit `ad9ddada7a82fd1552c97f3e4e9bd9d6b16c1728`).
The section below is preserved as a historical record of the pre-merge
open-PR snapshot; see "Confidence display" further down for the current,
post-merge status.

```
gh pr list --state open --json number,title,headRefName,baseRefName,mergeStateStatus,updatedAt
```

(as of the original audit pass, before #431 merged)

| # | Title | Base | Merge state | Updated |
|---|---|---|---|---|
| ~~431~~ | ~~fix: show confidence badge on every problem card~~ | main | CLEAN → **MERGED** | 2026-07-03T03:35:53Z |
| 385 | Remove per-card repeated metadata from rule reference page | main | UNKNOWN | 2026-06-30 |
| 376 | Fix P014 frontmatter heading centering false positive | main | UNKNOWN | 2026-06-26 |
| 375 | Align clean_minimal demo fixture docs with actual audit output | main | UNKNOWN | 2026-06-26 |
| 362 | Clarify Review needed warning prefix policy | main | UNKNOWN | 2026-06-24 |
| 349 | Preserve autonomous policy and Ester feedback audit | main | UNKNOWN | 2026-06-22 |
| 311 | Add sub-page location labels for PDF findings | main | UNKNOWN | 2026-06-15 |

Old open PRs (#311, #349, #362, #375, #376, #385) remain paused per existing
policy; this audit does not merge or rebase any of them.

## Part A — Base fetch

```
git fetch origin
git rev-parse origin/main
```

Original base SHA: **`425f14442a4dca3701676b4c66db368d7aab46c1`** (merge of
PR #430, `fix/p011-highlight-coverage`).

**Updated base SHA after PR #431:** **`ad9ddada7a82fd1552c97f3e4e9bd9d6b16c1728`**
(merge of PR #431, `fix/confidence-badge-every-card`). This document and its
branch were updated to merge `origin/main` at this SHA so the audit reflects
current `main`.

---

## Audit scope

This audit covers:

- rule catalog / `/rules` reference wording (`data/processed/rules/project_added_rules.json`);
- website problem-card wording (`web_app.py` overrides, `finding_explanations.py`, `polished_comments.py`, `issue_type_explanations.py`);
- remediation wording;
- detector behavior and constants (read-only inspection only — nothing changed);
- sorting/display behavior (`report_view.py` sort modes);
- confidence labels;
- highlight behavior (`highlight_targeting.py`, `pdf_highlight.py`);
- known broad-rule presentation-split candidate areas.

**This audit does not implement any fix, wording change, detector change, threshold change, or presentation split.**

---

## Summary of consistency status

| Area | Current status | Consistency with Ester | Risk | Recommended next action |
|---|---|---|---|---|
| Wording Slices 1–6 (29 rules: P011,P013,P023,P028–P032,P036,P039–P050,P053–P055,P066–P068,P074,P078) | Merged (PRs #414–#420) | consistent | low | None — maintain as new rules are added. |
| P021 word-count policy | Detector unchanged: `PHD_WORD_LIMIT=350`, `MS_WORD_LIMIT=150` | needs policy review | high | Send policy-confirmation message to Ester before any change (draft already in `ester_policy_review_p021_p026.md`). |
| P026 font policy | Detector accepts TNR/Arial/Computer Modern/Latin Modern + near-equivalent serif aliases; Ester sheet names only 3 families | needs policy review | high | Same as above — confirm whether Latin Modern/aliases should be explicitly sanctioned. |
| Broad umbrella rules (P014/P015/P017/P018/P019/P020/P024/P025/P027) | Wording aligned at umbrella level; atomic public-card mapping fully planned (docs only) but **not implemented** except P015A/B, P018A–Q (pre-existing) | partially consistent | medium–high | Implement P014 presentation-split prototype (lowest risk per mapping doc) once other UI cleanup settles. |
| Page-order sorting | `SORT_MODE_PAGE` implemented and merged (PR #426) | consistent | low | None — verify test coverage stays current. |
| Confidence labels | `_confidence_label()` returns only "High/Medium/Low confidence" (PR #427); "Needs review"/"Mixed confidence" strings removed | consistent | low | None on main job page. |
| Confidence badge — every card | Present on main job page (PR #427) **and** on category/rule/issue-type drill-down pages (PR #431, merged) | consistent | low | Live verification/restart after #431 if not already done. |
| Priority/Severity filter label | Renamed from "Priority" to "Severity" on both `job.html` and `rules.html` (PR #427) | consistent | low | None. |
| P011 highlight coverage | Now unions **all violating lines'** boxes (PR #430), not just the single worst line | mostly consistent | medium | Still not a true `table_bbox` (only unions lines that individually violate, not the full table region including compliant cells) — flagged in `highlight_quality_improvement_plan.md` as future detector-metadata work. |
| Table/list/figure highlight gaps | P035 already unions a full region (`body_bbox`/`caption_bbox`); P031/P040/P045/P046/P048/P053/P054/P068 still store no bbox or only a single worst-entry bbox | partially consistent | medium | Scope one rule family at a time per `highlight_quality_improvement_plan.md`; requires small `details` additions (detector work), not presentation-only. |
| P014 presentation-split candidate | Fully mapped (`ester_broad_rule_atomic_mapping.md`) as the lowest-risk first prototype; not implemented | not implemented | low (once implemented) | Implement as the first presentation-split prototype. |
| Stale dead-code catalog entries | `("P025","title_page_graduation_month_invalid")` still present in `finding_explanations.py`, `polished_comments.py`, `issue_type_explanations.py` (issue now emitted exclusively under P074) | inconsistent (dead code, unreachable) | low | Clean up in a future wording-only PR; does not affect current student output since P074 path is used exclusively. |

---

## Rule-by-rule consistency table

Legend — **Mismatch type:** none / wording-reference / remediation-reference /
detector-behavior / threshold-or-constant / policy-unclear /
presentation-split-needed / metadata-gap / source-freshness / duplicate-risk.

| Rule | Ester source expectation | Current rule-reference wording | Current auditor behavior | Consistency status | Mismatch type | Risk | Recommended action | Notes |
|---|---|---|---|---|---|---|---|---|
| P011 | Strict margin containment; text/tables/figures must not enter required margins | "Is all text contained entirely within the required page margins?" | Flags per-line overflow; highlight now unions **all** violating lines' boxes (PR #430) | mostly consistent | detector-behavior | medium | Consider table_bbox union for full-table overflow (future, detector-scoped) | PR #407 grouping / PR #430 union both preserved. |
| P012 | No edit requested | "Does the PDF contain annotations/comments?" | Detects PDF annotation objects | consistent | none | low | Keep as-is | |
| P013 | Page number exactly bottom-center, 0.5in | `/rules` question matches; job text frames as a manual-verification candidate signal, not a defect (defers to P019/P028/P037) | `page_number_candidate` finding: geometry/position only | consistent | none | low | Keep as-is | Wording-aligned since Slice 1 (PR #414). |
| P014 | One binary per named front-matter heading page (Approval, Bio Sketch, Ack., TOC, LoT, LoF) | Single umbrella catalog question covering all 6 pages | Two issue_types (`frontmatter_heading_layout_issue`, `frontmatter_heading_not_centered`); page identity via `details.heading`/`source_q_rule_id` | partially consistent | presentation-split-needed | medium | Implement P014 split (lowest-risk first candidate per atomic mapping) | No P014A–F public cards exist yet, unlike P015/P018. |
| P015 | Split front matter (Abstract→P044, Ack.→P043) from body indentation | Parent hidden on `/rules`; P015A/B public cards exist | Detector already skips Abstract/Ack. pages; only 2 issue_types (P015A/B) | mostly consistent | presentation-split-needed | low | Verify job cards route through P015A/B consistently | Already closest to done of the broad rules. |
| P017 | Split figure sentence-case+period vs. table title-case+no-period | Single combined catalog question | issue_types distinct but figure/table context lives in a detail field, not issue_type name | partially consistent | presentation-split-needed | medium | Confirm context field name before splitting | PR #407 LoF word-naming preserved. |
| P018 | One binary per YES/NO matrix TOC/LoT/LoF row | Parent hidden; **P018A–Q (17 cards)** already exist | Backend spans P018/P024/P032/P036/P039/P042/P046/P048 | mostly consistent | presentation-split-needed | medium | Audit job-card routing consistency (not new atomics) | Most complete existing split; remaining gap is display-routing consistency, not detection. |
| P019 | Split front-matter vs. body pagination per matrix row | Vague umbrella ("candidates…obvious…") | 5 issue_types across page/doc level; P013/P022/P028/P029/P037 already carry the atomic pieces | partially consistent | presentation-split-needed | high | Confirm whether "body starts at 1" has an issue_type before assuming a detector gap | P037 must not be folded in (PR #407 sensitive). |
| P020 | Separate binary per heading level (L1–L5) | Single question; catalog covers heading vs. table-title context only (not levels 1/3–5, which belong to P014/P027) | One issue_type, split by `details.source` ("heading"/"caption") | partially consistent | presentation-split-needed | medium | Split by context, not level, per verified mapping | Overlaps P027 (L2) and P017 (table title) — must pick one owner before splitting. |
| P021 | MS ≤200 words / PhD ≤400 words (per repo transcription of Ester sheet) | "Does the abstract exceed the NJIT word-count limit for the detected degree type?" / "PhD ≤350, MS ≤150" | `PHD_WORD_LIMIT=350`, `MS_WORD_LIMIT=150`; ambiguous degree type defaults to PhD limit | needs policy review | threshold-or-constant | high | Confirm limits with Ester/policy owner before any change | Constants conflict — not resolvable by rewording alone. |
| P022 | Per-page no-number binaries (Abstract, Title, Approval, Copyright) | Single question naming all 4 page types | One rule, per-`page_type` findings already | mostly consistent | presentation-split-needed | low | Low-priority consolidation | Already page-specific in job layer. |
| P023 | Double-spaced Ch.1–References, with named exceptions | "Is body text double-spaced, except for tables, figure descriptions, bullet points, and multi-line titles?" | Median-line-gap heuristic; exceptions excluded from sampling | consistent | none | low | Keep as-is | Wording-aligned since Slice 1. |
| P024 | Atomic TOC/List capitalization/punctuation questions | "Do TOC/LoT/LoF entries follow expected capitalization and punctuation style?" | 4 distinct issue_types; some already delegated to P018A–C | partially consistent | presentation-split-needed | medium | Split `list_of_tables_title_case`/`list_of_figures_sentence_case`/`unexpected_terminal_punctuation` next | PR #407 flagged-word presentation preserved. |
| P025 | Page-level structural binaries; DC wrapper = notice | Single umbrella question for 4 structural checks | 5 real issue_types + DC-wrapper notice (kept as notice, PR #407) | partially consistent | presentation-split-needed | medium | Split into 5 page-level cards | Stale dead `title_page_graduation_month_invalid` entries under P025 are unreachable (see duplicate-risk note below). |
| P026 | TNR, Arial, Computer Modern Typeface family; 12pt except tables/figures | "Does the body text use Times New Roman 12pt (or an accepted equivalent)?" | Accepts TNR/Arial/Computer Modern/**Latin Modern**/near-equivalent serif aliases; 11–13pt tolerance; page-level majority-of-page violation rule | needs policy review | policy-unclear | high | Confirm accepted-family scope and table/figure exemption mechanism with Ester | Detector is more permissive than the literal 3-family list; lowers FP risk but is an unconfirmed policy expansion. |
| P027 | Separate binary per heading level (L2–L5) | Single question | issue_type already **is** the split (`level1_not_all_caps` … `level5_...`) | mostly consistent | presentation-split-needed | low (PR407-sensitive) | Cleanest split candidate after P014; do not weaken bold-gate | PR #407 bold-heading gate must be preserved exactly. |
| P028 | Front matter=Roman, body=Arabic | "Do front-matter numbered pages use lowercase Roman numerals and body pages use Arabic numerals?" | Region-based style check | consistent | none | low | Keep as-is | Wording-aligned since Slice 5. |
| P029 | Front-matter Roman sequence continuous | "Do visible lowercase Roman numerals...appear in a continuous increasing sequence?" | Sequence-gap/repeat/decrease heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 5. |
| P030 | Per-section "(Continued)" heading binary | Matches | Conservative continuation-heading heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 1. |
| P031 | Bold Table/Figure + Page column headers present | Matches | Header-zone label-presence heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 2. |
| P032 | Wrapped entry internal single-spacing | Matches | Gap-heuristic vs. font-size-relative threshold | consistent | none | low | Keep as-is | Wording-aligned since Slice 2. |
| P036 | Double-spacing between entries | Matches | Inter-entry gap heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 2. |
| P037 | Sequential Roman anchored to preceding section (PR #407 dynamic logic) | Catalog wording still names the fixed template values (bio=iv, ded=v, ack=vi, toc=vii, lot=viii) as the NJIT-template anchor | `pdf_roman_section_anchors.py` computes expected value dynamically from the preceding detected section, not a hard-coded constant | mostly consistent | wording-reference | medium (PR407-sensitive) | Confirm wording describes the computed anchor, not a rewrite risk | **Do not** casually reword — must continue to describe computed, not hard-coded, expectation. |
| P039 | Per-level TOC hierarchy indent binary | "Are level-2 and level-3 Table of Contents entries indented to show hierarchy?" | Median-indent comparison heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 2. |
| P040 | Per-entry LoF terminal punctuation binary | "Does every figure description in the List of Figures end with terminal punctuation?" | Per-entry, page-relative index preserved (PR #407) | consistent | none | low | Keep as-is | Wording-aligned since Slice 2. |
| P041 | Dedication page header-free binary | Matches | Top-margin scan heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 3. |
| P042 | Appendix entry formatting binary (single vs. multiple) | Matches | Q058/Q059 pattern checks | consistent | none | low | Keep as-is | Wording-aligned since Slice 3. |
| P043 | Acknowledgements indentation binary (Q044/Q045) | Matches | Paragraph-block indentation heuristic; complements P015 | consistent | none | low | Keep as-is | Wording-aligned since Slice 6; PR #407 continuation-line handling preserved. |
| P044 | Abstract indentation binary (Q002/Q003) | Matches | Paragraph-block indentation heuristic; complements P015 | consistent | none | low (PR407-sensitive) | Keep as-is; do not regress continuation-line fix | Wording-aligned since Slice 6; PR #407 continuation-line false-positive reduction preserved untouched. |
| P045 | Bio Sketch publication layout binary (hanging indent, spacing) | Matches | Geometry-only heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 4. No bbox stored — highlight metadata gap (see highlight plan). |
| P046 | Separate LoT vs. LoF entry-number column alignment binaries | Single combined question ("all table numbers...and all figure numbers...") | Section-level finding (one per LoT/LoF), stores only worst-entry bbox | mostly consistent | presentation-split-needed / metadata-gap | low | Split by list context (display-only); consider column-region bbox union later | Wording-aligned since Slice 2 at the word level; still bundles LoT+LoF in one sentence. |
| P047 | Bio Sketch bullet single-spacing binary | Matches | Geometry-only heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 4. |
| P048 | Separate LoT vs. LoF page-number column alignment binaries | Single combined question | Section-level finding, worst-entry-based | mostly consistent | presentation-split-needed | low | Same as P046 | Wording-aligned since Slice 2. |
| P049 | Split bold vs. right-alignment of "Page" header | Combined question ("bold and right-aligned") | Two distinct issue_types already exist | mostly consistent | presentation-split-needed | low | Split display only | Wording-aligned since Slice 2. |
| P050 | "Table"/"Figure" header bold binary | Matches | Bold-style heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 1. |
| P053 | LoT entries free of final period | Matches | Structural period-check | consistent | none | low | Keep as-is | Wording-aligned since Slice 3. |
| P054 | TOC entries free of final period | Matches | Structural period-check | consistent | none | low | Keep as-is | Wording-aligned since Slice 3. |
| P055 | Entries only in the correct list (no Figure-in-LoT / Table-in-LoF) | Matches | Prefix-mismatch heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 3. No bbox confirmed — flagged for closer highlight-metadata look. |
| P066 | Bio Sketch degrees most-recent-to-oldest | Matches | Year-token ordering heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 4. |
| P067 | Bio Sketch publications most-recent-to-oldest | Matches | Year-token ordering heuristic (citation-block aware) | consistent | none | low | Keep as-is | Wording-aligned since Slice 4. |
| P068 | Approval Page committee role labels + signature/date blocks | Matches | Curated-phrase + indicator-count heuristic | consistent | none | low | Keep as-is | Wording-aligned since Slice 4. No bbox at all — flagged in highlight plan as needing scoping before any fix. |
| P074 | Graduation month exactly August/December/May | "Does the Title Page display a graduation month that is exactly August, December, or May?" | Regex match on title page, single line | consistent | none | low | Keep as-is | Wording-aligned since Slice 3. |
| P078 | Abstract free of "paper"/"article" and first-person pronouns | Matches | Regex match against extracted abstract body text | consistent | none | low | Keep as-is | Wording-aligned since Slice 3. |

---

## Known likely inconsistencies (confirmed this session)

### P021 — abstract word-count policy

- **Current detector constants (`src/njit_auditor/rules/latex_abstract.py:26-27`):** `PHD_WORD_LIMIT = 350`, `MS_WORD_LIMIT = 150`. Both the LaTeX-source and PDF paths import these same two constants.
- **Repo transcription of Ester's sheet (per `ester_feedback_source_of_truth.md` / `ester_policy_review_p021_p026.md`):** MS ≤200 words, PhD ≤400 words.
- Degree-type inference (`infer_degree_type()` / `_infer_degree_from_pdf()`) is a heuristic keyword scan that **defaults to the PhD (higher) limit** when ambiguous.
- **Status: needs policy review / threshold-or-constant / detector-behavior. Not changed by this audit.**

### P026 — font policy

- **Current detector (`src/njit_auditor/rules/pdf_font_compliance.py`):** accepts Times New Roman, Arial, Computer Modern, **and Latin Modern**, plus several near-equivalent serif aliases (NimbusRomNo9L, TeX Gyre Termes, Liberation Serif, FreeSerif, STIX); 12pt ±1pt (11.0–13.0pt) tolerance; violation only fires when both count ≥5 **and** fraction ≥50% of body candidate spans on a page (page-level, not single-span).
- **Repo transcription of Ester's sheet:** Times New Roman, Arial, and "Computer Modern Typeface family"; 12pt except tables/figures.
- Latin Modern and the serif aliases are **not** named in Ester's list — the detector is more permissive than the literal source text.
- **Status: needs policy review / detector-behavior / policy-unclear. Not changed by this audit.**

### Broad rules

P014/P015/P017/P018/P019/P020/P024/P025/P027 remain **partially consistent**
with Ester's one-question-per-row style because they are internally broad
umbrella rule_ids, even where wording is already aligned at the umbrella
level. The atomic mapping (`ester_broad_rule_atomic_mapping.md`) has fully
scoped **P014 as the lowest-risk first implementation candidate** (six
page-level cards, zero PR #407 entanglement, zero cross-rule overlap). P018
and P015 already have the most complete splits (P018A–Q, P015A/B) — their
remaining gap is job-card display routing consistency, not new atomics.
**Status: presentation-split-needed. Not implemented by this audit.**

### P037 — Roman numeral sensitivity

`pdf_roman_section_anchors.py` computes the expected Roman numeral for
DEDICATION/ACKNOWLEDGEMENTS/TABLE OF CONTENTS/LIST OF TABLES **dynamically
from the preceding detected section** (PR #407), not from a hard-coded
template. The catalog wording still lists the fixed NJIT-template values
(bio=iv, ded=v, ack=vi, toc=vii, lot=viii) as illustrative examples of that
template. **Any future wording pass must continue to describe the computed
expectation, not revert to implying a fixed anchor is checked in isolation.**

### P043/P044 — continuation-line sensitivity

PR #407's Abstract/Acknowledgements continuation-line false-positive
reduction (`_apply_abstract_indent_presentation`, `abstract_indent_location_label`,
`grouped_finding_display_dedup_key`) is untouched on current main and was
explicitly preserved through Slice 6 (PR #420). **No regression found this
session.**

### Confidence display

**Status: consistent (as of PR #431, merged `ad9ddada7a82fd1552c97f3e4e9bd9d6b16c1728`).**

- Main job page: every visible problem card shows exactly one of **High
  confidence / Medium confidence / Low confidence** — verified in
  `report_view.py`'s `_confidence_label()` and `job.html`'s
  `confidence_badge()` macro. "Needs review" and "Mixed confidence: ..."
  strings were removed by PR #427.
- Category/rule/issue-type drill-down pages (`problem_group.html`): PR #431
  plumbed `confidence_level`/`confidence_label`/`confidence_css_class`
  through `_problem_group_examples()` in `web_app.py` and added the same
  `confidence_badge()` macro (extracted into a shared `_macros.html`) to
  each example card. Every visible example card on these pages now shows
  exactly one confidence badge, restricted to the same three public labels.
  PR #431's own validation notes a live end-to-end check (fresh sample PDF,
  not a cached job) confirming exactly one badge per card on the main job
  page and all three drill-down views, with no "Needs review"/"Mixed
  confidence" text anywhere; this audit did not independently re-run that
  live check.
- **Current expected behavior (verified in source, both surfaces):**
  - every visible problem card on the main job page has exactly one confidence badge;
  - every visible problem card on category/rule/issue-type drill-down pages has exactly one confidence badge;
  - allowed public labels are only High confidence / Medium confidence / Low confidence;
  - "Needs review" and "Mixed confidence" do not appear publicly on either surface.
- **Live verification caveat:** source-level plumbing and PR #431's own
  described live check both confirm this, but no fresh live-server
  verification was performed independently in this update. If the deployed
  live server has not been restarted since PR #431 merged, a live
  restart/verification pass is still recommended before treating the
  deployed site (as opposed to `origin/main` source) as confirmed.

### Page-order sorting

`SORT_MODE_PAGE` exists in `report_view.py` (`VALID_SORT_MODES` includes
`"page_order"`), confirming PR #426 merged. Behavior verified by reading
the sort-mode branch: page-order sort groups by earliest affected page,
default/confidence modes remain intact and selectable. **Status:
consistent.**

### Highlight behavior

- **P011:** `pdf_margins.py` now builds `highlight_bbox` as the union of
  every violating line's box (`min(x0)`/`min(y0)`/`max(x1)`/`max(y1)` across
  `violations`), not just the single worst line — confirms PR #430 merged.
  This is still not a full **table-region** union (it only unions lines
  that individually violate the margin, not the entire table including
  compliant cells) — the gap flagged in `highlight_quality_improvement_plan.md`
  as future, detector-scoped work.
- **Table/list/figure families generally:** P035 already stores a genuine
  full-region `body_bbox`/`caption_bbox` union (the reference
  implementation). P031/P040/P045/P046/P048/P053/P054/P055/P068 either
  store no bbox at all or only a single worst-entry bbox — confirmed
  unchanged from the highlight-quality plan's findings. **Status: partially
  consistent; remaining gaps require small `details`-dict additions in the
  respective detector modules (future, separately scoped, per-rule work).**

---

## Duplicate-risk / metadata-gap note (new this session)

`("P025", "title_page_graduation_month_invalid")` dead-code catalog entries
remain present (and unreachable) in `finding_explanations.py`,
`polished_comments.py`, and `issue_type_explanations.py`. The detector now
emits this issue_type exclusively under `rule_id="P074"`
(`check_pdf_title_page_graduation_month`, already atomic and
wording-aligned since Slice 3 / PR #417). These entries do not affect
current student-facing output (the P074 code path is used exclusively),
but they are stale references that should be removed in a future
wording-only cleanup PR — flagged here, not removed by this audit.

---

## High-priority inconsistency list

1. **P021/P026 policy confirmation** — highest-impact open item; blocks any further wording or detector work on these two rules.
2. **Broad-rule presentation splits, starting with P014** — the largest remaining wording/behavior gap; fully scoped and ready to implement.
3. **Table/list/figure highlight metadata gaps** — P031/P040/P045/P046/P048/P053/P054/P055/P068 still lack a full-region bbox; P011's table-in-margin case is improved (PR #430) but still line-union, not table-union.
4. **P037/P044 wording safeguards** — no regression found, but any future wording pass must keep describing computed (not fixed) Roman-numeral expectations and must not touch the continuation-line presentation machinery.
5. **Stale dead-code catalog entries** (`P025`/`title_page_graduation_month_invalid`) — low risk, but worth a cleanup pass.

(The confidence-badge drill-down gap previously listed here was resolved by
PR #431, merged `ad9ddada7a82fd1552c97f3e4e9bd9d6b16c1728` — see "Confidence
display" above.)

---

## Recommended next PRs (not implemented here)

1. **Live verification/restart after PR #431**, if not already done — confirm on the actual deployed live server (not just `origin/main` source) that every problem card on the main job page and all three drill-down views shows exactly one confidence badge with no "Needs review"/"Mixed confidence" text.
2. **P014 presentation-split prototype** — implement the six page-level cards mapped in `ester_broad_rule_atomic_mapping.md`, with structural-invariant tests (rule_id/issue_type/grouping/anchors/highlight unchanged).
3. **P021/P026 policy-confirmation message to Ester / policy owner** — the draft message already exists in `ester_policy_review_p021_p026.md`; send it and record the answer before any detector change.
4. **Highlight metadata planning for one table/list/figure family at a time** (e.g., P046/P048 column-region union, following the P035 `_union_bbox()` precedent) — each needs its own golden-output comparison since it touches a detector's `details` dict.

---

## Non-goals

This audit does **not**:

- change rules, detectors, thresholds, or `src/njit_auditor/rules/`;
- change website wording, templates, or report JSON schema;
- change tests;
- change rule IDs, issue types, grouping keys, confidence labels, sorting behavior, or highlight behavior;
- commit Ester's raw Excel/Google Sheet exports, private student documents, generated reports, screenshots, or highlighted PDFs;
- implement P021, P026, broad presentation splits, P084, or TOC-leader WIP;
- merge or rebase any of the old paused PRs (#311, #349, #362, #375, #376, #385).

(PR #431 was reviewed, confirmed display-only, and merged as an explicitly
authorized follow-up step — see "Confidence display" above and Part A. This
audit document was then updated to reflect that merge; the update itself
remains docs-only.)
