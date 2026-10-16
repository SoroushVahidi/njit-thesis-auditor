# Autonomous branch integration review — 2026-10-16

## Scope and starting state

This was an independent, local review of two audit branches and a private historical replay. No dissertation, raw finding report, reviewer attachment, private ledger, or private source text is in this report or the proposed PRs. Detailed evidence remains in the ignored private integration run directory. No merge, deployment, distribution, reviewer contact, or shared ledger edit was performed.

| Ref at review start | Verified SHA and state |
| --- | --- |
| `origin/main` | `4efd780dde53eea907a714df8bfed86e923ef86a` |
| PR #620, `feature/offline-desktop-auditor-20261015` | Open, non-draft, head `ae0d00be4f5dfd5ac574912a001dffced69a9181` |
| Offline audit branch | `21f9e45445d69dd219d7cd6c95efc5b22c13ca4a` |
| R055 accuracy audit branch | `0e75f142d4f70b9210cce3c1882295a39e9f1660` |
| Coordination branch | Clean at the same commit as `origin/main` |

PR #620 had no reported status checks on its final head. Its earlier CI run on `7f6b165bd85f012e84346a36f392c029afd11afe` had three jobs that never started: GitHub reported an account payment or spending-limit block, with no test steps or logs. This is an infrastructure failure, not a passing or failing test result.

## Decisions

| Track | Verdict | Reason |
| --- | --- | --- |
| Offline code integration | **CONDITIONAL GO for one draft stacked PR** | A linked lock-file write was reproduced and fixed on a separate review branch. Source and clean Linux package checks pass; the native Windows release gate remains open. |
| Windows distribution | **NO-GO** | No genuine Windows x64 build, packaged browser/storage/ACL/network smoke, or native lifecycle evidence exists for the final source. |
| R055 geometry integration | **GO for one separate draft PR** | The change only adds existing entry geometry to finding metadata. Synthetic route checks, 19-document differential, and reviewer replay show stable detection counts. Human visual review of every corpus box remains a limit. |
| Historical removal reconciliation | **CONDITIONAL GO for engineering accounting** | The replay's 13 rows are cardinality leftovers, not 13 reliably identified physical targets. Row-level rematching found no lost warned parent entry, but individual reviewer labels and six newly surfaced P055 targets remain unreviewed. |

