# EF Comment-vs-Tool Overlap Evaluation After P072 (P001–P072)

- **Date:** 2026-06-08
- **Auditor scope:** P001–P072 implemented; **1014 pytest**
- **Baseline commit:** `1476a51` (PR #262 — P072 implementation)
- **Prior overlap doc:** `docs/evaluation/ef_overlap_after_p071_evaluation.md` (P001–P071 scope)
- **P072 current-dataset eval:** `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md`
- **Generated outputs:** `data/evaluation/generated/ef_overlap_after_p072/` (gitignored, not committed)
- **Privacy:** Aggregate-only. No dissertation body text, title text, author names, committee
  names, captions, EF comment text, or reference entry text are quoted anywhere in this document.

---

## 1. Purpose and Scope

This document refreshes the auditor-vs-expert EF overlap comparison after **P072**, the
infrastructure/localization companion to **P068**. P072 adds a structural role-label fallback
to approval-page detection without adding standalone issue types.

The main question: **Did P072 improve `committee_approval_page` overlap on the two EF-comparison
PDFs?** Secondary: confirm all other category metrics are unchanged.

**Comparison set:** Only the two PDFs with machine-extractable EF annotations.

---

## 2. Input Samples and Extractability

| Label | Comment status | EF annotations | Pages |
|---|---|---:|---:|
| Cibaku Elson 1st Review | extractable | 78 | 99 |
| Yin Haotian 2nd Review | extractable | 65 | 108 |

**Total EF annotations:** 143 (unchanged from all prior overlap eras)

Non-extractable PDFs (excluded from this comparison):
- Yin H 2nd Review (flattened): 0 extractable
- Yin H 4th Review (compressed): 0 extractable

---

## 3. Methodology

Same page/category overlap definition as all prior EF overlap docs:

- **Page overlap:** a page overlaps when both EF annotations and tool findings appear on it.
- **Category overlap:** at least one tool finding of the mapped category exists on a page
  where an EF comment of that category was placed.
- **Category mapping:** `src/njit_auditor/evaluation.py` `map_finding_rule_to_category()`;
  P068 maps to `committee_approval_page`.

Generated outputs (gitignored): `data/evaluation/generated/ef_overlap_after_p072/`

---

## 4. Overall Overlap Summary

| Metric | Cibaku | Yin Haotian | Total | P071-era total | Change |
|---|---:|---:|---:|---:|---|
| EF annotations | 78 | 65 | **143** | 143 | 0 |
| Tool findings (P011–P072) | 325 | 346 | **671** | 671 | **0** |
| Pages with EF comments | 42 | 44 | **86** | 86 | 0 |
| Pages with tool findings | 100 | 109 | **209** | 207 | +2 (page-number boundary effect) |
| Pages with both | 42 | 44 | **86** | 86 | 0 |
| EF-only pages | 0 | 0 | **0** | 0 | unchanged |
| Tool-only pages | 58 | 65 | **123** | 121 | +2 |

All EF-comment pages continue to have at least one tool finding (EF-only pages = 0).
The +2 tool-only pages delta is a minor page-number boundary effect; total findings unchanged.

---

## 5. EF Annotation Counts by Category

EF annotation totals are document-fixed; counts are unchanged from all prior eras.

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

---

## 6. Tool Finding Counts by Category (Comparison PDFs)

| Category | Cibaku | Yin Haotian | Total | P071-era total | Change |
|---|---:|---:|---:|---:|---|
| page_numbering | 111 | 119 | **230** | 230 | 0 |
| font_format | 92 | 103 | **195** | 195 | 0 |
| annotations | 78 | 65 | **143** | 143 | 0 |
| margin_or_overflow | 21 | 33 | **54** | 54 | 0 |
| indentation | 8 | 14 | **22** | 22 | 0 |
| heading_title | 5 | 4 | **9** | 9 | 0 |
| spacing_blank_lines | 7 | 6 | **13** | 13 | 0 |
| capitalization_case | 2 | 1 | **3** | 3 | 0 |
| title_page_metadata | 1 | 1 | **2** | 2 | 0 |
| references_citations | 0 | 0 | **0** | 0 | 0 |
| committee_approval_page | 0 | 0 | **0** | 0 | **0** |
| list_of_tables_figures_toc | 0 | 0 | **0** | 0 | 0 |
| frontmatter_structure | 0 | 0 | **0** | 0 | 0 |

**Total tool findings unchanged at 671** (+0 vs P071-era on these two files).

---

## 7. Category Coverage and Page Overlap

| EF category | EF total | Tool findings | Both pages | Coverage status | P071 → P072 change |
|---|---:|---:|---:|---|---|
| unclear_or_other | 88 | n/a | n/a | out of scope / manual-only | none |
| references_citations | 9 | 0 | 0 | still zero coverage | none |
| **committee_approval_page** | **5** | **0** | **0** | **still zero coverage** | **none — P072 fallback found 0 candidates** |
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

## 8. P072 Contribution Summary

### P068 reach on comparison PDFs

| File label | Pre-P072 P068 outcome | Post-P072 P068 outcome | P068 findings |
|---|---|---|---|
| Cibaku Elson 1st Review | Skip — no text-layer role labels | Skip — fallback 0 candidates | 0 |
| Yin Haotian 2nd Review | Skip — no text-layer role labels | Skip — fallback 0 candidates | 0 |

P072 fallback root cause (from five-PDF structural trace):

| File label | Heading gate matches | Eligible pages | Role-label pages | Fallback candidates |
|---|---:|---:|---:|---:|
| Cibaku Elson 1st Review | 0 | 20 | 0 | 0 |
| Yin Haotian 2nd Review | 0 | 108 | 0 | 0 |

All eligible pages return `_mostly_single_token_noise = True` and `role_label_count = 0` —
consistent with image-embedded approval pages lacking a machine-readable text layer.

### EF-overlap impact

| Metric | Pre-P072 (P071 overlap) | Post-P072 | Change |
|---|---|---|---|
| P068 reached comparison PDFs | 0/2 | 0/2 | **none** |
| P068 findings on comparison PDFs | 0 | 0 | 0 |
| `committee_approval_page` tool findings | 0 | 0 | **no change** |
| `committee_approval_page` page overlap | 0 both-pages | 0 both-pages | **no change** |
| Total tool findings (comparison set) | 671 | 671 | 0 |

**Interpretation:** P072 structural fallback scanned all eligible front-matter pages on both
comparison PDFs and found **0 role-label candidates**. The fallback cannot recover approval-page
content that does not exist as machine-readable text. The `committee_approval_page` EF gap
(5 EF comments, 0 tool findings) **persists** because the approval pages on these PDFs are
image-embedded. This is a **text-layer availability constraint**, not a P072 algorithm failure.

---

## 9. Comparison with P071 Overlap

| Metric | P071 era | P072 era | Change |
|---|---|---|---|
| Auditor rules (PDF) | P011–P071 | P011–P072 | +1 rule (P072 infrastructure) |
| EF annotations (comparison set) | 143 | 143 | 0 |
| Tool findings (comparison set) | 671 | 671 | **0** |
| EF-only pages | 0 | 0 | unchanged |
| `committee_approval_page` tool findings | 0 | 0 | **no change** |
| `committee_approval_page` both-pages | 0 | 0 | **no change** |
| `references_citations` tool findings | 0 | 0 | no change |
| P068 reach on comparison PDFs | 0/2 | 0/2 | no change |
| Positive category page overlap | indentation (2), margin_or_overflow (1) | same | unchanged |

---

## 10. High-Volume / Noisy Rules

| Rule | Cibaku | Yin Haotian | Total | Category | EF overlap |
|---|---:|---:|---|---|---|
| P013 | 95 | 104 | 199 | page_numbering | Low intent match; broad page coverage |
| P026 | 92 | 103 | 195 | font_format | Not in EF comment category set |
| P012 | 78 | 65 | 143 | annotations | Self-referential on EF-commented PDFs |
| P011 | 21 | 33 | 54 | margin_or_overflow | 1-page category overlap on Yin Haotian |
| P019 | 8 | 15 | 23 | page_numbering | Low EF intent match |

---

## 11. Remaining EF Gaps

### Persistent automatable gaps

1. **`committee_approval_page` (5 EF comments)** — P068 still skipped on both comparison
   PDFs. P072 structural fallback also returns 0 candidates. Root cause confirmed: approval
   pages are image-embedded with no machine-readable text. OCR is out of scope. This gap
   cannot be closed by further localization work unless the source PDFs are re-submitted
   with a text-layer approval page.

2. **`references_citations` (9 EF comments)** — P064 reaches both comparison PDFs (via P071)
   but emits 0 structural findings. EF comments target citation style, missing entries, or
   content issues not modeled by P064 v1. Q030 manual-only.

3. **`list_of_tables_figures_toc` (4 EF comments on Yin Haotian)** — LoT/LoF/TOC rules and
   P070 parser recall remain at zero on comparison PDFs; list-page detection issue on this
   dataset.

### Recommended next steps

1. Treat `committee_approval_page` EF gap as **structurally blocked** on this dataset.
   No further localization rule will change the result unless source PDFs change.
2. No new infrastructure rule for approval-page detection is warranted without new PDFs
   that have text-layer approval pages with variant headings (the P072 target scenario).
3. Continue `references_citations` semantic scoping as a separate track if prioritized.

---

## 12. Privacy Model

- EF annotation categories reported as aggregate counts only; no comment text quoted.
- Tool finding counts are aggregate; no dissertation body text, names, headings, or reference
  entries quoted.
- Page overlap reported as counts only (not page-number lists).
- Generated audit and comment JSON under `data/evaluation/generated/ef_overlap_after_p072/`
  are gitignored and not committed.
- Real dissertation files were not modified. No OCR. No external network calls.

---

## 13. Limitations

- **Two-file comparison set only** — category distributions may not represent all NJIT patterns.
- **No complete raw+commented pairs** — cannot measure false-positive delta on clean baselines.
- **Heuristic EF categorization** — keyword-based; `unclear_or_other` (88) is a permanent gap.
- **No semantic EF matching** — page/category overlap does not confirm same issue intent.
- **Structural detection ≠ compliance** — P072 proves a structural fallback path exists;
  finding nothing does not prove approval-page compliance.
- **Image-only approval pages** — Cibaku and Yin Haotian comparison PDFs have no text-layer
  approval pages; neither heading gate nor structural fallback can reach them.
- **Flattened PDFs excluded** — Yin H 2nd flattened and Yin H 4th compressed cannot contribute
  EF annotations.

---

## Cross-References

- Prior EF overlap (P071): `docs/evaluation/ef_overlap_after_p071_evaluation.md`
- P072 current-dataset eval: `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md`
- P072 scope/design: `docs/planning/p072_approval_page_heading_gate_recall_refinement_scope_and_design.md`
- Post-P070 full five-PDF aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md`
- Real thesis pairing readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- Category mapping: `src/njit_auditor/evaluation.py`
