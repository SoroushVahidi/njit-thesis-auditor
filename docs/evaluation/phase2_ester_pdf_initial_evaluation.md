# Phase 2 Initial Evaluation on Private Ester PDFs

Date: 2026-05-21  
Scope: Local/offline run of `njit-audit pdf` on private Ester PDF files already in this repository.

## Files Evaluated

- `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf`
- `data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf`

## Command Execution Status

- `njit-audit pdf ...` completed successfully for both files.
- No crashes occurred during normal runs on these two PDFs.

## Aggregate Findings (Current Foundation Rules)

### 1) `Yin_Haotian_Second_R_with_EF_Feedback.pdf`

- Pages: 108
- `P011` (possible margin-boundary text): 1483 findings
- `P012` (PDF annotations/comments): 65 findings
- `P013` (page-number candidates): 113 findings

### 2) `Yin_H_4th_Review_with_EF_comments_compressed.pdf`

- Pages: 137
- `P011` (possible margin-boundary text): 2027 findings
- `P012` (PDF annotations/comments): 0 findings
- `P013` (page-number candidates): 149 findings

## Example Finding Types (No Body Text)

- `P011`: “Possible text outside assumed NJIT margin rectangle.”
- `P013`: “Candidate page number 'iv' found near bottom margin.”
- `P012`: “PDF annotation/comment detected (Highlight).”

## Usefulness Assessment

- The Phase 2 foundation is useful for quickly surfacing:
  - likely page-number glyphs/zones,
  - possible annotation presence,
  - and possible margin-boundary outliers.
- It is especially useful as a triage signal before manual formatting review.

## Observed False Positives / False Negatives

- `P011` volume is high on both PDFs, indicating likely false positives from conservative block-level geometry checks (e.g., headings, lists, or layout elements near boundaries).
- `P013` is intentionally heuristic and may flag candidates that are not compliance issues by themselves.
- `P012` may under-detect comments if a PDF has flattened/removed annotation objects.

## Recommended Next PDF Rules / Improvements

1. Add page-type-aware margin thresholds (front matter vs. body) and smarter block filtering to reduce `P011` noise.
2. Add footer/header zone segmentation and sequence checks for stronger page-number validation beyond candidate detection.
3. Add optional PDF text normalization for rotated text and edge artifacts before margin checks.
4. Add confidence scoring or grouping to summarize many similar `P011` hits into fewer actionable issues.
5. Add optional compile-log to PDF cross-check signals in a later phase (still local-only).

## Privacy Notes

- Evaluation was performed fully local/offline.
- No paid APIs or external document uploads were used.
- No dissertation body text is copied into this summary.
