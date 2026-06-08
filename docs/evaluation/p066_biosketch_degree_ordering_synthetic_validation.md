# P066 — Biographical Sketch Degree Ordering: Synthetic Validation

**Rule:** P066  
**Module:** `njit_auditor.rules.pdf_biosketch_degree_ordering`  
**Issue type:** `biosketch_degree_order_suspicious`  
**Source Q-rule:** Q025 (degrees most-recent-first)

---

## Scope Statement

P066 implements Q025 only — structural year-ordering heuristic. The following
are explicitly out of scope for P066:

- **Q023** (no birthplace/date of birth) — manual-only; requires reading
  biographical content; high privacy risk; NLP needed
- **Q024** (no work experience) — manual-only; same reasons
- **Q025 "NJIT first" sub-requirement** — deferred; requires institution name
  recognition (text content reading)

P066 does not evaluate biography content, birthplace/date of birth, work
experience, institution correctness, or NJIT-first semantics.

---

## Overview

All 12 tests use entirely synthetic PDFs built from placeholder text with
clearly fake years. No real dissertation content, biographical prose, degree
names, institution names, or author names appear in any test. Privacy
constraints are enforced by a dedicated privacy test (test 11).

---

## Test Results

All 12 tests passed on first run.

| # | Test name | Scenario | Expected | Result |
|---|-----------|----------|----------|--------|
| 1 | `test_no_biosketch_page_no_findings` | No BIOGRAPHICAL SKETCH heading | No findings | PASS |
| 2 | `test_correct_descending_order_no_findings` | Years: 2023, 2019, 2015 (non-increasing) | No findings | PASS |
| 3 | `test_ascending_order_emits_finding` | Years: 2015, 2019, 2023 (wrong order) | `biosketch_degree_order_suspicious` | PASS |
| 4 | `test_partial_inversion_emits_finding` | Years: 2023, 2015, 2019 (partial inversion) | `biosketch_degree_order_suspicious` | PASS |
| 5 | `test_too_few_candidates_skips` | < `_MIN_YEAR_CANDIDATES = 3` year lines | No findings | PASS |
| 6 | `test_equal_years_skips` | All years = 2020 | No findings (order not determinable) | PASS |
| 7 | `test_image_only_page_no_findings` | No text blocks on page | No findings | PASS |
| 8 | `test_multiple_biosketch_headings_skips` | Two BIOGRAPHICAL SKETCH headings | No findings (ambiguous) | PASS |
| 9 | `test_publication_zone_years_excluded` | Ascending years only below Publications boundary | No findings | PASS |
| 10 | `test_long_prose_line_with_year_excluded` | Prose line > 120 chars excluded; remaining short lines checked | Short lines correctly classified | PASS |
| 11 | `test_no_biosketch_text_in_findings` | Ascending order (emits finding) | Placeholder text absent from all detail values | PASS |
| 12 | `test_finding_rule_id_is_p066` | Any emitted finding | `rule_id == "P066"` | PASS |

---

## Gate Coverage

| Gate | Test(s) covering it |
|------|---------------------|
| No BIOGRAPHICAL SKETCH heading → skip | 1 |
| Multiple headings → skip | 8 |
| Image-only page → skip | 7 |
| `< _MIN_YEAR_CANDIDATES = 3` year candidates → skip | 5 |
| All equal years → skip | 6 |
| Publication zone excluded | 9 |
| Long prose lines excluded | 10 |

---

## Finding Detail Fields Verified

For `biosketch_degree_order_suspicious`:
- `issue_type`, `page`, `year_candidate_count`, `first_candidate_year`,
  `last_candidate_year`, `inversion_count`, `first_inversion_index`,
  `expected_order`, `confidence`, `triage_tier`, `source_q_rule_ids`

No finding detail value contains placeholder text, degree names, institution
names, or biographical prose (test 11).

---

## Validation Status

**PASS — all 12/12 synthetic tests pass.**

Generated: 2026-06-08  
Pytest suite total at validation: 937 passed, 0 failed
