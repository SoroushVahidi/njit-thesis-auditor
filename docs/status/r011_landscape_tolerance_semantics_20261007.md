# R011: bottom-only allowances on landscape sheets (2026-10-07)

## Question

R011 relaxes only the text-space **bottom** edge, through three allowances:

- `BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT` (9.3 pt). Every other edge uses
  `OVERFLOW_TOLERANCE_PT` (3.0 pt).
- The final-line box / math-fragment / contents-row exception
  (`_is_ester_rejected_bottom_line_box`, up to one em, 12 pt cap).
- The references final-line allowance.

A landscape sheet's 1.5 in binding edge is the top edge when the sheet is
turned clockwise and the bottom edge when it is turned counter-clockwise.

## Provenance of the bottom allowances

**History.**

- `7090b82` (2026-08-25) set the bottom tolerance to 9.0 pt. Ester classified
  four bottom findings as false positives: Youra p42 (5.6 pt), Muyeed p19
  (5.2), Philip p55 (3.9) and Sebastian p16 (8.2). The sources were LaTeX and
  Word, and the content was prose and equations.
- `090779e` (2026-08-31) raised it to 9.3 pt. Ester classified Muyeed p36
  (9.17 pt) as a false positive. A content-independent cluster of 47 findings
  at 9.17 pt sat above a clean gap from 9.30 to 9.43 pt.
- Classification: DERIVED_FROM_ESTER_AUTHORITY (engineering calibration
  anchored on reviewed false positives).

**Ester's own range** (Youra p42, LaTeX template):

> Left ~1.5" (there are never problems with the left margins in latex) /
> Right ~1.0" to 1.1 / Top (to first text line) 1 to ~1.09" / Bottom ~0.9" to 1

**What the measured overflow is made of** (span origin vs. bbox, reviewed cases):

| Case | Overflow | Baseline below the 1 in line | Bbox below baseline |
|---|---|---|---|
| Youra p42 | 5.59 | 3.27 | 2.32 (0.19 em) |
| Sebastian p16 (Word) | 8.24 | 4.56 | 3.68 (0.31 em) |
| Muyeed p36 | 9.17 | 6.55 | 2.61 (0.22 em) |

So 9.3 pt is a combination of two things:

1. Real placement of the page's **last text line** into an ordinary 1 in bottom
   margin, which Ester accepted ("Bottom ~0.9" to 1"", plus the Word case).
2. A bbox descent artifact on the descender side of horizontal text.

Both belong to the end of the text flow, which is the text-space bottom. Every
reviewed case is portrait, where that edge is also the ordinary 1 in portrait
bottom.

## Semantics

| Sheet | Text-space edge | Portrait edge | Required | Before | After |
|---|---|---|---|---|---|
| portrait | bottom | bottom | 1 in | bottom allowances | unchanged |
| clockwise | top | **binding** | 1.5 in | 3 pt | 3 pt |
| clockwise | bottom | right | 1 in | bottom allowances | unchanged |
| clockwise | left | bottom | 1 in | 3 pt | 3 pt |
| clockwise | right | top | 1 in | 3 pt | 3 pt |
| counter-clockwise | top | right | 1 in | 3 pt | 3 pt |
| counter-clockwise | bottom | **binding** | 1.5 in | **bottom allowances** | **3 pt** |
| counter-clockwise | left | top | 1 in | 3 pt | 3 pt |
| counter-clockwise | right | bottom | 1 in | 3 pt | 3 pt |
| undetermined | bottom | binding or right | 1 in (both readings) | bottom allowances | unchanged |

**Rule.** The bottom allowances follow the end of the text flow, which is the
text-space bottom, but **never relax the binding margin**.

- No authority grants slack to the binding margin. The authority that exists
  points the other way: "there are never problems with the left margins in
  latex", and "the margin rule is very strict".
- Before this change, a counter-clockwise sheet gave its binding edge the full
  portrait-bottom allowance. That is up to about 11 pt for a single line,
  where a clockwise sheet's binding edge got 3 pt.
- The allowances are **not** remapped onto the portrait-bottom edge (text-space
  left or right). There a line overflows horizontally, at its end, so neither
  the descent artifact nor the last-line placement applies. Ester confirmed
  horizontal right-margin violations down to 5.4 pt (Sample B).
- An undetermined sheet keeps the allowance, because it reports only what
  violates both readings.

Implementation: `MarginFrame.last_line_bottom_allowances_apply` in
`rules/pdf_margins.py`. Tests: `tests/test_p011_landscape_tolerance_semantics.py`.

## Effect

- No counter-clockwise landscape sheet exists in the seven-document corpus,
  Samples A–D, or the other Ester-annotated PDFs.
- Anthony's 38 sheets are all clockwise, and none of their lines crosses the
  bottom, left or right boundary.
- No finding changes.

## Not addressed

- `BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT` applies to Word and LaTeX alike. This
  is intentional, per the 2026-08 batch (Sebastian, Word); it is not a LaTeX
  scope bug.
- `/Rotate`-built landscape pages whose text runs vertically in text space are
  part of the broader `/Rotate` audit.
