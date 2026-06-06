# Evaluation Data Manifest

- **Generated for commit:** `00b9c2d` (intentional last substantive code/eval baseline; five-PDF aggregate unchanged)
- **Latest main:** `5547e3e` (PR #184 — Implement P057 LoT LoF page-number ordering checks; P001–P057 implemented; web GUI present with upload, URL audit, and built-in sample audit)
- **Validation:** ruff, mypy, **695 pytest** after P057 implementation
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
| `data/processed/rules/project_added_rules.json` | P | 57 (P001–P057) | Yes |

P001–P057 are implemented; full Q-rule / guideline source coverage is not complete
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
- **Current full P001–P034 PDF evaluation (pre-P035 canonical):** `docs/evaluation/current_auditor_after_p034_evaluation.md`
- **P035 current-dataset subset (local 4 PDFs):** `docs/evaluation/p035_current_dataset_evaluation.md`
- **Canonical full-triage generated reports (gitignored):** `data/evaluation/generated/current_auditor_after_p034_p011_triage/` — see `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md`
- Historical generated folders (superseded): `current_auditor_after_p034/`, `current_auditor_after_p034_p013_triage/`, `current_auditor_after_p034_p026_triage/`
- **P036 current-dataset evaluation (not run):** `docs/evaluation/p036_current_dataset_evaluation.md`
- **P055 current-dataset evaluation (not run):** `docs/evaluation/p055_current_dataset_evaluation.md`
- **P056 current-dataset evaluation (not run):** `docs/evaluation/p056_current_dataset_evaluation.md`
- **P057 current-dataset evaluation (not run):** `docs/evaluation/p057_current_dataset_evaluation.md`
- **P039 current-dataset evaluation (not run):** `docs/evaluation/p039_current_dataset_evaluation.md`
- **P040 current-dataset evaluation (not run):** `docs/evaluation/p040_current_dataset_evaluation.md`
- **P041 current-dataset evaluation (not run):** `docs/evaluation/p041_current_dataset_evaluation.md`
- **P042 current-dataset evaluation (not run):** `docs/evaluation/p042_current_dataset_evaluation.md`
- P030–P042 per-rule evaluations: see `docs/status/current_project_state_and_next_steps.md` (evaluation index)
- EF overlap comparison: `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- EF overlap refinements: `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`,
  `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
