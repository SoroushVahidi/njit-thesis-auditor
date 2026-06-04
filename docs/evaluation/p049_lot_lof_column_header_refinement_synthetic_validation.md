# P049 Synthetic Validation — LoT/LoF Column-Header Style/Alignment Refinement

- **Date:** 2026-06-04
- **Rule:** P049 — PDF LoT/LoF column-header style/alignment refinement
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py`
- **Q-rule basis:** Q064 (List of Tables Page header), Q073 (List of Figures Page header)

---

## Summary

All 12 P049 synthetic tests pass. No false positives on correct headers; expected
issues are emitted on misaligned and non-bold Page headers.

---

## Test coverage

| Test | Scenario | Expected result | Status |
|------|----------|-----------------|--------|
| `test_p049_no_lot_lof_pages_no_findings` | TOC page only, no LoT/LoF heading | No P049 findings | Pass |
| `test_p049_lot_page_header_right_aligned_no_findings` | LoT Page header aligned + bold | No P049 findings | Pass |
| `test_p049_lot_page_header_misaligned_warns` | LoT Page header far left (x=200 vs page-number col ~513) | `lot_page_header_not_right_aligned` | Pass |
| `test_p049_lof_page_header_right_aligned_no_findings` | LoF Page header aligned + bold | No P049 findings | Pass |
| `test_p049_lof_page_header_misaligned_warns` | LoF Page header far left (x=200) | `lof_page_header_not_right_aligned` | Pass |
| `test_p049_lot_page_header_bold_no_bold_finding` | LoT Page header with Times-Bold font | No bold finding | Pass |
| `test_p049_lot_page_header_not_bold_warns` | LoT Page header non-bold (Helv), aligned | `lot_page_header_not_bold` | Pass |
| `test_p049_lof_page_header_not_bold_warns` | LoF Page header non-bold (Helv), aligned | `lof_page_header_not_bold` | Pass |
| `test_p049_too_few_entries_skipped` | Only 2 complete entries (< MIN=3) | No findings | Pass |
| `test_p049_no_page_header_skipped` | No Page header in header zone | No findings | Pass |
| `test_p049_finding_metadata_privacy_safe` | Misaligned + non-bold LoT | Findings; keys only privacy-safe metadata | Pass |
| `test_p049_import_and_wiring` | Empty PdfDocument | Returns empty list | Pass |

---

## Issue types

| Issue type | Q-rule | Condition |
|------------|--------|-----------|
| `lot_page_header_not_right_aligned` | Q064 | LoT Page header x1 deviates > 25pt from median page-number right-x |
| `lof_page_header_not_right_aligned` | Q073 | LoF Page header x1 deviates > 25pt from median page-number right-x |
| `lot_page_header_not_bold` | Q064 | LoT Page header spans have reliable non-bold font metadata |
| `lof_page_header_not_bold` | Q073 | LoF Page header spans have reliable non-bold font metadata |

---

## Gates and limitations

- Gate: requires ≥ 3 entries with confident `page_number_right_x` geometry per section.
- Bold check is skipped when any span lacks font metadata (conservative false-negative preference).
- Pages without a detected `Page` header are skipped; P031 handles the missing-header case.
- Findings contain only privacy-safe metadata (geometry, style flags, issue type, source Q-rule).
- No entry text, table/figure titles, captions, or arbitrary extracted text in findings.
- Current-dataset audit not run — only 4/5 evaluation PDFs directly accessible.
