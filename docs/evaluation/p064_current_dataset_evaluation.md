# P064 — References/Citations Structural Check: Current-Dataset Evaluation

## 1. Purpose and auditor version

- **Date:** 2026-06-08
- **Baseline commit:** `dd0f022` (post PR #228 — P064 implementation merged)
- **Validation:** ruff passed, mypy passed, **910 pytest** passed
- **Auditor scope:** P001–P064 implemented (PDF layout audit **P011–P064**; TeX audit P001–P010 not run here)
- **Module:** `src/njit_auditor/rules/pdf_references_citations_structural.py`
- **Generated artifacts (gitignored):** `data/evaluation/generated/p064_evaluation/`

Reporting is **aggregate-only**: file labels, rule IDs, page counts, entry counts, and skip reasons
only. No dissertation body text, reference entry text, author names, citation content, DOI strings,
URL strings, EF comment text, or any other dissertation content is quoted.

---

## 2. Dataset inventory

| File label | Source | Pages | Availability |
|---|---|---:|---|
| Cibaku Elson 1st Review | `data/raw/ester/250218 Cibaku Elson First Review.pdf` | 99 | tracked — accessible |
| Yin H 2nd Review (flattened) | `data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf` | 108 | tracked — accessible |
| Yin Haotian 2nd Review | `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf` | 108 | tracked — accessible |
| Yin H 4th Review (compressed) | `data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf` | 137 | tracked — accessible |
| Sebastian Fine clean baseline | archive-extracted from tracked ZIP | 29 | archive-extracted — accessible |

All five documented evaluation PDFs were accessible. Sebastian Fine clean baseline
(`Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf`) was extracted locally
from `data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`
to `data/evaluation/generated/p064_evaluation/` (gitignored; not committed).

---

## 3. P064 issue types

| Issue type (code) | Condition |
|---|---|
| `references_section_heading_not_detected` | No REFERENCES / BIBLIOGRAPHY / WORKS CITED / LITERATURE CITED heading found in a document with ≥5 body pages |
| `references_entry_indentation_inconsistent` | Mixed hanging-indent pattern among multi-line entry candidates (≥5 entries AND ≥3 multi-line entries required) |
| `references_entry_spacing_inconsistent` | Highly irregular inter-entry vertical gaps (≥20% outlier gaps AND outlier range exceeds threshold; ≥5 entries required) |

---

## 4. P064 findings by file

| File label | P064 total | `heading_not_detected` | `indentation_inconsistent` | `spacing_inconsistent` | Gate/skip outcome |
|---|---:|---:|---:|---:|---|
| Cibaku Elson 1st Review | **0** | 0 | 0 | 0 | Skip — high x-variance (59.7 pt > 50 pt threshold) |
| Yin H 2nd Review (flattened) | **0** | 0 | 0 | 0 | Skip — no body region detected |
| Yin Haotian 2nd Review | **0** | 0 | 0 | 0 | Skip — no body region detected |
| Yin H 4th Review (compressed) | **0** | 0 | 0 | 0 | Reached checks; 52 entries / 5 section pages — consistent formatting |
| Sebastian Fine clean baseline | **0** | 0 | 0 | 0 | Reached checks; 24 entries / 3 section pages — consistent formatting |
| **Total** | **0** | **0** | **0** | **0** | |

---

## 5. Per-file skip and gate details

### Cibaku Elson 1st Review

- **Body start:** Detected.
- **References heading:** Found (page 91).
- **Skip condition:** References section line x-coordinate standard deviation = 59.7 pt,
  exceeding the conservative high-x-variance threshold of 50 pt. This indicates noisy
  geometry in the extracted references section — likely caused by EF annotation markup
  artifacts (78 extractable EF annotations in this file) that add additional text blocks
  alongside reference entry text, widening the apparent x-coordinate spread.
- **Outcome:** Conservative skip applied; checks B and C not run.

### Yin H 2nd Review (flattened)

- **Body start:** Not detected. The text layer in this PDF has collapsed inter-word spacing
  (e.g., "CHAPTER1" without space), causing the body-start pattern (`CHAPTER\s+\d`)
  not to match. This is a known limitation of the flattened/compressed PDF text layer
  for this file.
- **References heading:** "BIBLIOGRAPHY" present at page 103, but not reachable from
  `_find_references_heading` because body_start is None.
- **Outcome:** Entire rule skipped; no body region detected gate not met.

### Yin Haotian 2nd Review

- **Body start:** Not detected. Identical text-layer behavior to Yin H 2nd Review (flattened):
  "CHAPTER1" / "CHAPTER2" collapsed without space. Both files share the same source
  dissertation and exhibit the same extraction artifact.
- **References heading:** "BIBLIOGRAPHY" present at page 103 (same layout as Yin H 2nd).
- **Outcome:** Entire rule skipped; no body region detected gate not met.

### Yin H 4th Review (compressed)

- **Body start:** Detected.
- **References heading:** Detected (page 133).
- **Section pages:** 5 pages from heading page to document end.
- **Entry candidates:** 52.
- **Text-layer quality:** Adequate (x-variance within threshold; not multicolumn).
- **Check B (indentation):** Gate met (≥5 entries, ≥3 multi-line candidates). No inconsistent
  hanging-indent pattern detected — formatting appears internally consistent.
- **Check C (spacing):** Gate met (≥5 entries). No highly irregular inter-entry gap outliers
  above the threshold detected — spacing appears internally consistent.
- **P064 findings:** 0.

### Sebastian Fine clean baseline

- **Body start:** Detected.
- **References heading:** Detected (page 27).
- **Section pages:** 3 pages from heading page to document end.
- **Entry candidates:** 24.
- **Text-layer quality:** Adequate.
- **Check B (indentation):** Gate met. No inconsistent hanging-indent pattern detected.
- **Check C (spacing):** Gate met. No highly irregular inter-entry gap outliers detected.
- **P064 findings:** 0.

---

## 6. Total P064 findings

| Metric | Value |
|---|---|
| P064 total across all five files | **0** |
| `references_section_heading_not_detected` | 0 |
| `references_entry_indentation_inconsistent` | 0 |
| `references_entry_spacing_inconsistent` | 0 |
| Files reaching entry-level checks (B and C) | 2 of 5 |
| Files skipped before entry-level checks | 3 of 5 |

---

## 7. Interpretation

### Whether P064 fired

P064 produced **zero findings** on all five evaluation PDFs. This does **not prove** references
section compliance — three of five files were skipped before entry-level checks could run.

### Skip and gate conditions summary

- **Cibaku Elson:** High x-variance skip. The references section's geometric data is too noisy
  for reliable indentation/spacing analysis. The most likely cause is EF annotation overlay
  artifacts affecting the extracted text block positions.

- **Yin H 2nd Review (flattened) and Yin Haotian 2nd Review:** Body-region detection failure.
  These two files share the same dissertation source and both exhibit collapsed inter-word
  spacing in their text layers ("CHAPTER1" without space). This is a PDF text-extraction
  limitation for this subset of the dataset; it is not a formatting defect in the dissertation.
  The BIBLIOGRAPHY heading is present at page 103 in both but is not reachable because the
  body-start gate is not met.

- **Yin H 4th Review (compressed) and Sebastian Fine:** Both files reached the full entry-level
  checks. No indentation inconsistency or spacing irregularity exceeding the conservative
  thresholds was detected. This indicates the references sections in these two files have
  internally consistent formatting by P064's heuristic measures.

### Zero findings: absence vs. detection

Zero P064 findings on a file mean either:
1. The references section formatting is consistent and no structural issues exist
   (Check B/C passed), **or**
2. A skip condition was triggered before checks could run (Cibaku, Yin H 2nd, Yin Haotian).

In case 2, P064 makes no claim about the formatting quality of those references sections.
The heading skip (Cibaku) and body-start skip (Yin H 2nd, Yin Haotian) are conservative
and intentional.

### Likely text-layer and extraction limitations

- **EF annotation artifacts:** EF PDF annotations can inject extra text blocks into the
  extracted layout that are not part of the original dissertation text. On Cibaku, this
  appears to widen the x-variance of the references section beyond the skip threshold.
- **Collapsed inter-word spacing:** Yin H 2nd (flattened) and Yin Haotian 2nd have
  compressed text-layer rendering without inter-word spaces. This affects all heading
  detection in P064 (and in other rules sharing the same body-start detection).
- **No OCR:** Image-only or unembedded-font pages would yield zero text blocks. P064
  silently skips any such pages within the references section.

---

## 8. Relation to EF overlap

P064 targets the **references_citations** zero-coverage gap identified in PR #226
(`docs/evaluation/ef_overlap_after_p063_evaluation.md`). In that analysis,
`references_citations` had 0% coverage because no rule at that time addressed
references section structure.

P064 adds structural coverage for:
- Heading presence (Check A)
- Entry indentation consistency (Check B)
- Entry spacing consistency (Check C)

Whether current-dataset P064 findings correspond to EF annotations in the
`references_citations` category depends on whether the EF reviewer annotated structural
issues (heading absence, inconsistent indent/spacing) vs. citation-style content
(APA/IEEE compliance, missing fields). P064 does not check citation content; any EF
annotations addressing citation format will remain outside P064's scope. For files
where skip conditions apply (3 of 5), no comparison to EF annotations is possible
from this run.

---

## 9. Generated output and gitignore

Generated evaluation artifacts:

```
data/evaluation/generated/p064_evaluation/
  cibaku_elson.json
  yin_h_2nd_flat.json
  yin_haotian_2nd.json
  yin_h_4th_comp.json
  sebastian_fine.json
  sebastian_fine_clean_baseline.pdf   ← extracted from ZIP, not committed
```

All contents of `data/evaluation/generated/` are covered by `.gitignore`:

```
data/evaluation/generated/
```

None of these files are committed. The extracted Sebastian Fine PDF will not be committed.

---

## 10. Privacy model

- All counts reported are aggregate-only: rule IDs, page counts, entry counts, skip reasons,
  x-variance values, and boolean outcomes.
- No dissertation body text, reference entry text, citation text, author names, committee
  names, article or book titles, DOI strings, URL strings, EF annotation text, or any
  other dissertation content is quoted.
- The extracted Sebastian Fine PDF is stored only in the gitignored generated path and
  is not committed.
- Findings contain only geometric/structural metadata as specified in the rule module.

---

## 11. Limitations and caveats

- P064 is a heuristic structural check; it does not verify citation style compliance
  (APA, IEEE, ACM, MLA, Chicago), completeness (all in-text citations matched), or
  reference entry content accuracy.
- On 3 of 5 evaluation PDFs, skip conditions prevented entry-level checks from running.
  These skips are conservative and appropriate given the text-layer limitations of this
  dataset subset.
- The five-PDF evaluation dataset is small and may not be representative of all
  dissertation formatting patterns at NJIT.
- Text-layer quality varies: EF annotation overlays (Cibaku), collapsed inter-word
  spacing (Yin H 2nd, Yin Haotian), and compressed/flattened rendering affect
  detection reliability across the dataset.
- Zero findings on Yin H 4th and Sebastian Fine reflect passing P064's conservative
  geometric thresholds, not a formal compliance determination.

---

## 12. Related docs

- P064 synthetic validation: `docs/evaluation/p064_references_citations_structural_synthetic_validation.md`
- P064 scope and design: `docs/planning/p064_references_citations_structural_check_scope_and_design.md`
- EF overlap analysis: `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- P063-era five-PDF snapshot: `docs/evaluation/current_auditor_after_p063_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
- Project status: `docs/status/current_project_state_and_next_steps.md`
