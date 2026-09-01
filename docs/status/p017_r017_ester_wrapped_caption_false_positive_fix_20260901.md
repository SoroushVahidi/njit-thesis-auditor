# R017/P017 2026-09-01: Wrapped Caption and Inline Reference False-Positive Fix

**Date:** 2026-09-01
**Scope:** R017 human feedback for internal rule P017 only.
**Baseline:** `main` at `ff5a78f23cef1de2b693448d920d6161e9d8317f`.

## Human Feedback

Ester Flaim reviewed R017 and marked the three selected body figure-caption
terminal-punctuation findings as false positives:

| Document | Physical page | Printed page | Finding |
|---|---:|---:|---|
| Anthony | 47 | 33 | Figure caption missing terminal punctuation |
| Praneeth | 28 | 9 | Figure caption missing terminal punctuation |
| Sebastian | 19 | 4 | Figure caption missing terminal punctuation |

Ester's common explanation was that the auditor was reading only the first
line of a wrapped figure description, not the complete caption.

## Root Cause

Confirmed for Ester's three reviewed false positives. `detect_caption_lines()`
in `src/njit_auditor/rules/pdf_captions.py` matched only the extracted line
beginning with `Figure`/`Fig.`/`Table` and stored that first extracted line as
`CaptionLine.caption_body`. The continuation lines were present in the PDF
extraction model, usually in the same text block, but were discarded before
`check_pdf_captions()` ran `_terminal_punctuation()`.

The bug was in caption grouping, not PDF extraction or evidence rendering. The
historical R017 evidence also showed only the first highlighted text line because
the finding bbox was the first-line caption anchor. Historical Ester artifacts
were not regenerated.

Finalization also exposed a second R017 false-positive mode during engineering
sanity checks, not from direct Ester review:

- Praneeth physical page 87: inline body prose beginning with a subfigure
  reference was parsed as a caption start.
- Praneeth physical page 95: inline body prose beginning with a subfigure
  reference was parsed as a caption start and continued on the next page.
- Praneeth physical page 102: the remaining `Figure 3.6` item is a genuine
  figure caption whose complete logical caption still lacks terminal punctuation.

The secondary root cause was caption-start parsing: the number pattern allowed
Roman-numeral letters inside the same segment as Arabic digits, so inline
subfigure references such as `3.2d` and `3.5c` were accepted as caption numbers.

## Fix

P017 now reconstructs a conservative logical caption body from same-text-block
continuation lines before applying terminal-punctuation and case checks.
Grouping stops at page numbers, a new caption start, source/note lines, left
edge shifts beyond tolerance, or vertical pitch larger than the tight caption
continuation threshold. The first-line bbox remains the anchor for highlighting
and layout consumers.

The shared caption helper affects both figure and table caption objects, but the
R017 rule scope is unchanged:

- Figure captions: terminal punctuation is checked against the complete logical
  caption body.
- Table captions/titles: existing P017 table checks continue to run against the
  caption body; no new table issue type or rule scope was added.

Future P017 findings also carry `caption_end_preview` so ending punctuation
context is available in finding details without changing historical packages.

P017 now also rejects caption-number candidates with a mixed Arabic/letter
segment, such as `4a` or `3.2d`. This is a general caption-number syntax guard,
not a document, page, figure-number, or vocabulary exception. Normal numeric
caption numbers such as `3.6` and Roman-numbered segments remain eligible.

## Seven-Document Regression Counts

Elbert remains excluded. Counts are direct P017 detector counts on the seven
human-validation PDFs.

| Document | Before | After wrapped-caption fix | Final |
|---|---:|---:|---:|
| Youra | 0 | 0 | 0 |
| Anthony | 3 | 0 | 0 |
| Muyeed | 0 | 0 | 0 |
| Philip | 0 | 0 | 0 |
| Praneeth | 18 | 3 | 1 |
| Sebastian | 1 | 0 | 0 |
| Patrick | 0 | 0 | 0 |

## Findings Changed

Removed because the reconstructed complete caption body ends with terminal
punctuation:

- Anthony: pages 47, 53, 79.
- Praneeth: pages 28, 29, 33, 35, 41, 46, 48, 51, 61, 64, 67, 72, 86, and one
  of two page-95 captions.
- Sebastian: page 19.

Removed by the secondary caption-number syntax guard:

- Praneeth: page 87 inline subfigure reference.
- Praneeth: page 95 inline subfigure reference.

Retained because the reconstructed logical text is a genuine figure caption and
still does not end with a terminal punctuation mark:

- Praneeth: page 102.

No unrelated new P017 findings were introduced.

## Tests

Added focused synthetic P017 coverage in `tests/test_pdf_rules.py` for:

- wrapped figure caption whose final logical line has punctuation.
- wrapped figure caption whose final logical line lacks punctuation.
- grouping not consuming following body text from a separate text block.
- Anthony-like wrapped caption plus source-note stop.
- Praneeth-like wrapped caption plus source-note stop.
- Sebastian-like wrapped caption plus source-note stop.
- wrapped table-caption shared-helper behavior without expanding P017 scope.
- regular numeric figure caption remains eligible and warns when punctuation is
  absent.
- subfigure references with mixed Arabic/letter number segments are not treated
  as figure captions when they are the first visible words on a line.
- subfigure references embedded in ordinary body-paragraph flow are not treated
  as figure captions.
- Praneeth page-87-like and page-95-like synthetic inline-reference structures
  are rejected.
- Praneeth page-102-like regular caption structure remains a genuine P017
  missing-punctuation finding.
- mixed-segment table references are rejected by the shared caption parser.

Existing tests already covered single-line caption with punctuation and
single-line caption without punctuation.

Validation run:

- Combined focused P017/caption suites: 89 passed, 661 deselected.
- Seven-document full audit-path P017 counts matched the final table above.
- `ruff check .`: passed.
- `mypy src`: passed.
- `python -m pytest`: 3192 passed, 3 warnings.

## Remaining Uncertainty

The grouping is intentionally conservative and same-block based. It fixes the
reviewed false positives and same-pattern wrapped captions in the current
validation PDFs without trying to solve every possible malformed PDF extraction
case. The remaining Praneeth findings should still be reviewed as real P017
outputs rather than suppressed by this fix.
