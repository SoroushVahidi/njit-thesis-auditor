# Result-Quality Audit — DigitalCommons Article 4387 (Standard Sample)

**Date:** 2026-06-20
**Branch / commit tested:** `main` @ `02c3528`
**PDF URL audited:** `https://digitalcommons.njit.edu/cgi/viewcontent.cgi?article=4387&context=theses`
(this is the same URL already pre-loaded by the homepage's "Use this URL" example button, `#fill-example-url` — i.e. this PDF is already the app's own designated standard sample, which is why it was chosen here)
**Job ID:** `WfkWfzhOS81pdv0lVVtqoQ`
**Audit type:** `pdf`, generated `2026-06-20T03:50:20.835478+00:00`

This is a **read-only, investigative report**. No detector logic, `report_view.py`,
templates, or any other website behavior was changed to produce it (see
"Validation" at the end). It does not quote any narrative thesis body text —
all examples below are structural elements (headings, table/figure captions,
TOC/List entries, page-footer tokens), consistent with this repo's
`AGENTS.md` guidance.

---

## 1. Headline numbers

| Metric | Value |
|---|---:|
| Total findings (raw, from detectors) | 201 |
| Visible problems (shown on the result page) | 125 |
| Displayed problem **cards** (after same-page/same-template grouping) | 43 |
| Distinct rules triggered | 24 (`P011`–`P068`) |
| Distinct rule × issue-type combinations | 30 |

The gap between 201 raw findings and 125 visible ones is **not a bug** — most
of it is one rule (`P013`, 76 of its 77 raw "page-number-candidate" findings)
being deliberately downgraded to "informational, not a problem" by
`_apply_page_number_presentation()` in `report_view.py` unless the candidate
is ambiguous or in an unusual position. That filter already does, for one
rule, the kind of "don't show 76 near-identical non-problems" suppression
this audit recommends extending elsewhere. It is called out here as a
**positive existing pattern to imitate**, not a problem to fix.

### Visible findings by category (what a student actually sees)

| Category | Visible count |
|---|---:|
| `list_of_tables_figures_toc` | 42 |
| `capitalization_case` | 35 |
| `margin_or_overflow` | 10 |
| `indentation` | 9 |
| `page_numbering` | 5 |
| `spacing_blank_lines` | 4 |
| `table_format` | 4 |
| `title_page_metadata` | 3 |
| `punctuation` | 3 |
| `figure_format` | 3 |
| `heading_title` | 2 |
| `font_format` | 2 |
| `committee_approval_page` | 2 |
| `frontmatter_structure` | 1 |

### Most repeated rule × issue-type combinations (as rendered, i.e. inside the 43 displayed cards)

| Rank | Rule | Issue type | Occurrences | Pages |
|---|---|---|---:|---|
| 1 | P036 | TOC inter-entry spacing too tight | 23 | 12 |
| 2 | P020 | Possible title-case issue | 16 | 1–3, 7 |
| 3 | P020 | Possible title-case issue (different reason code) | 15 | 1–3, 7, 62 |
| 4 | P015 | Missing later-paragraph indent | 8 | 31–34, 36, 40, 43, 69 |
| 5 | P040 | LOF entry missing terminal punctuation | 5 | 15 |
| 6 | P011 | Margin boundary violation (left) | 4 | 1–3, 74 |
| 7 | P036 | LOF inter-entry spacing too tight | 4 | 15 |
| 8 | P011 | Margin boundary violation (right) | 3 | 4–5, 11 |
| 9 | P023 | Body text not double-spaced | 3 | 2, 46, 74 |
| 10 | P017 | Missing terminal punctuation in caption | 3 | 52–54 |
| 11 | P035 | Figure caption not below body | 3 | 52–54 |
| 12 | P018 | TOC/List entry missing page number | 3 | 12, 14–15 |
| 13 | P036 | LOT inter-entry spacing too tight | 3 | 14 |
| 14 | P035 | Table caption not above body | 2 | 48, 56 |
| 15 | P024 | List of Figures sentence-case issue | 2 | 15 |

---

## 2. Method

