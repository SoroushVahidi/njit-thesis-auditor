# R036 Production Page-Relative Suppression/Abstention Design (2026-09-16)

Status: **production branch implementation** (not yet merged or deployed). This
is the productionization of the page-relative diagnostic work documented in
`r036_page_relative_spacing_experiment_20260916.md`.

## 1. Why the fixed 1.6 threshold was retired

The previous production R036 rule (`check_pdf_toc_list_entry_spacing`)
reported a finding whenever the inter-entry pitch was below a fixed `1.6`
multiple of the page's local single-line pitch
(`MIN_INTER_ENTRY_GAP_RATIO`). That fixed ratio is contradicted by 24
Ester-confirmed R036 false positives whose normalized ratios span **1.00 to
1.56** -- 12 of them on a single Praneeth page-11 TOC that Ester reviewed as
"All of these are False positives", and 12 more across Muyeed, Philip, and
Patrick after the split-section-number recovery. A fixed ratio cannot
reliably separate "normal" from "defective" when the reviewed false positives
sits below the threshold. The constant is therefore **retired as the decisive
production reporting rule**; it is retained only for import compatibility and
is documented as such.

## 2. Ground truth

* **Known Ester-confirmed R036 false positives: 24** (12 Praneeth page-11 +
  12 post-recovery Muyeed/Philip/Patrick). Mapped in
  `data/evaluation/r036_ester_false_positive_ground_truth_20260916.json`.
* **Known Ester-confirmed R036 true positives: 0.** No real-document R036
  finding has been confirmed by Ester as a genuine spacing defect.
* The page-relative diagnostic model (Model E, after the Patrick LOF
  structural-artifact resolution) suppresses all 24 false positives, is stable
  across `min_gaps` in {4,5,6} and neighbor floor in {0.65..0.80}, and detects
  an isolated artificial tight gap in a synthetic test -- but has never
  validated positive detection on a real dissertation.

## 3. Production semantics

Every eligible inter-entry gap is classified into exactly one of three
outcomes. Only **REPORT** produces a student-facing finding; the other two
emit nothing.

| Outcome | Meaning | Student-facing finding |
| --- | --- | --- |
| **SUPPRESS** | The gap matches normal local page rhythm. | No |
| **ABSTAIN** | Context is unreliable: page too sparse, ambiguous reconstruction, or untrustworthy neighborhood. | No |
| **REPORT** | Materially tighter than reliable local rhythm **and** the strong multi-signal gate is satisfied **and** the reporting gate is enabled. | Yes (normal R036 wording) |

### Confidence separation (made explicit in the code)

* **Suppression confidence** is high: page-relative normality is well
  supported, so a candidate matching local rhythm is confidently suppressed.
* **Abstention confidence** is high: structural/sparse/neighborhood
  uncertainty is confidently used to *refuse to decide*, never to force a
  PASS or FAIL.
* **Reporting confidence** is deliberately low: positive detection requires a
  stronger evidentiary gate than the diagnostic neighbor floor alone, and is
  **disabled** until a real true positive is validated.

The decision pipeline is:

```
candidate
  -> structural reliability gate   (reconstructed entry?  -> ABSTAIN)
  -> page-context sufficiency gate (page too sparse?       -> ABSTAIN)
  -> reliable-neighbor baseline     (no clean 2+ neighbors? -> ABSTAIN)
  -> normal-rhythm suppression test (matches local rhythm? -> SUPPRESS)
  -> strong-anomaly reporting gate  (only if gate enabled) -> REPORT / ABSTAIN
  -> otherwise ABSTAIN
```

Ambiguous candidates are never forced into SUPPRESS or REPORT; they ABSTAIN.

## 4. What was productionized (reliable parts of Model E)

* **Page-local context** -- page-relative inter-entry rhythm replaces the
  fixed 1.6 ratio.
* **Reliable-neighbor selection** -- for LOF/LOT with wrapped entries, compare
  against the nearest clean, structurally comparable neighbors, skipping gaps
  that touch wrapped entries and excluding lower-tail neighbors; TOC pages
  keep the simpler fixed window (validated against the reviewed TOC false
  positives).
