# P034 Current Dataset Evaluation

- **Date:** 2026-06-01 (refreshed after PR #67)
- **Current baseline commit:** `f3c1b06` (post–PR #67 middle-initial author comparison tolerance)
- **Auditor scope:** P001–P034 (P034 only reported here)
- **Generated artifacts (gitignored):**
  - Initial run (PR #66): `data/evaluation/generated/p034_evaluation/`
  - Post–PR #67 refresh: `data/evaluation/generated/p034_evaluation_after_author_fix/`

## 1. Purpose and scope

Evaluate the conservative P034 Copyright Page metadata/layout rule on the repository’s
documented evaluation PDF set (`data/processed/evaluation_data_manifest.json`).

This document tracks **two evaluation snapshots**:

1. **Before PR #67** (commit through PR #66, `99b9c7d`) — 2 `copyright_author_mismatch` findings.
2. **After PR #67** (commit `f3c1b06`) — middle-initial tolerance; rerun confirms **0** findings.

Reporting is **aggregate-only**. No author names, dissertation title text, committee names,
or body text is quoted. Author hashes appear only in gitignored `p034_summary.json`.

See `docs/evaluation/p034_author_mismatch_investigation.md` for the structural explanation of
the PR #66 author findings (leading middle initial on © line vs Title Page `by` line).

Evaluated inputs match the five-PDF full-evaluation set used for P030–P033, excluding the
rule-matrix XLSX and archive-only materials not verified locally.

## 2. Evaluation history

| Milestone | Commit | P034 findings | Author comparison with finding | Outcome |
|---|---|---:|---:|---|
| PR #66 initial evaluation | `99b9c7d` | **2** | 2 / 2 compared | Both `copyright_author_mismatch` on page 4 |
| PR #67 investigation + fix | `f3c1b06` | — | — | Middle-initial tolerance added |
| PR #67 post-fix rerun | `f3c1b06` | **0** | 0 / 2 compared | Confirmed by re-run (this refresh) |

## 3. Current results (after PR #67)

| File label | Copyright detected | Year comparison | Author comparison | P034 before PR #67 | P034 after PR #67 | Issue types after PR #67 | Notes |
|---|---|:---:|:---:|:---:|:---:|---|---|
| Cibaku Elson 1st review | yes (p. 4) | no | no | 0 | 0 | — | ©/year not parsed; title `by` author extracted |
| Yin H 2nd review (flattened) | yes (p. 4) | no | no | 0 | 0 | — | Same skip pattern |
| Yin Haotian 2nd review | yes (p. 4) | no | no | 0 | 0 | — | Same skip pattern |
| Yin H 4th review (compressed) | yes (p. 4) | **yes** (match) | **yes** (match) | **1** | **0** | — | Was author-hash mismatch; suppressed by middle-initial rule |
| Sebastian Fine clean baseline | yes (p. 4) | no | **yes** (match) | **1** | **0** | — | Was author-hash mismatch; suppressed by middle-initial rule |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

**Totals after PR #67 (5 evaluated PDFs):**

| Metric | Before PR #67 | After PR #67 |
|---|---:|---:|
| Copyright page confidently detected | 5 / 5 | 5 / 5 |
| Year comparison ran | 1 / 5 | 1 / 5 |
| Author-hash comparison ran | 2 / 5 | 2 / 5 |
| **P034 findings** | **2** | **0** |
| Top-margin header findings (Q009) | 0 | 0 |

On all five PDFs, the Copyright Page was identified on **page 4** via ©/copyright text in early
front matter.

## 4. Comparison outcomes (after PR #67)

| Outcome | Files |
|---|---:|
| No copyright page detected | 0 |
| Copyright detected; year/author comparison skipped | 3 |
| Comparison ran; no mismatch | 2 |
| Comparison ran; mismatch found | 0 |

## 5. Interpretation

**After PR #67, P034 reports 0 findings on all five evaluation PDFs**, while remaining
partially evaluative:

- **Copyright page detection** still runs on every file (5/5).
- **Year comparison** still runs on one file (Yin H 4th); years matched (2026); no finding.
- **Author comparison** still runs on two files; both now resolve as matches under
  middle-initial tolerance (previously flagged due to one extra 2-character leading token on
  the © line).

**Before PR #67**, the two author findings were **false positives**, not confirmed true
author inconsistencies (see investigation doc). This refresh confirms the fix suppresses
them without reintroducing findings on the other three files.

**Zero findings do not prove Q009–Q011 compliance** — three files still skip year/author
comparison because metadata extraction is incomplete.

**Usefulness vs noise:** After PR #67, P034 is **silent** on this dataset while still
performing detection and limited comparisons. Q009 (top-margin header) produced no warnings
here. Precision/recall against human review is not measured.

## 6. Limitations

- PDF text-layer extraction only; image-only copyright pages are skipped (none observed here).
- Middle-initial tolerance covers only one short prepended/appended token; other ©-line
  formatting may still false-positive or false-negative.
- Title Page year requires a standalone `Month YYYY` line or a single unambiguous year on
  page 1.
- Sebastian Fine clean baseline PDF extracted locally from the tracked ZIP; not committed.
- Pre–PR #67 counts reflect behavior before middle-initial tolerance; current behavior is
  defined by the post–PR #67 rerun at commit `f3c1b06`.

## 7. Related docs

- Author-mismatch investigation: `docs/evaluation/p034_author_mismatch_investigation.md`
- Synthetic validation: `docs/evaluation/p034_copyright_page_synthetic_validation.md`
- P033 current-dataset evaluation: `docs/evaluation/p033_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
