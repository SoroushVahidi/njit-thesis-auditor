# R037, Q029, Q074 current authority — 2026-10-06

Base: `817f093bf199d10225ad6eee2317c0b0684dff67`. This record updates
current presentation and authority metadata. Ester's dated Q matrix and the
2026-09-02 authority matrix remain historical evidence.

## R037 authority and presentation

The older R019 workbook note (preserved in
`r019_ester_sheet_authority_20260908.md`) called the Approval Page page iv and
said later pages continue sequentially. The 2026-09 live R037 workbook then
reviewed Anthony and Praneeth physical pages 10 and 11 and established the
Biographical Sketch as the iv anchor with continuous numbering afterward;
Ester's 2026-10-06 email again named Biographical Sketch page iv. This later
anchor supersedes the older Approval Page wording. A multi-page Biographical Sketch,
Acknowledgements, or Table of Contents advances the page sequence, so later
section headings have no fixed numeral by section type. The earlier project
catalog and 2026-09-02 authority matrix listed fixed single-page template
slots; that interpretation is superseded.

| Surface | Before | Current rule and change |
| --- | --- | --- |
| Detector `pdf_roman_section_anchors.py` | Already uses iv anchor and preceding page + 1 for later sections | Correct; untouched |
| Public `/rules` card and catalog metadata | Dedication v, Acknowledgements vi, TOC vii fixed | Sequence after Biographical Sketch iv, with continuation pages counted |
| Canonical report definition | Later sections described as fixed template slots | Describes preceding-page numeral + 1 |
| Grouped finding and suggested fix | Later sections described as template positions | Describes the next Roman numeral after the preceding numbered page |
| Detailed and issue explanations | Fixed slots for later sections | Describes continuation from iv |
| Polished comment | Fixed slot language | Describes continuation from iv |
| Issue label | `wrong_page_number_sequence` | Already accurate; unchanged |

The detector's conservative gates still apply: it needs a detected
Biographical Sketch heading and confident Roman numerals. This wording change
does not alter those gates or any pagination threshold.

## Q matrix supersessions

| Q row | Historical matrix status | Later Ester authority | Current effective implementation |
| --- | --- | --- | --- |
| Q029 | Hanging indent mandatory; mechanical coverage `unimplemented` | 2026-10-05 R045: hanging indent optional | P045 does not warn on its absence; `optional_not_enforced` |
| Q074 | List of Figures descriptions sentence case; mechanical coverage `implemented` | 2026-10-05 R024 and 2026-10-06 confirmation: List of Figures titles use title case | P024 finding maps to public R024E title-case card; `implemented` |

The original matrix questions stay verbatim in `ester_q_matrix.json` and its
XLSX source. `ester_q_current_authority_overlay.json` records the later
effective requirement and provenance. Generated Q coverage keeps the
historical mechanical status and adds the current overlay to these rows. The
consistency audit now reports them as superseded and compares Q074's public
card with the effective title-case question. Q029 is no longer counted as a
current missing mandatory check.

## Known limits

Q030 has established authority: Biographical Sketch publications should
match the References citation format without numbering. Its comparison check
is not implemented. R011's deeper final-line allowance outside References
remains unresolved. Historical annotated-document trace remains partial: the
prior all-round audit found 614 comment objects across 12 PDFs and two DOCX,
with only 52 DOCX comments individually taxonomized and another 143 covered
by a category-level comparison. This is sufficient to settle the current
R037/Q029/Q074 contradictions, but it does not support a claim that every
historical comment has been reconciled.
