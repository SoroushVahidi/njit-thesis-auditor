# Page Number Actionability Audit

Date: 2026-06-18

Scope:
- Active page-numbering findings shown by the default PDF web audit
- Rules in the `page_numbering` category that can surface in the UI:
  `P013`, `P019`, `P022`, `P028`, `P029`, `P037`
- `P082` is experimental/opt-in and is not part of the default web audit, so it
  is noted but not part of the visible-problem matrix below

Decision summary:
- Ordinary `P013` bottom-area candidates are inventory-only and do not appear in
  problem counts, grouped problem cards, category summaries, or rule summaries.
- Visible page-number findings are normalized into exact student-facing defect
  classes:
  - Missing page number
  - Wrong page-number location
  - Wrong page-numbering style
  - Wrong page-number sequence
  - Duplicate or ambiguous page number
  - Page number should be suppressed
- No default web page-number finding implies a font/size defect because no
  active page-number rule currently checks page-number font or size.

## Rule / issue audit

| rule_id | issue_type emitted by detector | current visible title / label | current visible comment / explanation | classification | specific defect claimed | observed location details | expected location details | observed style details | expected style details | sequence / missing / duplicate / suppressed details | main problem list? | exact wording fix / current outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P013 | `p013_document_overview` | Hidden in default web results | Hidden from problem and inventory views | Pure inventory / summary signal | None | No | No | No | No | No | No | Suppressed completely in default web UI |
| P013 | `page_number_candidate` with one bottom-area candidate | `Detected page-number candidate` | Inventory-only text: detected bottom-area candidate; not counted as a problem | Pure candidate / inventory signal | None | Yes: bottom-area candidate location when present | No | Yes: candidate style when present | No | No | No | Suppressed from problem lists and counts; optional inventory-only handling |
| P013 | `page_number_candidate` with top/outside-bottom candidate | `Wrong page-number location` | Problem: page number appears at `{observed_location}`, expected required bottom position | Likely problem | Wrong location | Yes | Yes: required bottom position | No | No | No | Yes | Visible only when the candidate itself carries a specific location suspicion |
| P013 | `page_number_candidate` with `candidate_count_on_page > 1` | `Duplicate or ambiguous page number` | Problem: multiple page-number-like tokens detected; verify actual number and remove duplicates | Likely problem | Duplicate / ambiguous page number | No | No | No | No | Yes: duplicate / ambiguous | Yes | Visible only when the detector has exact multiple-candidate evidence |
| P019 | `missing_page_number` | `Missing page number` | Problem: auditor did not find a clear page number on page `{page}` | Confirmed problem (heuristic) | Missing page number | No | No | No | No | Yes: missing | Yes | Wording now states the exact missing-number defect and fix |
| P019 | `inconsistent_position` | `Wrong page-number location` | Problem: page number appears at `{observed_location}`, expected required bottom position | Confirmed problem (heuristic) | Wrong location | Yes | Yes | No | No | No | Yes | Detector details were enriched to store observed and expected positions |
| P019 | `multiple_page_numbers` | `Duplicate or ambiguous page number` | Problem: multiple page-number-like tokens detected; verify actual number and remove duplicates | Confirmed problem (heuristic) | Duplicate / ambiguous page number | No | No | No | No | Yes: duplicate / ambiguous | Yes | Visible wording now states the duplicate/ambiguity defect directly |
| P019 | `mixed_numbering_style` | `Wrong page-numbering style` | Problem: page number appears to use `{observed_style}`, expected `{expected_style}` | Confirmed problem (heuristic) | Wrong numbering style | No | No | Yes | Yes | No | Yes | Detector details were enriched with observed/expected style labels |
| P019 | `sequence_gap` | `Wrong page-number sequence` | Problem: detected page number does not follow expected sequence. Observed / Expected shown | Confirmed problem (heuristic) | Wrong sequence | No | No | No | No | Yes: observed + expected sequence values | Yes | Detector details were enriched with explicit observed/expected sequence values |
| P022 | `visible_page_number_on_no_number_page` | `Page number should be suppressed` | Problem: a page number appears on a page type that may need numbering suppressed | Confirmed problem | Numbering appears where it should be suppressed | Yes: candidate top/bottom zone | No | No | No | Yes: suppressed-page status and page type | Yes | Visible wording now states suppression explicitly instead of generic “page number issue” language |
| P028 | `arabic_number_on_frontmatter_page` | `Wrong page-numbering style` | Problem: page appears to use Arabic numerals, expected lowercase Roman numerals | Confirmed problem | Wrong numbering style | No | No | Yes | Yes | No | Yes | Detector details were enriched with observed/expected style labels |
| P028 | `uppercase_roman_on_frontmatter_page` | `Wrong page-numbering style` | Problem: page appears to use uppercase Roman numerals, expected lowercase Roman numerals | Confirmed problem | Wrong numbering style | No | No | Yes | Yes | No | Yes | Exact observed and expected style wording now shown |
| P028 | `roman_number_on_body_page` | `Wrong page-numbering style` | Problem: page appears to use Roman numerals, expected Arabic numerals | Confirmed problem | Wrong numbering style | No | No | Yes | Yes | No | Yes | Exact observed and expected style wording now shown |
| P029 | `roman_sequence_gap` | `Wrong page-number sequence` | Problem: detected page number does not follow expected front-matter Roman sequence | Confirmed problem (heuristic) | Wrong sequence | No | No | No | No | Yes: observed + expected Roman values | Yes | Detector details now include explicit observed/expected Roman labels |
| P029 | `roman_sequence_repeat` | `Wrong page-number sequence` | Problem: detected page number repeats instead of following expected Roman sequence | Confirmed problem (heuristic) | Wrong sequence | No | No | No | No | Yes: observed + expected Roman values | Yes | Visible wording unified with exact sequence language |
| P029 | `roman_sequence_decrease` | `Wrong page-number sequence` | Problem: detected page number decreases instead of following expected Roman sequence | Confirmed problem (heuristic) | Wrong sequence | No | No | No | No | Yes: observed + expected Roman values | Yes | Visible wording unified with exact sequence language |
| P037 | `roman_bio_sketch_not_iv` | `Wrong page-number sequence` | Problem: detected page number does not match the expected section-anchored Roman value | Confirmed problem (heuristic) | Wrong sequence / wrong anchored value | No | No | No | No | Yes: observed + expected section value | Yes | Visible wording now maps to the exact sequence defect class |
| P037 | `roman_section_wrong_value` | `Wrong page-number sequence` | Problem: detected page number does not match the expected section-anchored Roman value | Confirmed problem (heuristic) | Wrong sequence / wrong anchored value | No | No | No | No | Yes: observed + expected section value | Yes | Visible wording now maps to the exact sequence defect class |

