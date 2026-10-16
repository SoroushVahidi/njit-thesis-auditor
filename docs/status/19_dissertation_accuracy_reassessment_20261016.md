# Nineteen dissertation accuracy reassessment — 2026-10-16

## Scope and provenance

This audit used the authorized local 19-PDF manifest and hash-checked all 19 source files. No dissertation, reviewer attachment, raw finding report, or private ledger was added to Git. Private aggregate inputs and run logs are under the repository's ignored `.accuracy-runs/20261016T045523Z` directory (mode 0700). The isolated branch began at `4efd780dde53eea907a714df8bfed86e923ef86a`; the validated engineering change ended at `8dd3b653f83f622dfd15e5e3611cf08967d1cfb8`. The historical report was generated at `14856250ce2aaf7a38610a086e8f5250a92655bf`. The final documentation commit is recorded in the local `FINAL_REPORT.md` and branch history.

The historical manifest lists 63 applicable rule IDs, including experimental P082; the default reevaluation kept P082 disabled, leaving 62 default-enabled IDs. Thirty internal rules emitted findings. Historical 4,545 raw and 1,682 student-visible findings were reproduced from the saved 19 reports. The current-tree run produced 4,517 raw and 1,646 visible findings with zero detector failures. Raw includes 2,103 P013 inventory rows and 19 P012 internal-summary rows, so raw volume is not an error count. The different commits and report filtering account for a changed result set; a lower count alone proves no accuracy gain.

## Distribution

| Internal rule | Historical raw / visible | Current raw / visible |
|---|---:|---:|
| P011 | 260 / 250 | 260 / 249 |
| P012 | 562 / 9 | 562 / 9 |
| P013 | 2131 / 9 | 2131 / 2 |
| P015 | 21 / 21 | 18 / 18 |
| P017 | 8 / 8 | 8 / 8 |
| P018 | 51 / 51 | 52 / 52 |
| P019 | 3 / 3 | 3 / 3 |
| P020 | 3 / 3 | 3 / 3 |
| P023 | 5 / 5 | 5 / 5 |
| P024 | 480 / 480 | 480 / 480 |
| P026 | 196 / 18 | 196 / 18 |
| P027 | 77 / 77 | 77 / 77 |
| P029 | 13 / 13 | 13 / 13 |
| P032 | 2 / 2 | 2 / 2 |
| P035 | 2 / 2 | 2 / 2 |
| P037 | 4 / 4 | 4 / 4 |
| P039 | 3 / 3 | 3 / 3 |
| P040 | 19 / 19 | 19 / 19 |
| P044 | 1 / 1 | 1 / 1 |
| P045 | 4 / 4 | 2 / 2 |
| P049 | 2 / 2 | 0 / 0 |
| P051 | 3 / 3 | 3 / 3 |
| P053 | 10 / 10 | 10 / 10 |
| P054 | 2 / 2 | 1 / 1 |
| P055 | 549 / 549 | 529 / 529 |
| P063 | 2 / 2 | 2 / 2 |
| P075 | 9 / 9 | 8 / 8 |
| P078 | 1 / 1 | 1 / 1 |
| P084 | 1 / 1 | 1 / 1 |
| P085 | 1 / 1 | 1 / 1 |
| P086 | 120 / 120 | 120 / 120 |

| Anonymous sample | Raw | Visible | Peak visible on one physical page |
|---|---:|---:|---:|
| sample_01 | 92 | 20 | 8 |
| sample_02 | 91 | 35 | 15 |
| sample_03 | 313 | 122 | 24 |
| sample_04 | 285 | 63 | 29 |
| sample_05 | 210 | 37 | 27 |
| sample_06 | 282 | 114 | 21 |
| sample_07 | 217 | 113 | 21 |
| sample_08 | 429 | 183 | 18 |
| sample_09 | 90 | 8 | 2 |
| sample_10 | 399 | 115 | 22 |
| sample_11 | 205 | 80 | 18 |
| sample_12 | 422 | 148 | 27 |
| sample_13 | 198 | 60 | 20 |
| sample_14 | 360 | 163 | 41 |
| sample_15 | 188 | 100 | 30 |
| sample_16 | 226 | 49 | 27 |
| sample_17 | 241 | 128 | 25 |
| sample_18 | 31 | 6 | 2 |
| sample_19 | 238 | 102 | 36 |