Draft PRs: [offline review #621](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/621), stacked on PR #620's feature branch at `c4ad543316f9a5a464586987905785636592b953`; [R055 review #622](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/622), targeting main at `19fa8f7cf27c3e6287f98bd7a51c653825f6894a`. Both were verified open and draft.

## Offline branch review and correction

The branch after PR #620 guards linked `audits/` and `tmp/` roots and child junctions, rejects linked JSON/Markdown/text report downloads including loops, and redacts job IDs and exception messages from combined-report and highlight failure logs. I reviewed the route table, ticket/cookie, Host/Origin/CSRF gate, upload/deletion and shutdown paths, package spec, and source parity tests. Synthetic auth and malformed/encrypted/URI-link tests cover the tested paths. The prior audit's broad development-environment bundle (7,987 files, 5.4 GB) remains unsuitable for distribution.

An independent adversarial check found a new linked-file boundary defect: `desktop.lock` could be a symlink to an empty file outside the application directory. Opening it in append mode wrote one byte outside before locking. The isolated review branch `review/offline-desktop-integration-20261016` refuses a linked or reparse-point lock file before opening it and adds a sentinel regression and a native Windows smoke step. Final review SHA: `c4ad543316f9a5a464586987905785636592b953`. This guard does not claim safety against a hostile same-user process racing filesystem changes.

The clean pinned Linux one-folder package built from the review source has 118 regular files, occupies 132 MB, and has launcher SHA-256 `600051ca4c4b50b3b3f909b79bf2b74cc330072b8a3aa574fec752dc6ac4f9ed`. Actual packaged synthetic smoke passed ticket login, upload, JSON/Markdown/text/combined PDF and highlighted/original PDF routes, sorting, linked-report denial with outside sentinel intact, two distinct concurrent jobs, deletion, Quit, empty `audits/` and `tmp/` on exit, and refusal of a linked lock file without writing its outside target. The traced packaged process bound only `127.0.0.1` and made zero `connect()` calls in this run. Bundle filenames and recursive archive names contained no known private sample, raw-data, review-ledger, credential, or cloud SDK names; this name inspection is not a byte-level confidentiality proof. This Linux result does not substitute for native Windows evidence. A real browser filter pass, eight-hour expiry, 30-minute idle shutdown, native ACLs and packet capture remain untested on the final package.

## R055 geometry review

The R055 branch adds `details["bbox"]` from the already extracted offending entry line in all four List of Tables/List of Figures issue branches. It changes no detection gate, threshold, rule ID, wording, canonical rule JSON, or input PDF. The new review test uses a synthetic rotated page with repeated and wrapped entries. It checks distinct target boxes and actual annotations through both the one-page student route and full highlighted PDF route. A correct-prefixed row stays unflagged. The added numeric box carries no copied entry text.

A fresh hash-checked 19/19 audit at the review source produced 4,517 raw and 1,646 student-visible findings with zero detector failures, matching the unpatched current tree. A record-level comparison found 3,988 records unchanged and exactly 529 P055 records changed only by adding a drawable box: 383 missing Figure prefix and 146 missing Table prefix. All 529 boxes retained visible area within their physical page bounds. The 136-case private reviewer replay passed 136/136 with zero unexpected removals against the exact unpatched current-tree baseline. These checks verify geometry and detection stability; they do not establish improved detector precision or recall, and they are not a human visual adjudication of all 529 boxes.

## Exact 13-row replay matrix and its identity limit

The **13 replay outputs** compare a saved nine-document web replay from `b891e7acc1ed071092ec57afbc348508333ad0bd` with a hash-checked current web replay from `4efd780dde53eea907a714df8bfed86e923ef86a`. They use the same private 136-case manifest, source paths and source SHA-256 values, and default web-audit path without a user rule override. The old run has no complete environment/config snapshot, so runtime parity beyond these facts cannot be proven. The separate 19-document historical report at `14856250ce2aaf7a38610a086e8f5250a92655bf` is **not** the baseline that generated these 13 rows. Source SHA-256 prefixes are `sample_01=1c3412857860`, `sample_03=234f6c951a2a`, and `sample_11=ba4e365aa265`; full hashes and PDF paths remain private.

`F` means `P055 / lof_entry_missing_figure_prefix`; `B` means `P045 / biosketch_publication_entry_spacing_not_double`. Entry indices are structural parser indices, not PDF text. **"Unresolved" below means no direct case-level reviewer truth label; the row's continued emission is verified.** Each row was traced through the saved raw finding ID, the old and current parser entries, page position, and the local source hash.

| Replay row | Anonymous sample | Issue / physical page | Old entry → current entry | Classification and confidence | Responsible change and exact authority |
| ---: | --- | --- | --- | --- | --- |
| 1 | sample_11 | F / 19 | 68 → 64, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9` entry segmentation; R055 policy `R055@email:2026-09-04`, no case judgment |
| 2 | sample_11 | F / 21 | 108 → parent 95 | **Legitimate FP correction** of duplicate continuation warning, **high** engineering confidence | `dccd1b9`; same R055 policy, no case judgment |
| 3 | sample_01 | F / 9 | 23 → parent 13 | **Legitimate FP correction** of duplicate continuation warning, **high** engineering confidence | `dccd1b9`; same R055 policy, no case judgment |
| 4 | sample_01 | F / 9 | 26 → parent 13 | **Legitimate FP correction** of duplicate continuation warning, **high** engineering confidence | `dccd1b9`; same R055 policy, no case judgment |
| 5 | sample_01 | F / 9 | 27 → 14, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 6 | sample_01 | F / 10 | 43 → 21, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 7 | sample_01 | F / 10 | 44 → 22, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 8 | sample_01 | F / 10 | 45 → 23, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 9 | sample_01 | F / 10 | 46 → 24, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 10 | sample_01 | F / 10 | 47 → 25, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 11 | sample_01 | F / 11 | 65 → 38, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 12 | sample_01 | F / 11 | 66 → 39, same row | **Unresolved** case truth; apparent-only removal, **high** row-match confidence | `dccd1b9`; same R055 policy, no case judgment |
| 13 | sample_03 | B / 6 | 1 → absent | **Legitimate FP correction**, **high** geometric confidence | `8d4afaa` baseline-step measurement; Q028 blank-line requirement, no case judgment |

For row 13, the old bbox-edge method measured 21.387 points across the entry boundary against a 21.669-point required pitch and warned. The current span-origin baseline measures 24.409 points against the same requirement, so the blank-line criterion is satisfied. The old row's unusual glyph height accounts for the difference. This is an engineering false-positive classification, not an attributed Ester judgment.

The replay matcher compares P055 cards by rule, page and issue when both lack boxes; card entry details are unavailable, so bipartite matching assigns arbitrary same-page rows and labels leftovers "removed." A direct match by extracted physical row found **17 old-only P055 continuation fragments**, each fully enclosed in a currently warned parent entry box, and **six current-only P055 warned targets**. Net P055 change is minus 11; the replay lists 12 positive page-level deficits because an added target on another page does not offset a deficit. Thus the 13 listed outputs are fully accounted for as replay rows, but they are not 13 exact physical removals. The six additions have no direct case-level judgment and were not tuned here. No true-violation regression was verified, and no detector fix was made as part of this reconciliation.

The R055 authority is the owner-reported 2026-09-04 Ester email recorded in `docs/status/r055_ester_email_policy_20260904.md`: a rule-wide prefix requirement with no case locator. The live R055 workbook rows say only that there was no then-current auditor finding; that is not an Ester false-positive or true-positive judgment. The R045 authority is Q028's spacing requirement plus the current authority pointer recording the 2026-10-05 Ester response that within-entry single spacing is mandatory and hanging indent optional. Neither source adjudicates sample_03's exact gap. All row classifications above are independent engineering assessments from private local PDF geometry and saved report data.

## Validation and limitations

| Exact review source | Check | Result |
| --- | --- | --- |
| Offline review SHA `c4ad543316f9a5a464586987905785636592b953` | Editable dev install, Ruff, mypy, 26 offline tests and 218 web tests together | **PASS**, 244 focused tests |
| Same offline SHA | Full pytest | **PASS**, 4,789 passed, 6 skipped |
| Same offline SHA | Clean pinned Linux build, actual packaged smoke, bundle name/TOC inspection | **PASS** with the platform and content-inspection limits above |
| R055 review SHA `19fa8f7cf27c3e6287f98bd7a51c653825f6894a` | Ruff, mypy, highlight/segmentation/route focused suite | **PASS**, 41 tests |
| Same R055 SHA | Fresh 19-document audit, exact JSON differential, physical-page box check, 136-case replay | **PASS**, counts and limits above |
| Same R055 SHA | Full pytest | **PASS**, 4,768 passed, 6 skipped |
| Private supervisor harness | Zero and nonzero worker exits, timeout, interruption, missing DONE, launch exception | **PASS**, six synthetic checks |

Both new PRs' GitHub Actions runs reported failure on Python 3.10, 3.11, and 3.12, but each job had zero steps and an annotation stating that it was not started because of account payment or spending-limit settings. These are blocked infrastructure checks, not executed CI tests. The local full-suite results above were recorded at the exact PR head commits.

The old offline and accuracy supervisors both used `try: sys.exit(main()) / except BaseException`. A successful `main()` returned zero; `sys.exit(0)` raised `SystemExit(0)`, which `BaseException` caught and falsely appended `STATE: FAILED`. Both preserved logs show a worker exit zero and DONE before that misleading fatal line. The new private integration supervisor uses `raise SystemExit(main())` outside an `except Exception` handler. The six private tests exercise its exit and interruption paths without changing either historical run or the live supervisor state.

## Merge and release blockers; next steps

1. Keep both proposed PRs as drafts. The user forbids merges; no production action is authorized. GitHub Actions at PR #620 and the two new draft PRs was blocked before jobs started by account billing/spending limits. Resolve that infrastructure gate and obtain executed CI before considering integration.
2. Before any Windows distribution, build the final offline source on a genuine Windows x64 host and complete the committed native checklist, including browser UI, package contents, ACLs, links/junctions, DNS/packet evidence, concurrency, deletion, expiration and shutdown. Do not distribute the earlier 5.4 GB broad-environment bundle.
3. Correct or supplement the private replay matcher with stable physical anchors before treating its cardinality leftovers as exact findings. Independently adjudicate the six current-only P055 targets and other unreviewed high-volume groups if accuracy claims are needed. Keep this detector work separate from the geometry PR.
4. Review the 12 remaining non-P055 geometry-free current findings by rule. Do not infer detector precision or recall from the added R055 highlights.
