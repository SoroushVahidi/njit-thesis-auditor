# P068 — Approval Page Committee Blocks: Current-Dataset Evaluation

**Rule:** P068  
**Module:** `njit_auditor.rules.pdf_approval_page_committee_blocks`  
**Issue types:** `approval_page_advisor_role_label_missing`, `approval_page_signature_blocks_sparse`  
**Evaluation date:** 2026-06-08  
**Status:** **Not run** — evaluation PDFs are not present in the workspace at implementation time.

---

## Planned dataset

Same five-PDF evaluation set used for post-P067 aggregate snapshots:

| File label | Expected availability |
|---|---|
| Cibaku Elson 1st Review | Direct when `data/raw/ester/` PDFs are present locally |
| Yin H 2nd Review (flattened) | Direct |
| Yin Haotian 2nd Review | Direct |
| Yin H 4th Review (compressed) | Direct |
| Sebastian Fine clean baseline | Extracted from tracked ZIP (gitignored output) |

---

## Evaluation plan (pending)

When PDFs are available locally:

1. Run `njit-audit pdf` per file and extract P068-only counts.
2. Record per file: unique `APPROVAL PAGE` detected (Y/N), `role_label_count`,
   `signature_date_indicator_count`, findings by issue type.
3. Write aggregate-only summary here; store generated JSON under
   `data/evaluation/generated/p068_evaluation/` (gitignored).

**Privacy:** No approval-page text, committee names, or EF comments in the evaluation doc.

---

## Expected gate behavior

P068 may skip files when:

- no unique `APPROVAL PAGE` heading is detected in the text layer
- approval body lines are sparse or noisy
- fewer than two role-label template phrases are found

Zero findings after a skip do not prove compliance.
