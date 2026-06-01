# P034 Current Dataset Evaluation

- **Date:** 2026-06-01
- **Baseline commit:** `5480a41` (post–PR #65 P034 implementation)
- **Auditor scope:** P001–P034 (P034 only reported here)
- **Generated artifacts (gitignored):** `data/evaluation/generated/p034_evaluation/`

## 1. Purpose and scope

Evaluate the conservative P034 Copyright Page metadata/layout rule on the repository’s
documented evaluation PDF set (`data/processed/evaluation_data_manifest.json`).

Reporting is **aggregate-only**. No author names, dissertation title text, committee names,
or body text is quoted. Author hashes and extraction metadata appear only in gitignored
`p034_summary.json`.

Evaluated inputs match the five-PDF full-evaluation set used for P030–P033, excluding the
rule-matrix XLSX and archive-only materials not verified locally.

## 2. Results summary

| File label | Availability | Copyright page detected | Year comparison | Author comparison | P034 count | Pages | Issue types | Notes |
|---|---|:---:|:---:|:---:|---:|---|---|---|
| Cibaku Elson 1st review | tracked | yes (p. 4) | no | no | 0 | — | — | ©/year line not confidently parsed; title `by` author extracted |
| Yin H 2nd review (flattened) | tracked | yes (p. 4) | no | no | 0 | — | — | Same skip pattern as Cibaku |
| Yin Haotian 2nd review | tracked | yes (p. 4) | no | no | 0 | — | — | Same skip pattern as Cibaku |
| Yin H 4th review (compressed) | tracked | yes (p. 4) | **yes** | **yes** | **1** | 4 | `copyright_author_mismatch` | Years match (2026); author hashes differ |
| Sebastian Fine clean baseline | archive-extracted | yes (p. 4) | no | **yes** | **1** | 4 | `copyright_author_mismatch` | Title graduation year not extracted; © year 2025 |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

**Totals (5 evaluated PDFs):**

| Metric | Count |
|---|---:|
| Copyright page confidently detected | 5 / 5 |
| Year comparison ran | 1 / 5 |
| Author-hash comparison ran | 2 / 5 |
| **P034 findings** | **2** (both `copyright_author_mismatch` on page 4) |
| Top-margin header findings (Q009) | 0 |

## 3. Comparison outcomes by category

| Outcome | Files |
|---|---:|
| No copyright page detected | 0 |
| Copyright detected; year/author comparison skipped | 3 |
| Comparison ran; no mismatch | 0 |
| Comparison ran; mismatch found | 2 |

On all five PDFs, the Copyright Page was identified on **page 4** via ©/copyright text in the
early front matter (no separate `COPYRIGHT PAGE` named heading observed in extraction metadata).

## 4. Interpretation

**P034 is partially active on this dataset**, not uniformly silent.

- **Detection recall appears high** for these NJIT-style PDFs: every evaluated file had a
  confidently detected Copyright Page on page 4.
- **Year comparison (Q010) ran on only one file** (Yin H 4th). On that file, extracted years
  matched and no year finding was emitted. The other four files skipped year comparison because
  the Title Page graduation month/year line or the ©-line year was not confidently extracted
  (or both).
- **Author comparison (Q011) ran on two files** and produced **`copyright_author_mismatch`**
  warnings on both. These are structurally plausible given different normalized author hashes
  between the Title Page `by` line and the © notice line; manual review is still required to
  confirm whether the underlying names truly differ or extraction/normalization is wrong.
- **No top-margin header findings (Q009)** on any file — either layouts are clean in the top
  15% band or header-like text was classified as non-actionable (e.g., page-number candidates).

**Zero findings on three files does not prove Q009–Q011 compliance** — comparisons were largely
skipped because metadata extraction was incomplete, not because mismatches were ruled out.

**Usefulness vs noise:** On this small set, P034 surfaces real comparison activity (2/5 author
checks) with no Q009 noise. Precision/recall against human review is **not** measured here;
author-hash mismatches may include false positives from ©-line formatting (institutional names,
line breaks, or non-author tokens).

## 5. Limitations

- PDF text-layer extraction only; image-only copyright pages are skipped (none observed here).
- Copyright page detection uses ©/copyright signals in the first six pages when front-matter
  headings exist; may conflate page 4 with other front-matter if layout differs.
- Title Page year requires a standalone `Month YYYY` line or a single unambiguous four-digit
  year elsewhere on page 1.
- Copyright author requires a ©/copyright notice with `YEAR` + remainder pattern; many layouts
  on this dataset did not yield a confident copyright-side author on three files.
- Sebastian Fine clean baseline PDF was extracted locally from the tracked ZIP; not committed.
- Two author findings are heuristic hash mismatches only — not verified against ground truth.

## 6. Related docs

- Synthetic validation: `docs/evaluation/p034_copyright_page_synthetic_validation.md`
- P033 current-dataset evaluation: `docs/evaluation/p033_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