The largest current visible issue groups are P055 missing Figure prefix (383), P024 List of Figures title case (378), P011 margin boundary (249), P055 missing Table prefix (146), and P086 bold unnumbered heading (120). These are concentrations for review, not false-positive counts. The maximum within one document/page was 41 findings. P024 and P055 co-occur on 52 document-pages, but their checks concern different features. A strict key of document, rule, issue, page, entry index, bbox, and side found zero duplicate excess. This does not exclude semantic overlap. One P019 visible item lacks a physical-page indicator in both saved runs.

Across 490 document-page instances with a page indicator, 330 had one visible finding, 103 had two to five, 12 had six to ten, 23 had 11 to 20, and 22 had 21 or more. This is a page-level concentration measure, not a count of distinct violations.

The private `distribution_summary.json` in the run directory preserves all 49 rule/issue groups and the anonymous per-document/physical-page counts for targeted follow-up without placing source identifiers or dissertation text in Git.

Current visible confidence metadata is high 221, medium 803, low 45, absent 577. The 577 absent values mainly reflect rules that do not emit this field; they must not be interpreted as low confidence. Before the fix, 541 visible findings lacked geometry, including all 529 P055 findings. After the fix, 12 lack geometry: P075 eight, P019 two, P078 one, and P084 one. Absence of geometry for those rules is a review item, not by itself proof of wrong highlights.

## Authority and case reconciliation

The direct review ledger contains 51 case rows: 46 current false-positive adjudications, four current true-violation adjudications, and one historical clarification case without a current adjudication. Read-only replay from the saved 19-document reports against the ledger's exact case locators passed all 50 current adjudications on both trees: zero reviewed FPs remaining, zero reviewed TPs missing, and zero identity ambiguities. The separate private 136-case reviewer manifest contains 111 FP, 20 TP, and five reviewer-violation checks. These are distinct evidence sets and must not be added together as unique judgments. The local spreadsheet, reviewer-source, and ledger inventories are available; the ledger, dated [authority matrix](ester_authority_matrix.md), [current status](CURRENT_STATUS.md), and reviewer replay were the structured authorities used here. A dated matrix row can be stale where its current pointer records later direct answers. New corpus rows without a direct judgment remain `UNREVIEWED_ENGINEERING_DEBT`, even if a similar case has been corrected. A generalization from a direct decision is `DERIVED_ENGINEERING_AUTHORITY` or `ENGINEERING_EQUIVALENCE`, not a new direct verdict.

- **R011/P011:** Eight direct false positives remain absent, and one direct true violation remains present under the ledger's case locators. The present run has 249 visible findings. The previous outdented-reference-label exception is a derived policy application; further final-line allowances still require evidence. No new threshold was inferred from the count.
- **R015/P015:** All four direct false positives remain absent and the direct true violation remains present under exact ledger locators. One FP and the TP share a page and issue category: coarse page matching misleadingly suggests an FP regression, while the case-locator replay distinguishes their anchors. The 18 current findings were left unchanged.
- **R026/P026:** One direct FP is absent at page/issue. The 18 visible font findings are medium confidence and otherwise unreviewed here; accepted font equivalences in the authority history do not justify suppressing every similar-looking case.
- **R036/P036:** Two direct case-specific FPs exist in the ledger; current corpus output is zero. The later authority pointer describes a more specific spacing policy, but zero output gives no corpus-level sensitivity evidence. A genuine positive fixture and future reviewer case are needed before changing policy.
- **R049/P049:** Historical two visible findings are absent on this tree, and the direct ledger has no R049 case. Treat the difference as unreviewed until its locations and detector history are adjudicated.
- **R055/P055:** The current authority pointer records the direct prefix requirement. Its 529 current findings all lacked stored geometry. This was a demonstrable presentation defect, regardless of whether any individual warning is a true violation. P086 remains evidence-limited and P082 stays opt-in; neither was enabled or tuned.

The repository label vocabulary is `true_positive`, `false_positive`, `false_negative`, `correct_but_too_strict`, `wrong_location`, `wrong_highlight`, `wrong_wording`, `duplicate`, and `policy_decision_needed`. This run confirms the R055 *missing highlight geometry* defect with synthetic tests and corpus output; it does not assign new reviewer truth labels to private findings. There is no independently established new corpus false negative, wording error, or policy decision. Private communications not represented by the accessible local records were not checked, and the raw attachments were not exhaustively re-adjudicated.

## Engineering change and before/after evidence

