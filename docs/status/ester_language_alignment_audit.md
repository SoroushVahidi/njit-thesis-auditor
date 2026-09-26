# Ester Language Alignment Audit

> **Purpose:** Repository-facing audit of how current **student-facing** website/rule language
> should be aligned with Ester Flaim's Excel/Google Sheet feedback **before** implementation
> begins. This document identifies what must eventually change; it does **not** authorize or
> perform behavior changes.
>
> **Source of truth:** [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md)
>
> **Recorded:** 2026-07-02 (post–PR #411; behavior baseline PR #408 @ `70dcd95`)
>
> **Historical note:** This document predates the final #9 cleanup snapshot (2026-07-05).
> For the current state, see [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md).
> Its P021 150/350 policy-conflict notes are superseded; current P021 policy is
> MS ≤200 words and PhD ≤400 words.

**Inspection basis (read-only):**

- `data/processed/rules/project_added_rules.json` — catalog `question` / `remediation`
- `src/njit_auditor/web_app.py` — `_RULE_TEXT_OVERRIDES`, public `/rules` card builder, P018A–Q delegation
- `src/njit_auditor/report_view.py` — grouped problem cards, `finalize_student_facing_comment_and_fix()`
- `src/njit_auditor/polished_comments.py` — issue-type comment/fix polish paths
- `src/njit_auditor/templates/` — job and problem-group HTML (not modified in this audit)

---

## Goal

Future website polish should make warnings, tone, rule names, and remediation language fully
consistent with Ester Flaim's **NJIT Thesis Auditor Formatting Rules** spreadsheet and **YES/NO
audit logic matrix** style.

**Main principle:**

> **One warning = one binary formatting question = one issue = one direct remediation.**

Student-facing text should read like Ester's review comments, not internal detector descriptions.
Alignment work should start with **wording and presentation**, not thresholds or classification logic.

---

## Current risk

The repository has **strong detector coverage** (P001–P083) and recent precision fixes (PR #407)
and UI display ordering (PR #408). Risks for the next polish phase:

| Risk | Why it matters |
|---|---|
| **Broad umbrella cards** | Rules like P014, P018, P019, P020, and P025 still surface multi-issue catalog questions or grouped comments that bundle several YES/NO matrix rows. |
| **Internal / developer tone** | Catalog `rule_definition` fields and some polished comments still use heuristic language ("candidate", "manual review", geometry metadata) even when student text is partially sanitized via `_websafe_rule_text()`. |
| **Presentation vs. detector drift** | `web_app.py` already hides some parent rules (P015, P018, P026, P039) and delegates TOC/List coverage to P018A–P018Q public cards — audit UI may still show umbrella P018/P024 findings unless presentation split is completed consistently in `report_view.py` / templates. |
| **Accidental behavior regression** | Wording cleanup that touches `polished_comments.py` or groups keyed by comment text can re-break PR #407 fixes (P011 grouping, P044 continuation lines, P037 LoT Roman logic presentation). |
| **Policy conflicts** | Ester's sheet limits (e.g. abstract word counts) may differ from current detector constants — must not be "fixed" silently during wording PRs. |

**Guardrail:** Wording cleanup must **not** change detector thresholds, `issue_type` values, grouping
keys, or golden outputs without explicit review.

---

## Alignment inventory

Columns:

- **Current student-facing issue** — catalog `question` and/or typical grouped-card headline (from `project_added_rules.json` + presentation layer).
- **Ester-style target** — atomic binary question + single remediation (from source-of-truth doc / YES/NO matrix).
- **Implementation type** — `wording-only` | `presentation-split-only` | `needs-new-atomic-rule` | `needs-human-policy-review` | `do-not-change-now`
- **Behavior risk** — `low` | `medium` | `high` (risk if mis-implemented during polish)
- **Priority** — suggested sequencing (`P1` urgent presentation, `P2` next, `P3` defer)

| P-rule | Current student-facing issue | Ester-style target wording | Implementation type | Behavior risk | Priority | Notes |
|---|---|---|---|---|---|---|
| **P011** | "Is all text (including tables and figures) contained entirely within the required page margins?" | Ester Column C/E via `ester_warning_wording_map.json` (2026-07-06); remediation leads with 1.5"/1" margins. | wording-only | medium | P1 | **Partially aligned in PR #24** — card titles + remediation; detector unchanged. |
| **P012** | "Does the PDF contain annotations/comments?" | (Ester: no edit requested) | do-not-change-now | low | P3 | Keep current question/remediation unless Ester revises sheet. |
| **P013** | Bottom-center page-number placement (catalog + `_RULE_TEXT_OVERRIDES`) | "Is each visible page number exactly bottom-center, 0.5 in from bottom edge?" | wording-only | medium | P1 | Override already tightens public `/rules` text; align grouped-card comments with matrix Q-rows; do not change P013 candidate detection. |
| **P014** | Single question for all named front-matter heading format (all caps, bold, centered, top) | Separate YES/NO questions per page: Approval, Bio Sketch, Acknowledgements, TOC, LoT, LoF (Q013, Q021, Q036, Q047, Q061, Q070). | presentation-split-only | medium | P1 | Findings already carry `source_q_rule_id` in many paths; student UI should show one card per Q-row, not one P014 umbrella. |
| **P015** | Body indentation after section headings (P015A/B public split exists) | Split front matter vs. body; Abstract → P044; Acknowledgements → P043; body questions separate. | presentation-split-only | medium | P1 | Parent P015 hidden on `/rules`; ensure audit job cards mirror P015A/B + P043/P044 atomics consistently. |
| **P017** | Combined figure-description + table-title case/punctuation question | Split: (1) figure sentence case + terminal period, (2) table title case + no period, (3) spacing/bold sub-checks per matrix. | presentation-split-only | medium | P1 | Backend emits Q065/Q074/Q075 on LoT/LoF contexts; presentation should not merge figure vs. table issues in one comment. PR #407 LoF word naming preserved. |
| **P018** | Umbrella TOC/LoT/LoF formatting question | Atomic questions per matrix row (leaders Q052, capitalization Q049–Q051, spacing, alignment, appendix, etc.). | presentation-split-only | high | P1 | P018A–P018Q public cards exist; parent P018 still drives many findings — highest-impact presentation-split target. Preserve PR #407 grouping. |
| **P019** | "Obvious sequence, style, or position inconsistencies" among page-number candidates | Split front-matter vs. body pagination checks; each binary per matrix style/sequence row. | presentation-split-only | high | P2 | Catalog remediation is vague ("Review page-number visibility…"). Prefer routing display to P028/P029/P037 atomics where `issue_type` allows. |
| **P020** | NJIT title-case on title-like PDF lines (single rule) | Separate questions per heading level (L1–L5) with level-specific capitalization/punctuation remediations. | presentation-split-only | medium | P1 | Overlaps P027 for numbered headings; presentation should not conflate L2 title case with L3 sentence case. PR #407 bold-heading gate must remain. |
| **P021** | Single question: abstract exceeds limit for inferred degree type (PhD ≤350, MS ≤150) | Separate MS and PhD binary questions with Ester limits (**sheet: MS 200 / PhD 400** per source-of-truth). | needs-human-policy-review | high | P2 | **Do not change constants now.** Flag conflict: catalog/detector use 150/350; Ester sheet cites 200/400. Resolve in human review before any detector or wording update. |
| **P022** | Visible page number on no-number front-matter pages | Per-page atomics (Abstract, Title, Approval, Copyright) — likely redundant with matrix-specific rows. | presentation-split-only | low | P2 | Could consolidate student messaging under Q001/Q008/Q012/Q014 style cards; detector output already page-specific via `page_type`. |
| **P023** | Body pages appear less than double-spaced | Binary: "Is body text (Ch.1–References) double-spaced?" with explicit exceptions (tables, figure descriptions, bullets, multi-line titles). | wording-only | medium | P2 | Catalog question close; expand remediation exceptions to match Ester sheet; `_RULE_TEXT_OVERRIDES` already simplifies Word path. |
| **P024** | Broad TOC/LoT/LoF capitalization and punctuation | Route student text through atomic TOC/List questions (Q049–Q051, Q065, Q074, Q075) not one combined rule card. | presentation-split-only | medium | P1 | Partially delegated to P018A–C; audit cards may still show P024 `issue_type` buckets — align comments per issue_type to one matrix question. |
| **P025** | Required front-matter structural elements (multi-issue) | Page-level binaries: Abstract body, Title page degree/institution, Approval content, order — plus DC wrapper **notice** not problem (PR #407). | presentation-split-only | medium | P1 | `digital_commons_wrapper_pages_detected` must stay notice framing. Split sparse/missing element findings into separate student questions. |
| **P026** | Times New Roman 12pt or accepted equivalent | Binary font family + binary 12pt size; accepted families: Times New Roman, Arial, Computer Modern family; 12pt except tables/figures. | needs-human-policy-review | high | P2 | Detector already accepts CM/LM/near-equivalents; Ester wording is aligned in overrides. Any future tightening of accepted families is **detector** work — classify policy review before behavior change. |
| **P027** | Numbered headings level-specific style (single catalog question) | Separate binary per level (L2 title case, L3 sentence case, L4/L5 sentence case + period). | presentation-split-only | medium | P1 | PR #407 requires bold before classifying numbered lines as headings — preserve in any comment rewrite. |
| **P030** | Continued heading on multi-page TOC/LoT/LoF | Per-section binaries: "Does this TOC continuation page show TABLE OF CONTENTS (Continued)?" (and LoT/LoF analogs). | wording-only | low | P2 | Catalog already fairly atomic (Q048, Q062, Q071). Minor tone alignment only. |
| **P031** | LoT/LoF column headers present in coarse regions | Atomics: bold Table/Figure label left; bold Page label right (Q063, Q064, Q072, Q073). | presentation-split-only | low | P2 | P049/P050 add bold/alignment refinements — student cards should reference one check each. |
| **P032** | Wrapped TOC/List entry internal spacing | Per-list binaries for wrapped continuation line spacing (Q053–Q055, Q066–Q067, Q076–Q078). | presentation-split-only | low | P2 | Delegated to P018E–G in public cards; align grouped comments similarly. |
| **P036** | Inter-entry spacing too tight on TOC/LoT/LoF | Separate binaries per list type for double spacing between entries (Q057, Q067, Q077). | presentation-split-only | medium | P2 | P076 triage rollup is reporting-only; student cards should not dump gap measurements (PR #371 precedent). |
| **P037** | Section-anchored Roman numerals (bio iv, toc vii, lot viii, …) | Per-section binary: "Does [section] page show the expected Roman numeral following the prior section?" | wording-only | medium | P1 | PR #407 computes LoT expected Roman from preceding page — **do not regress** in wording-only work. Comments should name section + expected numeral atomically. |
| **P039** | TOC L2/L3 indent hierarchy | Binary: "Are level-2 TOC entries indented relative to level-1?" and separate L3-vs-L2 question (Q056). | presentation-split-only | low | P2 | Parent hidden on `/rules`; delegated P018H — ensure job UI uses atomic headline per `issue_type`. |
| **P040** | Every LoF entry ends with terminal punctuation | Binary per entry: "Does this List of Figures entry end with terminal punctuation?" (Q075). | wording-only | low | P1 | PR #407 page-relative entry indexing in comments — preserve. Catalog question already atomic. |
| **P046** | LoT/LoF entry-number left-column alignment | Separate binaries for LoT vs. LoF column alignment (Q068, Q078). | presentation-split-only | low | P2 | Section-level findings — presentation can split by `list_of_tables` vs `list_of_figures` context without detector change. |
| **P048** | LoT/LoF page-number right-column alignment | Separate binaries (Q069, Q079). | presentation-split-only | low | P2 | Delegated P018N/Q — align wording with matrix. |
| **P049** | Page column header bold + right-aligned | Split bold vs. alignment into separate student questions (Q064, Q073). | presentation-split-only | low | P3 | Two `issue_type`s already exist — presentation-split at comment layer. |
| **P050** | Table/Figure column header bold | Separate LoT "Table" vs. LoF "Figure" header bold binaries (Q063, Q072). | presentation-split-only | low | P3 | Same as P049 — issue_types already separate. |

---

## Safe implementation sequence (future phases — not in scope now)

1. **Wording-only PRs** — Update catalog text, `_RULE_TEXT_OVERRIDES`, and `polished_comments.py` templates using existing `issue_type` / `details` fields. Golden-output diff on built-in samples required.
2. **Presentation-only splits** — Map each finding to a single matrix question for display (headline, suggested fix, `/rules` anchor) without changing detector emission. Prefer `source_q_rule_id` and existing `issue_type` granularity.
3. **Golden-output comparison harness** — Formalize before/after JSON/Markdown snapshots on `ester_sample_*` and protected regression tests (P011 grouping, P044 continuation, P037 LoT Roman, P025 notice, highlighted PDF).
4. **Detector behavior changes** — Only after explicit human review, policy resolution (P021, P026), and golden comparison. Includes any true atomic split requiring new `issue_type` or thresholds.
5. **Ester review pass** — Fresh live website sample audits (new jobs, not cached URLs) after wording PRs land; optional restart to align `/version` with merged `main`.

---

## Non-goals (this audit and immediate follow-ups)

This audit **does not**:

- implement Ester's requested rule splits at the detector layer;
- change detectors, thresholds, or `collect_pdf_layout_findings` order;
- change website templates (`src/njit_auditor/templates/`);
- change report JSON schema or grouping keys;
- change confidence sorting (PR #408);
- restart or redeploy the live server;
- merge/rebase old open PRs (#311, #349, #362, #375, #376, #385);
- start **P084** or TOC-leader WIP;
- commit private student documents or generated reports.

Future implementation must preserve **PR #407** warning-precision fixes and **PR #408**
confidence-sort behavior.

---

## Related documents

| Document | Role |
|---|---|
| [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) | External source materials and language principles |
| [ester_q_p_rule_public_rule_mapping.md](ester_q_p_rule_public_rule_mapping.md) | Q → P → public card layer map |
| `docs/planning/ester_atomic_rule_split_plan.md` | Historical atomic-split implementation notes (partially landed) |
| [open_pr_triage.md](open_pr_triage.md) | Open PR cleanup still paused |
