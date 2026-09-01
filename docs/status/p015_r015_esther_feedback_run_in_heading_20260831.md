# R015/P015 2026-08-31: Youra p101 Run-In Heading Follow-Up

**Date:** 2026-08-31
**Baseline:** R011 checkpoint `090779ed84433dd8541d972eb9ba8037e38c1960`
**Scope:** P015 paragraph-indentation follow-up on the single open item disclosed in
`docs/status/p015_r015_esther_feedback_false_positive_fix_20260825.md` ("Youra page
101 -- investigated in depth"). No other rule touched.

Note on naming: R015 is the human/student/evaluation-facing rule identifier;
P015 is the internal implementation identifier
(`src/njit_auditor/rules/pdf_indentation.py`). Both names refer to the same
detector throughout this document.

## Human feedback

The 2026-08-25 batch disclosed, but deliberately did not fix, a new HIGH
`missing_later_indent` finding that appeared on Youra physical page 101
(printed page 84) as a side effect of that batch's own row-remnant fix. Ester
has now reviewed that specific open item and clarified the structure:

- The auditor was identifying the **wrong line** as the paragraph start.
- The actual paragraph begins with the preceding **bold run-in phrase**,
  "Comparison with the Type 4 SMFR scenario".
- The line the detector had been flagging, "counterpart to the Type 4 SMFR
  configuration...", is ordinary continuation text, not a new paragraph
  start, and must not be reported as an R015 missing-indent violation.

Ester separately observed that bold text without a section number should not
appear, because bold is reserved for headings. Per the task brief, that
observation is audited for rule ownership (see below) but **not** folded
into this R015 fix.

## Reproduction (at R011 checkpoint, before this fix)

Youra physical page 101, real PDF
(`data/evaluation/private/5_Youra_Shin_PhD_Dissertation_Document_3rd review.pdf`):

```
{'page_number': '101', 'issue_type': 'missing_later_indent', 'indent_pt': '0.0',
 'expected': 'first_line_indent_approx_36pt', 'paragraph_line_count': '6',
 'paragraph_index': '3', 'bbox': '108.4,376.1,540.4,388.1', 'confidence': 'high', ...}
```

Raw layout around the affected row (all at font `LMRoman12-*`, size 11.96):

| # | y0-y1 | x0-x1 | style | text |
|---|---|---|---|---|
| 10 | 311.6-323.5 | 108.4-249.3 | regular | "andionosphericconvection." (end of prior paragraph) |
| 11 | 352.2-364.2 | 108.4-365.4 | **bold** | "Comparison with the Type 4 SMFR scenario" |
| 12 | 352.2-364.2 | 377.4-540.4 | regular | "Case 1 provides an observational" (same row as #11) |
| 13 | 376.1-388.1 | 108.4-540.4 | regular | "counterparttotheType4SMFRconfigurationdescribedbyParketal.(2018),in" |
| 14-19 | ... | 108.4-... | regular | remaining continuation lines |

Reconstructed paragraph sequence (before fix): line 11 alone (dropped, <2
lines); line 12 alone (dropped, <2 lines); line 13 becomes the misread "first
line" of a 6-line paragraph (13, 14, 16, 17, 18, 19), flush-left (0.0pt
indent) on a page whose established style is ~28-40pt indents ->
`missing_later_indent`.

## Root cause

`_merge_same_row_fragments` correctly refuses to merge line 11 (bold) and
line 12 (regular) into one text line -- they share a row but differ in
style, exactly the run-in-heading guard that must hold (merging them would
corrupt the heading's own readable text). But paragraph *grouping* had no
mechanism to recognize that line 12 -- and everything that follows it -- is
still the *same paragraph* the bold segment opens. Line 12's own x0 (377.4,
wherever the bold phrase happened to end) reads as a fresh, far-off paragraph
start; grouping's existing generous first-line tolerance (96pt) is not
enough to bridge it, so line 12 is orphaned and dropped, and line 13 --
genuinely flush-left continuation text -- is misread as the paragraph's
effective first line.

This is a **distinct root cause** from the 2026-08-25 batch's row-remnant
fix (a dropped short/symbol-heavy extraction fragment). Here nothing is
dropped for being unusable -- both line 11 and line 12 are independently
full, usable text. The mechanism is a run-in-heading-adjacent orphan, exactly
as disclosed (not assumed) in the prior status doc.

## Similar-case corpus audit

A same-row bold-lead / regular-continuation geometry scan (before applying
any style/section-number/paragraph-membership filtering) across all seven
evaluation PDFs found this raw shape in several places -- most are **not**
genuine run-in headings (table/numeric data rows, biographical fields,
inline equations) and are unaffected by paragraph grouping either way:

| document | pattern source | current P015 behavior |
|---|---|---|
| Youra p89, 91, 94, 101, 105 | genuine bold run-in headings (LaTeX `\paragraph{...}`-style) | only p101 had a finding before the fix; none after |
| Anthony p6, 60, 86, 130 | birth-date fields / numeric table rows (not headings) | 0 findings, unaffected |
| Muyeed p24-73 (many) | genuine bold run-in headings, several numbered (e.g. "2.1.3.2 Nondeterministic algorithms.") | 1 finding (p117, unrelated) before and after |
| Philip p50 | equation/symbol fragment (not a heading) | 6 findings before and after, byte-identical |
| Praneeth p80-102 | genuine numbered run-in headings (e.g. "3.2.2.3 MS conditions.") | 0 findings before and after |
| Sebastian | none found | 0 findings, unaffected |
| Patrick p17-63 | inline equations/symbols (not headings) | 0 findings, unaffected |

The real-corpus before/after run (below) confirms the fix is general: it
touches exactly one page across all seven documents (Youra p101) and leaves
every other page's findings byte-for-byte identical, despite the corpus
containing many other genuine run-in headings (Muyeed, Praneeth) that
exercise the same new code paths without producing any new or changed
finding.

## Fix (`src/njit_auditor/rules/pdf_indentation.py`)

1. **`_is_run_in_heading_lead`** (new): true for a bold-styled line sharing a
   physical row (via the existing `_vertical_overlap_fraction`) with a
   following, differently-styled (non-bold) line -- the same geometry
   `_merge_same_row_fragments` already uses to *refuse* to merge text, used
   here instead to identify the row's true left edge for grouping purposes.
   Explicitly excludes a bare section-number-only fragment (e.g. "2.1.3.2")
   as a candidate lead -- see "Regression found during validation" below.
2. **`_effective_row_start_x`** (extended): the existing row-remnant search
   window also accepts a run-in-heading lead as a correction source, but
   *without* `MAX_ROW_REMNANT_ABSORPTION_GAP_PT` (that bound is calibrated
   for short dropped fragments, not a full heading phrase's width -- Youra's
   own heading phrase spans ~257pt before the continuation starts).
3. **`_paragraph_starts_with_run_in_heading`** (new) +
   **`_find_heading_exempt_paragraph_indices`** (extended): a paragraph
   whose own first line is a bold run-in heading is now exempt from the
   missing-indent checks -- the same treatment already given to a paragraph
   that opens immediately after a genuine section heading. A flush-left
   run-in-heading paragraph is the *expected* style, not a violation.

None of `_merge_same_row_fragments`'s own merge decision,
`_paragraph_starts_like_continuation`,
`_find_split_heading_following_paragraph_indices`, detector thresholds, or
any presentation/wording code changed.

### Regression found during validation (not assumed upfront)

The first version of `_is_run_in_heading_lead` did not exclude bare section
numbers. On the real corpus this surfaced a **new** finding on Muyeed p34: a
numbered sub-heading split as "2.1.3.2" (bold, bare number) + "Nondeterministic
algorithms." (bold title) + "These algorithms are efficient, but their" (regular
run-in body), all on one row. Because the bare section number is *also* bold
and further left than the title, it was picked as the row's "leftmost" bold
lead instead of the title -- corrupting the indent measurement exactly the way
`_is_short_extraction_remnant`'s own bare-section-number exclusion (from the
2026-08-25 batch) already guards against for the unrelated split-heading
pattern. Fixed by adding the identical guard to `_is_run_in_heading_lead`.
After the fix, Muyeed p34 is correctly grouped (title-anchored, exempt, no
finding) and the rest of the corpus is unaffected -- see the before/after
table below.

