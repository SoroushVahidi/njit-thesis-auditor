# Ester YES/NO Audit-Matrix Alignment Audit

**Date:** 2026-06-18
**Baseline:** main at 8a116a4 (PR #321)
**Source feedback:** Ester's review email + attached `260330 YESNO audit logic matrix.xlsx`
**Source file (already in repo):** `data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx`

---

## 1. Ester's feedback (paraphrased)

- The tool should check **one rule at a time** so remediation is straightforward for a
  student to act on.
- Example given: P020 was perceived as checking multiple heading levels, but "how to
  correct it" only explains one level — confusing.
- Recommendations:
  1. Use the YES/NO matrix questions as rule/question names.
  2. Remove redundant "what it checks" sections when the question itself is explicit.
  3. Use matrix column D (remediation) sentences as "how to fix it" text.
  4. Apply this consistently — one check, one matching remediation.

---

## 2. Matrix structure

`260330_YESNO_audit_logic_matrix.xlsx` — single sheet (`Convert Word File to Google
She`), 90 rows × 4 columns, range `A1:D90`.

| Column | Header | Content |
|---|---|---|
| A | `Question ` | Question ID (`Q001`–`Q079`), or a bare front-matter section name used as a row-group header |
| B | `Rule / Question Text` | The YES/NO question text |
| C | `Rule Definition` | Expanded definition of what the question means |
| D | `Remediation` | The fix sentence for that exact question |

79 numbered questions, grouped under 10 section-header rows (no special
formatting/merged cells — just bare text in column A):

`Abstract, Title Page, Copyright Page, Approval Page, Biographical Sketch,
Dedication Page, Acknowledgements, Table of Contents, List of Tables, List of
Figures`

**Scope:** the matrix covers **front-matter sections only**. It does not cover body
chapters, numbered heading levels 1–5, margins, fonts, or body spacing — those are
P0xx rules with no matrix counterpart.

### Prior integration

`data/processed/rules/njit_rule_inventory.json` already contains a verbatim
transcription of all 79 matrix rows (`id`, `section`, `question`, `rule_definition`,
`remediation`, plus `implementation_status` / `implementation_module` linking each
Q-rule to the P-rule(s) that implement it). This was done in an earlier integration
pass (commit `513019a`) and confirmed identical to the live spreadsheet content. No
new transcription work was needed or done in this task; the matrix was used directly
as a *wording reference* for the P-rule presentation-layer fixes below, not
re-transcribed into a new file.

---

## 3. Root-cause finding: P020 vs P027

Ester's literal example ("P020 checks multiple heading levels") doesn't match
`pdf_title_capitalization.py` (P020) as implemented — P020 only ever covers **Level 2
headings and table titles**, both checked against the same single Title Case rule.

The rule that actually spans multiple heading levels with one combined remediation is
**P027** (`pdf_heading_levels.py`), which detects issues across heading Levels 1–5 and,
before this change, funneled all of them through one generic, all-levels-combined
remediation sentence:

> "Ensure numbered section headings follow the correct capitalization style for their
> level: Level 2 (1.x): Title Case; Level 3 (1.x.x): Sentence case (bold); Level 4
> (1.x.x.x) and Level 5 (1.x.x.x.x): Sentence case ending with a period."

This is exactly the failure mode Ester described: a Level-3 finding's remediation
mentions Level 2's rule, Level 4's rule, and Level 5's rule alongside the one that
actually applies. Both P020 and P027 were fixed (see §5); the doc treats Ester's "P020"
example as shorthand for "the heading-level-style family of rules" and documents the
P020→P027 mapping explicitly rather than silently diverging from the literal wording.

---

## 4. Gap analysis: presentation layer vs. detector output

Three presentation-layer modules build everything shown on a finding card:

| Module | Builds |
|---|---|
| `polished_comments.py` | `FindingView.polished_comment` (problem statement + remediation) |
| `finding_explanations.py` | `FindingView.detailed_explanation` ("What does this mean?") |
| `issue_type_explanations.py` | `FindingView.issue_type_label` / `issue_type_explanation` |

All three are explicitly documented as presentation-only — they never change detection
semantics, thresholds, or stored finding data. Each keys its lookup tables by
`(rule_id, issue_type)`, falling back to a rule-level entry, then to an absolute
generic fallback.

Before this change, the absolute fallback in `polished_comments.py` was:

```text
"Formatting check {rule_id} flagged issue type '{issue}' on page {page}."
```

— the literal banned phrase named in the task. A cross-reference of every
`(rule_id, issue_type)` pair actually emitted by the detectors in `src/njit_auditor/
rules/*.py` against the three lookup tables found roughly 80–90 pairs with **no**
bespoke entry anywhere, including every issue type produced by **P020, P023, P025,
P027,** and one of P038's two issue types — i.e. exactly the rule families named in the
task's focus list ("P020 heading/title levels", "front-matter structure rules",
"page-numbering/font/spacing rules", "any high-volume rule with generic remediation").

