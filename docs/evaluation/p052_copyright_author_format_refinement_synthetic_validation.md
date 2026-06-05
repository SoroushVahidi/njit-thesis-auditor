# P052 Synthetic Validation: Copyright Author Format Refinement

- **Rule:** P052 — PDF copyright page author-format refinement (Q011 improvement)
- **Module:** `src/njit_auditor/rules/pdf_copyright_page.py`
- **Function:** `check_pdf_copyright_author_format`
- **Date:** 2026-06-04
- **Test file:** `tests/test_pdf_rules.py` (9 tests, `test_p052_*`)

---

## Issue types implemented

| Issue type | Severity | Q-rule | Condition |
|---|---|---|---|
| `copyright_author_not_found` | WARNING | Q011 | Copyright page + year detected but no author/owner string extractable |

---

## Synthetic test cases

| Test | Scenario | Expected |
|---|---|---|
| `test_p052_standard_author_no_finding` | `© 2024 Author` — standard format with year and author | No P052 finding |
| `test_p052_no_year_no_finding` | `© Author` — no year (P051's domain) | No P052 finding |
| `test_p052_year_no_author_warns` | `© 2024` + `All Rights Reserved.` — year present, no author | P052 `copyright_author_not_found` |
| `test_p052_adjacent_line_author_no_finding` | `© 2024` on line N, `Test Author Name` on line N+1 | No P052 finding (adjacent-line helper fires) |
| `test_p052_no_copyright_page_no_finding` | No copyright page in document | No P052 finding |
| `test_p052_finding_metadata_privacy_safe` | Year-only copyright page | Finding contains no author names, copyright text, or title text |
| `test_p052_import_and_wiring` | Function importable; wired in `cli.py` | Assertion pass |
| `test_p052_p034_p051_unaffected` | Year mismatch case | P034 fires; no P051 or P052 |
| `test_p052_year_detected_flag_in_finding` | Year-only copyright page | Finding has `year_detected: "true"` and `source_q_rule_id: "Q011"` |

---

## Finding metadata (copyright_author_not_found)

| Field | Example value | Privacy |
|---|---|---|
| `issue_type` | `copyright_author_not_found` | Safe |
| `page` | `2` | Safe |
| `copyright_marker_detected` | `true` | Safe |
| `year_detected` | `true` | Safe |
| `triage_tier` | `low` | Safe |
| `source_q_rule_id` | `Q011` | Safe |

No author names, copyright line text, title text, or private content is included in findings.

---

## Current-dataset evaluation

No canonical audit run. Only 4/5 evaluation PDFs are directly accessible; canonical aggregate
remains **1,446** (generated for commit `00b9c2d`). P052 was not tested on the current
dataset; see `docs/evaluation/p052_current_dataset_evaluation.md`.

---

## Conservative gates applied

| Risk | Gate |
|---|---|
| Copyright page not confidently detected | `_find_copyright_page` reused from P034 |
| No year on page (P051's domain) | Skip when `_extract_copyright_year` and adjacent-line both return None |
| Author present via P034 extraction | Skip when `_extract_copyright_author` returns a result |
| "All Rights Reserved" mistaken for author | Extended `_AUTHOR_NOISE_RE` to exclude these phrases |
| Adjacent-line ambiguity | Require next-line to have 2+ words, no copyright marker, no year, no noise |
| Image-only pages | `_page_has_meaningful_text` gate in `_find_copyright_page` |
