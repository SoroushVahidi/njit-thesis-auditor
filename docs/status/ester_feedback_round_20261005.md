# Ester Feedback Round 2026-10-05: R011, R018, R024, R040, R045

**Base:** `origin/main` @ `2766f0a45c062d19b76a3b7b3f6283c913563181`
**Branch:** `fix/ester-feedback-round-20261005`
**Scope:** the five single-case questions in the 2026-10-04 review round.
No deployment, Drive change, or reviewer email is part of this work.

Reviewer-facing identifiers are `Rxxx`; implementation identifiers are
`Pxxx`. No dissertation text is reproduced here.

## Decisions and changes

| Rule | Reviewed case | Ester decision | Change |
|---|---|---|---|
| R011 | Sebastian, physical p28 / printed 13, final reference/DOI line, bottom margin | Not a violation | Narrow references-page final-line allowance in `pdf_margins.py` |
| R018 | Patrick, physical p11 / printed x, full-width List of Figures entry with no leader dots | True violation | Behavior unchanged; authority regression; R018D card wording now names List of Tables/List of Figures (P075 owns TOC leader style) |
| R024 | Muyeed, physical p16 / printed xiv, List of Tables title with a lowercase field-convention word | True violation (student may ignore); List of Tables and List of Figures both title case, with different codes | P024 findings map to public cards R024D (List of Tables title case, Q065) and R024E (List of Figures title case, Q074 slot) instead of the hidden parent R024. See "Follow-up reconciliation" below |
| R040 | Philip, physical p15 / printed xiii, wrapped List of Figures title ending without punctuation before gap-separated leaders | True violation | The first dot of a gap-separated ASCII leader run no longer counts as terminal punctuation |
| R045 | Patrick, physical p5 / printed iv, publication entries labeled [1], [2], no hanging indent, double-spaced | Not satisfied: "not numbered" (meaning open), single spacing mandatory, hanging indent optional | Missing hanging indent is no longer reported; Q028 spacing checks are scoped to the Publications/Presentations section and no longer depend on a hanging indent |

Ester also noted that R024 should not use one code for both lists. Both
atomic cards already existed (`web_app.py`), but findings never resolved to
them, so students saw the ambiguous parent "R024" with a dead `/rules`
anchor. Review workbooks should use R024D/R024E from now on.

## R011 allowance (exact shape)

A single bottom-margin line is allowed only when all hold: the page is a
confidently identified references page (a REFERENCES/BIBLIOGRAPHY heading
line or two or more bracket-numbered entries) and not a contents page; the
line's top is at most 7.5pt below the 1-inch boundary and its box at most
24pt below; it is the last text line on the page; a page number sits below
it and the line's midpoint is above the page number's top; and it continues
a single-spaced block (step from the line above 0.8-1.6 font sizes). Prose,
abstract, and contents pages, deeper bleeds, lines running into the page
number, and every left/right/top-margin case are unchanged.

## R040 rule

A period touching the title text counts ("title. . . ." and "title.……").
A lone ASCII period set off by a space before a different leader glyph
("title .……") still counts, as decided on 2026-09-19 (its gap belongs to
R018S). The first dot of a uniform ASCII leader run after a gap
("title (2.6) . . . . 30") is a leader, not punctuation.

## R045 rule

- The Publications/Presentations section is located by its label, spaced or
  concatenated ("PresentationsandPublications:"); education bullets are
  excluded (P047 owns them).
- Entries are separated by visible labels ("[1]", "(1)", "1.") or, without
  labels, by hanging-indent geometry. A section whose entries cannot be
  separated is skipped.
- Within an entry, a line pitch above 1.6x the font size is not single
  spacing (corpus single spacing: 1.15-1.2x; Patrick: 2.0x).
- Between entries, the step from one entry's last line to the next entry's
  first line must be at least 1.5x the within-entry pitch (corpus entries
  with a blank line: 1.66-2.0x). This replaces the absolute 20pt gap, which
  measured from line bottom to line top and would have flagged every
  single-spaced corpus document with a real blank line.
