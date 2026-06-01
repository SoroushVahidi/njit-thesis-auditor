# P033 Candidate Extraction Recall Investigation

- **Date:** 2026-06-01
- **Baseline commit (investigation start):** `5f27b0b` (post–PR #62 P033 current-dataset evaluation)
- **Implementation change:** yes — narrow below-heading fallback (same PR series)

## 1. What was investigated

PR #62 reported **0 P033 findings** on all five evaluation PDFs because **cross-page comparison never ran** (fewer than two confident title candidates per file). This investigation asked whether extraction was appropriately conservative or missing common NJIT front-matter layouts in the PDF text layer.

Constraints: aggregate/structural reporting only — no dissertation title text, author names, or body text.

## 2. Reproduction summary (pre-refinement)

| File label | Roles present | Confident candidates | Comparison | P033 findings |
|---|---|---:|---|---:|
| Cibaku Elson 1st review | title_page, abstract | 1 (eval doc noted 0 in one table row; title_page had 3 words) | skipped | 0 |
| Yin H 2nd review (flattened) | title_page, abstract | 1 | skipped | 0 |
| Yin Haotian 2nd review | title_page, abstract | 1 | skipped | 0 |
| Yin H 4th review (compressed) | title_page, abstract, approval_page | 1 | skipped | 0 |
| Sebastian Fine clean baseline | title_page, abstract, approval_page | 1 | skipped | 0 |

Skip reason on every file: `insufficient_confident_title_candidates` (need ≥2 distinct high-confidence hashes).

## 3. Structural diagnosis (privacy-safe)

### Layout pattern on all five PDFs

| Signal | Observation |
|---|---|
| ABSTRACT page number | **1** on all five files (heading on same sheet as title material) |
| Lines above ABSTRACT heading | **0** on every file |
| Title below ABSTRACT heading | **High-confidence block detected** on all files (probe: 3–19 normalized words, same hash as title_page on Yin H 4th / Sebastian when not deduplicated) |
| APPROVAL PAGE | Pages **5** on Yin H 4th and Sebastian only |
| Lines above APPROVAL PAGE heading | **0** on approval pages |
| Title below APPROVAL PAGE heading | **High-confidence block detected** on Yin H 4th and Sebastian (probe: 19–21 words) |

### Per-file skip mechanisms (pre-refinement)

| File label | Primary reason second candidate missing |
|---|---|
| Cibaku Elson 1st review | Title-page region only 3 normalized words on one role; abstract/approval title blocks not extracted (above-heading path only) |
| Yin H 2nd / Yin Haotian 2nd | Only `title_page` candidate; abstract role used above-heading on page 1 (empty band above heading) |
| Yin H 4th / Sebastian | Only `title_page` candidate; approval title sits **below** APPROVAL PAGE heading (not above) |

### Root cause

P033 initially extracted title-like text **only above** `ABSTRACT` and `APPROVAL PAGE` headings. On these PDFs, both headings sit at the **top** of the page (y≈70–81 pt). Dissertation titles appear in the band **below** the heading, not above it. The title-page extractor still found a page-1 candidate from the upper region before metadata markers.

This is a **recall gap in region selection**, not evidence that titles are image-only or absent.

### False-positive risks considered

| Risk | Mitigation in refinement |
|---|---|
| Capturing abstract body text below ABSTRACT | Stop at abstract-body opener lines (`this`, `in this`, …); cap lines (5), vertical gap (90 pt), words per line (12), total words (22) |
| Capturing committee text on approval pages | Stop at metadata markers (`Dissertation Committee`, `Dr.`, …) after title block starts |
| Duplicate same title on page 1 | Deduplicate candidates by normalized hash across roles |

## 4. Decision

**Refine P033** with a conservative below-heading fallback when above-heading extraction returns nothing, plus hash deduplication across roles.

Not chosen:

- **No change** — rejected; structural evidence shows titles are present but in the wrong band.
- **Docs only** — insufficient; comparison never ran on real PDFs.
- **Tests only** — implementation gap was real.

## 5. Implementation summary (narrow)

Module: `src/njit_auditor/rules/pdf_title_consistency.py`

- Added `_extract_below_heading_candidate` (strict line/word/gap budgets).
- Added `_extract_heading_region_candidate` (above, then below).
- Abstract below-heading: reject first line matching abstract-body openers.
- `_collect_title_candidates`: skip duplicate `title_hash` values across roles.
- Synthetic tests: below-heading abstract/approval paths, body-line guard, single-candidate PDF without approval page.

## 6. Post-refinement evaluation counts

Re-run on the same five PDFs (gitignored summary under
`data/evaluation/generated/p033_evaluation_after_recall_refinement/`):

| File label | Confident candidates | Roles | Comparison ran | P033 findings | Notes |
|---|---:|---|:---:|:---:|---|
| Cibaku Elson 1st review | 1 | title_page | no | 0 | Abstract below-heading matches title_page hash (deduplicated) |
| Yin H 2nd review (flattened) | 1 | title_page | no | 0 | Same dedup pattern |
| Yin Haotian 2nd review | 1 | title_page | no | 0 | Same dedup pattern |
| Yin H 4th review (compressed) | 2 | title_page, approval_page | **yes** | 0 | Similarity to reference ≥0.92 (probe ~0.96) |
| Sebastian Fine clean baseline | 2 | title_page, approval_page | **yes** | 0 | Similarity to reference ≥0.92 (probe ~0.95) |

**Total P033 findings after refinement:** **0** (comparison now runs on two files; no material mismatches).

## 7. Conclusion

| Question | Answer |
|---|---|
| Was extraction too conservative? | **Yes** for below-heading title bands on ABSTRACT and APPROVAL PAGE pages. |
| Is refinement justified? | **Yes**, with strict below-heading limits and hash deduplication. |
| Does refinement improve mismatch detection on this dataset? | **Partially** — enables comparison on Yin H 4th and Sebastian; still **0 findings** (titles align within threshold). |
| False positives on this dataset? | **None observed** after refinement. |

## 8. Limitations

- Still PDF text-layer only; image-only titles remain invisible.
- Abstract-on-page-1 layouts deduplicate abstract vs title_page when hashes match — comparison may still be skipped.
- Below-heading band may miss titles far below headings or multi-page abstract layouts.
- Similarity threshold (0.92) not calibrated against human review on this dataset.
- No evaluation of whether approval-page title variants should always match title-page wording.
- Investigation and post-refinement counts are structural; precision/recall not measured.

## 9. Related docs

- Pre-refinement evaluation: `docs/evaluation/p033_current_dataset_evaluation.md`
- Post-refinement counts: update in same file (section 10)
- Synthetic validation: `docs/evaluation/p033_title_consistency_synthetic_validation.md`
