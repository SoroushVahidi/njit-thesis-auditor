# PDF Highlight Debug Audit

**Date:** 2026-06-17
**Scope:** Debug and fix PDF highlighting so "Open highlighted PDF page" appears only when a
real, visible, correctly-located highlight can be drawn.
**Baseline:** main at d41f901 (PR #312), immediately following PR #320's three-tier
actionability model.
**Supersedes:** [`finding_actionability_and_highlight_audit.md`](finding_actionability_and_highlight_audit.md)'s
`highlight` / `page` / `explanation` three-tier model — the `page` tier (button label "Open PDF
page") is removed entirely by this work. See "Outcome" below.

---

## Phase 1 — Failure modes found

Failure modes were reproduced using synthetic `AuditFinding` fixtures injected directly into the
in-memory job store (the same technique used throughout `tests/test_finding_actionability.py` and
`tests/test_web_app.py`), plus direct calls to `pdf_highlight.build_highlighted_pdf` with
hand-built `boxes_by_page` dicts. Each numbered case below maps to the corresponding case in the
task brief.

### Case 1 — Highlight link appears but no visible highlight appears in the opened PDF

- **Affected rule/issue type:** P012 / `pdf_annotation_detected` (any rule with a `rect`/`bbox`
  detail), but reachable by any finding with a shape-valid bbox.
- **Example fixture:** `AuditFinding(rule_id="P012", page=2, details={"rect": "0.1,0.1,0.5,0.5"})`
  — a 0.4×0.4 point box, plausible if a detector ever emitted 0–1 normalized fractions instead of
  PDF points.
- **Route URL:** `/audits/{job_id}/pdf/highlighted?page=2&rule_id=P012`
- **Expected:** No highlight action shown (nothing meaningful would be visible).
- **Actual (before fix):** `report_view.py` computed `has_highlight = bbox is not None` — pure
  shape validity, via `is_drawable_bbox` (positive area, finite). A vanishingly thin or far
  off-page box still passed this check, so "Open highlighted PDF page" was shown. The PDF route
  then called `pdf_highlight.build_highlighted_pdf`, which called `page.add_rect_annot(...)`
  directly with the raw, unclipped box — PyMuPDF accepts off-page or sub-pixel rectangles without
  error, producing a technically-real annotation object that is imperceptible or invisible once
  the page is rendered.
- **Root cause:** No page-bounds/visibility check existed between "bbox is shape-valid" and
  "bbox would be visible once drawn on the actual page." Shape validity and visual visibility were
  conflated.

### Case 2 — Highlight appears on the wrong page

- **Affected rule/issue type:** Any rule; reachable when a finding's `page` is known but a request
  resolves to the wrong PDF page index.
- **Example fixture:** finding with `page=2`, requested via `_matching_findings_for_highlight` —
  page-number comparisons in `_coerce_page_number`/`_matching_findings_for_highlight` are 1-based
  throughout, and `build_highlighted_pdf` converts to 0-based (`page_index = page_number - 1`) in
  exactly one place. No off-by-one was found in current code, but no test previously asserted this
  boundary, so a future regression here would have gone unnoticed.
- **Route URL:** `/audits/{job_id}/pdf/highlighted?page=2&rule_id=...`
- **Expected:** Highlight drawn on page 2 (1-based, i.e. `doc[1]`).
- **Actual:** Correct in current code, but unverified by any test before this work.
- **Root cause:** Missing regression coverage for the 1-based/0-based boundary, not a live bug.
  Closed by `tests/test_pdf_highlight.py::test_build_highlighted_pdf_draws_valid_box` (asserts the
  annotation lands on `doc[1]` for `page_number=2`) and the new
  `test_highlight_action_consistent_across_main_category_rule_issue_type_pages`.

### Case 3 — Highlight appears in the wrong location

- **Affected rule/issue type:** Any rule with a bbox that is on-page but only partially so.
- **Example fixture:** `(500.0, 700.0, 700.0, 850.0)` on a 612×792pt page — half the box is past
  the page's right/bottom edge.
- **Expected:** A clipped, accurate rectangle covering only the real on-page problem area, or no
  highlight at all if nothing meaningful survives clipping.
- **Actual (before fix):** The full unclipped box, including the off-page portion, was passed to
  `add_rect_annot`. PyMuPDF silently accepts coordinates beyond the page's `MediaBox`; depending on
  viewer, the annotation can render at an unexpected position or simply be cut off without warning
  the caller.
- **Root cause:** No clipping step existed. Fixed by `clip_box_to_page()` (new), used by both
  `has_visible_highlight()` (eligibility) and `build_highlighted_pdf()` (drawing) so the same
  clipped rectangle is the one both checked and drawn.

### Case 4 — Highlight box too small, too large, inverted, shifted, or off-page

- **Example fixtures (now regression-tested in `test_pdf_highlight.py` and the parametrized
  `test_annotation_invalid_bbox_falls_back` in `test_finding_actionability.py`):**
  - Inverted: `(300.0, 260.0, 100.0, 200.0)`
  - Zero-area / degenerate point: `(100.0, 200.0, 100.0, 200.0)`
  - NaN: `(nan, nan, nan, nan)`
  - Infinite: `(inf, inf, inf, inf)`
  - Entirely off-page: `(-1000.0, -1000.0, -500.0, -500.0)` / `(2000.0, 2000.0, 2100.0, 2100.0)`
  - Too tiny (sub-2pt after clipping): `(100.0, 200.0, 100.5, 200.5)`
- **Actual (before fix):** Inverted/NaN/zero-area were already rejected by `is_drawable_bbox`
  (pre-existing). Off-page and too-tiny boxes were **not** rejected — `is_drawable_bbox` is
  shape-only and has no notion of a specific page's bounds or a minimum visible size.
- **Root cause:** Same gap as Case 1/3 — shape validity (`is_drawable_bbox`) was being used as a
  proxy for visibility, but it cannot detect off-page placement or a sub-visible size. Fixed by
  `clip_box_to_page()` plus the new `MIN_HIGHLIGHT_DIMENSION_PT = 2.0` threshold.

### Case 5 — Highlight route returns original PDF without making it clear that highlighting failed

- **Route URL:** `/audits/{job_id}/pdf/highlighted?page=1&rule_id=P011` (P011 findings carry no
  bbox at all).
- **Expected (per task brief):** This is an intentional, accepted fallback for **direct/manual**
  URL access — the route must never break, and the UI must simply never generate such a link in
  the first place.
- **Actual:** Confirmed this was already the route's behavior (`if not boxes_by_page: return
  plain_response`), and is correct *as a fallback*. The real defect was upstream: the UI **did**
  generate highlight-looking links for some no-bbox findings (Case 1/8), so this safe fallback was
  being hit far more often than intended, silently masking the eligibility bug rather than only
  guarding against truly-direct/manual URL tampering.
- **Root cause:** Not a route bug — a symptom of the eligibility bug (Case 1/8). Now that
  eligibility is strict, this fallback path is exercised only for genuinely out-of-policy/manual
  requests, and a `_logger.warning(...)` call was added (this session) for the one remaining case
  where the UI's own `boxes_by_page` was non-empty but drawing still produced zero visible
  annotations, so any future eligibility/draw mismatch is observable in logs rather than silent.

### Case 6 — Highlight route returns 200 but generated PDF has no annotations/rectangles

- **Example fixture:** all matched findings' bboxes resolve to out-of-range pages, e.g.
  `boxes_by_page = {99: [(100.0, 200.0, 300.0, 260.0)]}` against a 5-page PDF.
- **Route URL:** `/audits/{job_id}/pdf/highlighted?page=99&rule_id=P012`
- **Expected:** Either a clear fallback to the plain PDF, or a non-200 signal — never a "highlighted"
  response that is silently a no-op copy.
- **Actual (before fix):** `pdf_highlight.build_highlighted_pdf` called `doc.save(output_pdf)`
  **unconditionally**, regardless of whether any annotation was actually added in the page loop
  above it. Once the cache file existed on disk, the route's `if not cache_path.exists(): return
  plain_response` check could never trigger on a second request — but on the *first* request it
  would also pass straight through and serve a "highlighted" PDF that was a byte-for-byte (or
  near-identical) copy of the source, no different from the plain PDF, with no signal to the
  caller that nothing was drawn.
- **Root cause:** `build_highlighted_pdf` did not track whether anything was drawn before saving.
  Fixed: it now only calls `doc.save(output_pdf)` when `drawn > 0`, and returns a
  `HighlightDrawResult(drawn_count, skipped_count, pages_highlighted)` so callers can check
  `result.has_highlight` explicitly. The route now checks `cache_path.exists()` after the call (the
  only way it can exist is if something was drawn) and falls back to the plain PDF otherwise.

### Case 7 — Highlight route returns 500 for malformed bbox/page

- **Investigated:** Searched for any path where a raw bbox reaches `fitz.Rect(...)` /
  `add_rect_annot(...)` without first passing `is_drawable_bbox`. Found none in the current
  `web_app.py` → `pdf_highlight.py` path — `_coerce_bbox` (web_app.py) and
  `_parse_bbox_from_details` (report_view.py) both already filtered via `is_drawable_bbox` before
  this session's changes, and the route is wrapped in a catch-all `try/except Exception` that logs
  and falls back to the plain PDF.
- **Conclusion:** Not reproducible against current `main` for the finding-bbox path. A regression
  test (`test_highlighted_pdf_endpoint_degenerate_bbox_falls_back_without_500`) already existed
  pre-session documenting that this *used to* be possible via PyMuPDF's own (unvalidated)
  annotation-rect reader feeding a degenerate `rect` string into finding details — i.e. a
  real-world uploaded PDF with a broken annotation, not a bug in this code. The fix (validate
  before constructing `fitz.Rect`) was already in place; this session's `clip_box_to_page` and
  `has_visible_highlight` additions close the remaining gap (off-page/tiny boxes) using the same
  "validate, then build" discipline. Extended the parametrized invalid-bbox test to cover all 7
  required degenerate shapes end-to-end (zero area, inverted, NaN, infinity, outside page bounds,
  too tiny, malformed string) plus the wrong-coordinate-space case, asserting `!= 500` for each.

### Case 8 — UI claims highlight exists when bbox is invalid or untrusted

- **Affected rule/issue type:** Every rule reachable via the report-view pipeline.
- **Example fixture:** `AuditFinding(rule_id="P026", page=3, details={"issue_type":
  "possible_body_font_family_issue"})` — known page, **no bbox at all**.
- **Route/page URL:** `/audits/{job_id}`
- **Expected:** No PDF action of any kind. Explanation only.
- **Actual (before fix):** `report_view.py`'s `get_action_kind(has_bbox=False, page=3)` returned
  `"page"`, rendering button label **"Open PDF page"** linking to
  `/audits/{job_id}/pdf#page=3` — a real, clickable PDF action, in direct violation of "if the
  system cannot produce a correct visible highlight for a finding, the UI must show NO PDF action
  at all."
  - Separately, `_problem_group_examples()` (category/rule/issue-type drill-down pages) recomputed
    its own bbox-presence check from `job.findings` dicts rather than trusting the canonical
    `FindingView.has_highlight`/`action_kind` already computed once in `report_view.py`, risking
    divergence between the main results page and drill-down pages for the same finding.
- **Root cause:** (a) the three-tier `highlight` / `page` / `explanation` action model from PR
  #320 treated "page number known" as sufficient justification for a PDF button, when the task's
  policy requires a *real, visible highlight* specifically; (b) drill-down pages had their own,
  separately-computed eligibility logic instead of trusting one shared, already-computed source of
  truth.

---

## Phase 2 — Pipeline trace answers

Traced: detector bbox creation → `AuditFinding.details["rect"]`/`["bbox"]` (string) →
`report_outputs.audit_findings_to_json_dict` (JSON serialization, no transformation) →
`report_view._parse_bbox_from_details` (string → `tuple[float, float, float, float]`, shape
validation) → `report_view._finding_view_from_item` (eligibility: `has_visible_highlight`) →
`report_view_to_dict` → `JobState.findings` (serialized dicts in `web_app._run_audit_task`) →
Jinja templates (`job.html`, `problem_group.html`) → `pdf_finding_url()` (URL generation) →
`GET /audits/{job_id}/pdf/highlighted` → `_matching_findings_for_highlight` /
`_highlight_boxes_by_page` → `pdf_highlight.build_highlighted_pdf` (clip + draw) → `FileResponse`.

- **What bbox formats are supported?** A comma-separated `"x0,y0,x1,y1"` string under either the
  `rect` or `bbox` detail key (checked in that order, first non-empty wins), or four separate
  `x0`/`y0`/`x1`/`y1` string detail keys as a fallback. Exactly one bbox per `AuditFinding`.
- **Are bbox coordinates in PDF points?** Yes, by convention — they come from PyMuPDF's own
  `annot.rect` (already in PDF point space) for P012, and no unit conversion is performed anywhere
  in the pipeline. There is no coordinate-space tag carried alongside the bbox; a future detector
  that emitted, say, pixel or normalized coordinates would silently violate this assumption. The
  `MIN_HIGHLIGHT_DIMENSION_PT` threshold added this session is partly a defense against exactly
  that scenario (0–1 normalized fractions collapse to sub-2pt boxes once placed on a real page and
  are now rejected as "not really visible," rather than silently drawn as a near-invisible sliver).
- **Are page numbers 1-based or 0-based at each stage?** 1-based everywhere except inside
  `pdf_highlight.build_highlighted_pdf`'s internal loop, which is the single place that converts
  to PyMuPDF's 0-based `doc[page_index]` indexing (`page_index = page_number - 1`). No other module
  does this conversion.
- **Are rectangles normalized?** No — `is_drawable_bbox` rejects inverted rectangles (`x1 <= x0` or
  `y1 <= y0`) outright rather than swapping coordinates. This is a deliberate choice: silently
  "fixing" an inverted box risks masking a genuine wrong-coordinate-space bug as if it were a
  legitimate (if inverted) rectangle.
- **Are rectangles clipped to page bounds?** Yes, as of this session, via `clip_box_to_page()` —
  used identically by both the eligibility check (`has_visible_highlight`) and the draw step
  (`build_highlighted_pdf`), so a box is never "eligible" without also being exactly what gets
  drawn.
- **Are degenerate/NaN/inf/out-of-page bboxes rejected?** Yes. `is_drawable_bbox` rejects
  non-finite or non-positive-area shapes; `clip_box_to_page` additionally rejects boxes with no
  page overlap or with an overlap thinner than 2pt in either dimension (catches off-page and
  effectively-invisible/wrong-coordinate-space boxes).
- **Are multi-page/multi-box findings handled?** A single finding carries one bbox, but the
  highlighted-PDF route aggregates bboxes across *all* findings matching the requested
  page/rule_id/issue_type/finding_index filter into one `boxes_by_page` dict, so multiple findings
  sharing a page each contribute their own box to one response (capped at
  `MAX_HIGHLIGHT_BOXES_PER_PAGE = 25` per page), and findings on different pages are drawn onto
  their respective pages in the same document. Confirmed via
  `test_build_highlighted_pdf_multi_box_finding_draws_all_valid_boxes` (unit) and the new
  `test_highlighted_pdf_endpoint_draws_all_valid_boxes_for_multiple_matches` (route-level, includes
  one degenerate box that must be skipped without failing the other two).
- **Is a generated PDF guaranteed to contain at least one visible annotation if the UI says
  highlight exists?** Structurally yes: the same `has_visible_highlight()` predicate (page valid,
  bbox drawable, survives `clip_box_to_page`) governs both the UI's `has_highlight` field and what
  `build_highlighted_pdf` will actually draw, and `build_highlighted_pdf` only writes its output
  file when `drawn_count > 0`. There is no runtime cross-check forcing the two call sites to agree
  on every input in real time (e.g. if `pdf_page_sizes` is unavailable when the UI renders but
  available when the route later runs, or vice versa), so the route additionally logs a warning
  (added this session) on the one residual case where its own `boxes_by_page` was non-empty but
  drawing still produced nothing, so any future divergence is visible in logs rather than silent.

---

## Outcome

- The `page` action-kind tier and "Open PDF page" button are removed system-wide. Every finding is
  now either `highlight` (real, visible, page-bounds-checked highlight) or `explanation` (no PDF
  action at all, detailed explanation + honest reason text only).
- `pdf_highlight.py` gained `clip_box_to_page`, `has_visible_highlight`, `get_pdf_page_sizes`, and
  `HighlightDrawResult`; `build_highlighted_pdf` now clips/validates every box and only writes
  output when something was actually drawn.
- `report_view.py`'s `has_highlight` now uses `has_visible_highlight()` (page-bounds-aware) instead
  of bare bbox-shape validity, and accepts `pdf_page_sizes` so eligibility reflects the real PDF's
  geometry whenever it's available.
- Category/rule/issue-type drill-down pages now trust the same canonical per-finding fields
  (`has_highlight`, `action_kind`, `action_label`, `no_highlight_reason`, `detailed_explanation`,
  `issue_type_label`, `issue_type_explanation`) computed once by `report_view.py`, rather than
  recomputing their own eligibility.
- See [`finding_actionability_and_highlight_audit.md`](finding_actionability_and_highlight_audit.md)
  for the original (now superseded) three-tier model this work replaced.
