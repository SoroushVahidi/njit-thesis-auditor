# Data Inventory and Evaluation Sources (post PR #138)

- Date: 2026-06-05 (metadata refresh after P054 implementation)
- Historical baseline note: PR #47 (`8afdcad165ab`); **current auditor:** P001–P054 implemented, web UI present on `main` (`bbea14b` latest; manifest/eval baseline `00b9c2d`, **614** pytest)
- Scope: repository data organization and evaluation-source status (documentation only)

## 1. Executive summary

This repository contains six major data classes:

1. **Guideline/rule-source data** (`data/raw/guidelines/`) used to derive formatting requirements.
2. **Processed rule inventory data** (`data/processed/rules/`) defining Q001-Q079 inventory rules and project **P001-P054** implementation rules.
3. **EF-commented dissertation data** (`data/raw/ester/`) used for comparison against reviewer feedback.
4. **Clean/no-feedback dissertation baseline data** (zip in `data/raw/ester/`) used for false-positive analysis.
5. **Generated evaluation artifacts** (`data/evaluation/generated/`) used for reproducible snapshots and comparisons.
6. **Private/local-only data paths** (for example `data/evaluation/private/`) reserved for sensitive or local analysis outputs.

Real dissertation files include student names and dissertation body text. They must be handled as **privacy-sensitive** materials; reporting should stay aggregate (counts, page numbers, rule IDs, categories) and should not reproduce dissertation prose.

## 2. Data category table

