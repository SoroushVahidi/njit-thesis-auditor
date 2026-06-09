# Evaluation Data Manifest

- **Generated for commit:** `1476a51` (PR #262 — P072 implementation)
- **Latest main:** `1476a51` (PR #262)
- **Validation:** ruff, mypy, **1014 pytest** at the latest docs/status refresh
- **Canonical aggregate:** `docs/evaluation/current_auditor_after_p070_evaluation.md` — **1,543** findings; unchanged after P071 and P072 (both infrastructure-only); no separate `current_auditor_after_p072_evaluation.md`
- **Latest EF overlap:** `docs/evaluation/ef_overlap_after_p072_evaluation.md` — 143 EF annotations; 671 tool findings on comparison PDFs; `committee_approval_page` gap unchanged (5 EF, 0 tool); `references_citations` gap unchanged (9 EF, 0 tool)
- **Schema version:** 1
- **Machine-readable source:** `data/processed/evaluation_data_manifest.json`
- **Status:** Privacy-safe index of repository evaluation and guideline data (post PR #48)
- **Validation:** Protected by `tests/test_evaluation_data_manifest.py`

## Executive Summary

This manifest indexes committed, referenced, archive-contained, and gitignored evaluation
data paths. Counts below match `sample_counts` in the JSON manifest.

| Sample type | Count |
|---|---:|
| Guideline / rule-source files | 8 |
| Processed rule source files | 2 |
| EF-commented dissertation PDFs (tracked) | 4 |
| EF-commented dissertation PDFs (referenced, not standalone tracked) | 1 |
| Extractable-comment PDFs | 2 |
| Flattened / non-extractable-comment PDFs | 2 |
| Clean / no-feedback baseline archive (tracked ZIP) | 1 |
| Clean / no-feedback baseline PDF (archive-contained) | 1 |
| Rule matrix files | 1 |
| Original-archive-only materials | 12 |
| Generated / private gitignored paths | 2 |

**Privacy:** Real dissertation files contain student-identifying content and body text.
Reporting must remain aggregate-only. Do not quote dissertation body text.

---

## 1. Guideline Rule Sources

Authoritative NJIT formatting and process references under `data/raw/guidelines/`.

| Path | Type | Role | Privacy | Tracked |
|---|---|---|---|---|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | DOCX | formatting-rule-source | Low | Yes |
| `Titles Examples Level 1 to 5.docx` | DOCX | formatting-rule-source | Low | Yes |
| `Self-Self Assessment Sheet.pdf` | PDF | formatting-rule-source | Low | Yes |
| `Front Matter Pages Lorem Ipsum.pdf` | PDF | formatting-rule-source | Low | Yes |
| `PhD Title Pages.pdf` | PDF | formatting-rule-source | Low | Yes |
| `Dissertation Review Process.pdf` | PDF | process-admin-reference | Low | Yes |
| `PhD Dissertation Process Roadmap .xlsx` | XLSX | process-admin-reference | Low | Yes |
| `Link to PQ ETD Administartor_.docx` | DOCX | submission-reference | Low | Yes |

---

## 2. Processed Rule Sources

| Path | Prefix | Count | Tracked |
|---|---|---:|---|
| `data/processed/rules/njit_rule_inventory.json` | Q | 79 (Q001–Q079) | Yes |
| `data/processed/rules/project_added_rules.json` | P | 68 (P001–P068) | Yes |

P001–P068 are implemented; P068 formal current-dataset evaluation complete (3 findings on 2/5 files; 3/5 skipped at APPROVAL PAGE detection gate) and the full post-P068 aggregate is 1,590 findings (+3 vs P067-era); see `docs/evaluation/p068_current_dataset_evaluation.md` and `docs/evaluation/current_auditor_after_p068_evaluation.md`. The P067-era snapshot (`afe4ef6`, 1,587 findings) remains a historical baseline. Full Q-rule / guideline source coverage is not complete
(see `docs/status/source_to_implementation_coverage_after_p029.md`).

---

## 3. Data Sample Index

| Category | Path / name | Tracked status | Comment status | Evaluation usage | Privacy |
|---|---|---|---|---|---|
| EF-commented PDF | `250218 Cibaku Elson First Review.pdf` | tracked | extractable (78) | full eval + EF overlap | high |
| EF-commented PDF | `260415 Yin H _2nd_review with EF Comments.pdf` | tracked | flattened (0 extractable) | full eval only | high |
| EF-commented PDF | `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | tracked | extractable (65) | full eval + EF overlap | high |
| EF-commented PDF | `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | tracked | compressed_flattened (0 extractable) | full eval only | high |
| EF-commented PDF | `250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf` | referenced_not_standalone_tracked | unknown | not in current eval set | high |
| Clean baseline ZIP | `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | tracked | n/a (no EF comments) | full eval + refinement baselines | high |
| Clean baseline PDF | `Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf` | archive-contained | n/a | full eval + refinement baselines | high |
| Rule matrix | `260330_YESNO_audit_logic_matrix.xlsx` | tracked | n/a | rule inventory source; skipped in PDF eval | low |
| Original archive | 10 additional EF-annotated files (see JSON) | original_archive_only | not verified in tree | not used unless extracted locally | high |
| Original archive | 2 presentation files under `Presentations /` | original_archive_only | n/a | process/admin reference only | low |
| Generated outputs | `data/evaluation/generated/` | gitignored | n/a | local run artifacts | medium-high |
| Private outputs | `data/evaluation/private/` | gitignored | n/a | reserved local-only path | high |

---

## 4. Sebastian Fine Clean Baseline Caveat

Three related artifacts must be distinguished:

1. **Tracked ZIP:** `data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`
   is committed and contains the clean Revision 3 PDF.
2. **Archive-contained PDF:** `Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf`
   lives inside that ZIP at
   `Dissertations with no Feedback /Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf`.
   It is used in evaluation docs (29 pages) but is **not** present as a standalone tracked file.
3. **Referenced EF-annotated PDF:** `250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf`
   is documented in `docs/sources/ester_materials.md` but is **not** verified as a standalone
   tracked path in the current tree.

**Future evaluation scripts** should either extract the clean PDF from the ZIP locally or
document an explicit local path in run configuration. Do not commit extracted raw dissertation
files unless explicitly requested.

---

## 5. How Future Scripts Should Use This Manifest

1. **Never assume archive-only files exist as repository paths.** Check `tracked_status`
   before opening a file. Use `original_archive_only` entries only after local extraction
   from the original bundle.
2. **EF-overlap metrics:** use only PDFs with `comment_status: extractable` and
   `used_in_ef_overlap: true` (currently Cibaku 1st review and Yin Haotian 2nd review).
3. **Full audit-count evaluations:** may include flattened/compressed PDFs for raw finding
   counts, but do not attempt comment extraction on them.
4. **Clean baselines:** include archive-contained clean PDFs for false-positive / noise
   profiling; exclude them from EF-comment overlap because they have no EF annotations.
5. **Generated outputs:** write all raw audit JSON/MD and overlap summaries under
   `data/evaluation/generated/` (gitignored). Commit only curated aggregate docs under
   `docs/evaluation/` unless explicitly asked otherwise.
6. **Rule matrix XLSX:** treat `260330_YESNO_audit_logic_matrix.xlsx` as a rule-source
   artifact, not a PDF evaluation input.

---

## 6. Privacy Rules

1. Do not quote dissertation body text in docs, reports, or tests.
2. Do not commit raw generated audit outputs unless explicitly requested.
3. Prefer aggregate counts, page numbers, rule IDs, and high-level categories in reporting.
4. Keep sensitive or experimental outputs under gitignored paths
   (`data/evaluation/generated/`, `data/evaluation/private/`).
5. Do not make the repository public without a student-data handling review.
6. Do not modify raw guideline or dissertation source files in normal implementation PRs.

---

## 7. Cross-References

- Source inventory: `docs/status/data_inventory_and_evaluation_sources.md`
- Ester materials catalog: `docs/sources/ester_materials.md`
- Rule coverage audit: `docs/status/source_to_implementation_coverage_after_p029.md`
- Historical full P001–P029 evaluation: `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`
- **Prior full P001–P069 PDF evaluation (P069-era):** `docs/evaluation/current_auditor_after_p069_evaluation.md` — **1,590** findings (unchanged vs P068-era; P069 infrastructure-only); gitignored outputs under `data/evaluation/generated/current_auditor_after_p069/`
- **Current full P001–P070 PDF evaluation (P070-era):** `docs/evaluation/current_auditor_after_p070_evaluation.md` — **1,543** findings (−47 vs P069-era); gitignored outputs under `data/evaluation/generated/current_auditor_after_p070/`
- **P070 parser-reach evaluation:** `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md` — all 5 PDFs accessible; parser entries 185→167
- **P069 gate-reach evaluation:** `docs/evaluation/p069_frontmatter_heading_gate_recall_current_dataset_evaluation.md` — ACKNOWLEDGEMENTS +4; P065–P068 totals unchanged
- **Prior full P001–P068 PDF evaluation (P068-era):** `docs/evaluation/current_auditor_after_p068_evaluation.md` — **1,590** findings (P068 adds 3); gitignored outputs under `data/evaluation/generated/current_auditor_after_p068/`
- **P068 current-dataset evaluation:** `docs/evaluation/p068_current_dataset_evaluation.md` — 3 findings on 2/5 files; 3/5 skipped at APPROVAL PAGE detection gate
- **Prior full P001–P067 PDF evaluation (P067-era):** `docs/evaluation/current_auditor_after_p067_evaluation.md` — **1,587** findings (P067 adds 0); gitignored outputs under `data/evaluation/generated/current_auditor_after_p067/`
- **P067 current-dataset evaluation:** `docs/evaluation/p067_current_dataset_evaluation.md` — 0 findings; 3/5 files skipped at heading detection; 2/5 reached BIOGRAPHICAL SKETCH but no qualifying Publications boundary
- **Prior full P001–P066 PDF evaluation (P066-era):** `docs/evaluation/current_auditor_after_p066_evaluation.md` — **1,587** findings (P066 adds 0); gitignored outputs under `data/evaluation/generated/current_auditor_after_p066/`
- **P065-era PDF evaluation (prior full snapshot):** `docs/evaluation/current_auditor_after_p065_evaluation.md` — **1,587** findings; gitignored outputs under `data/evaluation/generated/current_auditor_after_p065/`
- **P062-era PDF evaluation (historical full snapshot):** `docs/evaluation/current_auditor_after_p062_evaluation.md` — **1,587** findings (P062 adds 0); gitignored outputs under `data/evaluation/generated/current_auditor_after_p062/`
- **P061-era PDF evaluation (prior full snapshot):** `docs/evaluation/current_auditor_after_p061_evaluation.md` — **1,587** findings; gitignored outputs under `data/evaluation/generated/current_auditor_after_p061/`
- **Historical full P001–P034 PDF evaluation (pre-P035 canonical):** `docs/evaluation/current_auditor_after_p034_evaluation.md`
- **P035 current-dataset subset (local 4 PDFs):** `docs/evaluation/p035_current_dataset_evaluation.md`
- **Canonical full-triage generated reports (gitignored):** `data/evaluation/generated/current_auditor_after_p034_p011_triage/` — P011/P012/P013/P026 triage rollups; see `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md`
- Historical generated folders (superseded): `current_auditor_after_p034/`, `current_auditor_after_p034_p013_triage/`, `current_auditor_after_p034_p026_triage/`
- **P036 current-dataset evaluation (not run):** `docs/evaluation/p036_current_dataset_evaluation.md`
- **P055 current-dataset evaluation (not run):** `docs/evaluation/p055_current_dataset_evaluation.md`
- **P056 current-dataset evaluation (not run):** `docs/evaluation/p056_current_dataset_evaluation.md`
- **P057 current-dataset evaluation (not run):** `docs/evaluation/p057_current_dataset_evaluation.md`
- **P058 current-dataset evaluation (not run):** `docs/evaluation/p058_current_dataset_evaluation.md`
- **P039 current-dataset evaluation (not run):** `docs/evaluation/p039_current_dataset_evaluation.md`
- **P040 current-dataset evaluation (not run):** `docs/evaluation/p040_current_dataset_evaluation.md`
- **P041 current-dataset evaluation (not run):** `docs/evaluation/p041_current_dataset_evaluation.md`
- **P042 current-dataset evaluation (not run):** `docs/evaluation/p042_current_dataset_evaluation.md`
- **P061 current-dataset evaluation (formal, post-implementation):** `docs/evaluation/p061_current_dataset_evaluation.md` — 0 findings on five-PDF local subset
- P030–P042 per-rule evaluations: see `docs/status/current_project_state_and_next_steps.md` (evaluation index)
- EF overlap comparison: `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- EF overlap after P063: `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- **Full repository audit after P071:** `docs/status/full_repository_audit_after_p071.md`
- **EF overlap after P072:** `docs/evaluation/ef_overlap_after_p072_evaluation.md` — 2 extractable-comment PDFs; 143 EF annotations; 671 tool findings; `committee_approval_page` gap unchanged (5 EF, 0 tool); structural fallback found 0 candidates (image-embedded approval pages)
- **P072 current-dataset evaluation:** `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md` — all 5 PDFs evaluated; fallback 0 candidates on 3 non-detecting files; aggregate 1,543 unchanged
- **EF overlap after P071:** `docs/evaluation/ef_overlap_after_p071_evaluation.md` — 2 extractable-comment PDFs; 143 EF annotations; P064 reaches 2/2 comparison PDFs after P071; `references_citations` gap unchanged (9 EF, 0 tool)
- **EF overlap after P068:** `docs/evaluation/ef_overlap_after_p068_evaluation.md` — 2 extractable-comment PDFs; 143 EF annotations; P064–P068 unchanged overlap on comparison set (historical baseline)
- Real thesis pairing and EF overlap readiness (P068-era): `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- EF overlap refinements: `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`,
  `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
