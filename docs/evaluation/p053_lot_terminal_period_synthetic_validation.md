# P053 Synthetic Validation: LoT Entry Terminal-Period Check

- **Rule:** P053 — List of Tables entry terminal-period check (Q065 refinement)
- **Module:** `src/njit_auditor/rules/pdf_lot_terminal_period.py`
- **Function:** `check_pdf_lot_terminal_period`
- **Date:** 2026-06-04
- **Test file:** `tests/test_pdf_rules.py` (9 tests, `test_p053_*`)

---

## Issue types implemented

| Issue type | Severity | Q-rule | Condition |
|---|---|---|---|
| `lot_entry_has_terminal_period` | WARNING | Q065 | Complete LoT entry (with page-number token) ends with `.` |

---

## Synthetic test cases

| Test | Scenario | Expected |
|---|---|---|
| `test_p053_lot_entry_no_period_no_finding` | Complete LoT entries without terminal period | No P053 finding |
| `test_p053_lot_entry_with_period_warns` | Complete LoT entry ending with `.` | P053 `lot_entry_has_terminal_period` |
| `test_p053_wrap_continuation_skipped` | Lines without page-number tokens (leading wrap lines) | No P053 finding |
| `test_p053_no_lot_page_no_finding` | No LIST OF TABLES page in document | No P053 finding |
| `test_p053_lof_page_not_checked` | LIST OF FIGURES page (not LoT) | No P053 finding |
| `test_p053_sparse_page_skipped` | LoT page with fewer than 2 entries | No P053 finding (gate) |
| `test_p053_finding_metadata_privacy_safe` | Entry with terminal period | Finding has no entry text, table titles, or private content |
| `test_p053_import_and_wiring` | Function importable; wired in `cli.py` | Assertion pass |
| `test_p053_p040_unaffected` | LoF page entries without terminal punctuation | P040 fires; no P053 |

---

## Finding metadata (lot_entry_has_terminal_period)

| Field | Example value | Privacy |
|---|---|---|
| `issue_type` | `lot_entry_has_terminal_period` | Safe |
| `page` | `2` | Safe |
| `section_type` | `list_of_tables` | Safe |
| `entry_index` | `0` | Safe |
| `terminal_punctuation` | `.` | Safe |
| `page_number_token_present` | `true` | Safe |
| `triage_tier` | `medium` | Safe |
| `source_q_rule_id` | `Q065` | Safe |

No table title text, entry text, captions, or private content is included in findings.

---

## Current-dataset evaluation

No canonical audit run. Only 4/5 evaluation PDFs are directly accessible; canonical aggregate
remains **1,446** (generated for commit `00b9c2d`). P053 was not tested on the current
dataset; see `docs/evaluation/p053_current_dataset_evaluation.md`.

---

## Conservative gates applied

| Risk | Gate |
|------|------|
| Non-LoT pages processed | Only process pages where `context.page_type == "list_of_tables"` |
| Wrap-continuation lines flagged | Only process entries with `page_number_token is not None` |
| Short fragments produce false positives | Skip entries with fewer than 10 chars after stripping |
| Leader dots mistaken for terminal period | Strip trailing leader dots (`.. . .`) before checking |
| Sparse / ambiguous pages | Gate: skip pages with fewer than 2 entries |
| Symmetric confusion with P040 | P040 checks LoF (must have terminal punct); P053 checks LoT (must NOT have terminal period); no overlap |
