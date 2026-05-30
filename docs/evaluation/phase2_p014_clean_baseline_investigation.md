# Phase 2 P014 Clean-Baseline Investigation

Date: 2026-05-29  
Scope: Investigation of P014 named front-matter heading check findings on Sebastian Fine
clean baseline (no EF feedback). Resulted in a centering fix.

## Motivation

The Sebastian Fine Revision 3 PDF (clean baseline, no feedback annotations) produced 6 P014
warnings — one for each detected named front-matter heading. Because this is a clean baseline,
these were investigated as potential false positives.

## Investigation

All 6 findings had the same issue: `centered=False`. The headings were:
- Bold (TimesNewRomanPS-BoldMT recognized correctly)
- All-caps
- Near top
- But: line_center ≈ 325pt vs page_center = 306pt → offset 19pt > 12pt tolerance

Root cause: P014 compared heading center against the **physical page center** (306pt for a 612pt
wide page). NJIT formatting uses asymmetric margins (1.5" left = 108pt, 1.0" right = 72pt),
so the text area center is at `(108 + 540) / 2 = 324pt` — 18pt right of the page center.

All tested PDFs (Sebastian Fine, Yin H 4th, Cibaku Elson, Yin Haotian 2nd) show heading centers
at ~324pt, confirming they are correctly centered within the text area per word-processor
conventions.

## Fix

Changed `_line_centered` in `src/njit_auditor/rules/pdf_headings.py` to compare against the
text area center `(LEFT_MARGIN_PT + page.width - RIGHT_MARGIN_PT) / 2` rather than the page
center `page.width / 2`. The 12pt tolerance is preserved.

Updated the centered-heading test fixture to place headings within the text area (108–540pt)
so the test reflects realistic centering behavior.

## P014 Count Before / After

| File | Before | After | Notes |
|------|-------:|------:|-------|
| Sebastian Fine clean baseline | 6 | 0 | All were centering false positives |
| Cibaku Elson | 1 | 0 | ABSTRACT centering false positive |
| Yin Haotian 2nd | 1 | 0 | ABSTRACT centering false positive |
| Yin H 4th compressed | 10 | 0 | All centering false positives |

## No True Positives Lost

Genuinely off-center headings (e.g., heading placed at x=120 with offset ≫ 12pt from text-area
center) still trigger P014 warnings. The fix narrows the definition of "centered" to match
how documents are actually typeset (centered in text area, not on page).

## Limitations

- If a document's margins differ from NJIT standard, the text-area-center assumption may not
  hold. P014 uses the standard NJIT left/right margins from pdf_margins.py.
- All P014 findings remain heuristic signals requiring manual review.
