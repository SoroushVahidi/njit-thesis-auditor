# P055 Scope and Design

- **Date:** 2026-06-05
- **Status:** **Implemented**
- **Baseline main:** `01103fa` (PR #169 — post-P054 consistency audit; P001–P054 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **54/54** implemented (`P001`–`P054`) |
| LoT/LoF column headers | **P031** — checks that "Table"/"Figure" and "Page" labels are present |
| LoT/LoF entry number alignment | **P046** — checks left-column x-alignment of entry number tokens |
| LoT terminal-period check | **P053** — warns when LoT entries end with `.` |
| TOC terminal-period check | **P054** — warns when TOC entries end with `.` |
| LoT/LoF entry type consistency | **Not checked** — no rule verifies that LoT entries start with "Table" and LoF entries start with "Figure" |
| Remaining automatable Q-rule gaps | Q023-Q025/Q033-Q034/Q039-Q043 all deferred (high FP or privacy risk). P055 extends existing LoT/LoF infrastructure with a new cross-type consistency check. |

After P054, the automatable Q-rule gaps from `docs/status/q_rule_coverage_after_p044.md` are
exhausted (high-FP or high-privacy-risk deferrals). P055 is scoped as a practical extension
of the existing LoT/LoF infrastructure rather than a new Q-rule.

Students occasionally place figure entries in the List of Tables or table entries in the
List of Figures, especially when copying/pasting or using badly configured Word templates.
The LoT heading is "LIST OF TABLES" — every entry should begin with "Table" (or "Table X.Y").
The LoF heading is "LIST OF FIGURES" — every entry should begin with "Figure" (or "Figure X.Y").
This is detectable with very low false-positive risk using the existing `extract_toc_entry_lines`
infrastructure.

---

## Selected P055 scope

### Rule title

**P055 — LoT/LoF cross-type entry check (Q063/Q072 extension)**

### Source basis

- **Q063:** LIST OF TABLES column header is "Table" — implies entries should be table entries.
- **Q072:** LIST OF FIGURES column header is "Figure" — implies entries should be figure entries.

NJIT guidelines define the LoT as the listing of tables and the LoF as the listing of figures.
An entry starting with "Figure" in the LoT (or "Table" in the LoF) is a misplaced entry —
a clear formatting error detectable heuristically.

### Scope included

1. Create `pdf_lot_lof_entry_type.py` (new module; uses `detect_toc_like_pages` / `extract_toc_entry_lines`).
2. Add `_get_entry_type_prefix(cleaned_text)` helper: return `"table"`, `"figure"`, or `None` based on case-insensitive prefix matching (`"table"` / `"figure"` at start of entry, optionally followed by a number).
3. Add `_check_lot_entry_type_page`: for each LoT page, check that complete entries (with `page_number_token`) do NOT start with "Figure". If they do, emit advisory.
4. Add `_check_lof_entry_type_page`: for each LoF page, check that complete entries do NOT start with "Table". If they do, emit advisory.
5. Add `check_pdf_lot_lof_entry_type` (P055): iterate LoT pages (`page_type == "list_of_tables"`) and LoF pages (`page_type == "list_of_figures"`); skip pages with fewer than 2 entries.
6. Gate: only check entries with `page_number_token is not None`; skip entries shorter than 10 chars after stripping; skip entries that don't match a clear prefix pattern.
7. Emit findings at `triage_tier: medium`; issue types `lot_entry_is_figure` and `lof_entry_is_table`.
8. Privacy-safe: findings include only structural metadata (page, entry index, entry type prefix detected, section type); no table/figure title text.
9. Register P055 in `project_added_rules.json`, wire into CLI, add evaluation category mapping.

### Scope excluded

- No changes to P031 (column header labels), P046 (number alignment), P053 (LoT terminal period), P054 (TOC terminal period), or P040 (LoF terminal punctuation).
- TOC appendix entries are excluded (TOC pages handled by P042/P054).
- No title-text content in findings; only the entry-type prefix classification.
- Entries with ambiguous or no clear type prefix are skipped (false-negative preferred over false-positive).

### Expected module path

`src/njit_auditor/rules/pdf_lot_lof_entry_type.py` (new module)

### Expected issue types

- `lot_entry_is_figure` — a complete LoT entry starts with "Figure" (wrong section); NJIT LoT should contain only table entries
- `lof_entry_is_table` — a complete LoF entry starts with "Table" (wrong section); NJIT LoF should contain only figure entries

### Expected evaluation category

`list_of_tables_figures_toc`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| LoT/LoF page misclassified | Reuse `detect_toc_like_pages`; only process `list_of_tables` / `list_of_figures` pages |
| Wrap-continuation lines flagged | Only process entries with `page_number_token is not None` |
| Short fragments produce false positives | Skip entries with fewer than 10 chars after stripping |
| Ambiguous prefix (e.g., "Figurative analysis") | Require "figure" or "table" followed by whitespace and a digit or end-of-match |
| No type prefix detectable | Skip entry (prefer false negative) |
| High false-positive rate | Advisory-only at `triage_tier: medium`; gate: ≥ 2 entries on page |

---

## Acceptance criteria for implementation

1. Emits `lot_entry_is_figure` when a complete LoT entry starts with "Figure".
2. Emits `lof_entry_is_table` when a complete LoF entry starts with "Table".
3. Does NOT flag TOC entries or entries on TOC pages.
4. Skips pages with fewer than 2 detected entries.
5. Findings contain only structural metadata — no table/figure title text.
6. All P001–P054 existing tests continue to pass.

---

## Test plan (9 synthetic tests)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p055_lot_correct_entries_no_finding` | LoT entries starting with "Table" → no findings |
| `test_p055_lot_figure_entry_warns` | LoT entry starting with "Figure" → `lot_entry_is_figure` |
| `test_p055_lof_correct_entries_no_finding` | LoF entries starting with "Figure" → no findings |
| `test_p055_lof_table_entry_warns` | LoF entry starting with "Table" → `lof_entry_is_table` |
| `test_p055_wrap_continuation_skipped` | Entries without page token skipped |
| `test_p055_sparse_page_skipped` | Page with < 2 entries skipped |
| `test_p055_finding_metadata_privacy_safe` | Finding details contain no entry text |
| `test_p055_import_and_wiring` | Importable and wired in cli.py |
| `test_p055_p053_p054_unaffected` | P053/P054 unaffected by P055 addition |

---

## Relationship to existing rules

| Rule | Page type | Check |
|------|-----------|-------|
| P031 | LoT + LoF | Column header labels "Table"/"Figure" and "Page" are present |
| P040 | LoF | LoF entries have terminal punctuation |
| P046 | LoT + LoF | Entry number left-column alignment |
| P053 | LoT | LoT entries do not have terminal period |
| **P055** | LoT + LoF | LoT entries start with "Table"; LoF entries start with "Figure" |