## Visible-category mapping

| Visible category | Detector sources |
|---|---|
| Missing page number | `P019:missing_page_number` |
| Wrong page-number location | `P013:page_number_candidate` outside bottom area, `P019:inconsistent_position` |
| Wrong page-numbering style | `P019:mixed_numbering_style`, `P028:*style mismatches*` |
| Wrong page-number sequence | `P019:sequence_gap`, `P029:*`, `P037:*` |
| Duplicate or ambiguous page number | `P013:page_number_candidate` with multiple candidates, `P019:multiple_page_numbers` |
| Page number should be suppressed | `P022:visible_page_number_on_no_number_page` |
| Font or size problem with page number | None in default web audit |
| Pure detected candidate / inventory | `P013:p013_document_overview`, ordinary `P013:page_number_candidate` in the expected bottom area |

## UI count policy

- `Problems found`, `Needs fixing`, `Worth checking`, category counts, and rule
  counts are computed from visible problem findings only.
- Routine `P013` inventory candidates do not contribute to:
  - main summary counts
  - grouped problem cards
  - category summaries
  - rule summaries
  - problem drill-down routes
- Default rule/category drill-down routes return no visible problem page when a
  job has only suppressed `P013` candidate inventory and no exact page-number
  defect.

## Remaining limitations

- No active default page-number rule checks page-number font family or size.
  The UI must not imply that a font/size problem was detected for page numbers.
- `P019` and `P029` remain heuristic checks driven by detected page-number
  candidates. Their wording is exact about the suspicion, but the findings still
  require manual verification.
- `P082` landscape page-number orientation remains experimental and is not part
  of the default web audit. If enabled in a future surface, it needs a separate
  actionability audit before being shown as a student-facing problem.
