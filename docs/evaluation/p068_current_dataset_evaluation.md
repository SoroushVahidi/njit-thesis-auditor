# P068 — Approval Page Committee Blocks: Current-Dataset Evaluation

**Date:** 2026-06-08  
**Baseline commit:** `cefc16c` (PR #243 — P068 implemented)  
**Validation status:** ruff clean, mypy clean, **963 pytest** passed  
**Rule:** P068 — Approval Page committee/signature-block structural check  
**Module:** `njit_auditor.rules.pdf_approval_page_committee_blocks`  
**Issue types:** `approval_page_advisor_role_label_missing`, `approval_page_signature_blocks_sparse`  
**Generated artifacts (gitignored):** `data/evaluation/generated/p068_evaluation/`

---

## Purpose

Run the implemented P068 heuristic on the documented five-PDF evaluation set and record only
privacy-safe aggregate results. No approval-page text, committee names, advisor names,
signatures, dates from real files, title text, or department/program text are quoted.

---

## Evaluated Files

| File label | Pages | Accessible | Source |
|---|---:|---|---|
| Cibaku Elson 1st Review | 99 | Yes | tracked PDF |
| Yin H 2nd Review (flattened) | 108 | Yes | tracked PDF |
| Yin Haotian 2nd Review | 108 | Yes | tracked PDF |
| Yin H 4th Review (compressed) | 137 | Yes | tracked PDF |
| Sebastian Fine clean baseline | 29 | Yes | extracted from tracked ZIP |

All five evaluation PDFs were accessible. Sebastian Fine was extracted from
`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`
into `data/evaluation/generated/p068_evaluation/sebastian_fine_clean.pdf`
(gitignored; not committed).

---

## P068 Findings by File

| File label | Accessible | Approval Page detected | Advisor-role check | Signature-block check | P068 findings | Notes |
|---|---|---|---|---:|---:|---|
| Cibaku Elson 1st Review | Yes | No | Skipped | Skipped | 0 | No machine-readable `APPROVAL PAGE` heading |
| Yin H 2nd Review (flattened) | Yes | No | Skipped | Skipped | 0 | No machine-readable `APPROVAL PAGE` heading |
| Yin Haotian 2nd Review | Yes | No | Skipped | Skipped | 0 | No machine-readable `APPROVAL PAGE` heading |
| Yin H 4th Review (compressed) | Yes | Yes (page 5) | Passed | Ran | 1 | Advisor role detected; 5 role labels; 0 signature/date indicators |
| Sebastian Fine clean baseline | Yes | Yes (page 5) | Ran | Ran | 2 | 4 role labels; no advisor-role phrase; 0 signature/date indicators |

**Total P068 findings: 3**

---

## Issue Type Breakdown

| Issue type | Count |
|---|---:|
| `approval_page_signature_blocks_sparse` | 2 |
| `approval_page_advisor_role_label_missing` | 1 |

---

## Detection Gate Summary

| Metric | Value |
|---|---:|
| PDFs evaluated | 5 |
| PDFs accessible | 5 |
| Unique `APPROVAL PAGE` detected | 2/5 |
| No `APPROVAL PAGE` heading detected | 3/5 |
| Ambiguous/multiple headings | 0/5 |
| Files reaching structural checks | 2/5 |

### Files with detected Approval Page

**Yin H 4th Review (compressed) — page 5**

- Role-label template phrases detected: 5
- Advisor-role phrase detected: yes
- Signature/date/blank indicators: 0 (date labels 0, signature labels 0, blank lines 0)
- Confidence: low
- Finding: `approval_page_signature_blocks_sparse` (1)

**Sebastian Fine clean baseline — page 5**

- Role-label template phrases detected: 4
- Advisor-role phrase detected: no
- Signature/date/blank indicators: 0
- Confidence: low
- Findings: `approval_page_advisor_role_label_missing` (1), `approval_page_signature_blocks_sparse` (1)

### Files skipped at detection gate

Three PDFs were skipped because `find_named_frontmatter_headings()` did not detect a
machine-readable standalone `APPROVAL PAGE` heading in the text layer. This is a known
limitation shared with P038 (required front-matter heading presence) on compressed or
flattened EF-comment PDFs where approval-page headings may be image-rendered or use
nonstandard formatting.

---

## Interpretation

P068 **did fire** on the current dataset: **3 findings** across **2/5** files.

- **3/5 files** produced zero findings because the Approval Page detection gate was not met.
  Zero findings on those files do **not** prove compliance.
- **2/5 files** reached structural checks. Both detected role-label phrases but found **zero**
  date/signature/underscore-blank indicators in the text layer, triggering sparse-block warnings.
- On Sebastian Fine, committee-member role labels were detected but no advisor-role template
  phrase (`dissertation advisor`, `doctoral dissertation advisor`, `major professor`) matched
  the curated prefix list.
- Likely text-layer limitations: signature lines and date fields on approval pages are often
  image-rendered, handwritten, or formatted outside the structural indicators P068 counts.
  Compressed/flattened PDFs may further reduce extractable structure.

---

## Privacy / Limitations

- Generated raw outputs remain uncommitted under `data/evaluation/generated/p068_evaluation/`
  (gitignored via `data/evaluation/generated/`).
- Sebastian Fine clean baseline was extracted locally from the tracked ZIP only.
- No approval-page text, committee names, advisor names, signatures, dates, title text,
  department text, or EF comment text were committed.
- P068 does not verify committee identity, signature authenticity, advisor-first ordering,
  date correctness, or semantic approval claims.
- Findings on this dataset used low confidence because role labels were detected without
  matching signature/date structural indicators.
