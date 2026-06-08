# P071 References Section Localization Recall — Synthetic Validation

- **Date:** 2026-06-08
- **Auditor scope:** P001–P071 implemented
- **Type:** Infrastructure / localization refinement only (no standalone P071 findings)
- **Module:** `src/njit_auditor/rules/pdf_references_citations_structural.py`
- **Privacy:** Synthetic fixtures only; no real dissertation or EF comment text quoted.

---

## Purpose

Validate the shared P071 localization refinements that improve P064 references-section
reach on compressed, flattened, and annotation-noisy PDFs without introducing new issue
types in v1.

## Affected rules

| Rule | Localization consumer change |
|---|---|
| P064 | Checks A/B/C can run when body-start or heading localization previously failed or x-variance skip fired on outlier geometry |

## Infrastructure-only nature

P071 emits **no standalone findings**. Issue types remain owned by P064 only.

## Q-rule basis (partial)

Q028–Q030 references/citations structural requirements — see
`docs/planning/p071_references_section_localization_recall_refinement_scope_and_design.md`.

## Synthetic test coverage

**12 tests** in `tests/test_p071_references_section_localization_recall.py`:

| # | Scenario |
|---:|---|
| 1 | Normal REFERENCES heading still detected |
| 2 | Collapsed `CHAPTER1` body-start detected |
| 3 | Collapsed `APPENDIXA` body-start detected |
| 4 | Tail scan finds BIBLIOGRAPHY without chapter heading |
| 5 | Tail scan ignores body prose containing "references" |
| 6 | Tail scan rejects TOC-style leader-dot REFERENCES line |
| 7 | Multiple tail REFERENCES candidates skipped (ambiguous) |
| 8 | Cluster x-variance ignores annotation outlier x-positions |
| 9 | Genuinely inconsistent x-variance still triggers skip |
| 10 | P064 indentation issue emitted for mixed hanging-indent entries |
| 11 | Clean references section produces no findings |
| 12 | Privacy — finding details omit synthetic entry text |

**Regression:** full suite **1000 pytest** passed (988 baseline + 12 P071 tests).

## Localization changes validated

1. Collapsed CHAPTER/APPENDIX body-start matching (`CHAPTER1`, `APPENDIXA`, etc.).
2. Back-matter tail heading fallback for standalone REFERENCES/BIBLIOGRAPHY headings.
3. TOC-style leader-dot line rejection in heading detection.
4. Dominant-entry-cluster x-variance gating (outlier annotation lines ignored for skip gate).
5. Entry grouping for checks B/C still uses all candidate lines (cluster filter applies to skip gate only).

## Privacy model

- No reference entry text, author names, DOIs, URLs, or EF comment text in findings or docs.
- Synthetic tests assert metadata keys only; secret placeholder strings must not appear in exports.

## Limitations

- No OCR; image-only references pages remain undetectable.
- No citation-style enforcement (APA/IEEE/etc.).
- Tail-scan ambiguity still skips when multiple standalone candidates appear.
- Real localization recall depends on PDF text-layer quality.
- Improved reach does not prove full references/citations guideline compliance.
