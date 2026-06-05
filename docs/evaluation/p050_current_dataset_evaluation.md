# P050 Current-Dataset Evaluation

- **Date:** 2026-06-04
- **Rule:** P050 — LoT/LoF left-column header bold-style check
- **Status:** **No canonical audit run**

---

## Evaluation status

No canonical five-PDF evaluation has been run for P050.

Only 4 of 5 evaluation PDFs are directly accessible in the current workspace. Sebastian Fine Revised is ZIP-only (not directly extractable). A canonical five-PDF rerun requires all five PDFs to be directly accessible.

The canonical five-PDF aggregate (**1,446 findings**) was produced at `generated_for_commit` `00b9c2d` (pre-P035 baseline, P011–P034 scope). This aggregate has not been updated.

---

## What P050 would check

P050 checks that the "Table" column header in the List of Tables and the "Figure" column header in the List of Figures are formatted in bold, when font metadata is reliably available. It only fires when:

- The page is classified as `list_of_tables` or `list_of_figures`
- At least 3 complete entries (with page-number right-x) are detected
- The left-column header label ("Table"/"Figure") is found in the header zone
- All spans in the header label expose non-None font metadata and none are bold

---

## Synthetic validation

9 synthetic tests pass. See `docs/evaluation/p050_lot_lof_left_column_header_bold_synthetic_validation.md`.

---

## Recommendation

Do not add P050 counts to the 1,446 canonical aggregate until a full P001–P050 five-PDF rerun is completed with all five evaluation PDFs accessible.
