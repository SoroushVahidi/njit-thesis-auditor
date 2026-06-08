# P070 TOC/LoT/LoF Entry Parser Recall — Synthetic Validation

- **Date:** 2026-06-08
- **Auditor scope:** P001–P070 implemented
- **Type:** Infrastructure / parser refinement only (no standalone P070 findings)
- **Module:** `src/njit_auditor/rules/pdf_toc_alignment.py`
- **Privacy:** Synthetic fixtures only; no real dissertation or EF comment text quoted.

---

## Purpose

Validate the shared P070 parser refinements that improve TOC/List entry extraction
recall for dependent rules without changing individual rule thresholds in v1.

## Affected rules

| Rule group | Parser consumer change |
|---|---|
| P018 | Alignment checks see more complete entries when wrap/split-column patterns present |
| P024, P027–P032, P036, P039–P042 | Formatting/spacing rules receive improved entry streams |
| P046–P056, P058–P062 | Alignment/ordering rules receive improved `page_number_token` recall |

## Infrastructure-only nature

P070 emits **no standalone findings**. Issue types remain owned by dependent rules.

## Q-rule basis (partial)

Q048–Q079 TOC/LoT/LoF formatting and ordering requirements — see
`docs/planning/p070_toc_lot_lof_entry_parser_recall_refinement_scope_and_design.md`.

## Synthetic test coverage

**12 tests** in `tests/test_p070_toc_lot_lof_entry_parser_recall.py`:

| # | Scenario |
|---:|---|
| 1 | Single-line TOC entry with inline page number |
| 2 | Wrapped entry pairs following right-column number |
| 3 | Short `Table` prefix with split page number |
| 4 | Short `Figure` prefix with inline page number |
| 5 | Ambiguous left-margin number not paired |
| 6 | Continued list heading not parsed as entry |
| 7 | Prose-like long line rejected |
| 8 | Empty list page yields no entries |
| 9 | `group_toc_page_runs()` combines consecutive TOC pages |
| 10 | P055 cross-type check uses parser entries |
| 11 | P062 still skips with insufficient comparable entries |
| 12 | Privacy — P055 finding details omit synthetic entry title strings |

**Regression:** full suite **988 pytest** passed (976 baseline + 12 P070 tests).

## Parser changes validated

1. Prefix-tolerant entry gates (`Table`/`Figure`/`Chapter`/`Appendix`/numeric prefix).
2. Leader-dot-aware prose guard (does not reject dotted TOC/LoT/LoF lines).
3. Safer inline page-number token extraction (requires leader dots or multi-space gap).
4. Relaxed right-column pairing for wrapped entries (12pt vertical gap).
5. Multi-line wrapped-entry merge with `is_wrapped` metadata.
6. Repeated list headings skipped during entry extraction.
7. Optional `TocPageRun` / `group_toc_page_runs()` helper for cross-page consumers.

## Privacy model

- No entry titles, captions, or dissertation text in findings or test assertions on metadata.
- Parser retains `cleaned_text` internally for dependent rules; P070 docs report counts only.

## Limitations

- No OCR; image-only list pages remain undetectable.
- No fuzzy typo matching on arbitrary headings.
- Real parser recall depends on PDF text-layer quality.
- Improvement does not prove full TOC/LoT/LoF guideline compliance.
- Five-PDF current-dataset before/after evaluation pending — evaluation PDFs not
  available in this workspace.
