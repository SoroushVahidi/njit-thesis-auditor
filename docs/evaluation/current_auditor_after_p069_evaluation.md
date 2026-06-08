# Full Auditor Evaluation After P069 — Five-PDF Aggregate Snapshot

**Date:** 2026-06-08  
**Baseline commit:** `e045817` (merge PR #249 — P069 front-matter heading gate recall)  
**Auditor scope:** P001–P069 implemented; PDF audit path includes all rules through P069  
**P069 note:** Infrastructure-only (`infrastructure_refinement`); **no standalone P069 findings**  
**Validation:** ruff clean, mypy 87 source files, **976 pytest** passed

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
| Yin H 4th Review (compressed) | 580 |
| Sebastian Fine clean baseline | 58 |
| **Total** | **1,590** |

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
| P068 | 0 | 0 | 0 | 1 | 2 | **3** |
| P046 | 0 | 0 | 0 | 2 | 0 | **2** |
| P053 | 0 | 0 | 0 | 2 | 0 | **2** |
| P048 | 0 | 0 | 0 | 1 | 0 | **1** |
| P049 | 0 | 0 | 0 | 1 | 0 | **1** |
| P054 | 0 | 0 | 0 | 1 | 0 | **1** |
| P058 | 0 | 0 | 0 | 1 | 0 | **1** |
| P069 | 0 | 0 | 0 | 0 | 0 | **0** |
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
| committee_approval_page | 3 |
| title_page_metadata | 3 |
| **Total** | **1,590** |

---

## Comparison with P068-Era Snapshot

| Snapshot | Total findings |
|----------|---------------:|
| P068-era (commit `5d8ebaf`) | 1,590 |
| P069-era (commit `e045817`) | **1,590** |
| Delta | **0** |

P069 is infrastructure-only and emits no standalone findings. The full five-PDF rerun
confirms **zero aggregate delta** versus the P068-era snapshot: every per-file total and
every rule total matches the prior evaluation.

---

## P069 Interpretation

| Metric | Value |
|--------|------:|
| Direct P069 findings | **0** (infrastructure-only) |
| P065 findings | 0 (unchanged) |
| P066 findings | 0 (unchanged) |
| P067 findings | 0 (unchanged) |
| P068 findings | 3 (unchanged) |

### Affected-rule delta table (P068-era → post-P069)

| Affected rule | P068-era count | Post-P069 count | Delta |
|---|---:|---:|---:|
| P065 | 0 | 0 | 0 |
| P066 | 0 | 0 | 0 |
| P067 | 0 | 0 | 0 |
| P068 | 3 | 3 | 0 |
| P041 | 0 | 0 | 0 |
| P043 | 0 | 0 | 0 |
| P044 | 7 | 7 | 0 |
| P045 | 0 | 0 | 0 |
| P047 | 0 | 0 | 0 |

P069 gate evaluation (PR #249) reported `ACKNOWLEDGEMENTS` variant recall **+4** on the
five-PDF set via curated `ACKNOWLEDGMENTS` mapping. That gate improvement did **not**
translate into new downstream findings on this dataset (P043 Acknowledgements indentation
remains 0 on all five files). APPROVAL PAGE, BIOGRAPHICAL SKETCH, and DEDICATION gate hits
were unchanged; P065–P068 downstream checks therefore produced identical counts.

See `docs/evaluation/p069_frontmatter_heading_gate_recall_current_dataset_evaluation.md`
for gate-reach details.

---

## P068 Summary (unchanged from P068-era)

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
| Cibaku Elson 1st Review | 325 | P013 (95), P026 (92), P012 (78), P011 (21) | EF annotations extractable; P068 skipped at APPROVAL PAGE gate |
| Yin H 2nd Review (flattened) | 281 | P013 (104), P026 (103), P011 (33), P019 (15) | Flattened PDF; P068 skipped at APPROVAL PAGE gate |
| Yin Haotian 2nd Review | 346 | P013 (104), P026 (103), P012 (65), P011 (33) | EF comments extractable; P068 skipped at APPROVAL PAGE gate |
| Yin H 4th Review (compressed) | 580 | P013 (133), P026 (117), P036 (77), P011 (70) | P068: 1 finding |
| Sebastian Fine clean baseline | 58 | P013 (25), P011 (12), P068 (2) | P068: 2 findings; clean baseline with no EF annotations |

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

Generated audit JSON/Markdown files and aggregate summary JSON:
`data/evaluation/generated/current_auditor_after_p069/`

Path is gitignored. Do not commit contents.

Files generated locally include:

- `cibaku.json` / `cibaku.md`
- `yin_h_2nd_flat.json` / `yin_h_2nd_flat.md`
- `yin_haotian_2nd.json` / `yin_haotian_2nd.md`
- `yin_h_4th_comp.json` / `yin_h_4th_comp.md`
- `sebastian_fine.json` / `sebastian_fine.md`
- `aggregate.json`

Sebastian Fine was extracted locally from the tracked ZIP (or reused from a prior gitignored
extraction) for the audit run and remains uncommitted.

---

## Privacy and Dataset Limitations

- All counts are aggregate-only. No dissertation text, author names, committee names, advisor
  names, signatures, dates, approval-page prose, EF comment text, or other private content
  appears in this document.
- Yin H 2nd flat and Yin H 4th compressed have embedded comment content that is not extractable
  as PDF annotations; P012 findings reflect annotation-object presence only where applicable.
- Sebastian Fine clean baseline is ZIP-contained; the extracted PDF is ephemeral and must not
  be committed.
- P069 improved `ACKNOWLEDGEMENTS` gate recall on four files but did not change aggregate
  finding counts on this dataset.
- Rules that show 0 findings on all five files may still apply to real submissions; the
  evaluation dataset is a small, non-representative sample.

Generated: 2026-06-08
