# P065 — Dedication Page Centering/Italic: Synthetic Validation

**Rule:** P065  
**Module:** `njit_auditor.rules.pdf_dedication_centering_italic`  
**Issue types:** `dedication_text_not_centered`, `dedication_text_not_italic`  
**Source Q-rules:** Q033, Q034

---

## Overview

All 15 tests use entirely synthetic PDFs built from placeholder text. No real
dissertation content, author names, dedication text, or committee text appears
in any test. Privacy constraints are enforced by a dedicated privacy test
(test 13).

---

## Test Results

All 15 tests passed on the first clean run after lint fixes.

| # | Test name | Scenario | Expected | Result |
|---|-----------|----------|----------|--------|
| 1 | `test_no_dedication_page_no_findings` | No DEDICATION heading in document | No findings | PASS |
| 2 | `test_centered_italic_dedication_no_findings` | Centered + italic text block | No findings | PASS |
| 3 | `test_off_center_dedication_emits_centering_finding` | Flush-left text (max offset) | `dedication_text_not_centered` | PASS |
| 4 | `test_non_italic_dedication_emits_italic_finding` | Roman (non-italic) spans | `dedication_text_not_italic` | PASS |
| 5 | `test_both_off_center_and_non_italic_emits_two_findings` | Flush-left + roman | Both issue types | PASS |
| 6 | `test_too_few_lines_skips_centering` | Only 1 text line (< `_MIN_TEXT_LINES=2`) | No centering finding | PASS |
| 7 | `test_too_few_spans_skips_italic` | 2 spans (< `_MIN_SPANS=3`) | No italic finding | PASS |
| 8 | `test_all_none_font_skips_italic` | 4 spans, all `font=None` | No italic finding | PASS |
| 9 | `test_image_only_page_no_findings` | Page with no text blocks | No findings | PASS |
| 10 | `test_multiple_dedication_headings_skips` | Two DEDICATION headings across two pages | No findings (ambiguous) | PASS |
| 11 | `test_dedication_heading_excluded_from_metrics` | DEDICATION heading + 1 real line | Heading not counted; centering skipped | PASS |
| 12 | `test_page_number_footer_excluded_from_metrics` | Page-number `"iv"` near bottom margin | Footer not counted in metrics | PASS |
| 13 | `test_no_dedication_text_in_findings` | Off-center placeholder text | Finding details contain no body text | PASS |
| 14 | `test_italic_font_recognized_no_italic_finding` | `heit` (Helvetica-Oblique) font | No italic finding | PASS |
| 15 | `test_finding_rule_id_is_p065` | Any emitted finding | `rule_id == "P065"` | PASS |

---

## Gate Coverage

| Gate | Test(s) covering it |
|------|---------------------|
| No DEDICATION heading → skip | 1 |
| Multiple DEDICATION headings → skip | 10 |
| Image-only / no text blocks → skip | 9 |
| `< _MIN_TEXT_LINES` → skip centering | 6, 11 |
| `< _MIN_SPANS` → skip italic | 7 |
| All-None font metadata → skip italic | 8 |
| Bottom-zone footer excluded | 12 |
| DEDICATION heading excluded from text lines | 11 |

---

## Finding Detail Fields Verified

For `dedication_text_not_centered`: `issue_type`, `page`, `line_count`,
`center_offset_pt`, `text_area_center_pt`, `block_center_pt`.

For `dedication_text_not_italic`: `issue_type`, `page`, `italic_span_ratio`,
`italic_span_count`, `total_span_count`.

No finding detail value contains placeholder text (test 13), dissertation body
text, author names, or dedication content.

---

## Validation Status

**PASS — all 15/15 synthetic tests pass.** No current-dataset findings
(evaluation against evaluation PDFs pending dedicated evaluation run).

Generated: 2026-06-08  
Pytest suite total at validation: 925 passed, 0 failed
