# R036 Evaluation Package Provenance (2026-09-25)

The archival tags below preserve the exact historical commits that generated
three Ester validation packages. The package artifacts remain available only
inside those historical commits; no private PDF or spreadsheet has been copied
into current `main`. Current `main` preserves the operational R036 result and
the reviewer ground-truth summary separately.

| Original branch | Original commit | Archival tag | Historical package files | Purpose and durable reviewer-result context | Retirement readiness |
| --- | --- | --- | --- | --- | --- |
| `evaluation/r036-praneeth-all-examples-20260912` | `0c7770a15db7b763247d508b400009a69d28d197` | `archive/r036-praneeth-all-examples-20260912` | `R036_Praneeth_Page11_All_Examples.pdf`, `R036_Praneeth_Page11_All_Examples.xlsx`, `scripts/ester_batch/build_r036_praneeth_multi_example_package.py`, `tests/test_r036_praneeth_multi_example_package.py` | All 12 selected Praneeth page-11 examples were adjudicated false positives. The 12 labels are in the current ground-truth record. | Ready after this provenance record is merged. |
| `evaluation/r036-remaining-findings-ester-validation-20260914` | `92f095a083d401a9413f2183cb6ecd067c1d7e2d` | `archive/r036-remaining-findings-validation-20260914` | `R036_Remaining_Findings_Validation_20260914.pdf`, `R036_Remaining_Findings_Validation_20260914.xlsx`, `scripts/ester_batch/build_r036_remaining_findings_validation_package.py`, `tests/test_r036_remaining_findings_validation_package.py` | Preserves the remaining-findings validation package generation. The consolidated current R036 record documents 24 Ester-confirmed false positives and no confirmed true positives; it does not infer classifications beyond its recorded labels. | Ready after this provenance record is merged. |
| `evaluation/r036-post-recovery-ester-validation-20260914` | `92197d57aeca820fe1496d1ad7ae42bf0a322662` | `archive/r036-post-recovery-validation-20260914` | `R036_PostRecovery_Remaining_Findings_Validation_20260914.pdf`, `R036_PostRecovery_Remaining_Findings_Validation_20260914.xlsx`, `docs/status/r036_post_recovery_remaining_findings_inventory_20260914.json`, `docs/status/r036_post_recovery_validation_package_20260914.md`, `scripts/ester_batch/build_r036_post_recovery_validation_package.py`, `tests/test_r036_post_recovery_validation_package.py` | Preserves the 96-finding inventory and selected 12-example package record. The adjudicated selected examples are represented in the current ground-truth record. | Ready after this provenance record is merged. |

Current durable evidence:

- [R036 current state](CURRENT_STATUS.md#r036-current-state) records the policy, 24 known false positives, zero confirmed true positives, and conservative production behavior.
- [Production suppression design](r036_production_page_relative_suppression_design_20260916.md) records the decision and validation results.
- [Ester false-positive ground truth](../../data/evaluation/r036_ester_false_positive_ground_truth_20260916.json) contains the 24 reviewed labels and explicitly does not infer true positives.

These tags preserve package-generation history and artifacts that are not in
current `main`; current `main` retains the operational result, engineering
rationale, and reviewer-ground-truth summary. Once this metadata record is
merged, the three evaluation branches can be retired without losing those
package commits or their recorded provenance.