1. Confirmed the running server (tmux session `web`, not `thesis-auditor-web`
   as initially assumed — see note below), homepage form fields
   (`POST /audits/url`, field `pdf_url`), and submitted the target PDF URL.
2. Job completed synchronously; saved `result_page.html`, `result.json`
   (`/download/json`), and `result.md` (`/download/markdown`) to
   `/tmp/njit_audit_4387/`.
3. Parsed `result.json`'s `metadata`, `grouped_summary` (incl. the
   per-rule triage blocks: `p013_triage`, `p011_margin_triage`,
   `p036_toc_list_spacing_triage`, etc.), `grouped_findings` (46 groups,
   the export-level grouping used for the JSON/Markdown downloads — this
   includes the suppressed P013 candidates), and the flat `findings` list
   (201 raw items with full `details`, including `bbox`, `line_preview`,
   `candidate_sample`, `gap_points`, etc.).
4. Parsed `result_page.html` directly (the actual student-facing render,
   125 visible findings folded into 43 cards) and cross-referenced against
   `src/njit_auditor/report_view.py` and `src/njit_auditor/report_outputs.py`
   to confirm *why* certain fields are or are not shown (not guessing from
   the HTML alone).
5. Fetched four problem-group pages for comparison:
   `/problems/rule/{P036,P013,P020,P011}` and
   `/problems/category/list-of-tables-figures-toc`.
6. Read the relevant detector source (`pdf_toc_list_entry_spacing.py` for
   P036) to determine whether missing detail is a rendering gap (data
   exists, just not shown) or a real detector gap (data was never
   captured).

One process note: the task's suggested command
`tmux capture-pane -t thesis-auditor-web -p -S -80` does not match a real
session; the server actually runs in a tmux session named `web` (confirmed
via `tmux ls`). Used `tmux capture-pane -t web -p -S -80` instead to satisfy
the same intent (recent server log history).

---

## 3. Step 3 — Reading the result page as a student

Walking through `result_page.html` card by card, the **single-occurrence**
cards (28 of the 43) are in reasonably good shape: each has a page number, a
plain-language "what does this mean?" explanation, a coarse on-page location
bucket (e.g. "Body area", "Near page center"), a suggested fix, and either an
"Open highlighted PDF page" or "Open original PDF page" action button. A
student hitting one of these in isolation can act on it.

The problems concentrate in two places:

- **Coarse location labels stand in for already-available precise ones.**
  Every card's "Location:" line comes from `sub_page_location_label()`
  (`src/njit_auditor/pdf_highlight.py:130`), a 14-bucket quadrant grid
  computed purely from the bbox center — by design, "for student orientation
  only" (see the docstring at that line). It is not meant to be the final
  word on location, but right now it *is* the only word on location for most
  rules, even when the underlying finding already has something much more
  specific in `details` (a caption/heading text snippet, a flagged word, an
  overflow distance, a spacing-gap measurement). See §5.
- **Large multi-occurrence groups expand into rows that all look the
  same.** Every card with more than one occurrence has a "Show individual
  occurrences" table. For low counts (2–4) this is fine. For the two largest
  groups — P036's 23-occurrence TOC-spacing group on page 12, and P020's
  16- and 15-occurrence title-case groups — every row in the expanded table
  has an identical "Details" and "Comment" column, differing only by the
  "Problem N" link. A student opening "Show individual occurrences" for the
  page-12 TOC group sees 23 rows that read as 23 verbatim copies of one
  sentence. See §4 for the concrete example and root cause.

---

## 4. Step 4 — Duplicate / grouping analysis

### 4.1 Same rule + same page + near-identical wording, with no per-occurrence differentiation

**Pattern:** P036 (`toc_inter_entry_spacing_too_tight`), page 12, 23
occurrences, card `#problem-55`.

Every row of the "Show individual occurrences" table for this card reads
(verbatim, only the `Problem N` number changes):

> Problem 55 / 56 / 57 ... — Page: 12 — Details: "TOC inter entry spacing too
> tight, review priority: high" — Comment: "Review needed: This check (P036)
> found a possible toc inter entry spacing too tight issue on page 12. Add
> visible double spacing or a blank line between consecutive TOC, List of
> Tables, or List of Figures entries per NJIT formatting guidance..."

