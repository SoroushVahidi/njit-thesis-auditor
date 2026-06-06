# P060 Synthetic Validation — TOC Section-Number Ordering Check

- **Rule:** P060 — TOC section-number ordering check
- **Module:** `src/njit_auditor/rules/pdf_toc_entry_number_ordering.py`
- **Date:** 2026-06-06
- **Status:** Implemented; 12 synthetic tests pass

## Summary

P060 checks that parseable numeric section entries in the Table of Contents
have section numbers in non-decreasing order. Entries starting with a
word prefix (CHAPTER, APPENDIX, ABSTRACT, etc.) are skipped. Only entries
with a `page_number_token` (complete entries) are compared.

Conservative gates:
- At least 3 entries with parseable section numbers
- At least 2 inversions before flagging
- Word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) skipped
- Wrapped continuation lines (no page_number_token) skipped
- LoT and LoF pages excluded; TABLE OF CONTENTS only

Issue type: `toc_entry_numbers_not_nondecreasing`
Q-rule basis: Q056 (TOC level hierarchy implies sequential ordering), Q057 (TOC spacing integrity)
triage_tier: medium

## Synthetic test results

| Test | Expected | Result |
|------|----------|--------|
| `test_p060_no_toc_page_no_finding` | No finding | PASS |
| `test_p060_toc_ascending_no_finding` | No finding | PASS |
| `test_p060_toc_one_inversion_no_finding` | No finding (1 inversion below gate) | PASS |
| `test_p060_toc_two_inversions_warns` | `toc_entry_numbers_not_nondecreasing` | PASS |
| `test_p060_lot_unaffected` | No finding (LoT page excluded) | PASS |
| `test_p060_lof_unaffected` | No finding (LoF page excluded) | PASS |
| `test_p060_sparse_toc_skipped` | No finding (< 3 entries) | PASS |
| `test_p060_word_prefix_entries_skipped` | No finding (word-prefix entries not counted) | PASS |
| `test_p060_subsection_two_inversions_warns` | Finding with subsection tuples | PASS |
| `test_p060_finding_metadata_privacy_safe` | Only allowed keys in details | PASS |
| `test_p060_import_and_wiring` | Callable; returns list | PASS |
| `test_p060_unparseable_entries_skipped` | No finding (only 1 inversion with parseable entries) | PASS |

All 12 tests pass.

## Privacy

Findings contain only structural metadata:
- `issue_type`, `page`, `section_type`, `entry_count`, `comparable_entry_number_count`,
  `inversion_count`, `first_inversion_index`, `triage_tier`, `source_q_rule_id`

No entry text, chapter/section titles, TOC heading text, or dissertation content is included.

## Current-dataset evaluation

Not run — only 4/5 evaluation PDFs directly accessible. See
`docs/evaluation/p060_current_dataset_evaluation.md` when a full rerun is performed.
