# Phase 2 P029 Boundary Guard Evaluation

Date: 2026-05-29  
Scope: Investigation and suppression of implausible Roman numeral candidates in P029.

## Motivation

The current evaluation snapshot (after PR #42) showed P029 = 2 on the Sebastian Fine clean
baseline with implausible expected values of 901 and 1001. These were identified as false
positives caused by TOC entries or body references containing Roman-numeral-like tokens
("m" = 1000, "cm" = 900) being included in the front-matter sequence.

## Root Cause

On pages 13 and 14 of Sebastian Fine (29-page front-matter-heavy document), `detect_page_number_candidates`
returned two additional roman_lower candidates beyond the real page-number sequence:

| Page | Text | Value | Source |
|------|------|------:|-------|
| 13 | `xi` | 11 | Real page number ✓ |
| 13 | `m` | 1000 | TOC entry or section reference — not a page number |
| 14 | `xii` | 12 | Real page number ✓ |
| 14 | `cm` | 900 | TOC entry or section reference — not a page number |

P029 included "m" and "cm" in its sequence because they were in front-matter pages,
had `roman_lower` style, and were not on recognized no-number pages. The resulting
comparisons:
- `m` (1000) as prev → `xii` (12) → `roman_sequence_decrease`, expected 1001
- `cm` (900) as prev → `xiii` (13) → `roman_sequence_decrease`, expected 901

Both findings were false positives. No front-matter section ever legitimately has 900+
Roman-numbered pages.

## Guard Logic

Added to `src/njit_auditor/rules/pdf_roman_sequence.py`:

```python
_MAX_PLAUSIBLE_FRONTMATTER_ROMAN = 50
```

Any candidate with `value > 50` is excluded from the P029 front-matter candidate list.
This removes "m" (1000), "cm" (900), "l" (50 is the boundary — value must be ≤ 50), and
similar large-value tokens while preserving all realistic front-matter page numbers.

A value of 50 is chosen conservatively: NJIT dissertations with >50 front-matter pages are
extremely rare. Real sequences iv→xiii (as in Sebastian Fine) are entirely within bounds.

## P029 Count Before / After

| File | Before | After | Notes |
|------|-------:|------:|-------|
| Sebastian Fine clean baseline | 2 | 0 | False positives removed |
| Yin H 4th compressed | 12 | 12 | All roman_sequence_repeat preserved (viii=8, well under 50) |
| Cibaku Elson | 0 | 0 | Unchanged |
| Yin Haotian 2nd | 0 | 0 | Unchanged |
| Yin H 2nd flattened | 0 | 0 | Unchanged |

## Tests Added

- `test_p029_implausible_high_value_roman_suppressed` — "m" (1000) inserted in sequence; guard suppresses it, no false finding
- `test_p029_cm_value_roman_suppressed` — "cm" (900) inserted in sequence; guard suppresses it
- `test_p029_real_gap_after_high_value_artifact_still_warns` — "m" artifact present but real gap remains after exclusion → warning still fires

## Limitations

- The threshold of 50 is heuristic. A document with >50 front-matter pages would have its
  high Roman numerals suppressed. In practice, NJIT theses do not exceed this.
- Tokens with values ≤ 50 that are still not page numbers (e.g., "l" = 50 as a word fragment)
  remain possible false positives but are much less common.
- All P029 findings still require manual review for final compliance decisions.
