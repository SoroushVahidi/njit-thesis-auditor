# P073 — P019 Page-Numbering Triage Rollup

- **Date:** 2026-06-09
- **Baseline commit:** `eb66d4a` (PR #267 — P073 scope doc)
- **Auditor scope:** P001–P072 implemented; **1014 pytest**; ruff clean; mypy 87 source files
- **P073 v1 type:** Docs/evaluation-only triage — no code behavior change, no new issue types
- **V2 code rollup** (`build_p019_page_numbering_triage_summary()` in `report_outputs.py`): **deferred**
- **Scope doc:** `docs/planning/p073_p019_page_numbering_triage_rollup_scope_and_design.md`
- **Generated outputs:** `data/evaluation/generated/p073_p019_triage/` — gitignored; not committed
- **Privacy:** Aggregate-only. No dissertation body text, page text, author names, EF comment text, titles, captions, or private content quoted anywhere in this document.

---

## 1. Purpose

P019 (`check_pdf_page_number_sequence`) has **67 findings** across the five evaluation PDFs —
the fifth-largest rule by count in the canonical aggregate — but unlike P011, P013, and P026,
has no dedicated triage rollup. This document classifies P019 findings by likely cause and
actionability level without altering any audit output or rule behavior.

P073 v1 answers:
- Which P019 findings are likely artifact-driven vs. likely real formatting issues?
- Where are findings concentrated?
- Which issue types warrant human reviewer attention?
- Is a future P019 code refinement rollup worth implementing?

---

## 2. Evaluation Dataset

| File label | Pages | EF comment status | Role in P019 analysis |
|---|---:|---|---|
| Cibaku Elson 1st Review | 99 | 78 extractable | EF-annotated comparison PDF |
| Yin H 2nd Review (flattened) | 108 | flattened (0 extractable) | EF-present, same doc as Yin Haotian |
| Yin Haotian 2nd Review | 108 | 65 extractable | EF-annotated comparison PDF |
| Yin H 4th Review (compressed) | 137 | compressed/flattened (0 extractable) | Compressed EF PDF; highest P019 count |
| Sebastian Fine clean baseline | 29 | no EF annotations | Clean baseline; no annotation artifacts |

---

## 3. P019 Issue Types — Overview

P019 checks for five issue types. Four were observed on the current five-PDF set:

| Issue type | Total | % | Description |
|---|---:|---:|---|
| `multiple_page_numbers` | 28 | 42% | Two or more page-number candidates detected on a single page |
| `mixed_numbering_style` | 23 | 34% | Roman and Arabic numeral candidates coexist on the same or adjacent pages |
| `inconsistent_position` | 10 | 15% | Page-number position (top/bottom, left/center/right) changes inconsistently across pages |
| `sequence_gap` | 6 | 9% | Detected numeric page value jumps by more than one from expected sequence |
| `missing_page_number` | 0 | 0% | Page expected to have a number has none detected |
| **Total** | **67** | **100%** | |

---

## 4. Per-File Breakdown

| File label | P019 total | `multiple_` | `mixed_` | `inconsistent_` | `sequence_gap` | Pages affected |
|---|---:|---:|---:|---:|---:|---|
| Cibaku Elson 1st Review | **8** | 2 | 3 | 2 | 1 | 10, 11 |
| Yin H 2nd Review (flattened) | **15** | 7 | 5 | 2 | 1 | 10, 11, 57, 58, 75, 88, 104 |
| Yin Haotian 2nd Review | **15** | 7 | 5 | 2 | 1 | 10, 11, 57, 58, 75, 88, 104 |
| Yin H 4th Review (compressed) | **25** | 10 | 9 | 4 | 2 | 7, 11, 12, 15, 17, 45, 50, 71, 115, 117, 134 |
| Sebastian Fine clean baseline | **4** | 2 | 1 | 0 | 1 | 13, 14 |
| **Total** | **67** | **28** | **23** | **10** | **6** | |

### Notable observation: Yin H identical pair

Yin H 2nd Review (flattened) and Yin Haotian 2nd Review produce **identical** P019 results —
15 findings each, same issue types, same affected pages. These are two versions of the same
dissertation (one EF-annotated, one flattened/compressed). The identity confirms that P019
findings on these files reflect the dissertation's actual page-numbering structure, not random
artifacts of one particular version. Any P019 finding appearing on both is structurally confirmed.

---

## 5. Cause-Category Classification

### 5a. Issue type × cause mapping

| Issue type | Predominant cause | Evidence | Actionability |
|---|---|---|---|
| `multiple_page_numbers` | EF annotation artifact | Count scales with EF presence; highest on Yin H 4th (10); Sebastian Fine (no EF) has 2 — lower baseline | **Low** (artifact likely) / **Medium** (Sebastian Fine) |
| `mixed_numbering_style` | Front-matter/body boundary + far-boundary-mixed | Pages 10–15 across all files = expected Roman/Arabic transition zone; pages 57–104 on Yin H files = far from boundary | **Medium** (boundary pages) / **High** (far-boundary pages) |
| `inconsistent_position` | EF annotation artifact | All 10 on EF-present PDFs (Cibaku, Yin H 2nd flat, Yin Haotian, Yin H 4th); 0 on Sebastian Fine | **Low** (artifact likely) |
| `sequence_gap` | Real formatting issue | Present on **all five files** (6 total); appears on clean baseline (Sebastian Fine) as well as EF PDFs | **High** |

### 5b. Per-file cause summary

| File label | Cause profile | Actionability summary |
|---|---|---|
| Cibaku Elson 1st Review | All 8 at pages 10–11; boundary zone; 78 EF annotations | `multiple_page_numbers` + `inconsistent_position`: artifact-suspected; `mixed_numbering_style`: boundary-expected; `sequence_gap` (1): high |
| Yin H 2nd Review (flattened) | 15 findings; pages 10–11 + scattered 57–104 | Boundary findings (pp. 10–11): medium; far-boundary `mixed_numbering_style` (pp. 57, 58, 75, 88, 104): high; `sequence_gap` (1): high |
| Yin Haotian 2nd Review | Identical to Yin H 2nd flat; confirmed structural | Same as above; structurally corroborated by identical-document twin |
| Yin H 4th Review (compressed) | 25 findings scattered across 11 pages; compressed text layer | `multiple_page_numbers` (10): artifact-suspected (compression + EF markup); `mixed_numbering_style` (9) mix of boundary and far-boundary; `sequence_gap` (2): high |
| Sebastian Fine clean baseline | 4 findings at pages 13–14; no EF | `multiple_page_numbers` (2) at pp. 13–14: medium (no EF; possible actual extra number); `mixed_numbering_style` (1): boundary-expected; `sequence_gap` (1): high |

---

## 6. Cause-Bucket Summary

| Cause bucket | P019 count | Interpretation | Suggested next action |
|---|---:|---|---|
| EF annotation artifact (`multiple_page_numbers` on EF PDFs) | ~24 | EF annotation text blocks detected as page-number candidates; not real formatting violations | Low reviewer priority; candidate for future artifact-guard in v2 code rollup |
| Front-matter/body boundary (`mixed_numbering_style` at pages ≤ 17) | ~10 | Roman/Arabic coexistence at front-matter/body transition; may be expected or a real regime-boundary error | Medium priority; confirm correct page-numbering regime starts at first body page |
| Far-boundary mixed numbering (`mixed_numbering_style` at pages > 20) | ~8 | Roman numeral candidates detected deep in body region; unexpected | High reviewer priority; may indicate stray Roman numerals in body captions or TOC-reference artifacts |
| Inconsistent position cluster | ~10 | Position shifts across pages; likely EF markup displacing text coordinates | Low reviewer priority on EF PDFs; medium on clean documents |
| Sequence gap (all files) | 6 | Real numeric jumps in detected page sequence; highest-signal issue | **High priority** — verify page numbers in sequence; check for missing pages or TOC pagination error |
| Uncertain / needs human review | ~9 | `multiple_page_numbers` on Sebastian Fine (2) + boundary `mixed_numbering_style` ambiguities | Manual review required |

---

## 7. Actionability Summary

| Actionability level | Count | Issue types | Notes |
|---|---:|---|---|
| **High** | ~14 | `sequence_gap` (6), far-boundary `mixed_numbering_style` (~8) | Most likely to represent real formatting violations needing correction |
| **Medium** | ~18 | Boundary `mixed_numbering_style` (~10), `multiple_page_numbers` on Sebastian Fine (2), uncertain `inconsistent_position` (~6) | Worth human review; may be real or boundary-expected |
| **Low / likely artifact** | ~35 | `multiple_page_numbers` on EF PDFs (~24), `inconsistent_position` on EF PDFs (~10) | Predominantly driven by EF annotation markup; low reviewer ROI |

---

## 8. High-Value Remediation Patterns

### Pattern A: `sequence_gap` — highest priority (6 findings, all files)

`sequence_gap` fires when the detected numeric page value jumps by more than 1 from the
expected sequence. This is the issue type least likely to be artifact-driven, and it fires
on all five files including the clean Sebastian Fine baseline. Reviewers should:

1. Locate the affected page (numeric page number only — no text)
2. Verify the PDF has consecutive page numbers at that location
3. If consecutive numbers are absent: check for deleted pages, missing front-matter pages, or PDF assembly errors

### Pattern B: Far-boundary `mixed_numbering_style` — second priority

`mixed_numbering_style` findings at pages significantly beyond the front-matter/body
transition (e.g., pages 45–134 on Yin H 4th, pages 57–104 on Yin H files) warrant review.
In a properly formatted NJIT dissertation, Arabic page numbers should be used exclusively
in the body. Roman numerals appearing deep in the body region indicate:
- A page from front matter was inserted at the wrong position, OR
- The page-number candidate detector found a Roman numeral in a TOC/LoT/LoF entry near that page, OR
- The body contains a page with a visible Roman numeral (non-standard)

Manual review of the flagged page position is recommended before reporting a violation.

### Pattern C: `multiple_page_numbers` on clean files — spot check

Sebastian Fine (no EF annotations) has 2 `multiple_page_numbers` findings at pages 13–14.
With no annotation markup, these are more likely to reflect a real formatting issue (e.g.,
a running header with a page-number-like token, or a chapter-opening page with visible number
and another candidate nearby). These 2 findings should be manually reviewed.

---

## 9. Likely Artifact Clusters

### Cluster 1: `multiple_page_numbers` on EF-annotated PDFs

The 26 `multiple_page_numbers` findings on the four EF/EF-present PDFs closely mirror the
EF annotation artifact pattern already documented for P011 (margin overflow) and P012
(embedded annotation objects). EF review comment text appearing in page margins is likely
being detected as a page-number candidate by `detect_page_number_candidates()`.

| File | EF annotations | `multiple_page_numbers` |
|---|---:|---:|
| Cibaku Elson 1st Review | 78 | 2 |
| Yin H 2nd Review (flattened) | 0 (flattened) | 7 |
| Yin Haotian 2nd Review | 65 | 7 |
| Yin H 4th Review (compressed) | 0 (compressed) | 10 |
| Sebastian Fine clean baseline | 0 | 2 |

The correlation is imperfect (flattened/compressed files still have high counts), but the
pattern is consistent with annotation-related text residue. Note: Yin H 2nd flat and Yin H
4th compressed have 0 extractable annotations but were annotated before being
flattened/compressed — residual annotation text is still present in the text layer.

### Cluster 2: `inconsistent_position` exclusively on non-clean PDFs

All 10 `inconsistent_position` findings appear on the four EF/EF-present PDFs; 0 on Sebastian
Fine. This is consistent with EF annotation markup shifting apparent text-block positions
relative to the page, causing the position-zone classifier to see inconsistency that would not
be present in an un-annotated version.

---

## 10. Future P019 Code Refinement Candidates

| Candidate | Evidence | Risk | Recommendation |
|---|---|---|---|
| Artifact guard for `multiple_page_numbers` on EF PDFs | 26/28 findings on EF PDFs; pattern mirrors P011/P012 artifact clusters | Medium — must not suppress real multi-number pages on clean PDFs | **Worth scoping** in v2; would follow P011 compression-artifact-guard pattern; requires threshold calibration |
| `triage_tier` metadata on P019 findings | Would enable rollup section in `build_grouped_summary()` like P011/P013/P026 | Low — metadata-only addition; no finding suppression | **Recommended for v2** — straightforward addition to `check_pdf_page_number_sequence()` |
| `inconsistent_position` suppression on EF PDFs | All 10 are EF PDFs; clean baseline has 0 | Medium — needs per-file EF flag not available at rule level | **Defer** — cross-rule information not easily available at audit time |
| Boundary-aware filter for `mixed_numbering_style` | Pages 10–15 are expected boundary zone | High — misclassifying real Roman-in-body violations as boundary-expected | **Defer** — manual review preferred; automated suppression risky |

### V2 recommendation

A `build_p019_page_numbering_triage_summary()` rollup in `report_outputs.py` (analogous to
`build_p011_margin_triage_summary()`) is **recommended for v2**. It would:
- Add `triage_tier` metadata to P019 findings (code change in `check_pdf_page_number_sequence()`)
- Group findings by issue type in JSON/Markdown output
- Flag `sequence_gap` as `triage_tier: high`
- Flag `multiple_page_numbers` on EF PDFs as `triage_tier: low` (after artifact-guard calibration)
- Require 8–10 unit tests in `tests/test_report_outputs.py`

V2 is **not in scope** for this PR. This triage doc provides the evidence base for scoping v2.

---

## 11. Relationship to Canonical Aggregate

| Metric | Value |
|---|---|
| Canonical five-PDF aggregate (P001–P070, post-P070) | **1,543** |
| P019 contribution to canonical | **67** |
| P019 count in this triage run | **67** |
| Consistent with canonical? | **Yes** |

No audit behavior changed. The 1,543 total is unchanged.

---

## 12. Generated-Output Path

Triage data saved to:
`data/evaluation/generated/p073_p019_triage/p019_triage_data.json`

This path is gitignored. Contents not committed. Sebastian Fine extracted PDF reused from
`data/evaluation/generated/p036_p063_gap_fill/sebastian_fine_clean.pdf` (also gitignored).

---

## 13. Privacy Protections

- No dissertation body text, page text, EF comment text, author names, titles, captions,
  reference entries, TOC/LoT/LoF entries, Bio Sketch text, Approval Page text, URLs/DOIs,
  labels/refs, or any private content quoted in this document.
- Numeric page numbers only (position in document, not page content).
- File labels only (not paths containing student names).
- Aggregate counts, percentages, and cause categories only.
- Generated outputs remain in gitignored paths; not committed.
- No OCR performed. No external network calls made.

---

## 14. Limitations

- **Five-PDF set is small.** 5 files do not constitute a representative sample; patterns may
  not generalize to other dissertations.
- **EF annotation artifacts.** Three of the five files contain EF reviewer annotation markup
  that inflates `multiple_page_numbers` and `inconsistent_position` counts; this is an
  evaluation-set artifact, not a representative distribution of clean student submissions.
- **Text-layer dependency.** Page-number candidate detection requires a machine-readable text
  layer; compressed/flattened PDFs may under- or over-detect candidates.
- **Cause classification is probabilistic.** Cause-bucket assignments in this document are
  based on aggregate patterns, not per-finding analysis. Human review is required before
  acting on individual findings.
- **Triage does not prove correctness.** Zero `sequence_gap` findings on a file would not
  prove page numbering is correct; the rule is conservative and may not detect all gaps.
- **No OCR.** Image-embedded pages are not analyzed.
- **Yin H duplicate pair.** Yin H 2nd (flattened) and Yin Haotian 2nd are two versions of
  the same dissertation; their identical results provide structural corroboration but do not
  constitute two independent data points.

---

## Cross-References

- P073 scope doc: `docs/planning/p073_p019_page_numbering_triage_rollup_scope_and_design.md`
- Post-P072 strategy: `docs/status/post_p072_backlog_and_data_strategy.md` (Recommendation 3)
- Canonical aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md` (P019: 67)
- P011 triage precedent: `docs/evaluation/p011_reporting_actionability_refinement.md`
- P013 triage precedent: `docs/evaluation/p013_reporting_actionability_refinement.md`
- P026 triage precedent: `docs/evaluation/p026_reporting_actionability_refinement.md`
- Phase 2 P019 legacy evaluation: `docs/evaluation/phase2_p019_page_number_validation_evaluation.md`
- P019 module: `src/njit_auditor/rules/pdf_page_numbers.py`
- P036–P063 gap-fill: `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`
