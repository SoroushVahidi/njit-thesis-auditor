# Ester Feedback Source of Truth

> **Purpose:** Document Ester Flaim's Gmail/Drive feedback as the language and remediation
> source of truth for future website wording, rule naming, and remediation polish — **without**
> authorizing detector behavior changes by itself.
>
> **Canonical live status:** [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)
>
> **Related mapping doc:** [ester_q_p_rule_public_rule_mapping.md](ester_q_p_rule_public_rule_mapping.md)

**Recorded:** 2026-07-02 (post–PR #409/#410 status sync; behavior baseline PR #408 @ `70dcd95`)

---

## 1. Authoritative source materials

Use these external artifacts as the primary language/remediation references. Do **not** import
private student PDFs, Gmail attachments, or generated audit reports into the repository.

| Source | Title / description | Identifier | Repository mirror (if any) | Role |
|---|---|---|---|---|
| **Google Sheet** | NJIT Thesis Auditor Formatting Rules | Spreadsheet ID `1IohAmbslfX1orMDr7gx6oJyGGTqAV_AAtF31GP-57Gc` | `data/specs/ester_p_rule_feedback.json` (subset of P-rules with Ester's proposed edits) | Current P-rule wording, Ester's proposed edits, original remediation, and Ester's proposed remediation |
| **Excel / Drive** | `260330 YESNO audit logic matrix.xlsx` | Drive/file ID `188x75m0ST3EWX9eiXcI2tBHn-plmeV6S` | `data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx` (tracked); transcribed Q-matrix in `data/specs/ester_q_matrix.json` | YES/NO audit logic matrix — model for binary question + remediation style |
| **Gmail threads** | Feedback on thesis-auditor warnings and sample reports | — | Not committed | Ester's reactions to sample warnings, grouping, and student-facing clarity |
| **Gmail threads** | Suggestions for the NJIT Thesis Auditor | — | Not committed | Product direction, atomic questions, remediation tone |
| **Gmail threads** | Meeting to discuss thesis-formatting AI project | — | Not committed | Scope, priorities, and presentation expectations |

When repository copies and Drive originals disagree, treat the **Drive originals** as the
language source of truth and open a maintainer task to refresh `data/specs/` — do not silently
change detector behavior during doc refresh.

---

## 2. Ester language principles

These principles apply to **student-facing presentation** (web UI warnings, `/rules` cards,
grouped problem comments, suggested fixes). They are **guidance for future polish**, not
permission to change detectors during repository cleanup.

1. **Student-facing language, not internal detector language.** Warnings should read like Ester's
   review comments, not engineer-facing heuristic descriptions.
2. **Strict binary yes/no formatting questions.** Each warning should be answerable as YES or NO,
   matching the YES/NO matrix style (`260330 YESNO audit logic matrix.xlsx`).
3. **Exactly one issue per warning.** Do not bundle unrelated checks in a single student-facing card.
4. **Exactly one remediation per issue.** The fix text should address only the question asked.
5. **Shared wording tradition.** Question and remediation should use the same kind of wording and
   literature as Ester's Excel/Google Sheet materials (formal, direct, NJIT dissertation context).
6. **Wording first, strictness second.** Align rule names, questions, and remediations before tuning
   thresholds, false-positive rates, or highlight accuracy.
7. **Internal breadth vs. external atomicity.** Broad detector findings may still exist internally
   for efficiency, but student-facing presentation should move toward atomic Ester-style questions.
8. **Documentation is not implementation authority.** This file records intent; detector or threshold
   changes require explicit review, golden-output comparison, and regression gates (see §5).

---

## 3. Specific rule notes from Ester's sheet

The table below captures Ester's feedback on selected P-rules. **Status here is presentation/split
guidance only** — it does not describe current detector behavior and does not authorize changes.

| P-rule | Ester guidance (summary) | Implementation note |
|---|---|---|
| **P011** | Reword around whether **all text is contained entirely within the required margins**. Margin rule remains **strict**: text, tables, and figures should not enter the required margins. | PR #407 improved overrun presentation without breaking grouping; preserve that behavior. |
| **P012** | **No edit requested** by Ester. | Keep current wording unless Ester revises the sheet. |
| **P013** | Reword around **visible page numbers being exactly in the designated bottom-center position**. | Align question/remediation with matrix page-number rows; do not change P013 detection thresholds without golden comparison. |
| **P014** | Broad front-matter heading checks should be **split by specific front-matter pages/questions** from the YES/NO matrix (Approval, Bio Sketch, Acknowledgements, TOC, LoT, LoF, etc.). | See `docs/planning/ester_atomic_rule_split_plan.md` for Q-mapping background; **do not implement splits in cleanup-only PRs**. |
| **P015** | **Split front-matter indentation from body indentation.** In front matter, **Abstract** and **Acknowledgements** are the main paragraph-structure pages. | P044/P043 handle Abstract/Acknowledgements atomically in places; body vs. front-matter split remains a future presentation/detector project. |
| **P017** | **Split figure-description checks from table-title checks.** Figure descriptions and table titles have different case, punctuation, spacing, and bold-label requirements. | LoF vs. LoT atomic Q-rules (e.g. Q074/Q075) are the model; preserve PR #407 LoF presentation fixes. |
| **P018** | **Split TOC, List of Tables, and List of Figures** checks into separate atomic questions. | Broad P018 may remain internally; public cards should trend toward Q052/Q061–Q073 style atomics. |
| **P019** | **Split front-matter pagination checks from body pagination checks.** | Roman vs. Arabic numbering families should not share one vague student-facing question. |
| **P020** | **Split title/heading checks by heading level.** Levels 1–5 each need separate questions/remediations. | PR #407 bold-heading requirement for numbered-pattern lines must be preserved. |
| **P021** | **Separate MS and PhD abstract word-count questions.** Use Ester's preferred limits from the sheet. | **Conflict flag:** current detector constants are PhD ≤350 / MS ≤150 (`abstract_word_count_exceeded`). If Ester's sheet differs, record the delta here and resolve in a dedicated review — **do not change limits during doc-only cleanup**. |
| **P022** | **Likely redundant** because no-visible-page-number checks are covered by specific front-matter questions (Q001, Q008, etc.). | Treat as presentation consolidation candidate, not a delete-without-review action. |
| **P023** | Body text from **Chapter 1 through References** should be **double-spaced**, with exceptions for tables, figure descriptions, bullet points, and multi-line titles. | Wording alignment only until a dedicated spacing project is scoped. |
| **P024** | TOC/List capitalization and punctuation should be handled through **more atomic TOC/List questions**, not one broad list-format warning. | PR #407 LoF sentence-case presentation fixes must be preserved. |
| **P025** | Split required front-matter **structural checks into page-level questions**: Abstract, Title Page, Copyright Page, Approval Page, Biographical Sketch, Dedication, Acknowledgements. | PR #407 Digital Commons wrapper **notice** (not problem) behavior must be preserved. |
| **P026** | Accepted font families: **Times New Roman, Arial, and Computer Modern Typeface family**. Font size **12 pt** except text in tables and figures. | Wording/remediation alignment only; do not regress P026 false-positive fixes from the ester-alignment stack. |
| **P030 / P031 / P032 / P036 / P039 / P040 / P046 / P048 / P049 / P050** (and similar TOC/List rules) | Remain aligned with Ester's **atomic TOC / List of Tables / List of Figures** wording from the YES/NO matrix and Formatting Rules sheet. | PR #407 P040 entry-index presentation fixes must be preserved. |

For Q-rule ↔ P-rule crosswalk, see [ester_q_p_rule_public_rule_mapping.md](ester_q_p_rule_public_rule_mapping.md).

---

## 4. Recommended polish sequence (future work)

This sequence is **planning guidance only**:

1. **Ingest** — Confirm sheet/matrix/Gmail wording against `data/specs/ester_p_rule_feedback.json` and `data/specs/ester_q_matrix.json`.
2. **Present** — Update student-facing question/remediation text, rule card titles, and grouped comment templates (web/report layer) toward atomic binary form.
3. **Split cards** — Where one P-rule maps to many Q-rules, split **public** rule references or problem-group presentation without changing `rule_id` / `issue_type` unless explicitly reviewed.
4. **Measure** — Golden-output comparison on built-in samples and approved evaluation PDFs before any detector threshold or classification change.
5. **Tune** — Only after wording alignment: false positives, highlight accuracy, confidence tiers.

Open PR cleanup (#311, #349, #362, #375, #376, #385) remains **paused**. **P084** remains **out of scope** unless explicitly requested.

---

## 5. Safety

**Do not use this document as permission to change detector behavior during cleanup.**

| Guardrail | Requirement |
|---|---|
| Preserve PR #407 fixes | P044 continuation-line FP reduction; P027 bold-heading requirement; P037 LoT Roman numeral FP reduction; P011 margin overrun presentation without grouping breakage; P024/P040 LoF presentation; P025 DC wrapper notice behavior |
| Preserve PR #408 fixes | Confidence sorting of grouped problem cards (display order only; grouping keys and detector output unchanged) |
| Preserve PR #406 fixes | Single-page `highlighted-page.pdf` behavior |
| Detector changes | Require golden-output comparison on built-in samples + protected regression tests before merge |
| Website wording changes | Preserve current `rule_id`, `issue_type`, grouping keys, problem anchors, confidence labels, and highlight behavior unless explicitly reviewed |
| Private data | Do **not** commit private student documents, Gmail attachments, or generated audit reports |
| Rule splits | Ester's requested atomic splits are **not implemented by this document**; track in planning docs, implement only in scoped PRs |
| Thresholds / rule IDs | No changes during documentation-only or status-sync work |

---

## 6. Maintainer pointers

| Topic | Document |
|---|---|
| Q → P → public card mapping | [ester_q_p_rule_public_rule_mapping.md](ester_q_p_rule_public_rule_mapping.md) |
| Atomic split planning (historical) | `docs/planning/ester_atomic_rule_split_plan.md` |
| Ester feedback implementation audit (historical) | [ester_feedback_implementation_audit_20260619.md](ester_feedback_implementation_audit_20260619.md) |
| Open PR triage | [open_pr_triage.md](open_pr_triage.md) |
| Live deployment | [live_deployment_checklist.md](live_deployment_checklist.md) |
