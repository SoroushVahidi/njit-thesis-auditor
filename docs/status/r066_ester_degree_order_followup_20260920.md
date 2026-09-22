# R066 Ester Degree-Order Follow-Up (2026-09-20, repaired 2026-09-21)

## Reviewer Ground Truth

Ester confirmed the Anthony R066 finding as a false positive. Anthony's degree
entries are already in reverse chronological order. No Ester-confirmed R066
true-positive example is available in the tracked workbook or feedback PDF.
This document does not invent one.

## Canonical Scope

R066/P066 implements Q025's structural degree-ordering portion only. It scans
the Biographical Sketch's explicit education subsection, from most recent to
oldest, and does not implement Q023 birthplace/date checks, Q024 work-history
checks, or the Q025 "NJIT first" institution-name requirement.

The detector compares one 4-digit year per short candidate line. It uses
year-only precision, requires at least three candidates, treats a later-listed
year more than two years newer as an inversion, and skips date ranges,
fragmented or missing date associations, ambiguous sections, and same-year
ties. Month names do not add precision.

## Root Cause and Fix (2026-09-20 change)

Anthony's pre-fix candidate years were structurally `[2026, 1993, 2026, 2019,
2016, 2013]`. The `1993` was a pre-education biographical date; the actual
education sequence was `[2026, 2019, 2016, 2013]`. Other pre-fix findings also
included publication years because the PDF text layer compacted or reversed
the publication heading words.

The 2026-09-20 fix required an explicit education subsection and recognized
the publication/presentation boundary only via an exact normalized-label set:
`PUBLICATIONS`, `PRESENTATIONS`, `PUBLICATIONSANDPRESENTATIONS`,
`PRESENTATIONSANDPUBLICATIONS`.

## PR #547 Review Regression and 2026-09-21 Repair

A Codex review on PR #547 found that the exact-label set was a regression
against the pre-2026-09-20 boundary detector. The prior detector used a
search-based regex (`\b(PUBLICATIONS?|PRESENTATIONS?|PUBLICATIONS?\s+AND\s+
PRESENTATIONS?)\b`) that recognized singular and plural forms and qualified
headings such as "Selected Publications" anywhere in a line. The exact-label
set only matched a line whose *entire* normalized text equaled one of the
four compact labels, so `Publication`, `Presentation`, and any prefixed or
suffixed heading (e.g. "Selected Publications") no longer stopped degree-year
collection. Publication-year lines below such a heading could re-enter the
degree candidate stream — the same contamination class R066 exists to
eliminate.

**Fix:** the boundary check now searches the compact (letters-only,
uppercased) form of each candidate line for the substring pattern
`PUBLICATIONS?|PRESENTATIONS?`, instead of requiring the whole compact line to
equal one of four fixed labels. This is a strict superset of both prior
behaviors:

- It still matches compact PDF-extracted merged labels with no inter-word
  spaces (`PublicationsAndPresentations`, `PresentationsAndPublications`),
  because the words `PUBLICATIONS` / `PRESENTATIONS` still appear as
  substrings once spacing is stripped.
- It matches singular and plural forms (`Publication`, `Publications`,
  `Presentation`, `Presentations`).
- It matches qualified/prefixed headings (`Selected Publications`, `Conference
  Presentations`, etc.) because the match is a substring search, not a
  whole-line equality check.
- It matches either heading word order (`Publications and Presentations` /
  `Presentations and Publications`), compact or spaced.

The fix does not reference any dissertation name, author name, physical page
number, or private phrase, and does not add a "Selected Publications"
special case — it is a single general pattern applied uniformly. No shared
tokenizer or other Biographical Sketch rule changed.

## Synthetic Boundary Matrix

Each row places three correctly-descending education years above a boundary
line and three ascending years below it (`tests/test_p066_biosketch_degree_ordering.py`).
If the boundary line were not recognized, the two groups would be treated as
one stream and the ascending years below it would trigger a spurious
inversion finding. A `== []` result therefore proves both recognition and
exclusion.

| Variant category | Recognized as boundary | Publication years excluded | Test name |
|---|---|---|---|
| Plural, spaced (`Publications`) | YES | YES | `test_boundary_plural_publications_excludes_years` |
| Singular, spaced (`Publication`) | YES | YES | `test_boundary_singular_publication_excludes_years` |
| Plural, spaced (`Presentations`) | YES | YES | `test_boundary_plural_presentations_excludes_years` |
| Singular, spaced (`Presentation`) | YES | YES | `test_boundary_singular_presentation_excludes_years` |
| Qualified/prefixed (`Selected Publications`) | YES | YES | `test_boundary_qualified_selected_publications_excludes_years` |
| Compact merged (`PUBLICATIONSANDPRESENTATIONS`) | YES | YES | `test_boundary_compact_publications_and_presentations_excludes_years` |
| Compact merged, reversed (`PRESENTATIONSANDPUBLICATIONS`) | YES | YES | `test_boundary_compact_reversed_presentations_and_publications_excludes_years` |
| No boundary line present (negative control) | N/A (no boundary exists) | NO — genuine finding fires | `test_boundary_control_missing_heading_still_detects_contamination` |

The control row proves the probe design is not vacuous: removing the boundary
line from the same six-year setup restores the genuine disorder finding, so
the other rows pass because the boundary is recognized, not because the
detector has gone blind to disorder.

## Five Removed Findings — Individual Audit

All five findings removed by the 2026-09-20 fix were re-inspected structurally
under the repaired 2026-09-21 detector (education-section gate plus the
generalized publication/presentation boundary). No dissertation prose,
titles, degree names, or institution names appear below — only physical page
numbers, structural zone classification, and year integers already present in
finding metadata.

| Alias | Physical page | Old/main collected years | Valid education years (corrected) | Contaminating category | Degree order valid | Genuine R066 violation |
|---|---:|---|---|---|---|---|
| Youra | 6 | `[2026, 2019, 2016, 2026, 2026, 2019, 2025, 2024]` | `[2026, 2019, 2016]` | Publication/presentation year (compact merged boundary heading) | YES (descending) | NO |
| Anthony | 6 | `[2026, 1993, 2026, 2019, 2016, 2013]` | `[2026, 2019, 2016, 2013]` | Pre-education date (two candidate lines before the explicit education subsection) | YES (descending) | NO — Ester-confirmed false positive |
| Muyeed | 6 | `[2026, 2018, 2024, 2024, 2024, 2024]` | `[2026, 2018]` (below the 3-candidate minimum; rule abstains) | Publication/presentation year (compact merged boundary heading) | YES (descending) | NO |
| Philip | 6 | `[2026, 2021, 2025, 2024, 2022, 2019, 2025, 2025]` | `[2026, 2021]` (below the 3-candidate minimum; rule abstains) | Publication/presentation year (compact merged boundary heading) | YES (descending) | NO |
| Patrick | 5 | `[2026, 2019, 2026]` | `[2026, 2019]` (below the 3-candidate minimum; rule abstains) | Publication/presentation year (compact merged boundary heading) | YES (descending) | NO |

**`GENUINE_R066_VIOLATIONS_AMONG_THE_FIVE_REMOVALS = 0`** — every one of the
five removed findings is a structurally-confirmed non-violation: the valid
education-year subsequence in each case is reverse chronological (or too
short to compare, which is itself the correct conservative outcome). Anthony
remains a no-report case, consistent with Ester's explicit judgment.

For reference, all five real-corpus documents happen to use the *compact
merged* boundary form (`PublicationsandPresentations` / `Presentationsand
Publications`, extracted with no inter-word spaces) — the form already
recognized by the pre-repair 2026-09-20 exact-label set. The PR-review
regression (loss of singular/qualified-heading recall) did not change any of
the seven real-corpus counts, because none of the seven documents happen to
use a singular or qualified heading. The repair generalizes recall for
documents that do, without touching any of the seven current outcomes.

## Education-Section Boundary Safety

- **Collection does not start before the explicit education subsection.**
  `_find_education_boundary_y` requires one of `EDUCATION`, `GRADUATE
  EDUCATION`, or `UNDERGRADUATE AND GRADUATE EDUCATION` (compact-normalized)
  and returns `None` (full skip) when absent. Verified structurally on all
  five real cases above (pre-education lines classified separately from
  education-zone lines) and by `test_non_education_date_before_section_is_ignored`.
- **Collection ends at a supported Publications/Presentations boundary.**
  Verified on all five real cases (each has a real, structurally distinct
  publication boundary that truncates the candidate stream) and by the
  synthetic boundary matrix above.
- **Singular/plural and qualified heading forms are safely handled after this
  repair.** Verified by the five new matrix rows covering `Publication`,
  `Publications`, `Presentation`, `Presentations`, and `Selected
  Publications`.
- **Compact PDF text extraction does not defeat the boundary.** All five
  real-corpus documents extract their boundary heading with no inter-word
  spaces, and all five are correctly recognized before and after the repair.
  The synthetic matrix additionally covers both compact word orders directly.
- **Publication sections cannot leak back into the degree stream merely
  because the heading wording differs from one exact label.** This was
  exactly the regression: the fix replaced whole-line equality against four
  fixed labels with a general substring search for the publication/
  presentation root word, so wording variation alone can no longer defeat
  the boundary.
- **A missing/ambiguous boundary causes conservative behavior, not
  speculative classification.** Unchanged by this repair: `test_
  multiple_biosketch_headings_skips`, the missing-education-heading skip
  path, date-range skips, fragmented-date skips, and same-year-tie skips all
  still return `[]`.

## Seven-Document R066 Audit (current, post-repair)

| Dissertation | Pre-2026-09-20 | Post-2026-09-20 / Post-repair |
|---|---:|---:|
| Youra | 1 | 0 |
| Anthony | 1 | 0 |
| Muyeed | 1 | 0 |
| Philip | 1 | 0 |
| Praneeth | 0 | 0 |
| Sebastian | 0 | 0 |
| Patrick | 1 | 0 |
| **Total** | **5** | **0** |

The 2026-09-21 boundary-recall repair does not change any of these seven
counts (verified by re-running the full seven-document audit before and
after the repair commit). The repair only affects documents that would use a
singular or qualified publication/presentation heading, which none of these
seven do.

## Closed-Rule Regression Check (same seven-document corpus)

| Rule | Expected anchor | Observed |
|---|---:|---:|
| R040 | 43 | 43 |
| R046 | 0 | 0 |
| R048 | 5 | 5 |
| R053 | 1 | 1 |
| R054 | 4 | 4 |
| R078 | 1 | 1 |

All six closed-rule anchors are unchanged by this repair.

## Validation and Privacy

- Synthetic coverage includes correct and incorrect order, ranges, month/year,
  expected/current labels, fragmented dates, irrelevant pre-section numbers,
  same-year ties, publication boundaries (plural, singular, qualified,
  compact, and reversed-compact forms, plus a negative control), and
  privacy-safe findings. 26 tests total in
  `tests/test_p066_biosketch_degree_ordering.py`.
- No private PDFs or dissertation text are committed. This document contains
  only aliases, physical page numbers, structural zone labels, and year
  integers already present in existing finding metadata.
- R068 and `LEADER_PLACEMENT_RULE_GAP` remain separate and untouched by this
  task.

## Merge Readiness

As of this repair, the publication-boundary regression identified by Codex
review is fixed, all five previously-removed real-corpus findings are
individually confirmed as non-violations, Anthony remains suppressed, genuine
synthetic disorder detection remains functional (see the control row in the
boundary matrix), closed-rule baselines are unchanged, and no private content
is committed. This document does not itself constitute a merge decision;
merge readiness also depends on the fresh CI run against the repaired commit,
tracked in the PR.
