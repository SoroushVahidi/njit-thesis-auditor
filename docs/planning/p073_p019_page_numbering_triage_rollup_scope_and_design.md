# P073 Scope and Design — P019 Page-Numbering Triage Rollup

- **Date:** 2026-06-09
- **Status:** Scoped — not yet implemented
- **Baseline commit:** `5b8a657` (PR #266 — P036–P063 gap-fill complete)
- **Validation baseline:** P001–P072 implemented; **1014 pytest**; ruff clean; mypy 87 source files
- **P073 name:** P019 Page-Numbering Triage Rollup
- **Type:** Evaluation/documentation triage — no audit behavior change

---

## 1. Motivation

### Why P019 triage is the best engineering fallback

After the P036–P063 gap-fill (PR #266) and the Sebastian Fine EF archive recovery attempt
(PR #265 — BLOCKED), the post-P072 strategy (`docs/status/post_p072_backlog_and_data_strategy.md`)
identifies P019 reporting triage as the best remaining engineering task:

| Option | Decision |
|---|---|
| Recommendation 1: Data acquisition (Sebastian Fine EF PDF) | Blocked — original Google Drive RAR not locally present |
| Recommendation 2: P036–P063 evaluation gap-fill | **Complete** (PR #266) |
| Recommendation 3: P019 reporting triage | **This PR** |
| All others (D/E/F/G/H) | Deferred or rejected |

P019 has **67 findings** across five evaluation PDFs — the fifth-largest rule by count
in the canonical aggregate (behind P013: 461, P026: 415, P011: 169, P012: 143). Like P011,
P013, and P026, P019 would benefit from a structured triage rollup that groups findings by
likely cause and helps reviewers distinguish actionable violations from likely artifacts.

P019 currently has **no** dedicated triage rollup (unlike P011, P013, P026, which all have
`p0NN_margin/font/page_triage` rollup sections in `report_outputs.py`). Without triage,
the 67 findings appear as raw per-page warnings with no cause classification.

### P019 finding profile (five-PDF, current auditor)

| File label | P019 count | Dominant issue type |
|---|---:|---|
| Cibaku Elson 1st Review | 8 | `mixed_numbering_style` (3), `multiple_page_numbers` (2) |
| Yin H 2nd Review (flattened) | 15 | `multiple_page_numbers` (7), `mixed_numbering_style` (5) |
| Yin Haotian 2nd Review | 15 | `multiple_page_numbers` (7), `mixed_numbering_style` (5) |
| Yin H 4th Review (compressed) | 25 | `multiple_page_numbers` (10), `mixed_numbering_style` (9) |
| Sebastian Fine clean baseline | 4 | `multiple_page_numbers` (2), `mixed_numbering_style` (1) |
| **Total** | **67** | `multiple_page_numbers`: 28; `mixed_numbering_style`: 23 |

Issue-type totals across all five files:

| Issue type | Count | % |
|---|---:|---:|
| `multiple_page_numbers` | 28 | 42% |
| `mixed_numbering_style` | 23 | 34% |
| `inconsistent_position` | 10 | 15% |
| `sequence_gap` | 6 | 9% |

---

## 2. Guideline / Q-Rule Basis

P019 performs conservative heuristic checks on page-number candidates detected by
`detect_page_number_candidates()`. The underlying guideline requirements are:

| Q-rule | Section | Requirement summary | Coverage by P019 |
|---|---|---|---|
| Q022 | Biographical Sketch | First Bio Sketch page has correct lowercase Roman numeral | Partially covered by `mixed_numbering_style`; exact-value check is P037 |
| Q031 | Dedication Page | Dedication page has next sequential lowercase Roman numeral | Partially covered by sequence checks; exact-value check is P037 |
| Q035 | Acknowledgements | Acknowledgements page has next sequential lowercase Roman numeral | Partially covered by sequence checks |
| Q046 | Table of Contents | TOC continues the Roman numeral sequence correctly | Partially covered by `sequence_gap` |
| Q060 | List of Tables | LoT continues the Roman numeral sequence correctly | Partially covered |

Additional implicit policy requirements addressed by P019:
- Arabic page numbers must appear on all body pages (no gaps — `sequence_gap`)
- Only one page number per page (`multiple_page_numbers` issue type)
- Page numbers must be consistently positioned (`inconsistent_position`)
- Roman and Arabic styles must not be mixed within the same page-numbering regime (`mixed_numbering_style`)

Q-rules not yet fully covered by P019 (deferred from v1):
- **Q001, Q008, Q012, Q014** — specific named pages (Abstract, Title, Copyright, Approval) must be free of any visible page number; P022 covers this separately
- **Full value-accuracy sequence** — checking exact expected Roman numeral values per section; P037 covers this for Bio Sketch
- **Full NJIT page-numbering policy** — Roman lowercase for front matter (starting at iii or iv), Arabic for body; P028 covers regime; P029 covers relative ordering

Classification summary:

| Check type | Covered by P019? | Notes |
|---|---|---|
| Sequence gaps / missing page numbers | Partially (`sequence_gap`, `missing_page_number`) | Conservative; not all gaps flagged |
| Multiple page numbers on one page | Yes (`multiple_page_numbers`) | May include EF annotation artifacts |
| Mixed Roman/Arabic on same page | Yes (`mixed_numbering_style`) | Concentrated at front-matter/body boundary |
| Inconsistent position across pages | Yes (`inconsistent_position`) | Conservative; top/bottom zone comparison |
| Exact Roman numeral values | No | P037 covers Bio Sketch; full coverage deferred |
| Named pages free of page numbers | No | P022 covers this separately |
| Full regime compliance | No | P028 covers regime; P029 covers ordering |

---

## 3. P073 v1 Scope

### What P073 v1 should produce

P073 v1 is a **documentation and evaluation triage task only**. It produces:

1. `docs/evaluation/p073_p019_page_numbering_triage_rollup.md` — a privacy-safe evaluation document that:
   - Runs (or reuses) P019 findings from the five-PDF current-dataset audit
   - Groups findings by: file label, issue type, page range
   - Identifies likely cause categories for each cluster (see §5 below)
   - Distinguishes: likely artifact-driven clusters, likely true formatting issues, and uncertain/manual-review-needed cases
   - Notes the high correlation between `multiple_page_numbers` and EF-annotation PDFs
   - Notes that Yin H 2nd (flattened) and Yin Haotian 2nd produce identical P019 results (same dissertation, two versions)
   - Records relationship to canonical 1,543 aggregate (P019: 67 unchanged)
   - Provides a recommendation on whether future P019 code refinement is warranted

2. *(Optional, future)* A `p019_page_numbering_triage` rollup section in `report_outputs.py` — analogous to `p011_margin_triage`, `p013_triage`, and `p026_font_triage` — that groups findings in JSON/Markdown reports for end users. This is a v2 consideration and is **not in scope for P073 v1**.

### What P073 v1 should NOT do

- Do not change `check_pdf_page_number_sequence()` behavior
- Do not add or remove issue types from P019
- Do not alter P013 candidate detection (shared module; P019 builds on P013 candidates)
- Do not suppress any P019 findings
- Do not add new unit tests unless a helper script is added to generate the triage doc
- Do not quote page text, candidate text, or dissertation content

---

## 4. Triage Evidence — Preliminary Analysis

### Pattern 1: `multiple_page_numbers` — likely EF annotation artifacts

`multiple_page_numbers` is the dominant issue type (28/67 = 42%). It fires when two or more
page-number candidates are detected on a single page. On EF-annotated PDFs, this is likely
caused by EF review comment text blocks appearing in the page margin alongside actual page
numbers — the same mechanism that inflates P012 (embedded annotation objects) and P011 (margin
overflow on EF PDFs).

| Evidence | Observation |
|---|---|
| Cibaku (78 EF annotations): 2 `multiple_page_numbers` | EF annotations likely add marginal text |
| Yin H 2nd flat (EF comments): 7 `multiple_page_numbers` | Same as Yin Haotian 2nd (same doc, EF present) |
| Yin Haotian 2nd (65 EF annotations): 7 `multiple_page_numbers` | Matches flat version exactly |
| Yin H 4th compressed (compressed/flattened): 10 `multiple_page_numbers` | Compression artifacts + EF text |
| Sebastian Fine (clean baseline, no EF): 2 `multiple_page_numbers` | Lower baseline; possible OCR artifacts |

**Triage verdict:** `multiple_page_numbers` findings on EF PDFs are predominantly artifact-driven.
Low actionability for real dissertation compliance. High candidates for a future `p019_artifact_suspected`
triage flag (analogous to P011's compression-artifact guard).

### Pattern 2: `mixed_numbering_style` — front-matter/body boundary concentration

`mixed_numbering_style` fires when Roman and Arabic numerals coexist on the same or adjacent
pages (23/67 = 34%). The page distributions show strong front-matter/body boundary clustering:

| File label | `mixed_numbering_style` count | Key pages |
|---|---:|---|
| Cibaku | 3 | 10, 11 |
| Yin H 2nd flat | 5 | 10, 11, 57, 58, 75, 88, 104 |
| Yin Haotian 2nd | 5 | 10, 11, 57, 58, 75, 88, 104 |
| Yin H 4th compressed | 9 | 7, 11, 12, 15, 17, 45, 50, 71 |
| Sebastian Fine | 1 | 13, 14 |

Pages 10–15 appear across all files — the front-matter/body transition zone. Findings here
may be genuine (mixed Roman/Arabic around the regime boundary) or may reflect the candidate
detector finding Roman numerals in TOC/LoT/LoF entries near the body start.

**Triage verdict:** Mixed signal. Pages 10–15 findings are partially expected (boundary region);
pages far from the boundary (57, 58, 75, 88, 104 on Yin H files) warrant manual review.

### Pattern 3: `inconsistent_position` — moderate signal

`inconsistent_position` (10/67 = 15%) fires when page-number position (top/bottom, left/center/right)
changes across pages. All ten on EF PDFs, none on Sebastian Fine. Consistent with EF annotation
markup shifting apparent text positions.

**Triage verdict:** Likely artifact-driven on EF PDFs; low actionability without further filtering.

### Pattern 4: `sequence_gap` — highest actionability

`sequence_gap` (6/67 = 9%) fires when a detected numeric page value jumps by more than 1 from
the expected sequence (skipped or missing page number). This is the least likely to be
artifact-driven.

| File label | `sequence_gap` |
|---|---:|
| Cibaku | 1 |
| Yin H 2nd flat | 1 |
| Yin Haotian 2nd | 1 |
| Yin H 4th compressed | 2 |
| Sebastian Fine | 1 |

**Triage verdict:** Highest actionability of any P019 issue type. Recommend flagging these
as `triage_tier: high` in a future `p019_page_numbering_triage` rollup (v2).

### Yin H duplicate note

Yin H 2nd Review (flattened) and Yin Haotian 2nd Review produce identical P019 findings —
15 each, same pages (10, 11, 57, 58, 75, 88, 104), same issue types. These are two versions
of the same dissertation. For triage purposes, they should be noted as a correlated pair;
any P019 finding that appears on both is confirmed to reflect the document's structure, not
a random artifact of one version.

---

## 5. Proposed Triage Algorithm (for v1 evaluation doc, and future v2 rollup)

The P073 v1 evaluation doc should compute the following from the existing five-PDF P019 findings:

```
For each P019 finding:
    group by: file_label, issue_type
    collect: page numbers (numeric only), count

For each (file_label, issue_type) group:
    record: count, page list (numeric), likely_cause category

Likely cause categories (privacy-safe — no text quoting):
    "artifact_suspected"   — multiple_page_numbers on EF-annotated PDFs, or inconsistent_position on EF PDFs
    "boundary_expected"    — mixed_numbering_style at pages consistent with front-matter/body transition
    "boundary_mixed"       — mixed_numbering_style at pages far from expected boundary
    "high_signal"          — sequence_gap findings (any file)
    "uncertain"            — any finding not clearly in above categories; flag for manual review
```

The rollup should NOT:
- Quote any page text, candidate text, or dissertation content
- Filter or suppress any findings from the audit output
- Change the canonical aggregate total

---

## 6. Output Document Plan

### Primary output (P073 v1)

**Doc:** `docs/evaluation/p073_p019_page_numbering_triage_rollup.md`

Contents:
- Date, baseline commit, validation status
- Purpose: triage/classify P019 findings by likely cause
- Five-PDF aggregate P019 results (by file label, issue type, page ranges numeric only)
- Cause-category classification table
- Yin H 2nd duplicate note
- Whether future P019 code refinement is warranted (recommendation)
- Relationship to canonical 1,543 aggregate
- Limitations

### Secondary output (P073 v2 — future, not in this scope)

A `build_p019_page_numbering_triage_summary()` function in `report_outputs.py`, analogous to
`build_p011_margin_triage_summary()`, that adds a `p019_page_numbering_triage` rollup to
JSON and Markdown reports. This would require:
- Adding `triage_tier` metadata to P019 findings in `check_pdf_page_number_sequence()` (code change)
- New grouped rollup in `build_grouped_summary()` output
- 8–10 unit tests in `tests/test_report_outputs.py`

**V2 is deferred.** P073 v1 covers the documentation/evaluation only.

### Generated output path

`data/evaluation/generated/p073_p019_triage/` — gitignored; never committed

---

## 7. Privacy Model

- No page text, candidate text, or dissertation content quoted anywhere
- Numeric page numbers only (position in document, not content)
- File labels only (not filename path with student names)
- Counts, page ranges, and category labels only
- Generated outputs remain in gitignored `data/evaluation/generated/p073_p019_triage/`

---

## 8. Synthetic/Current-Dataset Test Plan

**P073 v1 is docs/evaluation-only; no new unit tests are expected.**

If a helper script is added to generate the triage doc (v1.5), add:
- Test that P019 findings are correctly grouped by file label and issue type
- Test that page numbers appear as integers only (no text)
- Test that no dissertation content appears in triage output
- Test that canonical aggregate total is unchanged after grouping

**If v2 code changes are implemented**, add 8–12 tests in `tests/test_report_outputs.py`:
1. `p019_page_numbering_triage` section present in `grouped_summary`
2. Triage groups: one entry per `(file, issue_type)` pair
3. `triage_tier` field present on P019 findings after code change
4. `sequence_gap` findings get `triage_tier: high`
5. `multiple_page_numbers` on EF PDFs get `triage_tier: low` (artifact suspected)
6. Raw P019 count unchanged by triage metadata addition
7. Markdown report includes P019 Triage section
8. Privacy: no page text in triage output
9. Empty triage (no P019 findings): no section emitted
10. Coexistence with P011/P013/P026 triage sections
11. Page ranges are numeric integers only
12. Identical findings on Yin H 2nd flat vs Yin Haotian 2nd noted as correlated pair

---

## 9. Current-Dataset Evaluation Plan

For the P073 v1 triage doc:

1. Run `run_pdf_audit_full()` on each of the five evaluation PDFs (or reuse existing generated outputs)
2. Filter to `rule_id == "P019"`
3. Group by `(file_label, issue_type)` and collect page lists
4. Classify each group by likely cause (see §5)
5. Verify total P019 count = 67 (matches canonical aggregate)
6. Note Yin H 2nd flat / Yin Haotian 2nd identity
7. Record in `docs/evaluation/p073_p019_page_numbering_triage_rollup.md`

Generated outputs go only to `data/evaluation/generated/p073_p019_triage/` (gitignored).

---

## 10. Risks and Limitations

| Risk | Notes |
|---|---|
| Triage does not prove correctness | P019 is heuristic; findings may be false positives or true violations; manual review required |
| Five-PDF set is small | 5 files, 3 are EF-annotated; patterns may not generalize |
| `multiple_page_numbers` may mask real violations | Artifact-suspected classification is probabilistic; some `multiple_page_numbers` may be real |
| `mixed_numbering_style` at boundary is ambiguous | NJIT permits Roman/Arabic mix at front-matter/body boundary; P019 may fire correctly on non-compliant files |
| Text-layer dependency | Compressed/flattened PDFs may under- or over-detect candidates; P019 inherits these limitations |
| No OCR | Image-embedded pages not detected; P019 only sees machine-readable text layer |
| Same dissertation, two versions | Yin H 2nd flat and Yin Haotian 2nd produce identical results; neither is an independent sample |

---

## 11. Implementation Checklist for Next PR

Branch: `docs/p073-p019-page-numbering-triage-rollup`

- [ ] Extract Sebastian Fine from ZIP (or reuse `data/evaluation/generated/p036_p063_gap_fill/sebastian_fine_clean.pdf`)
- [ ] Run `run_pdf_audit_full()` on all five PDFs and filter to P019
- [ ] Create `docs/evaluation/p073_p019_page_numbering_triage_rollup.md` with per-file, per-issue-type counts, page ranges (numeric), and cause-category classification
- [ ] Verify P019 total = 67 (consistent with canonical 1,543)
- [ ] Update `data/processed/evaluation_data_manifest.json` with `p073_p019_triage_note`
- [ ] Update `docs/status/evaluation_data_manifest.md`, `current_project_state_and_next_steps.md`
- [ ] Update README to index the triage doc
- [ ] Run: `ruff check .`, `mypy src`, `python -m pytest` — confirm 1014 pass, no changes
- [ ] Do not commit generated outputs, extracted PDFs, or any private artifacts
- [ ] Do not modify P019 audit behavior

*(V2 code changes, if later decided, would be a separate PR.)*

---

## 12. Recommendation

**P073 v1 is ready for implementation as a docs/evaluation triage task.**

- No code changes required
- No privacy risk beyond existing evaluation workflow
- No new tests expected for v1
- Follows the established pattern of P011/P013/P026 triage evaluation docs
- Low implementation risk

**Recommended next branch:** `docs/p073-p019-page-numbering-triage-rollup`

If the triage doc reveals that `multiple_page_numbers` artifact filtering is worth adding to
`report_outputs.py` (v2), that can be scoped as a separate follow-on after the v1 doc is
committed and reviewed.

---

## Cross-References

- Post-P072 strategy: `docs/status/post_p072_backlog_and_data_strategy.md` (Recommendation 3)
- Canonical aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md` (P019: 67)
- P011 triage precedent: `docs/evaluation/p011_reporting_actionability_refinement.md`
- P013 triage precedent: `docs/evaluation/p013_reporting_actionability_refinement.md`
- P026 triage precedent: `docs/evaluation/p026_reporting_actionability_refinement.md`
- Phase 2 P019 legacy evaluation: `docs/evaluation/phase2_p019_page_number_validation_evaluation.md`
- P019 module: `src/njit_auditor/rules/pdf_page_numbers.py`
- P013 (candidate detection, shared module): `src/njit_auditor/rules/pdf_page_numbers.py`
- P036–P063 gap-fill: `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`
- Sebastian Fine EF recovery: `docs/evaluation/sebastian_fine_ef_archive_recovery.md`
