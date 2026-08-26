# P015/R015 2026-08 Batch: Row-Split False-Positive Fix

**Date:** 2026-08-25
**Baseline:** R011 checkpoint `7090b824a8c69e042ced2cb6240d51fbc559cdce`
**Scope:** P015 paragraph-indentation false positives only. No other rule touched.

Note on naming: R015 is the human/student/evaluation-facing rule identifier;
P015 is the internal implementation identifier (`src/njit_auditor/rules/pdf_indentation.py`).
Both names refer to the same detector throughout this document; no
repository-wide identifier rename was performed.

## Human feedback

Esther reviewed three real P015 findings — the only three that currently
surface across the seven-dissertation 2026-08 evaluation batch — and
classified all three as false positives:

| Student | Physical page | Printed page | Confidence | Issue type | Affected line |
|---|---|---|---|---|---|
| Youra | 86 | 69 | HIGH | `missing_later_indent` | "observational evidence directly linking individual SMFR types to corresponding..." |
| Muyeed | 144 | 123 | MEDIUM | `unexpected_indent_on_continuation_line` | "i l−1 is the output of the last layer. We set a one hour time limit for the" |
| Philip | 17 | 1 | MEDIUM | `unexpected_indent_on_continuation_line` | ", where η is the (often small) step size. Much previous work analyzes" |

Anthony, Praneeth, Sebastian, and Patrick had no current P015 finding.
Esther's own diagnosis pointed at mathematical/subscript content confusing
paragraph-boundary detection, and asked whether checking preceding-content
punctuation (e.g. "ends with a period") would help — with an explicit
warning not to adopt that rule blindly, since paragraphs legitimately follow
punctuation other than periods, equations, quotations, lists, and headings.

## Reproduction

All three were reproduced at the R011 checkpoint using the real PDFs
(`data/evaluation/private/`), confirming the exact page, issue type,
confidence, and indent value quoted above.

## Root cause (one mechanism, three manifestations)

Inspecting the raw PDF spans (not just rendered text) for all three cases
showed a single shared mechanism, distinct from Esther's own
period/punctuation hypothesis:

An inline displayed equation, subscript, or superscript can split one
physical printed text **row** into several text-extraction fragments (e.g.
Philip's row "of order O(e^{1/η}), where η is..." extracts as `"of order O"`
+ two equation-glyph fragments + `",where ηis the..."`; Muyeed's row "layers,
and Z_i^{l-1} is the output..." extracts as `"layers,andZi"` +
`"l−1istheoutputofthelastlayer..."`; Youra's row "...SMFR-driven responses.
However, despite..." extracts as `"drivenresponses."` +
`"However,despitethesewell-definedtheoreticalexpectations,"`).

