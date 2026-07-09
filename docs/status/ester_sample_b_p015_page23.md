# Ester Sample B P015 Page 23 Fix

**Recorded:** 2026-07-09
**Branch:** `fix/ester-sample-b-p015-page23`
**Base:** `main` @ `85c1bf7` (PR #482 merged)

## Scope

Narrow follow-up to PR #482 targeting the one Sample B P015 false positive it
left deferred: page 23, called out explicitly by Ester as high priority
(`docs/status/ester_sample_b_feedback_audit.md`, item SB-04).

Out of scope (left for later, separate branches):

- P011, P019, P038, P023, P020, P051, duplicate spacing, and font-formatting
  Sample B items from the audit.
- Sample B page 34's residual `P015` finding — not called out by Ester and not
  reproducibly the same failure family as page 23; left untouched.

## Root Cause

Sample B page 23 flagged `missing_later_indent` on the line "Eikonal
regularization [8], which enforces the unit gradient constraint and
improves..." — a genuine paragraph continuation, not a new paragraph.

The preceding visual line ("...function behaves as a valid signed distance
field. One widely used strategy is") was returned by text extraction as
**two separate line objects at the identical baseline** (same `y0`/`y1`,
same font, same non-bold/non-italic style), split roughly mid-sentence with
no stylistic signal. `group_lines_into_paragraphs` in
`src/njit_auditor/rules/pdf_indentation.py` sorts lines by `(y0, x0)` and
decides paragraph breaks using a horizontal-distance gate
(`X_GROUP_TOLERANCE_PT` / `FIRST_LINE_INDENT_GROUP_TOLERANCE_PT`). The large
x-jump between the two same-row fragments (108pt → 388pt) exceeded that gate
twice in a row:

1. It ended the in-progress paragraph early at the first fragment.
2. It then rejected the second fragment as a paragraph opener too (still too
   far right), leaving it as a filtered single-line paragraph.
3. The next real continuation line, correctly flush-left, was then read as
   the **first line of a new paragraph** — and flagged for missing the
   first-line indent that later-paragraph bodies are expected to have.

This is a **layout-extraction artifact** (category from the task brief),
distinct from the pages 24/26/27/38 false positives PR #482 already fixed
(continuation-style splits and section-opening sentences).

## Fix

Added `_merge_same_row_fragments` in `pdf_indentation.py`, run once on the
sorted line list before paragraph grouping. It merges two consecutive lines
into one only when **all** of the following hold:

- vertical position matches within 1pt (`SAME_ROW_Y_TOLERANCE_PT`) on both
  `y0` and `y1` — i.e., same baseline;
- the second fragment starts strictly to the right of where the first ends
  (no horizontal overlap, so it isn't a genuine second column); and
- the touching ends share font, bold, and italic state (`_same_run_style`) —
  i.e., no stylistic reason for the split.

That last condition is the important guard. An earlier version of this fix
merged same-baseline fragments unconditionally, which cleared page 23 but
also **newly flagged** Sample B pages 46 and 68 — both LaTeX-style run-in
headings (a short bold phrase ending in a period, e.g. *"Strong–Start
Annealing Principle."*, immediately followed by regular body text on the
same line). Those are a real style boundary, not an artifact, and merging
them fed a differently-styled row into the indent calculation and produced
a *new* false positive. Requiring matching font/bold/italic on both sides of
the join keeps the merge scoped to the observed page-23 pattern only.

## Result

- Sample B `P015` no longer fires on page 23.
- Sample B `P015` page 34 (unrelated, not in Ester's concern list) is
  unchanged.
- Sample A `P015` (page 77, from PR #482's baseline) is unchanged.
- No new `P015` findings appear on Sample B pages 46 or 68 (run-in heading
  guard, regression-tested directly).

## Files Changed

- `src/njit_auditor/rules/pdf_indentation.py`
- `tests/test_ester_sample_a_correctness.py`
- `tests/test_pdf_rules.py`

## Tests

Added:

- `test_ester_sample_b_p015_page_23_false_positive_resolved` — page 23
  cleared, page 34 untouched, on the real Sample B fixture.
- `test_p015_same_baseline_split_line_not_treated_as_new_paragraph` —
  synthetic PDF reproducing the same-baseline split pattern end-to-end
  through `check_pdf_indentation`.
- `test_merge_same_row_fragments_combines_matching_style_runs` — direct unit
  test of the merge helper for the matching-style case.
- `test_merge_same_row_fragments_keeps_run_in_heading_separate` — direct unit
  test guarding against merging a bold run-in heading into its regular-text
  continuation.

Existing PR #482 Sample A/B P015 coverage (pages 24/26/27/38 resolved,
page-number family, P012/P038 visibility) continues to pass unchanged.

Targeted:

```bash
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q \
  tests/test_ester_sample_a_correctness.py \
  tests/test_pdf_rules.py -k 'p015 or merge_same_row'
```

Full suite:

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m ruff check .
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q
```

Result: **2669 passed, 4 warnings** (ruff: all checks passed).

## Deferred / Still Open

Per `docs/status/ester_sample_b_feedback_audit.md`:

- `P011` low-overflow margin false positives (pages 1, 24, 39).
- `P019` highlight targeting + document-level numbering presentation.
- `P038` Acknowledgements false positive (page 9) + per-page front-matter
  handling.
- `P023` figure-description spacing exception (page 82).
- `P020` heading-level vs table-title specific wording (pages 71, 80).
- Duplicate `P016` spacing presentation on page 1.
- `P026` page-5 font highlight/feedback accuracy.
- `P051` category rename (Title page → Copyright page).
- Sample B `P015` page 34 residual finding — not in Ester's concern list;
  left as-is pending confirmation it's a real issue rather than another
  artifact class.
