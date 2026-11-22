# Sub-Page Location Labels — Salvage/Rebase Audit

> **Historical note:** This document predates the final #9 cleanup snapshot (2026-07-05).
> UI references (for example "All individual findings" panel) describe the pre-cleanup layout.
> For the current report flow, see [current_project_state_and_next_steps.md](../status/current_project_state_and_next_steps.md).

**Date:** 2026-06-19
**Branch:** `fix/sub-page-location-labels-current-ui` (from `main` @ `47be2ab`, PR #325)
**Source PR reviewed:** #311, `feature/subpage-location-labels` (opened 2026-06-15, head `a65d480`)
**Outcome:** Fresh reimplementation, not a rebase. See [Decision](#3-decision) below.

## 1. Why this wasn't a mechanical rebase

PR #311 branched right after PR #310 landed, before four substantial UI/architecture
changes merged into `main`:

- **#318** — mobile/desktop parity work on the job results page.
- **#320** — finding actionability + category/rule/issue-type drill-down pages
  (`GroupedProblemView`, `_problem_group_examples`/`_problem_group_context` in
  `web_app.py`, the shared `problem_group.html` template).
- **#321** — the strict PDF highlight eligibility policy: a PDF action button may
  only appear when `has_visible_highlight()` confirms a real, drawable, on-page
  rectangle. This replaced all earlier "Open PDF" / "Open PDF page" / "Open first
  example page" links that pointed at a page with no guaranteed visible highlight.
- **#324** — page-number, margin, and font finding actionability: exact, page-number
  wording for P013/P019/P022/etc., margin-side wording for P011, and font wording for
  P026, all driven by `finding_explanations.py`.

PR #311 touches exactly the two files most reshaped by that stack
(`src/njit_auditor/report_view.py`, `src/njit_auditor/templates/job.html`), and its
`FindingView`/template assumptions predate `bbox`, `has_highlight`, `action_kind`, and
the highlight-gated link rendering entirely. A `git merge-tree` rebase would have
either dropped the new actionability machinery or required hand-resolving every
conflicting hunk — at which point it is simpler and safer to design the feature against
the current architecture directly.

## 2. What PR #311 actually did (read-only inspection)

Inspected via a disposable scratch branch (`inspect/pr-311-sub-page-location-labels`,
deleted after review; no commits were made on it).

- Added a `number` field to `CaptionLine` in `rules/pdf_captions.py`, threaded into
  `details["caption_number"]`.
- Added `_build_pdf_sublocation(rule_id, details)` to `report_view.py`: a large
  rule-specific dispatcher (covering P011, P013, P014, P017, P019, P020, P024, P026,
  P027, P029, P030, P031, P035, P037, P038, P074, P082) that extracted and returned
  **literal text snippets** from finding details — e.g. a caption number, a heading
  string, a TOC entry, an "expected heading" string, or a `line_preview` excerpt.
- Rendered that string in `job.html` as a "page → label" link, e.g. `5 → Figure 3`,
  using a plain `/pdf#page={{ f.page }}` href — bypassing the (not-yet-existing)
  highlight eligibility check entirely.
- `tests/test_location_label.py` (420 lines) parametrized over the rule-specific
  snippet logic above.

### Why this design was rejected outright, independent of the merge conflicts

1. **Privacy invariant violation.** `job.html` states verbatim: *"No dissertation body
   text, titles, author names, committee names, or captions are shown."*
   `_build_pdf_sublocation` directly reproduces caption text, heading text, and TOC/line
   preview snippets pulled from the student's actual document. This is a hard
   "do not" for this task regardless of how cleanly it would merge.
2. **Bypasses the strict highlight policy.** Its `/pdf#page=` link has no relationship
   to `has_visible_highlight()`; on current `main` this is exactly the discredited
   "page-only" action pattern #321 removed.
3. **Rule-specific surface area.** A thirteen-rule dispatch table is a lot of bespoke
   logic to keep in sync with every future rule change, for a feature whose real value
   (per the original ask) is *"where on the page, roughly"* — not *"what does the
   flagged text say."*

## 3. Decision

**Strategy B — fresh reimplementation**, salvaging only the *concept* (a sub-page
position descriptor shown alongside the page number) and none of PR #311's code.

The new design:

- Adds `sub_page_location_label(bbox, page_size)` to `pdf_highlight.py` — a pure,
  presentation-agnostic function that buckets a bbox's center point into one of a
  fixed, small vocabulary of position labels (`"Top of page"`, `"Bottom of page"`,
  `"Left margin area"`, `"Right margin area"`, `"Upper-left area"`, `"Upper-right area"`,
  `"Lower-left area"`, `"Lower-right area"`, `"Header area"`, `"Footer area"`,
  `"Near page center"`, `"Body area"`), or `""` when the bbox/page size is missing or
  invalid. It never reproduces document text or raw coordinates.
- Repurposes the existing (previously vestigial) `FindingView.location_label` field for
  PDF audits: it used to just duplicate `str(page)` for PDF findings and was never
  rendered anywhere — confirmed by grep across `report_view.py`, `web_app.py`, and all
  test files before reuse. `report_view._finding_view_from_item` now computes
  `bbox`/`page_size`/`has_highlight` first, then calls
  `sub_page_location_label(bbox, page_size)` for PDF audits (source audits keep their
  existing `format_source_location` behavior, unchanged).
- `web_app.py`'s pre-existing `_student_location_text()` helper already read
  `location_label` to build a "Page X - {label}" string for the category/rule/issue-type
  drill-down pages (`problem_group.html`) — it was written anticipating exactly this
  feature, so those three pages required **zero** template changes to pick up the new
  labels.
- `job.html` gained one new "Location:" line per grouped problem card (next to the
  existing polished-comment/suggested-fix lines) and a small "Location" sub-line under
  the page number in both the occurrence table and the "All individual findings" panel.
  No change was made to the highlight-link gating logic (`f.has_highlight`), the
  `no_highlight_reason` fallback, or any action-button wording.

### Vocabulary mapping (geometry bands, fractions of page width/height)

| Band | Vertical | Horizontal | Label |
|---|---|---|---|
| y < 0.08 | header | any | "Header area" |
| 0.08–0.22 | top | left | "Upper-left area" |
| 0.08–0.22 | top | center | "Top of page" |
| 0.08–0.22 | top | right | "Upper-right area" |
| y > 0.92 | footer | any | "Footer area" |
| 0.78–0.92 | bottom | left | "Lower-left area" |
| 0.78–0.92 | bottom | center | "Bottom of page" |
| 0.78–0.92 | bottom | right | "Lower-right area" |
| 0.22–0.78 | middle | left (<0.20) | "Left margin area" |
| 0.22–0.78 | middle | right (>0.80) | "Right margin area" |
| 0.22–0.78 | middle | center, within 0.35–0.65 box | "Near page center" |
| 0.22–0.78 | middle | center, outside that box | "Body area" |

Bands are intentionally independent of any rule's margin-violation threshold (e.g.
P011's allowed-margin box) — they describe rough visual position for student
orientation, not a defect determination.

## 4. What was preserved unconditionally

- No detector thresholds, rule IDs, canonical rule JSON, or raw guideline files were
  touched.
- No dissertation body text, captions, headings, or TOC text is exposed anywhere in the
  new code path — `sub_page_location_label` only ever returns one of the fixed label
  strings above or `""`.
- The strict highlight-eligibility policy (`has_visible_highlight`, PR #321/#324) is
  completely unchanged; sub-page labels are informational text, never an action. A
  finding can show "Top of page" with no PDF action button (when its box fails the
  drawable/visible check), and a finding can show a "highlighted PDF" action with no
  position label (when bbox is missing but page is known) — these are independent
  signals by design.
- No previously-merged exact-problem wording (page-number, margin, font, Ester YES/NO
  matrix, P063 appendix clarity) was altered. New tests assert the exact phrases from
  #320/#323/#324 remain present and are not replaced by a location label alone.

## 5. Validation

- New unit tests: `tests/test_pdf_highlight.py` — 10 parametrized quadrant cases plus
  5 honesty/edge-case tests for `sub_page_location_label` (missing bbox, missing page
  size, degenerate bbox, off-page bbox, never-leaks-raw-coordinates).
- New web-integration tests: `tests/test_sub_page_location_labels.py` — 11 tests
  covering: a valid-bbox label rendering; a margin-side (P011-style) finding; missing/
  invalid bbox showing no misleading label and no highlight action; the highlight-policy
  regression (no forbidden action without a highlight, valid highlight still gets the
  button); page-number regressions (P013 routine suppression, P019 exact wording);
  margin/font wording regressions (P011/P026 exact phrases survive alongside the new
  label); cross-page consistency (main job page + category/rule/issue-type drill-downs);
  mobile/desktop parity; and a route crawl asserting no 500s across all of the above plus
  every linked highlighted-PDF endpoint.
- Full suite: `ruff check`, `mypy src/`, and `pytest` all green; see the PR description
  for exact counts.