| Category | Path or location | Examples | Committed vs gitignored vs original-archive-only | Purpose | Privacy risk | Recommended handling |
|---|---|---|---|---|---|---|
| Guideline/rule sources | `data/raw/guidelines/` | NJIT guideline docx/pdf/xlsx files | Committed | Authoritative formatting/process references | Low-Medium | Treat as read-only source material; do not edit in normal implementation PRs. |
| Processed rule inventories | `data/processed/rules/` | `njit_rule_inventory.json`, `project_added_rules.json` | Committed | Machine-readable rule inventory and implementation mapping | Low | Update through controlled rule-inventory workflows only. |
| EF-commented dissertations | `data/raw/ester/` | Cibaku/Yin EF-reviewed PDFs | Committed (subset) | Compare tool findings to human reviewer feedback | High | Keep repo private; avoid quoting dissertation body text. |
| Clean/no-feedback baseline | `data/raw/ester/` | `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | Committed (zip), extracted PDF not committed as standalone | False-positive baseline without EF comments | High | Use for aggregate baseline metrics; keep extracted artifacts out of commits unless explicitly requested. |
| Evaluation generated artifacts | `data/evaluation/generated/` | overlap summaries, per-run audit outputs | Gitignored (`.gitignore`) | Reproducible intermediate outputs for analyses | Medium-High | Keep generated outputs local; commit only curated docs. |
| Evaluation private/local-only | `data/evaluation/private/` | local sensitive datasets (path reserved) | Gitignored by pattern; directory may be absent | Private experiments/sensitive outputs | High | Keep any sensitive/local-only files here; do not commit. |
| Source/evaluation status docs | `docs/sources/`, `docs/evaluation/`, `docs/status/` | audit/evaluation markdown summaries | Committed | Human-readable traceability and status | Medium | Keep privacy-safe, aggregate-only summaries. |
| Original archive extras (not fully committed) | Documented in `docs/sources/ester_materials.md` | additional EF files and process slides | Original-archive-only / not fully committed | Optional expansion dataset and admin context | High | Verify availability before use; do not claim local presence without path evidence. |

## 3. Guideline/rule-source data

Files under `data/raw/guidelines/`:

- `Thesis and Dissertation Formatting Guidelines (WIP).docx` — primary formatting rule source.
- `Titles Examples Level 1 to 5.docx` — heading-level capitalization/style source.
- `Self-Self Assessment Sheet.pdf` — checklist-like formatting criteria source.
- `Front Matter Pages Lorem Ipsum.pdf` — front-matter layout examples/source cues.
- `PhD Title Pages.pdf` — department/title-page variant reference.
- `Dissertation Review Process.pdf` — process/admin reference (not a direct formatting-rule implementation source).
- `PhD Dissertation Process Roadmap .xlsx` — process/admin milestones (not a direct formatting-rule implementation source).

Also present in this folder:

- `Link to PQ ETD Administartor_.docx` — administrative reference.

## 4. Processed rule data

- `data/processed/rules/njit_rule_inventory.json`  
  Source/guideline-derived Q-rule inventory (`Q001-Q079`) with implementation status metadata.
- `data/processed/rules/project_added_rules.json`  
  Project implementation rule set (**P001-P054**) — P001–P054 implemented.

From the strict post-P029 audit plus post-audit updates through P054
(`docs/status/source_to_implementation_coverage_after_p029.md`):

- P-rules: **54/54** implemented (historical audit snapshot listed 29/29 at P029).
- Q-rules: mixed implemented/partial/not-implemented/manual-only status; full source coverage is not complete.

## 5. Commented dissertation data

Committed/referenced EF-commented sources in `data/raw/ester/`:

- `250218 Cibaku Elson First Review.pdf` — comments extractable (used in overlap matching).
- `Yin_Haotian_Second_R_with_EF_Feedback.pdf` — comments extractable (used in overlap matching).
- `260415 Yin H _2nd_review with EF Comments.pdf` — comments documented as flattened/non-extractable.
- `Yin_H_4th_Review_with_EF_comments_compressed.pdf` — comments documented as flattened/compressed non-extractable.
- `260330_YESNO_audit_logic_matrix.xlsx` — rule-matrix source used for processed rule inventory derivation.

Extractability evidence is documented in:

- `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`

## 6. Clean/no-feedback dissertation data

- `data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip` is committed and used as clean/no-feedback baseline input.
- `Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf` is used in evaluation docs as a clean baseline PDF, but is not present in this working tree as a standalone tracked file path.

This baseline is used for false-positive behavior checks and is excluded from EF-comment overlap matching because it contains no EF comments.

## 7. Original archive / not fully committed materials

`docs/sources/ester_materials.md` documents additional EF-annotated files and process materials available in the original archive but not fully committed (size/selection reasons). These should be treated as **archive-referenced only** unless verified by actual repository paths. Do not assume local availability without path evidence.

## 8. Evaluation usage table

| Evaluation dataset/use case | Source set | Current use | Inclusion/exclusion rule | Output location |
|---|---|---|---|---|
| Historical full P001-P029 evaluation across 5 PDFs | EF-commented subset + clean baseline PDF | Rule-volume snapshot at P029 milestone | Historical baseline doc | `docs/evaluation/current_auditor_after_p014_p029_evaluation.md` |
| Per-rule P030-P042 current-dataset evaluations | 5-PDF set (P035: local 4-PDF subset; P036–P042: not run) | Privacy-safe counts per new rule | Aggregate-only; no entry/body text quoted | `docs/evaluation/p030_current_dataset_evaluation.md` through `p042_current_dataset_evaluation.md` |
| Generated audit snapshots | Local PDF runs | All evaluation reruns | Gitignored | `data/evaluation/generated/` |
| Canonical full-triage five-PDF rerun | Same 5-PDF set | Latest JSON/MD with P011+P013+P026 triage | Gitignored; not committed | `data/evaluation/generated/current_auditor_after_p034_p011_triage/` (see `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md`) |
| EF comment-vs-tool overlap | Extractable-comment PDFs only | Page/category overlap against extractable EF comments | Excludes flattened-comment PDFs from comment extraction logic | `docs/evaluation/current_ef_comment_vs_tool_comparison.md` + `data/evaluation/generated/current_ef_comment_comparison/` (gitignored) |
| EF overlap refinement round 1 | Extractable PDFs + clean baseline | P013 noise-reduction impact measurement | Clean baseline included for stability/noise check; no EF-overlap role | `docs/evaluation/ef_overlap_driven_refinement_evaluation.md` + `data/evaluation/generated/ef_overlap_refinement/` (gitignored) |
| EF overlap refinement round 2 | Extractable PDFs + clean baseline | P018/P024 heading-variant robustness impact | Flattened-comment PDFs not used for comment extraction | `docs/evaluation/ef_overlap_refinement_round2_evaluation.md` + `data/evaluation/generated/ef_overlap_refinement_round2/` (gitignored) |

## 9. Privacy and reporting policy

1. Do not quote dissertation body text in docs/reports/tests.
2. Do not commit generated full audit outputs unless explicitly requested.
3. Prefer aggregate counts, page numbers, rule IDs, and high-level categories.
4. Keep private/local-only data in gitignored locations such as `data/evaluation/private/`.
5. Do not make the repository public without reviewing student-data handling.
6. Raw guideline/data files should not be modified by normal implementation PRs.

## 10. Recommended next 3 data/evaluation tasks

1. Create a machine-readable manifest for committed evaluation PDFs with comment-extractability status and intended evaluation role.
2. Add a privacy-safe evaluation dataset index (dataset, commit/date, run purpose, output path) for documented runs.
3. Expand EF-overlap evaluation only with additional extractable-comment PDFs, while keeping generated raw outputs under gitignored paths.
