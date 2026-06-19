# Problem Numbers And Page Actions

**Date:** 2026-06-19  
**Branch:** `fix/problem-numbers-and-page-actions`  
**Goal:** add stable visible problem numbers, allow original-PDF page actions when a
finding has a known page but no valid highlight, and improve no-highlight location guidance
without reintroducing fake highlights.

## Problem numbers

- Stable problem numbers are assigned in the presentation layer after suppression/filtering,
  not in detector logic.
- Visible findings are numbered in deterministic audit order: `Problem 1`, `Problem 2`,
  `Problem 3`, and so on.
- Suppressed/internal findings, such as non-problem P013 page-number candidates, do not
  receive visible problem numbers.
- The same problem number now appears on:
  - the main results page
  - category pages
  - rule pages
  - issue-type pages
  - JSON report entries (`problem_number`)
  - Markdown report headings (`### Problem N — ...`)
- Each visible finding also carries a stable anchor like `#problem-10`.

## PDF action policy

New policy:

- Real visible bbox highlight available:
  - show `Open highlighted PDF page`
  - route: `/audits/{job_id}/pdf/highlighted?...#page=N`
- No highlight, but page known:
  - show `Open original PDF page`
  - route: `/audits/{job_id}/pdf#page=N`
- No page known:
  - show no PDF action
  - explanation only

This preserves the strict no-fake-highlight rule:

- no fabricated bbox
- no mislabeled original-page link as highlighted
- no fallback that claims visual precision when none exists

## No-highlight guidance

When no exact highlight exists, the detailed explanation and the no-highlight reason now try
to say:

- where to look
- what was detected
- what region to inspect
- why there is no exact highlight

The fallback wording uses only safe metadata already available in the finding, such as:

- page number
- location label when available
- page/section type such as `List of Figures`
- caption context such as figure/table caption area
- heading area or page-number region
- page-margin area

Example style:

> No exact highlight is available, but this finding is on page 5 in the List of Figures
> section. Open the original PDF page and inspect the page-number region.

## Privacy limits

- No raw bbox coordinates are rendered in the student UI.
- No dissertation body paragraphs are quoted.
- No raw LaTeX commands are exposed.
- Nearby-word/context hints remain short and structural; raw caption/body snippets are not
  newly rendered.

## Validation

- `ruff check .`
- `mypy src`
- `python -m pytest -q`

Expected post-change baseline: test count above `1608`, zero failures, one existing warning.
