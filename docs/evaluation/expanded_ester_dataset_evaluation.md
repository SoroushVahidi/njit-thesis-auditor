# Expanded Ester Dataset Evaluation

Historical evaluation against the full Ester shared-drive dataset after PR #285 merge.
All findings are aggregate counts and category labels only.
No dissertation body text, EF comment text, author names, or EF comment
prose is reproduced in this document.

---

## 1. Dataset Inventory

| # | File | Student | Round | Date | Format | Has EF comments | EF extractable | Audit as PDF | Notes |
|---|------|---------|-------|------|--------|-----------------|----------------|--------------|-------|
| 1 | `250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf` | Sebastian Fine | 1st | 2025-01 | PDF | Yes | Yes | Yes | |
| 2 | `250129 Kang, Qi EF comments.pdf` | Kang Qi | — | 2025-01 | PDF | Yes | Yes | Partial | Standalone EF comment PDF, no full dissertation text |
| 3 | `250204 Kang Qi PhD dissertation_1st review with EF comments.pdf` | Kang Qi | 1st | 2025-02 | PDF | Yes | Yes | Yes | |
| 4 | `250213 Pennock Andrew Revised 1st Dissertation Draft with EF comments.pdf` | Pennock Andrew | 1st | 2025-02 | PDF | Yes | Yes | Yes | |
| 5 | `250218 Cibaku Elson First Review.pdf` | Cibaku Elson | 1st | 2025-02 | PDF | Yes | Yes | Yes | |
| 6 | `250409 Sebastian.Fine 3rd Review Draft with EF comments.docx` | Sebastian Fine | 3rd | 2025-04 | DOCX | Yes | No | **No** | Not supported by PDF auditor |
| 7 | `250415 Termini_DoloresThirdReview with EF comments.pdf` | Termini Dolores | 3rd | 2025-04 | PDF | Yes | Partial | Yes | 27 StrikeOut + 21 Highlight; many annotations have no text |
| 8 | `250828 Aguado Alvaro 3rd Review Dissertation Draft with EF comments.docx` | Aguado Alvaro | 3rd | 2025-08 | DOCX | Yes | No | **No** | Not supported by PDF auditor |
| 9 | `260330_YESNO_audit_logic_matrix.xlsx` | — | — | 2026-03 | XLSX | No | N/A | No | Rule matrix, metadata only |
| 10 | `260415 Yin H _2nd_review with EF Comments.pdf` | Yin Haotian | 2nd | 2026-04 | PDF | Yes | **No** | Yes | EF annotations flattened into PDF rendering |
| 11 | `260428 Yin H 3rd review with EF Comments.pdf` | Yin Haotian | 3rd | 2026-04 | PDF | Yes | Yes | Yes | |
| 12 | `260430 Yin H 4th review with EF comments.pdf` | Yin Haotian | 4th | 2026-04 | PDF | Yes | **No** | Yes | EF annotations flattened into PDF rendering |
| 13 | `260528Luo M 3rd review with EF comments.pdf` | Luo M | 3rd | 2026-05 | PDF | Yes | Yes | Yes | |
| 14 | `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | Sebastian Fine | clean | 2026-05 | ZIP | No | N/A | No | Clean draft (Revision 3), no EF annotations |
| 15 | `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | Yin Haotian | 4th (compressed) | — | PDF | Yes | **No** | Yes | Same content as YH 4th; EF annotations flattened |
| 16 | `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | Yin Haotian | 2nd (variant) | — | PDF | Yes | Yes | Yes | Variant of YH 2nd; annotations NOT flattened |

**Auditable PDFs:** 12 (all PDFs except the standalone Kang Qi comment PDF is partial)  
**DOCX files (not auditable):** 2  
**ZIP:** 1 (contains one clean-draft PDF; EF comparison not applicable)  
**XLSX:** 1 (rule matrix, metadata only)

---

## 2. Files Audited / EF Annotations Extracted

| Tag | File (short) | Audit findings | EF annotations (total) | EF with text | Extractable? |
|-----|-------------|---------------|------------------------|--------------|--------------|
| SF | Sebastian Fine 1st | 122 | 58 | 53 | Yes |
| KQ_comments | Kang Qi comment PDF | 111 | 53 | 52 | Yes |
| KQ_1st | Kang Qi 1st review | 128 | 14 | 14 | Yes |
| PA | Pennock Andrew 1st | 439 | 58 | 49 | Yes |
| CE | Cibaku Elson 1st | 325 | 78 | 70 | Yes |
| TD | Termini Dolores 3rd | 458 | 49 | 22 | Partial |
| YH_2nd | Yin H 2nd (260415) | 281 | **0** | 0 | **Flattened** |
| YH_3rd | Yin H 3rd | 483 | 151 | 54 | Yes |
| YH_4th | Yin H 4th (260430) | 347 | **0** | 0 | **Flattened** |
| LM_3rd | Luo M 3rd | 432 | 36 | 33 | Yes |
| YH_4th_cmp | Yin H 4th compressed | 532 | **0** | 0 | **Flattened** |
| YH_2nd_v2 | Yin H 2nd variant | 346 | 65 | 47 | Yes |
| **Total** | | **4,004** | **562** | **394** | 9/12 |

---

## 3. Per-file Tool Finding Counts by Top Rules

| Tag | P012 | P013 | P026 | P011 | P019 | P015 | P020 | P028 | P023 | P038 | Other |
|-----|------|------|------|------|------|------|------|------|------|------|-------|
| SF | 58 | 25 | — | 11 | 5 | — | 3 | 2 | — | 2 | 16 |
| KQ_comments | 53 | 20 | 17 | 6 | 4 | — | — | — | 3 | 4 | 4 |
| KQ_1st | 14 | 43 | 39 | 11 | 6 | — | — | — | 5 | 4 | 6 |
| PA | 58 | 165 | 161 | 24 | 9 | 10 | — | — | 4 | 4 | 4 |
| CE | 78 | 95 | 92 | 21 | 8 | 5 | — | 8 | 6 | — | 12 |
| TD | 49 | 163 | 202 | — | 10 | 5 | — | 8 | 9 | 5 | 7 |
| YH_2nd | — | 104 | 103 | 33 | 15 | 13 | — | — | 4 | 4 | 5 |
| YH_3rd | 151 | 124 | 123 | 32 | 10 | 17 | — | 8 | — | 5 | 13 |
| YH_4th | — | 125 | 123 | 41 | 16 | 16 | 4 | 10 | — | 5 | 7 |
| LM_3rd | 36 | 156 | 126 | 46 | 25 | 9 | 8 | 10 | — | — | 16 |
| YH_4th_cmp | — | 133 | 117 | 70 | 25 | — | 30 | — | — | — | 157 |
| YH_2nd_v2 | 65 | 104 | 103 | 33 | 15 | 13 | — | — | 4 | 4 | 5 |

**P012** count = EF annotation object count (annotation-marker detection, by design).  
**P013/P026** dominate on full dissertations — body text line/paragraph spacing findings.

---

## 4. EF Category Breakdown (extractable text annotations only)

| Category | SF | KQ_c | KQ_1 | PA | CE | TD | YH_3rd | LM | YH_2nd_v2 | Total |
|----------|----|----|----|----|----|----|--------|-----|---------|-------|
| unclear_or_other | 25 | 35 | 12 | 23 | 45 | 17 | 31 | 9 | 17 | **214** |
| heading_title | 20 | 5 | 1 | 7 | 11 | 2 | 6 | 8 | 6 | **66** |
| capitalization_case | 2 | 11 | — | 5 | 9 | — | 5 | — | 3 | **35** |
| references_citations | 3 | 1 | — | 6 | 5 | 2 | 2 | — | 4 | **23** |
| indentation | — | — | — | 1 | 2 | — | 8 | 6 | 11 | **28** |
| figure_format | 2 | — | — | 6 | 2 | — | — | 4 | — | **14** |
| table_format | 1 | 1 | 1 | 5 | 1 | — | 2 | 4 | 6 | **21** |
| spacing_blank_lines | 2 | — | — | — | — | — | 2 | 1 | 7 | **12** |
| list_of_tables_figures_toc | — | — | — | 2 | — | 1 | 3 | — | 4 | **10** |
| punctuation | 1 | 1 | — | — | — | — | 2 | 7 | 4 | **15** |
| committee_approval_page | — | — | — | 2 | 3 | — | — | — | 2 | **7** |
| margin_or_overflow | 1 | 2 | 1 | — | — | — | — | 3 | 1 | **8** |
| acknowledgements | — | 1 | — | — | 1 | — | — | — | 1 | **3** |
| page_numbering | 1 | — | — | — | — | — | — | — | — | **1** |
| **Total** | 58 | 57 | 15 | 57 | 79 | 22 | 61 | 42 | 66 | **457** |

Note: category counts include multi-category matches; total may exceed `ef_with_text`.

**Key observation:** 46.8% of all EF comments with text fall into `unclear_or_other` — meaning the categorizer cannot map them to a structural rule. These represent semantic/content feedback that is difficult to automate.

---

## 5. Version-Chain Analysis

### Yin Haotian (most data — 4 review versions)

| Version | File | Audit total | P013 | P026 | P011 | EF annotations | EF extractable |
|---------|------|-------------|------|------|------|----------------|----------------|
| 2nd (260415) | YH_2nd | 281 | 104 | 103 | 33 | 0 | Flattened |
| 2nd (variant) | YH_2nd_v2 | 346 | 104 | 103 | 33 | 65 | Yes |
| 3rd | YH_3rd | 483 | 124 | 123 | 32 | 151 | Partial |
| 4th (260430) | YH_4th | 347 | 125 | 123 | 41 | 0 | Flattened |
| 4th (compressed) | YH_4th_cmp | 532 | 133 | 117 | 70 | 0 | Flattened |

**Observations:**
- P013/P026 (body-text line/paragraph spacing) remain nearly constant from 2nd to 4th review (103–125). The student is either not addressing these warnings or the dissertation's growing body text keeps regenerating them. These warnings likely include false positives in normal body text.
- P011 (font compliance) is stable at 33 from 2nd through 3rd, then jumps to 41/70 at the 4th review — possibly new content or formatting changes introduced new font-compliance issues.
- The 3rd review shows the highest EF annotation count (151), of which 54 had extractable text. EF's text comments skew toward `indentation` (8), `heading_title` (6), and `capitalization_case` (5) — issues that P043, P017/P019, and P020 partially cover.
- The 2nd review EF comments (YH_2nd_v2) lean toward `indentation` (11), `spacing_blank_lines` (7), and `list_of_tables_figures_toc` (4) — structural issues that P043 and P036/P013 partially address.

### Sebastian Fine (2 versions — 1st PDF, 3rd DOCX)

| Version | File | Audit total | P012 | EF annotations | EF extractable |
|---------|------|-------------|------|----------------|----------------|
| 1st (EF PDF) | SF | 122 | 58 | 58 | Yes |
| 3rd | 250409 *.docx | N/A | N/A | Unknown | **DOCX — not auditable** |

EF's text annotations on the 1st review skew toward `heading_title` (20 out of 53 categorized), suggesting heading level/capitalization issues were a primary concern. The tool finds P012=58 (annotation markers), P013=25 (body spacing), P011=11.

### Kang Qi (standalone comment PDF + 1st review)

| File | Audit total | P012 | P013/P026 | EF annotations |
|------|-------------|------|-----------|----------------|
| Comment PDF only | 111 | 53 | 20/17 | 53 |
| 1st review PDF | 128 | 14 | 43/39 | 14 |

The standalone EF comment PDF has 53 annotations; the 1st review dissertation has only 14 PDF annotations. The comment PDF likely contains all the specific highlight comments, while the 1st review PDF has fewer in-document markers. The 1st review's high P013/P026 (43/39) compared to its 14 EF annotations suggests many body-text formatting warnings are tool-only with no direct EF annotation counterpart.

### Cibaku Elson (single version)

122 tool findings that are not P012/P013/P026 include P028=8 (chapter heading style) and P019=8. EF's 78 annotations break down with `heading_title` (11), `capitalization_case` (9), `references_citations` (5). The tool partially covers heading and capitalization issues but references/citations gaps remain.

---

## 6. Major EF-Only Gaps

| Gap | EF comment evidence | Tool coverage | Reason blocked |
|-----|--------------------|--------------|--------------------|
| **Semantic citation/reference style** | `references_citations` in 6/9 files (23 total) | Structural check only (P064) | Style/semantic — cannot auto-detect APA vs. not |
| **Figure/table formatting** | `figure_format` + `table_format` in most files (35 total) | P023/P024 partial | Caption placement, style, numbering semantic issues |
| **Approval/committee page** | `committee_approval_page` in 3 files (7 total) | P068/P072 structural only | Committee member names/degrees not text-extractable on image pages |
| **Unclear/content feedback** | 214/457 categorizable = 46.8% uncategorizable | None | Semantic editing, content corrections — not automatable |
| **DOCX annotation access** | 2 DOCX files (Sebastian Fine 3rd, Aguado Alvaro 3rd) | **None** | PDF auditor cannot ingest DOCX |
| **Flattened EF annotations** | YH 2nd (260415), YH 4th (260430), YH 4th compressed | Cannot extract via PyMuPDF | EF comments baked into page rendering layer |

---

## 7. Whether P080 Is Justified

**Yes, one scoped P080 is justified.**

The most actionable finding from this evaluation is the DOCX gap. Two EF-annotated dissertation drafts (`250409 Sebastian.Fine 3rd Review Draft with EF comments.docx`, `250828 Aguado Alvaro 3rd Review Dissertation Draft with EF comments.docx`) are completely unauditable by the current tool. The existing five-PDF canonical dataset does not include any DOCX baseline, so this is a qualitative gap — not just EF overlap.

All other gaps are either:
- Semantic (not automatable without LLM)
- OCR-blocked (flattened EF annotations)
- Already covered by existing rules

---

## 8. Recommended P080 Scope

**Recommended: DOCX comment extraction / pre-flight reporting refinement**

Specifically:
- **Type:** Reporting refinement (not a detection rule)
- **Scope:** Add a `njit-audit docx-comments` subcommand (mirroring `pdf-comments extract`) that extracts tracked changes and comment metadata from DOCX files via `python-docx` or similar
- **Output:** JSON + Markdown report of comment counts by type (Comment, Tracked Insert, Tracked Delete), without reproducing comment text
- **Rationale:** Unlocks EF comment extraction from 2 currently-inaccessible files; complements the existing `pdf-comments` workflow
- **What it is NOT:** A full DOCX formatting auditor; does not replace PDF as the primary audit target

Alternative (lower priority):
- Detection rule targeting specific heading/indentation gaps identified from the `heading_title` (66) and `indentation` (28) EF category counts — but these are partially covered by P019/P020/P043 already

---

## 9. Validation Confirmation

- No source-code changes made during this evaluation
- `ruff check .` — clean
- `mypy src` — clean
- `pytest` — 1091 passed
- `next_project_added_rule_id` = P080 (reserved, unassigned)
- `p_rules_implemented` = P001–P079