* **Structural-reconstruction abstention** -- preserves the Patrick fix: an
  LOF/LOT single-line entry whose first visual line starts at the
  caption-continuation indent (>= `CONTINUATION_INDENT_OFFSET_PT` right of the
  page's entry-number column) is a reassembly artifact and abstains.
* **Sparse-page handling** -- fewer than `MIN_PAGE_GAPS_FOR_PAGE_MODEL` (5)
  eligible gaps on a page abstains; there is **no fallback to an absolute
  threshold**.

## 5. Candidate production designs (evaluated on the 7 real dissertations)

| Design | Known FPs reported | Real reports | Abstained | Suppressed | Plausible | Technical artifacts |
| --- | --- | --- | --- | --- | --- | --- |
| **0: suppress/abstain only** (selected) | 0 | 0 | 103 | 345 | 0 | 0 |
| 1: Model E + strong local anomaly gate | 0 | 0 | 103 | 345 | 0 | 0 |
| 2: Model E + local + page-tail confirmation | 0 | 0 | 103 | 345 | 0 | 0 |
| 3: Model E + multi-signal reporting gate | 0 | 0 | 103 | 345 | 0 | 0 |

All four designs produce **zero real reports** on this corpus: no candidate
gap on any of the seven dissertations is "materially tighter than reliable
local rhythm" under the promoted Model E baseline, so Designs 1-3 have nothing
to report even with their reporting gates enabled. This is not a failure --
it is the evidence that the fixed-1.6 findings (96) were not real page-relative
anomalies.

## 6. Selected design and rationale

**Selected: Design 0 (suppress/abstain only).**

Rationale, per the conservative decision rule:

1. **Zero known Ester false positives** -- satisfied by all designs.
2. **No obvious technical-artifact reports** -- satisfied (zero reports).
3. **Minimal unsupported reporting** -- Design 0 reports nothing; Designs 1-3
   would report nothing *today* but carry a reporting gate that is unvalidated
   on any real true positive. Keeping the gate disabled is the least-unsupported
   choice.
4. **High interpretability** -- each candidate's outcome and abstain reason
   (sparse_page / reconstruction_uncertainty / unreliable_neighborhood) is
   explicit and documented.
5. **Graceful abstention** -- ambiguity always resolves to ABSTAIN, never to a
   forced finding.
6. **Future extensibility** -- the strong multi-signal gate
   (`strong_multi_signal`: extreme local deviation + page-tail + two-sided
   clean neighbors + absolute visual-separation sanity) is implemented and
   tested (a synthetic isolated tight gap reports when the gate is enabled).
   Enabling reporting later is a one-constant change
   (`PRODUCTION_REPORTING_GATE`), not a redesign, once a real true positive is
   obtained.

Because there is no Ester-confirmed R036 true positive, positive-detection
capability **remains unvalidated on real ground truth**. Selecting a reporting
gate would be manufacturing a detection claim the evidence does not support.
Design 0 productionizes exactly what is empirically supported: suppression
and abstention.

## 7. Real-corpus outcomes (selected design)

| Document | Candidates | Suppressed | Abstained | Reported |
| --- | --- | --- | --- | --- |
| Youra | 70 | 58 | 12 | 0 |
| Anthony | 34 | 26 | 8 | 0 |
| Muyeed | 162 | 123 | 39 | 0 |
| Philip | 48 | 38 | 10 | 0 |
| Praneeth | 51 | 35 | 16 | 0 |
| Sebastian | 15 | 15 | 0 | 0 |
| Patrick | 68 | 50 | 18 | 0 |
| **Total** | **448** | **345** | **103** | **0** |

All 24 known Ester false positives classify as SUPPRESS (17) or ABSTAIN (7);
none is REPORTED. Praneeth and Anthony final report counts are both 0.

Abstain reasons (whole corpus): sparse_page, reconstruction_uncertainty
(LOF/LOT continuation-indent artifacts, e.g. Patrick p11), and
unreliable_neighborhood (page edges / insufficient clean neighbors / a
candidate tighter than rhythm but with the reporting gate disabled).

## 8. Magic constants

| Constant | Value | Role |
| --- | --- | --- |
| `MIN_PAGE_GAPS_FOR_PAGE_MODEL` | 5 | sparse-page abstention threshold |
| `NEIGHBOR_RELATIVE_FLOOR` | 0.72 | suppression/abstention boundary (diagnostic neighbor floor, promoted) |
| `NORMAL_NEIGHBOR_FLOOR` | 0.90 | a neighbor is a valid "normal rhythm" reference only if >= this fraction of the neighbor median |
| `CONTINUATION_INDENT_OFFSET_PT` | 12.0 | LOF/LOT continuation-indent geometry for reconstruction abstention |
| `WRAP_Y0_TOLERANCE_PT` | 2.0 | wrapped-entry line contiguity tolerance |
| `STRONG_LOCAL_ANOMALY_FLOOR` | 0.65 | (disabled gate) extreme local-deviation bar |
| `STRONG_PAGE_TAIL_PERCENTILE` | 0.05 | (disabled gate) page-distribution lower tail |
| `STRONG_MIN_TWO_SIDED_NEIGHBORS` | 2 | (disabled gate) two-sided confirmation |
| `STRONG_ABSOLUTE_MIN_PITCH_RATIO` | 0.85 | (disabled gate) absolute visual-separation sanity guard |

`MIN_INTER_ENTRY_GAP_RATIO` (1.6) is retained for compatibility but **does not
control reporting**.

## 9. User-facing semantics

When the policy abstains, **no finding is emitted**, so no internal wording
(anomaly score, MAD, neighbor floor, diagnostic model, insufficient model
confidence) can reach a student. When a finding is reported (future, gate
enabled), it uses the existing normal R036 student-facing explanation and
issue types (`toc_inter_entry_spacing_too_tight`, etc.); P036/internal
identifiers are not exposed to students.

## 10. Limitations

* **No real true positive** -- positive detection is validated only on
  synthetic pages; the 24 known FPs are the only real ground truth, and they
  only validate suppression/abstention.
* **Zero-report baseline** -- the selected design intentionally reports
  nothing on the current corpus. If a genuine R036 defect exists in a
  dissertation, it is not surfaced until the reporting gate is enabled after a
  true positive is confirmed.
* **Page-edge abstention** -- candidates near the first/last entry of a page
  may abstain for lacking a two-sided clean neighborhood even when the gap is
  normal; this is conservative, not a miss of a finding.

## 11. Pointers

* Prior diagnostic status: `r036_page_relative_spacing_experiment_20260916.md`
  and `r036_patrick_lof_anomaly_resolution_20260916.md`.
* Ground truth: `data/evaluation/r036_ester_false_positive_ground_truth_20260916.json`.
* Design comparison output: `r036_production_design_comparison_20260916.json`.
* Production module: `src/njit_auditor/rules/r036_production_page_relative_spacing.py`.