`_is_usable_paragraph_line` (`MIN_TEXT_LEN=20`, alpha-ratio >= 0.45) is
applied *before* paragraph grouping, and the leftmost fragment(s) of each
split row above are short/symbol-heavy enough to fail it. They are silently
dropped — paragraph grouping never sees them. The surviving fragment then
starts partway across the row, at whatever x-position the dropped prefix
happened to end, and grouping/indent measurement (which only look at each
line's own `bbox.x0`) read that position as a real first-line indent.

This produces two different symptoms depending on where in the paragraph it
happens:

- **Muyeed, Philip:** the surviving fragment's inflated x0 becomes the "first
  line" of what the code treats as a freshly-started paragraph. Because its
  text also happens to read as a continuation clause ("l−1 is the output...",
  ", where η is..."), the existing `_paragraph_starts_like_continuation`
  heuristic (already correct) combines with the bogus indent to produce
  `unexpected_indent_on_continuation_line`.
- **Youra:** the orphaned fragment ("However, despite...") is itself too far
  from anything to join a paragraph (even with the existing generous
  first-line tolerance), so it becomes a 1-line "paragraph" that gets
  silently dropped (paragraphs require >=2 lines). The chain is broken: the
  *next* genuinely flush-left continuation line ("observational evidence...")
  is then misread as the new paragraph's first line, and — since it's flush
  (0pt) on a page whose established style is ~28-36pt indents — trips
  `missing_later_indent`.

This is a variant of the already-fixed page-23 pattern
(`docs/status/ester_sample_b_p015_page23.md`, `_merge_same_row_fragments`),
but one that fix doesn't reach: that fix only merges two fragments that are
**both already usable**, and requires near-identical baselines (+/-1pt),
which a subscript/superscript can violate by several points. It never
touches a fragment that fails usability outright and gets dropped before
merging is even considered.

## Root cause per case (not assumed identical)

- **Youra** — LaTeX. Ordinary prose sentence break (period + new sentence)
  landing on the same row as the end of the previous sentence, purely a
  layout coincidence; no math/equation involved at all. Category: layout-
  extraction artifact / paragraph-segmentation gap.
- **Muyeed** — LaTeX. A subscript character (`Z_i^{l-1}`) is what gets
  truncated; the dropped prefix is symbol-heavy, and the affected row's
  fragments also independently overlap by a few points (a second,
  contributing sub-issue: `_merge_same_row_fragments` requires strictly
  non-overlapping fragments, and a subscript's kerning can produce a few
  points of overlap). Category: mathematical/subscript notation confusing
  extraction, per Esther's own diagnosis.
- **Philip** — LaTeX. A displayed inline equation (`O(e^{1/η})`) directly
  interrupts the row; multiple private-use/math-glyph fragments sit between
  the dropped prefix and the surviving continuation. Category: equation/
  formula geometry, per Esther's own diagnosis.

Esther's period-ends-previous-content hypothesis was explicitly **not**
adopted: Youra's own case has that exact shape (a period, then a new,
capitalized sentence) and *needs* the reconnection to happen; a page-68-style
counter-example found during validation (see below) has the identical shape
and *must not* be reconnected. Sentence-final punctuation cannot
discriminate between the two; only the row's geometry (dropped-fragment
detection) reliably can.

## Fix (`src/njit_auditor/rules/pdf_indentation.py`)

1. **`_is_short_extraction_remnant`** (new): true for a line that fails
   `_is_usable_paragraph_line` purely for being short/symbol-heavy — never
   for being a named heading, page number, bullet, caption, **or bare
   section number** (`"2.4.3"`-style — that pattern already has dedicated
   handling in `_find_split_heading_following_paragraph_indices` and must not
   be eaten here; see "Rejected/refined approaches" below).
2. **`_vertical_overlap_fraction`** / **`_effective_row_start_x`** (new): for
   a usable line, scan a small window of neighboring raw lines (unfiltered,
   sorted by `(y0, x0)`) for a short-extraction-remnant that substantially
   overlaps the line's vertical extent and sits to its left, and return the
   leftmost such x0. A window (not strict adjacency) is needed because a
   subscript/superscript can shift a fragment's y0 enough to sort it out of
   strict left-to-right order.
3. **Join-gated correction in `group_lines_into_paragraphs`**: the candidate
   corrected x0 from step 2 is computed for every usable line but is **only
   ever applied when the plain grouping check first fails and the corrected
   x0 would let the line join the paragraph immediately above it**. If the
   correction doesn't actually reconnect anything, the line's true,
   unmodified geometry is used instead. This is the key safety property (see
   "Rejected/refined approaches").
4. **`_merge_same_row_fragments`** (existing function, extended): the
   same-row test now also accepts substantial vertical-overlap (not just
   near-identical baseline), and the no-overlap requirement now tolerates up
   to `SAME_ROW_OVERLAP_ALLOWANCE_PT=5.0` of horizontal overlap — both
   changes needed for Muyeed's subscript-kerning sub-issue. The existing
   `_same_run_style` (font/bold/italic match) gate is unchanged and still
   fully blocks merging a bold run-in heading into its regular continuation.

None of `_paragraph_starts_like_continuation`, `_group_confidence`-equivalent
logic (P015 has no confidence formula, just fixed thresholds), the heading/
split-heading exemptions, or any presentation/wording code changed.

## Rejected/refined approaches (found during validation, not assumed upfront)

- **Unconditional x0 rewrite** (first attempt): applying the corrected x0 to
  every usable line up front, before grouping. This over-reached: on the
  real Sample A fixture it absorbed a bare section-number heading ("2.4.3")
  into its title text, corrupting the dedicated split-heading exemption and
  producing two *new* false positives (pages 48, 62). Fixed by excluding
  bare section numbers from `_is_short_extraction_remnant`.
