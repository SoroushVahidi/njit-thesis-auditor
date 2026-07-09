# Ester Sample B P023 Figure-Description Spacing Fix

**Recorded:** 2026-07-08
**Branch:** `fix/ester-sample-b-p023-figure-description-spacing`
**Base:** `main` @ `a6defb3` (PR #486 merged)

## Scope

Narrow follow-up to `docs/status/ester_sample_b_feedback_audit.md` item SB-10.
Ester's Sample B feedback said the P023 body double-spacing check incorrectly
flagged a figure description on page 82 as not double-spaced. Ester's stated
policy (used verbatim below) already exempts figure descriptions:

> Is the text of the document — specifically from Chapter 1 (page 1) through
> the end of the reference section — double-spaced throughout, except for:
> * Text within tables
> * Figure descriptions
> * Bullet points
> * Multi-line titles?

Out of scope (left for later, separate branches): P011, P019, P038, P020,
font false positives, and any other Sample B item tracked in
`docs/status/ester_sample_b_feedback_audit.md`.

## Investigation

Reproduced on the real Sample B fixture: `check_pdf_body_spacing` emitted one
`P023` finding on page 82 (`median line spacing 12.0pt, ratio 1.00`). Page 82
consists entirely of two figure descriptions (Figure 3.3 and Figure 3.4);
there is no ordinary body prose on the page at all.

### Root cause

`src/njit_auditor/rules/pdf_body_spacing.py` already excluded single-line
figure/table captions via `CAPTION_PREFIX_RE`, which matches a full line that
starts with `"Figure N ..."` or `"Table N ..."` followed by caption text on
the *same* line. It did not exclude the rest of a multi-line figure
description — the continuation lines of the caption's own descriptive text —
which read as ordinary long, alpha-dense body lines and were measured for
double-spacing like any other paragraph.

This document's text extraction makes the gap worse: LaTeX inserts a wide
gap between a figure's number and its caption text, and PyMuPDF splits that
into two separate line objects sharing the same visual row (e.g.
`"Figure3.3"` at x=108 and `"Scheduling strategies for the ODW weight..."` at
x=178, both at the same `y0`/`y1`). Neither `CAPTION_PREFIX_RE` (page
82's label has no space before the number) nor `detect_caption_lines` in
`pdf_captions.py` (same reason, plus it only inspects one line at a time)
recognized this pattern, so all of the description's continuation lines fell
through as unexcluded body lines: 10 single-spaced gaps at ratio 1.00,
comfortably past the suspicious-gap and suspicious-fraction thresholds.

Table regions already have an analogous exclusion (`_table_band_ranges`,
anchored on `detect_caption_lines`' single-line `"Table N ..."` match); no
equivalent existed for figures, and the existing table anchor would not have
covered this document's split-row layout either.

## Fix

Added a figure-caption band exclusion to `pdf_body_spacing.py`, parallel to
the existing table-band mechanism but robust to the split-row layout:

- `FIGURE_LABEL_ANCHOR_RE` matches a line containing *only* a bare
  `"Figure N"` / `"Fig. N"` label with nothing else — a layout signature that
  never occurs in ordinary body prose (a body sentence referencing a figure
  always has more words on the same line).
- `_group_into_rows` groups line objects that share a top-of-bbox within
  1pt into one visual row, so a split label + description-start pair is
  treated as a single row.
- `_figure_caption_band_ranges` finds rows whose leftmost line is a bare
  figure-label anchor, then extends the excluded band downward through
  subsequent rows while the row-to-row pitch stays tight (≤ 1.7× the body
  font size, the same ratio already used for table rows) — i.e., for as long
  as the description text continues at single-spacing — and stops at the
  first row whose pitch indicates ordinary double-spaced body text has
  resumed.
- `check_pdf_body_spacing` excludes any line whose vertical center falls
  inside a figure-caption band from the body-line measurement, the same way
  it already excludes table-band lines.

No change was needed to finding wording: `finding_explanations.py`,
`polished_comments.py`, and `web_app.py`'s P023 remediation text already
state the body-text-only scope correctly ("double-spaced... except for
tables, figure descriptions, bullet points, and multi-line titles"). The bug
was purely in the detector measuring figure-description text as body text;
excluding that text keeps every remaining P023 finding correctly scoped to
real body paragraphs, so no wording changes were required.

## Result

- Sample B page 82 no longer emits a `P023` finding.
- Sample B, Sample A, Sample C, and Sample D each emit zero `P023` findings
  after the fix (Sample B's page 82 was the only pre-existing finding across
  the four curated samples).
- Ordinary single-spaced body paragraphs are still flagged: a figure
  description followed by a separate single-spaced body paragraph still
  produces exactly one `P023` finding, measuring only the body paragraph's
  lines (regression-tested directly).
- `P016`, `P064`, table handling, and all other spacing-adjacent rules are
  untouched.

## Files Changed

- `src/njit_auditor/rules/pdf_body_spacing.py`
- `tests/test_pdf_rules.py`
- `tests/test_ester_sample_a_correctness.py`

## Tests

Added:

- `test_ester_sample_b_p023_page82_figure_description_not_flagged` — real
  Sample B fixture: page 82's `P023` finding is cleared.
- `test_p023_figure_description_split_row_not_counted` — synthetic PDF model
  reproducing the split-row label/description layout; a 9-line single-spaced
  figure description alone must not trigger `P023`.
- `test_p023_figure_description_does_not_suppress_ordinary_body_paragraph` —
  synthetic PDF model with a figure description above a separate ordinary
  single-spaced body paragraph; `P023` must still fire, and the measured
  region/line count must reflect only the body paragraph.

Existing coverage that continues to hold unchanged:

- `test_p023_caption_lines_not_counted` (single-line caption exclusion).
- `test_p023_table_region_tight_spacing_not_flagged`,
  `test_p023_table_borders_not_treated_as_body_evidence`,
  `test_p023_table_plus_body_measures_only_body` (table-band exclusion,
  untouched).
- `test_single_spaced_body_warns_p023`,
  `test_p023_body_single_spaced_still_flagged_after_chapter` (ordinary body
  paragraphs still flagged).

Targeted:

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m ruff check .
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q \
  tests/test_ester_sample_a_correctness.py \
  tests/test_pdf_rules.py -k 'p023 or spacing'
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
- P020 heading-level vs table-title specific wording (pages 71, 80).
- P026 page-5 font highlight/feedback accuracy.
- P051 category rename (Title page → Copyright page) — resolved separately
  in PR #485.
- Sample B P015 page 34 residual finding (unrelated, not in Ester's concern
  list).
