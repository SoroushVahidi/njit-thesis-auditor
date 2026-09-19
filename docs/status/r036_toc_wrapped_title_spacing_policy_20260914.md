# R036/P036 TOC Wrapped-Title Spacing Policy (2026-09-14)

## Status: ambiguity resolved

The prior "interpretation A vs B" ambiguity documented in
`docs/status/p036_praneeth_forensic_investigation_20260908.md` (2026-09-08,
"Decision: no code change") is **closed** as of 2026-09-14. Ester reviewed
all 12 currently-firing P036 findings on Praneeth's TOC page 11 (the
`R036_Praneeth_Page11_All_Examples` package built on the
`evaluation/r036-praneeth-all-examples-20260912` branch) and gave an
explicit, unambiguous verdict:

> "All of these are False positives."

She then stated the governing rule directly:

> "The TOC must be double spaced except for titles that run longer than one
> line in which case these titles must be single spaced."

This supersedes the 2026-09-08 "no code change" decision, which was made
*because* the interpretation was still ambiguous, not because a fix was
judged unnecessary. It does not conflict with any other recorded Ester
judgment: her existing Anthony page-12 feedback ("chapter/appendix headings
should get flexibility") and the earlier Anthony page-11 confirmation are
both structural-heading exemptions, a narrower and different mechanism from
the general single-vs-double-spacing model this document describes, and
both remain intact (see "Anthony regression" below).

## Root cause of the 12 false positives

The old model (`MIN_INTER_ENTRY_GAP_RATIO = 1.4`) measured, for every pair
of consecutive logical TOC entries, the *blank bounding-box gap* between
the last physical line of one entry and the first physical line of the
next (`first_line.bbox.y0 - last_line.bbox.y1`), normalized by the larger
of the two lines' font sizes (or bbox height as a fallback).

That is the wrong geometric quantity. On the real Praneeth PDF (12pt body
font), the true single-line baseline-to-baseline pitch (`next.bbox.y0 -
prev.bbox.y0` between two physical lines of the *same* wrapped title) is
**13.8pt**. A genuinely double-spaced entry-to-entry transition advances by
**exactly 2x that** — **27.6pt** — confirmed on Praneeth's own page 11 (the
gap between a wrapped-entry continuation and the next numbered entry, entry
1.1 to entry 1.2, is 210.49 − 182.89 = 27.60pt) and independently on page 12
(27.6pt again, different entries, same document) and on Sebastian's page 9
(the one real wrapped title there also has an internal pitch of 13.8pt).
This 2x-pitch relationship is what "double spacing" *means*, almost by
definition, and it held with wide margins across every document checked
(see "Real-document validation" below).

The old model's **bounding-box gap**, however, is pitch *minus* the
bounding box's own ink/ascent-descent extent — for this font and
extraction, a single-spaced wrap's bbox gap is a tiny ~0.5pt, while a
genuinely double-spaced bbox gap is ~14.3pt. Normalized by the 12pt font
size, that is a **1.19x** ratio — comfortably real double spacing, but
below the 1.4x threshold the old model required. The 1.4 threshold itself
was apparently calibrated assuming bbox-gap/font-size approximates
pitch/font-size, which it does not: the two quantities differ by roughly
the bounding box's own height, and that residual varies enough between
fonts/extractions to make ratios cluster in different, seemingly arbitrary
places per document (0.94 for Philip, ~0.97–1.0 for Muyeed, 1.19 for
Praneeth, ~0.97–1.0 for Patrick, ~0.83–0.95 for Youra — all real
double-spaced TOCs, all previously scored below any threshold that could
plausibly separate them from genuinely single-spaced text). **This was not
a Praneeth-specific bug: it was firing false positives on effectively every
genuinely double-spaced TOC/List page in the corpus**, which the
before/after real-document counts below confirm directly.

## New measurement model

`src/njit_auditor/rules/pdf_toc_list_entry_spacing.py` now measures the
**baseline-to-baseline pitch** (`first_line.bbox.y0 - last_line.bbox.y0`)
between the last physical line of the previous logical entry and the first
physical line of the next, and compares it against the page's own **local
single-line pitch** — not a fixed multiple of nominal font size.