### Classification (per task's 6 categories)

| Category | Meaning | Rules in this audit |
|---|---|---|
| 1 | Already one-check-at-a-time, remediation-specific | P011, P012, P013, P019, P022, P028, P030, P033, P034, P063 (already had per-issue-type templates before this change) |
| 2 | Broad rule, but issue types specific enough | P026 (font family vs. size are already distinct issue types with distinct templates) |
| 3/4 | Broad rule **and** remediation too generic or mismatched | **P027** (5 levels, 1 combined remediation), **P025** (4 structural sub-checks, 1 combined remediation) — fixed in this task |
| 5 | Needs issue-type-specific rendering (data already supports it, presentation didn't use it) | **P020** (source=heading vs. caption, 3 reason categories, no template existed), **P023** (3 issue types, no `_ISSUE_TEMPLATES` entries), **P038** (`required_heading_missing` had zero coverage in `polished_comments.py`) — fixed in this task |
| 6 | Needs detector/data-model change later, not in this task | The remaining ~70 long-tail `(rule_id, issue_type)` pairs with no bespoke entry (e.g. most LoT/LoF formatting rules, P041/P051-P058 family). Presentation-only safety net improved (see §6), but true per-issue bespoke wording is future work. |

---

## 5. Implementation: presentation-layer fixes (this task)

All changes are presentation-only. No rule IDs, detector thresholds, or canonical
rule JSON files were modified. No body text, captions, titles, or author names are
ever rendered (`_BLOCKED_DETAIL_KEYS` in `polished_comments.py` is unchanged; new code
only reads bounded/categorical detail values such as `source`, `expected_or_reason`,
`expected_heading`, `inferred_level`).

### P027 — one comment + one remediation per heading level

Added 7 entries to `_ISSUE_TEMPLATES` (`polished_comments.py`) and
`_EXPLANATION_TEMPLATES` (`finding_explanations.py`), one per issue type the detector
actually emits: `level1_not_all_caps`, `level2_title_case_issue`,
`level3_sentence_case_issue`, `level4_sentence_case_issue`,
`level4_sentence_case_or_punctuation_issue`, `level5_sentence_case_issue`,
`level5_sentence_case_or_punctuation_issue`. Each names only its own level and its own
rule (ALL CAPS / Title Case / Sentence case / terminal period as applicable) and never
mentions the other levels.

Added a new `_ISSUE_REMEDIATION_OVERRIDES: dict[(rule_id, issue_type), str]` lookup in
`polished_comments.py`, checked **before** the rule-level catalog remediation. For all
7 P027 issue types this overrides the appended remediation to `""`, because the new
comment body already states the complete, level-specific fix — appending the old
combined-levels catalog sentence on top would silently reintroduce the exact problem
being fixed. The catalog `project_added_rules.json` is untouched; the CLI/source audit
still sees the original combined text.

The old dead template `("P027", "heading_style_issue")` (an issue_type the detector
never actually produces) was replaced with the 7 real ones. The P027 rule-level
fallback text (used only if a future 8th issue type appears without a template) was
reworded from a combined "Level 2/3/4/5 ..." sentence to a level-agnostic pointer:
*"NJIT uses a different style for each level ... check the level noted on this finding
and apply only that level's style."*

### P020 — heading vs. table-title, by actual cause, no quoted body text

P020 has one issue type (`possible_title_capitalization_issue`) but covers two
unrelated subjects (Level 2 headings vs. table titles, via `details["source"]`) and
three violation categories (`details["expected_or_reason"]`:
`first_word_requires_capital`, `word_after_separator_requires_capital`,
`major_word_requires_capital`). A template dict can't branch on two dimensions, so a
dedicated `_p020_title_case_comment()` helper was added (mirroring the existing
`_p013_candidate_comment()` precedent for the same reason). It states which subject
(heading or table title) and which violation category applies — **never** the
specific flagged word itself, since that word is extracted directly from the
dissertation text and the project's privacy policy blocks reproducing document text.
The previously-dropped specificity (the flagged word) lived only in
`AuditFinding.message`, which `FindingView` has no field for; rather than plumb a new
field through to expose that word, the fix communicates the violation *category*
instead, which is fully sufficient to act on. Remediation is suppressed
(`_ISSUE_REMEDIATION_OVERRIDES`) for the same reason as P027: the new body sentence
already states the complete Title Case rule.

### P025 — one comment + one remediation per front-matter structural element

P025 already emitted 5 cleanly distinct issue types from 4 independent sub-checks
(`missing_abstract_body`, `missing_title_page_degree_phrase`,
`missing_title_page_institution`, `sparse_approval_page_content`,
`possible_frontmatter_order_issue`) — a textbook Category 5 case: the detector data
already supported one-check-at-a-time, the presentation layer simply hadn't used it.
Added all 5 to `_ISSUE_TEMPLATES`, `_EXPLANATION_TEMPLATES`, `_ISSUE_TYPE_LABELS`, and
`_RULE_ISSUE_EXPLANATIONS`, each describing only its own missing/sparse/misordered
element. Added matching `_ISSUE_REMEDIATION_OVERRIDES` entries (one short, specific fix
sentence per element) replacing the old combined 4-clause catalog remediation.

### P038 — fill the `required_heading_missing` gap

`heading_phrase_not_exact` already had reasonable coverage everywhere; its sibling
issue type `required_heading_missing` had **none** at all (fell straight to the
absolute generic fallback in every one of the three presentation modules). Added it to
all three, using the already-recorded `details["expected_heading"]` (a canonical
heading name from a fixed internal list, not extracted document text) to name exactly
which required section is missing.

### P023 — high-volume rule, headline made issue-specific

P023 (body spacing) already had a clean, single-purpose catalog remediation and a
correct `suggested_fix` set directly by the detector — but its problem-statement
headline in `polished_comments.py` had **no** `_ISSUE_TEMPLATES` entries for any of its
3 issue types (`body_spacing_issue`, `excessive_line_gap`, `excessive_paragraph_gap`),
so the highest-volume rule in the catalog was showing the generic fallback headline on
every single finding. Added the 3 entries, reusing the wording already present in
`finding_explanations.py` for consistency.

### Safety net: removed the literal banned fallback phrase everywhere

`polished_comments.py`'s absolute fallback (used only when a `(rule_id, issue_type)`
pair has no bespoke template, no rule-level fallback) no longer emits "Formatting check
{rule_id} flagged issue type '{issue}'...". It now humanizes the issue type (reusing
`issue_type_explanations.humanize_issue_type`) and states it in plain language, e.g.
*"This check (P051) found a possible roman numeral mismatch issue on page 4."* The
rule's catalog remediation is still appended after this sentence whenever one exists
(unchanged `_finish_comment` behavior), so even long-tail Category 6 rules show a
rule-specific fix, not just a verify-manually instruction. This protects every
currently-unhandled pair, not only the ones given bespoke treatment above, without
requiring per-pair entries for all ~70 remaining long-tail issue types in this task.