## Validation

- New file `tests/test_p015_r015_ester_run_in_heading_20260831.py` -- 9 new
  tests, all pass: Youra-style positive case (no finding), unrelated later
  missing-indent paragraph still flagged alongside a run-in heading, direct
  unit coverage that paragraph grouping recognizes the bold segment as the
  paragraph start, an ordinary indented paragraph left unaffected, the
  Muyeed-shape numbered-heading-with-run-in-body regression lock (both an
  integration check and a direct `_effective_row_start_x` unit check), an
  existing-style true positive (`unexpected_indent_on_continuation_line`)
  still flagged alongside an unrelated run-in heading, and two standalone-bold-heading
  boundary cases (no same-row continuation) confirming the new logic does not
  fire and does not exempt an unrelated later missing-indent paragraph.
- `PYTHONPATH=src python -m pytest tests/ -k "p015 or indent" -q` -- 168
  passed (148 pre-existing + 11 prior 2026-08-25 batch + 9 new).
- `PYTHONPATH=src python -m pytest tests/test_ester_rule_consistency_audit.py
  tests/test_ester_sample_a_correctness.py tests/test_rule_registry_consistency.py
  tests/test_rule_classification_consistency.py
  tests/test_finding_index_page_order_consistency.py -q` -- 190 passed.
