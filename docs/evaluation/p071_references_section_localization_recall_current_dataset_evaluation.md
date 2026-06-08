# P071 References Section Localization Recall — Current-Dataset Evaluation

- **Date:** 2026-06-08
- **Baseline commit:** post-P070 main (`2c9a383` — P071 scoped; comparator pre-P071 P064 reach)
- **Comparator baseline:** P064-era five-PDF localization outcomes (`docs/evaluation/p064_current_dataset_evaluation.md`)
- **Auditor scope:** P001–P071 implemented
- **P071 type:** Infrastructure-only (`infrastructure_refinement`); no standalone findings
- **Privacy:** Aggregate-only reporting; no reference entry text quoted
- **Generated outputs (gitignored):** `data/evaluation/generated/p071_evaluation/`

---

## Purpose

Measure P064 localization reach before and after P071 on the documented five-PDF
evaluation set. P071 is infrastructure-only; full-audit aggregate totals are expected to
remain unchanged when P064 still emits zero findings after checks reach.

---

## Five-PDF accessibility

| File label | Accessible | Auditable |
|---|---|---|
| Cibaku Elson 1st Review | Yes | Yes |
| Yin H 2nd Review (flattened) | Yes | Yes |
| Yin Haotian 2nd Review | Yes | Yes |
| Yin H 4th Review (compressed) | Yes | Yes |
| Sebastian Fine clean baseline | Yes | Yes |

All five PDFs were accessible. Sebastian Fine was extracted from
`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip` into the
gitignored `p071_evaluation/` folder.

---

## P064 localization reach (pre-P071 vs post-P071)

| File label | Pre-P071 body start | Post-P071 body start | Pre-P071 heading localized | Post-P071 heading localized | Pre-P071 P064 outcome | Post-P071 P064 outcome |
|---|---|---|---|---|---|---|
| Cibaku Elson 1st Review | Yes | Yes | Yes | Yes | Skip — high x-variance (59.7 pt) | Reached checks; 0 findings |
| Yin H 2nd Review (flattened) | No | Yes | No | Yes (BIBLIOGRAPHY p.103) | Skip — no body region | Reached checks; 0 findings |
| Yin Haotian 2nd Review | No | Yes | No | Yes (BIBLIOGRAPHY p.103) | Skip — no body region | Reached checks; 0 findings |
| Yin H 4th Review (compressed) | Yes | Yes | Yes | Yes | Reached checks; 0 findings | Reached checks; 0 findings |
| Sebastian Fine clean baseline | Yes | Yes | Yes | Yes | Reached checks; 0 findings | Reached checks; 0 findings |
| **Five-PDF total** | **3/5** | **5/5** | **3/5** | **5/5** | **2/5 reached checks** | **5/5 reached checks** |

### Recovery mechanisms observed

| Mechanism | Files affected |
|---|---|
| Collapsed body-start (`CHAPTER1` tolerance) | Yin H 2nd flat, Yin Haotian 2nd |
| Tail-scan BIBLIOGRAPHY fallback | Yin H 2nd flat, Yin Haotian 2nd (also reachable via improved body start) |
| Dominant-cluster x-variance gate | Cibaku (annotation outlier lines no longer trigger skip) |

---

## Post-P071 full-audit aggregate vs post-P070 baseline

| Metric | Post-P070 | Post-P071 | Delta |
|---|---:|---:|---:|
| Total findings (5-PDF) | 1,543 | 1,543 | 0 |
| P064 findings | 0 | 0 | 0 |

Per-file totals unchanged: Cibaku 325, Yin H 2nd flat 281, Yin Haotian 2nd 346,
Yin H 4th comp 532, Sebastian Fine 59.

P071 improves **reach** (P064 checks run on 3 additional files) without changing finding
counts on this dataset because entry formatting remains consistent and no heading-not-detected
condition applies.

---

## EF overlap expectation

The `references_citations` EF category had **9 EF comments with 0 tool findings** on
comparison PDFs (`docs/evaluation/ef_overlap_after_p068_evaluation.md`). P071 addresses
the localization skip that prevented P064 from running on Cibaku and the two Yin 2nd-review
files. Closing the EF gap still requires P064 (or future rules) to emit findings that align
with EF semantic comments — citation style, completeness, and content issues remain outside
P071/P064 v1 scope.

---

## Limitations

- Zero P064 findings after improved reach do **not** prove compliance.
- Image-only or severely degraded references pages may still skip.
- No citation-style enforcement; Q030 remains manual-only.
- Aggregate unchanged on this dataset; reach improvement is the primary measurable outcome.

---

## Cross-references

- P064 evaluation (pre-P071 comparator): `docs/evaluation/p064_current_dataset_evaluation.md`
- P071 scope/design: `docs/planning/p071_references_section_localization_recall_refinement_scope_and_design.md`
- Post-P070 aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md`
