# Full Auditor Evaluation After P070 — Five-PDF Aggregate Snapshot

**Date:** 2026-06-08  
**Baseline commit:** `b0ec5e4` (merge PR #253 — P070 current-dataset evaluation docs; P070 code at `f0d8294`)  
**Auditor scope:** P001–P070 implemented; PDF audit path includes all rules through P070  
**P070 note:** Infrastructure-only (`infrastructure_refinement`); **no standalone P070 findings**  
**Validation:** ruff clean, mypy 87 source files, **988 pytest** passed

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
| Yin H 4th Review (compressed) | 532 |
| Sebastian Fine clean baseline | 59 |
| **Total** | **1,543** |

---

## Findings by Rule and File

| Rule | Cibaku | Yin H 2nd flat | Yin Haotian 2nd | Yin H 4th | Sebastian Fine | Total |
|------|-------:|---------------:|----------------:|----------:|---------------:|------:|
| P013 | 95 | 104 | 104 | 133 | 25 | **461** |
| P026 | 92 | 103 | 103 | 117 | 0 | **415** |
| P011 | 21 | 33 | 33 | 70 | 12 | **169** |
| P012 | 78 | 0 | 65 | 0 | 0 | **143** |
| P036 | 0 | 0 | 0 | 55 | 0 | **55** |
| P019 | 8 | 15 | 15 | 25 | 4 | **67** |
| P015 | 5 | 13 | 13 | 8 | 0 | **39** |
| P020 | 2 | 1 | 1 | 30 | 3 | **37** |
| P017 | 0 | 0 | 0 | 23 | 1 | **24** |
| P028 | 8 | 0 | 0 | 8 | 0 | **16** |
| P038 | 4 | 4 | 4 | 2 | 2 | **16** |
| P023 | 6 | 4 | 4 | 0 | 1 | **15** |
| P035 | 0 | 0 | 0 | 13 | 1 | **14** |
| P018 | 0 | 0 | 0 | 10 | 3 | **13** |
| P029 | 0 | 0 | 0 | 12 | 0 | **12** |
| P024 | 0 | 0 | 0 | 10 | 0 | **12** |
| P016 | 1 | 2 | 2 | 4 | 2 | **11** |
| P044 | 3 | 1 | 1 | 1 | 1 | **7** |
| P027 | 1 | 0 | 0 | 2 | 0 | **3** |
| P030 | 0 | 0 | 0 | 3 | 0 | **3** |
| P037 | 0 | 0 | 0 | 2 | 1 | **3** |
| P051 | 1 | 1 | 1 | 0 | 0 | **3** |
| P068 | 0 | 0 | 0 | 1 | 2 | **3** |
| P046 | 0 | 0 | 0 | 2 | 0 | **2** |
| P040 | 0 | 0 | 0 | 0 | 1 | **1** |
| P053 | 0 | 0 | 0 | 1 | 0 | **1** |
| P070 | 0 | 0 | 0 | 0 | 0 | **0** |
| *All others* | 0 | 0 | 0 | 0 | 0 | 0 |

---

## Findings by Category

| Category | Total |
|----------|------:|
| page_numbering | 559 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| list_of_tables_figures_toc | 84 |
| indentation | 46 |
| capitalization_case | 37 |
| spacing_blank_lines | 26 |
| heading_title | 19 |
| punctuation | 19 |
| table_format | 13 |
| figure_format | 7 |
| committee_approval_page | 3 |
| title_page_metadata | 3 |
| **Total** | **1,543** |

---

## Comparison with P069-Era Snapshot

| Snapshot | Total findings |
|----------|---------------:|
| P069-era (commit `e045817`) | 1,590 |
| P070-era (commit `b0ec5e4`) | **1,543** |
| Delta | **−47** |

P070 is infrastructure-only and emits no standalone findings. The −47 aggregate delta
comes from dependent TOC/LoT/LoF rules on Yin H 4th Review (compressed), where P070
parser refinements reject spurious parsed entries that previously fed spacing, alignment,
and punctuation checks. Sebastian Fine clean baseline increased by +1 (59 vs 58); the
three EF-comparison PDFs (Cibaku, Yin H 2nd flat, Yin Haotian 2nd) are unchanged.

---

## Per-File Comparison (P069-era → post-P070)

| File label | P069-era | Post-P070 | Delta | Main contributors | Notes |
|---|---:|---:|---:|---|---|
| Cibaku Elson 1st Review | 325 | 325 | 0 | P013, P026, P012, P011 | EF-overlap comparison PDF; no TOC/LoT/LoF pages |
| Yin H 2nd Review (flattened) | 281 | 281 | 0 | P013, P026, P011, P019 | Flattened PDF; no list pages |
| Yin Haotian 2nd Review | 346 | 346 | 0 | P013, P026, P012, P011 | EF-overlap comparison PDF; no list pages |
| Yin H 4th Review (compressed) | 580 | 532 | −48 | P013, P026, P036, P011 | Only file with dense TOC/LoT/LoF text layer |
| Sebastian Fine clean baseline | 58 | 59 | +1 | P013, P011, P068 | Prefix-gate recall +3 parser entries |

---

## Category Comparison (P069-era → post-P070)

| Category | P069-era | Post-P070 | Delta |
|---|---:|---:|---:|
| list_of_tables_figures_toc | 130 | 84 | −46 |
| punctuation | 20 | 19 | −1 |
| *All other categories* | unchanged | unchanged | 0 |

---

## Rule Comparison (P069-era → post-P070)

| Rule | P069-era | Post-P070 | Delta |
|---|---:|---:|---:|
| P036 | 77 | 55 | −22 |
| P040 | 13 | 1 | −12 |
| P018 | 19 | 13 | −6 |
| P024 | 12 | 10 | −2 |
| P048 | 1 | 0 | −1 |
| P049 | 1 | 0 | −1 |
| P053 | 2 | 1 | −1 |
| P054 | 1 | 0 | −1 |
| P058 | 1 | 0 | −1 |
| P065–P069, P061, P062 | unchanged | unchanged | 0 |

All rule deltas occur on Yin H 4th Review (compressed).

---

## P070 Interpretation

| Metric | Value |
|--------|------:|
| Direct P070 findings | **0** (infrastructure-only) |
| P065 findings | 0 (unchanged) |
| P066 findings | 0 (unchanged) |
| P067 findings | 0 (unchanged) |
| P068 findings | 3 (unchanged) |
| P061 findings | 0 (unchanged) |
| P062 findings | 0 (unchanged) |

### Parser recovery (from current-dataset evaluation)

| Mechanism | Count |
|---|---:|
| Multi-line merge | 4 |
| Split page-number pairing | 4 |
| Prefix-tolerant gates | 9 |
| Page runs | 7 (2 multi-page) |
| Parser entries (pre→post) | 185 → 167 (−18 net) |

P070 improved targeted recall on Sebastian Fine (+3 entries via prefix gates) while
reducing false-positive entry counts on Yin H 4th (−21 entries via heading/prose guards).
Dependent-rule decreases on Yin H 4th reflect fewer noisy parsed entries, not removal of
standalone P070 checks.

### EF-overlap expectation

Cibaku and Yin Haotian 2nd Review — the two extractable-comment EF-overlap PDFs — still
have zero detected TOC/LoT/LoF pages and zero `list_of_tables_figures_toc` findings.
EF-overlap gaps for `list_of_tables_figures_toc` are **not expected to change** from P070
on this dataset. See `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md`.

---

## P068 Summary (unchanged from P069-era)

| Metric | Value |
|--------|------:|
| Total P068 findings | 3 |
| Files with P068 findings | 2/5 |
| Files skipped at detection gate | 3/5 |

### P068 issue-type counts

| Issue type | Count |
|---|---:|
| `approval_page_signature_blocks_sparse` | 2 |
| `approval_page_advisor_role_label_missing` | 1 |

---

## Per-File Summary

| File | Total | Main contributors | Notes |
|------|------:|-------------------|-------|
| Cibaku Elson 1st Review | 325 | P013 (95), P026 (92), P012 (78), P011 (21) | EF annotations extractable; no list pages |
| Yin H 2nd Review (flattened) | 281 | P013 (104), P026 (103), P011 (33), P019 (15) | Flattened PDF; no list pages |
| Yin Haotian 2nd Review | 346 | P013 (104), P026 (103), P012 (65), P011 (33) | EF comments extractable; no list pages |
| Yin H 4th Review (compressed) | 532 | P013 (133), P026 (117), P036 (55), P011 (70) | P068: 1 finding; P070 parser deltas |
| Sebastian Fine clean baseline | 59 | P013 (25), P011 (12), P068 (2) | P068: 2 findings; prefix-gate recall |

---

## Largest Rules and Categories

### By rule (top 5)

| Rule | Total | Notes |
|------|------:|-------|
| P013 | 461 | Page-number candidate detector; high volume by design |
| P026 | 415 | Font family compliance |
| P011 | 169 | Margin violations; Yin H 4th inflated by compression artifacts |
| P012 | 143 | Embedded annotation objects (extractable-comment PDFs) |
| P036 | 55 | TOC/LoT/LoF inter-entry spacing; Yin H 4th only (−22 vs P069-era) |

### By category (top 5)

| Category | Total |
|----------|------:|
| page_numbering | 559 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| list_of_tables_figures_toc | 84 |

---

## Generated Output

Generated audit JSON files and aggregate summary JSON:
`data/evaluation/generated/current_auditor_after_p070/`

Path is gitignored. Do not commit contents.

Files generated locally include:

- `cibaku.json`
- `yin_h_2nd_flat.json`
- `yin_haotian_2nd.json`
- `yin_h_4th_comp.json`
- `sebastian_fine.json`
- `aggregate.json`

Sebastian Fine was extracted locally from the tracked ZIP for the audit run and remains
uncommitted. Parser-reach detail JSON remains under
`data/evaluation/generated/p070_evaluation/` from PR #253.

---

## Privacy and Dataset Limitations

- All counts are aggregate-only. No dissertation text, author names, committee names,
  TOC/LoT/LoF entry text, EF comment text, or other private content appears in this document.
- Yin H 2nd flat and Yin H 4th compressed have embedded comment content that is not
  extractable as PDF annotations; P012 findings reflect annotation-object presence only
  where applicable.
- Sebastian Fine clean baseline is ZIP-contained; the extracted PDF is ephemeral.
- P070 parser changes affect only files with detectable list pages (2/5 on this dataset).
- Rules that show 0 findings on all five files may still apply to real submissions; the
  evaluation dataset is a small, non-representative sample.

Generated: 2026-06-08
