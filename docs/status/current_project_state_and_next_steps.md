# Current Project State and Next Steps

- Date: 2026-05-29
- Branch: `improve-pdf-report-grouped-summaries` (grouped summary pending PR)
- Latest main: `4e73c39` (P026 body font compliance)

---

## 1. Implemented Feature Summary

### TeX Source Audit (P001–P010)

| Module | Rule(s) | What It Does |
|--------|---------|-------------|
| `latex_risky_commands.py` | P001 | Detects risky manual formatting commands (`\vspace`, `\setlength`, etc.) |
| `latex_labels.py` | P002–P004 | Duplicate `\label`, whitespace in label names, unresolved `\ref`/`\eqref` |
| `latex_figures_tables.py` | P005–P007 | Missing `\caption`, missing `\label`, caption terminal punctuation |
| `latex_structure.py` | P008 | Required document structure commands present (TOC, abstract, LOT/LOF) |
| `latex_linters.py` | P009–P010 | chktex and lacheck integration (graceful skip if not installed) |
| `latex_abstract.py` | Q004–Q005 | Abstract forbidden words ("paper"/"article") and first-person pronouns |
| `latex_metadata.py` | Q006 | Graduation month validation (Aug/Dec/May) |
| `abstract.py` | P021 (TeX) | Abstract word count (PhD ≤350, MS ≤150) |

### PDF Layout Audit (P011–P025)

| Module | Rule(s) | What It Does |
|--------|---------|-------------|
| `pdf_margins.py` | P011 | Text crossing 1.5"/1" margin boundaries |
| `pdf_annotations.py` | P012 | Embedded PDF annotation objects |
| `pdf_page_numbers.py` | P013, P019 | Page-number candidate detection; sequence/style consistency |
| `pdf_headings.py` | P014 | Named front-matter heading layout (bold/all-caps/centered/near-top) for 7 headings |
| `pdf_indentation.py` | P015 | First paragraph flush-left; subsequent paragraphs indented |
| `pdf_spacing.py` | P016 | Spacing/blank-line gap checks (front-matter focused) |
| `pdf_captions.py` | P017 | Caption terminal punctuation; table-title no-period signal |
| `pdf_toc_alignment.py` | P018 | TOC/list entry alignment (leaders, page-number column, indentation hierarchy) |
| `pdf_abstract.py` | P021 (PDF) | Abstract word count via PDF text layer |
| `pdf_frontmatter_no_page_number.py` | P022 | No visible page number on Abstract, Title, Approval, Copyright pages |
| `pdf_body_spacing.py` | P023 | Body text double-spacing (line spacing ≥ 1.55× font size, conservative threshold) |
| `pdf_font_compliance.py` | P026 | Body font size ≈12pt and Times New Roman (or accepted equivalent) |
| `pdf_toc_list_formatting.py` | P024 | TOC L1 (ALL CAPS), L2 (title case), LoT (title case, no period), LoF (sentence case) |
| `pdf_frontmatter_structure.py` | P025 | Abstract body presence, title-page degree/institution, approval-page content, front-matter order |
| `pdf_title_capitalization.py` | P020 | L2 heading and table-title title-case via bold font metadata |

### Infrastructure

| Module | Purpose |
|--------|---------|
| `report_outputs.py` | JSON/Markdown report generation; `build_grouped_summary`, `compact_page_list` added for triage summaries |
| `cli.py` | CLI entry point for both TeX and PDF audit modes |
| `pdf_layout.py` / `pdf_loader.py` | PDF geometry extraction (pdfplumber) |
| `pdf_models.py` | Typed data models for pages, blocks, spans |
| `models.py` | `Finding` model (rule_id, severity, detail, page, location) |
| `report_outputs.py` | JSON and Markdown report generation |
| `report.py` | Report aggregation |
| `comment_analysis.py` | EF comment keyword categorization |
| `evaluation.py` | EF comment vs. tool-finding comparison helpers |
| `pdf_comments.py` | PDF annotation extraction and cleaning |
| `rule_loader.py` | Load and validate rule inventory JSON files |

**P022 is now implemented** in `pdf_frontmatter_no_page_number.py` on the `implement-p022-frontmatter-no-page-number` branch.

---

## 2. Rule Coverage Summary

