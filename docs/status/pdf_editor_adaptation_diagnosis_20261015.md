# Synthetic PDF editor adaptation: baseline diagnosis

The prior proof of concept at `991e45bb06b8d8168a9da63f4274f3876ac21075`
was tested on three generated PDFs, five substitutions each. Its pinned full
suite completed with exit code 0: 4,775 passed, 6 skipped. The saved comparison
used the same auditor source for each original/transformed pair and identified
findings by severity, rule ID, physical page, issue type, and bounding box
rounded to one point. Across 15 pairs, 37 of 190 source warnings matched,
153 were lost, and 24 were introduced. A fresh five-trial replay confirmed
the failure pattern, although random replacement changed two individual counts.

| Rule | Source warnings | Lost | Introduced | Primary cause |
|---|---:|---:|---:|---|
| P011 | 5 | 0 | 18 | Changed folio text was treated as ordinary bottom-margin text. |
| P013 | 50 | 18 | 0 | Replaced folios stopped qualifying as page-number candidates. |
| P014 | 15 | 15 | 0 | Named front-matter headings became unrecognizable. |
| P017 | 10 | 10 | 0 | List of Figures entries were no longer classified as such. |
| P019 | 10 | 10 | 1 | Roman/Arabic page-number sequence evidence was changed. |
| P022 | 5 | 5 | 0 | A title-page folio was no longer recognized as a page number. |
| P025 | 10 | 10 | 0 | Title-page/degree/institution text cues disappeared. |
| P026 | 0 | 0 | 5 | Changed body text altered context-sensitive font classification. |
| P031 | 10 | 10 | 0 | List-page and column-header recognition disappeared. |
| P038 | 50 | 50 | 0 | Missing-heading checks stopped when front matter was not identified. |
| P040 | 10 | 10 | 0 | List of Figures structure and entries were no longer recognized. |
| P063 | 5 | 5 | 0 | An appendix label ceased to be recognized. |
| P085 | 10 | 10 | 0 | Chapter-number headings ceased to be recognized. |

This table assigns each changed finding to its direct detector trigger, not to
whether the original warning was adjudicated correct. The deliberate synthetic
left-margin violation was the only hand-verified defect and survived.

The baseline preserved all page sizes, line counts, line bounding boxes, and
font names and sizes on the generated sources. Character boxes moved by at
most 0.196 pt. Thus the 153 lost warnings are primarily due to **loss of
meaningful text and document markers**, especially page numbers and headings.
The 24 introduced warnings are likewise mainly downstream effects of lost
folio/body classification. No saved evidence attributes a changed finding to
font substitution, width drift, or a changed page/line extraction structure.
The existing comparison did not prove that all span/operator structure was
unchanged, so the adaptation evaluation will measure that explicitly.

Potential remedies to test are preserving original font and text operators,
using width-aware replacement, and retaining only narrowly defined generic
structural labels and folio sequences. Retaining these markers still discloses
document structure and does not establish confidentiality. Detector rules,
thresholds, and the auditor revision must stay unchanged for comparisons.
