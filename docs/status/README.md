# Project Status Documentation

**Start here:** [CURRENT_STATUS.md](CURRENT_STATUS.md) — its first section is the dated current
SHA, validation, and next-task snapshot; later sections preserve historical snapshots.
This replaces `current_project_state_and_next_steps.md` as the entry
point; that file (and `open_pr_triage.md`, `live_deployment_checklist.md`) are now historical
archives — each has a banner at the top pointing here. See also the top-level
[../ROADMAP.md](../ROADMAP.md), [../RULE_ARCHITECTURE.md](../RULE_ARCHITECTURE.md),
[../EVALUATION_DATA.md](../EVALUATION_DATA.md), and [../DEPLOYMENT.md](../DEPLOYMENT.md).

When recording a new dated status snapshot, update **both** `CURRENT_STATUS.md`
and the snapshot fields in `data/processed/evaluation_data_manifest.json`
(`main_commit_used_for_status_snapshot`, `pytest_count_used_for_status_snapshot`,
and `pytest_skips_used_for_status_snapshot`) in the same change. Use an observed
commit and validation result; do not predict a future squash-merge SHA or add a
documentation-only commit merely to chase it. The count fields record passes
and skips separately. Optionally set `NJITA_STRICT_STATUS_DRIFT=1` locally to
compare their sum against a fresh `pytest --collect-only` inventory.

This is not the first pass at this problem — [repo_polish_inventory.md](repo_polish_inventory.md)
(2026-07-03) identified the same staleness pattern. Keep the leading snapshot
of `CURRENT_STATUS.md` current and dated; preserve the later sections as
historical records.

| Topic | Document |
|---|---|
| Open PR triage and merge order (historical; see CURRENT_STATUS.md for current) | [open_pr_triage.md](open_pr_triage.md) |
| Ester feedback language source of truth | [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) |
| Ester language alignment audit (pre-implementation) | [ester_language_alignment_audit.md](ester_language_alignment_audit.md) |
| Ester current wording inventory | [ester_current_wording_inventory.md](ester_current_wording_inventory.md) |
| Ester next wording slice plan | [ester_next_wording_slice_plan.md](ester_next_wording_slice_plan.md) |
| Ester wording alignment checkpoint (Slices 1–6 complete) | [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md) |
| P021/P026 policy review questions (word-count limits, accepted fonts) | [ester_policy_review_p021_p026.md](ester_policy_review_p021_p026.md) |
| Broad Ester-style presentation-split plan (P014/P015/P017/P018/P019/P020/P024/P025/P027) | [ester_broad_presentation_split_plan.md](ester_broad_presentation_split_plan.md) |
| Broad-rule atomic mapping (issue_type → Ester-style card, implementation-ready) | [ester_broad_rule_atomic_mapping.md](ester_broad_rule_atomic_mapping.md) |
| Student-facing presentation cleanup plan (sorting, confidence/priority labels, highlight quality) | [student_facing_presentation_cleanup_plan.md](student_facing_presentation_cleanup_plan.md) |
| Highlight quality improvement plan (table/list/figure region highlighting) | [highlight_quality_improvement_plan.md](highlight_quality_improvement_plan.md) |
| Current consistency audit vs. latest available Ester files (wording + behavior) | [ester_current_consistency_audit.md](ester_current_consistency_audit.md) |
| Repository polish inventory (baseline, cleanup issues, recommended sequence) | [repo_polish_inventory.md](repo_polish_inventory.md) |
| Ester Q → P → public rule cards | [ester_q_p_rule_public_rule_mapping.md](ester_q_p_rule_public_rule_mapping.md) |
| Live server deploy / verify | [live_deployment_checklist.md](live_deployment_checklist.md) |
| Validated high-confidence warning examples (manual review, no change needed) | [high_confidence_warning_review_validated_examples.md](high_confidence_warning_review_validated_examples.md) |
| Evaluation data index | [evaluation_data_manifest.md](evaluation_data_manifest.md) |
| Data inventory | [data_inventory_and_evaluation_sources.md](data_inventory_and_evaluation_sources.md) |

Older dated audits below the "Historical" sections in `current_project_state_and_next_steps.md`
are preserved for milestone context — they are **not** current status.

The [Linux desktop validation record (2026-10-16)](../implementation/history/offline_desktop_linux_validation_20261016.md) preserves the earlier candidate evidence; use the [rc.3 release record](../releases/windows-0.2.0-rc.3.md) for the published Windows beta.
