# R046 Ester Left-Column Alignment Follow-Up (2026-09-19)

## Reviewer Ground Truth

Ester's live R046 review selected Anthony and Praneeth examples. Both are
authoritatively adjudicated as false positives for this follow-up. No
Ester-confirmed R046 true positive is available.

The reviewed Anthony case is no longer emitted at this branch's starting main
SHA, after intervening list-entry reconstruction work. The live review record is
kept as historical ground truth, and the final expected behavior remains no R046
report for that reviewed case. The reviewed Praneeth case was still emitted at
branch start and is removed by this fix.

## Reconstructed Rule Semantics

R046/P046 owns List of Tables and List of Figures entry-number left-column
alignment:

- Q068: List of Tables table numbers align vertically in one left column.
- Q078: List of Figures figure numbers align vertically in one left column.

The rule is not a title-text alignment rule, not a continuation-line hanging
indent rule, and not a page-number/right-column rule. R048/P048 remains the
separate right-column page-number alignment rule.

## Root Cause

P046 previously measured every complete row returned by the shared TOC/list
entry parser. For wrapped entries, some title continuation fragments carry
leaders and a page number and therefore look "complete" to shared list parsing.
Those fragments legitimately sit at a hanging-continuation x-position rather
than at the table/figure entry-number x-position. Treating them as entry numbers
created false left-column variance.

The root cause is structural, not document-specific:

- Anthony historical FP: wrapped List of Tables entry reconstruction; current
  main already reconstructs the reviewed case into entry-start x positions only.
- Praneeth FP: List of Figures continuation fragments with leaders/page numbers
  were measured as figure-number rows.

## Selected Policy

P046 now measures only reconstructed entries that begin with a recognizable
entry-number token:

- labeled forms such as `Table 1`, `Table 2.1`, `Figure 1`, or `Figure 2.1`;
- unlabeled dotted/chapter-style forms such as `2.1 Title`;
- unlabeled continuation fragments that begin with a dotted number followed by a
  lowercase continuation phrase are excluded.

The rule then compares the measured entry-number x positions against the median
entry-number x position with the existing 6 pt tolerance. The tolerance is not
expanded; the change is entry-role filtering plus a robust center.

## Seven-Document R046 Audit

| Dissertation | Before | After | Change | Structural reason |
|---|---:|---:|---:|---|
| Youra | 1 | 0 | -1 | hanging continuation fragments excluded |
| Anthony | 0 | 0 | 0 | reviewed historical FP already absent at branch start |
| Muyeed | 2 | 0 | -2 | hanging continuation fragments excluded |
| Philip | 1 | 0 | -1 | hanging continuation fragments excluded |
| Praneeth | 1 | 0 | -1 | reviewed continuation-fragment FP excluded |
| Sebastian | 0 | 0 | 0 | no R046 finding |
| Patrick | 1 | 0 | -1 | hanging continuation fragments excluded |
| **Total** | **6** | **0** | **-6** | all removals structurally explained |

Measured entry-number columns after the fix are stable within each section:
dominant x positions are approximately 108 pt for the reviewed corpus entries
that have enough measured LoT/LoF rows. Sebastian has too few measured entries
for the R046 gate.

## Genuine Misalignment Preservation

No Ester-confirmed R046 true positive is available. Synthetic regressions
preserve genuine detection for both labeled and unlabeled strong left-column
misalignment while confirming no report for correctly aligned entries, wrapped
continuations, varying label widths, fragmented rows, and benign extraction
jitter.

## R048 Diagnostic

P046 and P048 share the same TOC/list page parser, but this fix does not change
that shared parser. P046 now applies entry-number role filtering locally before
left-column measurement. P048 still measures page-number right edges and remains
a separate Ester-adjudicated task. Praneeth's known R048 false-positive context
is therefore diagnostic-only here and still requires the separate R048 follow-up.

## Related Backlog

`LEADER_PLACEMENT_RULE_GAP` remains separate and unimplemented in this task.

## Validation

- `ruff check .`: pass.
- `mypy src`: pass.
- `python -m pytest`: 3569 passed, 3 warnings.
- Targeted R046: 16 passed, 792 deselected.
- Targeted R048 diagnostic: 9 passed, 799 deselected.
- Combined R040/R046/R053/R054 slice: 115 passed, 3454 deselected.
- Seven-document corpus totals: R046 total 0; R040 total 43; R053 total 1;
  R054 total 4.

## Privacy

No private PDF, dissertation title text, or private excerpts are committed.
Regression fixtures use synthetic list-entry text. Corpus diagnostics are
reported only as aggregate counts and geometry classifications.
