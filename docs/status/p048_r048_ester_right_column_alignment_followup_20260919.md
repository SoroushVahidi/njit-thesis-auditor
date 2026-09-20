# R048 Ester Right-Column Alignment Follow-Up (2026-09-19)

## Reviewer Ground Truth

Ester's reviewed Praneeth R048 case is a false positive. The page numbers are
consistently aligned in the visual right column. No Ester-confirmed R048 true
positive is available.

## Reconstructed Rule Semantics

R048/P048 owns Q069/Q079: page-number alignment in the List of Tables and List
of Figures. The intended column is the visual right edge of the page-number
tokens. The rule applies to both LoT and LoF, not the general Table of Contents,
entry-number left alignment, leader placement, or title alignment.

Different-width Arabic or valid Roman page numbers may have different left
edges while sharing the same right edge. Wrapped entries remain associated with
their semantic page-number token through the shared list parser.

## Root Cause

The current detector already used the correct right-edge anchor and retained
the existing 10 pt tolerance. The Praneeth false positive came from P048
accepting the shared parser's page-number signal without validating Roman
numeral form. An invalid `LC` fragment inside a wrapped figure title was
therefore treated as a page-number token at an x-position left of the real
page-number column.

## Selected Policy

P048 now accepts Roman page-number tokens only when they match a canonical
Roman numeral form. Arabic numbers remain unchanged. Invalid Roman-looking
title fragments are not P048 page-number geometry and do not make an entry
complete. The shared parser is unchanged. The P048 right-edge anchor and 10 pt
tolerance are unchanged.

This is structural parser validation, with no dissertation-, page-, title-, or
author-specific exception.

## Seven-Document Audit

| Dissertation | Before | After | Change |
|---|---:|---:|---:|
| Youra | 1 | 1 | 0 |
| Anthony | 0 | 0 | 0 |
| Muyeed | 2 | 2 | 0 |
| Philip | 1 | 1 | 0 |
| Praneeth | 1 | 0 | -1 |
| Sebastian | 0 | 0 | 0 |
| Patrick | 1 | 1 | 0 |
| **Total** | **6** | **5** | **-1** |

The only changed finding is the reviewed Praneeth false positive. The five
remaining findings are strong right-edge outlier candidates, with deviations
well above the unchanged 10 pt tolerance; they were not adjudicated by Ester in
this task and are not suppressed broadly.

## R046 Boundary

R046 remains unchanged as an implementation and policy. Its seven-document
corpus total remains 0. R040 remains 43, R053 remains 1, and R054 remains 4.

## Validation and Privacy

- No Ester-confirmed R048 true positive is available.
- Synthetic coverage includes varying-width Arabic and Roman page numbers,
  strong right-edge misalignment, benign variation, leader separation, wrapped
  entries, and invalid Roman title fragments.
- Private PDFs and dissertation text are not committed.
- `LEADER_PLACEMENT_RULE_GAP` remains separate and unimplemented.
