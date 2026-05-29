# Phase 2 PDF Audit Milestone Summary

See also: [Rule Coverage Audit](rule_coverage_audit.md) — comprehensive mapping
of all Q001–Q079 and P001–P020 rules against NJIT guideline sources, with
priority backlog and gap analysis.

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

## 4) Implemented PDF Rules (P011–P025, including P022)

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
- `P022` front-matter no visible page number
  - Checks Abstract, Title, Approval, and Copyright pages for visible page-number candidates.
  - Uses P013-style top/bottom zone detection targeted at confirmed named no-number pages.
  - Year 1900–2099 tokens are suppressed on the title page to avoid graduation-year false positives.
  - EF evaluation: 0 findings on all 4 EF PDFs (expected — late-stage reviews have this corrected).
  - Manual review required.
- `P023` body-text double-spacing
  - Checks whether body-text line spacing is consistent with double-spacing (ratio ≥ 1.55×).
  - Requires ≥8 suspicious gaps, ≥60% suspicious fraction, median ratio < 1.55× to emit a warning.
  - Skips TOC, List, References, and all named front-matter pages.
  - Excludes top/bottom 15% margin zones (running headers, footnotes, page numbers).
  - EF evaluation: 0 findings on Yin 4th review (clean); 4–6 findings on earlier drafts.
  - Manual review required.
- `P024` TOC/LoT/LoF entry capitalization and punctuation
- `P025` front-matter structure: abstract body presence, title page degree phrase and institution, approval page content, Abstract-before-TOC order check
  - EF evaluation: 0 findings on Yin 4th review (clean/text-rich); 2 title-page false positives on 3 files with image-based title pages.
  - Manual review required.
  - Checks TABLE OF CONTENTS entries for expected capitalization by level (L1=ALL CAPS Q049, L2=Title Case Q050).
  - Checks LIST OF TABLES entries for Title Case compliance and absence of terminal periods.
  - Checks LIST OF FIGURES entries for sentence-case compliance (conservative: requires >60% later words capitalized).
  - TOC level classified by numbering pattern (`1.x`, `1.x.x`, `CHAPTER`) and indentation clusters.
  - Strips leader dots and page-number tokens before checking entry text.
  - EF evaluation: 12 findings on Yin 4th review (8 LoT title-case, 2 terminal punct, 1 TOC L2, 1 LoF); 0 on other files (TOC pages not extractable).
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
