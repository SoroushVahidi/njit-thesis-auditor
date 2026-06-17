# Category/problem page actionability audit

Scope: every category, rule, and issue-type page reachable from the web UI's
problem drill-down (`/audits/{id}/problems/category/...`,
`/problems/rule/{rule_id}`, `/problems/rule/{rule_id}/issue-type/{slug}`),
plus the main results page's grouped-problem cards. Goal: every page must
explain the *exact* problem, and a PDF action must only appear when it leads
somewhere useful. Triggered by a concrete bug report on P063 (see below).

Page-numbering rules (P013/P019/P022/P028) were already audited and fixed in
a prior pass — see `docs/planning/page_number_finding_wording_audit.md`. This
audit covers everything else.

## Headline bug: P063 (confirmed, fixed in this pass)

`single_appendix_uses_letter_label` is the issue type P063 actually emits
for a single-appendix document whose heading is "APPENDIX A" instead of
"APPENDIX". It had **no entry** in any of the three presentation
dictionaries:

| Layer | File | Had an entry? |
|---|---|---|
| Detailed explanation | `finding_explanations.py` `_EXPLANATION_TEMPLATES` | No |
| Issue-type label/explanation | `issue_type_explanations.py` | No |
| Polished comment | `polished_comments.py` `_ISSUE_TEMPLATES` | No (P063 had zero entries) |

Effect: the finding fell through to the fully generic polished-comment text
("Formatting check P063 flagged issue type '...' on page N.") and the
category page showed the broad "Front matter structure" heading with no
appendix-specific explanation anywhere — exactly the bug report. Fixed by
adding real entries for all four P063 issue types
(`single_appendix_uses_letter_label`, `multiple_appendix_missing_letter`,
`appendix_letter_sequence_gap`, `appendix_letter_sequence_repeat`) across all
three files, with Observed/Expected/What-to-fix wording for the headline
issue type. See "Net changes" below.

## Systemic bugs (affect every category, not just P063)

These were fixed once, generically, rather than per-rule:

1. **`build_group_explanation` ignored `issue_type` entirely.** It only ever
   looked up the rule-level fallback (`_RULE_FALLBACKS[rule_id]`), so the
   main results page's grouped-problem cards showed generic rule-wide text
   even on rules (like P063) that have a precise per-issue-type template.
   Fixed to try the issue-type template first (via `build_detailed_explanation`
   with neutral/absent details), falling back to the rule-level text only
   when no specific template exists.
2. **Category cards hid the exact issue type.** On a category page
   (`group_kind == "category"`), the example card title showed only
   `rule_id · rule_title` — the specific issue type was available only
   inside a collapsed "Issue type: ..." `<details>` block. Fixed so every
   example/grouped card always shows the issue-type label up front (when
   known), regardless of `group_kind`.
3. **Generic "Open PDF" buttons appeared with no useful destination.** Three
   places offered a plain `/audits/{id}/pdf` link with no page anchor
   whenever a finding/group had no known page or bbox: the per-example
   fallback in `problem_group.html`, the category/rule/issue-type page hero
   action, and the doc-level fallback branch of the grouped-problem card in
   `job.html`. All three now omit the PDF button entirely when no page/bbox
   is available anywhere in the group, relying on the existing "What does
   this mean?" explanation instead.
4. **`frontmatter_structure` category title/description were too broad** to
   tell P063 (appendix heading labels), P065 (dedication centering/italics),
   P066/P067 (biosketch ordering), and P025's structural cases apart. Title
   updated to "Front matter / appendix structure" and the description now
   says the examples below show the exact issue type per finding — combined
   with fix #2 above, this satisfies the "broad category page" acceptable
   outcome from the spec without needing a category split.

## Full per-rule coverage audit

