# Expanded EF Feedback Dataset Evaluation

- Date: 2026-05-29
- Auditor version: P011–P020 (commit c094972 + evaluation branch)
- Branch: evaluate-expanded-ef-feedback-dataset

## Purpose

Evaluate the current PDF auditor (P011–P020) against all available
EF-commented dissertation files now organized under `data/raw/ester/`.
Goal: understand which rules fire, which are noisy, and which files are
most useful for future comparison with Ester's comments.

No dissertation body text is included in this document.

---

## Dataset Inventory

| File | Size | Category |
|------|------|----------|
| `250218 Cibaku Elson First Review.pdf` | 5.5 MB | Commented PDF — Elson Cibaku, 1st review |
| `260415 Yin H _2nd_review with EF Comments.pdf` | 16 MB | Commented PDF — H. Yin, 2nd review |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | 16 MB | Commented PDF — H. Yin (Haotian), 2nd review (variant) |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | 1.4 MB | Commented PDF — H. Yin, 4th review (compressed) |
| `260330_YESNO_audit_logic_matrix.xlsx` | 16 KB | Rule matrix — not a dissertation PDF |
| `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | 312 KB | Archive — clean dissertation (no annotations) |

### Files Evaluated (PDF audit + comment extraction)

All four EF-commented PDFs were evaluated successfully.

### Files Skipped

| File | Reason |
|------|--------|
| `260330_YESNO_audit_logic_matrix.xlsx` | XLSX rule matrix, not a dissertation PDF |
| `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | Zip archive; contains a PDF with no EF annotations — useful as a clean baseline but not an EF feedback file |

---

## Audit Findings by Rule (P011–P020)

All severities are WARNING. Counts are per-file finding totals.

| File | P011 | P012 | P013 | P014 | P015 | P016 | P017 | P018 | P019 | P020 | **Total** |
|------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|----------:|
| Cibaku Elson (1st, 250218) | 21 | 78 | 99 | 1 | 5 | 1 | 0 | 0 | 8 | 0 | **213** |
| Yin H (2nd, 260415) | 33 | 0 | 113 | 1 | 13 | 2 | 0 | 0 | 15 | 0 | **177** |
| Yin Haotian 2nd (variant) | 33 | 65 | 113 | 1 | 13 | 2 | 0 | 0 | 15 | 0 | **242** |
| Yin H 4th (compressed) | 150 | 0 | 149 | 10 | 8 | 4 | 23 | 17 | 25 | 30 | **416** |
| **TOTAL** | **237** | **143** | **474** | **13** | **39** | **9** | **23** | **17** | **63** | **30** | **1048** |

---

## Audit Finding Categories

| File | margin | annotations | page_num | heading | indent | spacing | caption | toc_list | capitalization | punctuation | table |
|------|-------:|------------:|---------:|--------:|-------:|--------:|--------:|---------:|---------------:|------------:|------:|
| Cibaku Elson (1st) | 21 | 78 | 107 | 1 | 5 | 1 | — | — | — | — | — |
| Yin H 2nd (260415) | 33 | 0 | 128 | 1 | 13 | 2 | — | — | — | — | — |
| Yin Haotian 2nd | 33 | 65 | 128 | 1 | 13 | 2 | — | — | — | — | — |
| Yin H 4th (comp.) | 150 | 0 | 174 | 10 | 8 | 4 | 17 | 17 | 30 | 17 | 6 |

---

## Extracted Comment Counts

| File | Extractable | Count | Subtypes |
|------|:-----------:|------:|---------|
| Cibaku Elson (1st, 250218) | Yes | 78 | Highlight: 78 |
| Yin H 2nd (260415) | No | 0 | — |
| Yin Haotian 2nd (variant) | Yes | 65 | Highlight: 64, Text: 1 |
| Yin H 4th (compressed) | No | 0 | — |

The two Yin 2nd-review files (260415 and Yin_Haotian) produce identical audit
counts, suggesting they are the same document. The 260415 version has no
extractable annotations; the Yin_Haotian version has 65 extractable highlights.

---

## Extracted Comment Categories (EF-Readable PDFs)

Categories are derived from `categorize_comment_text` keyword matching.
These are approximate — most highlights land in `unclear_or_other`.

| Category | Cibaku Elson (78 total) | Yin Haotian (65 total) |
|----------|------------------------:|----------------------:|
| unclear_or_other | 53 | 35 |
| heading_title | 11 | 6 |
| capitalization_case | 9 | 3 |
| references_citations | 5 | 4 |
| committee_approval_page | 3 | 2 |
| indentation | 2 | 11 |
| figure_format | 2 | — |
| spacing_blank_lines | — | 7 |
| table_format | 1 | 6 |
| list_of_tables_figures_toc | — | 4 |
| punctuation | — | 4 |
| margin_or_overflow | — | 1 |
| acknowledgements | 1 | 1 |

---

## High-Level Observations

### Rules That Fire Most Often

1. **P013** (page-number candidates): 474 total — highest by far. Expected;
   this is a candidate detector by design and will always be high-volume on
   multi-page dissertations.

2. **P011** (margins): 237 total. Consistently fires across all files. The
   compressed 4th-review PDF (150 findings) is an outlier — likely due to
   compression artifacts affecting layout geometry extraction. The other three
   files produce 21–33 findings, which is plausible for a long dissertation.

