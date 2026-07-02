# Ester Next Wording Implementation Slice Plan

> **Purpose:** Decide the safest **next** wording-only implementation slice after the
> completed Slice 1 and Slice 2 PRs — **without implementing it yet**.
>
> **Recorded:** 2026-07-02 (post–PR #415 merge; behavior baseline PR #408 @ `70dcd95`)
>
> **Related:** [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) ·
> [ester_language_alignment_audit.md](ester_language_alignment_audit.md) ·
> [ester_current_wording_inventory.md](ester_current_wording_inventory.md)

**Inspection basis (read-only; no source edits in this planning PR):**

| Layer | File(s) |
|---|---|
| Rule catalog | `data/processed/rules/project_added_rules.json` |
| Public `/rules` cards | `src/njit_auditor/web_app.py` — `_RULE_TEXT_OVERRIDES`, P018A–Q delegation |
| Job explanations | `src/njit_auditor/finding_explanations.py` |
| Issue-type explanations | `src/njit_auditor/issue_type_explanations.py` |
| Comment polish / suggested fix | `src/njit_auditor/polished_comments.py` |
| Grouped problem cards | `src/njit_auditor/report_view.py` |

---

## Completed wording slices

These slices are **already merged** and should not be re-done unless Ester revises the sheet.

| Slice | PR | Rules | Scope |
|---|---|---|---|
| **Slice 1** | [#414](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/414) | P011, P013, P023, P030, P050 | First safe margin/spacing/continuation wording alignment |
| **Slice 2** | [#415](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/415) | P031, P032, P036, P039, P040, P046, P048, P049 | Already-atomic TOC/List wording alignment |

Both slices touched only:

- `data/processed/rules/project_added_rules.json` (question/remediation)
- `finding_explanations.py`, `issue_type_explanations.py`, `polished_comments.py`
- `web_app.py` `_RULE_TEXT_OVERRIDES` (and `toc_list_student_preview.py` for P036 display)
- Wording-only test expectation updates where needed

Neither slice touched `src/njit_auditor/rules/`, templates, thresholds, grouping keys,
`issue_type`, confidence labels, highlights, or report JSON schema.

---

## Candidate rule classification

Classification key:

| Label | Meaning |
|---|---|
| **safe-wording-only-now** | Atomic or nearly atomic; Ester binary/direct wording can land in catalog + presentation layers without detector/template changes. Use conservative “appears” where heuristic. |
| **safe-remediation-only-now** | Question mostly fine; remediation/suggested-fix text needs Ester directness only. |
| **presentation-only-later** | Detector/issue_types already granular, but student UI still shows umbrella rule_id or bundled headline; needs display routing/split, not just catalog text. |
| **needs-policy-review** | Ester sheet and detector/catalog disagree on policy constants or accepted families. |
| **needs-detector-work** | Honest Ester wording requires new detection, thresholds, or issue_types. |
| **already-good** | Current wording sufficiently Ester-aligned after prior slices; skip unless sheet changes. |
| **do-not-touch-now** | Explicitly out of scope: broad splits, policy review, P084/TOC WIP, or high regression risk. |

### Page numbering & headings (overlap with broad rules)

| Rule | Classification | Rationale |
|---|---|---|
| **P027** | presentation-only-later | Per-level `issue_type` templates exist in `polished_comments.py`, but catalog question bundles L1–L5. PR #407 bold-heading gate must be preserved. Overlaps P020 umbrella. |
| **P028** | safe-wording-only-now | Atomic regime checks (Roman front matter vs Arabic body). Job templates already per `issue_type`. Wording can align with matrix without touching detection. Low overlap risk if P019/P013 fallbacks are not edited. |
| **P029** | safe-wording-only-now | Atomic Roman sequence issue_types (gap/repeat/decrease). Direct remediation possible. Candidate verification signal wording must stay honest. |

### Front-matter structure & indentation

| Rule | Classification | Rationale |
|---|---|---|
| **P037** | safe-wording-only-now (careful) | Per-section Roman findings are atomic, but catalog question still lists **fixed** template numerals (e.g. LoT = viii). PR #407 computes expected Roman from preceding page — **wording must describe computed expectation**, not hard-coded anchors. |
| **P038** | safe-wording-only-now | Heading presence/phrase-variant checks are atomic per section. Overlaps P014 formatting presentation but does not require P014 split for wording-only pass. |
| **P041** | safe-wording-only-now | Single binary: no header text in dedication top margin. Small, isolated rule. |
| **P042** | safe-wording-only-now | Appendix TOC format; two atomic issue_types. |
| **P043** | safe-wording-only-now (careful) | Acknowledgements indentation; atomic issue_types. Standard indentation presentation — low PR #407 overlap (P044 is the sensitive one). |
| **P044** | safe-wording-only-now (careful) | Abstract indentation; atomic issue_types. **PR #407 continuation-line presentation must be preserved** — do not embed per-line text in grouping-key comments. |
| **P045** | safe-wording-only-now | Bio Sketch hanging-indent check; section-level finding with geometry metadata only. |
| **P047** | safe-wording-only-now | Bio Sketch bullet-section single-spacing; geometry-only heuristic. |
| **P065** | safe-wording-only-now (careful) | Dedication centered/italic — font/style heuristic; wording must use “appears” and not claim exact typography verification. |
| **P074** | safe-wording-only-now | Title page graduation month (August/December/May); atomic binary. |

### Copyright & abstract language

| Rule | Classification | Rationale |
|---|---|---|
| **P051** | safe-wording-only-now (careful) | Copyright year presence — conservative advisory when year not extractable. Wording must not overstate OCR/extraction capability. |
| **P052** | safe-wording-only-now (careful) | Copyright author presence — same advisory pattern as P051. |
| **P078** | safe-wording-only-now | Abstract forbidden terms / first-person check; atomic per finding. |

### TOC/List punctuation, ordering & consistency

| Rule | Classification | Rationale |
|---|---|---|
| **P053** | safe-wording-only-now | LoT entries must **not** end with terminal period (inverse of P040). Atomic; mirror Slice 2 tone. |
| **P054** | safe-wording-only-now | TOC entries must **not** end with terminal period. Atomic. |
| **P055** | safe-wording-only-now | Cross-type misplaced entry (Figure in LoT / Table in LoF). Atomic binary per issue_type. |
| **P056** | safe-wording-only-now (careful) | Mixed chapter-based vs sequential numbering — advisory, low confidence. Keep “appears to mix” wording. |
| **P057** | safe-wording-only-now | LoT/LoF page-number non-decreasing order; section/page-level advisory. |
| **P058** | safe-wording-only-now | TOC page-number non-decreasing order. |
| **P059** | safe-wording-only-now | LoT/LoF entry-number non-decreasing order. |
| **P060** | safe-wording-only-now | TOC section-number non-decreasing order. |
| **P061** | safe-wording-only-now (careful) | Cross-page LoT/LoF entry-number ordering; sparse-page gates — honest section-level wording. |
| **P062** | safe-wording-only-now (careful) | Cross-page TOC section-number ordering; same sparse-page caveat as P061. |

### Body, references, bio sketch, approval

| Rule | Classification | Rationale |
|---|---|---|
| **P063** | safe-wording-only-now (careful) | Appendix heading label convention on body pages; heuristic pattern match. |
| **P064** | presentation-only-later | Multiple issue_types (heading missing, indentation inconsistent, spacing inconsistent). Wording per issue_type is feasible, but catalog question is broad; defer to a dedicated slice or pair with issue-type-only overrides. |
| **P066** | safe-wording-only-now | Bio Sketch degree chronological order; metadata-rich comments already tested. |
| **P067** | safe-wording-only-now | Bio Sketch publication chronological order; same pattern as P066. |
| **P068** | safe-wording-only-now | Approval page role labels and signature/date structure; atomic issue_types. |

### Explicitly excluded from candidate evaluation

| Rule | Classification | Rationale |
|---|---|---|
| **P021** | needs-policy-review | Abstract word-count limits conflict with Ester sheet (150/350 vs 200/400). **Do not touch.** |
| **P026** | needs-policy-review | Accepted font families / job fallback drift. **Do not touch.** |
| **P014, P015, P017, P018, P019, P020, P025** | do-not-touch-now | Broad presentation-split rules — not wording-only. |
| **P084, TOC-leader WIP** | do-not-touch-now | Local WIP; out of scope. |

### Already handled or low priority

| Rule | Classification | Rationale |
|---|---|---|
| **P011, P013, P023, P030, P050** | already-good | Slice 1 complete. |
| **P031, P032, P036, P039, P040, P046, P048, P049** | already-good | Slice 2 complete. |
| **P012** | already-good | Ester: no edit requested. |

---

## Recommended Slice 3 (smallest safe next slice)

**Theme:** *Binary punctuation & simple structural atomics* — rules that are already one
issue per finding, have no presentation-split dependency, no policy conflict, and minimal
PR #407 regression surface.

| Rule | Why included |
|---|---|
| **P041** | Dedication top-margin header; single issue_type; isolated from PR #407 indentation fixes. |
| **P042** | Appendix TOC entry format; two clear issue_types; direct remediation. |
| **P053** | LoT must not end with period — natural pair to completed P040; atomic. |
| **P054** | TOC must not end with period — atomic inverse punctuation check. |
| **P055** | Misplaced Figure/Table in wrong list — binary, direct “move entry” remediation. |
| **P074** | Title page graduation month — binary, no heuristic overflow. |
| **P078** | Abstract forbidden terms / first-person — atomic language check. |

**Count:** 7 rules (within the 4–8 target band).

**Expected touch surfaces (implementation PR only — not this doc):**

- `project_added_rules.json` question/remediation for P041, P042, P053, P054, P055, P074, P078
- `_RULE_TEXT_OVERRIDES` in `web_app.py` for the same IDs
- Matching templates in `polished_comments.py`, `finding_explanations.py`, `issue_type_explanations.py`
- Wording-only test updates if exact-string assertions exist

**Explicitly not in Slice 3:** `report_view.py` presentation overrides (none required for these rules today).

---

## Recommended Slice 4 (following slice — planning only)

If Slice 3 lands cleanly, the next smallest cluster would be **Bio Sketch & Approval atomics**:

- P066, P067, P068, P045, P047

These already have metadata-enriched comments and tests; wording alignment is low-risk but
slightly wider than Slice 3 because of Bio Sketch geometry phrasing.

**Page-numbering atomics** (P028, P029) are a reasonable **Slice 5** candidate if kept
separate from P019/P013 umbrella fallbacks.

**Front-matter indentation** (P043, P044) should be its own slice **after** Slice 3/4 because
P044 interacts with PR #407 continuation-line presentation.

**P037** should be a dedicated slice with explicit “computed expected Roman” honest wording —
not bundled with generic front-matter rules.

---

## Deferred rules and reasons

| Rule(s) | Defer until | Reason |
|---|---|---|
| **P021** | Human policy resolution | Word-count constants conflict with Ester sheet. |
| **P026** | Human policy resolution | Font-family acceptance list and job fallback alignment need policy sign-off. |
| **P014, P015, P017, P018, P019, P020, P024, P025, P027** | Presentation-split phase | Umbrella catalog questions / job cards need display routing to atomic public cards, not catalog text alone. |
| **P037** | Dedicated slice with PR #407 awareness | Catalog fixed-numeral wording overstates dynamic detector behavior. |
| **P043, P044** | Post–Slice 3/4 indentation slice | P044 PR #407 continuation presentation is sensitive. |
| **P064** | Presentation or issue-type-only slice | Broad catalog question; multiple structural issue_types. |
| **P056–P062** | After Slice 3–5 | Ordering/advisory rules — safe wording but lower student-impact priority; some are section-level advisories. |
| **P065** | Optional later slice | Font/style heuristic for dedication italic/centering. |
| **P051, P052** | Optional later slice | Copyright extraction advisories — must not overstate extraction confidence. |
| **P084, TOC-leader WIP** | Separate feature work | Local dirty WIP; not part of Ester wording program. |

---

## Safety notes for future implementation PRs

Any **wording-only** implementation PR (starting with Slice 3) must:

1. Touch **only** presentation/wording layers:
   - `data/processed/rules/project_added_rules.json` (question/remediation fields)
   - `finding_explanations.py`, `issue_type_explanations.py`, `polished_comments.py`
   - `web_app.py` `_RULE_TEXT_OVERRIDES`
   - `toc_list_student_preview.py` or `report_view.py` **only** when a rule already has a
     documented display override pattern (not anticipated for Slice 3)
2. **Not** touch `src/njit_auditor/rules/`, templates, thresholds, grouping keys,
   `issue_type`, confidence labels, highlight coordinates, or report JSON schema.
3. **Not** touch P021, P026, P084, TOC-leader WIP, or broad-split parent rules.
4. Use **honest wording** wherever the detector is heuristic — prefer “does not appear” /
   “may not appear” over absolute claims.
5. Preserve **PR #407** fixes: P011 grouping keys, P044 continuation-line handling,
   P037 dynamic Roman presentation, P024/P040 LoF entry-index presentation, P025 DC wrapper
   notice framing, P027 bold-heading gate.
6. Preserve **PR #408** confidence-sort display behavior (wording changes must not alter
   grouping-key text in ways that split/merge problem cards unintentionally).
7. Run golden structural comparison before merge: `rule_id`, `page`, `severity`,
   `issue_type`, `category`, `confidence`, `location`, bbox/highlight, grouping anchors,
   occurrence counts — unchanged; only student-facing wording/remediation may differ.
8. Never stage/commit LFS pointer noise or private evaluation artifacts from worktrees.

---

## Related documents

| Document | Role |
|---|---|
| [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) | External Ester sources and language principles |
| [ester_language_alignment_audit.md](ester_language_alignment_audit.md) | Full P011–P050 alignment classification |
| [ester_current_wording_inventory.md](ester_current_wording_inventory.md) | Pre-slice wording inventory (partially superseded by #414/#415) |
| [ester_q_p_rule_public_rule_mapping.md](ester_q_p_rule_public_rule_mapping.md) | Q → P → public card mapping |
