# P046 LoT/LoF Entry Number Alignment Synthetic Validation

- **Date:** 2026-06-03
- **Rule:** P046 — LoT/LoF entry number left-column alignment (Q068/Q078)
- **Status:** **Synthetic validation only** — current-dataset audit not run (evaluation PDFs unavailable)
- **Baseline main at implementation:** P046 implementation PR

---

## Validation summary

| Check | Result |
|-------|--------|
| Synthetic unit tests | **9 passed** |
| `ruff check .` | ✅ Clean |
| `mypy src` | ✅ Clean (60 source files) |
| `python -m pytest` | ✅ **524 passed** |

---

## Synthetic test coverage

| Test | Scenario | Expected outcome | Pass |
|------|----------|-----------------|------|
| `test_p046_no_lot_lof_pages_no_findings` | No LIST OF TABLES or LIST OF FIGURES heading | No P046 findings | ✅ |
| `test_p046_lot_aligned_no_findings` | LoT entries at consistent x0 (all at 108pt) | No P046 findings | ✅ |
| `test_p046_lot_misaligned_warns` | LoT entry at x=130pt among entries at x=108pt | `lot_entry_number_column_misaligned` (Q068) | ✅ |
| `test_p046_lof_aligned_no_findings` | LoF entries at consistent x0 | No P046 findings | ✅ |
| `test_p046_lof_misaligned_warns` | LoF entry at x=134pt among entries at x=108pt | `lof_entry_number_column_misaligned` (Q078) | ✅ |
| `test_p046_too_few_entries_no_findings` | Only 2 entries (gate: MIN_ENTRIES=3) | No P046 findings | ✅ |
| `test_p046_finding_metadata_no_private_content` | Misaligned LoT | Findings contain geometry metadata only; no entry text | ✅ |
| `test_p046_q068_source_q_rule_id` | LoT misalignment | `source_q_rule_id` = `Q068` in finding | ✅ |
| `test_p046_q078_source_q_rule_id` | LoF misalignment | `source_q_rule_id` = `Q078` in finding | ✅ |

---

## Issue types

| Issue type | Q-rule | Condition |
|-----------|--------|-----------|
| `lot_entry_number_column_misaligned` | Q068 | LoT entry x0 range (max − min) > `X0_RANGE_THRESHOLD_PT = 6.0pt` across ≥ 3 entries |
| `lof_entry_number_column_misaligned` | Q078 | LoF entry x0 range (max − min) > `X0_RANGE_THRESHOLD_PT = 6.0pt` across ≥ 3 entries |

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
| Uses all entry x0 values | Includes continuation lines of wrapped entries which may have the same or different x0; conservative threshold reduces FP risk |
| Section-level finding | Emits one finding per section (LoT or LoF), not per individual misaligned entry |
| Gate: MIN_ENTRIES = 3 | Skips sections with fewer than 3 extracted entries |
| Compressed/flattened PDFs | If text layer not extractable, entries may not be detected; gate skips silently |
| Complements P018 | P018 checks page-number right-column alignment; P046 adds left-column (entry number) alignment |

---

## Current-dataset evaluation

No P046 current-dataset finding counts are available. See `docs/evaluation/p046_current_dataset_evaluation.md`.

---

## Privacy

Findings from P046 contain geometry metadata only:
`page_number`, `issue_type`, `section_type`, `entry_count`, `observed_x0_range_points`,
`expected_x0`, `observed_x0_max`, `allowed_x0_range_points`, `triage_tier`, `source_q_rule_id`.
No table/figure title text, entry descriptions, captions, or private student content is quoted.

Generated audit outputs remain gitignored under `data/evaluation/generated/`.
