# P062 Scope and Design

- **Date:** 2026-06-07
- **Status:** Implemented (PR #220)
- **Baseline main:** post PR #219

---

## Current state before P062

| Area | State |
|------|-------|
| P-rules | **61/61** implemented (`P001`–`P061`) |
| TOC section-number ordering (within page) | **P060** — warns when entries on a single TOC page have section numbers not in non-decreasing order |
| LoT/LoF entry-number ordering (within page) | **P059** — warns when entries on a single LoT/LoF page have entry numbers not in non-decreasing order |
| LoT/LoF entry-number ordering (cross-page) | **P061** — warns when combined entry numbers across multi-page LoT/LoF runs are not non-decreasing |
| TOC section-number ordering (cross-page) | **Not checked** — if a document's TABLE OF CONTENTS spans multiple pages, section numbers should be non-decreasing across the page boundary; no rule currently checks this |

P060 checks TOC section-number ordering within individual pages. For documents with
multi-page TOCs (common in long dissertations), a cross-page scrambling error (e.g., the
last entry on TOC page 1 is "Section 4.1" but the first entry on TOC page 2 is
"Section 2.3") would go undetected by P060.

This is the same gap that P061 filled for LoT/LoF relative to P059. P062 fills the
analogous gap for TABLE OF CONTENTS pages.

---

## Selected P062 scope

### Rule title

TOC cross-page section-number ordering check

### Rule ID

P062

### Q-rule basis

- **Q056** — "Are level-2 and level-3 entries indented to show hierarchy?"
  (hierarchy implies sequential section numbering across all TOC pages)
- **Q057** — "Is there visible double spacing between consecutive section-title entries?"
  (consistent ordering prerequisite for a well-structured TOC)

Sequential ordering of section numbers across pages is implied by the requirement
that the Table of Contents accurately reflects the document's section structure.

### Description

Emit a WARNING when the Table of Contents spans multiple consecutive pages and the
combined section-number sequence across those pages is not in non-decreasing order.
Collect parseable numeric section entries (e.g., "1 Introduction", "1.1 Background",
"2 Methods") from all consecutive TABLE OF CONTENTS pages, concatenate them in document
order, and check the full combined sequence for inversions.

This is the cross-page companion to P060 (which checks within each individual TOC page)
and the symmetric counterpart to P061 (which does the same for LoT/LoF pages).

### Issue types

| Issue type | Trigger |
|------------|---------|
| `toc_cross_page_entry_numbers_not_nondecreasing` | Multi-page TABLE OF CONTENTS with combined section-number sequence not non-decreasing |

### Scope boundaries

**In scope:**
- TABLE OF CONTENTS sections spanning ≥2 consecutive pages
- Only entries with parseable numeric section numbers (bare number prefix: "1", "1.1", "1.2.3")

**Out of scope:**
- Single-page TOC (covered by P060 for within-page inversions)
- LIST OF TABLES and LIST OF FIGURES pages (P061 handles LoT/LoF)
- Non-consecutive TOC pages (not combined into a single run)
- Word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) — same gate as P060
- Entries without `page_number_token` (wrapped continuation lines) — same gate as P060

### Section number parsing

Reuse `_parse_section_num` logic from P060 (`pdf_toc_entry_number_ordering.py`):
- Match bare numeric prefix (e.g., "1", "1.1", "2.3.4") at start of entry text
- Skip word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.)
- Return tuple (N,) for top-level, (N, M) for subsections, etc.

### Conservative gates

- At least 2 consecutive TABLE OF CONTENTS pages (multi-page TOC required)
- At least 3 total comparable entries across all pages of the section
- At least 2 inversions in the combined sequence before flagging
- Entries without `page_number_token` (wrapped continuation lines) skipped
- Entries with non-parseable or word-prefix starts skipped silently
- Non-consecutive TOC pages are not combined (each consecutive run evaluated independently)

### Findings

Privacy-safe metadata only — no entry text, section titles, or dissertation content.

