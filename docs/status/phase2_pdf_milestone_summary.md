# Phase 2 PDF Audit Milestone Summary

## 1) Project Goal

Build a local, privacy-preserving assistant for NJIT Graduate Studies thesis/dissertation formatting review.
The Phase 2 PDF path focuses on practical, layout-aware checks that can run offline on student PDFs.

## 2) Current PDF Command

```bash
njit-audit pdf path/to/thesis.pdf
```

## 3) Current Comment Workflow

```bash
njit-audit pdf-comments extract input.pdf --json-out comments.json --md-out comments.md
njit-audit pdf-comments clean input.pdf --out clean.pdf
```

## 4) Implemented PDF Rules (P011-P018)

- `P011` margin detection
  - Detects likely text crossing assumed NJIT margin bounds.
  - Refined and more conservative than initial version, but still heuristic.
  - Manual review required.
- `P012` annotations/comments
  - Detects embedded PDF annotation objects.
  - Generally high-signal on digital PDFs; can miss flattened comments.
  - Manual review still required for final submission readiness.
- `P013` page-number candidates
  - Detects likely page-number glyphs near top/bottom zones.
  - Intentional candidate detector (can be noisy/high-volume).
  - Manual review required.
- `P014` front-matter heading checks
  - Checks named heading layout/style (near-top, centered, bold, caps).
  - Conservative heuristic for obvious heading issues.
  - Manual review required.
- `P015` indentation
  - Checks strong indentation anomalies (unexpected opening indent, likely missing later indent).
  - Conservative/high-confidence gating added to reduce noise.
  - Manual review required.
- `P016` spacing / blank lines
  - Checks strong vertical-gap anomalies on named front-matter pages.
  - Conservative scope by design to avoid noisy body-page flags.
  - Manual review required.
- `P017` captions/table-list title formatting
  - Checks obvious caption/title punctuation and limited case-style signals.
  - Conservative and likely to under-report subtle/multi-line issues.
  - Manual review required.
- `P018` TOC/List alignment
  - Checks TOC/List page-number column alignment, missing page numbers, leader dots, and obvious indent outliers.
  - Conservative grouped warnings on named TOC/list pages only.
  - Manual review required.

## 5) Evaluation on Ester Clean PDF (Latest Known)

Source filename: `clean_without_annotations.pdf`

- `P011`: 33 (after refinement)
- `P012`: 0 (clean PDF)
- `P013`: 113
- `P014`: 1
- `P015`: 13 (after refinement)
- `P016`: 2
- `P017`: 0
- `P018`: 0

These are heuristic signals, not final compliance verdicts.

## 6) What This Can Already Help Graduate Studies With

- Identify PDFs that still contain reviewer annotations.
- Surface suspicious margin-boundary issues quickly.
- Surface candidate page numbers for rapid manual verification.
- Catch obvious named front-matter heading issues.
- Flag high-confidence indentation/spacing problems.
- Flag obvious caption and TOC/list formatting anomalies when visible in text layer.

## 7) What It Cannot Yet Do Reliably

- No OCR/scanned-PDF support.
- No computer-vision layout understanding.
- No semantic interpretation of reviewer intent.
- Subtle TOC/style/caption issues may be missed.
- Manual review is still required for final Graduate Studies decisions.

## 8) Recommended Next Improvements

1. Produce a cleaner student-facing PDF report.
2. Add JSON/Markdown output for `njit-audit pdf` findings.
3. Improve page-number sequence validation beyond candidate detection.
4. Improve expert-comment-to-finding comparison quality.
5. Test against more anonymized/synthetic thesis PDFs for robustness.
6. Add optional OCR path later only if needed.
