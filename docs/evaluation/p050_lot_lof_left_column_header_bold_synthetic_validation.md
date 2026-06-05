# P050 Synthetic Validation — LoT/LoF Left-Column Header Bold-Style Check

- **Date:** 2026-06-04
- **Rule:** P050
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py`
- **Function:** `check_pdf_lot_lof_left_column_header_bold`
- **Q-rule basis:** Q063 (List of Tables "Table" label bold), Q072 (List of Figures "Figure" label bold)

---

## Scope

P050 checks that the left-column header label ("Table" for LoT, "Figure" for LoF) is formatted in bold when font metadata is reliably available. It complements P031 (presence/coarse alignment) and P049 (Page-column header bold/alignment). P050 adds no new left-alignment check — P031 already covers coarse alignment with 80pt tolerance.

---

## Conservative gates

| Gate | Behavior |
|------|----------|
| Section type | LoT and LoF pages only; TOC excluded |
| Minimum entries | Requires ≥ 3 complete entries (with page_number_right_x) |
| Left header absent | Skip — P031 handles missing left header |
| Font metadata unavailable | `_is_line_confidently_not_bold` returns False → no finding |
| Bold header | No finding emitted |

---

## Synthetic test cases (9 tests)

| Test | Setup | Expected |
|------|-------|----------|
| No LoT/LoF pages | TOC-only page | No P050 findings |
| LoT left header bold (Times-Bold) | Bold "Table" label | No finding |
| LoT left header not bold (helv) | Non-bold "Table" label + reliable metadata | `lot_table_header_not_bold`, Q063 |
| LoF left header bold (Times-Bold) | Bold "Figure" label | No finding |
| LoF left header not bold (helv) | Non-bold "Figure" label + reliable metadata | `lof_figure_header_not_bold`, Q072 |
| Missing left header | No "Table"/"Figure" in header zone | No P050 findings |
| Too few entries (2) | Only 2 complete entries | Gate skips — no finding |
| Privacy-safe metadata | Non-bold left header | Finding keys ⊆ allowed set; no entry text, captions, or titles |
| Import and wiring | Empty PdfDocument | Returns `[]` |

All 9 tests pass on the P050 implementation branch.

---

## Issue types

| Issue type | Q-rule | Section | Condition |
|------------|--------|---------|-----------|
| `lot_table_header_not_bold` | Q063 | `list_of_tables` | "Table" header confidently non-bold |
| `lof_figure_header_not_bold` | Q072 | `list_of_figures` | "Figure" header confidently non-bold |

---

## Finding metadata (privacy-safe)

| Key | Example value |
|-----|--------------|
| `page_number` | `"4"` |
| `issue_type` | `"lot_table_header_not_bold"` |
| `section_type` | `"list_of_tables"` |
| `column_type` | `"left"` |
| `style_signal` | `"font_metadata"` |
| `font_metadata_available` | `"true"` |
| `entry_count` | `"3"` |
| `triage_tier` | `"low"` |
| `source_q_rule_id` | `"Q063"` |

No entry text, header label text, captions, figure/table titles, or private content is included in findings.

---

## Current-dataset evaluation

**Not run.** Only 4/5 evaluation PDFs are directly accessible. No canonical P050 current-dataset counts exist. The canonical five-PDF aggregate remains **1,446** at `generated_for_commit` `00b9c2d`.
