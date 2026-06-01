# P033 Current Dataset Evaluation

- **Date:** 2026-06-01 (updated after recall investigation)
- **Baseline commit:** `7982e86` (initial evaluation); post-refinement behavior documented in section 10
- **Auditor scope:** P001–P033 (P033 only reported here)
- **Generated artifacts (gitignored):** `data/evaluation/generated/p033_evaluation/`

## 1. Purpose and scope

Evaluate the conservative P033 cross-page front-matter title consistency rule on the
repository’s documented evaluation PDF set identified in
`data/processed/evaluation_data_manifest.json`.

Reporting is **aggregate-only**. No dissertation title text, title previews, author names,
committee names, or body text is quoted. No generated audit outputs are committed.

Evaluated inputs match the five-PDF full-evaluation set used for P030–P032, excluding the
rule-matrix XLSX and archive-only materials not verified locally.

## 2. Results summary

| File label | Availability | Page roles present | Confident candidates | Comparison outcome | P033 count | Pages | Notes |
|---|---|---|---|---:|---:|---|---|
| Cibaku Elson 1st review | tracked | title_page, abstract | 0 | insufficient_confident_title_candidates | 0 | — | Title-page text too short; no abstract/approval title block |
| Yin H 2nd review (flattened) | tracked | title_page, abstract | 1 | insufficient_confident_title_candidates | 0 | — | Title page only; abstract p.1 has no extractable title above heading |
| Yin Haotian 2nd review | tracked | title_page, abstract | 1 | insufficient_confident_title_candidates | 0 | — | Same pattern as Yin H 2nd |
| Yin H 4th review (compressed) | tracked | title_page, abstract, approval_page | 1 | insufficient_confident_title_candidates | 0 | — | Title page only (16-word candidate); abstract p.1 / approval p.5 lack title blocks |
| Sebastian Fine clean baseline | archive-contained (local extract) | title_page, abstract, approval_page | 1 | insufficient_confident_title_candidates | 0 | — | Title page only (18-word candidate); no title above abstract/approval headings |

### Skipped

| File label | Reason |
|---|---|
| Sebastian Fine 1st review (EF annotated) | Referenced in manifest; not present as a standalone tracked path |
| Rule matrix XLSX | Not a PDF evaluation input |

**Total P033 findings:** **0** across all five evaluated PDFs.

## 3. Candidate extraction detail (privacy-safe)

P033 requires **≥2 high-confidence** title candidates (normalized length ≥12 characters and
≥3 words) before comparison runs. The table below summarizes extraction attempts without
quoting title text.

| File label | Role | Page | Raw extract attempted | Meets confidence threshold | In comparison set |
|---|---|---:|:---:|:---:|:---:|
| Cibaku Elson 1st review | title_page | 1 | yes (2 words) | no | no |
| Cibaku Elson 1st review | abstract | 1 | no | — | no |
| Yin H 2nd review (flattened) | title_page | 1 | yes (3 words) | yes | yes |
| Yin H 2nd review (flattened) | abstract | 1 | no | — | no |
| Yin Haotian 2nd review | title_page | 1 | yes (3 words) | yes | yes |
| Yin Haotian 2nd review | abstract | 1 | no | — | no |
| Yin H 4th review (compressed) | title_page | 1 | yes (16 words) | yes | yes |
| Yin H 4th review (compressed) | abstract | 1 | no | — | no |
| Yin H 4th review (compressed) | approval_page | 5 | no | — | no |
| Sebastian Fine clean baseline | title_page | 1 | yes (18 words) | yes | yes |
| Sebastian Fine clean baseline | abstract | 1 | no | — | no |
| Sebastian Fine clean baseline | approval_page | 5 | no | — | no |

**Unique title hashes among confident candidates:** 1 per file (only one candidate each).

No cross-page similarity scores were computed because comparison was skipped on every file.

## 4. Structural context (privacy-safe)

