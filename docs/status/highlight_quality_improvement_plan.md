# Highlight Quality Improvement Plan

> **Purpose:** Plan highlight-quality improvements for the student-facing
> report before implementation. This addresses the user-observed problem:
> a table-related `highlighted-page.pdf` highlighted only part of the
> table text/cells instead of the full table region, so the visual cue was
> confusing rather than clear. (No screenshot or generated highlighted PDF
> is included in this repo — the observation is described in text only.)
>
> This plan is **documentation-only**. It does not implement any highlight
> change.
>
> **Recorded:** 2026-07-03 (post–PR #427 merge; main @ `91fdb7b0a1c898a4f2b376826c2a70d9318ed3d2`)
>
> **Related:** [student_facing_presentation_cleanup_plan.md](student_facing_presentation_cleanup_plan.md) ·
> [ester_broad_rule_atomic_mapping.md](ester_broad_rule_atomic_mapping.md) ·
> [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md)

---

## Purpose

- Highlights exist so a student can quickly see the exact region a warning
  refers to, without re-reading the whole page.
- For **table/list/figure warnings**, a highlight that covers only one
  cell, one token, or one row when the warning is actually about a whole
  table, column, or list entry reads as arbitrary and undermines trust in
  the tool — the student can't tell whether the highlighted spot is the
  *only* problem or just one visible symptom of a larger one.
- The goal here is to **improve highlight quality while preserving
  detector behavior** — the same findings should fire, with the same
  `rule_id`/`issue_type`/grouping/confidence; only the *drawn region* (and,
  where unavoidable, a small amount of already-computed geometry exposed
  into `details`) should change.
- Ester's style emphasizes direct, actionable feedback — a highlight that
  matches the warning's actual scope (word vs. line vs. entry vs. row vs.
  column vs. table vs. figure/caption) is part of making a warning directly
  actionable, the same way Slices 1–6 made wording direct and binary.

---

## Current highlight behavior

**Verified by reading (not editing) `src/njit_auditor/highlight_targeting.py`
and `src/njit_auditor/pdf_highlight.py`.**

- **Where highlight selection happens:** `highlight_targeting.py`'s
  `resolve_primary_highlight_bbox()` is the single entry point used by
  `report_view.py` for both individual and grouped findings. It calls
  `parse_highlight_bboxes_from_details()`, which:
  1. Reads `details["bbox"]` (falling back to `details["rect"]`) as the
     primary box.
  2. Additionally reads `body_bbox` and `caption_bbox` if present (used
     today only by P035 figure/table placement checks) and unions them in.
  3. For a **fixed, explicit list of (rule_id, issue_type) pairs**
     (`_TOKEN_HIGHLIGHT_RULES` — P020's title-case check, one P017
     sentence-case check, P024's LoF sentence-case check, and P027's
     Level 3–5 sentence/punctuation checks), it **shrinks** the box down to
     just the flagged word, using `word_bbox_in_line()` (exact span-based)
     or `estimate_word_bbox_in_line_bbox()` (a character-width estimate
     when only a line-level box and a text preview are available).
  4. If more than one box remains after this, `resolve_primary_highlight_bbox()`
     unions them via `_union_boxes()` (min of all `x0`/`y0`, max of all
     `x1`/`y1`).
- **The module's own stated design goal** (its docstring): *"Resolve the
  smallest reliable PDF highlight boxes for student-facing findings."*
  This governs the word-shrinking behavior for the specific rules listed
  above. **For every other rule, this module does not expand anything** —
  it only ever unions whatever boxes the detector already put in
  `details`. If a detector stores only one small box, the highlight is
  that one small box; this module has no logic to infer a larger region on
  its own.
- **How highlighted-page PDFs are generated:** `pdf_highlight.py`'s
  `build_highlighted_pdf()` / `build_highlighted_single_page_pdf()` simply
  draw translucent rectangle annotations (`add_rect_annot`) for whatever
  box(es) they're given, after `clip_box_to_page()` clips to the page and
  discards degenerate/too-thin boxes. **No expansion, padding, or region
  inference happens at draw time either** — by the time a box reaches this
  module, it is exactly what will be drawn.
- **How grouped findings choose a representative highlight:** grouping
  itself (in `report_view.py`) is unrelated to bbox selection — each
  individual finding resolves its own highlight bbox independently via the
  same `resolve_primary_highlight_bbox()` call; a grouped card's "has
  highlight" status and displayed highlight link come from its
  constituent findings, not a separately computed group-level region.