- `ruff check .` -- pass. `mypy src` -- pass (113 files).
- Full `pytest` -- **3169 passed** (baseline 3160 + 9 new tests; no
  pre-existing test needed updating).
- All seven real evaluation PDFs re-run end to end (below).

## Before / after: all seven real dissertations

| Document | Old total | New total | Old H/M | New H/M | Youra p101 still emitted? |
|---|---|---|---|---|---|
| Youra | 1 | 0 | 1/0 | 0/0 | No (suppressed) |
| Anthony | 0 | 0 | 0/0 | 0/0 | N/A |
| Muyeed | 1 | 1 | 1/0 | 1/0 | N/A |
| Philip | 6 | 6 | 5/1 | 5/1 | N/A |
| Praneeth | 0 | 0 | 0/0 | 0/0 | N/A |
| Sebastian | 0 | 0 | 0/0 | 0/0 | N/A |
| Patrick | 0 | 0 | 0/0 | 0/0 | N/A |

The only finding that changed anywhere in the seven-document corpus is
Youra page 101, which disappears. Muyeed's single finding (page 117) and all
six Philip findings (pages 21, 29, 86, 115, 117, 132) are byte-for-byte
identical -- same page, issue type, confidence, and indent value -- before
and after. No new R015 finding of any kind appears on Youra page 101 (or
anywhere else) after the fix.

## Separate bold-text observation (audited, not implemented)

Ester's separate observation -- "bold text without a section number should
not appear because bold is reserved for headings" -- describes the exact
structural pattern this fix's paragraph now correctly groups around (the
bold run-in phrase "Comparison with the Type 4 SMFR scenario" has no section
number). It is a distinct claim from the R015 paragraph-grouping/indent
question, however: it is about whether that bold, unnumbered phrase should
be styled as bold *at all*, not about paragraph indentation.

**Owning-rule audit:**

- **P020** (`src/njit_auditor/rules/pdf_title_capitalization.py`, bold
  Level-2 title-case heading check) is the closest existing owner
  conceptually. It already has dedicated run-in-heading detection
  (`_has_same_baseline_run_in_body`) for exactly this row shape (bold lead +
  non-bold continuation on the same baseline) -- but today that detection is
  used only to **exclude** such lines from P020's own title-case check (a
  comment there explicitly notes the excluded line "may be an
  unnumbered/run-in Level 4-5 heading or a bolded phrase"). P020 does not
  currently flag the unnumbered-bold-phrase pattern as its own violation.
- **P027** (`src/njit_auditor/rules/pdf_heading_levels.py`, numbered-heading
  level style) requires a heading to already match a numbered-section
  pattern before any style check applies, so it structurally cannot cover an
  *unnumbered* bold phrase.
- **P026** (`src/njit_auditor/rules/pdf_font_compliance.py`) governs font
  family/size compliance only, not bold usage as a heading-reserved style.

No existing rule currently implements "unnumbered bold text should not
appear." P020 and P027 are both mature, extensively Ester-reviewed rules
(see `docs/status/ester_sample_b_p020_specific_remediation.md` and multiple
P027 evaluation docs under `docs/evaluation/`) -- not unreviewed R016+ rules
-- but implementing this specific new check would still be a scope change to
an already-reviewed rule, not part of this R015 task. Per the task brief,
this is recorded as a tracked follow-up rather than implemented here:

> **Follow-up:** Consider whether P020 should be extended to flag an
> unnumbered bold run-in phrase (the same shape `_has_same_baseline_run_in_body`
> already detects and currently excludes) as its own violation, per Ester's
> "bold is reserved for headings" guidance. Needs a dedicated Ester review
> pass on P020's scope before any change, since it is separate from R015 and
> would change P020's existing, already-reviewed detection surface.

## Files changed

- `src/njit_auditor/rules/pdf_indentation.py`
- `tests/test_p015_r015_ester_run_in_heading_20260831.py` (new)
- `docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md` (this file)

## Remaining questions / follow-ups for Ester

1. Whether P020 should be extended to flag unnumbered bold run-in phrases
   (see "Separate bold-text observation" above) -- needs a dedicated P020
   scope review, not folded into this R015 task.
