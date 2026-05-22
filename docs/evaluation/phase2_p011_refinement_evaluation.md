# Phase 2 P011 Refinement Evaluation

Date: 2026-05-21  
Scope: Private/local re-run of the PDF auditor after refining `P011` margin heuristics.

## Evaluated Files

- `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf`
- `data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf`

## P011 Count Comparison

### `Yin_Haotian_Second_R_with_EF_Feedback.pdf` (108 pages)

- Previous `P011`: 1483
- New `P011`: 33
- Reduction: 1450 findings (97.77%)

### `Yin_H_4th_Review_with_EF_comments_compressed.pdf` (137 pages)

- Previous `P011`: 2027
- New `P011`: 150
- Reduction: 1877 findings (92.60%)

## Notes

- The command `njit-audit pdf ...` ran successfully on both files after refinement.
- Reduced counts indicate improved signal-to-noise, not guaranteed true-positive accuracy.
- Remaining `P011` warnings still require manual review for final compliance decisions.
- No dissertation body text or long annotation contents are included in this summary.
