# Page-number finding wording audit

Scope: P013, P019, P022, P028 (the rules that emit page-numbering findings in
the PDF/web path). Goal: confirm what each rule actually detects, so the web
UI never implies a confirmed defect when only a verification signal was
produced, and so confirmed defects explain the exact problem.

## P013 — page-number candidate detection (`pdf_page_numbers.py`)

- **Confirmed defect or candidate-only?** Candidate-only. P013 has no concept
  of "correct" or "incorrect" — it just records page-number-like tokens and
  their position/style for later rules (P019/P028) or a human to judge.
- **Issue types emitted:** `p013_document_overview` (one doc-level summary
  finding), `page_number_candidate` (one per page with a candidate).
- **Details available per `page_number_candidate` finding:** `location`
  (top/bottom), `position_type` (`bottom_center`/`bottom_right`/`top_center`/
  `top_right`/`other`), `number_style` (`arabic`/`roman_lower`/`roman_upper`/
  `other`), `candidate_count_on_page`, `candidate_sample`,
  `observed_summary`, `confidence`, `triage_tier` (always `informational`).
- **Known vs unknown:** knows observed position/style; does not know the
  "expected" style for that page (front-matter vs body classification is
  P028's job) and does not itself flag sequence/duplicate problems (that's
  P019's job), even though a per-page finding fires once per page regardless
  of candidate count — "multiple candidates on a page" is visible via
  `candidate_count_on_page` but P013 doesn't editorialize about it.
- **Prior bug:** title/explanations said "bottom center or top right" and
  implied that's an NJIT requirement. The canonical guideline only specifies
  bottom placement (0.5" from the bottom edge); there is no "top right"
  allowance and no explicit horizontal-alignment requirement. Wording fixed
  to stop asserting a location rule P013 doesn't enforce and NJIT doesn't
  state.

## P019 — page-number sequence/style validation (`pdf_page_numbers.py`)

- **Confirmed defect or candidate-only?** Confirmed-ish: each finding asserts
  a specific inconsistency (missing/duplicate/inconsistent/mixed/gap) derived
  from comparing candidates against each other, not just reporting a single
  observation. Still heuristic (`confidence: medium`/`low`), so framed as
  "appears to" rather than definitive.
- **Issue types emitted:** `missing_page_number`, `multiple_page_numbers`,
  `inconsistent_position`, `mixed_numbering_style` (per-page and one
  document-level rollup with `page=None`), `sequence_gap`.
- **Details available:** `page_number`, `issue_type`, `confidence`, plus
  type-specific context (`candidate_text` for duplicates,
  `expected_or_context` encoding the dominant position/style/expected vs
  actual sequence values — internal/compact, not meant for direct display).
  Post-processed with `triage_tier`/`p019_triage_category`/`triage_reason`.
- **Gap found:** none of P019's real issue types had a specific
  `polished_comments.py` template — every P019 finding fell through to the
  fully generic `"Formatting check P019 flagged issue type '...' on page
  N."` text. Fixed by adding specific templates for all five issue types.

## P022 — visible page number on a no-number page (`pdf_frontmatter_no_page_number.py`)

- **Confirmed defect or candidate-only?** Confirmed: this rule only fires
  when a named no-number page (abstract/title/approval/copyright) shows a
  page-number-like token, which NJIT explicitly disallows.
- **Issue type emitted:** `visible_page_number_on_no_number_page` (only one).
- **Details available:** `page_type`, `candidate_text`, `candidate_position`,
  `candidate_count`, `source_q_rule_id`, `confidence`, `suggested_fix`.
- **Gap found:** the real issue type had no `polished_comments.py` template
  and no `finding_explanations.py`/`issue_type_explanations.py` entry — the
  module's dictionaries were keyed with a similarly-named but never-emitted
  string (`frontmatter_page_has_page_number`). Fixed by adding entries under
  the real key. The old dead key has no direct test coverage and is left in
  place (harmless, unreachable) rather than removed, to minimize churn.

## P028 — page-numbering regime (front matter vs body) (`pdf_page_numbering_regime.py`)

- **Confirmed defect or candidate-only?** Confirmed: fires only when a
  candidate's numbering style doesn't match the region it's in
  (front-matter pages must use lowercase Roman; body pages must use Arabic).
- **Issue types emitted:** `arabic_number_on_frontmatter_page`,
  `uppercase_roman_on_frontmatter_page`, `roman_number_on_body_page`.
- **Details available:** `candidate_text`, `candidate_style`, `page_region`,
  `expected_or_reason`, `source_q_rule_id`, `confidence`, `suggested_fix`.
- **Gap found:** same pattern as P022 — the real issue types had no
  `polished_comments.py` template (fell through to generic text) and the
  explanation dictionaries were keyed with three placeholder-era strings
  (`frontmatter_page_number_style_issue`, `body_page_roman_number`,
  `frontmatter_arabic_number`) that the real detector never emits. Those
  three placeholder keys *are* exercised directly by existing tests
  (synthetic findings constructed with those exact strings), so they are
  kept as-is; new entries were added alongside them under the real issue
  type strings so real P028 findings also get specific wording.

## Net changes made

1. **P013 title/rule_definition/remediation** — web-only override (existing
   `_RULE_TEXT_OVERRIDES` pattern in `web_app.py`) makes the public title say
   "Page-number candidates detected for verification" instead of "Are there
   page-number candidates near top/bottom zones?", and stops implying P013
   itself verifies placement/style.
2. **P013 polished comment** — `polished_comments.py` now branches on
   `candidate_count_on_page` and `position_type` to produce one of: a normal
   bottom-position verification message, a multiple-candidates message, an
   outside-expected-bottom-area message, or an undetermined-position
   message — instead of one flat, vague template. The per-rule remediation
   line is suppressed for P013 (set to `""` in `_REMEDIATION_OVERRIDES`)
   since the new comment bodies already state the verification action,
   avoiding repeating "verify..." three times in one comment.
3. **P019/P022/P028 polished comments** — added rule/issue-type-specific
   templates so confirmed defects from these rules explain the exact problem
   (missing/duplicate/inconsistent/mixed/gap for P019; wrong style for the
   detected region for P028; visible number on a page that must have none
   for P022) instead of falling through to the fully generic fallback text.
4. **Explanation dictionaries** (`finding_explanations.py`,
   `issue_type_explanations.py`) — corrected the factually wrong "bottom
   center or top right" claim, reframed `page_number_candidate` as a
   verification signal rather than implying a defect, and added missing
   entries for P019's `inconsistent_position`/`mixed_numbering_style`/
   `sequence_gap` and P028's three real issue types and P022's real issue
   type. Mis-keyed dead entries that have no direct test coverage were
   removed (P013-keyed P019 issue types, P022's old key); mis-keyed entries
   that *are* covered by direct tests were kept unchanged.

No rule IDs, thresholds, or detector logic changed. No edits to canonical
rule JSON or raw guideline files. All changes are presentation-layer only.
