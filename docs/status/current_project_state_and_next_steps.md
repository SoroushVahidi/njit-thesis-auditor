# Current Project State and Next Steps

- Date: 2026-05-29
- Latest main: `443868c` (PR #39 — P029 Roman numeral sequence checks)

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

### PDF Layout Audit (P011–P028)

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
| `pdf_heading_levels.py` | P027 | Numbered heading level-specific style (L1 ALL CAPS, L2 Title Case, L3-5 Sentence case) |
| `pdf_page_numbering_regime.py` | P028 | Front-matter Roman / body Arabic page-numbering regime check |
| `pdf_roman_sequence.py` | P029 | Front-matter lowercase Roman numeral ordering (i, ii, iii...) |
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

---

## 2. Rule Coverage Summary

| Category | Total | Implemented | Partial | Not Implemented | Manual-Only |
|----------|------:|:-----------:|:-------:|:--------------:|:-----------:|
| Q-rules (Q001–Q079) | 79 | 2 (Q004, Q005) | ~38 | ~17 | ~22 |
| P-rules (P001–P029) | 29 | 29 | — | — | — |

### Q-Rule Not-Implemented Clusters (automatable)

- **TOC/list internal formatting**: wrapping spacing (Q053–Q055, Q066–Q067, Q076–Q077), "(Continued)" headers (Q048, Q062, Q071), column headers bold/aligned (Q063–Q064, Q072–Q073)
- **Front-matter visual checks**: copyright page (Q009–Q011), dedication centering/italic (Q033–Q034), bio-sketch content (Q023–Q025, Q027–Q029)
- **Heading level distinctions**: L3/L4/L5 partially addressed by P027; bold/italic enforcement still missing
- **Page-number sequence correctness**: Roman numeral value sequence (Q022, Q031, Q035, Q046, Q060 partially covered by P028 style check; actual sequence ordering not yet validated)
- **Figure/table body checks**: figure centering, table placement (above/below detection)
- **Cross-page title consistency**: title spelling across title/abstract/approval pages

---

## 3. Evaluation Summary

**EF PDFs tested (4 files):**

| File | Extractable Comments | Notes |
|------|:-------------------:|-------|
| `250218 Cibaku Elson First Review.pdf` | Yes (78 highlights) | Best overlap with heading/capitalization signals |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | Yes (65 highlights) | Best for indentation/spacing comparison |
| `260415 Yin H _2nd_review with EF Comments.pdf` | No (flattened) | Identical audit counts to Yin Haotian (same doc) |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | No (flattened) | Highest finding count — compression artifacts inflate P011 |

**Full evaluation (post P020 refinement):** See `docs/evaluation/after_p020_refinement_current_snapshot.md` for the current snapshot after PR #37 (CMBX heading detection). Prior full baseline: `docs/evaluation/current_auditor_after_p028_evaluation.md`.

**Summary counts across 4 EF PDFs (Yin H 4th compressed — highest volume):**

| Rule | Count | Notes |
|------|------:|-------|
| P011 | 150 | Inflated by compression artifacts on compressed PDF |
| P013 | 149 | Candidate detector; high volume by design |
| P026 | 117 | Font family violations (Georgia/Arial — real noncompliance) |
| P023 | 0 | Double-spacing appears correct in body |
| P025 | 0 | Front-matter structure correct |
| P022 | 0 | No stray page numbers on no-number pages |
| P028 | 8 | Mixed page-numbering regime (Arabic on front-matter, Roman on body) |
| P027 | 2 | Two L1 chapter headings not ALL CAPS |
| P024 | 12 | TOC/LoT/LoF capitalization/punctuation |

**Biggest current noise sources:**
- P013 (page-number candidates): always very high-volume by design
- P011 (margins): 70 findings on compressed PDF (down from 150 with artifact guard); 21–33 on normal PDFs
- P026 (font family): 92–117 warnings per document — real noncompliance but high volume

**Biggest coverage gaps relative to EF feedback:**
- P020 (title capitalization): fires 0 on 3 of 4 PDFs — bold metadata absent in most PDFs; font-size fallback still needed
- Cross-page title consistency: title spelling on title/abstract/approval — not automated
- TOC "(Continued)" headers: multi-page TOC not handled

**Clean baseline**: `Dissertations with no Feedback` zip contains Sebastian Fine Revision 3 — useful for false-positive analysis. Not yet run through the full P011–P028 auditor.

---

## 4. Remaining Gaps (Prioritized)

### A. High-Priority Automatable Rules Still Missing

| Priority | Gap | Addresses | Complexity | Risk |
|----------|-----|-----------|:----------:|:----:|
| ✅ DONE | P022: Page-number absence on named front-matter pages | Q001, Q008, Q012, Q014 | — | — |
| ✅ DONE | P026: Font compliance (Times New Roman 12pt body) | Guidelines requirement | — | — |
| ✅ DONE | P027: Heading level-specific style (L1/L2/L3-5) | Q051 | — | — |
| ✅ DONE | P028: Page-numbering regime (Roman/Arabic) | Q022, Q031, Q035, Q046, Q060 | — | — |
| ✅ DONE | P020 CMBX/font-size heading detection refinement | P020 recall; Q049–Q050 | — | — |
| 🟡 MED | Roman numeral sequence ordering (not just style) | Q022, Q031, Q035, Q046, Q060 | Medium | Medium |
| 🟡 MED | Figure/table centering check | Self-Assessment Sheet | Medium | Medium |
| 🟡 LOW | Copyright page identification and checks (Q009–Q011) | Q009–Q012 | High | High |
| 🟡 LOW | Multi-page TOC "(Continued)" heading | Q048, Q062, Q071 | Medium | Medium |

### B. Partial Rules Needing Refinement

| Rule | Issue | Suggested Fix |
|------|-------|--------------|
| P020 | Bold metadata absent in 3 of 4 tested PDFs; 0 findings | Add font-size ≥ 13pt as supplementary heading trigger |
| P011 | ~~Compressed PDFs inflate margin findings~~ | ✅ Done — artifact guard added (150 → 70 on compressed PDF; normal PDFs unchanged) |
| P013 | Always very high-volume; hard to action | Group by zone/page pattern; add summary-level output |
| P016 | Underrepresents body-page spacing issues vs EF feedback | Extend from front-matter focus to include body chapter pages |
| P025 | Nospace fallback covers only 6 degree forms | Extend degree pattern list; add coverage for edge-case NJIT abbreviations |

### C. Manual-Only Rules (22 total)

All in Approval Page (Q015–Q020) and Acknowledgements (Q037–Q042) sections. Require committee rank/affiliation parsing and semantic paragraph intent detection. Not practical without LLM-based analysis.

### D. Evaluation/Data Tasks

- Run clean baseline (Sebastian Fine zip) through current P011–P028 auditor to establish false-positive rates
- Build per-file precision/recall-style analysis mapping EF comment categories to rule IDs
- Investigate whether the Yin 4th review's inflated P011 count is truly compression artifacts
- Compare P028 findings on Cibaku Elson (Arabic on front-matter) against EF comments for corroboration

---

## 5. Recommended Next Implementation Bundles

### Bundle 1 (DONE): P022 — Page-Number Absence on Named Pages
### Bundle 2 (DONE): P026 — Font Compliance
### Bundle 3 (DONE): P027 — Heading Level Style
### Bundle 4 (DONE): P028 — Page-Numbering Regime

### Bundle 5 (DONE): P020 CMBX/Font-Size Heading Detection Refinement
CMBX (Computer Modern Bold) now recognized as bold at layout extraction layer.
Font-size fallback added for non-bold large-font headings.
See `docs/evaluation/phase2_p020_heading_detection_refinement_evaluation.md`.

### Bundle 6: Roman Numeral Sequence Ordering (P029) — IMPLEMENTED
**Summary:** P029 was added to conservatively validate visible lowercase Roman numeral ordering across front-matter pages. It flags repeats, decreases, and non-consecutive visible numerals while excluding recognized no-number pages (ABSTRACT, APPROVAL PAGE, etc.).
**Q-rule basis:** Q022, Q031, Q035, Q046, Q060
**Files changed:** `src/njit_auditor/rules/pdf_roman_sequence.py`, CLI integration, inventory and tests
**Risk:** Medium — heuristic, conservative checks; does not replace manual review.

### Bundle 7: P011 Compression Artifact Guard — IMPLEMENTED
**Summary:** Added a group-level artifact guard to P011. Groups with ≥5 lines all within 8pt of
the margin are suppressed as compression-coordinate artifacts. Reduced P011 from 150 → 70 on
the compressed Yin H 4th PDF while leaving all normal-PDF counts unchanged (21–33).
Added `confidence` (low/medium/high) to P011 finding details.
**Files changed:** `src/njit_auditor/rules/pdf_margins.py`, tests, evaluation and status docs.
**Risk:** Low — conservative threshold; does not affect normal PDFs.

### Bundle 8: Clean Baseline False-Positive Audit (evaluation task)
**Rationale:** The Sebastian Fine Revision 3 PDF (clean, no EF annotations) has not been run through the full P011–P028 auditor. Establishing false-positive counts is essential before further refinement.  
**Risk:** None — read-only evaluation task

---

## 6. Validation Status (main at 263529c)

| Check | Result |
|-------|--------|
| `python -m pytest` | ✅ 304 passed, 0 failed (after PR #37) |
| `ruff check .` | ✅ All checks passed |
| `mypy src` | ✅ No issues in 42 source files |

**Next recommended PR:** Bundle A (P029 Roman numeral sequence ordering) or Bundle B (P011 compression artifact guard). See `docs/evaluation/after_p020_refinement_current_snapshot.md`.