- **Whether table/row/column/figure/caption region metadata already
  exists:** partially. See the per-rule findings below — **P035 already
  computes and stores a genuine full-region union (`body_bbox`)**, proving
  the underlying mechanism works end-to-end. No other inspected rule
  currently stores a `table_bbox`, `row_bbox`, or `column_bbox` equivalent.

---

## Highlight target taxonomy

Expected behavior by warning scope, per the requirements below. This is
the target model; it is **not** current behavior for every rule (see the
candidate table).

### Word-level warnings
**Expected:** highlight only the affected word or phrase.
**Examples:** forbidden words in Abstract (P078), first-person pronouns
(P078), flagged capitalization words (P020, P027 Level 3–5).
**Current status:** already implemented — this is exactly what
`_TOKEN_HIGHLIGHT_RULES` + `word_bbox_in_line()` /
`estimate_word_bbox_in_line_bbox()` do today.

### Line-level warnings
**Expected:** highlight the full affected line, not only one token.
**Examples:** TOC/list entry wording (P024), heading line (P027 Level 1/2,
P014), caption line (P017 body-context checks).
**Current status:** already implemented for most of these — `entry.line.bbox`
(a full line) is the norm in `pdf_toc_list_formatting.py`,
`pdf_toc_alignment.py`, and `pdf_captions.py`.

### Entry-level warnings
**Expected:** highlight the full affected TOC/List entry, including
wrapped continuation lines when possible.
**Examples:** TOC entry capitalization, List of Figures punctuation, List
of Tables punctuation.
**Current status:** single-line entries already get a full-line box (see
above). **Wrapped continuation lines are not unioned in** for any rule
inspected — a wrapped entry's highlight is only as tall as whichever
single line the finding's `bbox` points to, not the whole wrapped block.

### Row-level warnings
**Expected:** highlight the full affected table row when possible.
**Examples:** table row/cell formatting findings, if row metadata exists.
**Current status:** no inspected rule currently distinguishes "row" from
"line" as a concept — a TOC/List "row" already is a `PdfTextLine`, so
line-level and row-level are effectively the same today for these rules.

### Column-level warnings
**Expected:** highlight the full affected column when possible.
**Examples:** list page-number column alignment (P046/P048-family),
table/figure number column alignment.
**Current status:** **not implemented.** `pdf_lot_lof_entry_number_alignment.py`
(the entry-number-column alignment detector) already collects the line
bbox of **every entry being compared** internally, but only stores the
**single worst-offending entry's line bbox** in `details["bbox"]` (see
`worst_bbox` in the candidate table below). The column's full vertical
extent across all compared entries is computed but discarded before
reaching `details`.

### Table-level warnings
**Expected:** highlight or outline the full table bounding box when the
warning concerns the table as a whole.
**Examples:** a table extending into the margin (P011, when the
overflowing text belongs to a table), table-level spacing/layout warnings.
**Current status:** **not implemented for P011.** `pdf_margins.py` selects
a single `worst_violation.line.bbox` (the single worst-offending line) the
same way the entry-alignment detector does — if a table's cells overflow
the margin across several rows, only one row's line is highlighted, not
the table's full extent. **This is the most likely explanation for the
exact behavior the user observed.**

### Figure/caption-level warnings
**Expected:** highlight the full figure, caption, or figure-caption region
depending on the warning's scope.
**Examples:** figure caption punctuation, figure description spacing,
figure object/layout warnings.
**Current status:** **already implemented, and the best model in the
codebase.** `pdf_figure_table_layout.py` (P035) computes `body_bbox` via
`_union_bbox()` — a genuine union of every text block in the figure/table's
body cluster — plus a separate `caption_bbox`, and
`highlight_targeting.py` already knows to union these two together for
P035's placement issue_types. This is proof that the "expose a union bbox
in details, let the existing presentation-layer union pick it up" pattern
already works end-to-end; it just hasn't been extended to other rule
families yet.

---

## Table/list/figure highlight requirements

- Table-level findings should prefer full table-region rectangles, not
  isolated words — **P035 already does this; P011 does not.**
- Row-level findings should prefer full row rectangles — for TOC/List
  content, a "row" is already a full `PdfTextLine`, so this requirement is
  effectively met wherever line-level highlighting already applies.
- Column-level findings should prefer full column rectangles — **not
  implemented anywhere inspected.**
- List-entry findings should cover the full affected entry block when
  possible, including wrapped continuation lines — **partially
  implemented** (single-line entries: yes; wrapped multi-line entries:
  no).
- Figure/caption findings should cover the full figure/caption region when
  possible — **already implemented for P035.**
- Text-span highlighting should remain for word-level issues — **already
  correct**, no change proposed.
