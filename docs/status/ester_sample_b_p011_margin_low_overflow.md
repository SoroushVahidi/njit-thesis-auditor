# Ester Sample B: P011 Low-Overflow Margin False-Positive Fix

**Date:** 2026-07-09
**Baseline:** `origin/main` @ `937572eb1fcfb83070a74ca807332ddaab6114ed` (PR #492 merge)
**Branch:** `fix/ester-sample-b-p011-margin-low-overflow`
**Scope:** P011 margin-overflow false positives only. Not addressed here: P026/P063
font false positive/highlight issue, and the PR #483 conflict — both deferred.

## Root cause

`run_pdf_margin_rule` (`src/njit_auditor/rules/pdf_margins.py`) already computes a
`confidence` label for every margin-overflow finding via `_group_confidence`:

- `"high"` — worst overflow ≥ 12pt, or ≥ 5 lines all overflowing ≥ 8pt
- `"medium"` — worst overflow ≥ 5pt, or ≥ 2 violating lines
- `"low"` — a single violating line with overflow under 5pt

Before this fix, a `"low"` confidence group still produced a full P011 warning
finding — same severity, same presentation, no distinction from a real violation.
That single-line, sub-5pt pattern is dominated by font-metric and text-extraction
measurement noise (PyMuPDF's reported glyph-run bbox can overrun the true ink
extent by a few points depending on font/rendering), not actual content placed
outside the required margin.

Ester's Sample B review confirms this exactly. Every P011 finding she marked as a
false positive (pages 1, 24, 39) was a `"low"` confidence, single-line finding with
overflow of 3.2–4.9pt. Every finding she confirmed as a real violation (pages 10,
15, 27, 33, 38) was `"medium"` or `"high"` confidence, with overflow of 5.4–21.2pt.
The narrowest gap in the data is a clean 0.5pt: page 1's false positive at 4.9pt vs.
page 15's true positive at 5.4pt — falling exactly on either side of the existing
5pt medium-confidence floor. No new threshold was needed; the fix is to stop
reporting findings that already self-identify as `"low"` confidence, since that
confidence tier has no cases anywhere in the reviewed data.

## Fix

In `run_pdf_margin_rule`, after computing `confidence` for a violation group and
before building the finding (`src/njit_auditor/rules/pdf_margins.py`, in the
per-side loop): if `confidence == "low"`, `continue` — skip the group entirely
instead of emitting a WARNING. Nothing else changes: the overflow-tolerance
threshold (3pt), the artifact guard for large low-overflow groups, the
`"medium"`/`"high"` confidence math, highlight-bbox construction, and the P011
question/remediation wording are all untouched.

This is deliberately narrow: it only suppresses the exact pattern Ester's review
identified as noise (single line, under 5pt), not "small overflow" broadly — a
2-line or 5pt+ group still gets `"medium"` and is still flagged.

## Before / after (Sample B fixture)

Before (33 pages flagged): 1, 10, 11, **15**, 24, **27**, **33**, **38**, 39, 41,
43, 47, 56, 62, 63, 68, 72, 73, 75, 76, 77, 78, 80, 89, 92, 97, 101, 103, 104, 105,
106, 107, 108

After (27 pages flagged): **10**, **15**, **27**, **33**, **38**, 41, 43, 47, 62,
63, 68, 72, 73, 75, 76, 78, 80, 89, 92, 97, 101, 103, 104, 105, 106, 107, 108

Suppressed (6 pages, all single-line `"low"` confidence, 3.1–4.9pt overflow):

| Page | Overflow | Ester-reviewed? |
|---|---|---|
| 1  | 4.9pt | Yes — marked false positive |
| 11 | 4.3pt | Not in Ester's reviewed set |
| 24 | 3.2pt | Yes — marked false positive |
| 39 | 4.7pt | Yes — marked false positive |
| 56 | 3.1pt | Not in Ester's reviewed set |
| 77 | 3.6pt | Not in Ester's reviewed set |

Pages 11, 56, and 77 were not part of Ester's explicit page list but match the
identical suppressed pattern (single line, sub-5pt) — suppressing them is the same
conservative rule applied consistently, not an extra judgment call.

Retained true positives (all Ester-confirmed pages, unchanged, still highlighted):

| Page | Overflow | Confidence |
|---|---|---|
| 10 | 21.2pt | high |
| 15 | 5.4pt  | medium |
| 27 | 9.8pt  | medium |
| 33 | 17.7pt | high |
| 38 | 17.6pt | high |

All other previously-flagged pages (41, 43, 47, 62, 63, 68, 72, 73, 75, 76, 78, 80,
89, 92, 97, 101, 103–108) were already `"medium"`/`"high"` confidence and are
unaffected by this fix.

## What was suppressed and why it's safe

Only single-line groups with worst-case overflow strictly under 5pt. This tier had
zero true positives and 100% false-positive rate in the reviewed Sample B data
(3/3 reviewed low-confidence findings were false positives; the other 3 unreviewed
low-confidence findings share the identical measurement profile). No `"medium"` or
`"high"` confidence finding — i.e. nothing with ≥5pt overflow or ≥2 violating
lines — is touched.

## What remains detected

Every P011 finding with overflow ≥5pt or more than one violating line, including
all 5 of Ester's confirmed Sample B true positives, all still resolving to a real,
visible highlight (`has_highlight=True`, `action_kind="highlight"`).

## Tests added

- `tests/test_pdf_rules.py`:
  - `test_p011_tiny_single_line_overflow_is_suppressed` (renamed from
    `..._is_low_confidence`) — synthetic single-line, sub-5pt overflow now produces
    a PASS, not a WARNING.
- `tests/test_p011_margin_visual_polish.py`:
  - `test_single_line_large_right_margin_overflow_stays_precise` — overflow bumped
    from ~4pt to ~18pt so this "far over the margin, must stay a precise highlight"
    case is unambiguously high confidence, distinct from the newly suppressed noise
    tier.
- `tests/test_ester_sample_a_correctness.py`:
  - `test_ester_sample_a_problem_finding_baseline` — updated Sample A baseline
    counts (P011 19 → 17; total 25 → 23) to reflect two Sample A findings that were
    the same single-line sub-5pt pattern.
  - `test_ester_sample_b_p011_low_overflow_false_positives_cleared` — real Sample B
    fixture, asserts zero P011 findings on pages 1, 24, 39.
  - `test_ester_sample_b_p011_true_positives_retained_with_highlights` — real Sample
    B fixture, asserts P011 still fires on pages 10, 15, 27, 33, 38, each with a
    real highlight (`has_highlight=True`, `action_kind="highlight"`).

## Deferred (not addressed in this branch)

- **P026/P063 font false positive / highlight issue** — separate rule; out of scope.
- **PR #483 conflict** — the Sample B feedback-audit documentation PR remains
  untouched per instructions; still needs a rebase/supersession decision.
