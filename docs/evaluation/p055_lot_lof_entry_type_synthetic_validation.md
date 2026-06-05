# P055 LoT/LoF Entry Type Synthetic Validation

- **Rule:** P055 — LoT/LoF cross-type entry check (Q063/Q072 extension)
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_entry_type.py`
- **Issue types:** `lot_entry_is_figure`, `lof_entry_is_table`
- **Validation type:** Synthetic only (no real-data audit run)

---

## Test coverage (10 synthetic tests)

| Test | Expected outcome | Result |
|------|-----------------|--------|
| `test_p055_lot_correct_entries_no_finding` | LoT entries starting with "Table" → no findings | Pass |
| `test_p055_lot_figure_entry_warns` | LoT entry starting with "Figure" → `lot_entry_is_figure` | Pass |
| `test_p055_lof_correct_entries_no_finding` | LoF entries starting with "Figure" → no findings | Pass |
| `test_p055_lof_table_entry_warns` | LoF entry starting with "Table" → `lof_entry_is_table` | Pass |
| `test_p055_wrap_continuation_skipped` | Entries without page-number token → skipped | Pass |
| `test_p055_sparse_page_skipped` | Page with < 2 entries → skipped | Pass |
| `test_p055_toc_entries_unaffected` | TABLE OF CONTENTS page → P055 does not fire | Pass |
| `test_p055_finding_metadata_privacy_safe` | Finding details contain no entry text or title content | Pass |
| `test_p055_import_and_wiring` | Importable and wired in cli.py | Pass |
| `test_p055_p053_p054_unaffected` | P053/P054 still fire correctly after P055 added | Pass |

---

## Privacy-safe metadata gate

Findings contain only:

- `issue_type` — `lot_entry_is_figure` or `lof_entry_is_table`
- `page` — page number string
- `section_type` — `list_of_tables` or `list_of_figures`
- `entry_index` — positional index (integer string)
- `observed_entry_type` — `figure` or `table`
- `expected_entry_type` — `table` or `figure`
- `page_number_token_present` — `true`
- `triage_tier` — `medium`
- `source_q_rule_id` — `Q063` (LoT) or `Q072` (LoF)

No entry text, figure/table titles, captions, dissertation body content, or private content is included in findings.

---

## Conservative gates applied

| Risk | Gate |
|------|------|
| Wrap continuation lines | Only entries with `page_number_token is not None` are checked |
| Short fragments | Entries shorter than 10 chars after stripping are skipped |
| Ambiguous prefix ("Figurative…") | Prefix must match `^figure\s+\d` or `^table\s+\d` (case-insensitive) |
| Sparse pages | Pages with fewer than 2 extracted entries are skipped |
| TOC pages | Only `list_of_tables` and `list_of_figures` page types are processed |

---

## Current dataset evaluation

**Not run.** Only 4/5 evaluation PDFs are directly accessible. A canonical real-data audit was not conducted for P055.

- `generated_for_commit`: `00b9c2d` (unchanged)
- `canonical aggregate`: `1,446` (unchanged)