| Category | Total | Implemented | Partial | Not Implemented | Manual-Only |
|----------|------:|:-----------:|:-------:|:--------------:|:-----------:|
| Q-rules (Q001–Q079) | 79 | 2 (Q004, Q005) | ~32 | ~23 | ~22 |
| P-rules (P001–P026) | 26 | 26 | — | — | — |

### Q-Rule Not-Implemented Clusters (automatable)

- **TOC/list internal formatting**: wrapping spacing (Q053–Q055, Q066–Q067, Q076–Q077), "(Continued)" headers (Q048, Q062, Q071), column headers bold/aligned (Q063–Q064, Q072–Q073)
- **Front-matter visual checks**: copyright page (Q009–Q011), dedication centering/italic (Q033–Q034), bio-sketch content (Q023–Q025, Q027–Q029)
- **Heading level distinctions**: L3 sentence case (Q051), L4/L5 period/italic enforcement
- **Page-number sequence**: Roman numeral tracking per named section (Q031, Q035, Q046, Q060)
- **Figure/table body checks**: figure centering, table placement (above/below detection)

---

## 3. Evaluation Summary

**EF PDFs tested (4 files):**

| File | Extractable Comments | Notes |
|------|:-------------------:|-------|
| `250218 Cibaku Elson First Review.pdf` | Yes (78 highlights) | Best overlap with heading/capitalization signals |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | Yes (65 highlights) | Best for indentation/spacing comparison |
| `260415 Yin H _2nd_review with EF Comments.pdf` | No (flattened) | Identical audit counts to Yin Haotian (same doc) |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | No (flattened) | Highest finding count — compression artifacts inflate P011 |

**P025 (current branch) result on all 4 EF files: 0 findings** — the nospace fallback correctly handles merged token encoding used by 3 of 4 PDFs.

**Biggest current noise sources:**
- P013 (page-number candidates): always very high-volume by design (~100–175 per file)
- P011 (margins): inflated on compressed PDFs (150 findings vs 21–33 on normal PDFs)
- P012 (annotations): correctly 1:1 with actual annotation count

**Biggest coverage gaps relative to EF feedback:**
- P020 (title capitalization): fires 0 on 3 of 4 PDFs — bold metadata absent in most PDFs; font-size fallback needed
- Page-number absence on named pages: EF flags these but no rule checks them specifically
- Cross-page title consistency: title spelling on title/abstract/approval — not automated

**Clean baseline**: `Dissertations with no Feedback` zip contains Sebastian Fine Revision 3 — useful for false-positive analysis. Not yet run against P022–P025.

---

## 4. Remaining Gaps (Prioritized)

### A. High-Priority Automatable Rules Still Missing

| Priority | Gap | Addresses | Complexity | Risk |
|----------|-----|-----------|:----------:|:----:|
| ✅ DONE | P022: Page-number absence on named front-matter pages | Q001, Q008, Q012, Q014 | — | — |
| ✅ DONE | P026: Font compliance (Times New Roman 12pt throughout body) | Guidelines requirement | — | — |
| 🔴 HIGH | P020 font-size fallback when bold metadata absent | P020 recall gap | Medium | Low-Med |
| 🟡 MED | L3/L4/L5 heading style enforcement | Q051; L4/L5 period/italic | Medium | Medium |
| 🟡 MED | Roman numeral sequence validation (front-matter sections) | Q022, Q031, Q035, Q046, Q060 | Medium | Medium |
| 🟡 MED | Figure/table centering check | Self-Assessment Sheet | Medium | Medium |
| 🟡 LOW | Copyright page identification and checks (Q009–Q011) | Q009–Q012 | High | High |
| 🟡 LOW | Multi-page TOC "(Continued)" heading | Q048, Q062, Q071 | Medium | Medium |

### B. Partial Rules Needing Refinement

| Rule | Issue | Suggested Fix |
|------|-------|--------------|
| P020 | Bold metadata absent in 3 of 4 tested PDFs; 0 findings | Add font-size ≥ 13pt as supplementary heading trigger |
| P011 | Compressed PDFs inflate margin findings (150 vs 21–33) | Add compression-detection guard or higher threshold for compressed PDFs |
| P013 | Always very high-volume; hard to action | Group by zone/page pattern; add summary-level output |
| P016 | Underrepresents body-page spacing issues vs EF feedback | Extend from front-matter focus to include body chapter pages |
| P025 | Nospace fallback covers only 6 degree forms | Extend degree pattern list; add coverage for edge-case NJIT abbreviations |

