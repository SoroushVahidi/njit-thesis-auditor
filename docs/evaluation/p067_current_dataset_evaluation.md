# P067 Current Dataset Evaluation

- **Date:** 2026-06-08
- **Rule:** P067 — Bio Sketch publication/presentation reverse-chronology check
- **Issue type:** `biosketch_publication_order_suspicious`
- **Generated artifacts (gitignored):** `data/evaluation/generated/p067_evaluation/`

## Purpose

Run the implemented P067 heuristic on the documented five-PDF evaluation set and record only
privacy-safe aggregate results. No publication text, author names, titles, venue names,
DOI/URL strings, or Bio Sketch prose are quoted.

## Results

| File label | BIOGRAPHICAL SKETCH detected? | Publications zone detected? | Comparable entries | P067 findings | Notes |
|---|---:|---:|---:|---:|---|
| Cibaku Elson 1st review | no | no | 0 | 0 | Skip at Bio Sketch heading gate |
| Yin H 2nd review (flattened) | no | no | 0 | 0 | Skip at Bio Sketch heading gate |
| Yin Haotian 2nd review | no | no | 0 | 0 | Skip at Bio Sketch heading gate |
| Yin H 4th review (compressed) | yes | no | 0 | 0 | Bio Sketch page detected on page 6; no qualifying Publications boundary detected |
| Sebastian Fine clean baseline | yes | no | 0 | 0 | Bio Sketch page detected on page 6; no qualifying Publications boundary detected |

## Aggregate Summary

- Bio Sketch heading detected: `2/5`
- Publications zone detected: `0/5`
- Files with `>=3` comparable entries: `0/5`
- Total P067 findings: `0`

## Interpretation

P067 produced no findings on the five-PDF current dataset, but that result is entirely gated
by section detection. Three files were skipped because no machine-readable `BIOGRAPHICAL
SKETCH` heading was detected. Two files reached the Bio Sketch gate but still skipped because
no qualifying Publications/Presentations subsection boundary was detected.

Zero findings do not prove Q027 compliance on this dataset.

## Privacy / Limitations

- Generated raw outputs remain uncommitted under a gitignored path.
- Sebastian Fine clean baseline was extracted locally from the tracked ZIP only.
- No publication text, titles, author names, venue names, DOI strings, URLs, or Bio Sketch
  prose were committed.
