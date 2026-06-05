# P056 Scope and Design

- **Date:** 2026-06-05
- **Status:** **Implemented**
- **Baseline main:** `6ca1119` (PR #173 — post-P055 consistency audit; P001–P055 implemented)

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
| LoT/LoF numbering format consistency | **Not checked** — no rule verifies that numbering format (chapter-based X.Y vs plain sequential N) is consistent within a LoT or LoF section |

After P055, the automatable Q-rule gaps from `docs/status/q_rule_coverage_after_p044.md` remain exhausted (high-FP or high-privacy-risk deferrals). P056 is scoped as a practical extension of the existing LoT/LoF infrastructure: a numbering-format consistency check.

Students and Word templates occasionally mix chapter-based numbering (Table 1.1, Table 2.3) with plain sequential numbering (Table 1, Table 2) within the same LoT or LoF section. This inconsistency is detectable from the structure of the entry number token without reading any title text.

---

## Selected P056 scope

### Rule title

**P056 — LoT/LoF entry numbering format consistency check**

### Source basis

- **Q063:** LIST OF TABLES column header is "Table" — implies entries should follow consistent naming conventions.
- **Q072:** LIST OF FIGURES column header is "Figure" — same.
- **Practical extension:** NJIT guidelines do not explicitly specify whether chapter-based (X.Y) or plain sequential (N) numbering should be used, but the format must be consistent throughout a section.

### Scope included

1. Create `pdf_lot_lof_number_format.py` (new module; uses `detect_toc_like_pages` / `extract_toc_entry_lines`).
2. Add `_classify_entry_number_format(cleaned_text)` helper: returns `"chapter_based"` (e.g. "Table 1.2"), `"sequential"` (e.g. "Table 1"), or `None` for ambiguous/no-match.
3. Add `_check_lot_number_format_page`: collect format classifications for all complete LoT entries on a page; if both `chapter_based` and `sequential` are present, emit advisory.
4. Add `_check_lof_number_format_page`: same for LoF pages.
5. Add `check_pdf_lot_lof_number_format` (P056): iterate LoT pages (`page_type == "list_of_tables"`) and LoF pages (`page_type == "list_of_figures"`); skip pages with fewer than 2 complete entries; require ≥ 2 entries of each format type to flag.
6. Gate: only check entries with `page_number_token is not None`; skip entries shorter than 10 chars after stripping; require at least 2 entries of each mixed format before flagging.
7. Emit findings at `triage_tier: low`; issue types `lot_mixed_numbering_format` and `lof_mixed_numbering_format`.
8. Privacy-safe: findings include only structural metadata (page, format counts, section type); no title text.
9. Register P056 in `project_added_rules.json`, wire into CLI, add evaluation category mapping.

### Scope excluded

- No changes to P031, P046, P048, P053, P054, or P055.
- Does not check whether chapter-based or sequential numbering is "correct" — only that the format is consistent within the section.
- Entries with ambiguous numbering (e.g., appendix entries "Table A.1") are skipped.
- TOC entries are excluded.
- No title-text content in findings.

### Expected module path

`src/njit_auditor/rules/pdf_lot_lof_number_format.py` (new module)

### Expected issue types

- `lot_mixed_numbering_format` — LoT section contains a mix of chapter-based and sequential entry numbering formats
- `lof_mixed_numbering_format` — LoF section contains a mix of chapter-based and sequential entry numbering formats

### Expected evaluation category

`list_of_tables_figures_toc`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| Sparse pages | Skip pages with < 2 complete entries (page_number_token present) |
| Ambiguous format | Only classify `chapter_based` (X.Y) or `sequential` (N); ignore appendix/letter formats |
| Single-format pages | Only flag if ≥ 2 entries of each format type are present in the page/section |
| Wrap continuation lines | Only process entries with page_number_token |
| Short fragments | Skip entries < 10 chars after stripping |
| False positives on appendix-prefixed entries | Skip entries where number starts with a letter (A.1, B.2) |
| Low-severity | Emit at `triage_tier: low` (advisory only) |

---

## Acceptance criteria for implementation

1. Emits `lot_mixed_numbering_format` when LoT contains both "Table 1.2" and "Table 1" style entries.
2. Emits `lof_mixed_numbering_format` when LoF contains both "Figure 1.2" and "Figure 1" style entries.
3. Does NOT flag LoT/LoF pages where all entries use the same format.
4. Does NOT flag TOC pages.
5. Findings contain only structural metadata — no table/figure title text.
6. All P001–P056 existing tests continue to pass.

---

## Test plan (9 synthetic tests)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p056_lot_consistent_sequential_no_finding` | All LoT entries sequential (Table 1, Table 2) → no findings |
| `test_p056_lot_consistent_chapter_based_no_finding` | All LoT entries chapter-based (Table 1.1, Table 1.2) → no findings |
| `test_p056_lot_mixed_format_warns` | LoT has both "Table 1" and "Table 1.2" entries → `lot_mixed_numbering_format` |
| `test_p056_lof_consistent_no_finding` | All LoF entries consistent → no findings |
| `test_p056_lof_mixed_format_warns` | LoF has both "Figure 1" and "Figure 1.2" entries → `lof_mixed_numbering_format` |
| `test_p056_toc_unaffected` | TOC pages → P056 does not fire |
| `test_p056_sparse_page_skipped` | Page with < 2 complete entries → skipped |
| `test_p056_finding_metadata_privacy_safe` | Findings contain no entry text or title content |
| `test_p056_import_and_wiring` | Importable and wired in cli.py |

---

## Relationship to existing rules

| Rule | Page type | Check |
|------|-----------|-------|
| P031 | LoT + LoF | Column header labels "Table"/"Figure" and "Page" are present |
| P046 | LoT + LoF | Entry number left-column alignment |
| P053 | LoT | LoT entries do not have terminal period |
| P055 | LoT + LoF | LoT entries start with "Table"; LoF entries start with "Figure" |
| **P056** | LoT + LoF | LoT/LoF entries use consistent numbering format (chapter-based vs sequential) |
