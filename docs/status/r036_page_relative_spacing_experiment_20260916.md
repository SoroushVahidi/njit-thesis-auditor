# R036 Page-Relative Spacing Experiment (2026-09-16)

> **Production design (2026-09-16):** the reliable parts of this diagnostic
> work have been productionized. See
> `r036_production_page_relative_suppression_design_20260916.md` for the
> selected production policy (suppress/abstain only, with the fixed 1.6 ratio
> retired as the decisive reporting rule and a disabled strong multi-signal
> reporting gate retained for future enablement once a real true positive is
> validated).

This is a diagnostic experiment only. Production R036 behavior is unchanged.

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

| Model | All diagnostic anomalies | Current 1.6 findings remaining | Abstentions | Suppressed |
| --- | ---: | ---: | ---: | ---: |
| Model A - Median-relative ratio | 2 | 2 | 28 | 418 |
| Model B - Robust z-score | 29 | 14 | 28 | 391 |
| Model C - Lower-tail percentile | 44 | 13 | 28 | 376 |
| Model D - Two-mode clustering | 1 | 1 | 28 | 419 |
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

## 18 Unrepresented-Finding Diagnostic Table

The prior audit supplied the authoritative 31/47/18 coverage counts. This script also records a reproducible signature-based approximation; if that approximation differs, use the authoritative audit count for review-planning language.

| # | Document | Page | Section | Pair | Ratio | Diagnostic Outcome | Reason |
| ---: | --- | ---: | --- | ---: | ---: | --- | --- |
| 1 | Muyeed | 10 | TOC | 21 | 1.24 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 2 | Muyeed | 12 | TOC | 7 | 1.24 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 3 | Muyeed | 12 | TOC | 8 | 1.24 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 4 | Muyeed | 12 | TOC | 9 | 1.11 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 0.89 is consistent with local rhythm |
| 5 | Muyeed | 12 | TOC | 10 | 1.38 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.11 is consistent with local rhythm |
| 6 | Muyeed | 14 | TOC | 0 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 7 | Muyeed | 14 | TOC | 2 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 8 | Muyeed | 14 | TOC | 3 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 9 | Muyeed | 14 | TOC | 5 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 10 | Muyeed | 14 | TOC | 6 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 11 | Muyeed | 14 | TOC | 7 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 12 | Muyeed | 14 | TOC | 8 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 13 | Muyeed | 14 | TOC | 9 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 14 | Muyeed | 14 | TOC | 11 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 15 | Muyeed | 14 | TOC | 12 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 16 | Muyeed | 14 | TOC | 13 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 17 | Muyeed | 14 | TOC | 14 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |
| 18 | Muyeed | 14 | TOC | 16 | 1.34 | SUPPRESSED_AS_NORMAL_PAGE_RHYTHM | gap/nearby median ratio 1.00 is consistent with local rhythm |

## Production Status

- Production R036 code path changed: NO
- Current fixed threshold: 1.6
- Current production findings: 96
- Email sent: NO
- Drive upload performed: NO
- Merged: NO
- Deployed: NO

## Artifacts

- Detail JSON: `docs/status/r036_page_relative_spacing_experiment_20260916.json`
- Ground truth JSON: `data/evaluation/r036_ester_false_positive_ground_truth_20260916.json`
