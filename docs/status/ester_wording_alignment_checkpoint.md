# Ester Wording Alignment Checkpoint

> **Purpose:** Summarize the Ester wording-alignment work completed so far and
> define the remaining work safely, so future sessions don't have to
> reconstruct this history from PR archaeology.
>
> **Recorded:** 2026-07-03 (post–PR #420 merge; main @ `3e402604fb91c6e8c6b59b3403928e7fbe59c022`)
>
> **Related:** [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) ·
> [ester_language_alignment_audit.md](ester_language_alignment_audit.md) ·
> [ester_current_wording_inventory.md](ester_current_wording_inventory.md) ·
> [ester_next_wording_slice_plan.md](ester_next_wording_slice_plan.md)

This is a documentation-only checkpoint. It does not change source behavior.

---

## Completed source-of-truth and planning PRs

| PR | Content |
|---|---|
| **#411** | Ester feedback source-of-truth snapshot. |
| **#412** | Ester language alignment audit. |
| **#413** | Current wording inventory. |
| **#416** | Next wording slice plan. |

These PRs are read-only research/planning artifacts — no source, rule, or template changes.

---

## Completed wording implementation slices

| PR | Slice | Rules |
|---|---|---|
| **#414** | Slice 1 | P011, P013, P023, P030, P050 |
| **#415** | Slice 2 | P031, P032, P036, P039, P040, P046, P048, P049 |
| **#417** | Slice 3 | P041, P042, P053, P054, P055, P074, P078 |
| **#418** | Slice 4 | P045, P047, P066, P067, P068 |
| **#419** | Slice 5 | P028, P029 |
| **#420** | Slice 6 | P043, P044 |

For every slice above, changes were **wording/remediation only**. None of these
PRs changed detector thresholds, rule IDs, issue types, grouping keys,
confidence labels, highlight behavior, `src/njit_auditor/rules/`, templates,
or report JSON schema. Slice 5 (P028/P029) and Slice 6 (P043/P044) additionally
preserved pre-existing sensitive presentation logic without modification:
Slice 5 left the P019/P028/P029/P037 overlap-differentiation logic in
`report_view.py` untouched (it is shared with the out-of-scope P019/P037
rules); Slice 6 left PR #407's Abstract continuation-line presentation
machinery (`_apply_abstract_indent_presentation`, `abstract_indent_location_label`,
`grouped_finding_display_dedup_key`) untouched.

---

## Rules now aligned at the wording/remediation layer

The following 29 rules have Ester-aligned binary questions and direct
remediation text, as of PR #420:

P011, P013, P023, P028, P029, P030, P031, P032, P036, P039, P040, P041, P042,
P043, P044, P045, P046, P047, P048, P049, P050, P053, P054, P055, P066, P067,
P068, P074, P078

---

## Deferred rules and reasons

| Rule(s) | Reason |
|---|---|
| **P021** | Human policy review needed — abstract word-count limits (catalog: 350/150 PhD/MS; Ester sheet: 200/400 as referenced in feedback). Do not change until a human policy owner confirms the correct limits. |
| **P026** | Human policy review / detector review needed — accepted font families (Times New Roman, Arial, Computer Modern) and job-card fallback wording currently drift from each other. |
| **P037** | PR #407-sensitive dynamic Roman-numeral logic. The catalog/job wording must describe a *computed* expected Roman numeral (derived from the preceding page), not a hard-coded template anchor. Do not casually rewrite this wording without re-verifying against PR #407's fix. |
| **P014, P015, P017, P018, P019, P020, P024, P025, P027** | Broad, umbrella-style rules. Their catalog questions and/or job-card fallbacks bundle multiple sub-cases or issue types. These need a presentation-split plan (routing to atomic public cards / issue-type-specific text), not a simple wording-only pass. |
| **P056–P062** | Lower-priority TOC/LoT/LoF ordering and advisory rules. Likely safe to wording-align, but several carry manual-review caveats (sparse-page gates, cross-page ordering) that must be checked individually before wording is tightened. |
| **P051, P052, P065** | Heuristic extraction/font/copyright-style rules (copyright year presence, copyright author presence, dedication centered/italic style). Wording must stay conservative ("appears to", "may need") and not overstate OCR/extraction or typography-verification confidence. |
| **P064** | Broad catalog question covering multiple structural issue types (heading missing, indentation inconsistent, spacing inconsistent). Needs a dedicated slice or issue-type-only overrides, not a single combined wording pass. |
| **P084 and TOC-leader WIP** | Out of scope. Local, uncommitted WIP work (in the dirty worktree at `/home/soroush/njit-thesis-auditor/main`) — not part of the Ester wording program. |

---

## Safety rules for future work

- Future implementation should continue using **small PRs**, one wording
  slice (or one planning document) at a time.
- Wording-only PRs must **not** touch `src/njit_auditor/rules/`.
- Broad presentation splits must **preserve existing detector findings** —
  only change how they are displayed/grouped/routed, not what is detected.
- Any detector change requires a **golden-output comparison** (before/after
  finding counts and fields on the canonical evaluation set) before merge.
- **P021 and P026 must not be changed** until Ester or a human policy owner
  confirms the intended policy (word-count limits; accepted font families).
- **PR #407** (Roman-numeral dynamic computation, Abstract continuation-line
  false-positive fix, LoT Roman-numeral false-positive fix, P011 margin
  presentation, P024/P040 LoF presentation, P025 DC wrapper notice) and
  **PR #408** (confidence sort baseline) behavior must be preserved across
  all future wording and presentation work.
- **Private student documents and generated reports must not be committed**
  to the repository.

---

## Recommended next step

The next PR should be **documentation/planning only** — pick one of:

1. A broad presentation-split plan for P014/P015/P017/P018/P019/P020/P024/P025/P027
   (how umbrella catalog questions and job-card fallbacks would route to
   atomic, per-issue-type public cards without changing detection).
2. A human-policy-review note for P021/P026, laying out the specific
   conflicting values (Ester sheet vs. current catalog) so a policy owner
   can make a single decision that then flows into one wording PR.
3. A heuristic-wording review for P051/P052/P065/P064 — auditing exactly
   what each detector verifies today so any future wording pass stays
   honest about extraction/style confidence.

**Do not** proceed directly to detector implementation for any of the above;
each needs a planning pass first, matching how Slices 1–6 were preceded by
PRs #411–#413 and #416.