| Field | Value |
|-------|-------|
| `issue_type` | `toc_cross_page_entry_numbers_not_nondecreasing` |
| `page` | page number of the FIRST TOC page in the consecutive run |
| `section_type` | `"table_of_contents"` |
| `page_count` | number of consecutive TOC pages in the run |
| `entry_count` | total number of comparable entries across all pages |
| `comparable_entry_number_count` | same as `entry_count` |
| `inversion_count` | number of consecutive inversions in the combined sequence |
| `first_inversion_index` | index of first inverted pair in combined sequence |
| `triage_tier` | `"medium"` |
| `source_q_rule_id` | `"Q056"` |

### triage_tier

`medium` — cross-page ordering errors indicate a structural assembly problem in the TOC.

---

## Implementation

```
src/njit_auditor/rules/pdf_toc_cross_page_entry_ordering.py
```

New module. Reuses `detect_toc_like_pages` / `extract_toc_entry_lines` from
`pdf_toc_alignment.py` and `_parse_section_num` / constants from
`pdf_toc_entry_number_ordering.py`. Groups consecutive TABLE OF CONTENTS pages into
runs (consecutive by document page number), collects their combined section-number
sequences, then applies the same inversion check as P060 across the full run.

Wired into `audit_runner.py` (`collect_pdf_layout_findings`) after P061, and into
`evaluation.py` (mapped to `"list_of_tables_figures_toc"` category). Updated in
`data/processed/rules/project_added_rules.json`.

---

## Acceptance criteria

1. Emits `toc_cross_page_entry_numbers_not_nondecreasing` when multi-page TOC has combined
   section-number sequence with ≥2 inversions and ≥3 comparable entries total.
2. Does NOT flag single-page TOC (requires ≥2 consecutive pages).
3. Does NOT flag LIST OF TABLES or LIST OF FIGURES pages.
4. Does NOT flag when combined sequence is non-decreasing.
5. Does NOT flag when fewer than 3 comparable entries across all pages.
6. Skips entries with non-parseable or word-prefix section numbers silently.
7. Does NOT combine non-consecutive TOC pages into one run.
8. Findings contain only structural metadata — no entry text, section titles.
9. All P001–P061 existing tests continue to pass.

---

## Test plan (implemented)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p062_single_page_toc_no_finding` | Single TOC page → no P062 finding (P060 scope) |
| `test_p062_two_page_toc_ascending_no_finding` | Two TOC pages, combined sequence non-decreasing → no finding |
| `test_p062_two_page_toc_one_inversion_no_finding` | Two TOC pages, 1 cross-page inversion → no finding |
| `test_p062_two_page_toc_two_inversions_warns` | Two TOC pages with ≥2 combined inversions → finding |
| `test_p062_lot_unaffected` | LoT page → P062 does not fire |
| `test_p062_sparse_combined_skipped` | Fewer than 3 combined comparable entries → skipped |
| `test_p062_word_prefix_entries_excluded` | CHAPTER, APPENDIX, ABSTRACT entries not counted |
| `test_p062_finding_metadata_privacy_safe` | Findings contain only allowed keys; no entry text |
| `test_p062_import_and_wiring` | Module importable; wired into audit_runner |
| `test_p062_non_consecutive_toc_pages_not_combined` | Non-consecutive TOC pages not combined |
| `test_p062_within_page_inversions_deferred_to_p060` | Single-page inversions are P060 scope; P062 requires multi-page |
| `test_p062_subsection_cross_page_inversions_warns` | Subsection entries (X.Y) with cross-page inversions → finding |

---

## Privacy notes

All findings contain only structural metadata:
- `issue_type`, `page`, `section_type`, `page_count`, `entry_count`,
  `comparable_entry_number_count`, `inversion_count`, `first_inversion_index`,
  `triage_tier`, `source_q_rule_id`
- No entry text, section titles, chapter names, or dissertation content
- Consistent with P060 (within-page TOC) and P061 (cross-page LoT/LoF) privacy posture

## Limitations / caveats

- Requires PDF text layer; flattened/image-based TOC pages produce no findings (false negatives)
- Conservative gate (≥2 inversions) reduces false positives at the cost of missing single-inversion cross-page errors
- Non-consecutive TOC pages (e.g., page 1 and page 3 of document) are not combined
- Dissertation-era NJIT documents rarely have multi-page TOCs with parseable numeric entries; current-dataset evaluation not run (only 4/5 evaluation PDFs directly accessible)
