# R011: outdented reference-number labels (2026-10-06)

## Behavior

On a confident references page (a REFERENCES/BIBLIOGRAPHY heading, or two or
more bracket-numbered entries; never a Table of Contents page; portrait sheets
only), R011 now measures the left edge of an entry line from where the entry
text starts, instead of from the "[n]" label, when all of these hold:

- the line opens with a standalone `[n]` label span, followed by a separate
  entry-text span that starts at or after the label's right edge;
- at least two such labels on the page share a right edge (within 1.5 pt),
  forming a label column.

Everything else is measured exactly as before:

- entry text that crosses the left margin (with or without a label);
- any right, top or bottom overflow;
- body text, captions, tables and figures;
- labels merged into the same span as their text;
- unaligned labels.

No tolerance changed. Implementation: `rules/pdf_margins.py`
(`_reference_label_column_x1`, `_left_edge_excluding_reference_label`).
Tests: `tests/test_p011_outdented_reference_labels.py`.

## DIRECT_ESTER_AUTHORITY

All of these are R011 entries on the live feedback sheet (the returned sheet
exports are kept private; none were modified).

- **Youra p42, "Ester Question 1" column:** "All dissertations that use the
  LATEX template will have this issue … I belive the margins in the latex to
  be set up correctly … Left ~1.5" ( there are never problems with the left
  margins in latex)".
- **Youra p42, verdict:** false positive, "this dissertation was written using
  LATEX and the margins of the template are set up this way. I do not ask
  students to make this correction".
- **Philip p55 and Muyeed p19:** false positive, "written using LATEX and the
  margins of the template are set up this way".
- **Patrick p88 (R011-R015 follow-up), TRUE_VIOLATION:** reference **entry
  text** (one long title word) crossing the **right** margin by 18 pt. The
  labels on that page sit inside the margin.

## DERIVED_POLICY_APPLICATION (not an Ester ruling)

The derived rule is: outdented numeric reference labels whose entry text
starts at or inside the 1.5 in edge are not an R011 problem.

- **Visual pattern.** The same pattern (labels about 0.33 in left of the edge,
  text at the edge) appears in bibliographies Ester reviewed and annotated
  without ever flagging the labels:
  - Yin, 2nd, 3rd and 4th reviews;
  - Luo, 3rd review;
  - Cibaku, 1st review;
  - Kang Qi, 1st review.
- **She still enforced margins in those reviews.** In the same documents she
  flagged text, tables and equations that crossed the right margin. That
  reviewer silence is supporting context, not a verdict.
- **Not a template default.** Prof. Goodman's current template places labels
  inside the margin. The outdented layout is a widespread LaTeX variant.
- **Structural, not producer-based.** The scope is defined by layout, not by
  PDF producer metadata: the pipeline has no LaTeX provenance, and producers
  vary (pdfTeX, XeTeX, post-processing tools).
- **Narrowness.**
  - It only moves the left measurement past a label that is visibly a
    separate numbering column.
  - The entry text stays fully constrained.
  - A labelled bibliography from another source with the identical layout
    would be treated the same way. That is a visual judgment, which is how
    the rule is applied.

**Philip p174 was never reviewed by Ester.** It is not recorded as an
adjudication. The reviewer candidate was dropped as materially equivalent to
the authority above.

## Effect (seven-document corpus, 316d3ba → this branch)

- Removed: 21 student-visible R011 left-margin findings (Philip p174–181: 8;
  Muyeed p190–202: 13). On every affected line, the label is the only content
  left of 108 pt and the entry text starts at 108.4 pt.
- Raw findings: 1516 → 1495.
- Student-visible findings: 644 → 623.
- No other finding changed. Patrick p88 is still reported, and the Anthony
  landscape findings are unchanged.
- Reviewed-authority replay (scratch ledger): 46 FP / 4 TP / 0 / 0.
