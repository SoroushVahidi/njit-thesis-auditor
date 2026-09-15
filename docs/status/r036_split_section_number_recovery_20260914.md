# R036 Split-Leading-Section-Number Recovery (2026-09-14, follow-up)

## Status

Follow-up to `docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md`
(the Ester 2026-09-14 TOC double-spacing policy fix). QA on the resulting
"remaining findings" reviewer package found 3 of 13 sampled examples were
not genuine policy questions at all: they were parent-heading-to-first-
child TOC transitions the existing structural exemption is designed to
skip, misclassified as ordinary peer transitions because PDF text
extraction had detached their leading section number. This document
records the root-cause investigation and the generic recovery fix, on
`fix/r036-recover-split-section-number-classification-20260914`, branched
from the pitch-model implementation
(`fix/r036-toc-wrapped-title-spacing-policy-20260914`, `0b0551f`).

## Root cause

A LaTeX `tocloft`-style TOC renders each entry's number, title, and page
number in three separate tab-stop columns. PyMuPDF's text-extraction line
segmentation treats each column as its own line object even though all
three share one visual row (baseline `y0` identical or within a fraction
of a point). Confirmed directly against raw `page.get_text("dict")` spans
for all three cases reported by QA:

| Case | Number span | Title span | Same y0? | Gap (number x1 → title x0) |
|---|---|---|---|---|
| Muyeed p13 | `"7"` @ x0=108.36 | `"CONTROLLING NEURAL NETWORK GENERALIZATION..."` @ x0=124.75 | y0=622.77 both | 10.5pt |
| Patrick p7 | `"2.2"` @ x0=124.39 | `"Scattering by Two Elastic Disks..."` @ x0=151.32 | y0=487.30 both | 12.0pt |
| Youra p12 | `"1.1"` @ x0=125.10 | `"Solar"` (title start) @ x0=152.59 | y0=163.02 both | 12.5pt |

A lone detached number fragment is either too short to survive
`MIN_CONTINUATION_TEXT_LEN` (8 chars -- "2.2", "1.1.1") or, for a bare
integer like "7", indistinguishable from a page number by
`NUMERIC_ONLY_RE` alone, so `_collect_entry_region_lines` silently
discarded it before this fix. Verified directly: none of `"7"`, `"2.2"`,
`"1.1"` appeared in that function's output on the real PDFs prior to the
fix. This broke two things downstream:

