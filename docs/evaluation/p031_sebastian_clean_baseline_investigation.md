# P031 Sebastian Fine Clean Baseline Investigation

- **Date:** 2026-05-30
- **Baseline commit:** `0aad49c711ad3c2b351e713c77b35084e8ceca81` (investigation started); refinement merged separately
- **Dataset:** Sebastian Fine clean baseline PDF (archive-contained; local ZIP extract only)
- **Finding under review:** 2 P031 warnings on page 11 (List of Tables)

## 1. What was investigated

PR #54 reported two P031 findings on the Sebastian Fine clean baseline:

| Page | Section type | Issue types | Expected labels | Observed header labels |
|---:|---|---|---|---|
| 11 | list_of_tables | missing_left_column_header; missing_page_column_header | Table; Page | (none detected) |

This investigation asked whether those warnings reflect a real formatting gap, acceptable
layout, text-layer artifact, or ambiguous/manual-review case.

## 2. Reproduction (privacy-safe)

Re-inspection of `data/evaluation/generated/p031_evaluation/p031_summary.json` and a
structural re-run on the locally extracted clean baseline PDF confirmed:

- Page 11 is confidently classified as **list_of_tables** (`heading_bottom_y ≈ 87.1 pt`).
- One extractable list entry is present below the heading (`entry indent x0 ≈ 113.4`,
  page-number column `x1 ≈ 537.6`).
- P031 reported **high-confidence** missing **Table** and **Page** header labels with an
  empty `observed_header_labels` field.

## 3. Structural explanation (no body text)

Geometry-only inspection of page 11 showed:

| Line role | Approx. y0 (pt) | Approx. x0 (pt) | Token length |
|---|---:|---:|---|
| Main section heading | 70.5 | 275.3 | 14 |
| Left header label | 84.3 | 108.0 | 5 (`Table`) |
| Page header label | 84.3 | 504.0 | 4 (`Page`) |
| First list entry | 98.1 | 113.4 | (entry line; not quoted) |

P031’s header band before refinement started at `heading_bottom_y + 2` (`≈ 89.1 pt`). The
**Table** and **Page** labels sit at **y0 ≈ 84.3**, which is **above** that lower bound
(tighter to the main heading than the rule expected). They were therefore excluded from
header-band search despite being present in the PDF text layer.

Page 12 (List of Figures) had **Figure** and **Page** labels at **y0 ≈ 98.1**, inside the
original band, and produced **no P031 findings** — consistent with a band-position artifact
rather than absent headers across the document.

## 4. Comparison to P031 assumptions

- **Guideline intent (Q063/Q064):** List pages should show **Table**/**Figure** and **Page**
  column header labels under the section heading. The Sebastian page **does** contain those
  short labels in the text layer.
- **Rule assumption gap:** The header band began strictly **below** `heading_bottom_y + 2`.
  Tight vertical layout can place column labels slightly **above** that cutoff while still
  visually under the main heading.
- **Not a casing/token issue:** Labels matched expected tokens (`Table`, `Page`).
- **Not absent headers:** Labels were present but outside the searched band.

## 5. Conclusion

**Likely false positive (text-layer / header-band extraction artifact).**

The Sebastian Fine LoT page appears to include the expected short header labels, but P031
missed them because of an overly strict header-band lower bound. Manual review is still
advisable for bold/right-alignment requirements (outside P031 scope), but the missing-label
warnings were not supported by the extractable text.

## 6. Code change

**Yes — narrow P031 refinement applied:**

- Extend the header search band upward by 12 pt above `heading_bottom_y`.
- Skip lines classified as the main section heading (`LIST OF TABLES`, etc.) so the band
  extension does not treat the title line as a column header.

Synthetic test added: `test_p031_header_row_immediately_below_heading_no_warning`.

After refinement, re-running P031 on the locally extracted Sebastian clean baseline PDF
produces **0 P031 findings**.

## 7. Limitations

- Refinement uses coarse geometry only; bold/centering still not checked.
- The 12 pt upward extension is heuristic; unusual layouts could still be missed or misread.
- Investigation used one clean baseline PDF; Yin H 4th behavior unchanged (0 findings with
  LoT/LoF pages detected).
- Local PDF extract and evaluation summary remain gitignored; not committed.

## 8. Related docs

- Current-dataset evaluation: `docs/evaluation/p031_current_dataset_evaluation.md`
- Synthetic validation: `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md`