| File label | Pages | ABSTRACT page | APPROVAL PAGE page | Named front-matter headings detected |
|---|---:|---:|---:|---|
| Cibaku Elson 1st review | 99 | 1 | — | yes (limited) |
| Yin H 2nd review (flattened) | 108 | 1 | — | yes |
| Yin Haotian 2nd review | 108 | 1 | — | yes |
| Yin H 4th review (compressed) | 137 | 1 | 5 | yes |
| Sebastian Fine clean baseline | 29 | 1 | 5 | yes |

On all five PDFs, the ABSTRACT heading was detected on **page 1** (same sheet as the title
page in the text layer). P033 looks for title-like lines **above** the ABSTRACT heading on
that page; none were found. Approval-page title blocks were not extractable on the two files
where APPROVAL PAGE appears (pages 5).

## 5. Interpretation

**Overall:** P033 produced **0 findings on all five evaluated PDFs**. This does **not**
prove cross-page title consistency. In every case, comparison was **skipped** because fewer
than two confident title candidates were extracted.

**Outcome categories (all files):**

| Category | Count | Meaning |
|---|---:|---|
| Roles present, &lt;2 confident candidates | 5 | Comparison never ran |
| Compared, no mismatch | 0 | — |
| Material mismatch flagged | 0 | — |
| No named front-matter headings | 0 | — |

**Why candidates were sparse:**

- **Title page:** Most files yielded one confident title-page candidate; Cibaku’s title-region
  text was too short (&lt;3 words) to qualify.
- **Abstract page:** ABSTRACT on page 1 shares the sheet with the title page; no separate
  title block appeared above the heading in the text layer.
- **Approval page:** On Yin H 4th and Sebastian, approval pages were detected (page 5) but
  no title-like lines appeared above APPROVAL PAGE.

**Usefulness vs noise on this dataset:** P033 was **silent** (no false-positive mismatches)
but also **non-evaluative** — it could not perform cross-page comparison on any file. The rule
appears conservative for this sample; usefulness for catching real inconsistencies remains
unmeasured (precision/recall not assessed).

## 6. Limitations

- PDF text-layer extraction only; titles in non-extractable regions or image-only text are
  skipped.
- Requires named front-matter headings; comparison needs ≥2 confident candidates.
- Abstract-on-page-1 layouts common in this dataset prevent abstract-page title extraction.
- Does not verify semantic equivalence, subtitles, or committee-page titles.
- Candidate and hash metadata are in gitignored `p033_summary.json` only.
- Sebastian Fine PDF extracted locally from the tracked ZIP; not committed.
- Zero findings do not demonstrate compliance; they reflect insufficient candidates for
  comparison on this evaluation set.

## 7. Related docs

- Synthetic validation: `docs/evaluation/p033_title_consistency_synthetic_validation.md`
- Candidate extraction recall investigation: `docs/evaluation/p033_candidate_extraction_recall_investigation.md`
- P032 current-dataset evaluation: `docs/evaluation/p032_current_dataset_evaluation.md`
- P025 front-matter structure: `docs/status/current_project_state_and_next_steps.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`

## 10. Post-refinement rerun (recall investigation)

After `docs/evaluation/p033_candidate_extraction_recall_investigation.md`, P033 gained a
conservative **below-heading** title band when above-heading extraction is empty (common when
ABSTRACT/APPROVAL PAGE is the first line on the page).

| File label | Candidates (post-refinement) | Comparison ran | P033 findings |
|---|---:|---|---:|
| Cibaku Elson 1st review | 1 | no | 0 |
| Yin H 2nd review (flattened) | 1 | no | 0 |
| Yin Haotian 2nd review | 1 | no | 0 |
| Yin H 4th review (compressed) | 2 | **yes** | 0 |
| Sebastian Fine clean baseline | 2 | **yes** | 0 |

When the below-heading abstract title matches the title-page hash, the abstract role is
deduplicated and comparison remains skipped (three files). Yin H 4th and Sebastian gain a
second candidate from the **approval_page** below-heading band; normalized similarity to the
title-page reference remained ≥0.92, so no warnings were emitted.

Gitignored post-refinement summary:
`data/evaluation/generated/p033_evaluation_after_recall_refinement/`
