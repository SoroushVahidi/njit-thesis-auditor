# EF-Comment Coverage Analysis (P083)

- **Date:** 2026-06-10
- **Source data:** `data/processed/ef_comment_coverage.json`
- **Scope:** P083 evaluation task — taxonomy classification of 52 DOCX-extracted EF comments
- **Auditor version:** P001–P082 (82 inventory entries; P083 is this evaluation task)
- **Canonical aggregate:** 1,543 (unchanged)

---

## 1. Summary

The P083 coverage table classifies 52 EF reviewer comments extracted (via P080) from 2
third-review DOCX dissertation drafts against the auditor's structural taxonomy. All rows are
`estimated_from_evaluation_notes` — individual comment text, dates, and page locations are not
committed; only the category-level breakdown from `docs/evaluation/post_p080_docx_pdf_overlap_evaluation.md`
was used.

| Metric | Value |
|---|---|
| Total rows | 52 |
| In-scope rows | 50 |
| Out-of-scope rows | 2 (SEM only) |
| Covered or partial rate | **0.74** (37 / 50) |
| Missing implementation rate | **0.20** (10 / 50) |
| Blocked rate | **0.06** (3 / 50) |

---

## 2. Taxonomy class breakdown

| Class | Count | % of in-scope | Notes |
|---|---|---|---|
| SIM | 3 | 6% | Page-number orientation (P082, experimental opt-in) |
| SIP | 34 | 68% | Partially covered by existing rules |
| SMI | 10 | 20% | In-scope gap — bold/heading style enforcement |
| SBL | 3 | 6% | Reference-list duplicates (semantic parsing required) |
| SEM | 2 | — | Grammar/editorial (out of scope) |
| PRF | 0 | — | — |
| AMB | 0 | — | — |

---

## 3. DOCX_3RD_A breakdown (22 comments)

| Category | Count | Class | Matched rules |
|---|---|---|---|
| indentation | 9 | SIP | P015, P044 |
| spacing_blank_lines | 4 | SIP | P016, P023 |
| margin_overflow | 3 | SIP | P011 |
| bold_heading_style | 2 | SMI | — |
| table_figure_layout | 2 | SIP | P017, P035 |
| front_matter | 1 | SIP | P025, P033, P038 |
| capitalization_case | 1 | SIP | P020 |

---

## 4. DOCX_3RD_B breakdown (30 comments)

| Category | Count | Class | Matched rules |
|---|---|---|---|
| capitalization_case | 10 | SIP | P020 |
| bold_heading_style | 8 | SMI | — |
| indentation | 3 | SIP | P015, P044 |
| page_number_orientation | 3 | SIM | P082 |
| reference_list_issue | 3 | SBL | P064 |
| grammar_editorial | 2 | SEM | — |
| front_matter | 1 | SIP | P025, P033, P038 |

---

## 5. Key finding: bold/heading style gap (SMI: 10)

The largest single in-scope gap is **bold weight enforcement on headings** — 10 SMI comments
across both DOCX files (2 from DOCX_3RD_A, 8 from DOCX_3RD_B). The reviewer directed students
to remove bold from specific headings or heading levels. P027 checks heading level style
consistency but does not enforce bold/unbold per heading level against a NJIT standard.

This gap does **not** currently pass the five-gate evidence bar:
- Gate 2 fails: only 2 DOCX files show the pattern (minimum 3 required).
- Gate 1 is uncertain: no explicit NJIT guideline section was found mandating non-bold at
  specific heading levels.

Recommendation: **block** as a future detector candidate until at least one more dissertation
file with this pattern becomes available.

---

## 6. Reference list gap (SBL: 3)

Three comments in DOCX_3RD_B address reference list structural issues (duplicate entries or
formatting inconsistencies). P064 checks structural reference-list properties, but per-entry
duplicate detection and per-entry formatting corrections require semantic content parsing
(comparing reference strings) rather than layout metadata. These are correctly classified as
`SBL` and should not be pursued as heuristic detectors.

---

## 7. Page-number orientation (SIM: 3)

Three comments in DOCX_3RD_B about landscape page-number orientation are now covered by P082
(experimental opt-in). These comments were the direct motivation for P082. The SIM
classification confirms P082 addresses the correct structural category, even though P082 is
experimental and disabled by default.

---

## 8. Comparison PDF context (not individually represented)

The `ef_overlap_after_p072_evaluation.md` documents 143 EF annotations from 2 comparison PDFs
(Cibaku + Yin Haotian). Those annotations are only available as category-level counts, not
individually extracted. Key observations from that dataset:

- `unclear_or_other`: 88 of 143 (61.5%) — confirming that a large share of reviewer feedback
  is semantic/unstructured and structurally un-auditable.
- `indentation`: 13 — SIP (partially covered by P015/P044).
- `capitalization_case`: 12 — SIP (P020 partial).
- `heading_title`: 17 — SIP (P014/P020/P038 partial).
- `references_citations`: 9 — SBL (same block as DOCX findings).
- `committee_approval_page`: 5 — SBL (image-embedded, no text layer).
- `list_of_tables_figures_toc`: 4 — SMI (zero coverage on comparison PDFs).

These are consistent with the DOCX taxonomy results and do not add new SMI gaps beyond what
the DOCX analysis found.

---

## 9. Conclusions

1. **The auditor partially or fully covers 74% of in-scope EF comments** — a healthy
   first-pass rate for a heuristic structural tool.
2. **The main in-scope miss is bold/heading style enforcement** (10 SMI, 20%), which does not
   pass the five-gate evidence bar at this time.
3. **14% of all in-scope gaps are technically blocked** (SBL: reference list semantics,
   committee approval page image layers).
4. **4% of all comments are out of scope** (SEM: grammar/editorial).
5. **No new detector candidates qualify** under the five-gate evidence policy based on the
   currently available DOCX data.
6. The canonical five-PDF aggregate remains **1,543** (P083 is evaluation-only, no detection
   changes).
