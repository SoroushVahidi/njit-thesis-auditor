# R036 Page-Relative Spacing Experiment (2026-09-16)

This began as a diagnostic experiment. As of the `fix/r036-production-page-relative-suppression-20260916` branch, the reliable parts of this work are productionized through the conservative SUPPRESS/ABSTAIN policy documented in `r036_production_page_relative_suppression_design_20260916.md`; the reporting gate remains disabled because no real Ester-confirmed R036 true positive exists.

## Why this experiment exists

Ester has rejected both reviewed R036 batches as false positives: the original 12 Praneeth page-11 examples and the later 12 post-recovery examples spanning TOC, LOF, LOT, wrapped/unwrapped entries, same-level transitions, and hierarchy transitions. Those reviewed examples span normalized ratios from 1.00 through 1.56, so the current fixed 1.6 ratio is not supported as a production discriminator.

## Ground Truth

- Known Ester false positives: 24 (YES)
- True positives inferred from Ester feedback: 0

## Page Statistics Summary

- Candidate gaps collected: 448
- TOC/list pages analyzed: 42
- Pages with too few candidate gaps for page-local modeling: 10
- Pages by section: {'table_of_contents': 20, 'list_of_tables': 5, 'list_of_figures': 17}

## Model Comparison

| Model | All diagnostic anomalies | Current production findings remaining | Abstentions | Suppressed |
| --- | ---: | ---: | ---: | ---: |
| Model A - Median-relative ratio | 2 | 0 | 28 | 418 |
| Model B - Robust z-score | 29 | 0 | 28 | 391 |
| Model C - Lower-tail percentile | 44 | 0 | 28 | 376 |
| Model D - Two-mode clustering | 1 | 0 | 28 | 419 |
| Model E - Neighbor-relative anomaly | 0 | 0 | 99 | 349 |

## Selected Diagnostic Candidate

Model E - Neighbor-relative anomaly

Model E is the most interpretable diagnostic candidate: it compares a gap against nearby gaps on the same page, suppressing uniform page rhythm while still surfacing isolated lower-tail spacing dips. It abstains on sparse pages.

## Sparse-Page Policy

Use page-local modeling only when a page has at least five eligible inter-entry gaps after reconstruction and structural exemptions; otherwise diagnostic outcome is INSUFFICIENT_CONTEXT rather than a finding.

## Section-Type Results

- TOC: {'SUPPRESSED_AS_NORMAL_PAGE_RHYTHM': 221, 'INSUFFICIENT_CONTEXT': 14}
- LOF: {'INSUFFICIENT_CONTEXT': 54, 'SUPPRESSED_AS_NORMAL_PAGE_RHYTHM': 109}
- LOT: {'INSUFFICIENT_CONTEXT': 31, 'SUPPRESSED_AS_NORMAL_PAGE_RHYTHM': 19}

## Current Production Finding Diagnostic Table

On the production page-relative branch, current production R036 findings should be zero. If any production findings exist, this table records their diagnostic context for review planning.

| # | Document | Page | Section | Pair | Ratio | Diagnostic Outcome | Reason |
| ---: | --- | ---: | --- | ---: | ---: | --- | --- |
|  | No current production R036 findings |  |  |  |  |  |  |

## Current Branch Production Status

- Production R036 code path changed: YES
- Fixed threshold as production decision rule: retired
- Current production findings: 0
- Email sent: NO
- Drive upload performed: NO
- Merged: NO
- Deployed: NO

## Artifacts

- Detail JSON: `docs/status/r036_page_relative_spacing_experiment_20260916.json`
- Ground truth JSON: `data/evaluation/r036_ester_false_positive_ground_truth_20260916.json`
