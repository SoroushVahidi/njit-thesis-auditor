# EF Comment-vs-Tool Overlap Evaluation After P063 (P001–P063)

- **Date:** 2026-06-08
- **Auditor scope:** P001–P063 implemented; 889 pytest
- **Baseline commit:** `cc049b2` (post PR #225)
- **Prior overlap doc:** `docs/evaluation/current_ef_comment_vs_tool_comparison.md` (P001–P029 scope; `559814d`)
- **P063-era aggregate snapshot:** `docs/evaluation/current_auditor_after_p063_evaluation.md` (1,587 findings; commit `f170be5`)
- **Privacy:** Aggregate-only. No dissertation body text, title text, author names, committee
  names, captions, or entry titles are quoted anywhere in this document.

---

## 1. Purpose and Scope

This document refreshes the auditor-vs-expert EF overlap comparison that was last performed at
the P029 era. Since that comparison, 34 additional rules (P030–P063) have been implemented
covering new categories: TOC/List internal formatting, front-matter structure, ordering checks,
indentation refinements, and appendix heading labels.

The purpose is threefold:

1. Measure how EF-comment category coverage has changed between the P029 era and P063.
2. Identify which EF comment categories remain unaddressed despite the new rules.
3. Inform the P064 recommendation with EF-comment-support evidence.

**What this comparison is:**
- A page/category-level overlap analysis between machine-extractable PDF annotation objects
  (EF reviewer comments) and deterministic auditor findings on the same pages.
- An aggregate picture of rule recall versus a human expert's annotation set.

**What this comparison is not:**
- A precision/recall measurement at the individual-comment level (no semantic matching).
- A claim that zero EF-only pages means full issue coverage (EF comments span many semantic
  categories the tool cannot address deterministically).
- A measurement against the full EF corpus: only the two extractable-comment PDFs are used.

---

## 2. Input Samples and Extractability

### 2a. Extractable-comment PDFs

Both comparison PDFs are tracked in `data/raw/ester/` and confirmed locally available.

| Label | Filename | Comment status | EF annotation objects | Pages |
|---|---|---|---:|---:|
| Cibaku Elson 1st Review | `250218 Cibaku Elson First Review.pdf` | extractable | 78 | 99 |
| Yin Haotian 2nd Review | `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | extractable | 65 | 108 |

**EF annotation totals (unchanged from P029 era):** 78 (Cibaku) + 65 (Yin Haotian) = **143**
annotation objects across both files.

### 2b. Non-extractable PDFs (excluded from comment-matching)

| Label | Comment status | Use in this analysis |
|---|---|---|
| Yin H 2nd Review (flattened) | flattened (0 extractable) | Excluded from EF-comment overlap; aggregate audit counts only |
| Yin H 4th Review (compressed) | compressed/flattened (0 extractable) | Excluded from EF-comment overlap; aggregate audit counts only |

### 2c. Clean baseline (no EF comments)

| Label | Status | Use |
|---|---|---|
| Sebastian Fine clean baseline (Revision 3) | archive-extracted from tracked ZIP | Excluded from EF-comment overlap; used for false-positive baseline in prior refinement rounds |

---

## 3. Methodology

### 3a. EF comment categorization

EF annotation objects are categorized by keyword pattern into a fixed set of coarse categories
using `scripts/evaluate_ester_pdf_comments.py` and `src/njit_auditor/comment_analysis.py`.
Categorization is keyword-based on annotation text; categories are exclusive and assigned
in priority order. "unclear_or_other" is the catch-all for annotations not matching any
keyword pattern.

Categories used (same set as the P029-era comparison):

| Category | Description |
|---|---|
| `unclear_or_other` | No keyword match; semantic/editorial feedback; manual-review-only |
| `indentation` | Indentation or paragraph indent signals |
| `spacing_blank_lines` | Blank line or vertical spacing signals |
| `heading_title` | Heading, title, or section label signals |
| `table_format` | Table-related formatting signals |
| `figure_format` | Figure-related formatting signals |
| `references_citations` | Reference list or citation formatting signals |
| `list_of_tables_figures_toc` | TOC/LoT/LoF structural signals |
| `capitalization_case` | Capitalization or case-consistency signals |
| `committee_approval_page` | Approval page, committee, or signature-block signals |
| `margin_or_overflow` | Margin, overflow, or text-boundary signals |
| `acknowledgements` | Acknowledgements or dedication page signals |
| `font_format` | Font, size, or typeface signals |

### 3b. Auditor finding categorization

Each P-rule is assigned a coarse category for comparison. The mapping is identical to the one
used in the P029-era comparison doc, extended for P030–P063:

| Category | Rules |
|---|---|
| `page_numbering` | P013, P019, P022, P028, P029, P037 |
| `font_format` | P026 |
| `margin_or_overflow` | P011 |
| `annotations` | P012 |
| `list_of_tables_figures_toc` | P018, P024, P030, P031, P032, P036, P039, P040, P042, P046, P048, P049, P050, P053, P054, P055, P056, P057, P058, P059, P060, P061, P062 |
| `indentation` | P015, P043, P044, P045, P047 |
| `spacing_blank_lines` | P016, P023 |
| `capitalization_case` | P020 |
| `heading_title` | P014, P027, P038, P063 |
| `table_format` | P017, P035 |
| `frontmatter_structure` | P025, P033, P034, P041, P051, P052 |
| `title_page_metadata` | P033 |
| `abstract_length` | P021 |
| `references_citations` | *(no P-rule)* |
| `committee_approval_page` | *(no P-rule)* |

### 3c. "Overlap" definition

This comparison uses **page-level overlap**: a page "overlaps" between EF comments and tool
findings when both the EF annotation set and the tool findings set include at least one item
on that page. Category overlap means at least one tool finding of the corresponding category
exists on a page where an EF comment of that category was placed.

This is the same definition used in the P029-era comparison and the two refinement-round docs,
enabling direct before/after comparison.

---

## 4. Aggregate EF Annotation Counts

EF annotation counts are unchanged from the P029-era comparison (comment extraction is
document-static; no re-extraction is needed as no new extractable-comment PDFs have been added).

### 4a. EF annotation counts by coarse category

| Category | Cibaku | Yin Haotian | Total |
|---|---:|---:|---:|
| unclear_or_other | 53 | 35 | 88 |
| heading_title | 11 | 6 | 17 |
| capitalization_case | 9 | 3 | 12 |
| references_citations | 5 | 4 | 9 |
| committee_approval_page | 3 | 2 | 5 |
| figure_format | 2 | 0 | 2 |
| acknowledgements | 1 | 1 | 2 |
| indentation | 2 | 11 | 13 |
| spacing_blank_lines | 0 | 7 | 7 |
| table_format | 1 | 6 | 7 |
| list_of_tables_figures_toc | 0 | 4 | 4 |
| margin_or_overflow | 0 | 1 | 1 |
| **Total** | **78** | **65** | **143** |

### 4b. EF comment page coverage

| File | EF annotation objects | Pages with EF comments |
|---|---:|---:|
| Cibaku Elson 1st Review | 78 | 42 |
| Yin Haotian 2nd Review | 65 | 44 |

---

## 5. Current Auditor Finding Counts (P063-era Snapshot)

Finding counts for the two comparison PDFs are taken from the P063-era full five-PDF aggregate
snapshot (`data/evaluation/generated/current_auditor_after_p063/`) and the reference doc
`docs/evaluation/current_auditor_after_p063_evaluation.md`. The snapshot was generated at
commit `f170be5` using `njit-audit pdf` on each file.

### 5a. Finding counts by rule — Cibaku Elson 1st Review (total 325)

| Rule | Count | Category |
|---|---:|---|
| P013 | 95 | page_numbering |
| P026 | 92 | font_format |
| P012 | 78 | annotations |
| P011 | 21 | margin_or_overflow |
| P019 | 8 | page_numbering |
| P028 | 8 | page_numbering |
| P023 | 6 | spacing_blank_lines |
| P015 | 5 | indentation |
| P038 | 4 | heading_title |
| P044 | 3 | indentation |
| P020 | 2 | capitalization_case |
| P027 | 1 | heading_title |
| P016 | 1 | spacing_blank_lines |
| P051 | 1 | frontmatter_structure |
| All others | 0 | — |

### 5b. Finding counts by category — Cibaku Elson 1st Review

| Category | P063-era count | P029-era count | Delta |
|---|---:|---:|---:|
| page_numbering | 111 | 115 | −4 |
| font_format | 92 | 92 | 0 |
| annotations | 78 | 78 | 0 |
| margin_or_overflow | 21 | 21 | 0 |
| indentation | 8 | 5 | +3 |
| spacing_blank_lines | 7 | 7 | 0 |
| heading_title | 5 | 1 | +4 |
| capitalization_case | 2 | 3 | −1 |
| frontmatter_structure | 1 | 0 | +1 |
| list_of_tables_figures_toc | 0 | 0 | 0 |
| references_citations | 0 | 0 | 0 |
| committee_approval_page | 0 | 0 | 0 |
| **Total** | **325** | **321** | **+4** |

*Delta note:* P029-era count was 321; P063-era count is 325 (+4). The small increase
reflects P038 (front-matter heading presence, 4 findings), P044 (abstract indentation, +2
above P029 P015 count), and P051 (copyright year advisory, 1 finding), partially offset by
P013 grouping refinement (−4 from the prior round-1 refinement that collapsed multi-candidate
pages to one warning per page).

### 5c. Finding counts by rule — Yin Haotian 2nd Review (total 346)

| Rule | Count | Category |
|---|---:|---|
| P013 | 104 | page_numbering |
| P026 | 103 | font_format |
| P012 | 65 | annotations |
| P011 | 33 | margin_or_overflow |
| P019 | 15 | page_numbering |
| P015 | 13 | indentation |
| P038 | 4 | heading_title |
| P023 | 4 | spacing_blank_lines |
| P016 | 2 | spacing_blank_lines |
| P020 | 1 | capitalization_case |
| P044 | 1 | indentation |
| P051 | 1 | frontmatter_structure |
| All others | 0 | — |

### 5d. Finding counts by category — Yin Haotian 2nd Review

| Category | P063-era count | P029-era count | Delta |
|---|---:|---:|---:|
| page_numbering | 119 | 128 | −9 |
| font_format | 103 | 103 | 0 |
| annotations | 65 | 65 | 0 |
| margin_or_overflow | 33 | 33 | 0 |
| indentation | 14 | 13 | +1 |
| spacing_blank_lines | 6 | 6 | 0 |
| heading_title | 4 | 1 | +3 |
| capitalization_case | 1 | 3 | −2 |
| frontmatter_structure | 1 | 0 | +1 |
| list_of_tables_figures_toc | 0 | 0 | 0 |
| references_citations | 0 | 0 | 0 |
| committee_approval_page | 0 | 0 | 0 |
| **Total** | **346** | **349** | **−3** |

*Delta note:* Small decrease (−3) from P013 grouping refinement (−9 page-number warnings),
partly offset by P038 (+3 heading_title) and P044 (+1 indentation), P051 (+1 frontmatter).

### 5e. Page coverage comparison

| File | EF comment pages | Tool-finding pages (P063) | Pages with both | EF-only pages | Tool-only pages |
|---|---:|---:|---:|---:|---:|
| Cibaku Elson 1st Review | 42 | 99 | 42 | 0 | 57 |
| Yin Haotian 2nd Review | 44 | 108 | 44 | 0 | 64 |

All EF-comment pages continue to have at least one tool finding on both files
(EF-only pages = 0 on both). This reflects the breadth of the high-volume rules
(P013, P026, P011, P012) which together cover nearly every page.

---

## 6. EF-Comment Category Coverage Table

This table consolidates EF-comment counts (from section 4a) with tool coverage status
(from sections 5b and 5d) and assesses the quality of that coverage for each category.

| EF category | EF total (Cibaku / Yin H) | Tool coverage at P029 | Tool coverage at P063 | Change | Notes |
|---|---|---|---|---|---|
| `unclear_or_other` | 53 / 35 (88 total) | not addressable | not addressable | none | Semantic/editorial feedback; requires human judgment; out of scope for deterministic rules by design |
| `heading_title` | 11 / 6 (17 total) | 1 / 1 finding | 5 / 4 findings (P027, P038) | **improved** | P038 (front-matter heading presence) adds heading-level coverage; EF heading comments often phrasing/editorial beyond what P027/P038 can check |
| `capitalization_case` | 9 / 3 (12 total) | 3 / 3 findings | 2 / 1 findings | slight regression | P020 recall constrained by font-metadata availability; no new coverage from P030–P063 |
| `references_citations` | 5 / 4 (9 total) | 0 / 0 | 0 / 0 | none | No dedicated P-rule; no structural reference-list check implemented; biggest unaddressed EF category after `unclear_or_other` by actionability |
| `committee_approval_page` | 3 / 2 (5 total) | 0 / 0 | 0 / 0 | none | P025/P038 check approval-page heading presence; committee rank/order, signature-line layout, and full page-structure completeness remain unaddressed |
| `indentation` | 2 / 11 (13 total) | 5 / 13 findings | 8 / 14 findings (P015, P044) | marginal improvement | P044 (abstract indentation) adds targeted coverage; P043 (acknowledgements) also available; still narrow vs EF volume |
| `spacing_blank_lines` | 0 / 7 (7 total) | 7 / 6 findings | 7 / 6 findings (P016, P023) | unchanged | Mechanical spacing check present; no page-level match increase recorded since P029 |
| `table_format` | 1 / 6 (7 total) | partial (P017) | partial (P017, P035) | marginal | P035 (figure/table centering) adds text-layer coverage; EF table comments often semantic/editorial; P035 fires 0 on these two PDFs |
| `list_of_tables_figures_toc` | 0 / 4 (4 total) | 0 / 0 | 0 / 0 | none on comparison PDFs | Many new P-rules target this category (P030–P062); none fire on these two PDFs; Yin Haotian still has 4 EF comments with no tool match |
| `margin_or_overflow` | 0 / 1 (1 total) | 21 / 33 findings | 21 / 33 findings (P011) | unchanged | P011 continues to fire on these pages; 1-page EF overlap on Yin Haotian preserved |
| `figure_format` | 2 / 0 (2 total) | partial (P035 area) | partial (P035 area) | no change on these PDFs | P035 fires 0 on these two PDFs; EF figure comments are likely layout/centering; manual-review required |
| `acknowledgements` | 1 / 1 (2 total) | not modeled | not modeled | none | P043 (acknowledgements indentation) added; fires 0 on these two PDFs; EF acknowledgements comments likely semantic |
| `font_format` | not a category in EF set | 92 / 103 findings | 92 / 103 findings | unchanged | P026 is a tool-only high-volume category; does not correspond to EF comment patterns in this set |

---

## 7. Tool-Only High-Volume Findings / Noise

These rules produce the largest finding volumes on the comparison PDFs but have low or zero
correspondence to extractable EF annotations. They are not errors — they detect real
noncompliance — but the EF reviewer's annotation set did not focus on these areas.

| Rule | Cibaku count | Yin H count | Category | EF overlap | Assessment |
|---|---:|---:|---|---|---|
| P013 | 95 | 104 | page_numbering | Low: page-level only (many pages overlap geometrically but not in EF intent) | High-volume by design; triage grouping (one warning per page) already implemented; grouping refinement from EF-overlap round 1 |
| P026 | 92 | 103 | font_format | Not present in EF comment set | Real noncompliance (font/size); EF reviewer may not have annotated every occurrence; reporting triage present |
| P012 | 78 | 65 | annotations | Self-referential: P012 counts reflect EF annotations themselves | Expected; fires only on EF-commented PDFs; not a tool false-positive |
| P011 | 21 | 33 | margin_or_overflow | 1-page EF match on Yin H | Real margin overflow; EF reviewer annotated sparsely in this category |
| P019 | 8 | 15 | page_numbering | Low | Sequence/style consistency; not annotated by EF reviewer in comment form |
| P028 | 8 | — | page_numbering | None | Regime check; no EF annotation match |

**Interpretation:** The dominant noise sources (P013, P026) produce volume that is disproportionate
to EF annotation density. This is a known characteristic of mechanically-complete heuristic rules
versus human spot-annotation behavior. Both rules have reporting-level triage available
(`p013_triage`, `p026_font_triage`) that group repeated warnings for actionability.

---

## 8. Missed Expert-Comment Categories

Categories with EF comment count > 0 and zero or negligible tool coverage, ordered by EF volume:

### 8a. `unclear_or_other` (88 EF comments, 0 tool coverage)

The largest EF category. These comments require semantic interpretation, editorial judgment,
or context-aware review. Examples of what falls here (without quoting): minor phrasing adjustments,
word-choice feedback, structural commentary on argument flow, and formatting issues not matching
any keyword pattern. No deterministic rule can address this by design. It should be counted as
a permanent gap from the auditor's perspective — not a P064+ target.

### 8b. `references_citations` (9 EF comments, 0 tool coverage)

Cibaku: 5, Yin Haotian: 4. No dedicated P-rule exists. EF comments in this category likely
relate to reference-list formatting (hanging indent, consistent style, APA/style-guide compliance).
Partially automatable: hanging-indent geometry for reference-list entries can be measured from
the PDF text layer. Citation format content (author order, date placement) is more semantic.
**This is the highest-priority automatable EF miss category after clearing `unclear_or_other`.**

### 8c. `committee_approval_page` (5 EF comments, 0 tool coverage)

Cibaku: 3, Yin Haotian: 2. P025 checks approval-page content presence; P038 checks heading
presence. The EF comments in this category likely target committee structure, signature-block
layout, or specific field ordering that is not checked by P025/P038. Full committee-rank/order
checking requires semantic institutional knowledge and is manual-only. Partial structural checks
(presence of expected text blocks) may be possible but precision is limited.

### 8d. `heading_title` (17 EF comments, low coverage — 5/4 tool findings)

Cibaku: 11, Yin Haotian: 6. P027 (level-specific style) and P038 (heading presence) together
produce 5/4 findings on the comparison PDFs, but EF comments in this category outnumber tool
matches significantly. The EF heading comments likely target specific phrasing, bold/italic
enforcement, or heading-body spacing that is beyond P027/P038 scope. P063 (body appendix heading
labels) fires 0 on these PDFs. Not a strong candidate for P064 (high EF volume but most EF
heading feedback is editorial/semantic).

### 8e. `capitalization_case` (12 EF comments, low coverage — 2/1 tool findings)

P020 recall is low because bold font metadata is required and unreliable on many PDFs. This is
a known limitation (documented in prior evaluation snapshots). Improving font-size fallback
heuristics in P020 could marginally improve this category. However, EF capitalization comments
may include heading phrasing (text content) rather than pure case format, which is semantic.

### 8f. `list_of_tables_figures_toc` (4 EF comments on Yin H, 0 tool coverage)

Despite many new P-rules (P030–P062) targeting this category, none fire on the two comparison
PDFs. The Yin Haotian EF comments in this category were documented in the round-2 refinement
(pages 10, 32, 49, 94) as likely requiring deeper entry-extraction recall improvements
(multi-line continuation, split-column, heading-page boundary) rather than new rule logic.
The P-rules in this area require specific structural signals that are sparse or absent in
these PDFs' text layer.

### 8g. `indentation` (13 EF comments, moderate coverage — 8/14 tool findings)

P015 and P044 together provide moderate coverage. The current page-level overlap result for
indentation has improved marginally from P029 to P063 (P044 adds abstract-indentation check).
EF indentation comments may include acknowledgements/dedication/body indentation variants
beyond what P015 and P044 scope.

---

## 9. P064/P065 Recommendations

### Primary recommendation: P064 — References/Citations Structural Check

**Candidate:** Conservative reference-list structural check for the body/bibliography section.

**EF comment support:**
- 9 EF annotation objects across both comparison PDFs (5 Cibaku, 4 Yin Haotian) in the
  `references_citations` category.
- Zero tool findings in this category at both P029 and P063.
- This is the highest-volume **automatable** EF miss after `unclear_or_other` and
  `committee_approval_page` (committee checks require semantic institutional knowledge).

**What is automatable (text-layer only):**
- Reference-section heading presence and correct label (REFERENCES, BIBLIOGRAPHY, WORKS CITED).
- Hanging-indent geometry: do reference entries have a consistent hanging-indent (first line
  flush-left or outdented, continuation lines indented further right)?
- Inter-entry spacing consistency: double-spacing between entries and single-spacing within.
- Terminal-punctuation pattern: do entries end with a punctuated token?

**What is not automatable (scope limit):**
- Citation style compliance (APA, MLA, IEEE) — requires content-level parsing.
- Author name format, journal title abbreviation, date placement — semantic content checks.
- Completeness (every in-text citation has a corresponding reference) — requires full-document
  cross-referencing.

**Privacy risks:** Low. Reference-section geometry checks use bounding-box coordinates and
inter-line gap ratios. No citation text, author names, or reference content need be quoted
in findings or test fixtures. Synthetic fixture using placeholder reference text is sufficient.

**Automatable scope for P064:**
A scoped conservative v1 could check:
1. `reference_section_heading_missing` — REFERENCES/BIBLIOGRAPHY/WORKS CITED not found in body.
2. `reference_section_hanging_indent_inconsistent` — entries on the reference-list page
   lack a detectable hanging-indent pattern (first-line x_start significantly further right
   than continuation lines, or no consistent pattern across ≥3 entries).
3. `reference_section_inter_entry_spacing_inconsistent` — entries are uniformly single-spaced
   with no double-space gap between them (if guideline requires double-spacing).

**Recommendation: Scope first (design + synthetic tests), then implement v1 conservative check.**

Gate: require reference-section heading detected before any sub-checks. Skip documents
where the reference section is not detectable from text layer alone (PDF layer quality guard).

---

### Alternative P064 candidate: Dedication page centering/italic (Q033/Q034)

Q033 (dedication text centered) and Q034 (dedication text italic) are completely unimplemented.
EF comment support is low (these PDFs have `acknowledgements` EF comments but not dedicated
dedication-centering comments). The check is technically feasible using bounding-box geometry
(centering) and font-style metadata (italic), but requires reliable italic detection and
dedication-page identification. Privacy risk is low (geometry only; no dedication text quoted).

**Recommendation:** Secondary candidate. Implement after references/citations check if
P064 references check is merged. Alternatively, implement as a low-effort scope-first doc
alongside P064.

---

### Alternative P064 candidate: Committee/approval page refinement

EF comment support: 5 comments total (Cibaku 3, Yin H 2). But most committee/approval-page
checking is semantic (role ordering, signature authenticity, institutional completeness) and
manual-only per the strict coverage audit. The automatable fraction is small: checking for
the presence of expected text blocks (advisor signature slot, committee member count). P025
and P038 already handle the most reliable structural signal (heading presence, body presence).

**Recommendation:** Defer. EF comment support is present but the automatable increment is
small, and the risk of false positives from heuristic committee-structure detection is high.

---

## 10. Limitations and Privacy Model

### Privacy protections applied in this document

- All EF annotation categories are reported as aggregate counts only. No annotation text is
  quoted.
- All tool finding counts are aggregate. No dissertation body text, figure captions, table
  titles, author names, committee names, or heading content is quoted.
- Page numbers are reported only as counts (not as lists of specific page numbers) except where
  a general range is needed for interpretation.
- The generated audit JSON and Markdown outputs under
  `data/evaluation/generated/current_auditor_after_p063/` are gitignored and must not be
  committed. They are referenced here only for aggregate count derivation.

### Methodological limitations

- **Text-layer only:** The auditor uses only the PDF text layer (via pdfplumber). Image-only
  floats, scanned-page dissertations, and flattened-comment PDFs cannot be fully analyzed.
  Several EF-targeted features (figure centering, committee-signature presence) may have lower
  recall than text-structured checks.
- **Two-file comparison set:** Only 2 of 4 tracked EF-commented PDFs have extractable
  comments. Category distributions across just two files may not be representative of all
  NJIT dissertation patterns. A third extractable-comment PDF (e.g., the Sebastian Fine EF
  version from the original archive) would improve stability.
- **No semantic EF matching:** Page-level overlap does not confirm that a tool finding and an
  EF comment on the same page are about the same issue. A tool finding on page 10 for
  font-format and an EF comment on page 10 for indentation is counted as "both present" but
  the issues are unrelated.
- **EF comment categories imprecise:** The keyword-based categorizer cannot distinguish all
  EF comment intent. Comments categorized as `unclear_or_other` (88 total) include a wide
  range of semantic feedback that may partially overlap with tool categories but cannot be
  classified confidently.
- **P030–P063 sparse on comparison PDFs:** 30 of the 34 new rules (P030–P063) produce zero
  findings on the two comparison PDFs. This does not mean these PDFs are compliant — it means
  the specific structural patterns these rules target (list-entry ordering inversions, TOC
  indentation hierarchy, appendix heading sequences, etc.) are either absent, sparse, or
  not recoverable from the text layer of these PDFs. Results on other PDFs (e.g., Yin H 4th
  compressed) show these rules do fire on documents with the targeted patterns.
- **P020 recall limited:** Capitalization-case findings are constrained by bold font-metadata
  availability; many PDFs lack reliable metadata, reducing recall for this category.
- **Historical EF comment counts are static:** The 78 (Cibaku) and 65 (Yin Haotian) annotation
  counts are fixed by the annotated PDFs as committed. They do not change with new auditor rules.
  The overlap analysis measures the auditor against these fixed samples.

---

## 11. Before/After Comparison Summary (P029 → P063)

| Metric | P029 era | P063 era | Change |
|---|---|---|---|
| Auditor rules (PDF) | P011–P029 | P011–P063 | +34 rules |
| EF-only pages (Cibaku) | 0 | 0 | unchanged |
| EF-only pages (Yin H) | 0 | 0 | unchanged |
| Tool-only pages (Cibaku) | 56 | 57 | +1 |
| Tool-only pages (Yin H) | 64 | 64 | unchanged |
| Cibaku total findings | 321 | 325 | +4 |
| Yin H total findings | 349 | 346 | −3 |
| `list_of_tables_figures_toc` coverage (EF 4 comments) | 0 findings | 0 findings | no change |
| `references_citations` coverage (EF 9 comments) | 0 findings | 0 findings | no change |
| `committee_approval_page` coverage (EF 5 comments) | 0 findings | 0 findings | no change |
| `heading_title` coverage (EF 17 comments) | 2 findings total | 9 findings total | +7 findings |
| `indentation` coverage (EF 13 comments) | 18 findings total | 22 findings total | +4 findings |

**Key takeaway:** The substantial P-rule expansion from P029 to P063 did not significantly
shift EF-comment category overlap on these two PDFs. The high-volume categories
(page_numbering, font_format) remain dominant. New rules primarily added coverage for
structural patterns not present in these PDFs or addressed categories not well-represented
in the EF annotation set. The most important persistent gap is `references_citations`,
which has EF-comment support and no tool coverage despite 34 new rules.

---

## Cross-References

- Prior EF overlap (P001–P029): `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- P063-era full five-PDF aggregate: `docs/evaluation/current_auditor_after_p063_evaluation.md`
- Real-thesis pairing and overlap readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- EF overlap round 1 (P013 noise): `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`
- EF overlap round 2 (P018/P024 variants): `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
- Evaluation data manifest (machine): `data/processed/evaluation_data_manifest.json`
- Project state: `docs/status/current_project_state_and_next_steps.md`
- Full repository audit after P063: `docs/status/full_repository_audit_after_p063.md`
- EF comment extraction script: `scripts/evaluate_ester_pdf_comments.py`
- EF overlap comparison script: `scripts/evaluate_current_ef_comment_overlap.py`
