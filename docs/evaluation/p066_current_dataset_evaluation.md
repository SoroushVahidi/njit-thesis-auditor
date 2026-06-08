# P066 — Biographical Sketch Degree Ordering: Current-Dataset Evaluation

**Rule:** P066  
**Module:** `njit_auditor.rules.pdf_biosketch_degree_ordering`  
**Issue type:** `biosketch_degree_order_suspicious`  
**Source Q-rule:** Q025 (degrees most-recent-first)  
**Evaluation date:** 2026-06-08

---

## Dataset

Five PDFs evaluated (four from the EF archive, one clean baseline):

| File | Total pages |
|------|-------------|
| Cibaku Elson 1st Review | 171 |
| Yin H 2nd Review flat   | 186 |
| Yin Haotian 2nd Review  | 185 |
| Yin H 4th Review compressed | 185 |
| Sebastian Fine clean baseline | 224 |

---

## Detection Gate Results

P066 requires:

1. Exactly one BIOGRAPHICAL SKETCH heading found via
   `find_named_frontmatter_headings()`.
2. The heading page contains text blocks with year-bearing lines in the
   education zone (above the Publications boundary).
3. At least `_MIN_YEAR_CANDIDATES = 3` candidate lines.

| File | BIOGRAPHICAL SKETCH detected? | Reason for skip / Result |
|------|-------------------------------|--------------------------|
| Cibaku Elson 1st Review | No | Heading not found in frontmatter scan → skipped |
| Yin H 2nd Review flat   | No | Heading not found in frontmatter scan → skipped |
| Yin Haotian 2nd Review  | No | Heading not found in frontmatter scan → skipped |
| Yin H 4th Review compressed | **Yes** — page 6 | See below |
| Sebastian Fine clean baseline | **Yes** — page 6 | See below |

---

## Files with Detected Bio Sketch

### Yin H 4th Review compressed — page 6

- Publications boundary detected at y ≈ 419.6 pt
- Year candidates (education zone): 4 lines extracted
- Year sequence: non-increasing (most-recent-first — correct order)
- Inversion count: 0
- **Finding emitted: NO**

### Sebastian Fine clean baseline — page 6

- Publications boundary detected at y ≈ 362.0 pt
- Year candidates (education zone): 3 lines extracted (minimum threshold met)
- Year sequence: non-increasing (most-recent-first — correct order)
- Inversion count: 0
- **Finding emitted: NO**

---

## Summary

| Metric | Value |
|--------|-------|
| PDFs evaluated | 5 |
| PDFs with detectable bio sketch | 2 |
| PDFs skipped (heading not detected) | 3 |
| P066 findings emitted | **0** |

---

## Notes

- The three skipped PDFs have a BIOGRAPHICAL SKETCH section, but the heading
  is not recognized by `find_named_frontmatter_headings()`. This is a
  known detection limitation shared with P041 (dedication) and P065
  (dedication centering). The heading text may be embedded in a non-standard
  block, mixed with a page header, or extracted with split spans.
- Both detected PDFs have correctly ordered degree entries (most-recent-first),
  so no Q025 violations were found in this dataset.
- 0/5 findings is a plausible baseline result: both dissertations' bio
  sketches list the most recent degree first.
- No dissertation text, degree names, institution names, or author names
  appear in this document.

Generated: 2026-06-08
