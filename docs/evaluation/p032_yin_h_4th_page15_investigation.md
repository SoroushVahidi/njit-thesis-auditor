# P032 Yin H 4th Page 15 Investigation

- **Date:** 2026-05-30
- **Baseline commit:** `f255320e356e4d7b4a63a859f3567ea3e933e803` (PR #58 P032 current-dataset evaluation)
- **Dataset:** Yin H 4th review (compressed) PDF — List of Figures page 15 only
- **Findings under review:** 3 P032 warnings on page 15 (`list_of_figures`)

## 1. What was investigated

PR #58 reported three high-confidence P032 findings on page 15 of the Yin H 4th
compressed PDF, all `wrapped_entry_internal_spacing` on List of Figures entries. This
investigation asked whether those warnings reflect true wrapped-entry double spacing,
false positives from wrap-pair heuristics, compressed-PDF geometry artifacts, or
ambiguous/manual-review cases.

## 2. Reproduction (privacy-safe)

Re-running P032 on the tracked Yin H 4th PDF before refinement reproduced:

| # | Page | Section type | Issue type | Observed gap (pt) | Expected max (pt) | Line height (pt) | Confidence |
|---:|---|---|---|---:|---:|---:|---|
| 1 | 15 | list_of_figures | wrapped_entry_internal_spacing | 32.3 | 20.4 | 12.0 | high |
| 2 | 15 | wrapped_entry_internal_spacing | 38.5 | 20.4 | 12.0 | high |
| 3 | 15 | wrapped_entry_internal_spacing | 38.8 | 20.4 | 12.0 | high |

Page 15 is classified as **list_of_figures**. Structural collection found **30** entry-region
lines and **23** likely wrap pairs; only **3** pairs exceeded the 1.7× line-height threshold.

## 3. Structural explanation (no body text)

### Page 15 layout pattern

- Entry lines use two horizontal bands: main entry text near **x0 ≈ 137 pt** and wrapped
  continuation near **x0 ≈ 149 pt** (indent delta within the 12 pt wrap tolerance).
- Normal wrapped continuations on this page show **~0.7 pt** vertical gaps (ratio ≈ 0.06).
- The three flagged pairs show **~32–39 pt** gaps (ratio ≈ 2.7–3.2) with the same indent
  pattern (continuation at **x0 ≈ 149 pt** → next line at **x0 ≈ 137 pt**).

### Repeated false-positive mechanism (all three findings)

For each flagged pair, geometry between the two collected entry lines includes:

1. A **short continuation line** at **x0 ≈ 149 pt** (no inline page-number token on that line).
2. An **intervening page-number-only text line** at **x0 ≈ 149 pt**, **len 2**, excluded from
   P032 entry collection because `MIN_CONTINUATION_TEXT_LEN = 8`.
3. A **large vertical gap** spanning that orphan page-number row plus entry-to-entry spacing.
4. The **next list entry’s first title line** at **x0 ≈ 137 pt**, on the same row as a
   left-column figure index token (**len 3**, **x0 ≈ 108 pt**).

P032’s consecutive-line pairing skipped the orphan page-number row and compared the
continuation line directly to the **next entry’s** first line. The measured gap therefore
mixed **entry boundary spacing** with the page-number row, not internal wrap spacing within
one entry.

| Flagged pair index | Continuation y1 (pt) | Orphan page-number y0 (pt) | Next entry y0 (pt) | Gap (pt) |
|---:|---:|---:|---:|---:|
| 2 | 181.9 | 192.4 | 214.2 | 32.3 |
| 10 | 351.9 | 367.1 | 390.4 | 38.5 |
| 21 | 562.6 | 577.7 | 601.4 | 38.8 |

None of the flagged second lines start with a `Figure N` prefix in the text layer (continuation
and split-entry layouts are common), so existing “new entry start” guards did not apply.

### Neighboring List of Figures pages

| Page | Entry lines | Wrap pairs | P032 flags | Typical wrap gap (pt) |
|---:|---:|---:|---:|---|
| 15 | 30 | 23 | 3 (before fix) | 0.7–38.8 |
| 17 | 34 | 17 | 0 | 0.7–1.1 |
| 18 | 13 | 6 | 0 | 0.7–10.1 |

Pages 17–18 show no wrap pairs above the P032 threshold, supporting that page 15’s warnings
were pairing artifacts rather than document-wide excessive internal spacing.

### Compression / geometry notes

- Entry line bbox heights on page 15 are uniform (**≈ 13.6 pt**); gaps are not from wildly
  inconsistent line boxes.
- Negative wrap gaps (**≈ −1.5 pt**) appear on tight multi-line wraps (overlapping y extents),
  separate from the flagged cases.
- This file is compressed/flattened; split page-number lines are consistent with text-layer
  decomposition rather than visible double-spaced wrap lines alone.

## 4. Conclusion

**Likely false positive (wrap-pair / split page-number text-layer artifact).**

The three P032 warnings on page 15 appear to measure **spacing between separate list entries**
after a continuation line, because page-number tokens on their own short lines are excluded
from entry-region collection. Manual review is still advisable for true visual wrap spacing on
this page, but the automated findings are **not supported** as internal wrapped-entry gaps.

## 5. Code change

**Yes — narrow P032 refinement applied:**

- Skip wrap-gap evaluation when a numeric-only or short page-number line appears strictly
  between two candidate entry-region lines (`_has_intervening_page_number_line`).
- Synthetic regression: `test_p032_orphan_page_number_between_entries_not_flagged`.

After refinement, re-running P032 on Yin H 4th compressed reports **0** findings on page 15
and **0** P032 findings document-wide. Synthetic excessive-gap cases still warn.

## 6. Limitations

- Does not pair right-column page numbers with entry lines the way P018 entry extraction can;
  only breaks wrap pairing when an intervening page-number line is visible in the text layer.
- True excessive internal spacing on a continuation immediately above an inline page-number
  line is still in scope; only gaps with an intervening page-number row are suppressed.
- Does not validate bold, leader dots, or full Q053–Q078 visual compliance.
- Investigation used one compressed dissertation PDF; pattern may differ on uncompressed exports.

## 7. Related docs

- P032 current-dataset evaluation: `docs/evaluation/p032_current_dataset_evaluation.md`
- P032 synthetic validation: `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md`
- P031 split page-number precedent: `docs/evaluation/p031_sebastian_clean_baseline_investigation.md`
