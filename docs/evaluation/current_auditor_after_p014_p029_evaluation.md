# Current Auditor Evaluation After P014 and P029 Refinements

## 1. Purpose and Auditor Version

- **Date:** 2026-05-29
- **Main commit:** `6a0baaf` — "Investigate P014 clean-baseline findings (#41)"
- **Auditor version:** P001–P029 implemented
- **Supersedes:** `docs/evaluation/after_p020_refinement_current_snapshot.md` (commit `96543ef`)

Recent precision improvements since the prior snapshot:

| PR | What changed |
|----|-------------|
| #39 | Added P029 — front-matter Roman numeral sequence ordering |
| #40 | P011 compression artifact guard: groups with ≥5 lines all within 8pt of margin suppressed |
| #41 | P014 centering: now compares against text-area center (324pt for NJIT margins), not page center |

---

## 2. Dataset Inventory

| File | Category | Pages |
|------|----------|------:|
| `250218 Cibaku Elson First Review.pdf` | EF-commented PDF — Elson Cibaku, 1st review | — |
| `260415 Yin H _2nd_review with EF Comments.pdf` | EF-commented PDF — H. Yin, 2nd review (flattened) | — |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | EF-commented PDF — H. Yin, 2nd review (65 highlights) | 108 |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | EF-commented PDF — H. Yin, 4th review (compressed) | 137 |
| `Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf` | Clean baseline — no EF annotations | 29 |

Skipped: `260330_YESNO_audit_logic_matrix.xlsx` (not a PDF).

---

## 3. Finding Counts by File

| Rule | Cibaku Elson | Yin H 2nd flat | Yin Haotian 2nd | Yin H 4th comp | Sebastian Fine |
|------|-------------:|---------------:|----------------:|---------------:|---------------:|
| P011 | 21 | 33 | 33 | **70** | 12 |
| P012 | 78 | — | 65 | — | — |
| P013 | 99 | 113 | 113 | 149 | 27 |
| P014 | **0** | **0** | **0** | **0** | **0** |
| P015 | 5 | 13 | 13 | 8 | — |
| P016 | 1 | 2 | 2 | 4 | 2 |
| P017 | — | — | — | 23 | 1 |
| P018 | — | — | — | 17 | 2 |
| P019 | 8 | 15 | 15 | 25 | 4 |
| P020 | 2 | 1 | 1 | 30 | 3 |
| P023 | 6 | 4 | 4 | — | 1 |
| P024 | — | — | — | 12 | — |
| P026 | 92 | 103 | 103 | 117 | — |
| P027 | 1 | — | — | 2 | — |
| P028 | 8 | — | — | 8 | — |
| P029 | — | — | — | 12 | 2 |
| **Total** | **321** | **284** | **349** | **477** | **54** |

`—` = 0 findings.

### Aggregate by Rule (all 5 files)

| Rule | Total | Category |
|------|------:|---------|
| P011 | 169 | margin_or_overflow |
| P012 | 143 | annotations |
| P013 | 501 | page_numbering |
| P014 | 0 | heading_title |
| P015 | 39 | indentation |
| P016 | 11 | spacing_blank_lines |
| P017 | 24 | punctuation |
| P018 | 19 | list_of_tables_figures_toc |
| P019 | 67 | page_numbering |
| P020 | 37 | capitalization_case |
| P023 | 15 | spacing_blank_lines |
| P024 | 12 | list_of_tables_figures_toc |
| P026 | 415 | font_format |
| P027 | 3 | heading_title |
| P028 | 16 | page_numbering |
| P029 | 14 | page_numbering |
| **Total** | **1,485** | |

### Aggregate by Category (all 5 files)

| Category | Total |
|---------|------:|
| page_numbering | 598 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| indentation | 39 |
| capitalization_case | 40 |
| spacing_blank_lines | 26 |
| list_of_tables_figures_toc | 31 |
| heading_title | 3 |
| punctuation | 21 |

---

## 4. Precision-Improvement Summary vs Prior Snapshot

Comparing against `after_p020_refinement_current_snapshot.md` (commit `96543ef`):

| File | Before | After | Change | Drivers |
|------|-------:|------:|-------:|---------|
| Cibaku Elson | 322 | 321 | −1 | P014: 1→0 |
| Yin H 2nd flat | 285 | 284 | −1 | P014: 1→0 |
| Yin Haotian 2nd | 350 | 349 | −1 | P014: 1→0 |
| Yin H 4th compressed | 555 | 477 | **−78** | P011: 150→70 (−80); P014: 10→0 (−10); P029: 0→12 (+12) |
| Sebastian Fine clean | 60 | 54 | −6 | P014: 6→0 (−6); P011: 14→12 (−2); P029: 0→2 (+2) |
| **Total** | **1,572** | **1,485** | **−87** | |

### P011 — Compression Artifact Guard