The local single-line pitch is calibrated *from the page itself*: every
already-grouped multi-line ("wrapped") entry's own internal,
consecutive-physical-line pitch is collected as ground truth for what
"single spaced" looks like on this page, in this font, in this
document — the same mechanism Ester's rule uses ("single-spaced" is
defined by how *this document* renders a wrapped title, not by an assumed
universal constant). These samples are further split into two buckets by
structural role — top-level (`toc_level_1`, e.g. a bare numbered chapter
heading) vs ordinary entries — because a page can legitimately use a
different single-line pitch for its headings than for its ordinary entries
even at the *same* font size (confirmed on Praneeth page 12: both measure
12pt, but a wrapped chapter heading's own two lines advance by 20.6pt while
an ordinary wrapped sub-entry advances by 13.8pt). The bucket matching the
transition's own role (`prev_level`) is preferred; the other bucket, then a
font-size-based fallback (`font_size * 1.15`, a standard single-line
leading factor), are used only when a page has no same-role — or no
multi-line entries at all — to calibrate from.

```
MIN_INTER_ENTRY_GAP_RATIO = 1.6   # was 1.4, but now a PITCH/PITCH ratio,
                                   # not a bbox-gap/font-size ratio
```

Genuine double spacing measures ~1.9–2.9x under this model (see table
below); genuine single/tight spacing measures ~0.8–1.5x. 1.6 sits with a
wide, empirically-confirmed margin from both — this is not a constant
tuned against Praneeth alone; it reflects the literal definition of
"double" (2x) with headroom on both sides for real-world imprecision.

### Logical entry grouping (three real bugs fixed)

Ester's rule requires distinguishing continuation lines (single-spaced,
same entry) from separate consecutive entries (double-spaced). Most of
this was already correctly implemented before this task
(`_group_lines_into_entries` / `_is_wrap_continuation_pair` /
`_looks_like_new_entry_start_given_previous`, in
`pdf_toc_list_wrapped_spacing.py`, shared with P032) — the 12 Praneeth
false positives were already correctly grouped into entries; only the
*measurement* was wrong (see above). Fixing the measurement alone,
however, surfaced three narrower, pre-existing entry-*grouping* bugs whose
effect is to silently merge a genuinely separate entry into the preceding
one, corrupting the new model's page-local pitch calibration (and, more
generally, making the merged entry's own true inter-entry gap
unmeasurable). Each was confirmed against real PDF geometry before being
fixed, all three in `NEW_ENTRY_START_RE` /
`_looks_like_new_entry_start_given_previous`
(`pdf_toc_list_wrapped_spacing.py`):

1. **Bare-numbered top-level headings** (a numbered all-caps heading split
   across two extracted physical lines, Praneeth page 12; and a numbered
   all-caps heading with the space after the period dropped by extraction,
   Sebastian page 9) were not
   recognized as starting a new entry because they have neither a decimal
   sub-number nor the word "CHAPTER"/"APPENDIX", and their own first
   physical line has no dot leaders yet. `NEW_ENTRY_START_RE` gained a
   `\d+(?:\.|\s)\s*(?-i:[A-Z])` alternative (already the same shape
   `NUMERIC_PREFIX_RE` in `pdf_toc_alignment.py` treats as an entry
   prefix elsewhere in this pipeline).
2. **Other structural headings** — "REFERENCES", "BIBLIOGRAPHY", "VITA",
   "GLOSSARY", "INDEX" (Anthony page 12: one structural row wrongly swallowing the following references row; Patrick page 8, same shape) — fail
   `_likely_entry_line`'s all-caps-short-line noise filter and have no
   recognized prefix. Added as literal keyword alternatives to
   `NEW_ENTRY_START_RE` (mirrors the keyword list already in
   `_classify_entry_level`, `pdf_toc_list_entry_spacing.py`).
3. **Unnumbered, no-prefix ALL-CAPS chapter titles** (a real wrapped
   chapter title wrongly swallowed into the preceding complete numbered
   entry) have no recognizable shape at all —
   this is the hard case: the first physical line of a genuinely new,
   unnumbered wrapped title is textually indistinguishable from an
   ordinary continuation line. The signal that does generalize: if the
   *previous* line is already rigorously confirmed complete (a real
   dot-leader run **and** `_line_has_page_number` agreeing there is a real
   page-number token — not just a raw `"..."` substring test), it cannot
   have a continuation, so whatever follows must start a new entry,
   whatever shape it has. `_looks_like_new_entry_start_given_previous` now
   checks this unconditionally, in addition to its existing (narrower) raw
   `"..."`-substring check.

