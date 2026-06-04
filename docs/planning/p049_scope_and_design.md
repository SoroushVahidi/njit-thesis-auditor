# P049 Scope and Design

- **Date:** 2026-06-04
- **Status:** **Scoped — not yet implemented**
- **Baseline main:** `3b49cfe` (PR #140 — post-P048 documentation consistency; P001–P048 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **48/48** implemented (`P001`-`P048`) |
| LoT/LoF column headers | **P031** — checks expected `Table`/`Figure` and `Page` header labels in coarse header regions |
| LoT/LoF entry and page-number columns | **P046/P048** — entry-number left-column and page-number right-column alignment |
| Remaining column-header gap | Q064/Q073 still have only partial coverage because P031 does not verify bold style or tighter page-label right-column alignment |

P049 should be a narrow P031 complement, not a rewrite of P031. It should only add conservative geometry/font-metadata checks where the PDF text layer exposes enough information.

---

## Selected P049 scope

### Rule title

**P049 — PDF LoT/LoF column-header style/alignment refinement**

### Source basis

- **Q064:** List of Tables `Page` label should be bold and right-aligned under the heading/page-number column.
- **Q073:** List of Figures `Page` label should be bold and right-aligned under the heading/page-number column.
- Optional partial support for **Q063/Q072** only when needed to evaluate left header style consistently.

### Scope included

1. Reuse `detect_toc_like_pages`, `extract_toc_entry_lines`, and P031 header-zone helpers where possible.
2. Process only `list_of_tables` and `list_of_figures` pages with at least one confident entry/page-number geometry signal.
3. Check the `Page` header x-position against the detected page-number right-column anchor with a conservative tolerance.
4. Check bold style only when font metadata is available and consistent across header spans.
5. Skip ambiguous, sparse, image-only, or metadata-unreliable pages.
6. Emit privacy-safe metadata only: page number, section type, issue type, observed/expected geometry, tolerance, confidence, and source Q-rule ID.

### Scope excluded

- No LoT/LoF entry text, captions, titles, page-number-adjacent text, or arbitrary extracted text in findings.
- No semantic/caption/title validation.
- No changes to P031 behavior unless a small helper extraction is required.
- No implementation in this scoping PR.

### Expected module path

`src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py`

### Expected issue types

- `lot_page_header_not_right_aligned` (Q064)
- `lof_page_header_not_right_aligned` (Q073)
- `lot_page_header_not_bold` (Q064, only when font metadata is reliable)
- `lof_page_header_not_bold` (Q073, only when font metadata is reliable)

### Expected evaluation category

`list_of_tables_figures_toc`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| Bold font metadata is unreliable in some PDFs | Only check bold when spans expose clear font/style evidence; otherwise skip style findings |
| Header labels may be split or absent in text extraction | Reuse P031 header-zone detection and skip ambiguous pages |
| Page-number column may vary or be absent | Require enough complete entries to derive a stable page-number anchor |
| Overlap with P031/P048 | P031 remains presence/coarse alignment; P048 remains entry page-number alignment; P049 only targets header style/tighter alignment |

---

## Acceptance criteria for implementation

1. Emits LoT/LoF-specific findings when the `Page` header is clearly far from the detected page-number column.
2. Emits bold-style findings only when the `Page` header text is confidently not bold.
3. Emits nothing for correct synthetic LoT/LoF headers.
4. Emits nothing for sparse, ambiguous, image-only, or metadata-unreliable pages.
5. Findings contain only privacy-safe geometry/style metadata.
6. P031, P046, and P048 behavior remains unchanged except for explicitly reused helpers.

---

## Validation plan

| Scope | Command |
|-------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| Focused P049 tests | `python -m pytest tests/test_pdf_rules.py -q -k "p049 or column_header_style"` |
| Lint | `ruff check .` |
| Types | `mypy src` |
| Full suite | `python -m pytest` |

---

## Safety

- Do not commit generated outputs under `data/evaluation/generated/`.
- Do not claim a canonical five-PDF current-dataset rerun unless all five PDFs are directly available and rerun.
- Keep findings and docs aggregate/metadata-only; do not quote dissertation content or LoT/LoF entries.
