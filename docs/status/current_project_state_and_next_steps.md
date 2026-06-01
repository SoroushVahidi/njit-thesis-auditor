# Current Project State and Next Steps

- **Date:** 2026-06-01
- **Latest main:** `179e247` (PR #68 — P034 evaluation refresh; P001–P034 implemented)
- **Validation:** 383 pytest passed (ruff, mypy, pytest)
- **Auditor scope:** P001–P034 implemented; full Q001–Q079 / guideline source coverage is **not** complete

- Strict coverage audit (historical baseline P029; updates through P034): `docs/status/source_to_implementation_coverage_after_p029.md`
- Data inventory: `docs/status/data_inventory_and_evaluation_sources.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
- **Current full-auditor snapshot (P001–P034 PDF):** `docs/evaluation/current_auditor_after_p034_evaluation.md` (1,446 findings across five PDFs)
- **P013 reporting triage:** `docs/evaluation/p013_reporting_actionability_refinement.md` — dedicated `p013_triage` rollup + Markdown section (raw P013 counts unchanged)
- Historical full-auditor snapshot (P001–P029): `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`
- Historical EF overlap study (P001–P029 scope): `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- EF-overlap refinement notes: `docs/evaluation/ef_overlap_driven_refinement_notes.md`
- EF-overlap refinement evaluation: `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`
- EF-overlap round2 notes: `docs/evaluation/ef_overlap_refinement_round2_notes.md`
- EF-overlap round2 evaluation: `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
- P030 synthetic validation: `docs/evaluation/p030_toc_continued_heading_synthetic_validation.md`
- P030 current-dataset evaluation: `docs/evaluation/p030_current_dataset_evaluation.md`
- P031 synthetic validation: `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md`
- P031 current-dataset evaluation: `docs/evaluation/p031_current_dataset_evaluation.md`
- P031 Sebastian clean-baseline investigation: `docs/evaluation/p031_sebastian_clean_baseline_investigation.md`
- P032 synthetic validation: `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md`
- P032 current-dataset evaluation: `docs/evaluation/p032_current_dataset_evaluation.md` (refreshed after PR #59; 0 P032 on all evaluated PDFs)
- P032 Yin H 4th page-15 investigation: `docs/evaluation/p032_yin_h_4th_page15_investigation.md`
- P033 synthetic validation: `docs/evaluation/p033_title_consistency_synthetic_validation.md`
- P033 current-dataset evaluation: `docs/evaluation/p033_current_dataset_evaluation.md` (refreshed after PR #63; 0 P033 findings; comparison runs on 2/5 files)
- P033 candidate-extraction recall investigation: `docs/evaluation/p033_candidate_extraction_recall_investigation.md`
- P034 synthetic validation: `docs/evaluation/p034_copyright_page_synthetic_validation.md`
- P034 current-dataset evaluation: `docs/evaluation/p034_current_dataset_evaluation.md` (refreshed after PR #67; 0 P034 findings on 5/5 files)
- P034 author-mismatch investigation: `docs/evaluation/p034_author_mismatch_investigation.md`

### P030–P034 evaluation docs (chronological)

| Order | Doc | Type |
|---:|---|---|
| 1 | `docs/evaluation/p030_toc_continued_heading_synthetic_validation.md` | Synthetic |
| 2 | `docs/evaluation/p030_current_dataset_evaluation.md` | Current dataset |
| 3 | `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md` | Synthetic |
| 4 | `docs/evaluation/p031_current_dataset_evaluation.md` | Current dataset |
| 5 | `docs/evaluation/p031_sebastian_clean_baseline_investigation.md` | Investigation |
| 6 | `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md` | Synthetic |
| 7 | `docs/evaluation/p032_current_dataset_evaluation.md` | Current dataset |
| 8 | `docs/evaluation/p032_yin_h_4th_page15_investigation.md` | Investigation |
| 9 | `docs/evaluation/p033_title_consistency_synthetic_validation.md` | Synthetic |
| 10 | `docs/evaluation/p033_current_dataset_evaluation.md` | Current dataset |
| 11 | `docs/evaluation/p033_candidate_extraction_recall_investigation.md` | Investigation |
| 12 | `docs/evaluation/p034_copyright_page_synthetic_validation.md` | Synthetic |
| 13 | `docs/evaluation/p034_current_dataset_evaluation.md` | Current dataset |
| 14 | `docs/evaluation/p034_author_mismatch_investigation.md` | Investigation |

**Privacy:** All evaluation docs are aggregate-only. Do not quote dissertation body text, title text, or author names. Generated audit JSON/MD outputs stay under gitignored `data/evaluation/generated/`.

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

### PDF Layout Audit (P011–P034)

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
| `pdf_toc_continued_headings.py` | P030 | Multi-page TOC/LoT/LoF continued-heading checks |
| `pdf_lot_lof_column_headers.py` | P031 | LoT/LoF column header label checks |
| `pdf_toc_list_wrapped_spacing.py` | P032 | Wrapped TOC/LoT/LoF entry internal spacing checks |
| `pdf_title_consistency.py` | P033 | Cross-page front-matter title consistency checks |
| `pdf_copyright_page.py` | P034 | Copyright Page top-margin header; year/author consistency with Title Page |
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
| P-rules (P001–P034) | 34 | 34 | — | — | — |

### Q-Rule Not-Implemented Clusters (automatable)

- **TOC/list internal formatting**: wrapping spacing partially covered by P032 (Q053–Q055, Q066–Q067, Q076–Q078); "(Continued)" headers (Q048, Q062, Q071) partially covered by P030; column headers bold/aligned (Q063–Q064, Q072–Q073) partially covered by P031
- **Front-matter visual checks**: copyright page (Q009–Q011) partially covered by P034; dedication centering/italic (Q033–Q034), bio-sketch content (Q023–Q025, Q027–Q029)
- **Heading level distinctions**: L3/L4/L5 partially addressed by P027; bold/italic enforcement still missing
- **Page-number sequence correctness**: Roman numeral value sequence (Q022, Q031, Q035, Q046, Q060 partially covered by P028 style check; actual sequence ordering not yet validated)
- **Figure/table body checks**: figure centering, table placement (above/below detection)
- **Cross-page title consistency**: partially covered by P033 (heuristic; skips ambiguous/image-only cases)

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

**Current EF comment-vs-tool overlap (extractable PDFs only):**
- Compared files: Cibaku Elson 1st review (78 comments), Yin Haotian 2nd review (65 comments)
- Page overlap: all EF-comment pages also have tool findings (Cibaku 42/42, Yin 44/44)
- Category overlap is narrow: Yin shows overlap in `indentation` (2 pages) and `margin_or_overflow` (1 page); Cibaku shows no positive overlap in the shared category set
- Major uncaptured EF areas remain `references_citations`, `committee_approval_page`, and semantic/manual feedback (`unclear_or_other`)

**Biggest current noise sources:**
- P013 (page-number candidates): always very high-volume by design
- P011 (margins): 70 findings on compressed PDF (down from 150 with artifact guard); 21–33 on normal PDFs
- P026 (font family): 92–117 warnings per document — real noncompliance but high volume

**Latest EF-overlap-driven refinement (P013 grouping):**
- P013 now emits one warning per page with candidates (instead of one per candidate line) and adds structured triage details (`issue_type`, candidate count/sample, style/position, confidence).
- Focused comparison-set impact:
  - Cibaku: P013 `99 → 95` (page coverage unchanged: 94 pages)
  - Yin Haotian: P013 `113 → 104` (page coverage unchanged: 103 pages)
  - Sebastian clean baseline: P013 `27 → 25`
- EF-overlap effect for P013 pages is unchanged on extractable-comment PDFs; refinement reduces repeated noise without narrowing coverage.

**Round 2 EF-overlap-driven refinement (P018/P024 heading variants):**
- Expanded TOC/List heading detection to include trailing punctuation and `(CONTINUED)`/`CONTINUED` suffix variants.
- Synthetic regression tests added for:
  - `TABLE OF CONTENTS.` handling (P018 path)
  - `LIST OF TABLES (CONTINUED)` handling (P024 path)
- Focused dataset impact was neutral (no count shifts on extractable-comment PDFs), but baseline behavior stayed stable (no added noise on Sebastian).

**Biggest coverage gaps relative to EF feedback:**
- P020 (title capitalization): fires 0 on 3 of 4 PDFs — bold metadata absent in most PDFs; font-size fallback still needed
- Cross-page title consistency: partial PDF heuristic via P033; manual review still required for edge layouts
- TOC "(Continued)" headers: multi-page TOC not handled

**Clean baseline:** Sebastian Fine Revision 3 (archive-contained) is in the five-PDF current-dataset evaluation set; used for P014/P031/P034 investigations and false-positive analysis.

**Per-rule current-dataset status (P030–P034):** All report **0** findings on the five-PDF set after respective refinements (see evaluation index above). This does not prove full guideline compliance.

---

## 4. Remaining Gaps After P034 (Prioritized)

### A. Automatable / partial (not yet fully covered)

| Priority | Gap | Type | Notes |
|----------|-----|------|-------|
| 🟡 High | Figure/table centering and placement | Automatable partial | Self-Assessment Sheet; above/below detection |
| 🟡 High | P034 copyright year/author extraction recall | Refinement | Year comparison ran 1/5; author 2/5; expand without quoting names in findings |
| 🟡 Med | Roman numeral **value** sequence (not just style/regime) | Automatable partial | Beyond P028/P029 style checks |
| 🟡 Med | Heading bold/italic enforcement beyond P027 | Partial | Level style partially covered |
| 🟡 Med | Body-page spacing (P016 front-matter focus) | Refinement | EF feedback suggests body gaps underrepresented |
| 🟡 Med | References/citations deterministic checks | Automatable partial | If TeX/BibTeX path feasible |
| 🟡 Med | Front-matter dedication/bio-sketch (Q023–Q029, Q033–Q034) | Partial/manual | Not covered by P025/P034 |
| 🟡 Low | Evaluation-set expansion | Data/eval | More extractable EF-comment PDFs from archive |
| 🟡 Low | EF category ↔ rule mapping at scale | Eval | Page/category precision/recall vs human comments |

### B. Recently addressed (P030–P034 — historical)

| Rule | Status |
|------|--------|
| P030 continued TOC/LoT/LoF headings | ✅ Implemented; 0 current-dataset findings |
| P031 LoT/LoF column headers | ✅ Implemented; false positives fixed (PR #55) |
| P032 wrapped-entry spacing | ✅ Implemented; Yin H 4th false positives fixed (PR #59) |
| P033 cross-page title consistency | ✅ Implemented; comparison on 2/5 files; 0 findings |
| P034 copyright page Q009–Q011 | ✅ Implemented; author false positives fixed (PR #67) |

### C. Partial rules still needing refinement

| Rule | Issue | Suggested direction |
|------|-------|---------------------|
| P020 | Bold metadata absent in many PDFs; low recall | Font-size fallback (historical note) |
| P013 | High volume by design | Further triage/grouping if needed |
| P016 | Front-matter-focused | Extend to body chapters conservatively |
| P025 | Limited degree/institution patterns | Extend nospace/abbreviation fallbacks |
| P033 | Comparison only 2/5 files | More candidate extraction paths (privacy-safe) |
| P034 | Year/author extraction skipped on 3/5 | ©-line and title-page pattern expansion |

### D. Manual-only / process-only (not automatable without semantic AI)

Approval Page committee semantics (Q015–Q020), Acknowledgements intent (Q037–Q042), administrative approval workflows, and many visual-layout judgments remain **manual-only** per the strict coverage audit.

### E. Evaluation / data tasks

- ~~Refresh a full P001–P034 aggregate snapshot~~ — done: `docs/evaluation/current_auditor_after_p034_evaluation.md`
- Expand EF overlap to additional extractable archive PDFs when available locally
- Per-category precision/recall vs EF comments (aggregate only)

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

### Bundle 8: P014 Clean-Baseline Investigation — IMPLEMENTED
**Summary:** Investigated 6 P014 false positives on Sebastian Fine clean baseline. Root cause:
P014 compared heading center against page center (306pt) instead of text-area center (324pt).
NJIT's asymmetric margins (1.5" left, 1" right) shift the text area center 18pt right of page
center. Fixed `_line_centered` to compare against text-area center. Before/after: Sebastian
Fine 6→0, Cibaku 1→0, Yin Haotian 1→0, Yin H 4th 10→0 — all false positives removed.
**Files changed:** `src/njit_auditor/rules/pdf_headings.py`, tests, evaluation docs.
**Risk:** Low — fix narrows false positives; off-center headings still flagged.

### Bundle 9: Current Evaluation Snapshot (after P011/P014/P029 refinements) — DONE
**Summary:** Full evaluation snapshot at commit `6a0baaf` across all 5 dissertation PDFs.
Total: 1,485 findings (down from 1,572). Key changes: P011 compressed 150→70; P014 0 everywhere;
P029 adds 12+2 findings. See `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`.

### Bundle 10: P029 Boundary Guard — IMPLEMENTED
**Summary:** P029 false positives on Sebastian Fine clean baseline (expected values 901/1001)
were caused by TOC entries "m" (1000) and "cm" (900) being included in the front-matter
Roman sequence. Added `_MAX_PLAUSIBLE_FRONTMATTER_ROMAN = 50` to exclude implausible
large-value candidates. Result: Sebastian Fine 2→0; Yin H 4th 12→12 (preserved).
**Files changed:** `src/njit_auditor/rules/pdf_roman_sequence.py`, tests, evaluation docs.
**Risk:** Low — only excludes candidates with Roman value > 50; all real front-matter sequences unaffected.

### Bundle 11: Next recommended tasks

Based on the current evaluation snapshot:

| Priority | Task | Rationale |
|----------|------|-----------|
| ✅ Done | P013 grouping / noise reduction | Implemented EF-overlap-driven per-page grouping + structured triage details |
| 🟡 High | EF category coverage expansion | `list_of_tables_figures_toc` still has uncovered EF pages on Yin; next step is TOC/List entry extraction robustness (wrapped/split entries) |
| 🟡 Med | EF comment ↔ rule comparison | Map EF comments to P-rule findings page-by-page |
| 🟡 Med | P011 bottom_margin clean-baseline investigation | 5 high-confidence findings on 29-page clean doc |
| 🟡 Low | P020 font-size fallback | CMR body PDFs still have P020=0 |
**Rationale:** The Sebastian Fine Revision 3 PDF (clean, no EF annotations) has not been run through the full P011–P028 auditor. Establishing false-positive counts is essential before further refinement.  
**Risk:** None — read-only evaluation task

---

## 6. Validation Status (main at `179e247`)

| Check | Result |
|-------|--------|
| `python -m pytest` | ✅ 383 passed |
| `ruff check .` | ✅ All checks passed |
| `mypy src` | ✅ No issues in 48 source files |

**Next recommended work:** Figure/table placement checks; P034 extraction recall; full P001–P034 aggregate evaluation refresh; EF overlap expansion on extractable PDFs.
