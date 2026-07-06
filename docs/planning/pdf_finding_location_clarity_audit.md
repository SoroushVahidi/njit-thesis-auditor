# PDF Finding Location Clarity Audit

> **Historical planning audit (2026-06-15).** This document records the baseline before the
> geometry-driven location-label chain (PR #326 and follow-ons through #357+) landed on `main`.
> Pipeline/UI statements below describe that baseline, not the current post-cleanup report flow.
> For current status, see
> [current_project_state_and_next_steps.md](../status/current_project_state_and_next_steps.md).
> Phase 1 UI location-label plumbing is largely implemented; Phase 2 detector-metadata gaps and
> the privacy allowlist guidance remain useful reference material.


## Scope

Goal: scope the next website improvement so students can more easily locate where each PDF finding happened, without changing detector behavior yet.

Requested output:

- inspect current finding data flow and HTML rendering
- classify current location precision for every public `/rules` PDF web rule
- identify safe Phase 1 quick wins from existing `details`
- identify deeper detector metadata gaps
- recommend a phased implementation plan

## Files inspected

- `src/njit_auditor/models.py`
- `src/njit_auditor/report_view.py`
- `src/njit_auditor/report_outputs.py`
- `src/njit_auditor/web_app.py`
- `src/njit_auditor/templates/job.html`
- `src/njit_auditor/templates/rules.html`
- `src/njit_auditor/templates/help.html`
- all current PDF detector modules under `src/njit_auditor/rules/` that emit P011-P068, P074, or P078 findings

## Current UI pipeline findings

1. PDF detector `details` are preserved in the JSON report, but the website does not render them.
   - `audit_findings_to_json_dict()` keeps PDF `details` intact.
   - `sanitize_report_for_web_export()` only redacts TeX/source findings, not PDF findings.

2. `build_report_view()` reads PDF `details`, but `FindingView` does not keep them.
   - For PDF audits, `FindingView.location_label` is just the page number string.
   - No PDF-specific derived location label is built from `details`.

3. `_run_audit_task()` drops raw PDF `details` when storing in-memory `job.findings`.
   - The job page only keeps `rule_id`, `severity`, `page`, `issue_type`, `category`, `polished_comment`, `suggested_fix`, `triage_tier`, `confidence`, and `location_label`.
   - That means templates cannot currently render existing PDF detector metadata even though it exists earlier in the pipeline.

4. `job.html` renders page links only.
   - Grouped cards show `affected_compact`, which is page-based for PDF findings.
   - Individual rows show the page link plus issue type, but no detector-provided location context.

5. The current privacy posture is strict and explicit.
   - `help.html` says the web UI does not show dissertation body text, titles, author names, or captions.
   - Any Phase 1 UI work should stay within that policy unless the product decision changes intentionally.

6. Catalog note:
   - `/rules` currently shows P021 as a PDF rule.
   - The rule inventory metadata still points at `latex_abstract.py`, but a compiled-PDF implementation exists in `pdf_abstract.py`.
   - This does not block location work, but it is worth cleaning up separately.

## High-level findings

1. The website currently exposes page-only location for almost every PDF finding, even when detectors already know more.

2. Most rules already emit enough structural metadata for a clearer student-facing location label without detector changes.
   - In this audit, 51 of 60 public PDF web rules have a clear Phase 1 improvement path from existing details alone.
   - The remaining 9 can still be labeled a little better, but exact paragraph/entry targeting needs detector work.

3. The safest Phase 1 labels are structural, not textual.
   - Good candidates: heading name, page-number position, section type, paragraph index, entry index, column header type, float number, run start page, compared page roles, invalid month, forbidden term/pronoun.

4. The biggest Phase 2 gaps are rules that currently only know page-level metrics or only know page-level counts.
   - Main examples: P015, P016, P018, P023, P026, P032, P039, P046, P051, P052, P057-P064, P066, P067.

5. Snippet risk is concentrated in a small subset of rules.
   - Medium-risk current fields: `line_preview` in P017, P020, P024, P027.
   - High-risk current field: P012 `content` from PDF annotations/comments.
   - Title/author/copyright line text is intentionally not exposed today and should stay hidden by default.

## Privacy guidance for Phase 1

Recommended allowlist for student-facing location labels:

- canonical heading text already defined by NJIT rules
- section/page type labels such as `Abstract`, `Approval Page`, `Table of Contents`
- single tokens such as page-number candidates, Roman numerals, invalid month, forbidden term, pronoun
- object identifiers such as `Figure 2`, `Table 3`, `entry 4`, `paragraph 2`, `block 1`
- coarse regions such as `top margin`, `bottom-center`, `upper-right`

Recommended default denylist for Phase 1:

- raw annotation/comment content
- full caption lines
- dissertation title text
- arbitrary TOC/List entry text
- author names
- committee names
- long abstract/body/reference snippets

If snippets are shown later, keep them short and opt-in:

- heading text: safe when canonical or tightly normalized
- caption label/number: safer than caption body text
- TOC/List entry title: only if truncated to 80-120 chars and product/privacy policy explicitly allows it

## Rule-by-rule matrix

| Rule ID | Public rule title | Current precision class | Current visible location in website | Useful hidden details already available | Better student-facing location without detector changes? | Detector changes needed? | Privacy risk if showing nearby text/snippets | Recommended location label |
|---|---|---|---|---|---|---|---|---|
| P011 | Possible text outside required margins | Page + region | Page only | `side`; `worst_overflow_pt`; `affected_line_count`; `confidence` | Yes | Only for exact offending line/bbox | None | `Page N, left/right/top/bottom margin` |
| P012 | PDF contains annotations/comments | Page + region | Page only | `annotation_type`; `rect`; `content` | Yes | No for coarse region; yes for anchor to commented text | High if annotation content is shown | `Page N, comment annotation near upper-right` |
| P013 | Page-number candidates near top/bottom zones | Mixed: document-level + page + region/text | Page only, or no page for overview | `location`; `position_type`; `number_style`; `candidate_count_on_page`; `candidate_sample` | Yes | No for better labels; yes for bbox/highlight | Low | `Page N, bottom-center Roman candidate "iv"` / `Document-wide overview` |
| P014 | Named front-matter headings style/layout | Page + affected object | Page only | `heading`; `centered`; `near_top`; `bold`; `all_caps` | Yes | No | Low | `Page N, ACKNOWLEDGEMENTS heading` |
| P015 | Likely indentation issues | Page only | Page only | `issue_type`; `indent_pt`; `expected`; `paragraph_line_count` | Slightly | Yes, for paragraph index or bbox | None | `Page N, paragraph indentation issue` |
| P016 | Likely excessive spacing or blank-line issues | Page only | Page only | `issue_type`; `largest_gap_pt`; `affected_gap_count`; `context` | Slightly | Yes, for anchor line/gap pair | None | `Page N, large blank-gap issue` |
| P017 | Caption/title formatting issues | Page + affected object or snippet | Page only | `caption_type`; `line_preview`; `confidence` | Yes | No for short preview; yes for safe caption-number extraction | Medium | `Page N, figure/table caption` |
| P018 | TOC/LoT/LoF alignment inconsistencies | Page + affected section | Page only | `page_type`; `issue_type`; `affected_entry_count`; `worst_delta_pt` | Yes | Yes, for exact entry index/snippet | None | `Page N, Table of Contents page-number column` |
| P019 | Page-number sequence/style/position inconsistencies | Mixed: page only / page + region/text | Page only | `issue_type`; `candidate_text`; `expected_or_context`; `confidence` | Yes | No for better labels; yes for bbox/highlight | Low | `Page N, multiple page-number candidates` / `Page N, missing page number` |
| P020 | Title-case capitalization issues | Page + affected object or snippet | Page only | `line_preview`; `source`; `detection_reason`; `expected_or_reason` | Yes | No for short preview; yes for safer split fields | Medium | `Page N, Level 2 heading` / `Page N, table title` |
| P021 | Abstract word-count limit | Page only | Page only | `word_count`; `limit`; `inferred_degree_type`; `caveat` | Slightly | No for page label; yes for multi-page abstract span | None | `Page N, Abstract word count` |
| P022 | Visible page number on no-number front-matter page | Page + region + token | Page only | `page_type`; `candidate_text`; `candidate_position`; `candidate_count` | Yes | No | Low | `Page N, approval page, bottom page-number candidate "ii"` |
| P023 | Body text appears not double-spaced | Page only | Page only | `median_body_gap_pt`; `estimated_body_font_size_pt`; `gap_to_font_ratio`; `affected_gap_count` | Slightly | Yes, for paragraph/block anchor | None | `Page N, body-text spacing issue` |
| P024 | TOC/LoT/LoF capitalization and punctuation | Page + affected object or snippet | Page only | `page_type`; `entry_level`; `line_preview`; `expected_or_reason` | Yes | No for short preview; yes for safer split fields | Medium | `Page N, TOC level 2 entry` / `Page N, List of Tables entry` |
| P025 | Required front-matter structural elements | Mixed: page/object + document comparison | Page only | `page_type`; `body_word_count`; `scan_pages`; `substantial_line_count`; `abstract_page`; `toc_page` | Yes | No | None | `Page 1, title page degree phrase missing` / `Page A vs Page B order issue` |
| P026 | Body font compliance | Page only or page + body-text area | Page only | `issue_type`; `observed_summary`; `affected_span_count`; `candidate_count` | Slightly | Yes, for exemplar span/bbox/font anchor | None | `Page N, body font family/size issue` |
| P027 | Numbered heading level-style issues | Page + affected object or snippet | Page only | `inferred_level`; `heading_pattern`; `line_preview`; `expected_or_reason` | Yes | No for preview; yes for bbox/highlight | Medium | `Page N, level 4 heading 3.2.1.1` |
| P028 | Wrong numbering regime by region | Page + region + token | Page only | `candidate_text`; `candidate_style`; `page_region`; `expected_or_reason` | Yes | No | Low | `Page N, front matter page with Arabic page number "2"` |
| P029 | Roman numeral sequence gap/decrease/repeat | Page + token | Page only | `candidate_text`; `candidate_value`; `previous_value`; `expected_value`; `page_region` | Yes | No | Low | `Page N, Roman numeral "vi" expected "v"` |
| P030 | Missing continued heading on TOC/List continuation page | Page + affected object | Page only | `section_type`; `expected_heading`; `observed_heading`; `section_start_page`; `continuation_index` | Yes | No | Low | `Page N, TOC continuation page 2` |
| P031 | LoT/LoF column-header labels/regions | Page + affected object | Page only | `section_type`; `expected_left_label`; `expected_page_label`; `observed_header_labels`; `observed_x0_pt` | Yes | No | Low | `Page N, List of Figures Page header` |
| P032 | Wrapped TOC/List entry internal spacing | Page + affected object | Page only | `section_type`; `entry_kind`; `observed_gap_pt`; `expected_max_gap_pt` | Yes | Yes, for exact entry index/snippet | None | `Page N, wrapped TOC level 2 entry` |
| P033 | Title consistency across Title/Abstract/Approval pages | Document-level comparison | First mismatch page only | `pages_compared`; `mismatch_pages`; `reference_page_role`; title hashes; similarity scores | Yes | No for compared-page label; yes for exact line anchor | None | `Title Page vs Abstract/Approval title mismatch` |
| P034 | Copyright page header/year/author consistency | Mixed: page + region/object | Page only | `observed_text_kind`; `approx_y0_pt`; `copyright_year`; `title_page_year`; author hashes | Yes | No for section label; yes for exact line/bbox | None | `Page N, Copyright Page top margin` / `Page N, year mismatch` |
| P035 | Figure/table float centering and caption position | Page + affected object | Page only | `float_type`; `float_number`; `center_delta_points` | Yes | No | Low | `Page N, Figure 2` / `Page N, Table 3` |
| P036 | TOC/LoT/LoF inter-entry spacing too tight | Page + affected object | Page only | `section_type`; `entry_pair_index`; `gap_points`; `gap_ratio` | Yes | No for pair index; yes for exact entry labels | None | `Page N, TOC entries 4-5 spacing` |
| P037 | Front-matter section Roman anchors | Page + affected object | Page only | `section_key`; `expected_roman`; `observed_roman`; `expected_value`; `observed_value` | Yes | No | Low | `Page N, TABLE OF CONTENTS page number should be vii` |
| P038 | Required front-matter heading missing or not exact | Mixed: document-level + page/object | No page for missing heading; page only for variant | `section_key`; `expected_heading`; `observed_heading_normalized` | Yes | No | Low | `Required heading missing: BIOGRAPHICAL SKETCH` / `Page N, heading should be ACKNOWLEDGEMENTS` |
| P039 | TOC hierarchy indentation | Page + affected object | Page only | `level`; `parent_level`; `observed_delta_points`; `required_delta_points` | Yes | Yes, for exact entry index/snippet | None | `Page N, TOC level 3 indentation` |
| P040 | LoF entry missing terminal punctuation | Page + affected object | Page only | `entry_index`; `line_y`; `terminal_punctuation_required` | Yes | No for entry index; yes for exact entry text | None | `Page N, List of Figures entry 3` |
| P041 | Dedication top-margin header text | Page + region | Page only | `line_y`; `line_x0`; `line_x1`; `top_region_threshold_points` | Yes | No for region label; yes for bbox/highlight | None | `Page N, Dedication top margin` |
| P042 | TOC appendix-entry format | Page + affected object | Page only | `appendix_entry_count`; `entry_index`; `expected_pattern` | Yes | No | None | `Page N, TOC appendix entry 1` |
| P043 | Acknowledgements paragraph indentation | Page + affected object | Page only | `paragraph_index`; `observed_x0`; `expected_left_margin`; `indent_delta_points` | Yes | No | None | `Page N, Acknowledgements paragraph 2` |
| P044 | Abstract paragraph indentation | Page + affected object | Page only | `paragraph_index`; `observed_x0`; `expected_left_margin`; `indent_delta_points` | Yes | No | None | `Page N, Abstract paragraph 1` |
| P045 | Biographical Sketch publication layout | Page + affected object | Page only | `multi_line_block_count`; `entry_index`; `observed_gap_points`; `required_gap_points` | Yes | No | None | `Page N, Biographical Sketch publication entry 2` |
| P046 | LoT/LoF entry-number left-column alignment | Page + affected object | Page only | `section_type`; `entry_count`; `observed_x0_range_points`; `expected_x0` | Yes | Yes, for exact offending entry | None | `Page N, List of Tables entry-number column` |
| P047 | Biographical Sketch bullet single-spacing | Page + affected object | Page only | `block_index`; `line_pair_index`; `observed_gap_points` | Yes | No | None | `Page N, Biographical Sketch bullet block 2` |
| P048 | LoT/LoF page-number right-column alignment | Page + affected object | Page only | `section_type`; `entry_index`; `observed_page_number_x`; `expected_page_number_x` | Yes | No | None | `Page N, List of Figures page number for entry 7` |
| P049 | LoT/LoF Page header right-alignment/bold | Page + affected object | Page only | `section_type`; `column_type`; `observed_x`; `expected_x`; `entry_count` | Yes | No | None | `Page N, List of Tables Page header` |
| P050 | LoT/LoF left header bold | Page + affected object | Page only | `section_type`; `column_type`; `style_signal`; `font_metadata_available` | Yes | No | None | `Page N, List of Figures Figure/Table header` |
| P051 | Copyright year present | Page only | Page only | `copyright_marker_detected` | Slightly | Yes, for year-line anchor | High if raw nearby text is shown | `Page N, Copyright Page year not found` |
| P052 | Copyright owner/author present | Page only | Page only | `copyright_marker_detected`; `year_detected` | Slightly | Yes, for author-line anchor | High if raw nearby text is shown | `Page N, Copyright Page author not found` |
| P053 | LoT entry has terminal period | Page + affected object | Page only | `section_type`; `entry_index`; `terminal_punctuation` | Yes | No | None | `Page N, List of Tables entry 5` |
| P054 | TOC entry has terminal period | Page + affected object | Page only | `section_type`; `entry_index`; `terminal_punctuation` | Yes | No | None | `Page N, TOC entry 12` |
| P055 | LoT entry says Figure / LoF entry says Table | Page + affected object | Page only | `section_type`; `entry_index`; `observed_entry_type`; `expected_entry_type` | Yes | No | None | `Page N, List of Figures entry 4 starts with Table` |
| P056 | LoT/LoF numbering-format mix | Page + affected object | Page only | `section_type`; `dominant_format`; `observed_formats`; `format_counts` | Yes | No | None | `Page N, List of Tables numbering format` |
| P057 | LoT/LoF page-number ordering within page | Page + affected object | Page only | `section_type`; `first_inversion_index`; `inversion_count` | Yes | Yes, for exact offending entry pair | None | `Page N, List of Tables page-number order` |
| P058 | TOC page-number ordering within page | Page + affected object | Page only | `section_type`; `first_inversion_index`; `inversion_count` | Yes | Yes, for exact offending TOC pair | None | `Page N, TOC page-number order` |
| P059 | LoT/LoF entry-number ordering within page | Page + affected object | Page only | `section_type`; `first_inversion_index`; `inversion_count` | Yes | Yes, for exact offending entry pair | None | `Page N, List of Figures entry-number order` |
| P060 | TOC section-number ordering within page | Page + affected object | Page only | `section_type`; `first_inversion_index`; `inversion_count` | Yes | Yes, for exact offending TOC pair | None | `Page N, TOC section-number order` |
| P061 | LoT/LoF cross-page entry-number ordering | Section/run-level | First page only | `section_type`; `page_count`; `first_inversion_index`; `inversion_count` | Yes | Yes, for exact page range and offending pair | None | `List of Tables pages N-N+1, cross-page entry-number order` |
| P062 | TOC cross-page section-number ordering | Section/run-level | First page only | `section_type`; `page_count`; `first_inversion_index`; `inversion_count` | Yes | Yes, for exact page range and offending pair | None | `TOC pages N-N+1, cross-page section-number order` |
| P063 | Appendix body-heading label convention | Page + affected object | Page only | `appendix_count`; `letter_found`; `expected_letter`; `found_letter`; `sequence_position` | Yes | No | Low | `Page N, APPENDIX heading` |
| P064 | References section heading / entry formatting | Section-level | Heading page only or body-start page only | `heading_type`; `body_start_page`; `section_page_count`; `affected_entry_count`; indent/spacing stats | Yes | Yes, for exact entry ids and end page | None | `References section starting on page N` |
| P065 | Dedication text block centered/italic | Page + affected object | Page only | `center_offset_pt`; `center_offset_ratio`; `text_line_count`; `italic_span_ratio` | Yes | No for block label; yes for bbox/highlight | None | `Page N, Dedication text block` |
| P066 | Biographical Sketch degree ordering | Page only or section-level | Page only | `year_candidate_count`; `first/last candidate year`; `inversion_count` | Slightly | Yes, for exact degree-entry index/snippet | None | `Page N, Biographical Sketch education section` |
| P067 | Biographical Sketch publication ordering | Page only or section-level | Page only | `entry_candidate_count`; `comparable_entry_count`; `first/last entry year`; `inversion_count` | Slightly | Yes, for exact publication-entry index/snippet | None | `Page N, Biographical Sketch publications section` |
| P068 | Approval Page committee/signature blocks | Page + affected object | Page only | `role_label_count`; `advisor_label_present`; date/signature counts; `detected_via` | Yes | No for block-level label; yes for exact block lines/bboxes | None | `Page N, Approval Page committee block` |
| P074 | Title Page graduation month | Page only | Page only | `detected_month`; `valid_months` | Yes | No | Low | `Page 1, Title Page graduation month "June"` |
| P078 | Abstract forbidden terms / first-person pronouns | Page + token | Page only | `term` or `pronoun`; `source_q_rule_ids`; `confidence` | Yes | No | Low | `Page N, Abstract term "paper"` / `Page N, pronoun "we"` |

## Top 10 quick wins from existing details only

1. Add a PDF-specific `location_label` builder before `details` are dropped from the web view pipeline.
   - Best insertion points: `build_report_view()` and/or the serialization step in `_run_audit_task()`.

2. Show exact heading names for front-matter heading rules.
   - Highest-value rules: P014 and P038.
   - Example: `Page 6, ACKNOWLEDGEMENTS heading`.

3. Show paragraph indices for front-matter paragraph-format rules.
   - P043 and P044 already expose `paragraph_index`.
   - Example: `Page 3, Abstract paragraph 2`.

4. Show page-number position/type labels.
   - P013, P019, P022, P028, and P029 already expose enough to say `bottom-center Arabic candidate`, `approval page bottom token`, or `Roman numeral expected v`.

5. Show continuation/run context for multi-page list rules.
   - P030 has `section_start_page` and `continuation_index`.
   - P061 and P062 have `page_count`.

6. Show section/object labels for TOC/LoT/LoF structural rules.
   - P031, P037, P040, P042, P048, P049, P050, P053, P054, P055, P056 already have safe structural fields.

7. Show figure/table identifiers for body-float findings.
   - P035 already has `float_type` and `float_number`.
   - Example: `Page 37, Figure 2`.

8. Show entry/block indices where already available.
   - P045, P047, P048, P053, P054, P055.

9. Show compared-page context for cross-page/document rules.
   - P025, P033, P061, P062, and P064 can all render better than a single arbitrary page number today.

10. Show single-token content only when it is intrinsically safe.
   - P074 invalid month.
   - P078 forbidden term/pronoun.
   - P022/P028/P029 page-number tokens.

## Top 10 deeper changes that need detector metadata

1. P011: add representative offending line bbox and a coarse page region.
   - Current details say which margin side is wrong, but not where on the page the worst line is.

2. P015: add paragraph index and first-line bbox.
   - Right now the rule can only say the page has an indentation issue.

3. P016: add anchor line pair for each large gap.
   - Needed to distinguish `after heading`, `between paragraphs`, or another blank-gap location.

4. P018: store offending TOC/List entry indexes, not just counts.
   - The current rule says a TOC/List page is inconsistent, but not which entry is off.

5. P023: add representative body paragraph or line-pair anchor.
   - This would let the UI jump students to the actual under-spaced area on the page.

6. P026: add exemplar noncompliant span/block metadata.
   - Page-level font counts are useful, but students still do not know what text block to inspect first.

7. P057-P062: store the first offending entry pair and explicit page range end.
   - `first_inversion_index` is a good start but still not a student-facing locator.

8. P064: add references-section end page plus offending entry indexes.
   - Today the rule localizes to the section start, not the specific bad entry or pair.

9. P066 and P067: store exact degree/publication entry indexes.
   - Current output only says the Biographical Sketch page looks out of order.

10. P017, P020, P024, and P027: replace raw preview strings with safer structured snippet fields.
    - Example targets: caption number, heading number, short normalized object label, or explicitly-truncated safe preview.
    - This is mainly a privacy-hardening improvement, not just a localization improvement.

## Proposed implementation plan

### Phase 1: render better labels from existing details only

Scope:

- no detector logic changes
- no export schema change required for JSON download
- only web-presentation plumbing plus derived labels

Recommended work:

1. Preserve PDF location metadata through the UI path.
   - Either keep selected `details` fields in `FindingView`, or derive a final `pdf_location_label` before serialization.

2. Add a small privacy-safe location formatter.
   - Input: `rule_id`, `page`, `issue_type`, and `details`.
   - Output: one short label string and optionally one secondary detail string.

3. Render the label in both:
   - grouped problem cards
   - individual occurrence rows

4. Keep an allowlist by rule/field.
   - Do not expose arbitrary `line_preview` or annotation `content` in Phase 1.
   - Prefer structural fields and single safe tokens.

5. Suggested Phase 1 rule subset for the first PR:
   - P013, P014, P022, P028, P029, P030
   - P031, P037, P038, P041, P043, P044, P045
   - P048, P049, P050, P053, P054, P055, P056
   - P074, P078

Why this subset:

- high student value
- low privacy risk
- already has clear location metadata
- avoids the harder snippet-policy decisions in P017/P020/P024/P027

### Phase 2: add detector metadata for important page-only or count-only rules

Priority targets:

- P011
- P015
- P016
- P018
- P023
- P026
- P057-P064
- P066
- P067

Recommended metadata shape:

- `section_type`
- `object_type`
- `object_index`
- `region`
- `bbox` or normalized page coordinates
- `snippet_safe` only when explicitly privacy-reviewed

### Phase 3: optional visual highlighting / PDF coordinates

If feasible later:

1. Add normalized PDF coordinates to selected findings.
2. Open the PDF at page + highlight region for supported rules.
3. Consider this only after Phase 1 proves the location-label design is useful.

Risks:

- PDF coordinate transforms are easy to get wrong
- highlight overlays add UI complexity
- this should be optional, not a dependency for basic location clarity

## Recommended next PR scope

Recommended next PR: Phase 1 only.

Concrete scope:

1. Add PDF location-label plumbing to the web report view.
2. Render a `Location:` line in grouped and individual result views.
3. Implement safe labels for the low-risk structural rules listed in the Phase 1 subset.
4. Leave raw preview/snippet rules and detector-limited page-only rules for follow-up PRs.

What not to include in that PR:

- detector algorithm changes
- bbox/highlight work
- raw annotation content
- raw caption/title/TOC text previews by default

## Final recommendations

- The next implementation PR should be small and UI-focused, not detector-focused.
- The highest-signal change is not new detection logic; it is stopping the PDF UI pipeline from collapsing everything to `page` only.
- Phase 1 should ship with an explicit allowlist of safe structural fields.
- Phase 2 should normalize location metadata across detectors instead of adding ad hoc one-off fields forever.

## Confirmation

- File added: `docs/planning/pdf_finding_location_clarity_audit.md`
- No detector behavior was changed.
- No report/export behavior was changed.
- No web rendering behavior was changed.
