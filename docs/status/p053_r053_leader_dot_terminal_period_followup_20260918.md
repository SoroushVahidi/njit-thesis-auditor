# R053/P053 Ester Leader-Dot Terminal-Period Follow-Up

**Updated:** 2026-09-18
**Branch:** `fix/r053-leader-dot-terminal-period-followup-20260918`
**Scope:** R053/P053 List of Tables terminal-period detection only. R054 and
R040 were inspected as diagnostics because they share list-entry parsing
concepts, but their rule implementations were not changed here.

R053 is the reviewer-facing rule identifier. P053 is the internal detector in
`src/njit_auditor/rules/pdf_lot_terminal_period.py`.

## Reviewer Ground Truth

Ester confirmed that the Praneeth List of Tables finding on physical PDF page
14, printed page xi, is a false positive. The apparent terminal periods are
leader dots between the table title and the page number, not punctuation
belonging to the semantic table title.

Required R053 behavior:

- titles followed only by leader dots and a page number must not be reported;
- a genuine period that belongs to the semantic title text must still be
  reported when the R053 policy forbids terminal periods;
- the reviewed Praneeth case must be non-reported after the fix.

No private table titles or thesis excerpts are included in this record.

## Root Cause

P053 already stripped page-number tokens and legacy ASCII dot leaders before
checking for a trailing period. The reviewed false positive used extracted
leader fragments that included Unicode ellipsis-style dot characters mixed with
ordinary periods. Because the legacy stripper only recognized ASCII period
leader runs, those visual leaders remained attached to the candidate title text.
The final ASCII dot in the leader run was then interpreted as a semantic
title-ending period.

The shared TOC/list row reconstruction correctly identified List of Tables
entries and page-number tokens; the defect was in P053's local terminal-title
extraction step.

## Implemented Policy

The fix is scoped to P053.

P053 now strips trailing visual dot leaders before applying the terminal-period
check:

1. Preserve the existing legacy behavior for spaced ASCII leader runs.
2. Strip separated dot-leader runs made from ASCII periods, Unicode ellipses,
   or middle-dot characters when the run has visible leader weight of at least
   two dots.
3. Strip attached multi-dot leader fragments of the same dot-like characters.
4. Preserve an isolated title-ending period before whitespace and separated
   leaders, so genuine semantic terminal periods still report.

The detector does not use student names, page numbers, private title strings,
or dissertation-specific exceptions.

## Seven-Document Corpus Result

The seven private evaluation dissertations were rerun for R053. Elbert remains
excluded.

| Document | Before | After | Delta |
|---|---:|---:|---:|
| Youra | 0 | 0 | 0 |
| Anthony | 0 | 0 | 0 |
| Muyeed | 1 | 1 | 0 |
| Philip | 0 | 0 | 0 |
| Praneeth | 2 | 0 | -2 |
| Sebastian | 0 | 0 | 0 |
| Patrick | 0 | 0 | 0 |
| **Total** | **3** | **1** | **-2** |

Both removed Praneeth findings were leader-dot artifacts on the List of Tables
page. The remaining Muyeed R053 finding is not part of this Ester review and
was not suppressed by the leader-dot fix.

## Cross-Rule Diagnostics

R054/P054 appears to have the same low-level leader-dot segmentation issue for
the known Praneeth TOC false positive. A non-mutating diagnostic simulation of
the P053-style stripper reduced Praneeth P054 findings from 6 to 1. R054 was
not changed in this branch and should be handled as the next focused rule if
the false positive remains unresolved.

R040/P040 is only partially related. The Anthony and Sebastian diagnostic
outputs did not change under the P053-style stripper. Praneeth showed mixed
additions/removals in simulation, so R040 needs its own rule-specific analysis;
it was not changed here.

## Regression Coverage

Privacy-safe synthetic tests cover:

- leader dots only after a semantic title;
- a genuine title-ending period before separated leaders;
- internal abbreviation periods;
- detached leader fragments in a separate span;
- attached leader fragments on the final title token;
- wrapped List of Tables titles where leaders occur on the final row.

## Validation

- `ruff check .`: pass.
- `mypy src`: pass.
- `python -m pytest`: 3550 passed, 3 warnings.
- Targeted P053 tests: 19 passed, 770 deselected.
- P040/P053/P054 diagnostic slice: 44 passed, 745 deselected.
- Seven-document R053 corpus audit: pass, total findings 3 to 1 with only the
  two Praneeth leader-dot artifacts removed.

No private PDFs, private table titles, or verbatim thesis text are committed.
