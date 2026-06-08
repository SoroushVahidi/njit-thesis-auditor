# EF Comment-vs-Tool Overlap Evaluation After P071 (P001–P071)

- **Date:** 2026-06-08
- **Auditor scope:** P001–P071 implemented; **1000 pytest**
- **Baseline commit:** `08c1a8d` (PR #256 — P071 references section localization recall)
- **Prior overlap doc:** `docs/evaluation/ef_overlap_after_p068_evaluation.md` (P001–P068 scope)
- **P070-era aggregate snapshot:** `docs/evaluation/current_auditor_after_p070_evaluation.md` (1,543 findings; commit `b0ec5e4`)
- **P071 localization eval:** `docs/evaluation/p071_references_section_localization_recall_current_dataset_evaluation.md`
- **Privacy:** Aggregate-only. No dissertation body text, title text, author names, committee
  names, captions, EF comment text, or reference entry text are quoted anywhere in this document.

---

## 1. Purpose and Scope

This document refreshes the auditor-vs-expert EF overlap comparison after **P071**, the
infrastructure/localization companion to **P064**. P071 improves references-section localization
(collapsed body-start matching, back-matter tail heading fallback, cluster-based x-variance gating)
without adding standalone issue types.

The main question: **Did P071 improve the `references_citations` EF gap now that P064 reaches the
two extractable-comment comparison PDFs?**

**Comparison set:** Only the two PDFs with machine-extractable EF annotations. Flattened and
compressed variants are excluded from comment matching.

---

## 2. Input Samples and Extractability

| Label | Comment status | EF annotations | Pages |
|---|---|---:|---:|
| Cibaku Elson 1st Review | extractable | 78 | 99 |
| Yin Haotian 2nd Review | extractable | 65 | 108 |

**Total EF annotations:** 143 (unchanged from P029/P063/P068 eras)

Non-extractable PDFs (excluded from this comparison):
- Yin H 2nd Review (flattened): 0 extractable
- Yin H 4th Review (compressed): 0 extractable

---

## 3. Methodology

Same page/category overlap definition as prior EF overlap docs:

- **Page overlap:** a page overlaps when both EF annotations and tool findings appear on it.
- **Category overlap:** at least one tool finding of the mapped category exists on a page
  where an EF comment of that category was placed.
- **Category mapping:** `src/njit_auditor/evaluation.py` `map_finding_rule_to_category()`;
  P064 maps to `references_citations`.

Generated outputs (gitignored): `data/evaluation/generated/ef_overlap_after_p071/`

---

## 4. Overall Overlap Summary

| Metric | Cibaku | Yin Haotian | Total | P068-era total | Change |
|---|---:|---:|---:|---:|---|
| EF annotations | 78 | 65 | **143** | 143 | 0 |
| Tool findings (P011–P071) | 325 | 346 | **671** | 671 | **0** |
| Pages with EF comments | 42 | 44 | **86** | 86 | 0 |
| Pages with tool findings | 99 | 108 | **207** | 207 | 0 |
| Pages with both | 42 | 44 | **86** | 86 | 0 |
| EF-only pages | 0 | 0 | **0** | 0 | unchanged |
| Tool-only pages | 57 | 64 | **121** | 121 | 0 |

All EF-comment pages continue to have at least one tool finding (EF-only pages = 0 on both
files). Overall page overlap is unchanged from the P068-era refresh.

---

## 5. EF Annotation Counts by Category

| Category | Cibaku | Yin Haotian | Total |
|---|---:|---:|---:|
| unclear_or_other | 53 | 35 | **88** |
| heading_title | 11 | 6 | **17** |
| capitalization_case | 9 | 3 | **12** |
| references_citations | 5 | 4 | **9** |
| committee_approval_page | 3 | 2 | **5** |
| indentation | 2 | 11 | **13** |
| spacing_blank_lines | 0 | 7 | **7** |
| table_format | 1 | 6 | **7** |
| list_of_tables_figures_toc | 0 | 4 | **4** |
| figure_format | 2 | 0 | **2** |
| acknowledgements | 1 | 1 | **2** |
| margin_or_overflow | 0 | 1 | **1** |
| punctuation | 0 | 4 | **4** |

EF annotation totals are static (document-fixed); counts are unchanged from P068.

---

## 6. Tool Finding Counts by Category (Comparison PDFs)

| Category | Cibaku | Yin Haotian | Total | P068-era total |
|---|---:|---:|---:|---:|
| page_numbering | 111 | 119 | **230** | 230 |
| font_format | 92 | 103 | **195** | 195 |
| annotations | 78 | 65 | **143** | 143 |
| margin_or_overflow | 21 | 33 | **54** | 54 |
| indentation | 8 | 14 | **22** | 22 |
| heading_title | 5 | 4 | **9** | 9 |
| spacing_blank_lines | 7 | 6 | **13** | 13 |
| capitalization_case | 2 | 1 | **3** | 3 |
| title_page_metadata | 1 | 1 | **2** | 2 |
| references_citations | 0 | 0 | **0** | 0 |
| committee_approval_page | 0 | 0 | **0** | 0 |
| list_of_tables_figures_toc | 0 | 0 | **0** | 0 |
| frontmatter_structure | 0 | 0 | **0** | 0 |

**Total tool findings unchanged at 671** (+0 vs P068-era on these two files).

---

## 7. Category Coverage and Page Overlap

| EF category | EF total | Tool findings | Both pages | Coverage status | P068 → P071 change |
|---|---:|---:|---:|---|---|
| unclear_or_other | 88 | n/a | n/a | out of scope / manual-only | none |
| references_citations | 9 | 0 | 0 | **still zero coverage** | localization improved; count unchanged |
| committee_approval_page | 5 | 0 | 0 | **still zero coverage** | none |
| list_of_tables_figures_toc | 4 | 0 | 0 | still zero on comparison PDFs | none |
| heading_title | 17 | 9 | 0 | partially covered | none |
| capitalization_case | 12 | 3 | 0 | partially covered | none |
| indentation | 13 | 22 | **2** | partially covered | none (2-page overlap preserved on Yin Haotian) |
| spacing_blank_lines | 7 | 13 | 0 | partially covered (mechanical) | none |
| table_format | 7 | 0 | 0 | partial rules exist; 0 on these PDFs | none |
| margin_or_overflow | 1 | 54 | **1** | partially covered | none (1-page overlap preserved) |
| figure_format | 2 | 0 | 0 | partial rules; 0 on these PDFs | none |
| acknowledgements | 2 | 0 | 0 | not modeled as EF category in tool map | none |
| font_format | — | 195 | 0 | tool-only high-volume | none |
| page_numbering | — | 230 | 0 | tool-only high-volume | none |
| annotations | — | 143 | n/a | self-referential (P012) | none |

---

## 8. P071 Contribution Summary

### P064 reach on comparison PDFs (localization vs findings)

| File label | Pre-P071 P064 outcome | Post-P071 P064 outcome | P064 findings |
|---|---|---|---|
| Cibaku Elson 1st Review | Skip — high x-variance (annotation outlier lines) | Reached checks | 0 |
| Yin Haotian 2nd Review | Skip — no body region detected | Reached checks | 0 |

P071 recovery mechanisms on these files (from five-PDF localization eval):

| Mechanism | Files affected on comparison set |
|---|---|
| Dominant-cluster x-variance gate | Cibaku |
| Collapsed body-start + tail BIBLIOGRAPHY fallback | Yin Haotian 2nd Review |

### EF-overlap impact

| Metric | Pre-P071 (P068 overlap) | Post-P071 | Change |
|---|---|---|---|
| P064 reached comparison PDFs | 0/2 | **2/2** | +2 files |
| P064 findings on comparison PDFs | 0 | 0 | 0 |
| `references_citations` tool findings | 0 | 0 | **no change** |
| `references_citations` category page overlap | 0 both-pages | 0 both-pages | **no change** |
| Total tool findings (comparison set) | 671 | 671 | 0 |

**Interpretation:** P071 successfully closes the **localization skip** that blocked P064 on both
comparison PDFs. P064 now runs entry/heading checks and emits **zero findings** because the
references sections pass structural gates on this dataset. The `references_citations` EF gap
(9 EF comments, 0 tool findings) **persists** because EF comments in this category are largely
**style, completeness, and content-level** issues outside P064/P071 v1 scope. **Q030 remains
manual-only**; no future P-rule should attempt APA/IEEE/MLA enforcement without explicit scope.

---

## 9. Comparison with P068 Overlap

| Metric | P068 era | P071 era | Change |
|---|---|---|---|
| Auditor rules (PDF) | P011–P068 | P011–P071 | +3 rules (P069–P071 infrastructure) |
| EF annotations (comparison set) | 143 | 143 | 0 |
| Tool findings (comparison set) | 671 | 671 | **0** |
| EF-only pages | 0 | 0 | unchanged |
| `references_citations` tool findings | 0 | 0 | **no change** |
| `references_citations` both-pages | 0 | 0 | **no change** |
| P064 reach on comparison PDFs | 0/2 | 2/2 | **improved localization** |
| `committee_approval_page` tool findings | 0 | 0 | no change |
| `list_of_tables_figures_toc` tool findings | 0 | 0 | no change |
| Positive category page overlap | indentation (2), margin_or_overflow (1) | same | unchanged |

**Key takeaway:** P071 improved P064 **reach** on the comparison PDFs but did **not** change
EF-comment category overlap metrics. The persistent `references_citations` gap is now better
understood as a **semantic/style mismatch**, not a localization failure.

---

## 10. High-Volume / Noisy Rules

| Rule | Cibaku | Yin Haotian | Total | Category | EF overlap |
|---|---:|---:|---|---|---|
| P013 | 95 | 104 | 199 | page_numbering | Low intent match; broad page coverage |
| P026 | 92 | 103 | 195 | font_format | Not in EF comment category set |
| P012 | 78 | 65 | 143 | annotations | Self-referential on EF-commented PDFs |
| P011 | 21 | 33 | 54 | margin_or_overflow | 1-page category overlap on Yin Haotian |
| P019 | 8 | 15 | 23 | page_numbering | Low EF intent match |

These rules dominate finding volume but have low correspondence to EF annotation intent.
Reporting triage rollups (`p013_triage`, `p026_font_triage`) remain available.

---

## 11. Remaining EF Gaps

### Persistent automatable gaps

1. **`references_citations` (9 EF comments)** — P064 now runs on both comparison PDFs but emits
   0 structural findings. EF comments likely target citation style, missing entries, or content
   issues not modeled by P064 v1. **No additional infrastructure rule is indicated** until a
   scoped structural check beyond indentation/spacing/heading is defined. Q030 manual-only.

2. **`committee_approval_page` (5 EF comments)** — P068 still skipped on both comparison PDFs
   (APPROVAL PAGE heading not detected). P069 heading-gate recall did not change comparison-PDF
   overlap counts.

3. **`list_of_tables_figures_toc` (4 EF comments on Yin Haotian)** — LoT/LoF/TOC rules
   (P030–P062) and P070 parser recall remain at zero on comparison PDFs; parser/list-page
   detection issue on this dataset, not absent rules.

### Recommended next steps

1. Treat `references_citations` EF gap as **partially addressed** — localization fixed; semantic
  /style coverage remains manual or requires explicitly scoped future rules (not P072 by default).
2. Continue front-matter heading-gate / approval-page detection work if `committee_approval_page`
   automation is prioritized.
3. Expand extractable-comment comparison set (e.g., Sebastian Fine EF archive PDF) for metric
   stability.
4. Investigate LoT/LoF/TOC list-page detection on comparison PDFs as a separate track from P071.

---

## 12. Privacy Model

- EF annotation categories reported as aggregate counts only; no comment text quoted.
- Tool finding counts are aggregate; no dissertation body text, names, headings, or reference
  entries quoted.
- Page overlap reported as counts only (not page-number lists).
- Generated audit and comment JSON under `data/evaluation/generated/ef_overlap_after_p071/`
  are gitignored and not committed.
- Real dissertation files were not modified. No OCR. No external network calls.

---

## 13. Limitations

- **Two-file comparison set only** — category distributions may not represent all NJIT patterns.
- **No complete raw+commented pairs** — cannot measure false-positive delta on clean baselines
  for the same student document.
- **Heuristic EF categorization** — keyword-based; `unclear_or_other` (88) is a permanent gap.
- **No semantic EF matching** — page/category overlap does not confirm same issue intent.
- **Localization ≠ coverage** — P071 proves P064 can reach references sections; zero P064
  findings do not prove references compliance.
- **Structural checks ≠ citation style** — P064 does not enforce APA/IEEE/ACM/MLA; Q030 manual-only.
- **Flattened PDFs excluded** — Yin H 2nd flattened and Yin H 4th compressed cannot contribute
  EF annotations despite high aggregate finding counts on the latter.

---

## Cross-References

- Prior EF overlap (P068): `docs/evaluation/ef_overlap_after_p068_evaluation.md`
- P071 localization eval: `docs/evaluation/p071_references_section_localization_recall_current_dataset_evaluation.md`
- Post-P070 full five-PDF aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md`
- Real thesis pairing readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- EF overlap comparison utility: `scripts/evaluate_current_ef_comment_overlap.py`
- Category mapping: `src/njit_auditor/evaluation.py`
