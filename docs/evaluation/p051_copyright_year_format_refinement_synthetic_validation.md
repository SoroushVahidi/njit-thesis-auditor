# P051 Synthetic Validation: Copyright Year Format Refinement

- **Rule:** P051 — PDF copyright page year-format refinement (Q010 improvement)
- **Module:** `src/njit_auditor/rules/pdf_copyright_page.py`
- **Function:** `check_pdf_copyright_year_format`
- **Date:** 2026-06-04
- **Test file:** `tests/test_pdf_rules.py` (9 tests, `test_p051_*`)

---

## Issue types implemented

| Issue type | Severity | Q-rule | Condition |
|---|---|---|---|
| `copyright_year_not_found` | WARNING | Q010 | Copyright page detected but no year token anywhere on page |

---

## Synthetic test cases

| Test | Scenario | Expected |
|---|---|---|
| `test_p051_standard_year_no_finding` | `© 2024 Author` (standard format with space) | No P051 finding |
| `test_p051_no_space_year_no_finding` | `©2024 Author` (no space between symbol and year) | No P051 finding |
| `test_p051_copyright_word_year_no_finding` | `Copyright 2024 Author` (word form) | No P051 finding |
| `test_p051_adjacent_line_year_no_finding` | `©` on line N, `2024` on line N+1, unrelated year elsewhere | No P051 finding (adjacent-line helper fires) |
| `test_p051_no_year_warns` | `© Author` — no year token anywhere on copyright page | P051 `copyright_year_not_found` |
| `test_p051_no_copyright_page_no_finding` | No copyright page in document | No P051 finding |
| `test_p051_year_present_unextractable_no_finding` | `©` marker present, two unrelated years on page | No P051 finding (conservative skip) |
| `test_p051_finding_metadata_privacy_safe` | No-year copyright page | Finding contains no copyright text, author names, or title text |
| `test_p051_import_and_wiring` | Function importable; wired in `cli.py` | Assertion pass |
| `test_p051_p034_unaffected` | Year present but mismatches title page | P034 `copyright_year_mismatch` fires; no P051 |

---

## Finding metadata (copyright_year_not_found)

| Field | Example value | Privacy |
|---|---|---|
| `issue_type` | `copyright_year_not_found` | Safe |
| `page` | `2` | Safe |
| `copyright_marker_detected` | `true` | Safe |
| `triage_tier` | `low` | Safe |
| `source_q_rule_id` | `Q010` | Safe |

No copyright line text, author names, title text, or private content is included in findings.

---

## Current-dataset evaluation

No canonical audit run. Only 4/5 evaluation PDFs are directly accessible; canonical aggregate
remains **1,446** (generated for commit `00b9c2d`). P051 was not retested on the current
dataset; see `docs/evaluation/p051_current_dataset_evaluation.md`.

---

## Conservative gates applied

| Risk | Gate |
|---|---|
| Copyright page not confidently detected | `_find_copyright_page` reused from P034 |
| Year present but in unexpected format | Skip via `_YEAR_TOKEN_RE` page-level check |
| Overlap with P034 year-mismatch | P034 fires when year IS found but mismatches; P051 only when completely absent |
| Adjacent-line ambiguity | Require next-line to have exactly one year, no alpha text |
| Image-only pages | `_page_has_meaningful_text` gate in `_find_copyright_page` |
