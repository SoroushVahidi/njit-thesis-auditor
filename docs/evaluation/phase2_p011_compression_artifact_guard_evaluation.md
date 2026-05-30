# Phase 2 P011 Compression Artifact Guard Evaluation

Date: 2026-05-29  
Scope: Private/local re-run of the PDF auditor after adding a compression artifact guard to P011.

## Motivation

P011 margin detection was previously refined (PR #36) to reduce findings from ~2000 to 150 on the
compressed Yin H 4th PDF and from ~1483 to 33 on the normal Yin Haotian 2nd PDF. After that
refinement, the compressed PDF still produced significantly more P011 warnings than normal PDFs
(150 vs 21–33). Investigation showed the pattern: nearly every body text line on most pages of
the compressed PDF barely crossed the right margin by ~3–7pt, producing a high-count low-overflow
group per page. Normal PDFs do not exhibit this pattern.

## Root Cause

PDF compression can alter text-block bounding boxes, creating a systematic coordinate shift where
body text is reported as extending ~3–7pt past the right margin boundary. This affects many lines
uniformly on affected pages. The resulting P011 findings have:

- `affected_line_count` ≥ 5 (often 10–20)
- `worst_overflow_pt` < 8pt (all lines barely crossing the margin)

Real margin violations on normal PDFs have isolated lines (count usually 1–3) or large overflows
when count is high. Neither pattern collides with the artifact signature.

## Artifact Guard Logic

Added in `src/njit_auditor/rules/pdf_margins.py`:

```
ARTIFACT_GUARD_MIN_COUNT = 5
ARTIFACT_GUARD_MAX_OVERFLOW_PT = 8.0
```

Per page/side group: if `count >= 5 AND worst_overflow < 8pt` → suppress (no finding emitted).

Also added `confidence` field to findings:
- `high`: worst_overflow ≥ 12pt, or count ≥ 5 with worst ≥ 8pt
- `medium`: worst_overflow ≥ 5pt, or count ≥ 2
- `low`: single-line with worst_overflow 3–5pt

## P011 Count Before / After

| File | Before | After | Change |
|------|-------:|------:|-------:|
| Yin H 4th compressed (137 pages) | 150 | 70 | −53% |
| Cibaku Elson (normal) | 21 | 21 | 0% |
| Yin Haotian 2nd (normal) | 33 | 33 | 0% |
| Yin H 2nd flattened (normal) | 33 | 33 | 0% |

## Confidence Distribution (After)

| File | low | medium | high |
|------|----:|-------:|-----:|
| Yin H 4th compressed | 4 | 13 | 53 |
| Cibaku Elson | 2 | 10 | 9 |
| Yin Haotian 2nd | 6 | 14 | 13 |
| Yin H 2nd flattened | 6 | 14 | 13 |

## Interpretation

- The artifact guard removes 80 of 150 findings on the compressed PDF — precisely the groups
  with the systematic coordinate-shift signature.
- The remaining 70 compressed-PDF findings include real separator-line overflows (36–70pt),
  genuinely wide text blocks, and small-count groups.
- All normal PDF counts are fully preserved; the guard threshold (count ≥ 5, worst < 8pt) does
  not match any group in the tested normal PDFs.

## Limitations

- The guard is a heuristic. A compressed PDF with many narrowly-placed real margin violations
  could theoretically be suppressed if they all fall below 8pt and number ≥ 5.
- The threshold values (5, 8pt) were tuned to the available test set; other PDFs may require
  manual review.
- All remaining P011 findings still require human review for final compliance decisions.
