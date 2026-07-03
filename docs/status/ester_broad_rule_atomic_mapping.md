# Ester Broad-Rule Atomic Mapping

> **Purpose:** Translate [ester_broad_presentation_split_plan.md](ester_broad_presentation_split_plan.md)
> into an implementation-ready mapping. For each broad rule, this document
> answers: **which existing `issue_type` or metadata field can honestly
> support which Ester-style binary question and remediation?**
>
> This mapping exists so future implementation does not guess — it verifies
> against the actual detector source (read-only inspection, no edits) what
> metadata already exists versus what would require new detector work.
>
> The target style is Ester's Excel/Google Sheet style: **one warning, one
> binary question, one issue, one direct remediation.** The first
> implementation should use **existing detector outputs and metadata only**
> — detector changes are out of scope for this document and for the first
> implementation PR it recommends.
>
> This document is **documentation-only**. It does not implement any split.
>
> **Recorded:** 2026-07-03 (post–PR #423 merge; main @ `0daa6ac4bc4414bdc88c189a736e4f7b67b8eb02`)
>
> **Related:** [ester_broad_presentation_split_plan.md](ester_broad_presentation_split_plan.md) ·
> [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md) ·
> [ester_policy_review_p021_p026.md](ester_policy_review_p021_p026.md)

---

## Mapping table format

Each rule section below uses this table:

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|

`Can be presentation-only?` values: `yes` / `probably` / `no` / `unknown`.
`Risk` values: `low` / `medium` / `high` / `PR407-sensitive` / `policy-sensitive`.

---

## P014 mapping — Front-matter heading style

**Verified from `src/njit_auditor/rules/pdf_headings.py`:** P014 emits only
**two** `issue_type` values regardless of page —
`frontmatter_heading_layout_issue` (any combination of failures) and
`frontmatter_heading_not_centered` (centering is the only failure). The page
identity comes from `details["heading"]` (the literal heading text, e.g.
`"APPROVAL PAGE"`, `"BIOGRAPHICAL SKETCH"`) and `details["source_q_rule_id"]`
(Q013/Q021/Q036/Q047/Q061/Q070), plus per-dimension booleans `centered`,
`near_top`, `bold`, `all_caps`. **The page split is a metadata split, not an
issue_type split** — this is the opposite of P018/P027 where issue_type
already encodes the split.

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P014 | `frontmatter_heading_layout_issue` / `frontmatter_heading_not_centered`, keyed by `details.heading` == "APPROVAL PAGE" | Single umbrella question for all 6 pages | Is the APPROVAL PAGE heading in all caps, bold, centered, and at the top of the page? | Format the APPROVAL PAGE heading in all caps, bold, and centered at the top of the page. | yes | `details.heading`, `details.source_q_rule_id` (already present) | low | Q013 |
| P014 | same, `details.heading` == "BIOGRAPHICAL SKETCH" | (same umbrella) | Is the BIOGRAPHICAL SKETCH heading in all caps, bold, centered, and at the top of the page? | Format the BIOGRAPHICAL SKETCH heading in all caps, bold, and centered at the top of the page. | yes | same | low | Q021 |
| P014 | same, `details.heading` == "ACKNOWLEDGEMENTS" | (same umbrella) | Is the ACKNOWLEDGEMENTS heading in all caps, bold, centered, and at the top of the page? | Format the ACKNOWLEDGEMENTS heading in all caps, bold, and centered at the top of the page. | yes | same | low | Q036 |
| P014 | same, `details.heading` == "TABLE OF CONTENTS" | (same umbrella) | Is the TABLE OF CONTENTS heading in all caps, bold, centered, and at the top of the page? | Format the TABLE OF CONTENTS heading in all caps, bold, and centered at the top of the page. | yes | same | low | Q047 |
| P014 | same, `details.heading` == "LIST OF TABLES" | (same umbrella) | Is the LIST OF TABLES heading in all caps, bold, centered, and at the top of the page? | Format the LIST OF TABLES heading in all caps, bold, and centered at the top of the page. | yes | same | low | Q061 |
| P014 | same, `details.heading` == "LIST OF FIGURES" | (same umbrella) | Is the LIST OF FIGURES heading in all caps, bold, centered, and at the top of the page? | Format the LIST OF FIGURES heading in all caps, bold, and centered at the top of the page. | yes | same | low | Q070 |
| P014 | `frontmatter_heading_layout_issue` vs `frontmatter_heading_not_centered`, cross-cut by `centered`/`near_top`/`bold`/`all_caps` booleans | The two issue_types only distinguish "centering-only failure" from "any other combination" | *(optional, later)* per-dimension questions, e.g. "Is the [PAGE] heading in bold?" | Format the [PAGE] heading in bold. | probably | the 4 boolean detail fields already exist, but a true per-dimension split changes the emitted issue_type semantics, not just display routing | medium | Not required for a first pass — six page-level cards already satisfy Ester's one-question-per-page-row style; a further per-dimension split is a nice-to-have, not a gap. |

**Abstract, Dedication, Copyright Page, Title Page:** P014 does **not**
cover these pages — `find_named_frontmatter_headings` only matches the six
headings above. Abstract/Dedication/Copyright/Title-Page structural checks
already live in other rules (P025 title-page/abstract structure, P034
copyright header, dedication centering/italics in the dedication-specific
rule). Do not add P014 cards for pages P014 never inspects.

---

## P015 mapping — Paragraph indentation

**Verified:** P015's own detector (`pdf_indentation.py`) already emits only
two issue_types — `unexpected_opening_indent` (P015A) and
`missing_later_indent` (P015B) — and **explicitly skips Abstract and
Acknowledgements pages** (delegated to P044 and P043, which are already
atomic and wording-aligned as of Slice 6 / PR #420).

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P015 | `unexpected_opening_indent` (already public card P015A) | Body first paragraph after a heading is unexpectedly indented | Is the first body paragraph after each heading flush-left? | Remove the first-line indent from the first paragraph after each heading. | yes (already done) | `details.paragraph_index` | low | Already split; verify job cards route through the P015A label consistently, not the raw P015 rule_id. |
| P015 | `missing_later_indent` (already public card P015B) | A later body paragraph is missing its expected first-line indent | Are body paragraphs after the first one indented? | Apply a first-line indent to this body paragraph. | yes (already done) | `details.paragraph_index` | low | Already split; same job-card consistency caveat as above. |
| P044 (not P015) | `abstract_first_paragraph_indented` / `abstract_subsequent_paragraph_not_indented` | Abstract paragraph indentation | *(already atomic — Slice 6)* | *(already atomic — Slice 6)* | yes (done) | n/a | low | Do not recreate an "Abstract" card under P015 — it would duplicate P044. |
| P043 (not P015) | `acknowledgements_first_paragraph_indented` / `acknowledgements_subsequent_paragraph_not_indented` | Acknowledgements paragraph indentation | *(already atomic — Slice 6)* | *(already atomic — Slice 6)* | yes (done) | n/a | low | Do not recreate an "Acknowledgements" card under P015 — it would duplicate P043. |

**Recommendation:** P015 needs **no new atomic split** at the detector or
card-definition level — P015A/P015B already exist. The only remaining gap
(per the broad-split plan) is verifying that audit **job cards** on
`/audits/{id}` route through the P015A/P015B labels the same way the public
`/rules` page does, which is a routing-consistency check, not a new split.
**Do not** touch P015 detection or attempt to add Abstract/Acknowledgements
cards here — that would duplicate P043/P044.

---

## P017 mapping — Figure/table caption and title formatting

**Verified from `src/njit_auditor/rules/pdf_captions.py`:** issue_types are
`unexpected_terminal_period`, `missing_terminal_punctuation`,
`possible_sentence_case_issue`, `possible_title_case_issue` — but the same
issue_type name is reused for **both** figure and table contexts; the
figure-vs-table distinction lives in a detail field (context/caption type),
not in a unique issue_type per rule.

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P017 | `possible_sentence_case_issue`, figure context | Combined figure+table case/punctuation question | Is this figure description written in sentence case? | Rewrite the figure description in sentence case. | yes | `details.caption_type` (or equivalent context field) must reliably read "figure" | low | Must not merge with the table title-case card below. |
| P017 | `unexpected_terminal_period` / `missing_terminal_punctuation`, figure context | (same) | Does this figure description end with terminal punctuation? | Add terminal punctuation (a period) to the end of the figure description. | yes | same | low | |
| P017 | `possible_title_case_issue`, table context | (same) | Is this table title written in title case? | Rewrite the table title in title case. | yes | same, must reliably read "table" | low | |
| P017 | `unexpected_terminal_period`, table context | (same) | Does this table title avoid ending with a final period? | Remove the final period from the table title. | yes | same | low | Already effectively covered by P053 (LoT entries) for the LoT-context version; the P017 body-caption version is the remaining gap. |
| — | (no P017 metadata identified) | Figure descriptions single-spaced and justified | Is the figure description single-spaced and justified? | Single-space and justify the figure description. | unknown | not found in `pdf_captions.py`; catalog notes point to P032 for wrapped-line spacing, not justification | medium | Justification is not currently checked by any rule found in this inspection — flag as a possible detector gap, not a presentation-only item, until confirmed. |
| — | (delegated) | Bold "Figure"/"Table" label and number | Is the "Figure"/"Table" label and number in bold? | Format the "Figure"/"Table" label and number in bold. | yes (done elsewhere) | n/a | low | Catalog notes this is partially covered via P050/P055/P056 already — do not duplicate under P017. |

**Recommendation:** the figure-vs-table distinction is the one metadata
gap worth confirming precisely (field name) before implementation; the
case/punctuation split itself is presentation-only once that field is
confirmed.

---

## P018 mapping — TOC/List formatting umbrella

**Verified:** P018 already has the most complete split in the codebase —
`_P018_PUBLIC_CARD_SPECS` in `web_app.py` defines **17 atomic cards
(P018A–P018Q)**, each with `parent_rule_id`, `source_q_rule_ids`,
`issue_types`, a binary `title`, and a `how_to_correct` remediation. The
underlying detectors remain on their own rule_ids (P018 itself for
leaders/page-number-column, plus P024, P032, P036, P039, P042, P046, P048).

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P018 (+P024) | `toc_level_capitalization`, `entry_level="1"` | Bundled TOC capitalization question | *(already atomic — P018A)* | *(already atomic — P018A)* | yes (done) | `details.entry_level` | low | |
| P018 (+P024) | `toc_level_capitalization`, `entry_level="2"` | (same) | *(already atomic — P018B)* | *(already atomic — P018B)* | yes (done) | `details.entry_level` | low | |
| P018 (+P024) | `toc_level_capitalization`, `entry_level` not "1"/"2" (level-3) | (same) | *(already atomic — P018C)* | *(already atomic — P018C)* | yes (done) | `details.entry_level` | low | Catalog notes Q051 level-3 sentence case remains "partial in detector" — confirm coverage before assuming full parity. |
| P018 | `inconsistent_leader_dots` | Umbrella leader-style question | *(already atomic — P018D)* | *(already atomic — P018D)* | yes (done) | n/a | low | |
| P018 (+P032) | `wrapped_entry_internal_spacing`, per level | Umbrella wrapped-spacing question | *(already atomic — P018E/F/G)* | *(already atomic — P018E/F/G)* | yes (done) | `entry_kind` (unknown kinds map to P018E only — a partial gap, per catalog notes) | low | |
| P018 (+P039) | `toc_l2_not_indented_relative_to_l1` / `toc_l3_not_indented_relative_to_l2` / `inconsistent_hierarchy_indent` | Umbrella hierarchy question | *(already atomic — P018H)* | *(already atomic — P018H)* | yes (done) | n/a | low | |
| P018 (+P036) | `toc_inter_entry_spacing_too_tight` | Umbrella spacing question | *(already atomic — P018I)* | *(already atomic — P018I)* | yes (done) | n/a | low | |
| P018 (+P042) | `single_appendix_missing_title` / `multiple_appendix_missing_letter` | Umbrella appendix question | *(already atomic — P018J/K)* | *(already atomic — P018J/K)* | yes (done) | n/a | low | |
| P018 (+P036/P046/P048) | LoT/LoF spacing, entry-number column, page-number column issue_types | Umbrella LoT/LoF formatting question | *(already atomic — P018L–Q)* | *(already atomic — P018L–Q)* | yes (done) | n/a | low | |
| P018/P024/P032/P036/P039/P042/P046/P048 | (all of the above) | **Job cards** on `/audits/{id}` may still show the umbrella rule_id/question instead of the P018A–Q label | Route every job-card display through the same `public_rule_reference_id()` lookup already used for `/rules` | n/a (routing consistency, not new wording) | probably | requires confirming `report_view.py` calls the same lookup for job-card headlines that `/rules` uses | medium | **This is the actual remaining gap for P018** — not new atomics, but ensuring one display path is used everywhere. |

**Already wording-aligned siblings** (do not re-touch): P031, P032, P036,
P039, P040, P046, P048, P049, P050, P053, P054, P055.

**Recommendation:** P018 needs **no new atomics**. The only implementation
work is a job-card routing audit — confirm every code path that renders a
P018/P024/P032/P036/P039/P042/P046/P048 finding for a job (not just
`/rules`) resolves through `public_rule_reference_id()` before display.

---

## P019 mapping — Pagination umbrella

**Verified from `src/njit_auditor/rules/pdf_page_numbers.py`:** P019 emits
`missing_page_number`, `multiple_page_numbers`, `inconsistent_position`,
`mixed_numbering_style` (page-level and document-level, distinguished by
`page_number == "-"`), and `sequence_gap` (emitted twice — once for Arabic
sequences with `expected_or_context` containing `style=arabic`, once for
Roman sequences with `style=roman_lower`). P013 (`page_number_candidate`,
`p013_document_overview`), P028, and P029 are separate rule_ids emitted by
different functions/files, already atomic and wording-aligned.

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P022 (not P019) | n/a | Abstract/Title/Copyright no visible page number | *(already atomic — P022)* | *(already atomic — P022)* | yes (done) | n/a | low | Already a separate rule; do not recreate under P019. |
| P028 (not P019) | `arabic_number_on_frontmatter_page`, `uppercase_roman_on_frontmatter_page`, `roman_number_on_body_page` | Front-matter uses lowercase Roman numerals / body uses Arabic numerals | *(already atomic — P028, Slice 5)* | *(already atomic — P028, Slice 5)* | yes (done) | n/a | low | Already wording-aligned; do not recreate under P019. |
| P029 (not P019) | `roman_sequence_gap`/`repeat`/`decrease` | Front-matter Roman numerals sequential | *(already atomic — P029, Slice 5)* | *(already atomic — P029, Slice 5)* | yes (done) | n/a | low | Already wording-aligned; do not recreate under P019. |
| P013 (not P019) | n/a | Page numbers bottom-center | *(already atomic — P013, Slice 1)* | *(already atomic — P013, Slice 1)* | yes (done) | n/a | low | Already wording-aligned; do not recreate under P019. |
| P019 | `sequence_gap`, `expected_or_context` contains `style=arabic` | Combined "page-number candidate sequence" wording, arabic and roman folded together | Does the body page numbering increase by exactly one on every numbered page? | Renumber this page (or restore missing pages) so the body Arabic sequence is consecutive. | probably | need to parse `style=arabic` out of `expected_or_context`, or check whether `observed_sequence`/`expected_sequence` are digit strings — no dedicated clean field exists today | medium | Overlaps conceptually with P028's body-Arabic-style check, but this is a *sequence* check, not a *style* check — keep distinct. |
| P019 | `mixed_numbering_style`, page-level (`page_number` is a real page) | Combined per-page mixed-style wording | Does this page show more than one page-numbering style? | Use one consistent page-numbering style on this page. | yes | `details.observed_style`, `details.expected_style` already present | low | |
| P019 | `mixed_numbering_style`, document-level (`page_number == "-"`) | Combined document-wide mixed-style wording | Does the document use more than one page-numbering style overall? | Use one consistent page-numbering style throughout each numbering section (front matter vs. body). | yes | `page_number == "-"` sentinel already distinguishes this from the page-level case | low | Must stay visibly distinct from the page-level card above — do not merge. |
| P019 | `inconsistent_position` | "Obvious sequence, style, or position inconsistencies" | Is this page's number in the same position as the rest of the document? | Move the page number to the position used throughout the rest of the document. | yes | `details.observed_location`, `details.expected_position` already present | low | |
| P019 | `missing_page_number` | (same umbrella) | Is a page number visible where neighboring pages both have one? | Add a visible page number to this page, matching the surrounding pages. | yes | context flag `expected_or_context="neighbors_have_plausible_candidates"` already present | low | |
| P019 | `multiple_page_numbers` | (same umbrella) | Does this page show more than one plausible page-number candidate? | Remove the extra page-number text so only one page number appears on this page. | yes | `details.candidate_text`/`plausible_candidate_count` already present | low | |
| — | (no confirmed issue_type found) | Body Arabic numbering starts at 1 in Chapter 1 | Does Arabic body numbering start at 1 on the first body page (Chapter 1)? | Set the Arabic page number on the first body page (Chapter 1) to 1. | no | not found in P019, P028, or P013 during this inspection | high (needs-new-atomic-detector, to be reconfirmed) | This specific check ("starts at 1 in Chapter 1," not just "sequential") was **not** located in any P019/P028/P013 code path inspected here. Do not assume it's covered — confirm with a targeted search before starting implementation, since it may need new detector work. |

**PR #407 sensitivity:** P037 (per-section fixed-template Roman numerals,
e.g. Biographical Sketch = iv) is **not** part of P019 and must not be
folded into any P019 split. Its expected values are computed dynamically
from the preceding page as of PR #407 — any future wording referencing
"expected Roman numeral" values must describe the *computed* expectation,
never a hard-coded numeral.

---

## P020 mapping — Heading-level formatting

**Verified from `src/njit_auditor/rules/pdf_title_capitalization.py`:**
P020 emits a **single** issue_type, `possible_title_capitalization_issue`,
distinguished only by `details["source"]` — which is `"heading"` (a bold,
Level-2-like line) or `"caption"` (a table-title line). **P020 does not
have level-specific metadata for Levels 1, 3, 4, or 5** — it structurally
never fires on those, by design (Level 1 is all-caps and covered by P014;
Level 3+ is sentence case and covered by P027).

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P020 | `possible_title_capitalization_issue`, `details.source == "heading"` | Single title-case question covering headings and table titles together | Is this Level 2 heading written in title case? | Capitalize this Level 2 heading in title case. | yes | `details.source`, `details.flagged_word`, `details.corrected_word` already present | medium | Overlaps P027's `level2_title_case_issue` — confirm the two rules don't both fire on the same line before splitting; if they can, the split must make that overlap visible, not hide it. |
| P020 | `possible_title_capitalization_issue`, `details.source == "caption"` | (same) | Is this table title written in title case? | Capitalize this table title in title case. | yes | same | low | Overlaps conceptually with P017's table-title-case target — implementation must pick one owner or clearly differentiate ("table title" vs. "table caption") to avoid a duplicate card. |
| — (not P020) | n/a | Level 1 heading capitalization | *(owned by P014, ALL CAPS check)* | n/a | n/a | n/a | n/a | Not a P020 gap — do not add a "Level 1" P020 card. |
| — (not P020) | n/a | Level 3/4/5 heading capitalization | *(owned by P027)* | n/a | n/a | n/a | n/a | Not a P020 gap — do not add "Level 3/4/5" P020 cards; see P027 mapping below. |

**Recommendation:** the task's original framing ("map P020 to cards by
heading level 1–5") does not match what P020 actually checks. Splitting
P020 honestly means splitting by **context** (heading vs. table title),
not by level — levels 1 and 3–5 are already owned by other rules. Any
future P020 wording must not claim level coverage P020 doesn't have.

---

## P024 mapping — TOC entry capitalization / wording

**Verified from `src/njit_auditor/rules/pdf_toc_list_formatting.py`:**
issue_types are `toc_level_capitalization` (with `details.entry_level`
"1" or "2"), `list_of_tables_title_case`, `list_of_figures_sentence_case`
(with `details.flagged_words`, the PR #407 flagged-word presentation
improvement), and `unexpected_terminal_punctuation`.

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P024 | `toc_level_capitalization`, `entry_level="1"` | Bundled capitalization question | *(already delegated — P018A)* | *(already delegated — P018A)* | yes (done) | `details.entry_level` | low | |
| P024 | `toc_level_capitalization`, `entry_level="2"` | (same) | *(already delegated — P018B)* | *(already delegated — P018B)* | yes (done) | `details.entry_level` | low | |
| P024 | `toc_level_capitalization`, `entry_level` not "1"/"2" | (same) | *(already delegated — P018C)* | *(already delegated — P018C)* | yes (done) | `details.entry_level` | low | |
| P024 | `list_of_tables_title_case` | Bundled TOC/LoT/LoF question | Is this List of Tables entry written in title case? | Capitalize this List of Tables entry in title case. | yes | issue_type already unique to this case | low | Not yet delegated to a P018 card — a gap distinct from the toc_level_capitalization ones above. |
| P024 | `list_of_figures_sentence_case` | (same) | Is this List of Figures entry written in sentence case? | Rewrite the flagged word(s) in this List of Figures entry in sentence case: {flagged_words}. | yes | `details.flagged_words` already present (PR #407) | low | Must preserve the PR #407 flagged-word presentation and page-relative index — do not regress to a vague "some entry on this page" phrasing. |
| P024 | `unexpected_terminal_punctuation` | (same) | Does this entry avoid ending with unexpected terminal punctuation? | Remove the unexpected terminal punctuation from this entry. | probably | need to confirm which list (TOC/LoT/LoF) this applies to via context, since the catalog doesn't specify a distinguishing detail key | medium | Confirm the entry-type context field before writing three separate cards; may only need one card if it's TOC-specific. |
| — | *(appendix entry format)* | n/a | *(already delegated — P018J/K via P042)* | *(already delegated — P018J/K via P042)* | yes (done) | n/a | low | Not a P024 issue_type at all — already owned by P042/P018J/K. |

**PR #407 preservation:** page-relative index presentation and flagged-word
presentation (both visible in `list_of_figures_sentence_case`'s
`details.flagged_words`) must be preserved exactly; no card split should
revert to a vague global list index.

---

## P025 mapping — Required front-matter structural content

**Verified from `src/njit_auditor/rules/pdf_frontmatter_structure.py`:**
P025's real issue_types are `missing_abstract_body`,
`missing_title_page_degree_phrase`, `missing_title_page_institution`,
`sparse_approval_page_content`, `possible_frontmatter_order_issue`, plus a
sixth, `digital_commons_wrapper_pages_detected`, emitted separately in
`audit_runner.py` and explicitly flagged as a **notice, not a problem**
(`_NOTICE_ISSUES` in `report_view.py`).

**Important finding — dead legacy entries:** `finding_explanations.py`,
`issue_type_explanations.py`, and `polished_comments.py` each still carry a
stale `("P025", "title_page_graduation_month_invalid")` dict entry left
over from before this check was split into its own rule. The detector now
emits `title_page_graduation_month_invalid` exclusively under **`rule_id
="P074"`** (`check_pdf_title_page_graduation_month`, already atomic and
wording-aligned since Slice 3 / PR #417). These `P025` entries are
unreachable dead code today — do not use them as a reference when mapping
P025's real scope, and flag them for cleanup in a future wording-only PR
(out of scope here).

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P025 | `missing_abstract_body` | Bundled front-matter-structure question | Does the Abstract page contain body text? | Add body text to the Abstract page below the heading. | yes | issue_type already unique | low | |
| P025 | `missing_title_page_degree_phrase` | (same) | Does the Title Page include the degree phrase (e.g. "Doctor of Philosophy")? | Add the degree phrase to the Title Page. | yes | issue_type already unique | low | |
| P025 | `missing_title_page_institution` | (same) | Does the Title Page include "New Jersey Institute of Technology"? | Add "New Jersey Institute of Technology" to the Title Page. | yes | issue_type already unique | low | |
| P025 | `sparse_approval_page_content` | (same) | Does the Approval Page contain committee member names, titles, and signature lines? | Add the committee member names, titles, and signature lines to the Approval Page. | yes | issue_type already unique | low | |
| P025 | `possible_frontmatter_order_issue` | (same) | Does the Abstract appear before the Table of Contents? | Move the Abstract so it appears before the Table of Contents. | yes | issue_type already unique | low | |
| P025 | `digital_commons_wrapper_pages_detected` | Already framed as a notice | *(keep as a notice, not a binary problem question)* | *(no remediation — informational)* | yes (already correct) | `_NOTICE_ISSUES` frozenset already routes this correctly | PR407-sensitive | **Must never be converted to a problem-style binary card** — this is explicitly a PR #407-protected notice. |
| — (not P025) | n/a | Copyright Page year/author match Title Page | *(owned by P051/P052)* | *(owned by P051/P052)* | n/a | n/a | policy-sensitive | Already-existing, separate rules; not part of P025's scope. Wording for these is deferred per the checkpoint doc (must stay conservative about extraction confidence). |
| — (not P025) | n/a | Approval Page honorifics / advisor order / rank order / external institution info | *(not currently implemented by any rule found in this inspection)* | n/a | no | none found | high (needs-new-atomic-detector or needs-policy-review) | Catalog notes for P068 explicitly list these as **out of scope** ("Manual review may still be needed for honorifics, rank order, NJIT/external ordering..."). Do not assume presentation-only; this needs new detection or is intentionally manual-only. |
| — (not P025) | n/a | Bio Sketch: no birth date/place; no work experience | *(explicitly out of scope, per P066's catalog notes: "high privacy risk")* | n/a | no | none found | policy-sensitive | Deliberately not automated — do not build a card for this without a separate privacy/policy review. |
| — (not P025) | n/a | Bio Sketch degrees/publications most-recent-to-oldest, publication formatting | *(already atomic — P066, P067, P045, P047, Slice 4)* | *(already atomic)* | yes (done) | n/a | low | Already wording-aligned; do not recreate under P025. |
| — (not P025) | n/a | Dedication centered text / italicized text | *(already implemented — dedication centering/italic rule, `dedication_text_not_centered`/`dedication_text_not_italic`)* | *(not yet in an Ester wording slice)* | probably | issue_type already exists per catalog | medium | Not part of P025; belongs to its own dedication-structure rule, listed as an "optional later slice" (P065-adjacent) in the checkpoint doc. |
| — (not P025) | n/a | Acknowledgements paragraph order/content, full names | *(not currently implemented by any rule found in this inspection)* | n/a | no | none found | high (needs-new-atomic-detector) | No existing rule was found in this inspection that checks Acknowledgements *content* (only P043 checks indentation *structure*). Flag as a potential detector gap. |

**Already wording-aligned siblings** (do not re-touch): P041, P042, P045,
P047, P066, P067, P068, P074, P078.

---

## P027 mapping — Numbered heading hierarchy / style

**Verified from `src/njit_auditor/rules/pdf_heading_levels.py`:** issue_type
already encodes the level directly — `level1_not_all_caps`,
`level2_title_case_issue`, `level3_sentence_case_issue`,
`level4_sentence_case_or_punctuation_issue`,
`level5_sentence_case_or_punctuation_issue` — plus `details.inferred_level`,
`details.heading_pattern`, and `details.line_preview` as supporting
metadata. **This is the cleanest split of all nine rules**: the issue_type
values are already one-per-level.

| Rule | Current issue_type / metadata source | Current broad wording or behavior | Proposed Ester-style card question | Proposed direct remediation | Can be presentation-only? | Needed metadata | Risk | Notes |
|---|---|---|---|---|---|---|---|---|
| P027 | `level1_not_all_caps` | Single umbrella question for all levels | Is this Level 1 (CHAPTER) heading in all caps? | Format this Level 1 (CHAPTER) heading in all caps. | yes | issue_type already unique | PR407-sensitive | Requires the line to have passed the bold gate (`_is_bold_line`) added in PR #407 — do not weaken that gate while splitting presentation. |
| P027 | `level2_title_case_issue` | (same) | Is this Level 2 (1.x) heading in title case? | Capitalize this Level 2 (1.x) heading in title case. | yes | issue_type already unique | PR407-sensitive | Overlaps P020's heading-context card (see P020 mapping) — implementation must resolve which rule owns this before shipping both. |
| P027 | `level3_sentence_case_issue` | (same) | Is this Level 3 (1.x.x) heading in sentence case? | Rewrite this Level 3 (1.x.x) heading in sentence case. | yes | issue_type already unique | PR407-sensitive | PR #407 also improved this level's location-label presentation — preserve it. |
| P027 | `level4_sentence_case_or_punctuation_issue` | (same) | Is this Level 4 (1.x.x.x) heading in sentence case and ending with a period? | Rewrite this Level 4 (1.x.x.x) heading in sentence case and add a period at the end. | yes | issue_type already unique | PR407-sensitive | |
| P027 | `level5_sentence_case_or_punctuation_issue` | (same) | Is this Level 5 (1.x.x.x.x) heading in sentence case and ending with a period? | Rewrite this Level 5 (1.x.x.x.x) heading in sentence case and add a period at the end. | yes | issue_type already unique | PR407-sensitive | |

**PR #407 preservation (critical):** the bold-line gate
(`_is_bold_line()` — a numbered-pattern line must be bold before being
classified as a heading candidate at all) is the core false-positive fix.
**Do not** broaden any P027 wording or presentation change in a way that
could be read as encouraging removal or relaxation of that gate. This
applies to the mapping above and to any future implementation.

---

## Duplicate-card avoidance

Broad-rule presentation splits must **not** create duplicate warnings when
a specific, already-atomic P-rule already reports the same issue under a
different rule_id. Concretely, when this mapping is implemented:

- **P019** must not duplicate P013 (bottom-center position), P028
  (front-matter/body style), or P029 (front-matter Roman sequence). If a
  P019 card would say the same thing as one of those, either suppress the
  P019 version for display or convert it into a grouped, document-wide
  summary that explicitly says "see the more specific warning above" — the
  same pattern `report_view.py` already uses to differentiate P019 from
  P028/P029/P037 overlap cases today.
- **P025** must not duplicate P074 (graduation month), P078 (abstract
  forbidden terms / first person), P041 (dedication header text), P045/P047
  (Bio Sketch layout), P066/P067 (Bio Sketch ordering), or P068 (Approval
  Page structure) — those rules already report their specific issues
  atomically. P025's remaining, non-duplicated scope is exactly the five
  real issue_types listed in its mapping table above, plus the
  `digital_commons_wrapper_pages_detected` notice.
- **P018** must not duplicate P031, P032, P036, P039, P040, P046, P048,
  P049, P050, P053, P054, or P055 — all of these already have their own
  atomic wording (several delegated into P018A–Q, several wording-aligned
  independently in Slices 2–3). The P018 split work is display routing, not
  new cards.
- **P020** and **P027** must not both present a card for the same physical
  heading line when a Level-2 heading could conceptually be checked by
  either rule's title-case logic — implementation must pick one owner (most
  likely P027, since its `issue_type` values are level-specific and its
  `pdf_heading_levels.py` docstring already states it is "supplementary to
  P020 (adds coverage for non-bold PDFs)" for Level 2) or clearly
  differentiate the two in wording (e.g., "numbered heading" vs. "bold
  heading-like line") before shipping cards for both.
- **P017** and **P020**'s table-title-case card must not both fire as
  separate visible cards for the same table title — pick one owner (P017
  already owns "table titles and LoT entries" per its catalog
  `rule_definition`; P020's caption-context card should likely be treated
  as the *body-title* counterpart to P017's *LoT-entry* version, and the
  wording must make that distinction explicit, not silent).

---

## Recommended implementation order after this mapping

1. **Implement one presentation-only split prototype for the lowest-risk
   broad rule or sub-rule.**
2. **Prefer a broad rule where existing metadata already cleanly identifies
   issue type and remediation.** Based on this mapping, **P014** (six
   page-level cards, keyed cleanly by `details.heading`, all `risk: low`,
   zero PR #407 entanglement, zero overlap with other rules) is the
   strongest first candidate — every card in its table above is `yes` for
   "can be presentation-only" with no open metadata questions. **P027**
   is a close second on pure cleanliness (issue_type already IS the split)
   but carries `PR407-sensitive` risk and a P020 overlap question that
   should be resolved first, per the guardrail below.
3. **Add tests proving structural output invariants** before merging any
   split prototype:
   - `rule_id` unchanged
   - `issue_type` unchanged
   - grouping unchanged
   - anchors unchanged
   - highlight/bbox unchanged
   - only public card / question / remediation wording changes
4. **Do not start with P027, P024, P037, P019, P021, or P026** — each
   carries either a PR #407 sensitivity, a cross-rule overlap question, a
   confirmed metadata gap, or an unresolved policy question that should be
   settled first.
5. **Do not start with a detector change.** Every "no" or "needs-new-
   atomic-detector" row in this mapping (the P019 "starts at 1" check, P025
   Approval Page honorifics/ordering, Bio Sketch birth/work-experience,
   Acknowledgements content) requires its own separate scoping pass, not a
   presentation split.

**First implementation prototype candidate: P014.** The mapping table
above shows all six page-level cards as `yes` / `low risk` with metadata
(`details.heading`, `details.source_q_rule_id`) already present in every
finding. This is the clearest, safest starting point identified in this
document.

---

## Non-goals

- This PR does **not** implement presentation splits.
- This PR does **not** change detectors.
- This PR does **not** change thresholds.
- This PR does **not** change source files.
- This PR does **not** change templates.
- This PR does **not** change tests.
- This PR does **not** change report schema.
- This PR does **not** implement P021/P026.
- This PR does **not** touch P084 or TOC-leader WIP.
