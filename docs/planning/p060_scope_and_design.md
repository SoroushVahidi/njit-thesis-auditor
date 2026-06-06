# P060 Scope and Design

- **Date:** 2026-06-05
- **Status:** **Implemented**
- **Baseline main:** `fa120d9` (PR #194 — post-P059 consistency audit; P001–P059 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **59/59** implemented (`P001`–`P059`) |
| LoT/LoF page-number ordering | **P057** — warns when LoT/LoF entry page numbers are not non-decreasing |
| TOC page-number ordering | **P058** — warns when TOC entry page numbers are not non-decreasing |
| LoT/LoF entry-number ordering | **P059** — warns when LoT/LoF entry numbers (Table N / Figure N) are not non-decreasing |
| TOC section-number ordering | **Not checked** — no rule verifies that numeric section/chapter entries in the TOC (e.g., "1 Introduction", "1.1 Background", "2 Methods") appear in non-decreasing order |

After P059, entry-number ordering is covered for both LoT/LoF pages. The natural companion check is the TOC dimension: numeric section entries in the Table of Contents should be in non-decreasing order. A section numbered "2.1" appearing before "1.3" in the TOC, or "CHAPTER 3" before "CHAPTER 2", indicates a scrambled or incorrectly assembled list.

---

## Selected P060 scope

### Rule title

TOC section-number ordering check

### Rule ID

P060

### Q-rule basis

Implied by hierarchical structure and ordering requirements for the TOC:

- **Q056** — "Are level-2 and level-3 entries indented to show hierarchy?" (hierarchy implies sequential numbering)
- **Q057** — "Is there visible double spacing between consecutive section-title entries?" (sequential ordering is a prerequisite for the TOC being a valid navigation aid)

Ordering is not stated as an explicit Q-rule; it is implied by the requirement that the TOC accurately represent the document structure.

### Description

Emit a WARNING when a TABLE OF CONTENTS page contains parseable numeric section entries whose numbers are not in non-decreasing order. A decrease in section number between consecutive comparable entries (e.g., "2.1" appearing before "1.3") signals a copy-paste ordering error or corrupt TOC.

### Issue types

| Issue type | Trigger |
|------------|---------|
| `toc_entry_numbers_not_nondecreasing` | TOC entries with parseable section numbers not in non-decreasing order |

### Scope boundaries

**In scope:**
- TABLE OF CONTENTS pages only
- Numeric section entries: entries starting with a bare number pattern `N` or `N.M` (e.g., "1 Introduction", "1.1 Background", "2.3 Analysis")

**Out of scope:**
- LIST OF TABLES and LIST OF FIGURES pages (P059 covers LoT/LoF entry ordering)
- Entries starting with words (CHAPTER, ABSTRACT, ACKNOWLEDGEMENTS, LIST, APPENDIX, etc.)
- Mixed hierarchy pages (both top-level `N` entries and subsection `N.M` entries on the same page) — if the page mixes single-component and multi-component numbers from different chapter roots, the comparison is ambiguous; such pages are skipped
- Entries with non-parseable text

### Entry number parsing

For each complete entry (has `page_number_token`, text ≥ 10 chars):

1. Check if the entry text starts with a bare digit sequence, optionally followed by `.`:
   - Pattern `N ...` where N is an integer (e.g., "1 Introduction..." → (1,))
   - Pattern `N.M ...` where N.M is chapter.section (e.g., "1.1 Background..." → (1, 1))
2. Skip entries starting with a non-digit character (words like CHAPTER, ABSTRACT, etc.).
3. Skip entries where the number is not parseable.
4. If the page has both top-level entries (`N`) and subsection entries from different chapters (`N.M` with different N), skip (mixed hierarchy; too ambiguous to order-check reliably).

Comparison:
- Top-level-only entries: compare integer values.
- Subsection entries: compare `(N, M)` tuples lexicographically.

### Conservative gates

- At least 3 entries with parseable section numbers (skip sparse pages).
- At least 2 inversions before flagging (conservative; avoids flagging on accidental single swap).
- Entries with non-parseable section numbers are skipped silently.
- Mixed-hierarchy pages are skipped.

### Findings

Privacy-safe metadata only — no entry text, chapter titles, or section names.

| Field | Value |
|-------|-------|
| `issue_type` | `toc_entry_numbers_not_nondecreasing` |
| `page` | page number of the TOC page |
| `section_type` | `"table_of_contents"` |
| `entry_count` | number of entries with parseable section numbers |
| `comparable_entry_number_count` | same as `entry_count` |
| `inversion_count` | number of consecutive pairs with decreasing section numbers |
| `first_inversion_index` | index of first inverted pair among comparable entries |
| `triage_tier` | `"medium"` |
| `source_q_rule_id` | `"Q056"` |

### triage_tier

`medium` — likely indicates a scrambled TOC entry or assembly error; common source of review feedback.

---

## Likely implementation

```
src/njit_auditor/rules/pdf_toc_entry_number_ordering.py
```

New module; does not modify any existing rule module.

Issue type: `toc_entry_numbers_not_nondecreasing`

Wire into `cli.py` and `evaluation.py` after existing P059 call.

---

## Acceptance criteria

1. Emits `toc_entry_numbers_not_nondecreasing` when TOC has ≥ 2 consecutive section-number pairs with decreasing values and ≥ 3 comparable entries total.
2. Does NOT flag pages where all section numbers are non-decreasing.
3. Does NOT flag pages with fewer than 3 comparable entries.
4. Does NOT flag LIST OF TABLES or LIST OF FIGURES pages.
5. Does NOT flag pages where entries start with words (CHAPTER, ABSTRACT, APPENDIX, etc.).
6. Skips entries where section number is not parseable.
7. Skips pages with mixed hierarchy (ambiguous comparison).
8. Findings contain only structural metadata — no entry text, chapter titles, or section names.
9. All P001–P059 existing tests continue to pass.

---

## Test plan (planned)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p060_no_toc_page_no_finding` | No TOC page → no findings |
| `test_p060_toc_ascending_no_finding` | TOC section numbers non-decreasing → no finding |
| `test_p060_toc_one_inversion_no_finding` | Single inversion below threshold → no finding |
| `test_p060_toc_two_inversions_warns` | TOC with ≥ 2 inversions → `toc_entry_numbers_not_nondecreasing` |
| `test_p060_lot_unaffected` | LoT page → P060 does not fire |
| `test_p060_lof_unaffected` | LoF page → P060 does not fire |
| `test_p060_sparse_toc_skipped` | Fewer than 3 parseable entries → skipped |
| `test_p060_word_prefix_entries_skipped` | Entries starting with words → silently excluded |
| `test_p060_subsection_two_inversions_warns` | Subsection-based entries with ≥ 2 inversions → finding |
| `test_p060_finding_metadata_privacy_safe` | Findings contain only allowed keys; no entry text |
| `test_p060_import_and_wiring` | Module importable; returns list |
| `test_p060_unparseable_entries_skipped` | Entries with no parseable section number → silently excluded |
