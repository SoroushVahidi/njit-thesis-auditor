# Ester Current Wording Inventory

> **Purpose:** Inventory the **actual current student-facing wording** used by the auditor
> (website `/rules`, audit job cards, suggested fixes) compared with Ester Flaim's preferred
> Excel/Google Sheet language — **before** any wording implementation begins.
>
> **Related:** [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) ·
> [ester_language_alignment_audit.md](ester_language_alignment_audit.md)
>
> **Recorded:** 2026-07-02 (post–PR #412; behavior baseline PR #408 @ `70dcd95`)
>
> **Historical note:** This document predates the final #9 cleanup snapshot (2026-07-05).
> For the current state, see [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md).

**Inspection basis (read-only, not modified):**

| Layer | File(s) |
|---|---|
| Rule catalog (canonical text) | `data/processed/rules/project_added_rules.json` |
| Public `/rules` cards | `src/njit_auditor/web_app.py` — `_RULE_TEXT_OVERRIDES`, `_P018_PUBLIC_CARD_SPECS`, P015A/B split |
| Audit job explanations | `src/njit_auditor/finding_explanations.py` — `_ISSUE_EXPLANATIONS`, `_RULE_FALLBACKS` |
| Comment polish / suggested fix | `src/njit_auditor/polished_comments.py` — `_ISSUE_TEMPLATES`, fix maps |
| Grouped problem cards | `src/njit_auditor/report_view.py` — `finalize_student_facing_comment_and_fix()` |
| HTML shell | `src/njit_auditor/templates/` — problem-group / job templates (no rule copy embedded) |

**Note:** There is no `issue_explanations.py` on `main`; job-card issue text lives in
`finding_explanations.py`.

**Wording surfaces:**

1. **`/rules` question** — catalog `question` + `_websafe_rule_text()` overrides (and P018A–Q delegated cards).
2. **Audit job card headline / comment** — `finding_explanations.py` + `polished_comments.py` (often starts with "Problem:" or "may").
3. **Suggested fix / remediation** — catalog `remediation`, polish-layer fix strings, `_RULE_TEXT_OVERRIDES`.

---

## Goal

This inventory records **where current website/rule wording differs** from Ester's preferred style
so the next implementation PR can change text **honestly** (without pretending atomic checks exist
when detectors still emit broad findings).

**Main target:** Website warning language should use **Ester/student-facing binary question** wording,
not internal detector language ("heuristic", "candidate", "may", multi-issue umbrellas).

---

## Inventory table

**Ester target** summaries come from the YES/NO matrix and Formatting Rules sheet (see source-of-truth
doc). **Current** columns cite the primary student-facing source: catalog question/remediation unless
job-card text materially differs.

| Rule | Current website/rule wording | Current remediation wording | Ester target wording | Recommended next action | Risk level | Notes |
|---|---|---|---|---|---|---|
| **P011** | **Q:** "Is all text contained entirely within the required page margins?" **Job:** "Some content appears too close to or beyond the required page margin…" | Catalog: strict 1.5"/1" margins; no text/tables/figures in margins. Job matches. | **Q:** Is all text contained entirely within the required margins? **Fix:** Same strict margin rule. | wording-only-change | medium | Catalog/`/rules` already close to Ester. Job cards use softer "appears" phrasing; PR #407 added measured overrun in `location_label` — preserve grouping. |
| **P012** | **Q:** "Does the PDF contain annotations/comments?" **Job:** explains pre-existing PDF markup, not auditor highlight. | "Resolve or delete all annotations before final submission." | (Ester: no edit requested) | keep-as-is | low | Aligns with Ester sheet. |
| **P013** | **Q (override):** "Are all visible page numbers located exactly at the designated bottom-center position, 0.5 inches from the bottom edge?" **Job fallback:** vague "page-numbering style, placement, sequence, or presence." | Override: bottom-center, 0.5 in, verify style for section. | **Q:** Is each visible page number exactly bottom-center, 0.5 in from bottom? | wording-and-remediation-change | medium | `/rules` override is Ester-aligned; job fallback bundles sequence/style (P019/P028 territory). |
| **P014** | **Q:** single question for all named front-matter headings (all caps, bold, centered, top). **Job:** per-heading issue text via `source_q_rule_id` paths. | Long multi-page remediation listing Q013/Q021/Q036/Q047/Q061/Q070. | Separate binary per page (Approval, Bio Sketch, Acknowledgements, TOC, LoT, LoF). | presentation-split-needed | medium | Detector emits per-Q findings; student cards should not use umbrella P014 question on job UI. |
| **P015** | **Parent hidden on `/rules`.** Public **P015A/B** cards: body indentation after headings. **Job:** issue-specific P015A/B templates. | P015A/B + pointers to P043/P044 for front matter. | Split front matter vs. body; Abstract→P044, Acknowledgements→P043. | presentation-split-needed | medium | `/rules` split exists; ensure every job card routes to P015A/B/P043/P044 reference, not parent P015. |
| **P017** | **Q:** combined figure sentence case + terminal punct **and** table title case + no period. **Job:** separate templates per `issue_type` (LoF vs LoT). | Combined remediation in catalog; per-issue fixes in polish layer. | Split figure-description vs table-title binaries (Q074/Q075 vs Q065). | presentation-split-needed | medium | Issue types already separate; catalog question and grouped headlines still bundled. PR #407 LoF word naming preserved. |
| **P018** | **Parent hidden.** **P018A–Q** public cards are atomic binaries. **Job:** "Problem:" templates per `issue_type` (leaders, alignment, missing page number). | Catalog umbrella remediation points to P018A–Q; job text still under rule_id P018. | One binary per TOC/LoT/LoF matrix row (Q049–Q079 family). | presentation-split-needed | high | Largest gap: `/rules` atomics vs job cards still keyed to umbrella P018. Use `public_rule_reference_id` consistently. |
| **P019** | **Q:** "Do page-number candidates show obvious sequence, style, or position inconsistencies?" **Job:** "Problem: …" per issue_type. | "Review page-number visibility, position, style consistency, and sequence continuity." | Split front-matter vs body pagination; one binary per check. | presentation-split-needed | high | Catalog question is internal ("candidates", "obvious"). Prefer display routing to P028/P029/P037 atomics where possible. |
| **P020** | **Q:** "Do title-like PDF lines follow NJIT title-case capitalization heuristics?" **Job:** title-capitalization template. | Word/Overleaf source check; title-case rules. | Separate binary per heading level (L1–L5). | presentation-split-needed | medium | Overlaps P027; catalog uses "heuristic" (stripped on `/rules` only). PR #407 bold-heading gate on P027. |
| **P021** | **Q:** "Does the abstract exceed the NJIT word-count limit for the detected degree type?" **Job:** "PhD … 350 words, MS … 150 words." | "Shorten… PhD ≤350, MS ≤150." | **Separate** MS and PhD binaries; Ester sheet cites **MS 200 / PhD 400**. | human-policy-review-needed | high | **Constants conflict.** Do not change limits in wording-only PR. |
| **P022** | **Q:** "Do any named no-number front-matter pages … show a visible page number?" **Job:** per `page_type` (abstract, title, approval, copyright). | Remove page number from listed page types. | Per-page no-number binaries (Q001, Q008, Q012, Q014); may be redundant. | presentation-split-needed | low | Already page-specific in job layer; tighten to matrix question text per `page_type`. |
| **P023** | **Q:** "Does any body-text page show line spacing that appears to be less than double-spaced?" **Job:** double-spacing required. | Override shortens to Word "Double"; catalog mentions LaTeX. | Binary double-spacing Ch.1–References with **exceptions** (tables, figure descriptions, bullets, multi-line titles). | remediation-only-change | medium | Question mostly fine; remediation should list Ester exceptions explicitly. |
| **P024** | **Q:** "Do TOC/LoT/LoF entries follow expected capitalization and punctuation style?" **Job:** per `issue_type` templates. | Level 1 ALL CAPS, L2 Title Case, LoT no period, LoF sentence case. | Atomic TOC/List questions (Q049–Q051, Q065, Q074, Q075) — not one combined rule. | presentation-split-needed | medium | Delegated to P018A–C on `/rules`; job cards may still show P024 rule_id. |
| **P025** | **Q:** "Do required front-matter pages contain expected structural elements?" **Job:** per `issue_type` (abstract body, degree phrase, institution, approval sparse, order). | Multi-element remediation paragraph. | Page-level binaries (Abstract, Title, Copyright, Approval, Bio Sketch, Dedication, Acknowledgements); DC wrapper = **notice** not problem. | presentation-split-needed | medium | PR #407 notice framing for `digital_commons_wrapper_pages_detected` must be preserved. |
| **P026** | **Q (catalog):** "Times New Roman 12pt (or accepted equivalent)" **Job fallback:** "Times New Roman 12pt" only. **Override:** adds Arial, CM/LM accepted. | Override: Word TNR/Arial 12pt; CM/LM accepted for LaTeX. | Times New Roman, Arial, Computer Modern family; 12pt except tables/figures. | human-policy-review-needed | high | Detector accepts CM/LM/near-equivalents; **job fallback lags override** and omits Arial. Policy review before any family-list tightening. |
| **P027** | **Q:** "Do numbered headings follow the expected level-specific capitalization and punctuation style?" **Job:** per-level templates (L2–L5). | Per-level capitalization/punctuation fix text. | Separate binary per heading level. | presentation-split-needed | medium | Issue types already per-level; catalog question still bundled. PR #407 bold requirement + location label — do not regress. |
| **P030** | **Q:** "Do multi-page TOC/LoT/LoF sections use a continued heading on subsequent pages?" | Add "(Continued)" heading per section. | Per-section continued-heading binaries (Q048, Q062, Q071). | wording-only-change | low | Already fairly atomic; minor tone alignment ("may be missing" → binary question). |
| **P031** | **Q:** "Do LoT/LoF pages show expected Table/Figure and Page column header labels…?" | Add bold Table/Figure and Page labels under list heading. | Q063/Q064/Q072/Q073 atomics (bold + alignment). | presentation-split-needed | low | Coarse "expected coarse regions" wording; split bold vs alignment (P049/P050) at presentation. |
| **P032** | **Q:** "Do wrapped TOC/List entries appear internally single-spaced…?" | Adjust wrapped entry internal spacing. | Per-list wrapped-line spacing binaries (Q053–Q055, etc.). | presentation-split-needed | low | Delegated P018E–G on `/rules`; job cards use P032 rule_id. |
| **P036** | **Q:** "Do consecutive TOC/LoT/LoF entries have visible double spacing between them?" | Add double spacing / blank line between entries. | Per-list inter-entry spacing binaries (Q057, Q067, Q077). | presentation-split-needed | medium | P076 triage is reporting-only; job comments must not expose raw gap measurements. |
| **P037** | **Q:** fixed-template Roman anchors (bio iv, ded v, ack vi, toc vii, lot viii). **Job:** per-section "Problem: … numbered '…' expected '…'" | Ensure fixed template Roman numerals per section. | Sequential Roman after prior section (Q060: LoT follows TOC) — not hard-coded viii only. | wording-only-change | medium | PR #407 computes LoT expected from preceding page — **wording must match that behavior**; catalog question still lists fixed viii. |
| **P039** | **Parent hidden.** **P018H** public card for TOC hierarchy. **Job:** L2/L3 indent templates. | Indent L2 relative to L1, L3 relative to L2. | Q056 binary hierarchy question(s). | presentation-split-needed | low | `/rules` delegated; job uses P039 rule_id. |
| **P040** | **Q:** "Does every List of Figures entry … end with a terminal punctuation mark?" **Job:** terminal punctuation template. | End each LoF description with `.` `?` or `!` | Q075 binary per entry. | keep-as-is | low | Already atomic and Ester-aligned; PR #407 entry-index presentation — preserve. |
| **P046** | **Q:** "Are all table/figure numbers aligned vertically in a consistent left column…?" | Align entry numbers at same left margin. | Separate LoT (Q068) vs LoF (Q078) binaries. | presentation-split-needed | low | Section-level finding; split headline by list context. |
| **P048** | **Q:** "Are all LoT/LoF page numbers aligned vertically in a consistent right column?" | Align page numbers in right column. | Q069 / Q079 separate binaries. | presentation-split-needed | low | Delegated P018N/Q on `/rules`. |
| **P049** | **Q:** Page column header right-aligned **and** bold. | Bold + right-align Page header. | Split alignment vs bold (Q064, Q073). | presentation-split-needed | low | Two issue_types exist; presentation can use separate Ester questions. |
| **P050** | **Q:** Left-column Table/Figure header bold. | Bold Table/Figure header. | Q063 / Q072 separate binaries. | wording-only-change | low | Nearly atomic; minor tone polish only. |

---

## Implementation safety notes

This inventory **does not**:

- change website wording, templates, or `finding_explanations.py` / `polished_comments.py` yet;
- change detectors, thresholds, or `collect_pdf_layout_findings` order;
- change report JSON schema, grouping keys, `rule_id`, or `issue_type`;
- change confidence sorting (PR #408) or highlight behavior (PR #406/407).

It **should be used to design the next wording-only implementation PR** with golden-output comparison
on built-in samples before merge.

**Must preserve:** PR #407 warning-precision fixes (P011 grouping, P044 continuation lines, P037 LoT
Roman logic, P024/P040 LoF presentation, P025 DC wrapper notice, P027 bold-heading); PR #408
confidence-sort display order.

---

## Proposed first implementation slice (not in scope now)

Safest first wording PR — **no broad splits, no detector changes, no P021/P026 policy changes:**

| Rule | Action | Rationale |
|---|---|---|
| **P012** | keep-as-is | Ester: no edit requested |
| **P040** | keep-as-is | Already atomic and aligned |
| **P030** | wording-only-change | Minor "may" → binary question tone; honest to current detector |
| **P023** | remediation-only-change | Add Ester exception list to suggested fix; no detection change |
| **P011** | wording-only-change | Job card headline → catalog binary question; keep PR #407 `location_label` details |
| **P013** | wording-and-remediation-change | Align job fallback with `/rules` override (bottom-center 0.5 in); stop bundling sequence in P013 fallback text |
| **P050** | wording-only-change | Low-risk bold-header tone alignment |

**Explicitly defer:** P014, P015, P017, P018, P019, P020, P024, P025, P027 (presentation-split-needed);
P021, P026 (human-policy-review-needed); any rule requiring new `issue_type` or threshold change
(future-detector-work-needed).

**Process:** One PR touching only `finding_explanations.py`, `polished_comments.py`, and/or
`web_app.py` `_RULE_TEXT_OVERRIDES` + catalog JSON question/remediation fields — **no**
`src/njit_auditor/rules/` detector modules. Run golden JSON diff on `ester_sample_*` before merge.

---

## Related documents

| Document | Role |
|---|---|
| [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) | External source materials |
| [ester_language_alignment_audit.md](ester_language_alignment_audit.md) | Implementation-type classification |
| [ester_q_p_rule_public_rule_mapping.md](ester_q_p_rule_public_rule_mapping.md) | Q → P → public card map |
