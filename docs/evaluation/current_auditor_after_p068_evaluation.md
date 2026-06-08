# Full Auditor Evaluation After P068 — Five-PDF Aggregate Snapshot

**Date:** 2026-06-08  
**Baseline commit:** `5d8ebaf` (merge PR #244 — P068 current-dataset evaluation docs)  
**Auditor scope:** P001–P068 implemented; PDF audit path includes all rules through P068  
**Validation:** ruff clean, mypy 86 source files, **963 pytest** passed

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

## Comparison with P067-Era Snapshot

| Snapshot | Total findings |
|----------|---------------:|
| P067-era (commit `afe4ef6`) | 1,587 |
| P068-era (commit `5d8ebaf`) | **1,590** |
| Delta | **+3** |

P068 adds 3 new findings on this evaluation dataset:

- 3/5 files: no machine-readable `APPROVAL PAGE` heading detected; P068 skipped at the first gate.
- 2/5 files: unique `APPROVAL PAGE` detected on page 5; structural checks ran and emitted warnings.
- See `docs/evaluation/p068_current_dataset_evaluation.md` for per-file gate details.

Absence of P068 findings on the three skipped files does not prove Approval Page compliance.
On those files, the rule never reached committee-block structural checks because the
`APPROVAL PAGE` heading was not detected in the text layer.

---

## P068 Summary

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

P068 fired on Yin H 4th Review (compressed) and Sebastian Fine clean baseline. Both detected
role-label template phrases but found zero date/signature/underscore-blank indicators in the
text layer. Sebastian Fine also lacked a matching advisor-role template phrase.

---

## Per-File Summary

| File | Total | Main contributors | Notes |
|------|------:|-------------------|-------|
| Cibaku Elson 1st Review | 325 | P013 (95), P026 (92), P012 (78), P011 (21) | EF annotations extractable; P068 skipped at APPROVAL PAGE gate |
| Yin H 2nd Review (flattened) | 281 | P013 (104), P026 (103), P011 (33), P019 (15) | Flattened PDF; P068 skipped at APPROVAL PAGE gate |
| Yin Haotian 2nd Review | 346 | P013 (104), P026 (103), P012 (65), P011 (33) | EF comments extractable; P068 skipped at APPROVAL PAGE gate |
| Yin H 4th Review (compressed) | 580 | P013 (133), P026 (117), P036 (77), P011 (70) | +1 P068 (`approval_page_signature_blocks_sparse`) vs P067-era |
| Sebastian Fine clean baseline | 58 | P013 (25), P011 (12), P068 (2) | +2 P068 vs P067-era; clean baseline with no EF annotations |

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
`data/evaluation/generated/current_auditor_after_p068/`

Path is gitignored. Do not commit contents.

Files generated locally include:

- `cibaku.json` / `cibaku.md`
- `yin_h_2nd_flat.json` / `yin_h_2nd_flat.md`
- `yin_haotian_2nd.json` / `yin_haotian_2nd.md`
- `yin_h_4th.json` / `yin_h_4th.md`
- `sebastian_fine.json` / `sebastian_fine.md`
- `aggregate_summary.json`

Sebastian Fine was extracted locally from the tracked ZIP into
`data/evaluation/generated/current_auditor_after_p068/extracted/` for the audit run and
remains uncommitted.

---

## Privacy and Dataset Limitations

- All counts are aggregate-only. No dissertation text, author names, committee names, advisor
  names, signatures, dates, approval-page prose, EF comment text, or other private content
  appears in this document.
- Yin H 2nd flat and Yin H 4th compressed have embedded comment content that is not extractable
  as PDF annotations; P012 findings reflect annotation-object presence only where applicable.
- Sebastian Fine clean baseline is ZIP-contained; the extracted PDF is ephemeral and must not
  be committed.
- P068 shows 3 findings because 2/5 files exposed a machine-readable `APPROVAL PAGE` heading
  with role labels but no extractable signature/date indicators. This does not indicate full
  Approval Page noncompliance; signature blocks may be image-rendered or outside the text layer.
- Rules that show 0 findings on all five files may still apply to real submissions; the
  evaluation dataset is a small, non-representative sample.

Generated: 2026-06-08