**A broader version of fix 3 was tried and reverted.** Making *any* raw
`"..."`/`"...."` substring match on *previous* an unconditional trigger
(rather than requiring `_line_has_page_number` to independently agree)
caused a large regression verified empirically: P036 finding counts spiked
across every one of the seven real dissertations (e.g. Praneeth
0 → 7, Anthony 0 → 17), because ordinary running prose in List of
Figures/Tables captions frequently contains an ellipsis or a run of
periods with no actual page number nearby, and the loose version treated
every such line as "complete," over-splitting real wrapped captions
throughout the corpus. The narrower, rigorously-confirmed version was
substituted and re-validated (see below); it also had to be tightened once
more after a second real false trigger was found (`_line_has_page_number`'s
short-roman-numeral branch, with no dot-leader requirement of its own,
misread a trailing all-roman-letter abbreviation as ending in the roman
numeral "LC" = 150 and wrongly split a Praneeth List of Figures caption —
fixed by additionally requiring a real dot-leader run on *previous*, not
`_line_has_page_number` alone).

## Real-document validation

`check_pdf_toc_list_entry_spacing` run against the real, private PDFs in
`data/evaluation/private/` (gitignored; copied into this worktree only to
run the checker, not committed), before this fix (origin/main,
`e510501`) vs after:

| Document | Before | After | Disappeared | Remained | New |
|---|---:|---:|---:|---:|---:|
| Praneeth | 50 | **0** | 50 | 0 | 0 |
| Anthony | 0 | 0 | 0 | 0 | 0 |
| Youra | 38 | 20 | 18 | 20 | 0 |
| Muyeed | 116 | 114 | 4 | 108 | 2 |
| Philip | 26 | 20 | 6 | 20 | 0 |
| Sebastian | 0 | 0 | 0 | 0 | 0 |
| Patrick | 43 | 39 | 5 | 35 | 1 |

Praneeth's 12 Ester-reviewed page-11 cases: **12 → 0**, exactly (the full
page-11 sequence, not just the 12 flagged pairs, is reproduced exactly with
real coordinates in
`tests/test_rules/test_r036.py::test_r036_praneeth_page11_real_geometry_all_examples_clean`).

Every document's total finding count went down or stayed the same — no
document became newly noisy. The 3 new findings (2 in Muyeed, 1 in Patrick)
are pairs that were previously invisible to the checker entirely because
they were on the wrong side of one of the three grouping bugs above (e.g.
a structural appendix-to-references transition, ratio 1.00 — exactly
single-spaced, genuinely unmeasured before the REFERENCES-grouping fix, now
correctly evaluated); none is evidence of new over-triggering from the
measurement-model change itself. Muyeed and Patrick still carry the
largest remaining counts (114 and 39); spot-checking their gap ratios shows
tight clustering near 1.0 (genuinely no double spacing detected, not
measurement noise near the 1.6 threshold), consistent with real,
previously-undetectable-by-the-old-model violations rather than a residual
calibration artifact — but these were never part of Ester's reviewed set
and are flagged here for a future review pass, not asserted as confirmed
true positives.

### Anthony regression

Anthony was **0 P036 findings before this task and 0 after** — the
existing structural-boundary exemption (`_is_exempt_structural_transition`,
unchanged by this fix) and both grouping-bug fixes (REFERENCES-after-
APPENDIX on page 12, the unnumbered ALL-CAPS chapter title on page 11) were
required together to hold Anthony at 0 under the new pitch-based model;
without either grouping fix, Anthony regressed to 6–17 findings during
development (see "A broader version... was tried and reverted" above) —
caught by exactly this real-document check, not by unit tests alone.

## What this is not

This is not a Praneeth-specific patch. The measurement model change (pitch
vs bbox-gap) and all three grouping fixes are expressed in terms of
generic TOC/List structure (entry roles, dot-leader/page-number
confirmation, structural-heading keywords already used elsewhere in this
same rule family) and were each validated against real geometry on a
different document than the one that surfaced it (fix 1: Praneeth +
Sebastian; fix 2: Anthony + Patrick; the pitch model itself: Praneeth +
Sebastian + Anthony). No code path branches on filename, student name, or
any Praneeth-specific string.
