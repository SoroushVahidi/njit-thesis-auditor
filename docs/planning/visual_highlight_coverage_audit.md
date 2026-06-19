# Visual/Layout Highlight Coverage Audit

**Date:** 2026-06-19
**Branch:** `fix/expand-visual-highlight-coverage` (from `main` @ `c73b697`)
**Goal:** expand real highlighted-PDF support beyond P012 for visual/layout rules
**only** where reliable page/bbox geometry already exists — never invent geometry,
never fake highlights, never show a PDF action button unless
`has_visible_highlight()` confirms a real, visible, drawable box.

## 1. Why this is mostly a detector-level change, not a plumbing change

The entire bbox → highlight pipeline is already generic and rule-agnostic:

- `report_view._parse_bbox_from_details()` reads `details["bbox"]` (or legacy
  `details["rect"]`, or separate `x0/y0/x1/y1` keys) from **any** rule's finding
  payload — it has no rule-specific logic.
- `report_view._finding_view_from_item()` calls `has_visible_highlight(bbox, page=...,
  page_count=..., page_size=...)` and `sub_page_location_label(bbox, page_size)`
  generically for every finding, regardless of `rule_id`.
- `web_app.py`'s `/audits/{job_id}/pdf/highlighted` route, `_matching_findings_for_highlight`,
  and `_highlight_boxes_by_page` already consume `FindingView.bbox` generically.
- `pdf_highlight.build_highlighted_pdf` draws on a copy of the PDF and only writes
  output when at least one box was actually drawn (`HighlightDrawResult.has_highlight`).

So the only gap is inside individual detector modules: several already compute
real per-line/per-span geometry internally (via `PdfTextLine.bbox` / `PdfTextSpan.bbox`)
but discard it before constructing `AuditFinding.details`, storing only aggregate
text/counts. This audit identifies exactly which findings can safely retain that
geometry, and which cannot.

A new shared helper, `pdf_models.format_bbox_detail()`, serializes a `BBox` or raw
`(x0, y0, x1, y1)` tuple into the `"x0,y0,x1,y1"` string shape `_parse_bbox_from_details`
already expects — so every rule below uses one common, tested serialization instead of
each re-inventing `f"{x:.1f}"` formatting.

## 2. Privacy safety of adding `details["bbox"]`

Verified via grep: neither `line_preview` (existing raw-text detail key already present
on several rules) nor `FindingView.bbox` (raw coordinates) are ever rendered in any
Jinja template — `details` is filtered down to named `FindingView` fields before
reaching templates, and `bbox` is consumed only by `has_visible_highlight` /
`sub_page_location_label` / the highlighted-PDF route, never printed as text. Adding a
`details["bbox"]` key to a rule's payload carries no risk of new text/coordinate leakage,
as long as no new *rendered* field is introduced alongside it. No new rendered field is
introduced by this change.

## 3. Classification scheme

1. **Already highlightable** — works today (P012).
2. **Geometry exists but not propagated** — the detector touches a `PdfTextLine`/
   `PdfTextSpan` (which has `.bbox`) at the point a finding is built, but the bbox is
   discarded before reaching `details`. Safe to propagate.
3. **Page known but no bbox** — only a page number is available; no specific region
   the detector can point to.
4. **No reliable geometry** — neither page nor box is well-defined for this finding.
5. **Should remain explanation-only** — geometry might technically exist somewhere
   but is not a faithful single defect location (e.g. a page-wide statistical
   aggregate across many line-pairs) — propagating it would be misleading, not helpful.

## 4. Per-rule findings

