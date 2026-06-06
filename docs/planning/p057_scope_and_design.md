# P057 Scope and Design

- **Date:** 2026-06-05
- **Status:** **Implemented**
- **Baseline main:** `c6a21e2` (PR #177 — post-P056 consistency audit; P001–P056 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **56/56** implemented (`P001`–`P056`) |
| LoT/LoF column headers | **P031** — checks "Table"/"Figure" and "Page" label presence |
| LoT/LoF entry number alignment | **P046** — checks left-column x-alignment of entry number tokens |
| LoT/LoF page number alignment | **P048** — checks right-column alignment |
| LoT terminal-period check | **P053** — warns when LoT entries end with `.` |
| TOC terminal-period check | **P054** — warns when TOC entries end with `.` |
| LoT/LoF cross-type entry check | **P055** — warns when LoT entry starts with "Figure" or LoF entry starts with "Table" |
| LoT/LoF numbering format consistency | **P056** — warns when section mixes chapter-based (X.Y) and sequential (N) numbering |
| LoT/LoF page-number ordering | **Not checked** — no rule verifies that page numbers listed in LoT/LoF entries appear in non-decreasing order |

After P056, the structural LoT/LoF checks cover column headers, entry type correctness, numbering format consistency, terminal punctuation, and alignment. One remaining mechanical check is page-number ordering: entries in the List of Tables and List of Figures should reference pages in the order they appear in the document (non-decreasing). A table on page 50 appearing before a table on page 30 in the LoT indicates either a copy-paste ordering error or a structural document problem.

---

## Selected P057 scope

### Rule title

LoT/LoF page-number ordering check

### Rule ID

P057

### Q-rule basis

Partial/heuristic coverage for:
- **Q069** — "Are all table page numbers aligned vertically in one right column?" (ordering is implied by a correct list)
- **Q079** — "Are all figure page numbers aligned vertically in one right column?" (same)

### Description

Emit a WARNING when a List of Tables or List of Figures page contains complete entries whose listed page numbers are not in non-decreasing order. A decrease in page number between consecutive complete entries signals either an out-of-order entry or a copy-paste error.

### Issue types

| Issue type | Trigger |
|------------|---------|
| `lot_page_numbers_not_ascending` | LoT has two consecutive complete entries where the second entry's page number is less than the first's |
| `lof_page_numbers_not_ascending` | LoF has same pattern |

### Gates (conservative)

1. Only entries with `page_number_token is not None` (complete entries; excludes wrap continuations).
2. `page_number_token` must parse to a positive integer.
3. Page with fewer than **3** complete entries with valid integer page numbers → skip (too sparse to establish ordering).
4. Entry text length ≥ 10 chars (existing short-entry filter).
5. Require **≥ 2** out-of-order pairs before flagging (single swap may be a multi-volume edge case).
6. TOC pages excluded.

### Finding details (privacy-safe metadata only)

```python
{
    "issue_type": "lot_page_numbers_not_ascending",
    "page": str(page_number),
    "section_type": "list_of_tables",
    "entry_count": str(total_complete),
    "out_of_order_count": str(n_inversions),
    "triage_tier": "medium",
    "source_q_rule_id": "Q069",
}
```

No entry text, table/figure titles, or caption content is included.

### Triage tier

`medium` — page-number ordering violations are relatively actionable and indicate a real structural problem. Not `low` because the signal is deterministic (integer comparison), not advisory.

---

## Design notes

- **Algorithm:** Collect `(entry_index, page_num)` pairs for all complete entries with valid integer `page_number_token`. Walk the sequence; count inversions (positions where `page_num[i] > page_num[i+1]`). If `n_inversions >= 2`, emit one finding per LoT/LoF page.
- **Multi-page LoT/LoF:** The check is per-page (each `TocPageContext` is checked independently). If a LoT spans two pages, page-number ordering is checked separately on each page. Cross-page ordering is not checked in v1 (too many false positives for appendix entries that may restart numbering).
- **Appendix entries:** Entries with letter-prefixed numbers (e.g., "Table A.1") have non-integer page references and are skipped by the integer-parse gate. This avoids false positives for appendix tables that may appear on pages interleaved with body tables.
- **One finding per page:** A single `WARNING` finding is emitted for the page, with `out_of_order_count` in the details. No finding text quotes page-number values from entries.

---

## Relationship to existing rules

| Rule | Page type | Check |
|------|-----------|-------|
| P018 | TOC + LoT + LoF | Leader and page-number column alignment |
| P046 | LoT + LoF | Entry number left-column x-alignment |
| P048 | LoT + LoF | Page-number right-column x-alignment |
| P053 | LoT | LoT entries do not have terminal period |
| P055 | LoT + LoF | LoT entries start with "Table"; LoF entries start with "Figure" |
| P056 | LoT + LoF | LoT/LoF entries use consistent numbering format |
| **P057** | LoT + LoF | LoT/LoF entry page numbers are in non-decreasing order |

---

## Implementation sketch

```python
# src/njit_auditor/rules/pdf_lot_lof_page_order.py

MIN_ENTRY_TEXT_LEN = 10
MIN_COMPLETE_ENTRIES = 3
MIN_INVERSIONS_TO_FLAG = 2

def _parse_page_num(token: str) -> int | None:
    s = token.strip()
    return int(s) if s.isdigit() else None

def _check_page_order(context, entries, issue_type, section_type, source_q_rule_id):
    page_nums = []
    for entry in entries:
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        n = _parse_page_num(entry.page_number_token)
        if n is not None:
            page_nums.append(n)
    if len(page_nums) < MIN_COMPLETE_ENTRIES:
        return []
    inversions = sum(
        1 for i in range(len(page_nums) - 1) if page_nums[i] > page_nums[i + 1]
    )
    if inversions < MIN_INVERSIONS_TO_FLAG:
        return []
    return [AuditFinding(
        rule_id="P057",
        severity=Severity.WARNING,
        page=context.page.page_number,
        message=(
            f"List entry page numbers are not in ascending order: "
            f"{inversions} out-of-order pair(s) detected among {len(page_nums)} entries. "
            f"NJIT guidelines (Q069/Q079) imply entries should be ordered by page."
        ),
        details={
            "issue_type": issue_type,
            "page": str(context.page.page_number),
            "section_type": section_type,
            "entry_count": str(len(page_nums)),
            "out_of_order_count": str(inversions),
            "triage_tier": "medium",
            "source_q_rule_id": source_q_rule_id,
        },
    )]
```

---

## Acceptance criteria

1. Emits `lot_page_numbers_not_ascending` when LoT has ≥ 2 consecutive pairs with decreasing page numbers.
2. Emits `lof_page_numbers_not_ascending` when LoF has same.
3. Does NOT flag LoT/LoF pages where all entries have ascending or equal page numbers.
4. Does NOT flag pages with fewer than 3 complete entries with valid integer page numbers.
5. Does NOT flag TOC pages.
6. Findings contain only structural metadata — no entry text, table/figure titles, or caption content.
7. All P001–P056 existing tests continue to pass.

---

## Test plan (planned)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p057_lot_ascending_no_finding` | All LoT page numbers ascending → no findings |
| `test_p057_lot_one_inversion_no_finding` | Single inversion below threshold → no findings |
| `test_p057_lot_two_inversions_warns` | LoT with ≥ 2 inversions → `lot_page_numbers_not_ascending` |
| `test_p057_lof_mixed_order_warns` | LoF with ≥ 2 inversions → `lof_page_numbers_not_ascending` |
| `test_p057_toc_unaffected` | TOC pages → P057 does not fire |
| `test_p057_sparse_page_skipped` | Page with < 3 complete entries → skipped |
| `test_p057_non_integer_page_skipped` | Entries with non-integer page tokens → skipped gracefully |
| `test_p057_finding_metadata_privacy_safe` | Findings contain no entry text or title content |
| `test_p057_import_and_wiring` | Importable and wired in cli.py |
