# R054/P054 Ester Leader-Dot Terminal-Period Follow-Up

**Updated:** 2026-09-18
**Branch:** `fix/r054-leader-dot-terminal-period-followup-20260918`
**Scope:** R054/P054 Table of Contents terminal-period detection only. R040 was
inspected diagnostically but not changed.

R054 is the reviewer-facing rule identifier. P054 is the internal detector in
`src/njit_auditor/rules/pdf_toc_terminal_period.py`.

## Reviewer Ground Truth

Ester confirmed that the Praneeth Table of Contents finding on physical PDF
page 11, printed page viii, is a false positive. The apparent terminal periods
are leader dots between the TOC title and the page number, not punctuation
belonging to the semantic TOC title.

Required R054 behavior:

- TOC entries followed only by leader dots and a page number must not be
  reported;
- a genuine period that belongs to the semantic title text must still be
  reported when the R054 policy forbids terminal periods;
- the reviewed Praneeth case must be non-reported after the fix.

No private TOC titles or thesis excerpts are included in this record.

## Root Cause

P054 already stripped page-number tokens and legacy ASCII/hyphen leader runs
before checking for a trailing period. The reviewed false positive used
extracted leader fragments that included Unicode ellipsis-style dot characters
mixed with ordinary periods. Because the legacy stripper did not recognize
those Unicode visual leader fragments, the final dot in the leader sequence was
interpreted as semantic title-ending punctuation.

One Praneeth TOC row also extracted as repeated trailing leader fragments. The
updated stripper removes repeated visual leader fragments until only semantic
title text remains.

The shared TOC/list row reconstruction correctly identified TOC entries and
page-number tokens. The defect was local to P054 title extraction before the
terminal-period check.

## Implemented Policy

The fix is scoped to P054. P053 was not modified and R040 was not modified.

P054 now strips trailing visual leaders before applying the terminal-period
check:

1. Preserve existing legacy behavior for spaced ASCII dot leaders and
   hyphen/underscore leaders.
2. Strip separated dot-leader runs made from ASCII periods, Unicode ellipses,
   or middle-dot characters when the run has visible leader weight of at least
   two dots.
3. Strip attached multi-dot leader fragments of the same dot-like characters.
4. Repeat stripping when PDF extraction leaves multiple trailing leader
   fragments on the same entry.
5. Preserve an isolated title-ending period before separated Unicode leaders,
   so genuine semantic terminal periods still report.

The detector does not use student names, page numbers, private title strings,
or dissertation-specific exceptions.

## Seven-Document Corpus Result

The seven private evaluation dissertations were rerun for R054. Elbert remains
excluded.

| Document | Before | After | Delta |
|---|---:|---:|---:|
| Youra | 1 | 1 | 0 |
| Anthony | 0 | 0 | 0 |
| Muyeed | 1 | 1 | 0 |
| Philip | 2 | 2 | 0 |
| Praneeth | 6 | 0 | -6 |
| Sebastian | 0 | 0 | 0 |
| Patrick | 0 | 0 | 0 |
| **Total** | **10** | **4** | **-6** |

All removed findings are Praneeth TOC leader-dot artifacts. The reviewed
physical-page-11 false positive is non-reported after the fix. No findings were
added.

## R053 Regression

The nearest analogous rule, R053/P053, was rerun after the R054 fix. The
seven-document R053 corpus result remains unchanged: Youra 0, Anthony 0,
Muyeed 1, Philip 0, Praneeth 0, Sebastian 0, Patrick 0; total 1.

## R040 Diagnostic

R040/P040 output did not change. Existing Ester feedback for R040 remains a
separate pending follow-up: Anthony and Praneeth contain false positives, while
Sebastian involves a distinct reviewer-noted leader-placement issue. This R054
branch does not claim to resolve R040.

## Regression Coverage

Privacy-safe synthetic tests cover:

- ASCII dot leaders;
- Unicode ellipsis leaders;
- middle-dot leaders;
- a genuine title-ending period before separated Unicode leaders;
- internal abbreviation periods;
- detached leader fragments in a separate span;
- attached leader fragments on the final title token;
- wrapped TOC titles where leaders occur on the final row.

## Validation

- `ruff check .`: pass.
- `mypy src`: pass.
- `python -m pytest`: 3558 passed, 3 warnings.
- Targeted P054 tests: 20 passed, 777 deselected.
- Targeted P053 tests: 19 passed, 778 deselected.
- P040/P053/P054 diagnostic slice: 52 passed, 745 deselected.
- Seven-document R054 corpus audit: pass, total findings 10 to 4 with only
  Praneeth leader-dot artifacts removed.
- Seven-document R053 corpus audit: pass, unchanged at total 1.
- R040 diagnostic: output unchanged.

No private PDFs, private TOC titles, or verbatim thesis text are committed.