**Why they should stay grouped, but need internal differentiation:** these
genuinely are 23 instances of the *same defect pattern* (tight spacing between
consecutive TOC entries), so collapsing them into one card is the right call
— the user's "examples of the same problem" framing is correct here, and
splitting them into 23 unrelated cards would be worse. The actual gap is that
**the underlying finding already carries an `entry_pair_index` (0–22) and a
measured `gap_points` / `gap_ratio` / `required_gap_points` per row**
(confirmed in `details` for each raw finding, e.g. `entry_pair_index: "0"`,
`gap_points: "2.4"`, `required_gap_points: "16.8"`, `gap_ratio: "0.20"`), but
none of that is plumbed into the occurrence table — `report_view.py` reuses
the same `polished_comment` for every row in a group.

**Proposed grouping key (no change needed):** rule + issue_type + page is
already correct and already implemented (`_normalize_grouping_text` +
`_grouping_context_signature` in `report_outputs.py`).

**Proposed student-facing wording for each row:** *"Entries #1–#2 on page
12: gap 2.4pt, needs ≥16.8pt (ratio 0.20×)."* — built entirely from existing
`details` keys, no detector change required.

The same exact pattern, smaller scale, repeats for:
- P036 `lof_inter_entry_spacing_too_tight` (4 occurrences, page 15)
- P036 `lot_inter_entry_spacing_too_tight` (3 occurrences, page 14)
- P040 `lof_entry_missing_terminal_punctuation` (5 occurrences, page 15) —
  has an `entry_index` per row but no per-row differentiation rendered either.

### 4.2 Same rule, different reason codes, rendered as visually separate cards on the same pages

