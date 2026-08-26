# P011/R011 2026-08 Batch: Three False-Positive Root Causes and Fixes

**Date:** 2026-08-25
**Baseline:** `origin/main` @ `989746a120f6e1bd865c17aa5f6380eafde7ccd2`
**Scope:** P011 margin-overflow false positives only. No other rule touched.

## Ground truth

Esther reviewed the lowest-confidence surviving P011 finding from each of
seven real dissertations (`data/evaluation/private/`) and classified all
seven as false positives:

| Student   | Page | Side   | Overflow | Source | Content              |
|-----------|------|--------|----------|--------|-----------------------|
| Youra     | 42   | bottom | 5.6pt    | LaTeX  | prose                |
| Anthony   | 48   | right  | 3.0pt    | Word   | prose                |
| Muyeed    | 19   | bottom | 5.2pt    | LaTeX  | prose                |
| Philip    | 55   | bottom | 3.9pt    | LaTeX  | equation             |
| Praneeth  | 56   | right  | 3.0pt    | Word   | prose                |
| Sebastian | 16   | bottom | 8.2pt    | Word   | prose                |
| Patrick   | 87   | right  | 6.9pt    | LaTeX  | references           |

All seven were reproduced at HEAD (before this fix) using the real PDFs and
confirmed still emitted with these exact page/side/overflow values.

## Root cause analysis

These do **not** share one cause. Per-line geometry (bbox, font size, spans)
was inspected for each of the seven, plus the full distribution of every
other P011 finding across all seven documents (~700 groups), to avoid fitting
a threshold to just the seven reviewed points.

### Cause 1 -- bottom-margin single-trailing-line slack (Youra, Muyeed, Philip, Sebastian)

A fully justified line that lands last on an otherwise full page has its own
descent/leading dip a few points past the nominal 1-inch line. This is normal
single-line typographic slack, not content placed outside the margin. It
occurs in **both** Word (Sebastian) and LaTeX (Youra, Muyeed, Philip) source
PDFs, and on **both** prose and equation lines (Philip) -- so it is a
property of "one trailing line", not of a source engine or content type.

Evidence: the four confirmed false positives measure 3.9-8.2pt overflow.
Plotting `overflow_pt` against the violating line's own font size across all
seven documents shows a smooth, unbroken continuum from ~3pt to 30+pt with
**no natural gap** anywhere in the bottom-margin data -- so a single
universal ratio-based cutoff can't be derived from the seven points alone
without also silently resolving a distinct known-open question (see
"Deliberately not resolved" below). The chosen fix is instead anchored to the
highest confirmed false positive (8.2pt) with a small, disclosed buffer.

### Cause 2 -- right-margin trailing-whitespace-in-bbox artifact (Anthony, Praneeth)

Confirmed by inspecting the raw PDF spans of both flagged lines: every one
ends with a literal trailing space character, and PyMuPDF's span bbox extends
to the space glyph's full advance width (~0.25em, e.g. exactly 3.0pt at
12pt Times New Roman) even though that space has no visible ink. This is a
text-extraction measurement artifact, not a real margin violation.

