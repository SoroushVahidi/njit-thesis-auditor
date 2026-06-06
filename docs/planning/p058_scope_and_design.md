# P058 Scope and Design

- **Date:** 2026-06-05
- **Status:** **Scoped** (not yet implemented)
- **Baseline main:** `8a1b74b` (PR #186 — post-P057 consistency audit; P001–P057 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **57/57** implemented (`P001`–`P057`) |
| LoT/LoF page-number ordering | **P057** — checks that LoT/LoF entry page numbers are non-decreasing |
| TOC page-number ordering | **Not checked** — no rule verifies that page numbers listed in TABLE OF CONTENTS body entries appear in non-decreasing order |

After P057, all structural LoT/LoF ordering checks are covered. The natural companion check is the TABLE OF CONTENTS itself: body chapter entries listed in the TOC should reference pages in non-decreasing order, consistent with the physical order of chapters in the document. An entry for Chapter 5 (page 80) appearing before Chapter 2 (page 15) in the TOC indicates a copy-paste ordering error or a corrupt TOC.

---

## Selected P058 scope

### Rule title

TOC page-number ordering check

### Rule ID

P058

### Q-rule basis

Implied by general TOC correctness; practical refinement of P057's ordering pattern to TABLE OF CONTENTS pages.

### Description

Emit a WARNING when a TABLE OF CONTENTS page contains body entries (arabic integer page numbers) that are not in non-decreasing order. A decrease in page number between consecutive arabic-numbered entries signals either an out-of-order TOC entry or a copy-paste error.

### Issue types

| Issue type | Trigger |
|------------|---------|
| `toc_page_numbers_not_nondecreasing` | TOC has ≥ 2 consecutive arabic-numbered entries where the second entry's page number is less than the first's |

### Gates (conservative)

1. Only `list_of_tables_figures_toc`-detected pages with `page_type == "table_of_contents"`.
2. Only entries with `page_number_token is not None` (complete entries; excludes wrap continuations).
3. `page_number_token` must parse to a positive integer (roman numerals skipped — front-matter entries excluded naturally).
4. Page with fewer than **3** complete entries with valid integer page numbers → skip (too sparse).
5. Entry text length ≥ 10 chars (existing short-entry filter).
6. Require **≥ 2** out-of-order pairs before flagging.

### Finding metadata (privacy-safe metadata only)

```python
{
    "issue_type": "toc_page_numbers_not_nondecreasing",
    "page": str(page_number),
    "section_type": "table_of_contents",
    "entry_count": str(total_comparable),
    "comparable_page_number_count": str(total_comparable),
    "inversion_count": str(inversions),
    "first_inversion_index": str(first_inversion_index),
    "triage_tier": "medium",
    "source_q_rule_id": "Q057",
}
```

No entry text, chapter titles, heading content, or arbitrary extracted text is included.

### Triage tier

`medium` — page-number ordering violations in the TOC are actionable and indicate a real structural problem. Deterministic (integer comparison), not advisory.

---

## Design notes

- **Algorithm:** Same as P057. Collect `(entry_index, page_num)` pairs for all complete TOC entries with valid positive integer `page_number_token`. Walk the sequence; count inversions. If `n_inversions >= 2`, emit one finding per TOC page.
- **Roman numeral entries:** Entries with roman-numeral page tokens (front-matter: Abstract, Acknowledgements, etc.) return `None` from `_parse_page_num` and are excluded. This means checking is restricted to the body-chapter section of the TOC, which is appropriate.
- **Multi-page TOC:** The check is per-page (each `TocPageContext` is checked independently). If the TOC spans two pages, page-number ordering is checked per page. Cross-page ordering is not checked in v1.
- **LoT/LoF excluded:** `_SECTION_CONFIG` maps only `"table_of_contents"` to the issue type; LoT/LoF are excluded (already covered by P057).
- **One finding per page:** A single `WARNING` finding is emitted per page with `inversion_count` in the metadata. No page-number values are quoted.
- **Infrastructure reuse:** Module will import `detect_toc_like_pages`, `extract_toc_entry_lines`, `TocPageContext`, `TocEntryLine` from `pdf_toc_alignment.py`, and can reuse the `_parse_page_num` helper from P057 or define its own.

---

## Relationship to existing rules

| Rule | Page type | Check |
|------|-----------|-------|
| P018 | TOC + LoT + LoF | Leader and page-number column alignment |
| P024 | TOC + LoT + LoF | Entry capitalization and terminal punctuation style |
| P039 | TOC | TOC level indentation hierarchy (L1/L2/L3) |
| P054 | TOC | TOC entries must not have terminal period |
| P057 | LoT + LoF | LoT/LoF entry page numbers are in non-decreasing order |
| **P058** | TOC | TOC body-entry page numbers are in non-decreasing order |

---

## Likely implementation

```
src/njit_auditor/rules/pdf_toc_page_number_ordering.py
```

Issue type: `toc_page_numbers_not_nondecreasing`

---

## Acceptance criteria

1. Emits `toc_page_numbers_not_nondecreasing` when TOC has ≥ 2 consecutive arabic-numbered entry pairs with decreasing page numbers.
2. Does NOT flag TOC pages where all arabic-numbered entries have ascending or equal page numbers.
3. Does NOT flag pages with fewer than 3 comparable (arabic integer) entries.
4. Does NOT flag LoT or LoF pages.
5. Skips entries with roman-numeral page tokens (front-matter entries).
6. Findings contain only structural metadata — no entry text, chapter titles, or heading content.
7. All P001–P057 existing tests continue to pass.

---

## Test plan (planned)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p058_toc_ascending_no_finding` | All TOC arabic entries ascending → no findings |
| `test_p058_toc_one_inversion_no_finding` | Single inversion below threshold → no findings |
| `test_p058_toc_two_inversions_warns` | TOC with ≥ 2 inversions → `toc_page_numbers_not_nondecreasing` |
| `test_p058_lot_lof_unaffected` | LoT and LoF pages → P058 does not fire |
| `test_p058_roman_entries_skipped` | Roman-numeral page tokens excluded from comparison |
| `test_p058_sparse_toc_skipped` | Fewer than 3 arabic entries → skipped |
| `test_p058_finding_metadata_privacy_safe` | Findings contain only allowed keys |
| `test_p058_import_and_wiring` | Module importable; returns list |
