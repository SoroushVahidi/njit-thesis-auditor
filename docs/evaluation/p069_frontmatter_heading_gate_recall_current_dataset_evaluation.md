# P069 Front-Matter Heading Gate Recall — Current-Dataset Evaluation

- **Date:** 2026-06-08
- **Baseline commit:** post-P068 main (`c6c1256` era)
- **Auditor scope:** P001–P069 implemented
- **Privacy:** Aggregate gate-reach counts only; no heading line text, names, or body prose quoted.
- **Generated outputs (gitignored):** `data/evaluation/generated/p069_evaluation/`

---

## Purpose

Measure before/after gate-reach on the five-PDF evaluation set for canonical headings
used by P065–P068 consumers, and record whether dependent-rule finding counts changed.

**Before** = strict `find_named_frontmatter_headings()` exact match.  
**After** = P069 `find_frontmatter_headings_for_gates()`.

---

## Five-PDF set

| Label | Accessible |
|---|---|
| Cibaku Elson 1st Review | Yes |
| Yin Haotian 2nd Review | Yes |
| Yin H 2nd Review (flattened) | Yes |
| Yin H 4th Review (compressed) | Yes |
| Sebastian Fine clean baseline | Yes |

---

## Aggregate gate-reach comparison

| Heading | Strict hits (5-PDF) | Gate hits (5-PDF) | Change |
|---|---:|---:|---|
| APPROVAL PAGE | 2 | 2 | 0 |
| BIOGRAPHICAL SKETCH | 2 | 2 | 0 |
| DEDICATION | 0 | 0 | 0 |
| ACKNOWLEDGEMENTS | 0 | **4** | **+4** |

Gate recall improved `ACKNOWLEDGEMENTS` detection via curated `ACKNOWLEDGMENTS` variant
mapping on four files. No additional hits for APPROVAL PAGE, BIOGRAPHICAL SKETCH, or
DEDICATION on this dataset (remaining skips are not variant-map recoverable in v1).

---

## Dependent-rule finding totals (post-P069)

| Rule | Total findings (5-PDF) | P068-era baseline | Change |
|---|---:|---:|---|
| P065 | 0 | 0 | 0 |
| P066 | 0 | 0 | 0 |
| P067 | 0 | 0 | 0 |
| P068 | 3 | 3 | 0 |

P068 findings remain on Yin H 4th Review compressed (1) and Sebastian Fine clean
baseline (2). Cibaku and Yin Haotian 2nd Review still have zero P068 findings because
APPROVAL PAGE headings were not detected on either file (strict and gate).

---

## EF-overlap expectation

EF-overlap gaps for `committee_approval_page`, `references_citations`, and
`list_of_tables_figures_toc` on the two extractable-comment PDFs are **not expected to
change** from P069 alone on this dataset because APPROVAL PAGE and DEDICATION gates
did not gain new hits on those comparison files. A post-P069 EF-overlap refresh remains
recommended only if future datasets expose additional gate matches.

---

## Interpretation

P069 v1 delivers infrastructure and measurable `ACKNOWLEDGEMENTS` variant recall on the
five-PDF set, but does not yet unlock P065–P068 downstream checks on the files that
previously skipped at APPROVAL PAGE / DEDICATION / BIOGRAPHICAL SKETCH gates. Image-only
or non-variant heading text layers remain the limiting factor.

---

## Limitations

- Five-PDF set is small and not representative.
- Gate improvements do not prove compliance.
- No OCR; image-rendered headings remain undetectable.
- LoT/LoF entry parser recall is a separate track.
