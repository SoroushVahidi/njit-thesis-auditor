# P061 Scope and Design

- **Date:** 2026-06-06
- **Status:** Scoped (not yet implemented)
- **Baseline main:** `4f1ea71` (PR #198 — post-P060 consistency audit; P001–P060 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **60/60** implemented (`P001`–`P060`) |
| LoT/LoF page-number ordering (within page) | **P057** — warns when entries on a single LoT/LoF page have page numbers not in non-decreasing order |
| TOC page-number ordering (within page) | **P058** — warns when entries on a single TOC page have page numbers not in non-decreasing order |
| LoT/LoF entry-number ordering (within page) | **P059** — warns when entries on a single LoT/LoF page have entry numbers not in non-decreasing order |
| TOC section-number ordering (within page) | **P060** — warns when entries on a single TOC page have section numbers not in non-decreasing order |
| LoT/LoF entry-number ordering (cross-page) | **Not checked** — if a document's List of Tables or List of Figures spans multiple pages, entry numbers should be non-decreasing across the page boundary; no rule currently checks this |

P057–P060 check ordering within individual pages. For documents with multi-page LoT or LoF
sections, a cross-page scrambling error (e.g., the last entry on LoT page 1 is "Table 8" but
the first entry on LoT page 2 is "Table 2") would go undetected by P059 because each page is
checked independently.

---

## Selected P061 scope

### Rule title

LoT/LoF cross-page entry-number ordering check

### Rule ID

P061

### Q-rule basis

- **Q063** — "Is the word 'Table' … left-aligned in a separate column?" (correct column order
  implies sequential entry numbering across all LoT pages)
- **Q072** — "Is the word 'Figure' … left-aligned in a separate column?" (same for LoF)

Ordering across pages is implied by the requirement that LoT/LoF entries accurately reflect the
order of tables/figures in the document.

### Description

Emit a WARNING when a document's List of Tables or List of Figures spans multiple pages and the
combined entry number sequence across those pages is not in non-decreasing order. Specifically:
collect comparable entry numbers from all LoT (or all LoF) pages in document order, concatenate
them, and check the full sequence for inversions.

This is a cross-page companion to P059 (which checks within each individual page). P061 catches
the case where each page is individually ordered but the boundary between pages introduces an
inversion.

### Issue types

| Issue type | Trigger |
|------------|---------|
| `lot_cross_page_entry_numbers_not_nondecreasing` | Multi-page LoT with combined cross-page entry-number sequence not non-decreasing |
| `lof_cross_page_entry_numbers_not_nondecreasing` | Multi-page LoF with combined cross-page entry-number sequence not non-decreasing |

### Scope boundaries

**In scope:**
- LIST OF TABLES sections spanning ≥2 pages
- LIST OF FIGURES sections spanning ≥2 pages
- Only entries with parseable entry numbers (numeric token after "Table"/"Figure" label)

**Out of scope:**
- Single-page LoT or LoF (covered by P059 for within-page inversions)
- TABLE OF CONTENTS pages (P060 handles TOC; a companion cross-page TOC check is possible but deferred)
- Entries where the entry number is not parseable
- Mixed sequential + chapter-based format sections (same gate as P059)
- Appendix/letter-prefixed entries (same gate as P059)

### Entry number parsing

Reuse `_parse_entry_num` logic from P059 (`pdf_lot_lof_entry_number_ordering.py`):
- Strip "Table"/"Figure" prefix (case-insensitive)
- Parse sequential (N) or chapter-based (N.M) numeric token
- Skip letter-prefixed entries (appendix tables/figures)
- Skip entries where number is not parseable

Mixed-format pages (both sequential and chapter-based) are skipped per P059's gate.

### Conservative gates

- At least 2 LoT pages (or 2 LoF pages) with comparable entries (multi-page LoT/LoF required)
- At least 3 total comparable entries across all pages of the section
- At least 2 inversions in the combined cross-page sequence before flagging
- Entries without `page_number_token` (wrapped continuation lines) skipped
- Entries with non-parseable numbers skipped silently

### Findings

Privacy-safe metadata only — no entry text, table/figure titles, or captions.

| Field | Value |
|-------|-------|
| `issue_type` | `lot_cross_page_entry_numbers_not_nondecreasing` or `lof_cross_page_entry_numbers_not_nondecreasing` |
| `page` | page number of the FIRST LoT/LoF page in the section |
| `section_type` | `"list_of_tables"` or `"list_of_figures"` |
| `page_count` | number of pages in the section |
| `entry_count` | total number of comparable entries across all pages |
| `comparable_entry_number_count` | same as `entry_count` |
| `inversion_count` | number of consecutive inversions in the combined sequence |
| `first_inversion_index` | index of first inverted pair in combined sequence |
| `triage_tier` | `"medium"` |
| `source_q_rule_id` | `"Q063"` (LoT) or `"Q072"` (LoF) |

### triage_tier

`medium` — cross-page ordering errors indicate a structural assembly problem in the LoT/LoF.

---

## Likely implementation

```
src/njit_auditor/rules/pdf_lot_lof_cross_page_entry_ordering.py
```

New module. Uses `detect_toc_like_pages` / `extract_toc_entry_lines` infrastructure. Groups
consecutive same-type pages (list_of_tables or list_of_figures), collects their combined entry
number sequences, then applies the same ordering check as P059.

Wire into `cli.py` and `evaluation.py` after existing P060 call.

---

## Acceptance criteria

1. Emits `lot_cross_page_entry_numbers_not_nondecreasing` when multi-page LoT has combined
   entry-number sequence with ≥2 inversions and ≥3 comparable entries total.
2. Emits `lof_cross_page_entry_numbers_not_nondecreasing` analogously for multi-page LoF.
3. Does NOT flag single-page LoT or LoF (requires ≥2 pages).
4. Does NOT flag TABLE OF CONTENTS pages.
5. Does NOT flag when combined sequence is non-decreasing.
6. Does NOT flag when fewer than 3 comparable entries across all pages.
7. Skips entries with non-parseable entry numbers silently.
8. Skips mixed sequential + chapter-based format sections.
9. Findings contain only structural metadata — no entry text, table/figure titles, or captions.
10. All P001–P060 existing tests continue to pass.

---

## Test plan (planned)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p061_single_page_lot_no_finding` | Single LoT page → no P061 finding (P059 scope) |
| `test_p061_two_page_lot_ascending_no_finding` | Two LoT pages, combined sequence non-decreasing → no finding |
| `test_p061_two_page_lot_one_inversion_no_finding` | Two LoT pages, 1 cross-page inversion → no finding |
| `test_p061_two_page_lot_two_inversions_warns` | Two LoT pages with ≥2 combined inversions → finding |
| `test_p061_two_page_lof_two_inversions_warns` | Two LoF pages with ≥2 combined inversions → lof finding |
| `test_p061_toc_unaffected` | TOC page → P061 does not fire |
| `test_p061_sparse_combined_skipped` | Fewer than 3 combined comparable entries → skipped |
| `test_p061_mixed_format_skipped` | Mixed sequential + chapter-based across pages → skipped |
| `test_p061_finding_metadata_privacy_safe` | Findings contain only allowed keys; no entry text |
| `test_p061_import_and_wiring` | Module importable; returns list |
| `test_p061_word_only_entries_skipped` | Non-Table/Figure entries skipped |
| `test_p061_chapter_based_cross_page_warns` | Chapter-based numbers crossing page boundary with inversions → finding |