Evidence: plotting `overflow_pt / dominant_font_size` for every right-margin
finding across all seven documents shows a **clean, sharp gap**: 190+ findings
(the entire Anthony and Praneeth "medium" population) cluster tightly at
ratio 0.248-0.261 (matching one trailing space almost exactly), then nothing
until ratio 0.491 where a structurally different population begins (longer
real overflows, TOC page-number columns, Patrick's references). This gap is
exactly what a real, single-space measurement bug produces and a reverse-fit
threshold would not.

### Cause 3 -- reference-list unbreakable-citation overflow (Patrick)

Patrick's flagged lines have **no** trailing whitespace -- their spans show
real ink (a citation title ending in a period) extending past the margin.
Bibliography entries routinely contain a long title, DOI, or foreign-language
phrase that cannot be wrapped without altering the citation. This is a
distinct, content-driven cause requiring a bounded content-aware exception,
not a geometry correction.

## Cross-checked against prior P011 audits

`docs/status/p011_precision_false_negative_audit_20260710.md` (Sample A /
Sample B, different dissertations) independently flagged a recurring
~9.2pt single-line bottom-margin "footer zone" cluster (Sample A pages 11,
26, 42, 54, 66, 71, 82, 83) as an **open policy question**, not a confirmed
false positive, and separately confirmed several right-margin findings as
**true positives** (Sample B pages 10, 15, 27, 33, 38, overflow 5.4-21.2pt).

- The bottom-margin fix's tolerance (9.0pt) was chosen to sit strictly
  **below** that disputed ~9.2pt cluster, so pages 11, 42, 66, 71, 82, 83 (and
  all of Sample B's confirmed-true-positive right-margin findings, none of
  which are bottom-margin) remain flagged exactly as before. Only pages 26
  (6.0pt) and 54 (5.7pt) -- both below the new tolerance and never confirmed
  by Esther, only guessed as "probable TP" -- are now suppressed, consistent
  with the newly confirmed evidence. **This fix does not resolve the open
  ~9.2pt question**; it remains open for a future Esther review.
- Sample B page 75 (bottom-margin, equation, 6.5pt, previously unreviewed) is
  now also suppressed, consistent with Philip's confirmed 3.9pt bottom-margin
  equation false positive.
- No right-margin or reference-hanging-indent finding in either sample
  changed in a way that contradicts a confirmed-true-positive label.

## Fixes (`src/njit_auditor/rules/pdf_margins.py`)

1. **`_content_right_edge()`** (new): walks a line's spans from the end,
   skips whitespace-only trailing spans, and trims the trailing whitespace
   characters off the last content span's measured right edge using a
   standard ~0.25em space-glyph advance width. Used in `_line_violation` for
   the right-margin check only; it can only narrow the measured edge, never
   widen it. Left/top/bottom geometry is untouched.

2. **`BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT = 9.0`** (new, replaces
   `OVERFLOW_TOLERANCE_PT` for the bottom side only): a per-side pre-filter
   tolerance in `_line_violation`, applied to the *raw* overflow before any
   grouping or confidence math. Surviving bottom violations still report
   their true, unmodified overflow-from-1-inch and confidence -- the
   tolerance only changes whether a small single-line dip is reported at
   all, not the magnitude of anything that survives.

3. **`REFERENCES_MARGIN_EXTRA_TOLERANCE_PT = 6.0`** (new): a bounded extra
   allowance (total ~9.0pt) applied at the group level in
   `run_pdf_margin_rule`, only when `content_kind == "references_hanging_indent"`
   and the side is left/right. The existing `infer_page_margin_context` /
   `infer_margin_content_kind` classification (already used for remediation
   wording) is now computed earlier in the loop and reused for this
   suppression decision, rather than duplicated.

No thresholds shared with other rules changed. `OVERFLOW_TOLERANCE_PT` (3.0,
left/top/right generic), the artifact guard, `_group_confidence`, the
existing "low confidence" suppression (`ester_sample_b_p011_margin_low_overflow.md`),
and all highlight/presentation geometry are unchanged.

## Why not simpler / broader fixes

- A single widened flat tolerance ("make 3.0pt bigger") was rejected: it
  would not explain why Anthony/Praneeth's cause is purely a measurement
  artifact (fixable at the geometry level with zero recall cost) while
  Patrick's and the bottom-margin cases are policy/content judgment calls
  with real recall tradeoffs that must be bounded and disclosed.
- A Word-vs-LaTeX classifier was rejected per the task's explicit guidance:
  the bottom-margin cause is empirically confirmed on both a Word document
  (Sebastian) and three LaTeX documents, so a uniform, source-agnostic
  tolerance is both simpler and better supported by the evidence than a
  fragile classifier.
- An unlimited references exception was rejected: it would also hide a
  genuinely oversized reference-block margin problem. The existing ~24pt
  hanging-indent left-margin violations (covered by
  `test_numbered_reference_left_margin_overflow_stays_high_confidence_with_correct_wording`)
  are far outside the new 9.0pt bound and remain flagged.

## Validation

- `PYTHONPATH=src python -m pytest tests/test_p011_esther_r011_batch_2026_08.py -q` -- 8 new tests, all pass.
- `PYTHONPATH=src python -m pytest tests/ -k "p011 or margin" -q` -- 165 passed.
- `ruff check .` -- pass.
- `mypy src` -- pass (113 files).
- Full `pytest` -- 3145 passed (after updating 3 pre-existing count-assertion
  tests whose expected counts encoded the now-corrected false positives; see
  below).
- All seven real evaluation PDFs re-run end to end: all seven Esther-reviewed
  findings suppressed; zero previously-"high"-confidence findings vanished
  across all seven documents (three were correctly downgraded from
  high to medium after the right-margin trim reduced their measured overflow
  below 12pt -- Praneeth pages 17, 18, 58 -- still surfaced, not lost).

### Pre-existing tests updated (stale expected counts, not regressions)

- `tests/test_p011_near_miss_regression.py`: `test_ester_sample_b_visible_p011_count_is_27`
  -> `..._is_26` (page 75, unreviewed 6.5pt bottom equation, now correctly
  suppressed); `test_ester_sample_a_visible_p011_count_is_17` -> `..._is_15`
  (pages 26, 54, both never-confirmed "probable TP" guesses, now correctly
  suppressed).
- `tests/test_ester_sample_a_correctness.py::test_ester_sample_a_problem_finding_baseline`:
  total problem count 22 -> 20 (same two Sample A pages).

## Remaining open questions for Esther

1. The ~9.2pt recurring bottom-margin "footer zone" cluster flagged in the
   2026-07-10 audit (Sample A pages 11, 42, 66, 71, 82, 83, and the
   equivalent cluster visible across Muyeed/Philip/Praneeth/Youra in this
   batch) is **still open** -- this fix deliberately stops just below it.
   Recommend a follow-up review of a few of these specific pages.
2. Whether reference-list right-margin overflow beyond ~9pt (e.g. Patrick
   pages 5, 88, 90, currently still flagged at 10.2-18.0pt) is ever
   acceptable for a sufficiently long, genuinely unbreakable citation, or
   whether the bounded exception here is already generous enough.
