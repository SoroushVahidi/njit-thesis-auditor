# Ester Sample B Duplicate Spacing Section Fix

**Recorded:** 2026-07-09
**Branch:** `fix/ester-sample-b-spacing-duplicate-section`
**Base:** `main` @ `6ff0c32` (PR #482, #484, #485 merged)

## Scope

Narrow follow-up to `docs/status/ester_sample_b_feedback_audit.md` item
SB-15 (canonical PR #483 numbering). Ester's Sample B feedback said the
"Spacing / blank lines" section appears twice in the report and that the
report should not repeat the same information.

Out of scope (left for later, separate branches): P011, P019, P038, P023,
P020, P026/P063 font false positives — all still tracked in
`docs/status/ester_sample_b_feedback_audit.md`.

## Investigation

Reproduced on the real Sample B fixture: page 1 emitted **two** `P016`
findings, both in the `spacing_blank_lines` category:

- `excessive_line_gap` (`affected_gap_count: 2`, `largest_gap_pt: 63.7`)
- `excessive_paragraph_gap` (`affected_gap_count: 1`, `largest_gap_pt: 63.7`)

Both landed under the same student-facing category/topic label
("Spacing / blank lines"), on the same page, with the **same** largest gap
value — reading to a student as the identical complaint shown twice. This
ruled out the other hypotheses on the investigation list:

- Not a duplicate category *section* (there is one `spacing_blank_lines`
  topic, as expected) and not a duplicate/near-duplicate label caused by two
  slightly different category keys.
- Not confusion between the page-order section and the topic-grouping
  section — `test_report_section_order_page_before_topic` and
  `test_nav_jump_links_page_order_before_topic` in
  `tests/test_ester_wording_and_page_order.py` already lock in that those
  are one page-order pass and one topic-grouped index, not two copies of the
  same content, and this branch does not touch that ordering.
- It is a `P016`-specific issue, and a real double-emission at the
  **detector** level, not a display/grouping artifact.

### Root cause

In `src/njit_auditor/rules/pdf_spacing.py::check_pdf_spacing`, each page
computes two overlapping gap lists from the same set of line-to-line gaps:

- `excessive_gaps`: gaps over `excessive_gap_threshold = max(30, 3 * median_line_height)`
- `paragraph_gaps`: gaps over `paragraph_gap_threshold = max(42, 4 * median_line_height)`

Because `paragraph_gap_threshold` is always stricter (higher) than
`excessive_gap_threshold`, **any gap large enough to count as a paragraph
gap is, by construction, already counted as a line gap.** Whenever both
`page_issue_findings["excessive_line_gap"]` and
`page_issue_findings["excessive_paragraph_gap"]` are populated for a page,
they are always anchored on the same largest gap — this is a structural
guarantee of the threshold design, not a coincidence specific to this PDF.
The old code appended both findings unconditionally, so any page with a gap
big enough to be paragraph-level always produced two redundant P016 cards.

## Fix

In `check_pdf_spacing`, when a page has both `excessive_paragraph_gap` and
`excessive_line_gap` candidates, drop `excessive_line_gap` and keep only the
more specific `excessive_paragraph_gap` finding. No category, template, or
report-view grouping logic needed to change — deduplicating at the
detector source keeps the web UI, JSON export, and Markdown export
consistent automatically, since none of them re-derive category groupings
independently.

This does not affect pages where only one of the two ever fires (the
common case, and still exercised by existing tests), and does not touch
`suspicious_heading_blank_gap`, `P023`, or any other rule.

## Result

- Sample B page 1 now emits exactly one `P016` finding
  (`excessive_paragraph_gap`), one "Spacing / blank lines" card.
- No other page/rule behavior changed; rule ID `P016` and JSON/Markdown
  schema are unchanged — only which of two mutually-redundant issue types
  is emitted.
- Page-order section still renders before topic grouping (untouched,
  covered by existing tests).

## Files Changed

- `src/njit_auditor/rules/pdf_spacing.py`
- `tests/test_pdf_rules.py`
- `tests/test_ester_sample_a_correctness.py`

## Tests

Added:

- `test_pdf_rules.py::test_p016_paragraph_gap_suppresses_redundant_line_gap` —
  synthetic PDF with one line-level-only gap and one gap crossing both
  thresholds; confirms only `excessive_paragraph_gap` survives.
- `test_ester_sample_a_correctness.py::test_ester_sample_b_p016_page1_no_duplicate_spacing_finding` —
  real Sample B fixture: exactly one `P016` finding on page 1, category
  `spacing_blank_lines`.
- Updated `test_pdf_rules.py::test_repeated_excessive_gaps_grouped_for_p016`:
  its gap pattern also crosses the paragraph threshold, so post-fix the
  single grouped finding is `excessive_paragraph_gap` (still
  `affected_gap_count == 2`) instead of `excessive_line_gap` — the grouping
  guarantee this test checks is preserved, just reported under the more
  specific issue type.

Existing coverage that continues to hold unchanged:

- `test_obvious_large_blank_gap_warns_for_p016` (line-gap-only scenario).
- `test_p016_heading_gap_reported_as_after_heading` (unrelated
  `suspicious_heading_blank_gap` path).
- `test_report_section_order_page_before_topic` and
  `test_nav_jump_links_page_order_before_topic` in
  `tests/test_ester_wording_and_page_order.py` (page-order-before-topic
  layout, untouched by this fix).
- P023 body-spacing tests (different rule, different detector, unaffected).

Targeted:

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m ruff check .
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q \
  tests/test_ester_wording_and_page_order.py \
  tests/test_ui_minor_wording_consistency.py \
  tests/test_web_demo_fixtures.py
```

Full suite:

```bash
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q
```

## Deferred / Still Open

Per `docs/status/ester_sample_b_feedback_audit.md`:

- P011 low-overflow margin false positives (pages 1, 24, 39).
- P019 highlight targeting + document-level numbering presentation.
- P038 Acknowledgements false positive (page 9) + per-page front-matter
  handling.
- P023 figure-description spacing exception (page 82).
- P020 heading-level vs table-title specific wording (pages 71, 80).
- P026 page-5 font highlight/feedback accuracy.
- Sample B P015 page 34 residual finding (unrelated, not in Ester's concern
  list).