`src/njit_auditor/rules/pdf_lot_lof_entry_type.py` now serializes the already-extracted offending entry line bbox for all four P055 issue branches, using the same formatter as sibling TOC rules. No detector gate, rule ID, threshold, wording, guideline, or canonical JSON changed. A four-case synthetic regression in `tests/test_rules/test_r055.py` failed before the patch and passes after it; it checks all branch types, drawable geometry, and the offending row coordinates.

A fresh 19/19 hash-verified patched audit had 4,517 raw and 1,646 visible findings with zero detector failures. A full JSON comparison found 3,988 structurally identical finding records and exactly 529 records differing only by a new P055 bbox: 383 missing Figure prefix and 146 missing Table prefix. All 529 boxes parse as drawable and retain visible area inside the corresponding physical PDF page bounds. Visible geometry coverage therefore rose from 1,105/1,646 to 1,634/1,646. This verifies presence and geometric visibility, not a human visual judgment on every PDF. The 136-case reviewer replay passed with zero missing targets and zero unexpected removals when compared with the exact unpatched current-tree replay. The direct-ledger read-only replay independently preserved all 50 current adjudications.

The historical-to-current replay, before this patch, passed 136/136 case checks but reported 13 unexpected removals (12 P055 and one P045). Those are pre-existing cross-commit changes and are not silently credited to this fix. The broader 19-report comparison found 191 historical-only and 155 current-only identity rows, including many P055 entry-index or geometry-identity shifts; their counts are not independent adjudications. They remain candidates for targeted review.

## Validation and reproducibility

Run commands from this worktree, with private arguments held in the local run directory:

```text
python -m pip install -e ".[dev]"                 # exit 0, baseline tree
ruff check .                                        # exit 0, candidate tree
mypy src                                            # exit 0, candidate tree
python -m pytest -q tests/test_rules/test_r055.py tests/test_r055_lof_segmentation.py
                                                    # 17 passed, exit 0
python -m pytest -q tests/test_highlight_target_baseline.py tests/test_highlight_pdf_student_routes.py tests/test_rules/test_r055.py tests/test_r055_lof_segmentation.py
                                                    # 40 passed, exit 0
PYTHONPATH=<private-plugin>:src LIVENESS_OUT=<private-run>/liveness_final.json python -m pytest -q -p liveness_plugin
                                                    # 4,767 passed, 6 skipped, exit 0
PYTHONPATH=src python <private-run>/reevaluate_patched.py
                                                    # 19/19, exit 0
PYTHONPATH=src python <private-run>/check_p055_geometry.py
                                                    # 3,988 unchanged; 529 valid added boxes, exit 0
PYTHONPATH=src python <private-run>/check_p055_page_visibility.py
                                                    # 529 within physical page bounds, exit 0
python <private-run>/summarize_distribution.py      # 49 rule/issue groups, exit 0
PYTHONPATH=src python scripts/ester_judgment_replay.py --manifest <private-manifest> --output-dir <private-output> --baseline-dir <unpatched-current-output> --liveness <private-liveness>
                                                    # 136/136, zero unexpected removals, exit 0
PYTHONPATH=src python <private-run>/replay_saved_ledger.py
                                                    # 50/50 direct cases on both trees, exit 0
```

The first changed-tree full suite had 4,766 passes, six skips, and one failure: an existing synthetic privacy test's metadata allowlist did not include bbox. That test now permits numeric geometry while still rejecting copied entry text; its focused rerun passed, and the final full suite passed as shown above. The unpatched-tree full suite had 4,763 passed and six skipped, with Ruff, Mypy, and installation all exiting zero. Its historical-baseline reviewer replay exited one solely because of the 13 unexpected removals described above. Private logs, per-document reports, corpus hashes, and full command arguments remain in the run directory. Independent human visual review of all 529 new highlights was unavailable; the code review here was limited to the changed detector and tests.

## Next actions

Review the 13 historical-to-current removals at exact target level, especially the prior P055 entry segmentation changes; distinguish genuine fixed false positives from missed true violations. Keep exact case locators in future R015 replay so a same-page FP and TP are not conflated. Use fresh independent judgments for the highest-volume P024/P055/P086 concentrations, the remaining R026 font findings, and any suspected semantic duplicates. Investigate the 12 remaining geometry-free findings by rule and determine which require a drawn highlight. Existing reading-frame ambiguity remains a separate evidence gap. Preserve P082 opt-in status and avoid R086 tuning until direct evidence supports it; request new reviewer policy only after an exact case reveals a genuinely unanswered rule.
