# Full Auditor Evaluation After P066 — Five-PDF Aggregate Snapshot

**Date:** 2026-06-08  
**Baseline commit:** `e5caace` (merge PR #236 — P066 implementation)  
**Auditor scope:** P001–P066 implemented; PDF audit path includes all rules through P066  
**Validation:** ruff clean, mypy 84 source files, 937 pytest passed

---

## Files Evaluated

| File label | Availability |
|------------|--------------|
| Cibaku Elson 1st Review | Direct |
| Yin H 2nd Review (flattened) | Direct |
| Yin Haotian 2nd Review | Direct |
| Yin H 4th Review (compressed) | Direct |
| Sebastian Fine clean baseline | Extracted from tracked ZIP (not committed) |

---

## Total Findings by File

| File | Total findings |
|------|---------------:|
| Cibaku Elson 1st Review | 325 |
| Yin H 2nd Review (flattened) | 281 |
| Yin Haotian 2nd Review | 346 |
| Yin H 4th Review (compressed) | 579 |
| Sebastian Fine clean baseline | 56 |
| **Total** | **1,587** |

---

## Findings by Rule and File

| Rule | Cibaku | Yin H 2nd flat | Yin Haotian 2nd | Yin H 4th | Sebastian Fine | Total |
|------|-------:|---------------:|----------------:|----------:|---------------:|------:|
| P013 | 95 | 104 | 104 | 133 | 25 | **461** |
| P026 | 92 | 103 | 103 | 117 | 0 | **415** |
| P011 | 21 | 33 | 33 | 70 | 12 | **169** |
| P012 | 78 | 0 | 65 | 0 | 0 | **143** |
| P036 | 0 | 0 | 0 | 77 | 0 | **77** |
| P019 | 8 | 15 | 15 | 25 | 4 | **67** |
| P015 | 5 | 13 | 13 | 8 | 0 | **39** |
| P020 | 2 | 1 | 1 | 30 | 3 | **37** |
| P017 | 0 | 0 | 0 | 23 | 1 | **24** |
| P018 | 0 | 0 | 0 | 17 | 2 | **19** |
| P028 | 8 | 0 | 0 | 8 | 0 | **16** |
| P038 | 4 | 4 | 4 | 2 | 2 | **16** |
| P023 | 6 | 4 | 4 | 0 | 1 | **15** |
| P035 | 0 | 0 | 0 | 13 | 1 | **14** |
| P040 | 0 | 0 | 0 | 12 | 1 | **13** |
| P024 | 0 | 0 | 0 | 12 | 0 | **12** |
| P029 | 0 | 0 | 0 | 12 | 0 | **12** |
| P016 | 1 | 2 | 2 | 4 | 2 | **11** |
| P044 | 3 | 1 | 1 | 1 | 1 | **7** |
| P027 | 1 | 0 | 0 | 2 | 0 | **3** |
| P051 | 1 | 1 | 1 | 0 | 0 | **3** |
| P030 | 0 | 0 | 0 | 3 | 0 | **3** |
| P037 | 0 | 0 | 0 | 2 | 1 | **3** |
| P046 | 0 | 0 | 0 | 2 | 0 | **2** |
| P053 | 0 | 0 | 0 | 2 | 0 | **2** |
| P048 | 0 | 0 | 0 | 1 | 0 | **1** |
| P049 | 0 | 0 | 0 | 1 | 0 | **1** |
| P054 | 0 | 0 | 0 | 1 | 0 | **1** |
| P058 | 0 | 0 | 0 | 1 | 0 | **1** |
| P066 | 0 | 0 | 0 | 0 | 0 | **0** |
| *All others* | 0 | 0 | 0 | 0 | 0 | 0 |

---

## Findings by Category

| Category | Total |
|----------|------:|
| page_numbering | 559 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| list_of_tables_figures_toc | 130 |
| indentation | 46 |
| capitalization_case | 37 |
| spacing_blank_lines | 26 |
| punctuation | 20 |
| heading_title | 19 |
| table_format | 13 |
| figure_format | 7 |
| title_page_metadata | 3 |
| **Total** | **1,587** |

---

## Comparison with P065-Era Snapshot

| Snapshot | Total findings |
|----------|---------------:|
| P065-era (commit `b233f3b`) | 1,587 |
| P066-era (commit `e5caace`) | **1,587** |
| Delta | **0** |

P066 adds 0 new findings on this evaluation dataset:

- 3/5 files: BIOGRAPHICAL SKETCH heading not detected by frontmatter scan → skipped
- 2/5 files: heading detected; year-ordering check ran; years found to be non-increasing (most-recent-first — correct order) → no finding
- See `docs/evaluation/p066_current_dataset_evaluation.md` for per-file details

Absence of P066 findings does not prove bio-sketch compliance. Reasons
findings may not fire even on a non-compliant bio sketch:

- Bio sketch page is image-rendered (no text layer) → skipped by all layout rules
- BIOGRAPHICAL SKETCH heading absent or in a non-standard block → detection gate not met
- Fewer than `_MIN_YEAR_CANDIDATES = 3` short education-zone lines → skip gate
- All year candidates equal → skip gate (year gap must exceed `_MIN_YEAR_GAP = 2`)

---

## Per-File Summary

| File | Total | Main contributors | Notes |
|------|------:|-------------------|-------|
| Cibaku Elson 1st Review | 325 | P013 (95), P026 (92), P012 (78), P011 (21) | EF annotations extractable (78 comments) |
| Yin H 2nd Review (flattened) | 281 | P013 (104), P026 (103), P011 (33), P019 (15) | Flattened PDF; comments not extractable |
| Yin Haotian 2nd Review | 346 | P013 (104), P026 (103), P012 (65), P011 (33) | Same dissertation as Yin H 2nd flat; EF comments extractable (65 comments) |
| Yin H 4th Review (compressed) | 579 | P013 (133), P026 (117), P036 (77), P011 (70) | Compression artifacts inflate P011; highest volume |
| Sebastian Fine clean baseline | 56 | P013 (25), P011 (12) | Clean baseline; no EF annotations |

---

## Largest Rules and Categories

### By rule (top 5)

| Rule | Total | Notes |
|------|------:|-------|
| P013 | 461 | Page-number candidate detector; high volume by design; see `p013_triage` rollup |
| P026 | 415 | Font family compliance; real noncompliance on most evaluation files |
| P011 | 169 | Margin violations; Yin H 4th inflated by compression artifacts; see `p011_margin_triage` |
| P012 | 143 | Embedded annotation objects (only extractable-comment PDFs) |
| P036 | 77 | TOC/LoT/LoF inter-entry spacing; Yin H 4th only |

### By category (top 5)

| Category | Total |
|----------|------:|
| page_numbering | 559 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| list_of_tables_figures_toc | 130 |

---

## Generated Output

Generated audit JSON files: `data/evaluation/generated/current_auditor_after_p066/`  
Path is gitignored — do not commit contents.

Files:
- `cibaku.json`
- `yin_h_2nd_flat.json`
- `yin_haotian_2nd.json`
- `yin_h_4th.json`
- `sebastian_fine.json`

Sebastian Fine was extracted locally from the tracked ZIP into a separate
gitignored path under `data/evaluation/generated/` for the audit run and remains
uncommitted.

---

## Privacy and Dataset Limitations

- All counts are aggregate-only. No dissertation text, author names, degree names, institution names, bio-sketch prose, EF comment text, or other private content appears in this document.
- Yin H 2nd flat and Yin H 4th compressed have embedded comment objects that are not extractable; P012 findings on these files reflect embedded PDF annotation presence only, not readable content.
- Sebastian Fine clean baseline is ZIP-contained; the extracted PDF is ephemeral and must not be committed.
- P065 (dedication centering/italic) and P066 (bio-sketch degree ordering) both show 0 findings due to detection gate limitations on this dataset. This does not indicate compliance.
- Rules that show 0 findings on all five files (P041, P042, P043, P045, P047, P055, P056, P057, P059, P060, P061, P062, P063, P064, P065, P066, and others) may still apply to real submissions — the evaluation dataset is a small, non-representative sample.

Generated: 2026-06-08
