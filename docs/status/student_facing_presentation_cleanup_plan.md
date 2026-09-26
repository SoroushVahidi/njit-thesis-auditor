# Student-Facing Presentation Cleanup Plan

> **Purpose:** After the completed Ester wording slices (PRs #414–#420) and
> the broad-rule presentation mapping (PRs #423–#424), the next improvements
> should focus on the **student-facing report experience itself** — how
> problems are ordered, which reliability labels are shown, and how
> accurately highlights point at the actual defect. The report should be
> easier for students to follow in document order, should use Ester's
> style, and should avoid confusing or duplicate labels.
>
> This document is **documentation-only**. It does not implement sorting,
> confidence, priority, highlight, detector, or template changes.
>
> **Recorded:** 2026-07-03 (post–PR #424 merge; main @ `b1fe7d7c0eee63aac5f4c566edd7b7e4a98a6970`)
>
> **Related:** [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md) ·
> [ester_broad_presentation_split_plan.md](ester_broad_presentation_split_plan.md) ·
> [ester_broad_rule_atomic_mapping.md](ester_broad_rule_atomic_mapping.md) ·
> [ester_policy_review_p021_p026.md](ester_policy_review_p021_p026.md)

---

## Current student-facing presentation issues

### 1. Page-order sorting

**Requirement:** Problems should be sortable by page order so warnings from
the same page appear together and students do not need to jump back and
forth through the PDF.

**Current state (verified in `src/njit_auditor/report_view.py`):** a sort
mechanism already exists for confidence —
`SORT_MODE_DEFAULT` / `SORT_MODE_CONFIDENCE_DESC` / `SORT_MODE_CONFIDENCE_ASC`
in `VALID_SORT_MODES`, validated by `normalize_sort_mode()`, and applied by
`sort_grouped_problems()` (a stable sort keyed by
`_grouped_problem_confidence_rank()`). This is exactly the shape a new
`SORT_MODE_PAGE` value should follow. Two implementation details verified
directly in the source, both worth preserving for a new mode:

- `sort_grouped_problems()` is called **once**, at the `web_app.py` route
  level (`sorted_grouped_problems = sort_grouped_problems(grouped_problems,
  sort_mode)`), **after** problem numbers and anchors have already been
  assigned in canonical order (`for problem_number, index in
  enumerate(sorted(visible_indexes), start=1): ...
  problem_anchor=f"problem-{problem_number}"`). This means **today's
  confidence sort mode reorders cards visually without renumbering them** —
  "Problem #3" can appear visually before "Problem #1" when sorted by
  confidence, but its number and anchor never change.
- `sort_grouped_problems()` is documented as never mutating "a card's
  problem numbers, anchors, or grouped occurrences, so links and references
  stay stable."

**Planning details:**

- Add a sorting option such as `page` / `Sort by page` alongside the
  existing `default`, `confidence_desc`, `confidence_asc` values.
- Keep the existing default order as the default.
- Keep PR #408 confidence sorting fully intact — the new mode is additive,
  not a replacement.
- Page-order sort should use the **earliest affected page** for each
  grouped problem. A grouped card's occurrences may span several pages
  (e.g., a repeated indentation issue on pages 12, 15, and 20) — sort by
  the minimum page number among them, not the first-listed occurrence.
- Problems spanning multiple pages should sort by their earliest affected
  page, consistent with the point above.
- Problems without a page number (document-level findings, e.g. P025's
  `possible_frontmatter_order_issue` or the DC-wrapper notice) should
  appear **after** all page-specific warnings, not interleaved based on an
  arbitrary default.
- Within the same page, preserve the existing stable default order (a
  Python stable sort naturally does this if the sort key only distinguishes
  by page).
- **Recommendation, following the confidence-sort precedent found above:**
  page-order sort should also reorder cards **without renumbering them** —
  "Problem #7" stays "Problem #7" wherever it visually lands, exactly like
  confidence sort does today. This keeps anchors and any external links
  (e.g., a markdown report cross-reference, or a bookmarked URL fragment)
  stable regardless of which sort mode a student currently has selected.
- This should be presentation/report behavior only — `sort_grouped_problems`
  operates on already-built `GroupedProblemView` dicts and never touches
  detector output, thresholds, or grouping keys.

---

### 2. Priority vs. confidence confusion

**Requirement:** Student-facing problem cards should show only one
reliability label: **Confidence**. Priority should be hidden from
student-facing problem cards and retained only for developer/internal
references if still useful.

**Current state (verified in `src/njit_auditor/templates/job.html` and
`rules.html`):** the confusion is real and has a precise source — it is
**not** the rule catalog's static `priority` field (`"priority": "high"` in
`project_added_rules.json`) leaking into student view; that field is never
rendered in either template. Instead:

- `job.html:665` — the results-page filter control is `<label
  for="filter-severity">Priority</label>`: a dropdown that filters by
  `severity` (WARNING/FAIL/PASS) and `data-severity` attributes, but is
  **labeled "Priority" in the visible UI text**, sitting directly alongside
  the genuine `confidence_badge` macro output on the same problem cards.
- `job.html:478` — "Filter by priority → Needs fixing" is a shortcut link
  into that same mislabeled severity filter.
- `rules.html:114–116` — the `/rules` reference page has the identical
  pattern: `<label for="rule-filter-severity">Priority</label>`, again
  filtering by `severity_label`, not by the catalog's `priority` field.
- Separately, `job.html`'s `severity_status_badge()` macro renders an
  **Info** / **Review** / **Fail** badge per card (driven by `severity` and
  `triage_tier`) immediately next to the **High/Medium/Low/Mixed/"Needs
  review"** `confidence_badge()` output — two badges that both read as
  "how seriously should I take this," which is the actual source of
  student confusion.

**Planning details:**

- The fix is **not** "stop showing the catalog `priority` field" (it's
  already hidden) — it is **stop labeling the severity/triage filter and
  its shortcut link "Priority"** on both `job.html` and `rules.html`, and
  **reconsider whether the `severity_status_badge` (Info/Review/Fail)
  should keep appearing directly next to the confidence badge** on the same
  card, since together they read as two competing reliability signals.
- A future implementation should decide: (a) rename the filter label to
  something accurate (e.g. "Status" or "Type"), and/or (b) keep the
  severity badge but visually/semantically separate it from the confidence
  badge so a student reads them as two different questions ("is this a
  confirmed defect or a review item?" vs. "how sure is the tool?"), not one
  ambiguous "how important is this" signal.
- The catalog's internal `priority` field (used only for developer
  planning/triage, e.g. in `project_added_rules.json`) should continue to
  exist for internal/developer reference — this document does not
  recommend removing it from the data model, only confirming it is not
  rendered to students (verified: it currently is not).

---

### 3. Three public confidence labels only

**Requirement:** Student-facing confidence must have exactly three public
values: **High, Medium, Low**.

**Current state (verified in `src/njit_auditor/report_view.py`):** the
internal confidence taxonomy is **already** exactly three values —
`_CONFIDENCE_ORDER = ("high", "medium", "low")` and `_CONFIDENCE_LABELS =
{"high": "High", "medium": "Medium", "low": "Low"}`. There is no richer
internal taxonomy (no "likely"/"possible"/other internal buckets) to map
down. The extra labels the requirement is concerned about are **synthesized
by the label-building logic itself**, for two edge cases, both in
`_confidence_label()`:

- **No confidence value present at all** on any occurrence in a grouped
  card → returns the literal string `"Needs review"`.
- **A grouped card contains occurrences at more than one confidence
  level** (e.g., one high-confidence and one low-confidence occurrence
  grouped under the same problem card) → returns `"Mixed confidence: {list}"`
  (e.g. `"Mixed confidence: High, Low"`).

**Planning details:**

- Do not show public labels such as "Needs review," "Likely," "Possible,"
  or other extra categories — per the requirement, this means the "Needs
  review" and "Mixed confidence: ..." strings specifically, since no other
  extra internal categories were found to exist.
- Internal confidence metadata may remain richer if needed in the future —
  today it is not richer, but the normalization logic (`_normalize_confidence`,
  `_ordered_confidence_levels`) already exists as the seam where any future
  richer internal state would be collapsed to the public three.
- Public display should map internal states into High / Medium / Low. For
  the "no confidence value present" case, this likely means defaulting to
  **Low** confidence display (per the requirement: "Uncertain/manual-review
  cases should display as Low confidence, with explanatory text if
  needed") rather than a separate "Needs review" bucket.
- For the "mixed levels within one grouped card" case, the requirement
  implies collapsing to the **lowest** level present, consistent with the
  existing sort-ranking philosophy already coded in
  `_grouped_problem_confidence_rank()` (a mixed card's ascending-sort rank
  is already based on `levels[-1]`, the lowest level present — "a reviewer
  scanning for likely false positives should not have a low-confidence
  occurrence hidden inside a card sorted as high," per that function's own
  comment). Displaying the same card as plain "Low" (with explanatory text
  noting the underlying occurrences vary) would be consistent with that
  existing philosophy, not a new one.
- Sorting by confidence should use High → Medium → Low (descending) and
  Low → Medium → High (ascending) — this already matches
  `_CONFIDENCE_DESC_RANK`/`_CONFIDENCE_ASC_RANK` exactly as implemented
  today; no sort-ranking change is implied by the label-normalization work,
  only the CSS class (`confidence-badge--mixed-orange` / `--unknown`) and
  label text built on top of it.
- This should be a **display normalization** (collapsing `_confidence_label()`'s
  two edge-case branches into the three canonical labels), not a detector-
  confidence rewrite — `details["confidence"]` values emitted by detectors
  are untouched.

---

### 4. Latest Ester Excel/Google Sheet consistency

**Requirement:** Student-facing wording, warning style, rule names, and
remediation language should remain aligned with Ester's latest Excel/Google
Sheet language as much as possible, before each wording/presentation
implementation.

**Planning details:**

- Before starting any future wording or presentation-split PR, check
  whether a newer version of Ester's Excel/Google Sheet source-of-truth
  notes exists (in the private `data/raw/ester/` sources, never committed
  in generated/derived form) and whether it changes any assumption baked
  into [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md)
  or the wording slices already merged (#414–#420).
- Do not rely only on older internal wording docs if Ester's latest sheet
  has a clearer or updated phrase — the source-of-truth doc should be the
  first thing re-checked, not the last.
- Keep the established style from Slices 1–6: **one warning = one binary
  question = one issue = one direct remediation**, and continue using
  "appears to" / "detected" / "may need" for heuristic findings, per the
  checkpoint doc's safety rules.
- If a newer sheet update **conflicts** with current detector behavior
  (P021's limits are now resolved at MS ≤200 / PhD ≤400; P026's accepted-font list
  remains an example of a policy conflict per
  [ester_policy_review_p021_p026.md](ester_policy_review_p021_p026.md)),
  document the conflict as policy/review work in a dedicated doc — do not
  silently change detector behavior or wording to match a newer sheet
  without that review step.
- Do not import private files (Ester's spreadsheet exports, student
  dissertations, review PDFs) or generated reports into the repository at
  any point in this process — per the existing hard constraint already
  honored by every wording-slice and planning PR in this program.

---

### 5. Highlight quality for table/list/figure warnings

**Requirement:** For table-level findings, the highlighted page should show
the full table bounding box when possible, including the full
row/column/table area relevant to the warning, not only isolated detected
words.

**Current state (verified in `src/njit_auditor/highlight_targeting.py`):**
the module's own docstring states its design goal directly: *"Resolve the
smallest reliable PDF highlight boxes for student-facing findings."* This
is the **opposite** design philosophy from what table/row/column-level
findings need — the module is deliberately built to shrink highlights to
the tightest reliable region (a token, a word, a single line), not to
union them into a full table/row/column/figure region. Concretely:

- `resolve_primary_highlight_bbox()` reads `details["bbox"]` plus a fixed
  set of extra keys — `_EXTRA_BBOX_KEYS = ("body_bbox", "caption_bbox",
  "token_bbox", "word_bbox", "rect")` — and unions **only** whichever of
  these a specific detector happens to populate. **There is no
  `table_bbox`, `row_bbox`, or `column_bbox` key recognized today.**
- This means the "highlights only a partial cell" problem the user
  observed is very likely a genuine **metadata gap**, not a bug in the
  union/highlight-drawing logic itself: if a table-related detector (e.g.
  P046 entry-number column alignment, P048 page-number column alignment,
  P031 header alignment) only ever populates `details["bbox"]` with the
  single misaligned token's box, `resolve_primary_highlight_bbox()` has
  nothing else to union it with, no matter how the highlight-drawing code
  is improved.

**Planning details (all conditional on confirming the exact gap per rule
before implementation):**

- Text-span highlights are acceptable for word-level findings (e.g. P020
  title-case, P017 sentence-case single-word issues) — this document does
  not recommend changing those.
- Table-level findings should prefer full **table-region** rectangles when
  the underlying detector can determine the table's bounding box (it
  already scans all rows to compute alignment, so the geometry likely
  exists internally even if not currently exposed in `details`).
- Row-level findings should prefer full **affected-row** rectangles where
  possible.
- Column-level findings should prefer full **affected-column** rectangles
  where possible.
- Figure-level findings should prefer full **figure/caption-region**
  rectangles where possible — `caption_bbox`/`body_bbox` already exist as
  recognized keys for some P035 figure/table placement checks, so this may
  already be partially solved for that rule family and should be checked
  rule-by-rule rather than assumed universal.
- List-entry findings should ideally cover the **full affected entry line
  or wrapped-entry block**, not only one token — the `_LIST_LOCATION_RULE_IDS`
  frozenset (`P018`, `P024`, `P032`, `P036`, `P040`, `P046`, `P053`) in
  `report_view.py` is the existing set of rules with list-aware location
  labeling and is the natural starting point for an entry-block bbox
  audit.
- **This should start as a highlight/presentation improvement using
  existing metadata only, where such metadata already exists** (e.g. any
  rule that already populates `body_bbox`/`caption_bbox`/multiple `bbox`-like
  keys that just aren't being unioned correctly today) — that subset is
  presentation-only and low-risk.
- **If current metadata lacks a table/row/column bounding box for a given
  rule, that rule's improvement is detector work** (adding a new detail
  key such as `table_bbox`, populated from geometry the detector likely
  already computes internally), not a presentation change, and must be
  scoped and reviewed separately with its own golden-output comparison —
  do not conflate "expose more of what's already computed" with "compute
  new geometry" when scoping the first implementation PR.
- Do not change detection thresholds as part of any highlight cleanup —
  this work is about what region gets drawn, never about which findings
  fire.

---

## Recommended implementation sequence

1. **Documentation-only inventory** of current sort/confidence/priority/
   highlight behavior, if a future review finds this plan insufficiently
   detailed for a specific rule family (e.g. a per-rule highlight-metadata
   audit for the table/list rules named in section 5).
2. **Implement page-order sorting** as a presentation-only, additive sort
   option (section 1).
3. **Hide "priority" mislabeling** from student-facing problem cards —
   rename the severity/triage filter labels on `job.html` and `rules.html`,
   and reconsider the visual/semantic relationship between the severity
   badge and the confidence badge (section 2).
4. **Normalize displayed confidence** to High / Medium / Low by collapsing
   the "Needs review" and "Mixed confidence: ..." label branches in
   `_confidence_label()` (section 3).
5. **Improve table/list/figure highlight bounding boxes** using existing
   metadata only, rule-by-rule, starting with whichever rules already
   populate multiple bbox-like keys that aren't yet unioned or drawn
   correctly (section 5) — flag any rule that needs new detector metadata
   as separate, later work.
6. **Implement the P014 presentation-split prototype** (recommended by
   [ester_broad_rule_atomic_mapping.md](ester_broad_rule_atomic_mapping.md))
   only after the report UI labels and sorting behavior above are stable —
   splitting a rule's presentation while the surrounding card chrome
   (labels, sort, highlight) is still being reworked would make it harder
   to isolate regressions.
7. **Only then** proceed to the remaining broad presentation splits
   (P015/P017/P018/P019/P020/P024/P025/P027) per the atomic mapping.

---

## Safety guardrails

- Do not change detector logic.
- Do not change thresholds.
- Do not change `src/njit_auditor/rules/`.
- Do not change report JSON schema unless separately planned and reviewed.
- Preserve PR #407 warning-precision fixes (P011 grouping, P024/P040 LoF
  presentation, P025 DC-wrapper notice framing, P027 bold-heading gate,
  P037 dynamic Roman-numeral computation, P044 Abstract continuation-line
  handling).
- Preserve PR #408 confidence sorting while adding page-order sorting — the
  new mode is additive, following the exact `SORT_MODE_*` /
  `VALID_SORT_MODES` / `normalize_sort_mode()` pattern already in place.
- Do not remove internal metadata (e.g. the catalog's `priority` field) if
  tests or developer docs still use it — hide it from student view only
  where it is actually shown, which this inspection found to be the
  mislabeled severity filters, not the catalog field itself.
- Keep source and templates cleanly separated from docs-only planning —
  this document and any of its follow-on planning docs must not edit
  `src/`, `templates/`, or `tests/`.
- Do not commit private student documents, generated reports, or LFS
  pointer artifacts.

---

## Recommended next implementation PR

**Add page-order sorting as an additional report sort option.**

Why this should be the next implementation PR (not a documentation PR):

- It directly addresses Ester's review-flow request (review problems in
  document order, not scattered by confidence or arbitrary default order).
- It is very likely **presentation-only** — `sort_grouped_problems()`
  already operates purely on already-built `GroupedProblemView` dicts, and
  every grouped problem already carries page information needed to compute
  "earliest affected page."
- It follows an **existing, proven pattern** (`SORT_MODE_CONFIDENCE_DESC`/
  `_ASC` from PR #408) closely enough that the implementation risk is lower
  than any of the other four items, all of which touch label/badge display
  logic or (for highlights) potentially detector metadata.
- It can be tested for **stable sorting behavior** directly — a test can
  assert that a page-order-sorted card list is ordered by minimum page
  number, ties preserve original order, and pageless cards sort last,
  without needing new fixtures beyond what confidence-sort tests already
  use.
- It does **not** require any detector changes, unlike part of item 5
  (highlight quality), which this plan has already flagged as
  metadata-dependent per rule.

**This document does not implement it.** The next PR should implement only
this one item, with its own tests proving `rule_id`, `issue_type`, grouping,
anchors, and problem numbers are unaffected by the new sort mode — mirroring
the same invariants already required for every wording-slice PR in this
program.