**Pattern:** P020 `possible_title_capitalization_issue` appears as **two
separate cards** with almost-overlapping page lists: one group on pages
1–3, 7 (16 occurrences) and another on pages 1–3, 7, 62 (15 occurrences).
Both cards have the identical title "Possible title-case issue" and the
identical badge styling; the only difference is buried in the
"What does this mean?" text ("a major word ... is not capitalized" vs. "the
first word is not capitalized").

**Why this looks like duplication to a student:** two cards with the same
rule, same category, nearly the same page list, and the same visible title
reads as the auditor reporting the same problem twice. It is not a bug —
they are legitimately different *reasons* (`expected_or_reason:
major_word_requires_capital` vs. `first_word_requires_capital`) — but nothing
in the card header signals that distinction.

**Proposed grouping key:** keep the existing split (it is semantically
correct — "first word" vs. "a later major word" are different things to fix),
but **add the reason code to the visible card title**, e.g. "Possible
title-case issue — first word not capitalized" vs. "— major word not
capitalized", so the two cards read as clearly related-but-distinct rather
than duplicated.

### 4.3 Same category, same page, different rule IDs, visually disconnected

**Pattern:** Page 15 carries three separate cards from three different
rules — P040 (`lof_entry_missing_terminal_punctuation`, 5 occ.), P036
(`lof_inter_entry_spacing_too_tight`, 4 occ.), and P024
(`list_of_figures_sentence_case`, 2 occ.) — all about the List of Figures on
the same page, but they appear in whatever order their rule IDs sort to in
the result page, with no "these are all about your List of Figures on page
15" grouping above the rule level.

**Proposed grouping key:** a page-and-section-level secondary grouping
(`category=list_of_tables_figures_toc` + `section_type=list_of_figures` +
page) purely for *display ordering/sectioning*, not for merging counts —
i.e. keep all three as distinct cards (they are genuinely distinct defects)
but render them adjacently under one "List of Figures (page 15)" sub-heading
so a student fixing the LoF on page 15 sees everything relevant in one place.

### 4.4 Margin findings: grouped correctly, but per-occurrence severity is invisible

**Pattern:** P011 `margin_boundary_violation`, left-margin group (pages 1–3,
74). Per-occurrence `details` show meaningfully different severities —
page 1: `worst_overflow_pt: 36.5`, `affected_line_count: 24`; page 2:
`worst_overflow_pt: 67.3`, `affected_line_count: 15` — but the occurrence
table's "Details" column shows the identical generic text ("Margin boundary
violation / review priority: informational / conf: high / fix: ...") for
every row, with no overflow distance or line count. A student cannot tell
from the table that page 2's violation is nearly twice as bad as page 1's.

**Proposed student-facing wording:** *"Page 2: ~67.3pt past the left margin
across 15 lines."* — already in `details`, no detector change needed. This
matches the gap already flagged generically in
`docs/planning/margin_font_actionability_audit.md` ("Remaining limitations" —
P011 cannot name the offending content type), but the magnitude data is a
narrower, already-available fix that document didn't call out.

---

## 5. Step 5 — Location-precision analysis

| Rule / issue type | Current location wording shown to student | What's missing | Already in `details`? | Detector change needed? | Recommended label |
|---|---|---|---|---|---|
| P020 `possible_title_capitalization_issue` | "Location: Near page center" / "Top of page" | Which heading/caption, and which word needs the capital letter | **Yes** — `line_preview` (the actual caption/heading text) and `expected_or_reason` (e.g. `first_word_requires_capital`) both exist per finding | No | *"Page 56, table caption — capitalize the first word."* (no caption text quoted, per this repo's "no thesis body text" convention) |
| P017 `missing_terminal_punctuation` | "Location: Near page center" | Which caption is missing punctuation | **Yes** — `line_preview` exists (e.g. the figure-caption text) | No | *"Page 52, Figure 4.1 caption — add terminal punctuation at the end."* |
| P024 `list_of_figures_sentence_case` | generic page-level text | Which LoF entry / figure number | **Yes** — `line_preview` exists (the actual LoF entry text) | No | *"Page 15, List of Figures entry for Figure 4.1 — use sentence case."* |
| P011 `margin_boundary_violation` | "Location: Body area" | Overflow magnitude, line count, content type (table/figure/paragraph) | **Partially** — `worst_overflow_pt` and `affected_line_count` exist; content type does **not** | Magnitude: no. Content type: yes (already flagged in `margin_font_actionability_audit.md`) | *"Page 2, left margin: content extends ~67pt beyond the margin across 15 lines."* |
| P035 `figure_caption_not_below_body` / `table_caption_not_above_body` | generic page-level text | Which figure/table number on the page | **Yes** — `float_number` (e.g. `"4.1"`) exists | No | *"Page 52, Figure 4.1 — caption should be below the figure body."* |
| P036 (all three `*_inter_entry_spacing_too_tight` issue types) | "Page 12" only, sometimes "no location" | Which pair of consecutive entries, by name; the actual gap measurement | Gap measurement: **yes** (`gap_points`, `gap_ratio`, `required_gap_points`). Entry text/title: **no** — `pdf_toc_list_entry_spacing.py` only stores `entry_pair_index`, never the line text of either entry | Gap measurement: no. Entry text: **yes**, detector would need to also store e.g. `previous_entry_text` / `next_entry_text` from the already-available `PdfTextLine` objects | Quick win: *"Page 12, entries #1–#2: gap 2.4pt (needs ≥16.8pt)."* Full fix (after detector change): *"Page 12, between 'List of Figures' and the next TOC entry: gap 2.4pt."* |
| P040 `lof_entry_missing_terminal_punctuation` | "Page 15" only | Which LoF entry | No — only `entry_index` (a bare integer) is stored, no entry text | Yes — same fix as P036: capture entry text at detection time | *"Page 15, List of Figures entry #2 — add terminal punctuation."* (until detector change: at least show "entry #2" instead of nothing) |
| P018 `missing_page_number` (TOC/List) | "Page 12/14/15" only | Which entry is missing its page number | No — only `affected_entry_count` (a count) is stored | Yes — needs entry text captured | *"Page 12, table of contents — 1 entry has no page number; check entries in the [section] block."* |
| P013 `page_number_candidate` (the few that surface, e.g. multi-candidate pages) | "Footer area" | The actual detected token (e.g. "iv", "16") and its style | **Yes** — `candidate_sample` and `number_style` both exist per finding | No | *"Page 42, footer: two number-like tokens detected ('16' and 'ii') — verify which is the real page number."* |
| P015 `missing_later_indent` | "Page 31" + generic text | Which paragraph (there can be more than one per page) | Partially — `paragraph_line_count` exists, but no paragraph-start text/position is captured | Yes, if disambiguation across multiple paragraphs per page is wanted | *"Page 31, paragraph of 7 lines starting partway down the page — apply first-line indent."* (no body-text snippet quoted, per this repo's "no thesis body text in docs" convention — same restraint should probably apply to the rendered finding text itself, so this is naturally compatible) |

**Pattern across the table:** for roughly half of the rows, the fix is
**purely a `report_view.py`/template change** — the precise data already
exists in `details` and is computed at detection time, it is simply dropped
when building the polished comment / occurrence-table row. For the other
half (mainly the P036 family and P040/P018's entry-level rules), the
detector genuinely never captures the entry text, so a metadata change in
the rule module is required first.

---

## 6. Step 6 — Result page vs. problem-group pages

Compared `result_page.html` against `/problems/rule/P036`,
`/problems/rule/P013`, `/problems/rule/P020`, `/problems/rule/P011`, and
`/problems/category/list-of-tables-figures-toc`.

**Finding: the rule/category pages do not add precision beyond the result
page — they just re-list the same occurrences as flat "example" cards,
inheriting the exact same gaps.**

Concretely, `/problems/rule/P036` ("Examples of this problem", 30 examples)
renders all 23 page-12 TOC-spacing occurrences as 23 separate `<article>`
cards, each with the same generic "Location: Page 12" and the same comment
text used on the result page — i.e., the page explicitly designed to give a
student worked examples of one rule provides *zero* additional
disambiguating information over the collapsed card on the result page. The
"Examples of this problem" link is valuable for `is_grouped=False` /
low-count cases (e.g. P011's 4 margin occurrences, where each example at
least shows a distinct page number), but for the high-volume TOC/title-case
groups it currently just multiplies the same vague text by N.

`/problems/rule/P013` is the one bright spot: it only shows the few P013
occurrences that survived the visibility filter (the multi-candidate page 42
case), confirming the suppression logic from §1 also applies correctly on
the rule-detail page, not just the result page.

**Conclusion:** any fix to the location/grouping wording belongs in the
shared rendering path used by both the result page and the rule/category
pages (the `FindingView`/`GroupedProblemView` construction in
`report_view.py`), not in the rule/category page template separately — they
already share the same data, so a single fix propagates to all three
surfaces.

---

## 7. Step 7 — Scoring summary (top 15 problem types)

Ratings: Location clarity / Grouping quality / Student usefulness =
good / medium / poor. Fix priority = high / medium / low.

| # | Rule | Issue type | Occ. | Location clarity | Grouping quality | Student usefulness | Fix priority |
|---|---|---|---:|---|---|---|---|
| 1 | P036 | TOC inter-entry spacing too tight | 23 | poor | medium | poor | **high** |
| 2 | P020 | Title-case (major word) | 16 | medium | medium | medium | **high** |
| 3 | P020 | Title-case (first word) | 15 | medium | medium | medium | **high** |
| 4 | P015 | Missing later-paragraph indent | 8 | medium | good | medium | medium |
| 5 | P040 | LOF entry missing terminal punctuation | 5 | poor | medium | poor | medium |
| 6 | P011 | Margin violation (left) | 4 | medium | good | medium | medium |
| 7 | P036 | LOF inter-entry spacing too tight | 4 | poor | medium | poor | medium |
| 8 | P011 | Margin violation (right) | 3 | medium | good | medium | medium |
| 9 | P023 | Body text not double-spaced | 3 | good | good | medium | low |
| 10 | P017 | Missing terminal punctuation (caption) | 3 | medium | good | medium | **high** |
| 11 | P035 | Figure caption not below body | 3 | medium | good | medium | medium |
| 12 | P018 | TOC/List entry missing page number | 3 | poor | good | poor | medium |
| 13 | P036 | LOT inter-entry spacing too tight | 3 | poor | medium | poor | medium |
| 14 | P035 | Table caption not above body | 2 | medium | good | medium | medium |
| 15 | P024 | List of Figures sentence-case issue | 2 | medium | good | medium | **high** |

"Grouping quality: medium" (rather than "poor") for the P036 family reflects
that the *grouping itself* (which findings belong together) is correct; the
deduction is entirely about the occurrence table not differentiating rows.
Rows marked **high** fix priority are ones where the fix is a `report_view.py`
template change with zero detector risk (P020, P017, P024) or a
high-occurrence/high-visibility rule where even a partial fix (entry index +
gap numbers) meaningfully helps (P036).

---

## 8. Quick wins (template/`report_view.py` only — no detector changes)

All of these surface data that already exists in `details` for every
affected finding; none require touching a `rules/*.py` detector:

1. Render `line_preview` (+ flagged word from `expected_or_reason`) for
   P020, P017, and P024 instead of the generic polished comment alone.
2. Render `worst_overflow_pt` + `affected_line_count` per occurrence for
   P011, in both the card meta and the occurrence-table "Details" column.
3. Render `gap_points` / `required_gap_points` / `gap_ratio` /
   `entry_pair_index` per occurrence for the P036 family in the
   occurrence-table rows (the comment can stay grouped; only the per-row
   "Details" column needs to vary).
4. Render `float_number` for P035 (`figure_caption_not_below_body`,
   `table_caption_not_above_body`) so multi-figure/table pages disambiguate.
5. Render `candidate_sample` + `number_style` for the P013 cases that do
   surface as visible problems.
6. Add the reason code (e.g. "first word" vs. "a major word") to the P020
   card title so the two near-duplicate-looking groups read as distinct.
7. Add a `gap_to_font_ratio`/`median_body_gap_pt` line for P023 (data
   already in `details`, currently dropped from the polished comment).

None of these change which findings are grouped or how many problems are
counted — they only enrich what is already shown per occurrence/example.

## 9. Deeper fixes (require detector metadata changes)

These need a `details` key that the detector does not currently emit:

1. **P036** (`pdf_toc_list_entry_spacing.py`) — capture the text of
   `previous_entry`/`next_entry`'s lines (already available as
   `PdfTextLine` objects inside the detector, just not stored) so each
   spacing finding can name the two TOC/LoT/LoF entries it's between.
2. **P040** (LOF/LOT terminal-punctuation detectors) — store the entry text
   alongside the existing `entry_index`.
3. **P018** (missing page number in TOC/List) — store which entry/entries
   are affected, not just a count.
4. **P011** — store a coarse content-type guess (table/figure/paragraph) if
   feasible, per the pre-existing limitation already noted in
   `docs/planning/margin_font_actionability_audit.md`.

## 10. Recommended next PR scope

A single, template-only PR covering §8 items 1–3 (P020/P017/P024 line
preview, P011 overflow magnitude, P036 gap numbers) would address the
highest-occurrence, highest-visibility groups (54 of the 125 visible
findings: 16+15 P020, 23 P036-TOC, 4+3 P011) without touching any detector,
keeping risk low and matching the "no detector logic changes" constraint
this audit itself was run under. The P036/P040/P018 entry-text detector
change (§9) is a reasonable follow-up PR once the template plumbing exists
to consume it.

---

## Validation

This pass added one new file (`docs/planning/digitalcommons_4387_result_quality_audit.md`)
and changed nothing else — confirmed via `git status --short` showing only
this file as new, no modifications to any tracked source, template, or
detector file. No "tiny bug" blocked the audit (the job completed
successfully on the first submission), so per the task's constraint, no code
was touched.

```
python -m pytest -q
```

Result: **1741 passed, 1 warning in 19.88s** (the one warning is a
pre-existing `UserWarning: Duplicate name: 'main.tex'` from
`tests/test_upload_handling.py::test_duplicate_member_paths_rejected`,
unrelated to this report). `git status --short` at the same time showed only
this report file as new; the pre-existing unstaged `AGENTS.md` diff and
untracked `docs/status/ester_feedback_implementation_audit_20260619.md` were
not touched and are not part of this change.
