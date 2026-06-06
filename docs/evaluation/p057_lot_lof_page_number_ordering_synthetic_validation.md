# P057 Synthetic Validation — LoT/LoF Page-Number Ordering

- **Date:** 2026-06-05
- **Rule:** P057 — LoT/LoF page-number ordering check
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_page_number_ordering.py`
- **Issue types:** `lot_page_numbers_not_nondecreasing`, `lof_page_numbers_not_nondecreasing`
- **Q-rule basis:** Q069 (LoT page-number column), Q079 (LoF page-number column)
- **Triage tier:** medium

---

## Design summary

P057 emits a WARNING when a List of Tables or List of Figures page contains complete entries
whose listed page numbers are not in non-decreasing order. A decrease in page number between
consecutive complete entries signals either an out-of-order entry or a copy-paste error.

**Conservative gates:**
- At least 3 complete entries with comparable (positive integer) page numbers
- At least 2 inversions (consecutive pairs where page number decreases) before flagging
- Entry text must be ≥ 10 characters
- Non-integer page tokens (roman numerals, letter-prefixed entries) are excluded
- TOC pages are excluded; only LIST OF TABLES and LIST OF FIGURES are checked
- Per-page check only; cross-page ordering not checked in v1

**Finding metadata** (privacy-safe; no entry text, titles, or captions):
- `issue_type`, `page`, `section_type`, `entry_count`, `comparable_page_number_count`,
  `inversion_count`, `first_inversion_index`, `triage_tier`, `source_q_rule_id`

---

## Synthetic test results

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_p057_no_lot_lof_page_no_finding` | No LoT/LoF page present | No findings | ✅ Pass |
| `test_p057_lot_ascending_no_finding` | LoT page numbers ascending | No findings | ✅ Pass |
| `test_p057_lot_one_inversion_no_finding` | LoT with 1 inversion (below threshold) | No findings | ✅ Pass |
| `test_p057_lot_two_inversions_warns` | LoT with 2 inversions | `lot_page_numbers_not_nondecreasing` | ✅ Pass |
| `test_p057_lof_ascending_no_finding` | LoF page numbers ascending | No findings | ✅ Pass |
| `test_p057_lof_two_inversions_warns` | LoF with 2 inversions | `lof_page_numbers_not_nondecreasing` | ✅ Pass |
| `test_p057_sparse_page_skipped` | Fewer than 3 comparable entries | No findings | ✅ Pass |
| `test_p057_non_integer_page_skipped` | Entries with roman numeral page tokens | No findings | ✅ Pass |
| `test_p057_toc_unaffected` | TOC page with inversions | No findings | ✅ Pass |
| `test_p057_finding_metadata_privacy_safe` | Findings contain only allowed metadata keys | All keys in allowed set | ✅ Pass |
| `test_p057_import_and_wiring` | Module importable, returns list | callable, returns list | ✅ Pass |
| `test_p057_toc_entries_unaffected` | TOC entries with ascending order | No findings | ✅ Pass |

**12/12 tests passed.**

---

## Current-dataset evaluation

**Not run** — only 4/5 evaluation PDFs are directly accessible in the workspace.
The canonical five-PDF aggregate (generated at commit `00b9c2d`) is preserved at 1,446 total
findings and has not been updated. P057 findings are not included in the canonical aggregate.

See `docs/evaluation/p057_current_dataset_evaluation.md` for the placeholder evaluation record.

---

## Privacy

All test cases use synthetic PDFs with generic entry text (no dissertation content, no author
names, no committee names, no title text). Finding metadata contains only structural counts
and integer indices — no entry text, table/figure titles, captions, or other private content.