Groups where `affected_line_count ≥ 5` AND `worst_overflow < 8pt` are suppressed as
coordinate-shift artifacts. Impact:

| File | Before | After |
|------|-------:|------:|
| Yin H 4th compressed | 150 | 70 |
| Cibaku Elson | 21 | 21 |
| Yin Haotian 2nd / Yin H 2nd flat | 33 | 33 |
| Sebastian Fine | 14 | 12 |

### P014 — Text-Area Centering Fix

P014 now compares heading center against text-area center `(108 + 540) / 2 = 324pt` rather
than page center (306pt). NJIT's asymmetric margins shifted all correctly-centered headings
18pt right of page center, exceeding the 12pt tolerance and producing false positives.
P014 = 0 across all 5 evaluated files after the fix.

| File | Before | After |
|------|-------:|------:|
| Sebastian Fine | 6 | 0 |
| Yin H 4th compressed | 10 | 0 |
| Cibaku Elson | 1 | 0 |
| Yin Haotian 2nd / Yin H 2nd flat | 1 | 0 |

### P029 — Roman Numeral Sequence Ordering

New rule (PR #39). Flags `roman_sequence_repeat`, `roman_sequence_gap`, and
`roman_sequence_decrease` on front-matter pages with visible lowercase Roman numerals.

| File | P029 | Notes |
|------|-----:|-------|
| Yin H 4th compressed | 12 | All `roman_sequence_repeat` — known repeated pages in the compressed PDF |
| Sebastian Fine | 2 | Both `roman_sequence_decrease` with implausibly large expected values (901, 1001) — likely false positives from TOC page-reference text misclassified as Roman numerals |
| Others | 0 | No issues |

---

## 5. Clean Baseline Analysis (Sebastian Fine, 29 pages)

Total findings: **54** (down from 60 in prior snapshot).

| Rule | Count | Assessment |
|------|------:|-----------|
| P013 | 27 | Expected — page-number candidate detector is high-volume by design |
| P011 | 12 | Mix: 5 high-confidence bottom_margin (overflow 20–23pt), likely real; 2 low-confidence right_margin (3.0pt), borderline |
| P020 | 3 | 3 title-capitalization signals on page 3 — warrant manual check |
| P019 | 4 | Multiple/mixed page-number candidates on pages 13–14, sequence gap — possible real issue at body start |
| P029 | 2 | Both `roman_sequence_decrease` with expected values 901/1001 — likely false positives (non-Roman text misclassified) |
| P018 | 2 | TOC missing page number and inconsistent indent on page 9 — warrant manual check |
| P016 | 2 | Excessive paragraph/line gap on page 5 — possible real spacing issue |
| P017 | 1 | Missing caption terminal punctuation on page 19 — warrant manual check |
| P023 | 1 | Possible body text not double-spaced on page 28 — may be references section |

**Clean-baseline false-positive candidates:**
- P029 (2): Expected values of 901/1001 are clearly artifact — P029 is misclassifying
  non-Roman text near the front/body boundary. This is a known P029 limitation.
- P011 low-confidence (2): Right-margin overflow of exactly 3.0pt — borderline tolerance edge cases.
- P013 (27): By design; not a false positive in the error sense.

**Remaining likely real findings (clean baseline):**
- P011 high-confidence bottom_margin (5): Suggest figures or tables extending below the 1"
  bottom margin — possible real formatting issues even in a "clean" document.
- P020 (3), P017 (1), P018 (2): Warrant manual review but plausible on any document.

---

## 6. Recommended Next Development Bundles

Based on the current evidence:

| Priority | Task | Rationale |
|----------|------|-----------|
| 🟡 High | P029 false-positive triage | Expected values 901/1001 on Sebastian Fine indicate misclassification of body-page text as front-matter Roman numerals. Needs a stricter body-boundary guard. |
| 🟡 High | P013 grouping / noise reduction | 501 candidate findings across 5 files; hard to action individually. Grouping by zone + type + consecutive-page pattern would improve usability. |
| 🟡 Med | EF comment category-to-rule comparison | Map extracted EF comment categories to P-rule findings on a page basis to estimate precision/recall against expert feedback. |
| 🟡 Med | P011 high-confidence bottom_margin investigation | Clean-baseline shows high-confidence bottom_margin findings (22–23pt overflow). Investigate whether these are figures/tables or true text violations. |
| 🟡 Low | P020 font-size fallback for CMR-based PDFs | P020 still fires 0 on Yin 2nd (no bold metadata) except via CMBX detection. Font-size ≥13pt as supplementary trigger could improve recall. |

---

## 7. Limitations

- All findings are heuristic signals, not final NJIT compliance verdicts.
- P013 is a candidate detector by design; its high volume is expected.
- P026 font-family violations (415 total) may include Computer Modern (LaTeX default) which
  some departments accept.
- P029 is conservative but can produce false positives near the front/body page boundary.
- No OCR or scanned-PDF support.
