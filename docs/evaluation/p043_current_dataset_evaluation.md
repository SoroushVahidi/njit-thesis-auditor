# P043 Current Dataset Evaluation

- **Date:** 2026-06-03
- **Rule:** P043 — Acknowledgements page paragraph indentation (Q044/Q045)
- **Status:** **No local audit run** — evaluation PDFs unavailable in workspace
- **Baseline main at implementation:** `70b37bc` (PR #116)

---

## Evaluation status

No P043 current-dataset finding counts are available. The evaluation PDFs required for a
local P001–P043 aggregate run are not present in the workspace at the time of this doc.

**What was validated:**

- 7 synthetic unit tests covering the P043 gate conditions, Q044/Q045 issue types, correct
  format (no findings), privacy-safe metadata, and pre-heading text exclusion. All pass.
- `ruff check .` — clean
- `mypy src` — clean (57 source files)
- `python -m pytest` — **498 passed**

---

## Canonical aggregate baseline (unchanged)

| Field | Value |
|-------|-------|
| Canonical pre-P035/…/P043 five-PDF aggregate | **1,446** total findings |
| `generated_for_commit` | `00b9c2d` |
| Canonical eval doc | `docs/evaluation/current_auditor_after_p034_evaluation.md` |

P043 does not alter the canonical 1,446 baseline. The baseline was established before P035
and has not been updated by a full P001–P043 rerun. The next full rerun should target a
gitignored output under `data/evaluation/generated/` and must not commit generated JSON/MD.

---

## P043 v1 limitations

| Limitation | Detail |
|-----------|--------|
| Heading detection gate | Emits nothing if ACKNOWLEDGEMENTS heading is not in the text layer (compressed/flattened PDFs) |
| Paragraph block gate | Emits nothing if fewer than 2 paragraph blocks found below the heading |
| Indented-first-paragraph styles | Some disciplines use a uniformly indented style; INDENT_THRESHOLD_PT=18pt reduces FP risk |
| Continuation lines only | Considers first-line x-position of each paragraph block; not a full paragraph-flow analysis |
| Left-margin derivation | Left margin is the minimum x0 across all body lines; may be affected by very short lines |

---

## Privacy

Findings from P043 contain geometry metadata only:
`page_number`, `issue_type`, `paragraph_index`, `observed_x0`, `expected_left_margin`,
`indent_delta_points`, `required_indent_points`, `triage_tier`, `source_q_rule_id`.
No Acknowledgements paragraph text, advisor names, or other private content is quoted.

Generated audit outputs remain gitignored under `data/evaluation/generated/` and were not
committed.

---

## Future canonical rerun

When evaluation PDFs are available locally:

1. Run `njit-audit pdf` on the five canonical evaluation PDFs.
2. Collect P043 aggregate counts only (no per-PDF body text).
3. Save outputs to `data/evaluation/generated/current_auditor_after_p043/` (gitignored).
4. Add a summary of aggregate P043 counts to this doc.
5. Do **not** update `generated_for_commit` unless the run is complete and validated.
