# P046 Current Dataset Evaluation (see gap-fill for five-PDF results)

> **Gap-fill evaluation (2026-06-09, commit `85a1326`):** Full five-PDF current-dataset audit now complete.
> P046 total: **2** findings on Yin H 4th (compressed) (`lot_entry_number_column_misaligned`: 1, `lof_entry_number_column_misaligned`: 1).
> See `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`.

- **Date:** 2026-06-03
- **Rule:** P046 — LoT/LoF entry number left-column alignment (Q068/Q078)
- **Status:** **No canonical audit run** — only 4 of 5 evaluation PDFs are directly accessible; Sebastian Fine Revised is ZIP-only
- **Baseline main at implementation:** `5be1edc` (PR #130)

---

## Evaluation status

No P046 current-dataset finding counts are available. A canonical five-PDF run requires all
five evaluation PDFs to be directly accessible. At the time of implementation:

- 4 PDFs are directly accessible in `data/raw/ester/`
- The fifth (Sebastian Fine Revised) is archive-contained in
  `Dissertations with no Feedback -20260529T012213Z-3-001.zip` and not committed as a
  standalone tracked file

**What was validated:**

- 9 synthetic unit tests covering P046 gate conditions, Q068/Q078 issue types, aligned
  entries (no findings), misaligned entries, and finding metadata privacy. All pass.
- `ruff check .` — clean
- `mypy src` — clean (60 source files)
- `python -m pytest` — **524 passed**

---

## Canonical aggregate baseline (unchanged)

| Field | Value |
|-------|-------|
| Canonical pre-P035/…/P046 five-PDF aggregate | **1,446** total findings |
| `generated_for_commit` | `00b9c2d` |
| Canonical eval doc | `docs/evaluation/current_auditor_after_p034_evaluation.md` |

P046 does not alter the canonical 1,446 baseline.

---

## P046 v1 limitations

| Limitation | Detail |
|-----------|--------|
| Section-level finding | One finding per section (LoT or LoF), not per individual misaligned entry |
| Gate: MIN_ENTRIES=3 | Skips sections with fewer than 3 extracted entries |
| Includes continuation lines | x0 values from all `extract_toc_entry_lines` output, including wrapped entry continuations; conservative 6pt threshold reduces FP risk |
| Compressed/flattened PDFs | Entry x0 not extractable; gate skips silently |

---

## Future canonical rerun

When all five evaluation PDFs are directly accessible:

1. Run `njit-audit pdf` on the five canonical evaluation PDFs.
2. Collect P046 aggregate counts only (no per-entry text).
3. Save outputs to `data/evaluation/generated/current_auditor_after_p046/` (gitignored).
4. Add a summary of aggregate P046 counts to this doc.
5. Do **not** update `generated_for_commit` unless the run is complete and validated.

---

## Privacy

Findings from P046 contain geometry metadata only:
`page_number`, `issue_type`, `section_type`, `entry_count`, `observed_x0_range_points`,
`expected_x0`, `observed_x0_max`, `allowed_x0_range_points`, `triage_tier`, `source_q_rule_id`.
No table/figure title text, entry descriptions, captions, or private student content is quoted.

Generated audit outputs remain gitignored under `data/evaluation/generated/`.