- Catalog source corrected from Q026 (education bullets) to Q028.

## Seven-document corpus diff (base `2766f0a` vs branch)

| Rule | Document / physical page | Change | Classification |
|---|---|---|---|
| R011 | Sebastian p28 | bottom-margin finding removed | Adjudication-driven (Ester FP) |
| R011 | Sebastian p27 | bottom-margin finding removed | Same references final-line family (top +5.3pt, 21.4pt) |
| R040 | Muyeed p21 | finding added | Philip pattern: title without punctuation, leaders after a gap |
| R040 | Praneeth p15 | finding added (a different entry from the earlier reviewed false positive, which keeps its attached period) | Philip pattern |
| R045 | Patrick p5 | `missing_hanging_indent` removed; `wrapped_line_spacing_not_single` added | Adjudication-driven |
| R045 | Youra p6 | `entry_spacing_not_double` removed | Incidental: the old check compared education-degree blocks, not publications |

R018 and R024 finding sets are unchanged (Patrick p11 and Muyeed p16 still
flagged). No other rule changed.

## Follow-up reconciliation (branch `fix/ester-20261005-r024-r045-reconciliation`)

**R024 (authority 2026-10-05).** Ester: "List of Figures have title case and
list of Tables have title case. These rules should be labeled with different
codes." Applied as:

- List of Tables titles: title case, public code R024D (`list_of_tables_title_case`).
- List of Figures titles: title case, public code R024E (`list_of_figures_title_case`).
  Both use the same title-case check (`check_apa_title_case_phrase`).
- The earlier List of Figures sentence-case reading of Q074 is superseded.
  The P024 sentence-case heuristic and P017's List of Figures sentence-case
  branch are removed. P017 still checks body figure captions for sentence
  case: that is a body-caption rule Ester's answer did not address.
- No public renumbering: R024D/R024E already existed as atomic cards.

Corpus effect: 198 new R024E findings across all seven documents (an
earlier "about 229" was a counting error); the underlying entries all fail
title case, because the corpus uses sentence case. Sources that still say
sentence case for figure descriptions: the NJIT formatting guideline, the
Self-Assessment Sheet, Q074's text, Ester's own P017 sheet edit, and her
2026-09-07 Anthony p14 ruling.

R024E calibration: 17 of the 198 were duplicate findings on continuation
rows of wrapped entries (long multi-panel captions whose first row picked up
a non-page token, so the shared logical-entry repair left the rows apart).
P024 now groups an unnumbered, indented row directly below an open entry
into that entry, and reports the entry once. The finding quotes an ordinary
lowercase word rather than a panel label or notation token when one exists.
Result: 181 R024E findings, one per violating entry (Muyeed 46, Philip 17,
Praneeth 17; other documents unchanged); no other rule's findings changed.

**R045 (authority 2026-10-05).** Ester listed three issues: "not numbered",
not single-spaced, no hanging indent; the hanging indent is not mandatory
and the others are. Applied: single spacing mandatory (unchanged from this
round), hanging indent optional (unchanged). Numbering is **not**
implemented: the reviewed entries are visibly labeled [1], [2], the other
six corpus documents and the NJIT Front Matter template use unnumbered
entries, and Ester's rules are usually stated declaratively, so the note may
mean entries must not be numbered.

## Pending Ester clarification (not implemented)

1. **R045 numbering:** "Should publication and presentation entries be
   numbered, or unnumbered?" (Patrick p5 entries are labeled [1], [2].)
2. **R011 beyond references pages:** whether the final-line allowance should
   extend to prose, abstract, or contents pages with the same geometry
   (e.g. Sebastian p1/p3/p9, Praneeth p82).

## Pre-existing replay discrepancy (not changed here)

A read-only ground-truth replay (scratch copy of the private ledger) reports
46 reviewed false positives with 1 still present on both the base commit and
this branch: the R015/P015 `missing_later_indent` case on Youra physical page
101 (ledger replays last passed on 2026-09-08). This branch introduces no new
replay failure; the P015 case needs its own follow-up.