Columns: issue types actually emitted (grep'd from each rule module) →
covered in `finding_explanations.py` / `issue_type_explanations.py` /
`polished_comments.py` → whether the category title is plausible for what
the rule actually checks.

### `frontmatter_structure` category ("Front matter / appendix structure")

| rule | issue types emitted | explanation | issue-type dict | polished comment | category title ok? |
|---|---|---|---|---|---|
| P063 | `single_appendix_uses_letter_label`, `multiple_appendix_missing_letter`, `appendix_letter_sequence_gap`, `appendix_letter_sequence_repeat` | **fixed this pass** | **fixed this pass** | **fixed this pass** | yes |
| P065 | `dedication_text_not_centered`, `dedication_text_not_italic` | yes | yes | no (falls to fallback) | yes |
| P066 | `biosketch_degree_order_suspicious` | no | no | no | yes |
| P067 | `biosketch_publication_order_suspicious` | no | no | no | yes |
| P025 (structural cases) | `sparse_approval_page_content`, `possible_frontmatter_order_issue` | no | no | no | yes |

### `title_page_metadata` category ("Title page")

| rule | issue types emitted | explanation | issue-type dict | polished comment | category title ok? |
|---|---|---|---|---|---|
| P033 | `frontmatter_title_mismatch` | yes | no (only dead keys `title_page_mismatch`/`title_consistency_mismatch`, never emitted) | no | yes |
| P034 | `copyright_top_margin_header_text`, `copyright_year_mismatch`, `copyright_author_mismatch` | yes | partial (missing 1st & 3rd) | partial | borderline — copyright page, not title page |
| P051 | `copyright_year_not_found` | no (string only keyed under P034) | partial (label only) | no | borderline |
| P052 | `copyright_author_not_found` | no (string only keyed under P034) | partial (label only) | no | borderline |
| P041 | `dedication_top_margin_header_text` | yes | no | no | **no — this is a dedication-page check, mis-grouped under "Title page"** |
| Q006 | (no issue_type; doc-level) | n/a | n/a | n/a | yes |

### `list_of_tables_figures_toc` category ("TOC / lists")

22 rule ids (P018, P030–P032, P036, P039, P040, P042, P046, P048–P050,
P053–P062, plus P024's TOC-style cases). Only **P030** has full coverage.
**P061** has a polished-comment template but no explanation entries. All
others (P018, P031, P032, P036, P039, P040, P042, P046, P048, P049, P050,
P053–P060, P062, and P024's TOC cases) have **zero** entries in all three
dicts — every finding from these rules falls through to fully generic text.
Category title is accurate for all of them (they are genuinely TOC/LoT/LoF
checks); the gap is purely missing per-issue-type wording, not mislabeling.

### `abstract_length` / `abstract_structure` / `abstract_language`

| rule | issue types emitted | explanation | issue-type dict | polished comment |
|---|---|---|---|---|
| P021 | none literal — `word_count`+`limit` keys synthesized into `abstract_word_count_exceeded` by a `_resolve_issue_type` helper that exists **only** in `finding_explanations.py` | yes (via synthesis) | no — `issue_type_explanations.py`/the web drill-down route has no equivalent resolver, so the issue-type page for P021 never resolves the synthesized type | no (no `_RULE_FALLBACKS["P021"]` entry was present before this pass for the *issue-type* dict path) |
| P008 | none — `abstract_structure` issue_type is never actually set by the rule's source modules | n/a (dead key) | n/a | n/a |
| Q004 / Q005 | none (details only ever carry `file`/`line`/`suggested_fix`) | n/a | n/a | n/a |

### `references_citations` category

P064 actually emits `references_section_heading_not_detected`,
`references_entry_indentation_inconsistent`,
`references_entry_spacing_inconsistent` — all three dicts only have the
dead key `references_structural_issue`, which P064 never emits. Full gap.

### `margin_or_overflow` / `font_format` / `committee_approval_page`

P011 and P026 are fully covered (no action needed). P068
(`approval_page_advisor_role_label_missing`,
`approval_page_signature_blocks_sparse`) has labels in
`issue_type_explanations.py` but no explanations and no polished-comment
templates.

### `spacing_blank_lines` category

P016 actually emits `excessive_line_gap`, `excessive_paragraph_gap`,
`suspicious_heading_blank_gap` — the first two strings exist in the dicts
but are keyed to `("P023", ...)`, not `("P016", ...)`, so they never match
for a real P016 finding. P023's actual issue type
(`possible_body_text_not_double_spaced`) is itself uncovered everywhere
(only the legacy `body_spacing_issue` string is covered).

### `page_numbering` category — already audited/fixed

P013/P019/P022/P028 fixed in the prior pass. **P082**
(`landscape_page_number_orientation_advisory`,
`landscape_page_number_position_advisory`) and **P037**
(`roman_bio_sketch_not_iv`, `roman_section_wrong_value`) are fully
uncovered. **P029** has a label/explanation for `roman_sequence_gap` only;
`roman_sequence_repeat` and `roman_sequence_decrease` have labels but no
explanations, and no polished-comment templates exist for any of the three.

## Net changes made this pass

1. P063: full Observed/Expected/What-to-fix wording for
   `single_appendix_uses_letter_label`, plus completed coverage for the
   other three P063 issue types, in all three presentation files.
2. `build_group_explanation` now prefers the issue-type-specific template.
3. Example/grouped cards always surface the issue-type label, not just
   inside a collapsed details block.
4. PDF-action policy tightened: no generic, destination-less "Open PDF"
   button at the hero/group level or per-example level; page-known-only
   findings honestly say "Open PDF page" (not "Open highlighted PDF page");
   doc-level/no-page findings show explanation only.
5. `frontmatter_structure` category label/description updated to acknowledge
   the appendix-structure content it contains.

## Deliberately deferred (follow-up work, not done in this pass)

Writing bespoke Observed/Expected/What-to-fix prose for the ~30 remaining
gapped issue types above (mostly the P031–P062 TOC/LoT/LoF family, P066,
P067, P025's structural cases, P064, P082, P037, P068, P016/P023's real
strings, P051/P052) is a large, separate content-authorship effort —
out of scope for this pass, which targeted the P063 bug report plus the
systemic template/policy bugs that affect every category page regardless of
per-issue-type wording. Those findings still get an honest, non-misleading
experience after this pass (rule-specific or generic fallback text, no
misleading PDF button) — they just don't yet get P063-level precision.