3. **P012** (annotations): 143 total, but only for the two PDFs with
   extractable annotation objects (78 and 65). Correctly correlates 1:1 with
   the actual extracted annotation count — a strong quality signal.

4. **P019** (page-number sequence): 63 total. Fires consistently, suggesting
   page-number style or position inconsistencies across all evaluated files.

### Rules with Low or Zero Firing

- **P017** (caption punctuation/case): fires only for the compressed 4th-review
  PDF (23 findings). The other three produce 0 — either captions are well-
  formatted or the text layer does not expose enough caption lines.

- **P018** (TOC/list alignment): fires only for compressed 4th-review (17
  findings). TOC content may not be reliably detected in other PDFs.

- **P020** (title capitalization): fires only for the compressed 4th-review
  (30 findings — 7 first_word, 23 major_word; 14 caption + 16 heading source).
  Produces 0 for others, likely because the text layer in those PDFs does not
  expose bold font metadata reliably, preventing heading detection.

- **P014** (front-matter heading style): fires consistently but at very low
  counts (1–10 per file). Suggests most front-matter headings are correctly
  placed, with the compressed file having more issues.

### Key File-Level Observations

**Cibaku Elson (1st review):**
- Only file with both many extractable comments (78) AND significant P012 count.
- EF comment categories suggest heading/capitalization and title issues are real
  (9 capitalization_case + 11 heading_title comments) — but P020 fires 0, and
  P014 fires 1. This is a potential gap.
- High `unclear_or_other` comment ratio (53/78) — most highlights are
  content-level feedback, not format-specific.

**Yin H 2nd (260415) vs Yin Haotian 2nd (variant):**
- Identical audit counts (P011–P019). Almost certainly the same document.
- The 260415 version has flattened/unextractable annotations (0 P012).
- The Haotian version has 65 extractable highlights (65 P012).
- Yin Haotian comment categories show: indentation (11), spacing (7), and
  table_format (6) are significant — matching the P015 (13) and P016 (2) signals.
  P016 may be under-counting spacing issues relative to EF feedback.

**Yin H 4th (compressed):**
- Highest finding count by far (416). Several possible explanations:
  1. The 4th review genuinely has more formatting issues than earlier reviews.
  2. PDF compression artifacts distort layout geometry, inflating P011/P013.
  3. The compressed PDF may have more text-layer content exposed (explaining
     why P017/P018/P020 fire here but not elsewhere).
- The 150 P011 findings are unusually high — warrants review of whether
  compression is causing spurious margin violations.
- 0 extractable annotations despite being labeled "with EF comments" — comments
  may have been flattened or embedded as PDF content rather than annotation objects.

### Rules That May Need Refinement

| Rule | Observation | Suggested Next Step |
|------|-------------|---------------------|
| P013 | Always high-volume; hard to action | Consider grouping by zone/page pattern to reduce noise |
| P011 | 150 on compressed file (outlier) | Investigate whether compression artifacts are triggering false margins |
| P020 | Bold font detection misses 3 of 4 PDFs | Explore font-size threshold as a supplementary heading signal |
| P016 | Under-counts spacing vs EF feedback | Expand from front-matter-only to body-page gaps |
| P017/P018 | Only activate on compressed file | May need caption/TOC detection tuning for other PDF types |

### Most Useful Files for Future Evaluation

| File | Why Useful |
|------|-----------|
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | 65 extractable highlights covering diverse categories; best for comment-vs-finding comparison |
| `250218 Cibaku Elson First Review.pdf` | 78 extractable highlights; strong heading/capitalization signal overlap with P014/P020 gap |
| `Dissertations with no Feedback (zip)` | Clean baseline (Sebastian Fine, Revision 3); useful for before/after comparison and false-positive rate estimation |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | Shows full auditor surface; useful for testing P017/P018/P020 — but verify compression artifacts first |

---

## Privacy / Content Note

- No dissertation body text was read, quoted, or reproduced.
- Extracted comment content was summarized only as category counts.
- Generated machine reports are stored under `data/evaluation/generated/`
  which is gitignored.
- Only this high-level summary document is committed.

---

## Recommended Next Steps

1. **P011 compression investigation:** Run P011 on the uncompressed Yin 4th-
   review PDF (when available) to determine whether the 150 findings reflect
   real issues or compression artifacts.

2. **P020 font signal fallback:** Add font-size-based heading detection as a
   fallback when bold metadata is unavailable, to capture headings in the
   Cibaku and Yin 2nd-review PDFs.

3. **P016 scope expansion:** Extend spacing checks from front-matter-only to
   include body pages, to better match the spacing feedback EF provides.

4. **Comment-to-finding alignment:** Use the Yin Haotian 2nd-review file
   (best comment coverage) for a deeper category-level alignment study between
   EF highlight categories and auditor rule categories.

5. **Clean baseline evaluation:** Extract the Sebastian Fine PDF from the zip
   in `data/raw/ester/` and run the auditor on it to estimate false-positive
   rates in a no-feedback document.

6. **Acquire more annotated data:** The large EF feedback archive (`ai-formatting-
   project.rar`) contains ~10 more annotated files not yet committed. Adding a
   subset would broaden the evaluation surface.
