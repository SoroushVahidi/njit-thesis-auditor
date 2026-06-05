# P050 Scope and Design

- **Date:** 2026-06-04
- **Status:** **Implemented**
- **Baseline main:** `8f2e2e5` (PR #144 — post-P049 documentation consistency; P001–P049 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **49/49** implemented (`P001`–`P049`) |
| LoT/LoF "Page" column header | **P031** — presence + approximate alignment; **P049** — tighter right-edge alignment + bold check |
| LoT/LoF "Table"/"Figure" left column header | **P031** — presence + approximate left alignment; **bold check not verified** |
| Remaining column-header gap | Q063/Q072 still have incomplete coverage because P031 and P049 do not verify the bold style of the left column header ("Table"/"Figure" label) |

P050 should be the narrow left-column complement to P049. It adds the bold-style check
for the "Table" and "Figure" column headers, exactly as P049 added it for the "Page" header.

---

## Selected P050 scope

### Rule title

**P050 — PDF LoT/LoF left-column header ("Table"/"Figure") bold-style check**

### Source basis

- **Q063:** List of Tables `Table` label should be bold and left-aligned under the table-number column.
- **Q072:** List of Figures `Figure` label should be bold and left-aligned under the figure-number column.

### Scope included

1. Reuse `detect_toc_like_pages`, `extract_toc_entry_lines`, and P031 header-zone helpers.
2. Process only `list_of_tables` and `list_of_figures` pages with at least MIN_COMPLETE_ENTRIES=3 complete entries.
3. Locate the "Table"/"Figure" left column header in the P031 header zone (existing `_matches_left_label` helper).
4. Check bold style only when font metadata is available and consistent across all header spans.
5. Skip ambiguous, sparse, image-only, or metadata-unreliable pages.
6. Emit privacy-safe metadata only: page number, section type, issue type, entry count, confidence, source Q-rule ID.

### Scope excluded

- No left-column alignment refinement (P031 already checks with 80pt tolerance; risk of FP is higher for alignment than bold).
- No LoT/LoF entry text, captions, titles, or arbitrary extracted text in findings.
- No changes to P031 or P049 behavior.
- Implementation: extended `src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py` with `check_pdf_lot_lof_left_column_header_bold`. Wired into CLI and evaluation mapping. 9 synthetic tests added.

### Expected module path

Extend `src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py` (same module as P049)
or create `src/njit_auditor/rules/pdf_lot_lof_left_column_header_bold.py`.

Preferred: extend the P049 module to keep all column-header style checks together.

### Expected issue types

- `lot_table_header_not_bold` (Q063, only when font metadata is reliable)
- `lof_figure_header_not_bold` (Q072, only when font metadata is reliable)

### Expected evaluation category

`list_of_tables_figures_toc`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| Bold font metadata unreliable in some PDFs | Only check bold when all spans expose clear font/style evidence; otherwise skip |
| Left header label may be split or absent | Reuse P031 header-zone detection; skip when no confident match |
| Overlap with P031 | P031 handles presence and coarse alignment; P050 only adds bold style when metadata is reliable |

---

## Acceptance criteria for implementation

1. Emits `lot_table_header_not_bold` when "Table" header text is confidently not bold on a LoT page.
2. Emits `lof_figure_header_not_bold` when "Figure" header text is confidently not bold on a LoF page.
3. Emits nothing for bold headers.
4. Emits nothing when font metadata is unreliable.
5. Emits nothing for sparse, ambiguous, or image-only pages.
6. Findings contain only privacy-safe style metadata.
7. P031 and P049 behavior remains unchanged.

---

## Validation plan

| Scope | Command |
|-------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| Focused P050 tests | `python -m pytest tests/test_pdf_rules.py -q -k "p050 or left_column_header_bold"` |
| Lint | `ruff check .` |
| Types | `mypy src` |
| Full suite | `python -m pytest` |

---

## Safety

- Do not commit generated outputs under `data/evaluation/generated/`.
- Do not claim a canonical five-PDF current-dataset rerun unless all five PDFs are directly available and rerun.
- Keep findings and docs aggregate/metadata-only; do not quote dissertation content or LoT/LoF entries.