| Rule | Issue type(s) | Page known? | Geometry computed? | Stored in details (before)? | Classification | Action taken |
|---|---|---|---|---|---|---|
| P012 | `pdf_annotation_detected` | Yes | Yes (`annot.rect`) | Yes (`details["rect"]`) | Already highlightable | None (reference implementation) |
| P011 | `margin_boundary_violation` | Yes | Yes — `LineViolation.line.bbox` per (page, side) group | No — only `worst_overflow_pt`/`affected_line_count` | (2) Geometry exists, not propagated | Propagate worst-violation line's bbox |
| P026 | `possible_body_font_size_issue`, `possible_body_font_family_issue` | Yes | Yes — `PdfTextSpan.bbox` for every violating span | No — only `observed_summary`/counts | (2) Geometry exists, not propagated | Propagate first violating span's bbox (never `.text`) |
| P027 | `level2_title_case_issue`, `level{3,4,5}_sentence_case_issue`, `level{4,5}_sentence_case_or_punctuation_issue`, `level1_not_all_caps` | Yes | Yes — exact 1:1 `PdfTextLine.bbox` per finding | No | (2) Geometry exists, not propagated | Propagate the line's bbox |
| P063 | `single_appendix_uses_letter_label`, `multiple_appendix_missing_letter`, `appendix_letter_sequence_repeat`, `appendix_letter_sequence_gap` | Yes | Yes — exact 1:1 heading-line bbox, discarded by `_collect_appendix_headings` returning `(page, text)` tuples | No | (2) Geometry exists, not propagated | Extend collected tuple to carry bbox |
| P020 | `possible_title_capitalization_issue` (source="heading") | Yes | Yes — `PdfTextLine.bbox` directly in scope in the bold/font-size-fallback loop | No — `TitleLikeLine` has no bbox field | (2) Geometry exists, not propagated | Add `bbox` field to `TitleLikeLine`, populate from `line.bbox` |
| P020 | `possible_title_capitalization_issue` (source="caption") | Yes | Yes — `detect_caption_lines()` iterates `PdfTextLine` (has `.bbox`) but `CaptionLine` has no bbox field | No | (2) Geometry exists, not propagated | Add `bbox` field to `CaptionLine`, thread into `TitleLikeLine.bbox` |
| P013 | `page_number_candidate` | Yes | Yes — `PageNumberCandidate` built from `line.bbox` during classification, then discarded | No — dataclass has no bbox field | (2) Geometry exists, not propagated | Add `bbox` field to shared `PageNumberCandidate`; use `primary.bbox` |
| P013 | `p013_document_overview` | No (doc-level) | N/A — aggregate across all pages | N/A | (3) Page known but no bbox (not even page known here) | Stays explanation-only (unchanged; this is a summary card, not a per-location finding) |
| P022 | `visible_page_number_on_no_number_page` | Yes | Yes — `line.bbox` used transiently in `_candidates_on_page` for top/bottom classification, then discarded | No — candidate dict only has `text`/`location` | (2) Geometry exists, not propagated | Add `"bbox"` key to the candidate dict; use `first["bbox"]` |
| P028 | `arabic_number_on_frontmatter_page`, `uppercase_roman_on_frontmatter_page`, `roman_number_on_body_page` | Yes | Yes — exact 1:1, one real `PageNumberCandidate` per finding (`for candidate in candidates:`) | No (candidate had no bbox field) | (2) Geometry exists, not propagated | Free once `PageNumberCandidate.bbox` exists — use `candidate.bbox` |
| P019 | `inconsistent_position` | Yes | Yes — `mismatched_candidates` is a real list of `PageNumberCandidate` objects for that page | No | (2) Geometry exists, not propagated | Use `mismatched_candidates[0].bbox` |
| P019 | `missing_page_number` | Yes | No — by definition, no candidate exists on this page (that's the finding) | N/A | (3) Page known but no bbox | Stays explanation-only — there is no token to box |
| P019 | `multiple_page_numbers` | Yes | Candidates exist, but 2+ on the same page with no way to pick "the" one without contradicting the finding's own message ("verify which token is the actual page number") | No | (5) Should remain explanation-only | Stays explanation-only — boxing one would mislead about which is correct |
| P019 | `mixed_numbering_style` (per-page and document-wide variants) | Sometimes | Multiple candidates with different styles on the page; no single representative | No | (5) Should remain explanation-only | Stays explanation-only |
| P019 | `sequence_gap` (arabic/roman) | Yes | The specific candidate object for the gap page is not retained past `_find_sequence_gap` (only `(page, value)` tuples survive) | No | (2) Geometry exists upstream, but the call site as written has already discarded the candidate object | Documented as future work — see §6; not implemented in this change to avoid widening blast radius beyond the stated priority list |
| P023 | `body_spacing_pattern` (page-level statistical finding) | Yes | No single discrete location — the finding is a page-wide median line-spacing ratio across potentially dozens of line pairs | N/A | (5) Should remain explanation-only | Stays explanation-only — boxing one line-pair would fabricate a location for a pattern that is not localized |
| P038 | `heading_phrase_not_exact` | Yes | Yes — exact 1:1 `line.bbox` in scope at the point the finding is built | No | (2) Geometry exists, not propagated | Propagate the line's bbox |
| P038 | `required_heading_missing` | No (no page assigned at all) | No — the heading is absent entirely, there is nothing to box | N/A | (3) Page known but no bbox (not even page known) | Stays explanation-only |

## 5. What was implemented

Bbox propagation was added for, in priority order:

1. **P011** margins — worst-overflow line's bbox per (page, side) group.
2. **P026** fonts — first violating span's bbox (never the span's `.text`).
3. **P027** headings — exact line bbox, all issue types.
4. **P020** title-case — exact line/caption bbox, both detection sources.
5. **P063** appendix labels — exact heading-line bbox, all issue types.
6. **Page-number rules**, limited to findings with one unambiguous, exact candidate:
   - P013 `page_number_candidate` (the page's `primary` candidate).
   - P022 `visible_page_number_on_no_number_page` (the page's first candidate).
   - P028 all issue types (one candidate per finding by construction).
   - P019 `inconsistent_position` only (the first mismatched candidate).

P023 remains entirely explanation-only, per explicit instruction not to fabricate
blank-line/spacing highlights when geometry is page-wide rather than localized.

## 6. Explicitly out of scope (left as explanation-only, with rationale)

- **P019** `missing_page_number`, `multiple_page_numbers`, `mixed_numbering_style`,
  `sequence_gap` — see table above for per-issue-type rationale. `sequence_gap` in
  particular has geometry available *upstream* (in `detect_page_number_candidates`)
  but the call site that builds the finding has already reduced candidates to bare
  `(page, value)` tuples; recovering the candidate object would require a small
  refactor of `check_pdf_page_number_sequence`. Left as future work since it is not
  one of the rules named in the priority list and the existing explanation-only
  behavior is already correct and honest.
- **P038** `required_heading_missing` — heading is absent; there is no page or region
  to box, by definition.
- **P023** — page-wide statistical aggregate; no single representative location.
- **P017** (figure/table captions) — not in the original priority list. Adding a
  `bbox` field to `CaptionLine` (needed for P020's caption-derived path) incidentally
  makes P017 propagation-eligible too, but P017's own finding construction was left
  unchanged in this change to keep the diff scoped to the rules explicitly named.
  Noted here as a natural, low-risk follow-up.

## 7. Risk notes

- All bbox values added to `details` are sourced from geometry the detector already
  computed during normal detection (no new heuristics, no new thresholds, no change
  to which findings fire or their severity/confidence).
- `has_visible_highlight()` still gates every "highlighted PDF" action — a finding
  with an invalid, off-page, or too-small bbox after clipping will not show a button,
  exactly as before. Adding `details["bbox"]` can only ever *add* a highlight action
  to a finding that previously had none; it cannot remove or weaken an existing one.
- No rule ID, threshold, canonical rule JSON, or raw guideline file was touched.
- No raw bbox coordinates, dissertation body text, or LaTeX source is newly exposed in
  any rendered template — only `has_highlight`/`location_label`/the highlight action
  button derive from the new `bbox` values, none of which print the coordinates or
  underlying text.

## 8. Bug found and fixed while testing: stale "no highlight" sentence

While writing web-level regression tests (category 1, P011), discovered that
`report_view._margin_detailed_explanation()` and `_font_detailed_explanation()`
**unconditionally** appended the literal sentence "No exact highlight is available
for this finding." to `FindingView.detailed_explanation` — regardless of the
finding's actual `has_highlight` value. Before this change, `bbox` was never present
for P011/P026, so `has_highlight` was always `False` and the sentence was always
true. Once P011/P026 started carrying real `bbox` values, the sentence became
**actively wrong** for any finding that now has a real highlight: the UI would show
both an "Open highlighted PDF page" button *and* a contradictory "No exact highlight
is available" sentence in the same card. This is exactly the kind of inconsistency
Phase 6 ("highlight button supplements, never replaces, the full explanation") is
meant to prevent.

Fix: both functions now take `has_highlight: bool` and only append the sentence when
`False`, matching the pattern already used for `FindingView.no_highlight_reason`. The
two call sites (`_apply_margin_presentation`, `_apply_font_presentation`) pass
`finding.has_highlight` through. No wording changed for any finding that still lacks
a highlight (verified by the full existing margin/font actionability test suites,
which assert the sentence's presence for no-bbox findings and continue to pass
unmodified). The generic per-issue-type explanation path used by P020/P027/P063 (and
the page-numbering family's `_page_number_detail_text`) was checked and has no
equivalent hardcoded sentence, so no fix was needed there.

## 9. Tests added (Phase 8)

New file `tests/test_visual_highlight_coverage.py` (15 tests, parametrized to more
individual cases), covering all ten required categories:

1. P011 margin propagation — real highlight, unchanged wording, no contradiction.
2. P026 font propagation — real highlight, no body-text/coordinate leak (parametrized
   over both `possible_body_font_family_issue` and `possible_body_font_size_issue`).
3. P020 / P027 / P063 propagation — real highlight, raw bbox string never present in
   rendered HTML (parametrized over the three rules).
4. No-geometry findings (`P019 missing_page_number`, `P038 required_heading_missing`)
   stay explanation-only — `has_highlight=False`, `action_kind="explanation"`, no
   `/pdf/highlighted` link rendered.
5. Invalid/degenerate bbox safety — zero-area, inverted, and NaN bbox strings in
   stored `details["bbox"]` all resolve to `has_highlight=False` with no crash, and a
   manually-constructed highlight request for the same job/rule/page falls back to
   the plain PDF (200, not 500).
6. P012 regression — existing highlight behavior unaffected when mixed in the same
   job as the newly-propagated rules.
7. Forbidden-action regression — "Open PDF page" and "Open first example page" never
   reappear on any rendered page for the newly-highlightable rules.
8. Actionability-wording regression — exact P028/P022 phrases from
   `test_page_number_actionability.py`'s pre-bbox baseline are unchanged once `bbox`
   is added to the same finding shapes.
9. Mobile/desktop parity — identical highlight-button counts and identical set of
   `/pdf/highlighted` links under mobile vs. desktop `User-Agent`/`Viewport-Width`
   headers.
10. No-500 route crawl — main, category, rule, issue-type, and highlighted-PDF routes
    for a job containing every newly-propagated rule (plus a no-geometry P023 control
    finding), asserting no route ever returns 500.

## 10. Final validation

- `ruff check src/ tests/test_visual_highlight_coverage.py` — all checks passed.
- `mypy src/` — Success: no issues found in 93 source files.
- `python -m pytest -q` — **1595 passed**, 1 warning (pre-existing, unrelated
  `zipfile` duplicate-name warning from `test_upload_handling.py`), 0 failed. Baseline
  before this change was 1580 passed; the 15 new tests in
  `tests/test_visual_highlight_coverage.py` account for the full increase, with zero
  regressions anywhere else in the suite.
