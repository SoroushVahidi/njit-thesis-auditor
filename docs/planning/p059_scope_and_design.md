# P059 Scope and Design

- **Date:** 2026-06-05
- **Status:** **Scoped** (not yet implemented)
- **Baseline main:** `1016857` (PR #190 — post-P058 consistency audit; P001–P058 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **58/58** implemented (`P001`–`P058`) |
| LoT/LoF page-number ordering | **P057** — warns when LoT/LoF entry page numbers are not non-decreasing |
| TOC page-number ordering | **P058** — warns when TOC entry page numbers are not non-decreasing |
| LoT/LoF numbering format consistency | **P056** — warns when section mixes chapter-based (X.Y) and sequential (N) numbering |
| LoT/LoF entry-number sequence | **Not checked** — no rule verifies that the entry numbers listed in LoT/LoF entries (e.g., Table 1, Table 2, Table 3) appear in non-decreasing order |

After P058, page-number ordering is covered for both LoT/LoF and TOC pages. The natural companion check is the entry-number dimension: entries in the List of Tables and List of Figures should be numbered in non-decreasing order (Table 1, Table 2 … Table N, or Table 1.1, Table 1.2 … Table 2.1 …). An entry numbered "Table 5" appearing before "Table 2" in the LoT indicates a copy-paste ordering error or a corrupt list.

---

## Selected P059 scope

### Rule title

LoT/LoF entry-number ordering check

### Rule ID

P059

### Q-rule basis

Implied ordering requirement for LoT/LoF entries:
- **Q063** — "Is the word 'Table' … left-aligned in a separate column?" (correct column order implies sequential numbering)
- **Q072** — "Is the word 'Figure' … left-aligned in a separate column?" (same)

### Description

Emit a WARNING when a List of Tables or List of Figures page contains complete entries whose entry numbers (the numeric token following the "Table"/"Figure" label) are not in non-decreasing order. A decrease in entry number between consecutive entries (e.g., Table 3 appears before Table 1 in the LoT) signals a copy-paste ordering error.

### Issue types

| Issue type | Trigger |
|------------|---------|
| `lot_entry_numbers_not_nondecreasing` | LoT entries with entry numbers not in non-decreasing order |
| `lof_entry_numbers_not_nondecreasing` | LoF entries with entry numbers not in non-decreasing order |

### Scope boundaries

**In scope:**
- LIST OF TABLES pages: emit `lot_entry_numbers_not_nondecreasing`
- LIST OF FIGURES pages: emit `lof_entry_numbers_not_nondecreasing`

**Out of scope:**
- TABLE OF CONTENTS pages (chapter entries don't have standalone entry numbers)
- Entries where the entry number cannot be parsed (wrap-continuation lines, non-standard prefixes)
- Pages with mixed sequential + chapter-based numbering (P056 already flags this; skip ordering check)

### Entry number parsing

For each complete entry (has `page_number_token`, text ≥ 10 chars):

1. Strip the "Table" or "Figure" prefix (case-insensitive).
2. Parse the remaining numeric token at the start of the stripped text:
   - Sequential: integer `N` (e.g., "Table 3 …" → 3)
   - Chapter-based: tuple `(C, N)` from `C.N` (e.g., "Table 2.3 …" → (2, 3))
3. Skip entries where no numeric token is parseable.
4. If the page has both sequential and chapter-based entries, skip (mixed format; P056 scope).

Comparison:
- Sequential entries: compare integer values.
- Chapter-based entries: compare `(C, N)` tuples lexicographically.

### Conservative gates

- At least 3 entries with parseable entry numbers (skip sparse pages).
- At least 2 inversions before flagging (conservative; avoids flagging on accidental single swap).
- Entries with non-parseable numbers are skipped silently.
- Mixed-format pages are skipped.

### Findings

Privacy-safe metadata only — no entry text, table/figure titles, or captions.

| Field | Value |
|-------|-------|
| `issue_type` | `lot_entry_numbers_not_nondecreasing` or `lof_entry_numbers_not_nondecreasing` |
| `page` | page number of the LoT/LoF page |
| `section_type` | `"list_of_tables"` or `"list_of_figures"` |
| `entry_count` | number of entries with parseable entry numbers |
| `comparable_entry_number_count` | same as `entry_count` |
| `inversion_count` | number of consecutive pairs with decreasing entry numbers |
| `first_inversion_index` | index of first inverted pair among comparable entries |
| `numbering_format` | `"sequential"` or `"chapter_based"` |
| `triage_tier` | `"medium"` |
| `source_q_rule_id` | `"Q063"` (LoT) or `"Q072"` (LoF) |

### triage_tier

`medium` — likely indicates a copy-paste or reordering error; common source of review feedback.

---

## Likely implementation

```
src/njit_auditor/rules/pdf_lot_lof_entry_number_ordering.py
```

New module; does not modify any existing rule module.

Issue types: `lot_entry_numbers_not_nondecreasing`, `lof_entry_numbers_not_nondecreasing`

Wire into `cli.py` and `evaluation.py` after existing P058 call.

---

## Acceptance criteria

1. Emits `lot_entry_numbers_not_nondecreasing` when LoT has ≥ 2 consecutive entry-number pairs with decreasing values and ≥ 3 comparable entries total.
2. Emits `lof_entry_numbers_not_nondecreasing` analogously for LoF.
3. Does NOT flag pages where all entry numbers are non-decreasing.
4. Does NOT flag pages with fewer than 3 comparable entries.
5. Does NOT flag TABLE OF CONTENTS pages.
6. Does NOT flag pages with mixed sequential + chapter-based numbering.
7. Skips entries where entry number is not parseable.
8. Findings contain only structural metadata — no entry text, table/figure titles, or captions.
9. All P001–P058 existing tests continue to pass.

---

## Test plan (planned)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p059_no_lot_page_no_finding` | No LoT/LoF page → no findings |
| `test_p059_lot_ascending_no_finding` | LoT entry numbers non-decreasing → no finding |
| `test_p059_lot_one_inversion_no_finding` | Single inversion below threshold → no finding |
| `test_p059_lot_two_inversions_warns` | LoT with ≥ 2 inversions → `lot_entry_numbers_not_nondecreasing` |
| `test_p059_lof_two_inversions_warns` | LoF with ≥ 2 inversions → `lof_entry_numbers_not_nondecreasing` |
| `test_p059_toc_unaffected` | TOC page → P059 does not fire |
| `test_p059_sparse_lot_skipped` | Fewer than 3 parseable entries → skipped |
| `test_p059_mixed_format_skipped` | Mixed sequential + chapter-based entries → skipped |
| `test_p059_chapter_based_two_inversions_warns` | Chapter-based numbering with ≥ 2 inversions → finding |
| `test_p059_finding_metadata_privacy_safe` | Findings contain only allowed keys; no entry text |
| `test_p059_import_and_wiring` | Module importable; returns list |
| `test_p059_unparseable_entries_skipped` | Entries with no parseable number → silently excluded |
