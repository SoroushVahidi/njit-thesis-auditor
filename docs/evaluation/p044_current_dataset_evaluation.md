# P044 Current Dataset Evaluation (see gap-fill for five-PDF results)

> **Gap-fill evaluation (2026-06-09, commit `85a1326`):** Full five-PDF current-dataset audit now complete.
> P044 total: **7** findings on all five files (`abstract_subsequent_paragraph_not_indented`: 6, `abstract_first_paragraph_indented`: 1).
> See `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`.

- **Date:** 2026-06-03
- **Rule:** P044 — Abstract page paragraph indentation (Q002/Q003)
- **Status:** **No canonical audit run** — only 4 of 5 evaluation PDFs are directly accessible; Sebastian Fine Revised is ZIP-only
- **Baseline main at implementation:** `8485e52` (PR #120)

---

## Evaluation status

No P044 current-dataset finding counts are available. A canonical five-PDF run requires all
five evaluation PDFs to be directly accessible. At the time of implementation:

- 4 PDFs are directly accessible in `data/raw/ester/`
- The fifth (Sebastian Fine Revised) is archive-contained in
  `Dissertations with no Feedback -20260529T012213Z-3-001.zip` and not committed as a
  standalone tracked file

A partial non-canonical 4-PDF run could be performed (as with P035), but was deferred
because a new rule (P045 or subsequent) was not yet ready, and the project already has a
documented non-canonical subset pattern from P035.

**What was validated:**

- 9 synthetic unit tests covering the P044 gate conditions, Q002/Q003 issue types, correct
  format (no findings), single-paragraph gate (Q003 skipped), pre-heading text exclusion,
  finding metadata privacy, and source_q_rule_id fields. All pass.
- `ruff check .` — clean
- `mypy src` — clean (58 source files)
- `python -m pytest` — **507 passed**

---

## Canonical aggregate baseline (unchanged)

| Field | Value |
|-------|-------|
| Canonical pre-P035/…/P044 five-PDF aggregate | **1,446** total findings |
| `generated_for_commit` | `00b9c2d` |
| Canonical eval doc | `docs/evaluation/current_auditor_after_p034_evaluation.md` |

P044 does not alter the canonical 1,446 baseline. The baseline was established before P035
and has not been updated by a full P001–P044 rerun. The next full rerun should target a
gitignored output under `data/evaluation/generated/` and must not commit generated JSON/MD.

---

## P044 v1 limitations

| Limitation | Detail |
|-----------|--------|
| Heading detection gate | Emits nothing if ABSTRACT heading is not in the text layer (compressed/flattened PDFs) |
| Q003 paragraph block gate | Skips Q003 check if fewer than 2 paragraph blocks found; many abstracts are single-paragraph |
| Indented-first-paragraph styles | Some disciplines use uniformly indented abstract paragraphs; INDENT_THRESHOLD_PT=18pt reduces FP risk |
| Continuation lines only | Considers first-line x-position of each paragraph block; not a full paragraph-flow analysis |
| Left-margin derivation | Left margin is the minimum x0 across all body lines; may be affected by very short lines |
| P015 overlap | P015 may also flag the abstract opening paragraph via `unexpected_opening_indent`; P044 uses distinct issue types and does not conflict |

---

## Privacy

Findings from P044 contain geometry metadata only:
`page_number`, `issue_type`, `paragraph_index`, `observed_x0`, `expected_left_margin`,
`indent_delta_points`, `required_indent_points`, `triage_tier`, `source_q_rule_id`.
No Abstract paragraph text, thesis title, author names, or other private content is quoted.

Generated audit outputs remain gitignored under `data/evaluation/generated/` and were not
committed.

---

## Future canonical rerun

When all five evaluation PDFs are directly accessible:

1. Run `njit-audit pdf` on the five canonical evaluation PDFs.
2. Collect P044 aggregate counts only (no per-PDF abstract text).
3. Save outputs to `data/evaluation/generated/current_auditor_after_p044/` (gitignored).
4. Add a summary of aggregate P044 counts to this doc.
5. Do **not** update `generated_for_commit` unless the run is complete and validated.

If only 4 PDFs remain accessible and a partial run is performed, label the results
explicitly as non-canonical (4-PDF subset) as per the P035 precedent.
