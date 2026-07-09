# Ester Sample B Feedback Audit

**Recorded:** 2026-07-08  
**Branch:** `fix/ester-sample-a-correctness-pass1`  
**Current base at record time:** `main` after PR #481 merge (`32952f2`)

## Scope

This is a planning / source-of-truth audit for the newest Sample B feedback, with the goal of
separating:

- what PR #481 already fixed in presentation / wording,
- what PR #482 is intended to fix in detector / highlight behavior, and
- what still needs a separate follow-up pass.

## Source availability

- `Sample B Feedback.docx` was **not present in the repo tree** / accessible from the coding
  environment, so this audit does **not** claim to have reproduced Ester's exact document text.
- The audit is grounded in:
  - `docs/status/ester_email_alignment_audit.md`
  - `docs/status/ester_sample_a_correctness_pass1.md`
  - `data/specs/ester_warning_wording_map.json`
  - `data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx`
  - `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf` (built-in Sample B fixture)
  - the current detector / report output on built-in `ester_sample_b`

## Built-in Sample B snapshot

The built-in `ester_sample_b` fixture currently reproduces as **63 student-facing problems**:

- `P011` 33
- `P015` 13
- `P019` 3
- `P013` 2
- `P020` 2
- `P023` 1
- `P028` 2
- `P038` 1
- `P051` 1

This snapshot is useful for regression tracking, but it is not a substitute for the missing
`Sample B Feedback.docx`.

## Sample B concern matrix

| Sample B item | Rule ID | Page | Ester's judgment | PR #481 resolves? | PR #482 resolves? | Still needs new work? | Recommended next fix |
|---|---|---:|---|---|---|---|---|
| SB-01 | P011 | 1 | false positive | no | no | yes | Tighten margin noise filtering so page-number / crop-box / artifact cases do not count as margin violations. |
| SB-02 | P011 | 24 | false positive | no | no | yes | Same P011 artifact/noise distinction; preserve strict text/table/figure margin policy. |
| SB-03 | P011 | 39 | false positive | no | no | yes | Same P011 artifact/noise distinction; avoid loosening the rule globally. |
| SB-04 | P015 | 23, 24, 26 | false positive | no | yes | maybe | Keep the detector conservative around continuation lines and paragraph-internal text; regression should lock out mid-paragraph highlights. |
| SB-05 | P015 | 27, 38 | false positive | no | yes | maybe | Exclude section-opening sentences / code-like blocks from normal body-indent checks. |
| SB-06 | P013 / P028 | 10, 11 | incorrect highlight / false positive | no | partial | yes | Prefer the real bottom-center page-number candidate and ignore TOC/list/body-number decoys. |
| SB-07 | P019 | 57, 58 | false positive / wrong numbering style | no | partial | yes | Separate page-number style from numbering-regime checks and keep the exact page-number highlight on the number itself. |
| SB-08 | P019 | document-level | incorrect no-highlight handling | no | no | yes | Surface document-level numbering issues honestly, but do not silently omit them when no page anchor exists. |
| SB-09 | P038 | 9 | false positive | no | no | yes | Keep front-matter heading detection explicit and do not treat `ACKNOWLEDGEMENTS` as missing when the heading is present / variant-matched. |
| SB-10 | P023 | 82 | category / wording issue | no | no | yes | Keep the rule scoped to body spacing and preserve the Ester exception list: tables, figure descriptions, bullets, and multi-line titles. |
| SB-11 | P020 | 71 | incorrect remediation specificity | no | no | yes | Use the specific Google Sheet wording for the heading-level question/remediation instead of generic capitalization advice. |
| SB-12 | P020 | 80 | table-title vs figure-caption specificity | no | no | yes | Keep table-title wording separate from figure-caption wording; do not cross-wire the remediations. |
| SB-13 | UI / report layout | n/a | duplicate section display | no | no | yes | Remove the duplicate `Spacing blank lines` presentation so the report does not repeat the same information. |
| SB-14 | P063 | 5 | incorrect highlight / font formatting | no | no | yes | Recheck font extraction / tolerance / highlight targeting against the actual page-5 content before any detector tuning. |
| SB-15 | P051 | 4 | correct feedback, wrong category label | no | no | yes | Rename the category to `COPYRIGHT PAGE` so the student-facing taxonomy matches Ester's page framing. |

## What is already covered

- PR #481 already fixed the student-facing wording and fallback-remediation source of truth.
- PR #482 is the right branch for detector / highlight stabilization, especially P015 and the
  page-number family.
- The current Sample A correctness doc remains the better template for conservative detector
  changes and regression coverage.

## What remains unresolved

- P011 margin false positives on Sample B pages 1, 24, and 39.
- P038 front-matter heading handling and honest no-highlight behavior.
- P023 spacing / figure-description exception handling.
- P020 table-title and heading-level specificity.
- Duplicate section presentation.
- P063 font-formatting / highlight targeting.
- P051 category labeling.

## Safest next implementation branch

Keep `fix/ester-sample-a-correctness-pass1` draft until it is retargeted onto `main`, then make
the next pass narrowly focus on:

1. P015 indentation false positives.
2. P013 / P028 / P019 page-number highlighting and candidate selection.
3. P038 visibility / no-highlight handling only if it can be proven safely.

Leave P011, P023, P020, P063, and P051 category cleanup for separate, smaller passes unless
reproducible evidence shows one of those can be fixed with a very low-risk change.