### C. Manual-Only Rules (22 total)

All in Approval Page (Q015–Q020) and Acknowledgements (Q037–Q042) sections. Require committee rank/affiliation parsing and semantic paragraph intent detection. Not practical without LLM-based analysis.

### D. Evaluation/Data Tasks

- Run clean baseline (Sebastian Fine zip) through current auditor to establish false-positive rate for P023–P025
- Build per-file precision/recall-style analysis mapping EF comment categories to rule IDs
- Add P022–P025 findings to the expanded EF feedback dataset evaluation doc once those rules are merged
- Investigate whether the Yin 4th review's inflated P011 count is truly compression artifacts (compare with uncompressed version if available)

---

## 5. Recommended Next Implementation Bundles

### Bundle 1 (DONE): P022 — Page-Number Absence on Named Pages
Implemented in `pdf_frontmatter_no_page_number.py`. 0 findings on all 4 EF PDFs.

### Bundle 2 (DONE): P026 — Font Compliance
Implemented in `pdf_font_compliance.py`. EF evaluation: 92–117 family warnings per document (all use CMR or Georgia), 0–1 size warnings. These are real noncompliance signals, not false positives.

### Bundle 3: P020 Font-Size Fallback
**Rationale:** 3 of 4 tested PDFs lack bold metadata, causing P020 to fire 0 on heading-rich documents with real title-case issues (confirmed by EF comments on Cibaku).  
**Q-rule basis:** Q049–Q050  
**Files to change:** `src/njit_auditor/rules/pdf_title_capitalization.py`  
**Tests:** Synthetic spans with no bold flag but large font size (≥13pt); verify no regression on body-text false positives  
**Risk:** Low-Medium — font size is more stable than bold flag; need body-text size threshold

### Bundle 3: P026 — Font Compliance (Times New Roman 12pt)
**Rationale:** The formatting guidelines explicitly require Times New Roman 12pt throughout body text. This is a top-level requirement that no current rule validates.  
**Q-rule basis:** Formatting Guidelines main requirement  
**Files to change:** New `pdf_font_compliance.py`; `project_added_rules.json`  
**Tests:** Synthetic spans with correct/incorrect font names and sizes  
**Risk:** Medium — embedded fonts may alias font names; need allowlist for TNR variants (TimesNewRoman, Times-Roman, NimbusRoman, etc.)

### Bundle 4: Heading Level 3–5 Style + P020 Level-Number Detection
**Rationale:** L3 (sentence case bold), L4/L5 (sentence case + period/italic) are unchecked. Also, using section numbering (X.x, X.x.x) to distinguish L2 from L3 in TOC and body would improve P020/P024 accuracy.  
**Q-rule basis:** Q051; `Titles Examples Level 1 to 5.docx`  
**Files to change:** `pdf_title_capitalization.py`, `pdf_toc_list_formatting.py`  
**Tests:** Numbered heading patterns; sentence-case detection; L4/L5 period enforcement  
**Risk:** Medium — sentence-case detection is tricky; need to suppress body text false positives

### Bundle 5: Clean Baseline False-Positive Audit + P022–P025 Evaluation Update
**Rationale:** The Sebastian Fine Revision 3 PDF (clean, no EF annotations) in the data zip has not been run through the current auditor. Establishing its false-positive counts for P021–P025 is essential before further refinement.  
**Q-rule basis:** N/A (evaluation task)  
**Files to change:** New evaluation doc in `docs/evaluation/`  
**Tests:** No new tests; running the CLI on the clean PDF  
**Risk:** None — read-only evaluation task

---

## 6. Validation Status (as of implement-p022-frontmatter-no-page-number branch)

| Check | Result |
|-------|--------|
| `python -m pytest` | ✅ 255 passed, 0 failed |
| `ruff check .` | ✅ All checks passed |
| `mypy src` | ✅ No issues in 40 source files |

---

## 7. Branch Readiness

The `improve-pdf-report-grouped-summaries` branch is **ready for PR** against main. All 255 tests pass, linting is clean, mypy is clean. Grouped summaries evaluated on Yin 4th review (463 findings, 6 high-volume rules correctly identified).

**Next PR after this merge:** Bundle 3 (P020 font-size fallback) to improve heading detection recall on PDFs without bold metadata.
