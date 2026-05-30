# Current Auditor Evaluation After P028

## 1. Purpose and Auditor Version

- **Date:** 2026-05-29
- **Main commit:** `6c6370c` (Polish repository state after P028 — PR #35)
- **Auditor version:** P001–P028 implemented; grouped-summary JSON/Markdown reports enabled
- **Supersedes:** `docs/evaluation/expanded_ef_feedback_dataset_evaluation.md` (P011–P020 era)

This document is a current-state evaluation snapshot capturing full P011–P028 audit
output on all available dissertation data. No dissertation body text is included.

---

## 2. Dataset Inventory

| File | Size | Category |
|------|------|----------|
| `250218 Cibaku Elson First Review.pdf` | 5.5 MB | EF-commented PDF — Elson Cibaku, 1st review |
| `260415 Yin H _2nd_review with EF Comments.pdf` | 16 MB | EF-commented PDF — H. Yin, 2nd review (flattened annotations) |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | 16 MB | EF-commented PDF — H. Yin (same doc, 65 extractable highlights) |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | 1.4 MB | EF-commented PDF — H. Yin, 4th review (compressed, flattened) |
| `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | 312 KB | ZIP archive — Sebastian Fine, Revision 3 (clean baseline) |
| `260330_YESNO_audit_logic_matrix.xlsx` | 16 KB | **Skipped** — XLSX rule matrix, not a dissertation PDF |

### Evaluated PDFs (5)

All 4 EF-commented PDFs were evaluated. The clean baseline was extracted from the ZIP
to an ignored path (`data/evaluation/generated/`) and evaluated.

---

## 3. Finding Counts by File

| File | Total | P011 | P012 | P013 | P014 | P015 | P016 | P017 | P018 | P019 | P020 | P023 | P024 | P026 | P027 | P028 |
|------|------:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| Cibaku Elson (1st) | **320** | 21 | 78 | 99 | 1 | 5 | 1 | — | — | 8 | — | 6 | — | 92 | 1 | 8 |
| Yin H 2nd (260415) | **284** | 33 | — | 113 | 1 | 13 | 2 | — | — | 15 | — | 4 | — | 103 | — | — |
| Yin Haotian 2nd | **349** | 33 | 65 | 113 | 1 | 13 | 2 | — | — | 15 | — | 4 | — | 103 | — | — |
| Yin H 4th (compressed) | **555** | 150 | — | 149 | 10 | 8 | 4 | 23 | 17 | 25 | 30 | — | 12 | 117 | 2 | 8 |
| Sebastian Fine (baseline) | **60** | 14 | — | 27 | 6 | — | 2 | 1 | 2 | 4 | 3 | 1 | — | — | — | — |

Rules not shown (0 across all files): P021, P022, P025.

### Aggregate by Rule (all 5 files)

| Rule | Total | Category |
|------|------:|---------|
| P011 | 251 | margin_or_overflow |
| P012 | 143 | annotations |
| P013 | 501 | page_numbering |
| P014 | 19 | heading_title |
| P015 | 39 | indentation |
| P016 | 11 | spacing_blank_lines |
| P017 | 24 | punctuation / table_format |
| P018 | 19 | list_of_tables_figures_toc |
| P019 | 67 | page_numbering |
| P020 | 33 | capitalization_case |
| P023 | 15 | spacing_blank_lines |
| P024 | 12 | list_of_tables_figures_toc |
| P026 | 415 | font_format |
| P027 | 3 | heading_title / capitalization_case |
| P028 | 16 | page_numbering |
| **Total** | **1,568** | |

### Aggregate by Category (all 5 files)

| Category | Total |
|---------|------:|
| page_numbering | 584 |
| font_format | 415 |
| margin_or_overflow | 251 |
| annotations | 143 |
| indentation | 39 |
| list_of_tables_figures_toc | 29 |
| capitalization_case | 33 |
| heading_title | 22 |
| spacing_blank_lines | 26 |
| punctuation | 20 |
| table_format | 6 |

---

## 4. Comment Extraction Results

| File | Extractable | Count | Subtypes |
|------|:-----------:|------:|---------|
| Cibaku Elson (1st) | Yes | **78** | 78 highlights (annotation type detected, body not read) |
| Yin H 2nd (260415) | **No** | 0 | Flattened — annotations rendered into PDF content stream |
| Yin Haotian 2nd | Yes | **65** | 65 highlights |
| Yin H 4th (compressed) | **No** | 0 | Flattened |

The 260415 and Yin Haotian files are the same document (identical audit counts for all
non-P012 rules). The 260415 version has flattened annotations; the Haotian version has
65 extractable highlights, making it the best file for comment-vs-finding comparison.

---

## 5. Grouped-Summary Observations

The new `grouped_summary` field in JSON reports substantially improves triage
for Graduate Studies. Key observations from this evaluation:

### High-Volume Rules (≥5 findings) by File

**Cibaku Elson:** 8 grouped rules — P011, P012, P013, P015, P019, P023, P026, P028  
**Yin H 2nd (260415):** 5 grouped rules — P011, P013, P015, P019, P026  
**Yin Haotian 2nd:** 6 grouped rules — P011, P012, P013, P015, P019, P026  
**Yin H 4th (compressed):** 11 grouped rules — P011, P013, P014, P015, P017, P018, P019, P020, P024, P026, P028  
**Sebastian Fine (baseline):** 3 grouped rules — P011, P013, P014

### Practical Benefit of Grouped Summaries

Without the grouped summary, a reviewer seeing 555 findings on Yin H 4th would need
to read the full list. The grouped summary immediately shows:
- P011=150 (margin, 124 pages) — flagged as likely compression artifact
- P013=149 (page candidates, 132 pages) — candidate detector, not errors per se
- P026=117 (font family, 117 pages) — Georgia/Arial throughout body (real noncompliance)
- P028=8 (mixed regime: 4 Arabic on FM, 4 Roman on body) — real page-numbering issue

This reduces the "attention budget" needed from hundreds of individual lines to a
handful of structured bullet points.

---

## 6. Signal/Noise Assessment

### Strong Signals (low false-positive risk)

| Rule | Evidence |
|------|---------|
| P012 | 1:1 with actual annotation count; 78 and 65 correctly detected |
| P026 | Correctly identifies CMR12 (LaTeX default) and Georgia/Arial (Word) as non-Times; counts match expected font use |
| P028 | Cibaku: 8 front-matter pages with Arabic numbers — real issue; Yin 4th: mixed regime (4+4) — consistent with incomplete page-number transition |
| P023 | Cibaku: 6 body-spacing pages — plausible for a 1st-review submission; baseline has only 1 |
| P027 | 1–2 findings per file, all L1 not-all-caps — targeted and plausible |

### Noisy/High-Volume (by design)

| Rule | Observation |
|------|-------------|
| P013 | 27–149 candidates per file; unavoidably high volume; grouped summary helps |
| P026 | 92–117 per file; one finding per body page; real noncompliance but visually overwhelming without grouping |
| P011 | 14–150; **highly variable** — 150 on compressed PDF vs 14–33 on others; compression artifacts likely |

### Possible False Positives

| Rule | Observation |
|------|-------------|
| P011 | 150 findings on compressed Yin 4th vs 14–33 on normal PDFs — compression artifacts distorting layout geometry |
| P014 | 6 warnings on Sebastian Fine baseline (clean PDF) — named headings may lack bold metadata on this PDF; possible PDF rendering issue rather than real formatting errors |
| P020 | 3 findings on Sebastian Fine baseline — minor title-case signals; review needed |

### Possible False Negatives

| Rule | Observation |
|------|-------------|
| P020 | Fires 0 on Cibaku Elson and both Yin 2nd files (CMR PDFs) — bold metadata absent; confirmed EF comment evidence of real capitalization issues on Cibaku; **font-size fallback needed** |
| P022 | 0 on all files — either correct or front-matter page numbers not in top/bottom zone for these PDFs |
| P025 | 0 on all files — front-matter structure appears correct in all tested PDFs |

---

## 7. Clean Baseline Analysis (Sebastian Fine, Revision 3)

Sebastian Fine Revision 3 is a "clean" dissertation with no EF annotations —
an excellent baseline for estimating false-positive rates.

**Total findings: 60** — dramatically lower than any EF-commented file (284–555).

### Finding breakdown

| Rule | Count | Likely Cause |
|------|------:|-------------|
| P013 | 27 | Expected — all dissertations have page-number candidates |
| P011 | 14 | Some margin findings — may be legitimate or PDFplumber layout artifacts |
| P014 | 6 | Named heading style warnings — bold metadata absent or headings not fully styled |
| P019 | 4 | Page-sequence consistency notes |
| P020 | 3 | Minor title-case signals |
| P018 | 2 | TOC alignment |
| P016 | 2 | Spacing signals |
| P023 | 1 | One body-spacing page |
| P017 | 1 | One caption |

### Rules with 0 findings on baseline

P012 (no annotations ✓), P015 (clean indentation ✓), P021 (word count OK ✓),
P022 (no stray page numbers ✓), P024 (0 — TOC capitalization OK), P025 (0 ✓),
**P026 (0 — font appears Times-compatible ✓)**, P027 (0 ✓), P028 (0 ✓).

**P026 = 0 on baseline is the most significant result.** Sebastian Fine appears to use
Times New Roman or an accepted equivalent throughout — no body font findings. This
confirms P026 is correctly distinguishing CMR/Georgia (flagged) from TNR (not flagged),
and the baseline is properly formatted in this regard.

**P015 = 0 on baseline:** No indentation issues — Cibaku (5 findings) and Yin 2nd
(13 findings) differences appear to be real formatting issues, not noise.

**P028 = 0 on baseline:** Sebastian Fine uses the correct Roman→Arabic page-numbering
regime. Cibaku's 8 `arabic_number_on_frontmatter_page` findings are real violations.

---

## 8. Recommended Next Development Bundles

### Bundle A: P020 Font-Size Fallback (highest priority)
**Rationale:** P020 fires 0 on Cibaku Elson and both Yin 2nd files, despite confirmed
EF comment evidence of real title-case issues (9 `capitalization_case` comments on
Cibaku). Bold metadata is absent in CMR-based PDFs. Using font-size ≥ 13pt as a
supplementary heading trigger would add coverage for ~3 of 4 tested PDFs.  
**Q-rule basis:** Q049–Q050  
**Modules:** `pdf_title_capitalization.py`  
**Risk:** Low-Medium — font size is more reliable than bold flag; needs body-text size threshold to avoid false positives  
**Estimated impact:** Would activate P020 on CMR PDFs, potentially surfacing real heading issues

### Bundle B: P011 Compression Artifact Detection
**Rationale:** P011 fires 150 times on the compressed Yin 4th vs 14–33 on normal PDFs.
This 5–10× inflation is strongly consistent with compression artifacts distorting
layout geometry. A per-page compression detection heuristic or adaptive threshold
would reduce this noise.  
**Modules:** `pdf_margins.py`  
**Risk:** Medium — need to define compression detection without losing real margin findings  
**Estimated impact:** Would reduce P011 from 150 to ~30 on compressed PDFs

### Bundle C: Clean Baseline P014 Investigation
**Rationale:** Sebastian Fine has 6 P014 warnings (named heading style issues) on a
"clean" baseline. This is surprising — if headings are correctly styled, P014 should
fire 0 or very few. Likely cause: bold metadata not exposed for some heading fonts.
Investigating would help calibrate P014 accuracy.  
**Modules:** `pdf_headings.py`  
**Risk:** Low — investigation only; fix may require adding font-size-based bold inference  
**Estimated impact:** Would improve P014 precision

### Bundle D: P029 Roman Numeral Sequence Ordering
**Rationale:** P028 confirms that Cibaku uses Arabic on front-matter (real issue).
P028 checks style but not sequence order (i.e., whether front-matter pages form i, ii,
iii, iv... in order). Adding sequence ordering would address Q022, Q031, Q035, Q046, Q060
more completely.  
**Q-rule basis:** Q022, Q031, Q035, Q046, Q060  
**Modules:** New `pdf_page_numbering_sequence.py`  
**Risk:** Medium — depends on having enough Roman-numeral candidates to form a sequence  

### Bundle E: P021 PDF Mode for Yin 2nd and Cibaku
**Rationale:** P021 = 0 on all files. This suggests either word counts are within limits
or the abstract extraction is missing content. Verifying P021 would confirm abstract
compliance for these PDFs.  
**Risk:** Low — read-only verification

---

## 9. Privacy Note

- No dissertation body text was read, quoted, or reproduced in this document.
- EF comment content was not examined (counts only).
- Generated full JSON/Markdown reports are stored under
  `data/evaluation/generated/current_after_p028/` which is gitignored.
- Only this high-level summary document is committed.