- If the current detector only provides a token bbox, the UI must not
  pretend it has a full table bbox — `highlight_targeting.py` already
  respects this: it never invents geometry, it only unions what's
  explicitly present in `details`. This property should be preserved by
  any future change.
- Where full-region metadata is missing, this document identifies exactly
  what would be needed (see Metadata gaps below) rather than assuming
  presentation-layer code alone can produce it.

---

## Candidate rules for highlight improvement

| Rule / issue family | Current highlight scope | Desired highlight scope | Existing metadata available? | Can improve without detector change? | Risk | Notes |
|---|---|---|---|---|---|---|
| **P011** margin overflow | **Fixed** (`fix/p011-margin-visual-polish`) — `details["highlight_bboxes"]` now stores one tight box per *adjacent* group of violating lines (lines with nothing between them merge; separated lines stay separate), plus `details["margin_boundary_bbox"]`, a thin guide rectangle marking the exact required-margin boundary line for the affected side | Tight per-group regions, never a union spanning unrelated content between separated violations | Done | done | low | Previously "the union of every violating line's box" (PR #430) over-highlighted when violations were separated by clean lines (the user's Cases 1/2/5). `details["bbox"]` (the full-side union) is kept unchanged for backward compatibility with any consumer expecting one box (e.g. `has_visible_highlight`'s availability check); the precise multi-box + guide fields are what the highlighted-PDF drawing path (`_highlight_boxes_by_page` in `web_app.py`) actually renders, via a new P011-specific branch in `highlight_targeting.parse_highlight_bboxes_from_details()`. Mixed-side pages (e.g. top + right, the user's Case 4) already roll up to one problem card via the pre-existing `P011DisplayState`/`_apply_p011_combined_presentation` mechanism; that card's comment now includes a per-side "Side detail: ... margin (~X pt over, N line(s) affected)" breakdown instead of only a vague "flagged N separate margin-boundary warnings," and the highlighted PDF already draws separate boxes/guides per side because the drawing endpoint aggregates boxes across every matching finding on the page, not just one. **Limitation (unresolved, out of scope for this PR):** P011 only sees the PDF text layer (`page.text_blocks` → `PdfTextLine`) — it detects text inside table cells and figure captions, but has no notion of a table or figure as a distinct geometric object, so a genuine image/graphic (not text) extending into the margin is not detected at all. |
| **P017** figure/table captions and titles | Full caption line bbox (`caption.bbox`) | Already line-level; acceptable as-is | Yes | yes (already correct) | low | No change needed. |
| **P018** TOC/List umbrella (leaders, wrapped spacing, hierarchy) | Full entry line bbox (`entry.line.bbox`) via `_details_with_affected_entry_preview()` | Already line/entry-level for single-line entries; wrapped continuation lines not unioned in | Partial (only the anchor line is stored, not continuation lines) | probably (union already-available wrapped-line bboxes where the detector groups them) | medium | Wrapped-entry union would need a small addition inside `pdf_toc_alignment.py`/`pdf_toc_list_entry_spacing.py`, not new detection. |
| **P024** TOC capitalization / entry issues | Full entry line bbox (`entry.line.bbox`) | Already line-level; acceptable as-is | Yes | yes (already correct) | low | No change needed. |
| **P031/P049/P050** column header issues | **No bbox stored at all** (`pdf_lot_lof_column_headers.py`, `pdf_lot_lof_column_header_style_alignment.py`) — findings fall back to "open original page," not a highlight | Full header-row or column-label region | No — `line.bbox` is used for internal geometric comparisons but never written to `details` | no (needs a new `details["bbox"]` key added, using geometry the detector already computes) | medium | Bigger lift than P011: goes from **no highlight** to a highlight, not "small" to "full." |
| **P032/P036/P039** wrapped/list spacing and indentation | Gap-region bbox between two lines (`gap_bbox_between_boxes()` in `pdf_toc_list_entry_spacing.py`) | Already appropriately scoped to the specific gap being flagged | Yes | yes (already correct) | low | No change needed. |
| **P040/P053/P054** punctuation in lists | **Fixed** (`fix/list-entry-highlight-polish`) — `details["bbox"] = format_bbox_detail(entry.line.bbox)` now stored on every finding, matching the full offending entry line | Full entry line | Done | done | low | Previously flagged as "trivial: store `entry.line.bbox` instead of just its `y0`" — implemented exactly that, plus `page_type` on P040 so its location label reads "List of Figures" instead of the generic "list" fallback. **`affected_entry_preview` (full entry text, used by P018/P046) was deliberately not added** — `test_p040_findings_metadata_no_private_content` / `test_p053_finding_metadata_privacy_safe` explicitly assert no LoF/LoT/TOC entry text may appear in `details`, a stricter contract than P018/P046 (whose catalog "no entry text" claims are themselves already stale relative to their code). Location clarity for these three rules is achieved via `page_type`/`section_type` + `page_entry_index` only, not text reproduction. |
| **P046/P048** column alignment (entry-number / page-number columns) | Single worst-offending entry's line bbox (`worst_bbox` in `pdf_lot_lof_entry_number_alignment.py`) | Full column region spanning all compared entries (or at minimum, all *affected* entries, not just the worst one) | Partial — `entries_by_section`/`affected` already hold every compared entry's line bbox before the `max()` pick | no (requires unioning the already-collected bboxes instead of selecting one) | medium | Same shape of fix as P011 — expose already-computed geometry, no new detection. |
| **P055** wrong list entry (Figure in LoT / Table in LoF) | **No bbox stored at all** (`pdf_lot_lof_entry_type.py`) | Full entry line | Not confirmed during this inspection — needs a targeted look at how this detector accesses entry geometry | unknown | medium | Flagged for a closer look before scoping a fix; not confirmed to be as trivial as P040/P053/P054. |
| **P045/P047** Biographical Sketch list/entry spacing | **No bbox stored at all** (`pdf_biosketch_publication_layout.py`, `pdf_biosketch_bullet_spacing.py`) | Full affected entry or bullet block | No — line/block geometry is used internally for gap/threshold comparisons but never written to `details` | no (needs a new `details["bbox"]` key, e.g. a block union) | medium | Same "no highlight today" situation as P031/P049/P050. |
| **P068** Approval Page committee blocks | **No bbox stored at all** (`pdf_approval_page_committee_blocks.py`) | Full committee-entry block or whole Approval Page body region | Not confirmed — file has no `bbox` references at all, suggesting geometry may not even be tracked per-line here | unknown | medium | May need more than metadata exposure; scope after confirming what geometry, if any, this detector already has internally. |
| **P035** figure/table caption placement and centering | **Already full-region**: `body_bbox` (union of all text blocks in the body cluster) + `caption_bbox` | No change needed | Yes — this is the reference implementation | yes (already correct) | low | **Use this as the template/precedent for extending the pattern to P011 and P046/P048.** |

---

## Metadata gaps

None of the following keys exist in `_EXTRA_BBOX_KEYS`
(`highlight_targeting.py`) or in any inspected rule's `details` output
today, except where noted:

| Missing field | Needed for full-region highlight, or can it be safely inferred? |
|---|---|
| `table_bbox` | Needed as a new concept, but **can be safely inferred today** for P011-on-a-table and P046/P048 cases by unioning line bboxes the detector *already iterates internally* — no new geometric computation, just exposing more of what's already computed. Confirm case-by-case before implementing (a table region should union only the rows that are part of the same table, not unrelated body text). |
| `row_bbox` | Not currently distinct from a TOC/List "line" bbox — likely does not need a separate name; `bbox` already serves this role wherever line-level highlighting exists. |
| `column_bbox` | Needed as a new concept for P046/P048; **can be safely inferred** the same way as `table_bbox` above (union of the compared entries' existing line bboxes, restricted to the misaligned ones or all of them, to be decided during implementation). |
| `entry_bbox` / `wrapped_entry_bbox` | Needed for wrapped multi-line TOC/List entries; **can likely be inferred** by unioning the anchor line's bbox with its already-identified continuation line(s) — `pdf_toc_list_entry_spacing.py` already identifies wrapped-line relationships for its own gap calculations. |
| `figure_bbox` | Already effectively covered by P035's `body_bbox` naming; no new field needed, just extending the pattern to other rules if a figure-specific (non-table) case arises. |
| `caption_bbox` | **Already exists** and already works (P035). No gap. |
| `region_bbox` / `highlight_scope` | A generic named concept was considered by the presentation-cleanup plan's original phrasing, but this inspection found no evidence a generic field is needed — every gap above is addressable with a rule-specific union of geometry the detector already has, not a new generic taxonomy field. Recommend **not** introducing a generic `highlight_scope` field unless a future rule's scope genuinely can't be expressed as "union these already-known boxes." |

---

## Recommended implementation sequence

1. **Add tests documenting current highlight target behavior** for
   representative fixtures — pin today's word/line/entry/table/figure
   highlight sizes for P011, P017, P018, P024, P035, and the
   currently-no-highlight rules (P031/P040/P045/P046/P053/P054/P068), so
   any future change has a clear, reviewable before/after diff.
2. **Add presentation-layer support for a richer highlight_scope concept
   only if a future rule's need can't be expressed as a simple union** —
   this inspection found no such case yet (see Metadata gaps above), so
   this step may turn out to be unnecessary.
3. **Improve list-entry highlights first** (wrapped continuation lines for
   P018/P032/P036) since the anchor-line-to-continuation-line relationship
   is already computed internally for spacing checks — lowest-risk of the
   "needs a small `details` addition" group.
4. **Improve table-level highlights** (P011 when overflow spans a table,
   P046/P048 column regions) once step 1's baseline tests exist, following
   the P035 `_union_bbox()` pattern exactly. This directly addresses the
   user-observed complaint.
5. **Improve figure/caption highlights separately** — largely already
   done via P035; revisit only if a non-P035 figure-related rule is found
   to need it later.
6. **Add new detector metadata only where no bbox exists at all today**
   (P031/P049/P050 column headers, **P040/P053/P054 punctuation — done, see
   `fix/list-entry-highlight-polish`**, P045/P047 Biographical Sketch, P068
   Approval Page, and P055 pending confirmation) — in a later,
   separately-scoped PR per rule family, each with its own golden-output
   comparison, since these add a `details` key
   that didn't exist before rather than just re-exposing existing
   geometry.

---

## Recommended first implementation candidate

**No purely presentation-only candidate exists today** — every genuine
region-size improvement requires exposing already-computed geometry from
inside a `src/njit_auditor/rules/*.py` file (touching the `details` dict
construction), even though none of them require new detection logic or
threshold changes. Given that constraint:

**Recommended next PR: `test: capture current highlight target behavior`.**

This is the safe, correct next step because:
- It requires **zero source changes** — pure fixture/test additions.
- It establishes the golden-output baseline (current bbox sizes, per rule)
  that every subsequent highlight-region change in the sequence above will
  need for a before/after comparison.
- It directly de-risks the highest-value next step (P011's table-overflow
  case, matching the user's exact complaint) by making that future change
  reviewable against a pinned "here's what today's highlight looks like"
  reference, rather than eyeballing it.

The next-safest **implementation** candidate, once the baseline tests
exist, is a small PR replicating P035's exact `_union_bbox()` pattern for
P011 and P046/P048's `worst_bbox` selection — this is the closest thing to
"presentation-only" available: no new geometry is computed, only a
`max()` (pick one) is changed to a union (combine all/affected), guided by
a proven, already-shipped precedent in the same codebase.

**Status update (2026-07-03):** the baseline tests landed as PR #429, and the
P011 union fix landed as PR #430. A **further** refinement is now open as PR
[#437](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/437),
pending review/merge: the PR #430 union sometimes over-highlighted when
violating lines were separated by unaffected content, so #437 groups only
*adjacent* violating lines into tight boxes and adds a margin-boundary guide
line, while keeping the original union in `details["bbox"]` as a
backward-compatible fallback. P046/P048's `worst_bbox`→union follow-up
described above is **not** part of #437 and remains open future work.

---

## Safety guardrails

- Do not change detector logic while improving highlights — every proposed
  change above re-exposes geometry a detector already computes internally;
  none change what triggers a finding or its thresholds.
- Do not change thresholds.
- Do not change rule IDs or issue types.
- Do not change confidence or sorting behavior.
- Do not change report JSON schema unless separately planned — adding a
  `details` key is additive and should not require a schema version bump,
  but confirm against `report_view.py`'s serialization before any
  implementation PR.
- Do not commit screenshots, private PDFs, generated highlighted PDFs, or
  sample reports — this plan intentionally describes the observed problem
  in text only.
- Preserve PR #407 warning-precision fixes (P011 grouping, P024/P040 LoF
  presentation, P025 DC-wrapper notice framing, P027 bold-heading gate,
  P037 dynamic Roman-numeral computation, P044 Abstract continuation-line
  handling).
- Preserve PR #408 confidence sorting and PR #426 page-order sorting.
- Highlight changes must be tested with structural invariants: same
  finding count, same rule IDs, same issue types, same grouping, same
  confidence, only highlight target boxes or display layers changed.

---

## Non-goals

- This PR does not implement highlight changes.
- This PR does not change detectors.
- This PR does not change thresholds.
- This PR does not change source files.
- This PR does not change templates.
- This PR does not change tests.
- This PR does not change report schema.
- This PR does not implement P021/P026, broad presentation splits, P084,
  or TOC-leader WIP.
