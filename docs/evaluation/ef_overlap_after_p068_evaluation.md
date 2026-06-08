# EF Comment-vs-Tool Overlap Evaluation After P068 (P001–P068)

- **Date:** 2026-06-08
- **Auditor scope:** P001–P068 implemented; **963 pytest**
- **Baseline commit:** `6446c24` (PR #247 — real-thesis pairing readiness refresh)
- **Prior overlap doc:** `docs/evaluation/ef_overlap_after_p063_evaluation.md` (P001–P063 scope)
- **P068-era aggregate snapshot:** `docs/evaluation/current_auditor_after_p068_evaluation.md` (1,590 findings; commit `5d8ebaf`)
- **Privacy:** Aggregate-only. No dissertation body text, title text, author names, committee
  names, captions, or EF comment text are quoted anywhere in this document.

---

## 1. Purpose and Scope

This document refreshes the auditor-vs-expert EF overlap comparison that was last performed at
the P063 era. Since that comparison, five additional rules (P064–P068) were implemented:

| Rule | Category mapping | Issue focus |
|---|---|---|
| P064 | `references_citations` | Reference-section structural checks |
| P065 | `frontmatter_structure` | Dedication centering/italic |
| P066 | `frontmatter_structure` | Bio Sketch degree ordering |
| P067 | `frontmatter_structure` | Bio Sketch publication ordering |
| P068 | `committee_approval_page` | Approval Page committee/signature blocks |

The purpose is to measure whether P064–P068 changed EF-comment category coverage on the two
extractable-comment comparison PDFs, especially `references_citations` and
`committee_approval_page`.

**Comparison set:** Only the two PDFs with machine-extractable EF annotations. Flattened and
compressed variants are excluded from comment matching (aggregate audit counts only).

---

## 2. Input Samples and Extractability

| Label | Comment status | EF annotations | Pages |
|---|---|---:|---:|
| Cibaku Elson 1st Review | extractable | 78 | 99 |
| Yin Haotian 2nd Review | extractable | 65 | 108 |

**Total EF annotations:** 143 (unchanged from P029/P063 eras)

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
  P064–P068 mappings added as documented in section 1.

Generated outputs (gitignored): `data/evaluation/generated/ef_overlap_after_p068/`

---

## 4. Overall Overlap Summary

| Metric | Cibaku | Yin Haotian | Total |
|---|---:|---:|---:|
| EF annotations | 78 | 65 | **143** |
| Tool findings (P011–P068) | 325 | 346 | **671** |
| Pages with EF comments | 42 | 44 | **86** |
| Pages with tool findings | 99 | 108 | **207** |
| Pages with both | 42 | 44 | **86** |
| EF-only pages | 0 | 0 | **0** |
| Tool-only pages | 57 | 64 | **121** |

All EF-comment pages continue to have at least one tool finding (EF-only pages = 0 on both
files). This is unchanged from the P063-era overlap.

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

EF annotation totals are static (document-fixed); counts are unchanged from P063.

---

## 6. Tool Finding Counts by Category (Comparison PDFs)

| Category | Cibaku | Yin Haotian | Total | P063-era total |
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

**Total tool findings unchanged at 671** (+0 vs P063-era on these two files).

---

## 7. Category Coverage and Page Overlap

| EF category | EF total | Tool findings | Both pages | Coverage status | P063 → P068 change |
|---|---:|---:|---:|---|---|
| unclear_or_other | 88 | n/a | n/a | out of scope / manual-only | none |
| references_citations | 9 | 0 | 0 | **still zero coverage** | none — P064 fired 0 on both files |
| committee_approval_page | 5 | 0 | 0 | **still zero coverage** | none — P068 fired 0 on both files |
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

## 8. P064–P068 Contribution Summary

| Rule | Cibaku findings | Yin Haotian findings | Fired on comparison PDFs? | EF-overlap impact |
|---|---:|---:|---|---|
| P064 | 0 | 0 | No | `references_citations` gap unchanged (9 EF, 0 tool) |
| P065 | 0 | 0 | No — DEDICATION heading gate skip | `frontmatter_structure` unchanged |
| P066 | 0 | 0 | No — BIOGRAPHICAL SKETCH heading gate skip | `frontmatter_structure` unchanged |
| P067 | 0 | 0 | No — Publications boundary not reached | `frontmatter_structure` unchanged |
| P068 | 0 | 0 | No — APPROVAL PAGE heading gate skip | `committee_approval_page` gap unchanged on comparison PDFs |

**P068 on full five-PDF set (context):** P068 added **3** findings on Sebastian Fine clean
baseline (2) and Yin H 4th Review compressed (1) in the post-P068 aggregate snapshot. Those
files are excluded from EF-comment extraction; the comparison PDFs did not receive P068
findings.

**Interpretation:** P064–P068 did not change EF-overlap metrics on the two extractable-comment
PDFs. All five rules were skipped by conservative detection gates on this comparison set
(reference-section localization, DEDICATION heading, BIOGRAPHICAL SKETCH heading, Publications
boundary, APPROVAL PAGE heading).

---

## 9. Comparison with P063 Overlap

| Metric | P063 era | P068 era | Change |
|---|---|---|---|
| Auditor rules (PDF) | P011–P063 | P011–P068 | +5 rules |
| EF annotations (comparison set) | 143 | 143 | 0 |
| Tool findings (comparison set) | 671 | 671 | **0** |
| EF-only pages | 0 | 0 | unchanged |
| `references_citations` tool findings | 0 | 0 | **no change** |
| `committee_approval_page` tool findings | 0 | 0 | **no change** |
| `list_of_tables_figures_toc` tool findings | 0 | 0 | no change |
| Positive category page overlap | indentation (2), margin_or_overflow (1) | same | unchanged |

**Key takeaway:** The P064–P068 rule expansion did not shift EF-comment category overlap on
the two extractable-comment PDFs. Persistent gaps remain `references_citations` (9 EF comments)
and `committee_approval_page` (5 EF comments), both blocked by heading/text-layer detection
gates on this dataset rather than absent rule logic.

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

## 11. Remaining EF Gaps and P069 Justification

### Persistent automatable gaps

1. **`references_citations` (9 EF comments)** — P064 implemented but skipped on both
   comparison PDFs (reference-section heading/entry gates not met). Highest-priority
   automatable miss after `unclear_or_other`.

2. **`committee_approval_page` (5 EF comments)** — P068 implemented but skipped on both
   comparison PDFs (APPROVAL PAGE heading not detected). P068 fired only on non-comparison
   files in the five-PDF aggregate.

3. **`list_of_tables_figures_toc` (4 EF comments on Yin Haotian)** — LoT/LoF/TOC rules
   (P030–P062) remain at zero on comparison PDFs; parser recall issue, not absent rules.

### Heading-gate skip pattern (P069 justification)

| Rule | Skip reason on comparison PDFs |
|---|---|
| P065 | No machine-readable standalone DEDICATION heading |
| P066 | BIOGRAPHICAL SKETCH heading not detected |
| P067 | Publications/Presentations boundary not reached |
| P068 | APPROVAL PAGE heading not detected |

This reinforces the scoped **P069 front-matter heading gate recall** infrastructure task:
`docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md`.

### Recommended next steps

1. Implement P069 heading-gate recall refinement.
2. Refresh EF overlap again after P069 on the same two extractable-comment PDFs.
3. Extract and test Sebastian Fine EF-annotated PDF from original archive to expand comparison set.
4. Investigate LoT/LoF/TOC entry-extraction recall as a separate parser track.

---

## 12. Privacy Model

- EF annotation categories reported as aggregate counts only; no comment text quoted.
- Tool finding counts are aggregate; no dissertation body text, names, or headings quoted.
- Page overlap reported as counts only (not page-number lists) except where prior docs
  established the same aggregate methodology.
- Generated audit and comment JSON under `data/evaluation/generated/ef_overlap_after_p068/`
  are gitignored and not committed.
- Real dissertation files were not modified. No OCR. No external network calls.

---

## 13. Limitations

- **Two-file comparison set only** — category distributions may not represent all NJIT patterns.
- **No complete raw+commented pairs** — cannot measure false-positive delta on clean baselines
  for the same student document.
- **Heuristic EF categorization** — keyword-based; `unclear_or_other` (88) is a permanent gap.
- **No semantic EF matching** — page/category overlap does not confirm same issue intent.
- **Zero coverage may reflect gates** — P064–P068 skips do not prove rules are absent; they
  prove the comparison PDFs did not expose the required text-layer signals.
- **Flattened PDFs excluded** — Yin H 2nd flattened and Yin H 4th compressed cannot contribute
  EF annotations despite high aggregate finding counts on the latter.

---

## Cross-References

- Prior EF overlap (P063): `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- P068-era full five-PDF aggregate: `docs/evaluation/current_auditor_after_p068_evaluation.md`
- Real thesis pairing readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- P069 scope: `docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md`
- EF overlap comparison utility: `scripts/evaluate_current_ef_comment_overlap.py`
- Category mapping: `src/njit_auditor/evaluation.py`
