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

## 4) Implemented PDF Rules (P011–P028)

- `P011` margin detection
  - Detects likely text crossing assumed NJIT margin bounds.
  - Artifact guard added: groups with ≥5 lines all within 8pt of the margin are suppressed as
    compression-coordinate artifacts; reduces false positives 53% on the compressed Yin H 4th PDF.
  - Adds `confidence` field (low/medium/high) to finding details.
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
  - Centering now checks against text-area center (accounting for NJIT's 1.5"/1" margins), not
    physical page center. This eliminated false positives on all tested PDFs.
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
- `P024` TOC/LoT/LoF entry capitalization and terminal punctuation
  - Checks TABLE OF CONTENTS entries for expected capitalization by level (L1=ALL CAPS, L2=Title Case).
  - Checks LIST OF TABLES entries for Title Case compliance and absence of terminal periods.
  - Checks LIST OF FIGURES entries for sentence-case compliance.
  - TOC level classified by numbering pattern (`1.x`, `1.x.x`, `CHAPTER`) and indentation clusters.
  - EF evaluation: 12 findings on Yin 4th review; 0 on other files (TOC pages not extractable).
  - Manual review required.
- `P025` front-matter structure: abstract body presence, title-page degree/institution, approval-page content, Abstract-before-TOC order
  - EF evaluation: 0 findings on Yin 4th review (text-rich); 2 title-page false positives on image-based title pages.
  - Manual review required.
- `P026` body font compliance
  - Checks font size (expected 12pt, ±1pt tolerance) and font family (Times New Roman or accepted equivalent).
  - One finding per (page, issue_type). Requires ≥5 violations AND ≥50% of body spans.
  - Accepted aliases: Times, TimesNewRomanPSMT, NimbusRomNo9L, TeX Gyre Termes, Liberation Serif, FreeSerif, STIX.
  - Computer Modern (CMR12, the LaTeX default) is flagged as non-Times.
  - EF evaluation: 92–117 family warnings per document (all 4 PDFs use CMR or Georgia/Arial); 0–1 size warnings.
  - Manual review required.
- `P027` heading-level style check
  - Infers heading level from numbered-section patterns (1.1, 1.1.1, etc.) and CHAPTER/APPENDIX headings.
  - Checks: L1 = ALL CAPS; L2 = Title Case; L3-5 = Sentence case (L4/L5 + terminal period).
  - EF evaluation: 1 finding (Cibaku Elson), 2 findings (Yin 4th) — all `level1_not_all_caps`.
  - Manual review required.
- `P028` page-numbering regime
  - Checks that front-matter numbered pages use lowercase Roman numerals and body pages use Arabic numerals.
  - Region detected from named front-matter headings + first CHAPTER/APPENDIX heading.
  - Q-rule basis: Q022, Q031, Q035, Q046, Q060.
  - EF evaluation: 8 findings on Cibaku Elson (Arabic on front-matter); 8 on Yin 4th (mixed regime); 0 on Yin 2nd.
  - Manual review required.
- `P029` roman sequence ordering
  - Conservatively validates visible lowercase Roman numeral ordering within front-matter (i, ii, iii...).
  - Flags `roman_sequence_repeat`, `roman_sequence_gap`, and `roman_sequence_decrease` on adjacent visible-numbered front-matter pages.
  - Skips named no-number pages; requires ≥2 visible roman candidates; conservative to avoid false positives.
  - EF evaluation: 12 findings on Yin 4th compressed (all repeats); 0 on other EF PDFs.
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
