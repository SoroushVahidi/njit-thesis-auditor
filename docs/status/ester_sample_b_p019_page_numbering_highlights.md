# Ester Sample B: P019 Page-Numbering Highlight Fix (Pages 57-58)

**Date:** 2026-07-09
**Baseline:** `origin/main` @ `ae815a9d09af5883a2fff90424d20d94d6d6e3f3` (PR #489 merge)
**Branch:** `fix/ester-sample-b-p019-page-numbering-highlights`
**Scope:** P019 pages 57/58 only (SB-07 from `docs/status/ester_sample_b_feedback_audit.md`).
Not addressed here: P011 margin false positives, P026/P063 font false positive/highlight
issue, and the PR #483 conflict — all deferred per that audit's recommended sequencing.

## Root cause

Sample B's built-in fixture (`data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf`)
reproduces a published paper as a dissertation chapter. That reprinted material carries
its own original page numbering ("2", "1") printed near the top of pages 57 and 58,
*in addition to* the manuscript's real, continuously incrementing page number ("43",
"44") printed at bottom-center — the same position used on all 106 of the document's
other numbered pages.

P019's `check_pdf_page_number_sequence` (in `src/njit_auditor/rules/pdf_page_numbers.py`)
flags any page with more than one plausible page-number-shaped token as
`multiple_page_numbers`, with no allowance for "one candidate is the document's
overwhelming, established pattern; the other is a rare secondary token at the opposite
edge of the page." Ester's Sample B review judged this a false positive: the
manuscript's real page number is unambiguous, so requiring manual "verify which token
is correct" review is unwarranted here. The recommended fix in the audit doc was to
"keep the exact page-number highlight on the number itself," which also pointed at a
second, independent problem: the finding's bbox was `plausible[0].bbox` — the first
candidate found in document scan order — which on these two pages happened to be the
top token (the noise), not the real page number.

**A second, non-obvious coupling:** P013 (`run_pdf_page_number_candidates_rule`, same
file) independently computes its own `candidate_count_on_page` using the same
"how many plausible tokens are on this page" logic, and
`page_number_student_preview.classify_visible_page_number_issue` separately maps
`candidate_count_on_page > 1` to the same `duplicate_or_ambiguous_page_number`
problem type P019 uses. Normally P013's raw candidate finding for a page is suppressed
in `report_view._collect_claimed_page_number_keys` as "redundant with P019's confirmed
problem" — but only when P019 *does* report a problem there. Fixing only P019's
`multiple_page_numbers` check (without also fixing P013's count) simply stopped P019
from claiming pages 57/58, which un-suppressed P013's own raw candidate finding at
those same pages — moving the exact same false positive from P019 to P013 instead of
resolving it. This was caught by `tests/test_ester_sample_a_correctness.py::test_ester_sample_b_page_number_false_positives_resolved`
going from passing to failing (`P013 == 0` → `P013 == 2`) during development of this fix.

## Fix

Added two small helpers to `src/njit_auditor/rules/pdf_page_numbers.py`:

- `_dominant_location(filtered_by_page)` — returns `"top"` or `"bottom"` only when one
  location accounts for at least 90% of all plausible page-number candidates *and*
  the document has at least 10 such candidates total. Both thresholds are deliberately
  conservative: they require an unmistakable, document-wide pattern, and are inactive
  (return `None`, changing nothing) on short documents or documents without a clear
  numbering-location pattern — including every existing synthetic test PDF in this
  suite, which are all 2-5 pages.
- `_filter_secondary_location_noise(plausible, dominant_location)` — on a page that has
  a candidate at the document's dominant location, drops any candidate at a *different*
  location. Never fires when both candidates share the same location (e.g.
  bottom-center + bottom-right), which remains a genuine same-location ambiguity.

Both `check_pdf_page_number_sequence` (P019) and `run_pdf_page_number_candidates_rule`
(P013) now apply this filter before deciding whether a page has more than one plausible
candidate, so the two rules stay consistent. The `multiple_page_numbers` bbox now also
uses `_primary_plausible_candidate` (rank-based: position score, then style score, then
text length) instead of the first-detected candidate, so any remaining genuine
ambiguity highlights the strongest, most page-number-like token.

Nothing else changed: `_filter_toc_column_candidates`, the mixed-style checks, the
sequence-gap checks, and the `inconsistent_position` check are untouched — they operate
on the unfiltered candidate lists exactly as before, so P028's regime checks and P013's
front-matter TOC-noise suppression are unaffected.

## Before / after (Sample B fixture)

| | Before | After |
|---|---|---|
| P019 `multiple_page_numbers` on pages 57, 58 | 2 findings (false positive) | 0 |
| P019 document-level `mixed_numbering_style` | 1 finding | 1 finding (unchanged — still surfaced honestly with `has_highlight=False` and a document-level explanation, not silently dropped) |
| P013 `page_number_candidate` on pages 57, 58 | suppressed (redundant with P019) | still correctly reports 1 plausible candidate per page, not a duplicate |
| Highlight bbox on any remaining `multiple_page_numbers` finding | first-detected candidate (could be the wrong token) | highest-ranked (dominant position + style) candidate |

## Tests added

- `tests/test_pdf_rules.py`:
  - `test_p019_embedded_reprint_top_number_not_flagged_as_multiple` — the exact
    pages-57/58 pattern, synthesized at a document size large enough to trigger the
    dominant-location filter.
  - `test_p019_genuine_duplicate_bottom_candidate_still_flagged_in_large_doc` — a
    same-location (both bottom) duplicate remains flagged even in a large document.
  - `test_p019_embedded_reprint_pattern_not_suppressed_in_small_document` — conservative
    guard: below the minimum sample size, a top+bottom split is still flagged (not
    enough signal to trust a "dominant" location).
  - `test_p019_multiple_page_numbers_highlight_targets_dominant_candidate` — the bbox on
    a remaining genuine `multiple_page_numbers` finding is the dominant/highest-ranked
    candidate, not scan-order-first.
  - `test_p013_embedded_reprint_top_number_not_counted_as_duplicate` — P013's own
    `candidate_count_on_page` gets the same filtering, closing the P013/P019 coupling
    gap described above.
- `tests/test_ester_sample_a_correctness.py`:
  - `test_ester_sample_b_p019_page57_58_embedded_reprint_not_flagged` — real Sample B
    fixture, asserts zero `duplicate_or_ambiguous_page_number` findings from either
    P019 or P013 on pages 57/58.
  - `test_ester_sample_b_p019_document_level_finding_still_surfaced_honestly` — the
    document-level mixed-numbering-style finding remains present with an honest
    "document-level, no highlight" explanation.

All pre-existing P019/P013/P028 tests (41 in `test_pdf_rules.py` matching
`p019|page_number|numbering`, plus the full Sample A/B correctness suite) continue to
pass unchanged.

## Deferred (not addressed in this branch)

- **P011 margin false positives** — separate rule, separate root cause; out of scope.
- **P026/P063 font false positive / highlight issue** — separate rule; needs its own
  investigation into font extraction/tolerance per the original Sample B audit
  (SB-14).
- **PR #483 conflict** — the Sample B feedback-audit documentation PR is currently
  `CONFLICTING`/`DIRTY` against `main` (base advanced past it after several
  individual fix PRs landed, including this one). Left untouched per instructions;
  needs a rebase/supersession decision by whoever picks it up next.