1. **Entry-boundary detection** (`_looks_like_new_entry_start_given_previous`):
   a numbered title with no number in its own text no longer matches
   `NEW_ENTRY_START_RE`, so it can be silently absorbed as a
   "continuation" of the preceding entry (confirmed: Muyeed's "6.9
   Conclusion" was swallowing "7 CONTROLLING NEURAL NETWORK
   GENERALIZATION").
2. **Structural exemption classification** (`_classify_entry_level` /
   `_is_exempt_structural_transition`): with no digit prefix,
   `_classify_entry_level` returns `"unknown"` for both sides of a pair,
   and "pairs involving an unclassifiable level are never exempt" -- so a
   genuine parent-heading-to-first-child transition (which the exemption
   is explicitly designed to skip, per the September 14 pitch-model
   status doc) is checked as an ordinary peer instead.

A second, related artifact was found while validating the fix: some rows
also detach a **trailing dot-leader run** from the title (observed gap
~0.3pt, e.g. Youra `"1 INTRODUCTION"` / `"..............."`). Left alone,
that stray fragment becomes a spurious second "physical line" of what is
really a single-line entry, corrupting the September 14 pitch model's
same-entry internal-pitch calibration (`_internal_wrap_pitches_by_role`)
with a near-zero sample -- observed directly: Youra page 12's calibration
was pulled from a correct ~14.3pt median down to a corrupted ~7.3pt
median by exactly this kind of sample, which in turn made every genuine
double-spaced pair on that page look nearly twice as over-spaced as it
really was (ratio 3.23 instead of the correct ~1.65). Both artifacts are
the same underlying phenomenon (one visual row split into multiple line
objects) and are fixed by the same mechanism.

## Corpus-wide audit (before any fix)

Freshly run against `fix/r036-toc-wrapped-title-spacing-policy-20260914`
(`0b0551f`), the seven evaluation dissertations reproduced exactly the
expected baseline:

| Dissertation | R036 findings |
|---|---:|
| Youra | 20 |
| Anthony | 0 |
| Muyeed | 114 |
| Philip | 20 |
| Praneeth | 0 |
| Sebastian | 0 |
| Patrick | 39 |
| **Total** | **193** |

For every one of these 193 findings, both sides of the pair were checked:
if `_classify_entry_level` already returned a real level (`toc_level_*`,
or `table_entry`/`figure_entry` for LOT/LOF pages, which never depend on
numbering), the side was `CLEAN_NUMBERING`; otherwise the raw PDF spans
were searched for a same-baseline, smaller-x0, hierarchy-number-shaped
sibling.

| Category | Findings (rolled up, either side) |
|---|---:|
| CLEAN_NUMBERING | 53 |
| SPLIT_NUMBER_RECOVERABLE | 140 |
| POSSIBLE_SPLIT_NUMBER_AMBIGUOUS | 0 |
| UNNUMBERED_BY_DESIGN | 0 |
| OTHER_EXTRACTION_ISSUE | 0 |

Of the 140 recoverable findings, a static per-side classification (not yet
accounting for the entry-grouping cascade the real fix produces) found 32
would resolve to a parent-to-first-child depth relationship (i.e. become
exemption-eligible) and 108 would resolve to same-level peers or another
non-exempt shape (i.e. recovering the number would improve the audit
trail but not change the finding's presence). Zero cases were ambiguous
(more than one plausible number candidate) or had no recoverable number
at all among the 4 affected dissertations -- consistent with all four
being LaTeX-generated with the same extraction behavior throughout.

**This confirmed the QA reviewer's 3 known cases were not an isolated
problem: 72.5% of the then-current 193 findings had at least one
misclassified side.**

## Recovery model

Fixed entirely in `_collect_entry_region_lines`
(`pdf_toc_list_wrapped_spacing.py`, shared with P032), via a new
`_reassemble_split_row_fragments` pass that runs on the raw candidate
lines *before* the existing `NUMERIC_ONLY_RE` / `MIN_CONTINUATION_TEXT_LEN`
filters (which still apply afterward, unchanged, to whatever remains
unmerged):

1. Cluster candidate lines into visual rows by sequential y0 proximity
   (within 2.0pt -- generous enough for the observed ~0.3pt sub-pixel
   rounding, far below the smallest genuine inter-line pitch in the
   corpus, ~13-14pt, so two truly different physical lines are never
   merged).
2. Within a row, identify the single unambiguous "primary" fragment: the
   one that is neither a hierarchy-number shape (`^[0-9]+(\.[0-9]+){0,3}\.?$`),
   a plain page-number shape, nor a pure dot-leader/punctuation run. A row
   with zero or more than one such fragment is left completely untouched.
3. If the fragment immediately to the primary's *left* is a valid
   hierarchy-number shape within a sensible gap (≤40pt -- observed real
   gaps are ~10-13pt, this is a generous multiple while staying far short
   of a typical 150pt+ dot-leader run), prepend it.
4. If the fragment immediately to the primary's *right* is a pure
   dot-leader run, append it.
5. A page-number fragment (far right, large x0, already handled by the
   existing `NUMERIC_ONLY_RE` filter) is never merged onto anything, and
   two adjacent number-shaped fragments are never concatenated with each
   other.

This is purely a line-reassembly step: it does not touch the pitch
formula, the 1.6 threshold, or any classification/exemption logic
directly -- `_classify_entry_level` and `_is_exempt_structural_transition`
are unchanged, and now simply see the correct, complete entry text.

## Safeguards against over-reach

- Only merges when there is exactly one unambiguous primary fragment in
  the row (never guesses between multiple candidates).
- Requires the number fragment to match a strict hierarchy-number shape,
  not an arbitrary numeral.
- Requires the number to sit *immediately to the left* of the title
  within a bounded gap -- never bridges to a distant, unrelated fragment.
- Never attaches a page-number-shaped fragment as a prefix, and never
  concatenates two number-shaped fragments together.
- No dissertation name, page number, or literal entry text is
  special-cased anywhere in the fix.

## Corpus-wide validation (after the fix)

| Dissertation | Before | After | Change |
|---|---:|---:|---:|
| Youra | 20 | 0 | -20 |
| Anthony | 0 | 0 | 0 |
| Muyeed | 114 | 71 | -43 |
| Philip | 20 | 9 | -11 |
| Praneeth | 0 | 0 | 0 |
| Sebastian | 0 | 0 | 0 |
| Patrick | 39 | 16 | -23 |
| **Total** | **193** | **96** | **-97** |

Praneeth's 12 Ester-reviewed page-11 cases remain suppressed (exact
real-geometry reproduction test still green). Anthony remains at 0 (its
own structural-heading exemptions, unrelated to this fix, still hold).

**Reason for the 97 removed findings**, in order of confirmed evidence
strength:

1. **Recovered parent-to-first-child exemption.** A conservative,
   evidence-backed lower bound is 32 (the pre-fix static per-side audit
   above) -- confirmed with full detail for the three original QA cases
   (Muyeed "7"→"7.1", Patrick "2.2"→"2.2.1", Youra "1.1"→"1.1.1", plus
   Muyeed's "6.9"→"7" finishing-into-heading case, all now exempt and
   spot-checked directly against `_is_exempt_structural_transition`).
2. **Corrected entry grouping.** Recovering a heading's own number often
   also fixes which physical lines get grouped into which entry (the
   "6.9 Conclusion" / "7 CONTROLLING..." merge bug above is one instance)
   -- this changes which pairs exist to be evaluated at all, independent
   of the exemption outcome, and is not captured by the static per-side
   audit.
3. **Corrected calibration.** The dot-leader-fragment fix alone changed
   the total from 38 (recovery of leading numbers only, calibration still
   corrupted) to 96 (both fixes) -- i.e. fixing that corruption *raised*
   the count by 58, revealing genuine violations the corrupted, too-low
   calibration had been masking as false passes. Youra's complete drop to
   0 falls in the opposite direction: its true single-line pitch (~14.3pt)
   and its actual inter-entry pitch (~23.6pt) yield ratio ≈1.65, just
   above the 1.6 threshold -- genuinely, uniformly double-spaced (with
   this document's own margin above single spacing), not a detector
   artifacts. Spot-checked directly (see below).

An exact, findings-by-findings attribution across all 97 (grouping vs.
exemption vs. calibration, since a single recovered number can shift more
than one mechanism at once) was not attempted -- it would need a full
before/after entry-diffing tool beyond this task's scope. The aggregate
counts, the four fully-traced cases, and the spot checks below are the
evidence base for this document's conclusions.

### Spot checks on the remaining 96

Ratios for the remaining findings on Muyeed/Patrick/Philip cluster in
1.0-1.6 (genuinely under-spaced, correctly still detected), not at any
single suspicious value -- e.g. Muyeed: `{1.2: 33, 1.3: 18, 1.5: 16, 1.0:
2, 1.1: 1, 1.4: 1}`; Philip: `{1.6: 5, 1.0: 4}` (the 1.0 cluster includes
clean, now-correctly-numbered appendix entries like `A.2 The Lyapunov
Inequality...` → `A.3 The Lyapunov Inequality...`). This is consistent
with genuine remaining violations, not a residual calibration artifact.

## Shared-code impact (P032)

`_collect_entry_region_lines` is shared with P032
(`check_pdf_toc_list_wrapped_spacing`, wrapped-entry internal spacing).
P032's real-corpus finding count was 0 on every one of the 7 dissertations
both before and after this fix (compared directly against the original
SHA's file via a side-loaded module) -- no change. The full test suite
(3504 tests, including all existing P032 tests) passes unchanged both
before and after.

## Package wrap-label bug (investigated, not fixed here)

QA separately flagged that the reviewer-package script's
`_wrap_flags_for_pair` used `len(entry) > 1` to decide whether an entry
"wraps," which is fooled by exactly this same row-splitting phenomenon
(a dot-leader fragment at an *identical* y0, not merged because the
package script does its own lightweight entries lookup and does not
call `_reassemble_split_row_fragments`). This is package-script-only --
`_reassemble_split_row_fragments` lives in the detector and is not used
by `scripts/ester_batch/build_r036_remaining_findings_validation_package.py`.
Recommended fix (not applied in this task, which explicitly excludes the
package branch): change the wrap check to require genuinely distinct y0
values (`len({round(l.bbox.y0, 1) for l in entry}) > 1`) rather than raw
fragment count, or simply route the package's entry lookup through
`_collect_entry_region_lines` (now automatically immune to this
specific artifact) instead of re-deriving lines separately.

## Threshold and pitch model

Unchanged: `MIN_INTER_ENTRY_GAP_RATIO = 1.6`,
`SINGLE_LINE_PITCH_FALLBACK_MULTIPLIER = 1.15`, and the pitch formula
itself (`pdf_toc_list_entry_spacing.py`) were not touched by this task.
