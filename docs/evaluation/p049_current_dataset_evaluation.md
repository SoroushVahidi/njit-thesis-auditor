# P049 Current-Dataset Evaluation

- **Date:** 2026-06-04
- **Rule:** P049 — PDF LoT/LoF column-header style/alignment refinement
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_column_header_style_alignment.py`
- **Q-rule basis:** Q064 (List of Tables Page header), Q073 (List of Figures Page header)

---

## Status: Not run — canonical five-PDF rerun blocked

Only 4 of the 5 evaluation PDFs are directly accessible in the workspace (Sebastian Fine Revised
is available as a ZIP archive only, not as a directly loadable PDF). A canonical five-PDF
P001–P049 aggregate rerun is therefore not possible at this time.

The canonical aggregate (1,446 findings from P001–P034, generated at commit `00b9c2d`) remains
unchanged. P049 findings are not included in the current canonical baseline.

---

## What would a canonical run show?

P049 is a conservative heuristic. Expected behavior on real NJIT PDFs:

- Many LoT/LoF pages may not expose reliable bold font metadata in the text layer (depends on PDF
  toolchain), so `lot/lof_page_header_not_bold` findings would be suppressed for those PDFs.
- Right-alignment findings (`lot/lof_page_header_not_right_aligned`) would only fire when the
  Page header's right edge deviates more than 25pt from the median page-number right-column anchor.
- Expected finding count: 0 for well-formatted PDFs; 1–2 per section for formatting outliers.

---

## Next step

Run a full P001–P049 aggregate when all five evaluation PDFs become directly accessible.
Until then, the canonical baseline remains at `generated_for_commit: 00b9c2d`.
