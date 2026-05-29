# Phase 2 PDF Audit Milestone Summary

## 1) Project Goal

Build a local, privacy-preserving assistant for NJIT Graduate Studies thesis/dissertation formatting review.
The Phase 2 PDF path focuses on practical, layout-aware checks that run offline on student PDFs.

## 2) Current PDF Command

```bash
njit-audit pdf thesis.pdf --json-out report.json --md-out report.md
```

Notes:

- Console output is still shown by default.
- `--json-out` / `--md-out` are optional structured outputs for workflow use.

## 3) Current Comment Workflow

```bash
njit-audit pdf-comments extract input.pdf --json-out comments.json --md-out comments.md
njit-audit pdf-comments clean input.pdf --out clean.pdf
```

## 4) Implemented PDF Rules (P011-P019)

- `P011` margin detection
  - Detects likely text crossing assumed NJIT margin bounds.
  - Refined and more conservative than initial version, but still heuristic.
  - Manual review required.
- `P012` annotations/comments
  - Detects embedded PDF annotation objects.
  - High-signal on digital PDFs, but flattened comments can be missed.
  - Manual review required.
- `P013` page-number candidates
  - Detects likely page-number glyphs near top/bottom zones.
  - Candidate detector by design; can be high-volume.
  - Manual review required.
- `P014` front-matter heading checks
  - Checks named heading layout/style (near-top, centered, bold, caps).
  - Conservative heuristic for obvious heading issues.
  - Manual review required.
- `P015` indentation
  - Checks strong indentation anomalies.
  - Conservative/high-confidence gating added to reduce noise.
  - Manual review required.
- `P016` spacing / blank lines
  - Checks strong vertical-gap anomalies on named front-matter pages.
  - Conservative scope to avoid noisy body-page flags.
  - Manual review required.
- `P017` caption/title formatting
  - Checks obvious caption/title punctuation and limited case-style signals.
  - Conservative and likely to under-report subtle/multi-line issues.
  - Manual review required.
- `P018` TOC/List alignment
  - Checks TOC/List page-number alignment, missing numbers, leader dots, and obvious indent outliers.
  - Conservative grouped warnings on named TOC/list pages only.
  - Manual review required.
- `P019` page-number sequence/style validation
  - Builds on P013 candidates and checks obvious sequence/style/position inconsistencies.
  - Includes missing/multiple/inconsistent-position/sequence-gap/mixed-style signals.
  - Conservative and candidate-based; does not yet enforce full NJIT-specific numbering policy.
  - Manual review required.
- `P020` title and heading capitalization
  - Checks NJIT title-case compliance for Level 2 headings (bold, X.x format) and table titles.
  - Based on `Titles Examples Level 1 to 5.docx` guideline: Level 2 uses Title Case.
  - Skips body paragraphs, figure captions (sentence case), references pages, and all-caps labels.
  - Preserves all-caps acronyms; skips hyphenated words and math tokens conservatively.
  - Manual review required.

## 5) Evaluation on Ester Clean PDF (Latest Known)

Source filename: `clean_without_annotations.pdf`

- `P011`: `33` (after refinement)
- `P012`: `0` (clean PDF)
- `P013`: `113`
- `P014`: `1`
- `P015`: `13` (after refinement)
- `P016`: `2`
- `P017`: `0`
- `P018`: `0`
- `P019`: `15`
- `P020`: not yet run on this file (added after this snapshot)

These are heuristic signals, not final compliance verdicts.

## 6) What This Can Already Help Graduate Studies With

- Identify PDFs that still contain reviewer annotations.
- Surface suspicious margin-boundary issues quickly.
- Surface page-number candidates and obvious sequence/style irregularities.
- Catch obvious named front-matter heading issues.
- Flag high-confidence indentation/spacing issues.
- Flag obvious caption and TOC/list formatting anomalies where visible in text layer.
- Produce JSON/Markdown audit summaries for repeatable review workflows.

## 7) What It Cannot Yet Do Reliably

- No OCR/scanned-PDF support.
- No computer-vision layout understanding.
- No semantic interpretation of reviewer intent.
- Subtle TOC/style/caption/page-number policy issues may still be missed.
- Manual review is still required for final Graduate Studies decisions.

## 8) Recommended Next Improvements

1. Produce an even cleaner student-facing PDF audit report format.
2. Strengthen page-number policy validation beyond candidate-based heuristics.
3. Improve expert-comment-to-finding comparison quality.
4. Expand robustness testing with more anonymized/synthetic thesis PDFs.
5. Add optional OCR path later only if needed.