- **Still-unconditional, section-number-excluded rewrite**: even after that
  exclusion, unconditionally rewriting x0 surfaced a *different* new false
  positive on real Sample B (pages 68, 71, 72, 78, 93): a short, non-bold
  fragment ("principle.") that is genuinely the wrapped tail of one sentence
  sitting on the same row as the genuinely-new, legitimately-indented start
  of the *next* paragraph ("During the early phase of training..."). This
  case is geometrically indistinguishable from Youra's confirmed-good case
  (same vertical-overlap fraction, same non-bold style, same "ends in a
  period, followed by a capitalized new sentence" shape) — no local,
  per-row signal discriminates them. Fixed by making the correction
  **join-gated**: only trust it when it demonstrably reconnects the line to
  the paragraph above; a corrected x0 that still doesn't join anything is
  discarded, so an unrelated same-row coincidence can no longer silently
  zero out a genuinely new paragraph's real indent. This resolved both
  regressions with zero remaining side effects on Sample B/C/D (see below).
- **"Ends with a period" rule** (Esther's own suggestion): rejected per the
  task brief and confirmed wrong by the page-68 counter-example above — the
  identical punctuation shape needs opposite treatment depending on
  paragraph structure, which punctuation alone cannot resolve.
- **Confidence downgrade instead of a fix**: rejected — Youra's confirmed
  case was HIGH confidence; downgrading would not have removed the finding,
  and would not address Muyeed/Philip's MEDIUM findings either.

## Validation

- `PYTHONPATH=src python -m pytest tests/test_p015_esther_r015_batch_2026_08.py -q` — 11 new tests, all pass.
- `PYTHONPATH=src python -m pytest tests/ -k "p015 or indent" -q` — 148 pre-existing tests, all pass unchanged.
- `ruff check .` — pass. `mypy src` — pass (113 files).
- Full `pytest` — 3157 passed (after updating one pre-existing count assertion; see below).
- All seven real evaluation PDFs re-run end to end (see next section).
- All four `ester_sample_*` real fixtures (A/B/C/D, independent of the seven
  2026-08 dissertations) re-run: Sample A's own pre-existing P015 finding
  (page 77) turned out to be the same root cause and is now also correctly
  suppressed (see below); Sample B, C, and D are **byte-for-byte identical**
  before/after (same pages, same issue types, same confidence, same indent
  values) — zero side effects.

### Pre-existing test updated (stale expectation, not a regression)

`tests/test_ester_sample_a_correctness.py::test_ester_sample_a_problem_finding_baseline`:
P015 count 1 -> 0 (total 20 -> 19). Sample A page 77's single finding was the
exact same root cause as the three Esther-confirmed false positives: a short
fragment ("MPDPTWinstances.") on a split text row was silently dropped,
orphaning the true continuation and making the next paragraph look like it
was missing an indent. Confirmed via direct diagnosis (see below), not
assumed.

## Before / after: all seven real dissertations

| Document | Old total | New total | Old H/M | New H/M | Esther target still emitted? |
|---|---|---|---|---|---|
| Youra | 1 | 1 | 1/0 | 1/0 | No (page 86 suppressed) |
| Anthony | 0 | 0 | 0/0 | 0/0 | N/A (none before or after) |
| Muyeed | 2 | 1 | 1/1 | 1/0 | No (page 144 suppressed) |
| Philip | 9 | 6 | 6/3 | 5/1 | No (page 17 suppressed) |
| Praneeth | 0 | 0 | 0/0 | 0/0 | N/A |
| Sebastian | 0 | 0 | 0/0 | 0/0 | N/A |
| Patrick | 0 | 0 | 0/0 | 0/0 | N/A |

All three Esther-reviewed targets are gone. Anthony/Praneeth/Sebastian/Patrick
remain at zero — no new findings were introduced on any of those four
documents.

## Every P015 finding that changed as a side effect (individually classified)

Beyond the three confirmed targets, the fix changed five other findings
across Muyeed/Philip/Youra. Each was individually diagnosed (not assumed):

| Document | Page | Change | Classification | Basis |
|---|---|---|---|---|
| Muyeed | 117 | unchanged | stable positive control | Same finding, same values, before and after |
| Philip | 21, 29, 86, 115, 132 | unchanged | stable positive controls | Same findings, same values, before and after |
| Philip | 58 | disappeared | **likely corrected false positive** | Paragraph's true first line recovered a subscript-truncated prefix ("T_m follows..."); the recovered line is correctly recognized as a continuation (`_paragraph_starts_like_continuation` now true), matching the same mechanism as the three confirmed targets |
| Philip | 101 | disappeared | **likely corrected false positive** | Same mechanism: an equation/subscript-truncated line ("mfollows directly from the weak Harris theorem...") is now correctly folded into its paragraph instead of standing alone as a mis-indented continuation |
| Youra | 101 | **new appearance** | **possible new false positive — investigated, disclosed, not fixed in this task** | See below |

### Youra page 101 — investigated in depth

A new `missing_later_indent` (HIGH) finding appeared. Root cause: a
**different, pre-existing** detector limitation — a bold-or-plain run-in
heading ("Comparison with the Type 4 SMFR scenario") shares a row with the
genuine start of the following paragraph's first line ("Case 1 provides an
observational..."), and the two fail to merge (correctly, per the run-in-
heading guard) and fail to join anything else (the x-gap exceeds even the
generous first-line tolerance). "Case 1 provides an observational..." is
silently orphaned and dropped (1-line paragraph), and the genuinely-
continuing next physical line ("counterpart to the Type 4 SMFR
configuration...") is misread as the paragraph's effective first line —
*this exact misclassification already existed before this fix*. What changed
is that this fix's row-remnant reconnection correctly folded in three more
downstream lines that are genuinely part of the same paragraph (extending it
from 2 lines to 6), crossing `MIN_LINES_FOR_MISSING_LATER_INDENT=4` and
exposing a pre-existing miscount that had previously been silently below the
line-count gate.

This is not caused by the new row-remnant-absorption logic touching this
row (neither "Comparison with..." nor "Case 1 provides..." is a short/
symbol-heavy remnant — both are independently usable, ordinary text) and is
not one of Esther's three confirmed cases. Fixing the underlying run-in-
heading-adjacent-orphan pattern properly would require a materially broader
change than the narrow, evidence-bound scope of this task, and — given how
easy it proved to introduce new regressions in this exact area (see
"Rejected approaches" above) — was deliberately left for a separate,
dedicated follow-up rather than risked here. **Flagged explicitly as a
remaining open item, not silently shipped.**

## False-negative safety (positive controls)

- Zero previously-existing findings vanished silently anywhere in the seven
  real documents except the three confirmed targets and the two same-family
  Philip corrections above (both independently diagnosed as genuine
  corrections, not recall loss).
- `tests/test_p015_esther_r015_batch_2026_08.py` includes three positive
  controls proving the fix is narrowly targeted: a genuinely unindented
  later paragraph is still flagged even with an unrelated dropped fragment
  elsewhere on the page; a genuinely mis-indented continuation line (no
  row-split involved) is still flagged; a real new, correctly-indented
  paragraph starting on its own row after an unrelated short trailing word
  is evaluated normally, with no residual absorption.
- All pre-existing P015 tests (148, including every prior Ester Sample A/B
  regression, the split-numbered-heading test, the run-in-heading guard
  test, and the original same-baseline-split page-23 test) pass unchanged.
- Sample B/C's own confirmed-real findings (pages 22, 23, 34, 46, 79, 88)
  are byte-for-byte unchanged.

## Files changed

- `src/njit_auditor/rules/pdf_indentation.py`
- `tests/test_p015_esther_r015_batch_2026_08.py` (new)
- `tests/test_ester_sample_a_correctness.py`

## Remaining questions / follow-ups for Esther

1. Youra page 101 (see above): a pre-existing, unrelated run-in-heading-
   adjacent orphaning pattern is now visible where it was previously masked
   by a line-count coincidence. Recommend a dedicated follow-up review of
   this specific pattern rather than folding a broader fix into this batch.
2. The `_merge_same_row_fragments` overlap allowance (5pt) and vertical-
   overlap fraction (50%) were calibrated from Muyeed's specific subscript
   geometry; no other real-corpus regression surfaced from loosening them,
   but they have not been stress-tested against a wider corpus of heavily
   mathematical dissertations beyond the seven evaluated here.
