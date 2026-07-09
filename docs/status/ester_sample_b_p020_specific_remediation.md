# Ester Sample B P020 Item-Specific Remediation Fix

**Recorded:** 2026-07-09
**Branch:** `fix/ester-sample-b-p020-specific-remediation`
**Base:** `main` @ `e1aacaa` (PR #487 merged)

## Scope

Narrow follow-up to `docs/status/ester_sample_b_feedback_audit.md` items SB-11
and SB-12. Ester's Sample B feedback flagged two distinct P020 problems:

- **Page 71** — the flagged item is a third-level (Level 3) heading. Level 3
  headings use sentence case (only the first letter capitalized); the auditor
  should not suggest capitalizing a minor word like "and".
- **Page 80** — the flagged item is a table title. The remediation must be
  table-title-specific: title case (every word capitalized except
  prepositions, conjunctions, and articles), no final period — not generic or
  figure-caption wording.

Out of scope (left for later, separate branches): P011, P019, P038,
P026/P063 font false positives, and margin/page-numbering issues — per
`docs/status/ester_sample_b_feedback_audit.md`.

## Source of truth

The live Google Sheet ("NJIT Thesis Auditor Formatting Rules",
`docs.google.com/spreadsheets/d/1IohAmbslfX1orMDr7gx6oJyGGTqAV_AAtF31GP-57Gc`)
returned HTTP 401 (sign-in required) — consistent with the existing note in
`data/specs/ester_warning_wording_map.json`. No Gmail/Drive connector is
available in this environment either. Column C/E language was instead sourced
from the local mirrors already in the repo:

- `data/specs/ester_p_rule_feedback.json` (P017 Column C/E mirror) —
  table-title remediation verbatim: *"Edit table title to title case: each
  word capitalized except for articles, prepositions and conjunctions... Delete
  period from table title."*
- `data/specs/ester_q_matrix.json` — Q051 ("In the TOC, are all level-3
  section titles (X.xx) displayed in sentence case?") and Q065 ("Are all
  listed table titles in title case and free of a final period?").

Neither mirror has a P020-keyed entry (P020 sits outside Ester's originally
mapped P011–P018/P042+ range in `ester_warning_wording_map.json`), so the
wording above was adapted from the P017/Q051/Q065 source-of-truth text rather
than copied from an existing P020 entry.

## Investigation

Reproduced on the real Sample B fixture (`get_builtin_sample("ester_sample_b")`
→ `run_pdf_audit_full`).

### Page 71 — root cause

Page 71 has a genuine Level 3 numbered heading: a bold line containing only
`"3.4.3"` immediately followed by a bold heading-text line. `pdf_title_capitalization.py`'s
generic bold-heading detection (used by P020) has no concept of heading level —
it treats every bold, non-excluded line as if it were a Level 2 (Title Case)
heading, contrary to the module's own documented scope ("Level 3–5: Sentence
case — NOT checked by P020"). `pdf_heading_levels.py` (P027) does have correct
Level 3+ sentence-case logic, but its numbered-pattern regexes require the
number prefix and heading text on the *same* line — which this document's text
extraction does not produce (the number lands on its own line). So neither
rule correctly classified this heading, and P020 fell back to full Title Case
checking. Combined with a text-extraction artifact (words glued together
without spaces after commas: `"Implementation,Experiments,andResults"`), the
word tokenizer read `"and"` and `"Results"` as a single token `andResults`,
which Title Case rules then flagged as needing capitalization — producing the
nonsensical suggestion "capitalize 'andResults' as 'AndResults'".

### Page 80 — root cause

Page 80's finding is a table title (`details["source"] == "caption"`), and
most of the remediation-string builders already branch correctly on `source`
to distinguish "table title" from "heading" text
(`title_case_subject_kind`, `_title_case_subject_and_rule_clause`,
`_p020_title_case_comment`, `_p020_title_case_explanation`). One builder did
not: `title_case_student_preview.py:p020_short_likely_problem` (and its
sibling `p020_short_suggested_fix`'s fallback branch) hardcoded `"In this
heading"` regardless of `source`, so the short, most-visible card text for a
table-title finding said "heading" instead of "table title". This function
feeds both the web card (`report_view.py:_apply_title_case_presentation`) and
the Markdown export (`report_outputs.py:_p020_title_case_individual_comment`).
Separately, none of the four rule-text strings for the table-title branch
mentioned the "no final period" rule, so even a correctly-labeled table-title
finding under-stated the full remediation Ester specified.

There was no cross-wiring with figure-caption remediation: P020 only ever
creates `source == "caption"` items for `caption_type == "table"`
(`detect_pdf_title_like_lines` explicitly skips non-table captions, since
figure descriptions use sentence case and are out of P020's scope), and no
figure-caption wording appears anywhere in the P020 code paths. The bug was a
wrong subject noun ("heading"), not borrowed figure-caption content.

## Fix

1. **`src/njit_auditor/rules/pdf_title_capitalization.py`** — added
   `_LEVEL3PLUS_NUMBER_ONLY_RE` (`^\d+(?:\.\d+){2,4}$`, i.e. 2+ dots = Level
   3/4/5). `detect_pdf_title_like_lines` now tracks, across each page's lines
   in reading order, whether the immediately preceding bold line was a
   Level 3+ number-only line; if so, the following bold heading-text line is
   excluded from P020 entirely (matching the module's own documented scope).
   Level 2 number prefixes (single dot) are unaffected — those headings
   remain Title Case-checked exactly as before.
2. **`src/njit_auditor/title_case_student_preview.py`** —
   `p020_short_likely_problem` and `p020_short_suggested_fix` now take a
   `source` keyword (default `"heading"`, preserving old call sites) and use
   `title_case_subject_kind(source)` to say "table title" instead of always
   saying "heading".
3. **`src/njit_auditor/report_view.py`** and **`src/njit_auditor/report_outputs.py`**
   — updated the two call sites to pass `details.get("source", "")` through.
4. **Rule-text wording** expanded to Ester's full table-title language in the
   four places that build it: `report_view.py:_title_case_subject_and_rule_clause`,
   `polished_comments.py:_p020_title_case_comment`,
   `finding_explanations.py:_p020_title_case_explanation`, and
   `report_outputs.py:_P020_TITLE_CASE_SUBJECT_AND_RULE` (unused constant,
   updated for consistency) — now: *"NJIT requires table titles to use Title
   Case (every word capitalized except prepositions, conjunctions, and
   articles) and table titles must not end with a period."*

No detector behavior changed for Level 2 headings, non-table captions, or any
rule other than P020's own bold-heading detection loop.

## Result

- Sample B page 71: the `P020` finding is gone — the heading is now correctly
  recognized as Level 3+ (out of P020's scope) instead of being misread as a
  Level 2 Title Case violation, so no nonsensical "capitalize 'and'"-style
  suggestion is possible.
- Sample B page 80: the single `P020` finding now says "table title"
  everywhere (short card comment, suggested fix, detailed explanation), never
  "heading" or "figure", and states the full title-case-with-exceptions +
  no-final-period rule.
- A bold heading identical to page 71's, without a preceding Level 3+ number
  line, is still checked (regression-tested) — the exclusion is targeted to
  the specific two-line numbered-heading pattern, not a blanket suppression.
- A bold heading preceded by a Level 2 number line (single dot) is still
  checked (regression-tested) — the exclusion only applies to 2+ dots.

## Files Changed

- `src/njit_auditor/rules/pdf_title_capitalization.py`
- `src/njit_auditor/title_case_student_preview.py`
- `src/njit_auditor/report_view.py`
- `src/njit_auditor/report_outputs.py`
- `src/njit_auditor/finding_explanations.py`
- `src/njit_auditor/polished_comments.py`
- `tests/test_pdf_rules.py`
- `tests/test_ester_sample_a_correctness.py`
- `tests/test_live_review_warning_fixes_batch1.py`
- `docs/status/ester_sample_b_p020_specific_remediation.md` (this file)

## Tests

Added:

- `test_p020_level3_numbered_heading_excluded_from_title_case_check` —
  synthetic PDF: bold `"3.4.3"` line + bold heading text that would otherwise
  warn; asserts no `P020` finding.
- `test_p020_same_heading_text_without_level3_prefix_still_warns` — same
  heading text alone still warns (targeted, not blanket, exclusion).
- `test_p020_level2_numbered_heading_not_excluded` — boundary check: a
  Level 2 (single-dot) number prefix does not trigger the exclusion.
- `test_p020_short_main_card_wording_table_title_source` — unit test locking
  `p020_short_likely_problem`/`p020_short_suggested_fix`'s `source="caption"`
  branch to say "table title", never "heading".
- `test_ester_sample_b_p020_page71_third_level_heading_not_flagged` — real
  Sample B fixture: page 71's `P020` finding is cleared.
- `test_ester_sample_b_p020_page80_table_title_remediation_is_table_specific`
  — real Sample B fixture: page 80's `P020` finding wording is table-specific,
  never mentions "heading" or "figure", and includes the period/word-case
  rules.

Existing P020/P027/table-title coverage continues to pass unchanged.

Targeted:

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m ruff check .
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q \
  tests/test_ester_sample_a_correctness.py \
  tests/test_pdf_rules.py -k 'p020 or title_case or table'
```

Full suite:

```bash
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q
```

Result: 2681 passed (2675 pre-existing + 6 new), ruff clean.

## Deferred / Still Open

Per `docs/status/ester_sample_b_feedback_audit.md`:

- P011 margin false positives (pages 1, 24, 39).
- P019 highlight targeting + document-level numbering presentation.
- P038 Acknowledgements false positive (page 9).
- P063 font-formatting / highlight targeting (page 5).
- Duplicate section presentation — resolved separately in PR #486.
- P051 category rename — resolved separately in PR #485.
