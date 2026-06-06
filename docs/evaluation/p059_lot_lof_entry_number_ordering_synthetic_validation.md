# P059 Synthetic Validation — LoT/LoF Entry-Number Ordering Check

- **Rule:** P059 — LoT/LoF entry-number ordering check
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_entry_number_ordering.py`
- **Date:** 2026-06-05
- **Status:** Implemented; 12 synthetic tests pass

## Summary

P059 checks that entries in a List of Tables or List of Figures have entry numbers
(the numeric token following the "Table"/"Figure" label) in non-decreasing order.

Conservative gates:
- At least 3 entries with parseable entry numbers
- At least 2 inversions before flagging
- Mixed sequential + chapter-based format pages skipped
- Appendix/letter-prefixed entries skipped
- TOC pages excluded

Issue types: `lot_entry_numbers_not_nondecreasing`, `lof_entry_numbers_not_nondecreasing`
Q-rule basis: Q063 (LoT), Q072 (LoF)
triage_tier: medium

## Synthetic test results

| Test | Expected | Result |
|------|----------|--------|
| `test_p059_no_lot_page_no_finding` | No finding | PASS |
| `test_p059_lot_ascending_no_finding` | No finding | PASS |
| `test_p059_lot_one_inversion_no_finding` | No finding (1 inversion below gate) | PASS |
| `test_p059_lot_two_inversions_warns` | `lot_entry_numbers_not_nondecreasing` | PASS |
| `test_p059_lof_two_inversions_warns` | `lof_entry_numbers_not_nondecreasing` | PASS |
| `test_p059_toc_unaffected` | No finding (TOC excluded) | PASS |
| `test_p059_sparse_lot_skipped` | No finding (< 3 entries) | PASS |
| `test_p059_mixed_format_skipped` | No finding (mixed format) | PASS |
| `test_p059_chapter_based_two_inversions_warns` | Finding with chapter-based tuples | PASS |
| `test_p059_finding_metadata_privacy_safe` | Only allowed keys in details | PASS |
| `test_p059_import_and_wiring` | Callable; returns list | PASS |
| `test_p059_unparseable_entries_skipped` | No finding (only 1 inversion with parseable entries) | PASS |

All 12 tests pass.

## Privacy

Findings contain only structural metadata:
- `issue_type`, `page`, `section_type`, `entry_count`, `comparable_entry_number_count`,
  `inversion_count`, `first_inversion_index`, `triage_tier`, `source_q_rule_id`

No entry text, table/figure titles, captions, or dissertation content is included.

## Current-dataset evaluation

Not run — only 4/5 evaluation PDFs directly accessible. See
`docs/evaluation/p059_current_dataset_evaluation.md` when a full rerun is performed.