### "What it checks" de-emphasis (`/rules` catalog page)

The matrix's `rule_definition` text for front-matter rules generally adds real,
non-redundant detail beyond the question (implementation thresholds, exclusions, what
is/isn't covered) — removing it outright would violate "never remove useful ...
expected ... text." Per the task's fallback instruction, it was moved into a
collapsible `<details>`/`<summary>` block (`templates/rules.html`) titled "What it
checks (details)", so the question/title and "How to correct it" (always visible) are
now the primary content, matching the UI priority order in the task (question →
observed → NJIT-expects-as-detail → fix). This is a uniform, content-preserving change
applied to all rule cards, not a selective deletion.

---

## 6. What was *not* changed (Category 6 / explicitly out of scope)

- No rule IDs were added, removed, or renumbered.
- No detector thresholds were changed (`_TITLE_CASE_MAJOR_WORD_MIN`,
  `MIN_ABSTRACT_BODY_WORDS`, `MIN_APPROVAL_BODY_LINES`, confidence levels, etc. are
  untouched).
- `data/processed/rules/project_added_rules.json`, `front_matter_rules.json`, and
  `njit_rule_inventory.json` (canonical rule data, also used by the CLI/source audit)
  were **not** modified.
- The remaining ~70 long-tail `(rule_id, issue_type)` pairs without a bespoke template
  (mostly LoT/LoF column/number/spacing rules, P041/P051–P058 family, P064 sub-types)
  still rely on the improved generic safety net rather than per-issue bespoke wording.
  These are legitimate future Category 6 work, not attempted here to keep this change
  reviewable and tightly scoped to the rules Ester's feedback and the task's focus list
  named explicitly.
- `docs/web_ui_demo_guide.md` / `docs/web_ui_manual_qa_checklist.md` were reviewed;
  no UI language changes here are material enough (button labels, action kinds, page
  structure all unchanged) to require updates.

---

## 7. Validation

- `ruff check .` — clean (one line-length violation introduced during editing was
  fixed before final validation).
- `mypy src` — clean (93 source files).
- `python -m pytest` — **1525 passed**, 0 failed (baseline before this task: 1509
  passed; this task added 16 new tests — 14 in `tests/test_finding_actionability.py`
  §24 "Ester YES/NO matrix alignment", 2 in `tests/test_help_rules.py` for the
  collapsible "What it checks" markup).
- New tests cover: P027 level-specific remediation across multiple levels (Level 1 vs.
  Level 3, plus all 7 issue types) with no cross-level mentions and no old combined
  remediation text; P020 heading-vs-caption source specificity with no cross-subject
  mixing and no flagged-word leakage; P025 issue-specific remediation across multiple
  front-matter elements with no old combined remediation text; P038
  `required_heading_missing` matrix-aligned wording, distinct from
  `heading_phrase_not_exact`; the generic safety-net fallback (exercised via P029, a
  rule with no bespoke template) emitting no banned phrase while still appending the
  rule's catalog remediation; and the `/rules` page's collapsible "What it checks"
  markup with "How to correct it" confirmed to remain outside the collapsed block.
- Re-ran the full pre-existing actionability/highlight/parity suite
  (`test_finding_actionability.py`, `test_mobile_desktop_consistency.py`,
  `test_pdf_highlight.py`, `test_p063_appendix_body_headings.py`) standalone — 97 + 13
  passed, confirming P013/P063 wording precision, highlight eligibility, and
  mobile/desktop parity are unaffected before re-confirming via the full suite above.
- Confirmed no change to `finding_explanations.get_action_kind` /
  `get_action_label` / `get_no_highlight_reason`, the PDF-highlight eligibility gate
  from PR #321, or any mobile/desktop template — this task only added lookup-table
  entries and one collapsible details block, never touched the action/highlight
  decision logic.

## 8. Remaining risks

- The new `_p020_title_case_comment` / per-level P027 wording is based on reading the
  detector source directly (issue_type strings, detail keys); if a future change to
  `pdf_title_capitalization.py` or `pdf_heading_levels.py` adds a new issue type or
  renames an existing one, the corresponding template/override entries must be added
  alongside it or that finding will silently fall back to the generic (but no longer
  banned-phrase) safety net.
- P025's and P038's `_ISSUE_REMEDIATION_OVERRIDES` entries are intentionally terse;
  if NJIT's actual front-matter requirements change, both the override text here and
  the catalog `remediation` field would need updating together.
