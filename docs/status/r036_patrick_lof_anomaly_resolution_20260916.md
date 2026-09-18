# R036 Patrick LOF Anomaly Resolution (2026-09-16)

Companion to `r036_page_relative_spacing_experiment_20260916.md`. This began
as a diagnostic experiment. As of the
`fix/r036-production-page-relative-suppression-20260916` branch, the reliable
parts are productionized through the conservative SUPPRESS/ABSTAIN policy in
`r036_production_page_relative_suppression_design_20260916.md`; the reporting
gate remains disabled because no real Ester-confirmed R036 true positive
exists.

## Scope

Resolve the two remaining R036 diagnostic anomalies on Patrick p11 LOF
(pair 2 and pair 7) that the page-relative experiment left as
`PARSER/STRUCTURAL_CONCERN`, and determine whether a parser fix, a Model E
neighbor-selection fix, or a wrap-classification fix is required.

## Source state

- Source experiment branch: `experiment/r036-page-relative-spacing-model-20260916`
- Source experiment SHA: `19d2da36cf7f6d98f61ab4a256e0b1b9ae09df4b`
- Resolution branch: `experiment/r036-resolve-patrick-lof-anomalies-20260916`

## Phase 1 — Exact reproduction

Both anomalies were reproduced from Patrick's real PDF
(`Thesis Patrick Grice July 22.pdf`, physical page index 10, printed page
11, section `list_of_figures`). The page has 34 raw entry-region lines,
grouped into 15 reconstructed entries, yielding 14 eligible inter-entry
gaps.

### Pair 2 (anomaly)

- Previous entry (reconstructed, single line): `5.1 One Newton iteration
  (5.6) with ω= 0.5,1,2 where Γ∗is a disk of radius` — first-line x0 =
  137.29, last-line y0 = 228.52.
- Next entry (reconstructed, single line): `2.5usingaplanewavewithincident
  angleϑ = 0.............` — first-line x0 = **148.98** (caption-
  continuation indent, not the entry-number column), first-line y0 =
  244.20.
- Measured pitch = 244.20 − 228.52 = **15.673 pt** (one single-line
  pitch); local single-line pitch = 14.347 pt; normalized ratio = 1.092.
- Neighboring clean gaps on the page are 22.284 pt and 23.612 pt
  (1.5× / 1.6× the single-line pitch).
- Model E gap/nearby-median ratio = 15.673 / 22.948 = **0.68** ≤ 0.72 →
  flagged `POTENTIAL_PAGE_RELATIVE_ANOMALY`.

### Pair 7 (anomaly)

- Previous entry (reconstructed, single line): `5.6 OneNewtoniteration
  (5.6)wherethescattererΓ∗isanellipse.Figure` — first-line x0 = 137.29,
  last-line y0 = 447.00.
- Next entry (reconstructed, two lines, wrapped): `5.6aplotsaplanewave
  reconstructionandFigures5.6b,5.6cplotsa` (first-line x0 = 148.98) then
  `beamreconstructionwithRinc= 4,ϑ = 0andc = 1,5.` (first-line y0 =
  477.02).
- Measured pitch = 462.68 − 447.00 = **15.674 pt**; local single-line
  pitch = 14.347 pt; normalized ratio = 1.092.
- Neighboring clean gaps are 22.284 pt and 23.612 pt.
- Model E gap/nearby-median ratio = 15.674 / 22.284 = **0.70** ≤ 0.72 →
  flagged `POTENTIAL_PAGE_RELATIVE_ANOMALY`.

## Phase 2 — Visual inspection (raw PyMuPDF word-level)

The rendered page was inspected via raw PyMuPDF word extraction (the
environment's model does not accept image input, so word-level geometry was
used as the ground-truth proxy; both regions were cross-checked against the
150-dpi render and the right-margin page-number column).

### Pair 2 region (5.1)

Raw words at y0 = 229.8 (5.1's first visual line) include `5.1`, `One`,
`Newton`, `iteration`, `(5.6)`, `with`, `ω`, `=`, `0.5,`, `1,`, `2`,
`where`, `a`, `disk`, `of`, `radius` — but **not** the expected
`Γ∗is a disk` word group: a separate `Γ∗is` word sits at y0 = 228.5
(x0 = 406.2), detached from the main line by a sub-point baseline
difference. The entry's true first visual line is
`5.1 One Newton iteration (5.6) with ω = 0.5, 1, 2 where Γ∗is a disk of
radius`, but the reconstruction's *measured* last line and the next
entry's first line do not correspond to the two visual lines that bound a
single inter-entry gap on the rendered page.

The next entry's first visual line (y0 = 244.2) reads `2.5 using a plane
wave with incident angle ϑ = 0. . . . . 61` — a continuation-indented line
(x0 = 149.0) with a dot-leader run and a page number, i.e. it is the
continuation of 5.1's caption, not the first line of a new entry. The
grouping logic nonetheless split it into its own reconstructed entry
because `_looks_like_new_entry_start_given_previous` does not recognize a
continuation-indented dot-leader line as a new entry start when the
previous line has no dot leaders of its own.

### Pair 7 region (5.6)

Raw words at y0 = 448.3 (5.6's first visual line) read `5.6 One Newton
iteration (5.6) where the scatterer Γ∗is an ellipse. Figure` — a single
visual line. The next visual line (y0 = 462.7) reads `5.6a plots a plane
wave reconstruction and Figures 5.6b, 5.6c plots a` at the caption-
continuation indent (x0 = 149.0), and the line after (y0 = 477.0) reads
`beam reconstruction with Rinc = 4, ϑ = 0 and c = 1, 5. . . . . 64` with
a dot-leader run and a page number. These are the continuation of 5.6's
own caption, not a separate entry. The grouping logic split the
continuation-indented line into its own reconstructed (wrapped) entry, so
the *measured* gap from 5.6's first line to the continuation line is a
single-line pitch (15.674 pt), not the inter-entry gap that exists between
5.6's caption and 5.7.

### Classification

| Case | Question | Answer |
| --- | --- | --- |
| Pair 2 | Separate LOF entries? | No — "2.5 using…" is the continuation of 5.1's caption. |
| Pair 2 | Caption wrap? | Yes — 5.1's caption wraps; extraction detached one line. |
| Pair 2 | Extraction split? | Yes — `Γ∗is` detached; continuation line mis-grouped as a new entry. |
| Pair 2 | Figure number detached? | No. |
| Pair 2 | Page-number/dot-leader mistaken for content? | No — the page number (61) and dot leaders are on the continuation line, correctly excluded from the measured pitch. |
| Pair 2 | Gap tighter than neighbors on rendered page? | No — the visual inter-entry gap (end of 5.1's caption → start of 5.2) is the normal ~22 pt rhythm. |
| Pair 2 | Typography/geometry artifact? | Yes. |
| **Pair 2** | **Classification** | **STRUCTURAL_GROUPING_ARTIFACT** |
| Pair 7 | Separate LOF entries? | No — "5.6a plots…" and "beam reconstruction…" are the continuation of 5.6's caption. |
| Pair 7 | Caption wrap? | Yes — 5.6's caption wraps across two continuation lines. |
| Pair 7 | Extraction split? | Yes — continuation lines mis-grouped as a separate (wrapped) entry. |
| Pair 7 | Figure number detached? | No. |
| Pair 7 | Page-number/dot-leader mistaken for content? | No — the page number (64) and dot leaders are on the final caption line. |
| Pair 7 | Gap tighter than neighbors on rendered page? | No — the visual inter-entry gap (end of 5.6's caption → start of 5.7) is the normal ~22 pt rhythm. |
| Pair 7 | Typography/geometry artifact? | Yes. |
| **Pair 7** | **Classification** | **STRUCTURAL_GROUPING_ARTIFACT** |

Both cases are structural grouping artifacts: the grouping logic split a
wrapped caption's continuation lines into their own reconstructed entries,
so the *measured* inter-entry gap is a single-line pitch rather than the
true (normal-rhythm) visual gap between two entries.

## Phase 3 — Local sequence table (Patrick p11 LOF)

| pair | previous (first line) | next (first line) | pitch | local | ratio | wraps | ME score (before) | ME score (after) | outcome (before) | outcome (after) |
| ---: | --- | --- | ---: | ---: | ---: | :---: | ---: | ---: | --- | --- |
| 0 | 4.5 Numerical validation… (wrapped) | 4.6 The pressure… (wrapped) | 23.61 | 14.35 | 1.646 | WW | 1.244 | abstain | SUPPRESSED | INSUFFICIENT_CONTEXT |
| 1 | 4.6 The pressure… (wrapped) | 5.1 One Newton… | 22.28 | 14.35 | 1.553 | W- | 1.000 | 1.13 | SUPPRESSED | SUPPRESSED |
| 2 | 5.1 One Newton… | 2.5 using a plane wave… | 15.67 | 14.35 | 1.092 | -- | 0.683 | abstain | **ANOMALY** | INSUFFICIENT_CONTEXT |
| 3 | 2.5 using a plane wave… | 5.2 One Newton… | 22.28 | 14.35 | 1.553 | -- | 1.000 | abstain | SUPPRESSED | INSUFFICIENT_CONTEXT |
| 4 | 5.2 One Newton… | 5.3 One Newton… (wrapped) | 23.61 | 14.35 | 1.646 | -W | 1.060 | abstain | SUPPRESSED | INSUFFICIENT_CONTEXT |
| 5 | 5.3 One Newton… (wrapped) | 5.5 One Newton… (wrapped) | 22.28 | 14.35 | 1.553 | WW | 1.000 | 1.000 | SUPPRESSED | SUPPRESSED |
| 6 | 5.5 One Newton… (wrapped) | 5.6 One Newton… | 22.28 | 14.35 | 1.553 | W- | 1.000 | 1.17 | SUPPRESSED | SUPPRESSED |
| 7 | 5.6 One Newton… | 5.6a plots a plane wave… (wrapped) | 15.67 | 14.35 | 1.092 | -W | 0.703 | abstain | **ANOMALY** | INSUFFICIENT_CONTEXT |
| 8 | 5.6a plots… (wrapped) | 5.7 Three Newton… (wrapped) | 22.28 | 14.35 | 1.553 | WW | 1.000 | 0.971 | SUPPRESSED | SUPPRESSED |
| 9 | 5.7 Three Newton… (wrapped) | 5.8 The curvature… | 23.61 | 14.35 | 1.646 | W- | 1.060 | 1.060 | SUPPRESSED | SUPPRESSED |
| 10 | 5.8 The curvature… | 5.9 Three Newton… (wrapped) | 22.28 | 14.35 | 1.553 | -W | 0.971 | abstain | SUPPRESSED | INSUFFICIENT_CONTEXT |
| 11 | 5.9 Three Newton… (wrapped) | 5.10 The curvature… (wrapped) | 23.61 | 14.35 | 1.646 | WW | 1.060 | 1.060 | SUPPRESSED | SUPPRESSED |
| 12 | 5.10 The curvature… (wrapped) | 5.11 Three Newton… (wrapped) | 22.28 | 14.35 | 1.553 | WW | 1.000 | 1.000 | SUPPRESSED | SUPPRESSED |
| 13 | 5.11 Three Newton… (wrapped) | 5.12 Three Newton… (wrapped) | 22.28 | 14.35 | 1.553 | WW | 0.971 | abstain | SUPPRESSED | INSUFFICIENT_CONTEXT |

Pair 2 and pair 7 are isolated because of *entry reconstruction* (the
grouping logic split wrapped captions' continuation lines into their own
entries), not because of actual spacing: the true visual inter-entry gaps
on the rendered page follow the same ~22 pt rhythm as every other gap on
the page.

## Phase 4 — Model E neighbor selection

The original Model E compared a gap against the pitches of the four
immediately adjacent gaps (offsets −2, −1, +1, +2). For pair 2, the
adjacent gaps (pairs 0, 1, 3, 4) included two contaminated gaps (pair 0:
both entries wrapped; pair 4: next entry wrapped), so the neighbor median
was dragged toward the clean gaps but the candidate's own pitch (a
single-line pitch, not a true inter-entry gap) was still far below the
clean rhythm. For pair 7, the adjacent gaps (pairs 5, 6, 8, 9) were all
clean, but the candidate's pitch was again a single-line pitch measured
across a reassembled boundary. In both cases the anomaly came from the
*candidate's own reconstruction*, not from the neighbor selection per se —
but the neighbor selection could not distinguish a clean inter-entry gap
from a reassembled boundary, so it scored the artifact against a clean
baseline.

Flaws identified:
- Comparing a reassembled boundary (not a single visual gap) against clean
  inter-entry gaps.
- Using contaminated neighbors (gaps touching wrapped entries with
  non-contiguous extraction) in the baseline.
- No abstention when the candidate's own entries were reconstructed.

## Phase 5 — Decision: Outcome C (Model E neighbor-selection artifact)

A parser/grouping fix (Outcome A) was evaluated and rejected as the
primary fix: the grouping logic (`_group_lines_into_entries`,
`_looks_like_new_entry_start_given_previous`) is shared with the
production P032 detector, and a change there risks altering production
behavior without a demonstrated, behavior-neutral correction. The
structural exemption and split-section-number recovery are preserved
untouched.

A wrap-classification fix (Outcome B) was not required: the `_wraps`
predicate (distinct physical baselines > 2 pt) is already correct; the
issue is that a *single-line* entry's first visual line was reassembled
from a continuation line, which the current `previous_wraps` /
`next_wraps` flags do not capture.

The chosen fix (Outcome C) is diagnostic-only, in
`src/njit_auditor/rules/r036_page_relative_spacing_experiment.py`:

1. **Structural-reconstruction abstention.** The collector now records each
   candidate's previous entry's first-line x0 and whether the previous
   entry is single-line. After the page's entry-number column is known
   (the leftmost first-line x0 over the whole page), a single-line LOF/LOT
   entry whose first visual line starts at the caption-continuation indent
   (≥ `CONTINUATION_INDENT_OFFSET_PT` = 12 pt to the right of the column)
   is flagged `previous_entry_is_reconstructed`. Model E abstains
   (`INSUFFICIENT_CONTEXT`) for such candidates instead of scoring them.
   This is generic geometry (first-line x0 relative to the page's
   entry-number column); it is scoped to LOF/LOT single-line entries and
   contains no Patrick-specific strings or pages.

2. **Clean-neighbor baseline for LOF/LOT pages with wrapped entries.**
   When an LOF/LOT page contains wrapped entries, Model E compares a gap
   against the nearest *clean* neighbor on each side (a neighbor that does
   not touch a wrapped entry), scanning outward from the candidate and
   excluding lower-tail neighbors that would drag the baseline down. Pages
   with no wrapped entries (the common single-line-caption case) keep the
   original fixed-window behavior, as do all TOC pages (preserving the
   pre-fix behavior already validated against the reviewed TOC false
   positives).

3. **TOC behavior unchanged.** TOC pages keep the original fixed-window
   neighbor selection (offsets −2, −1, +1, +2), so the 16 Muyeed TOC
   normal-rhythm cases and all reviewed TOC false positives are unaffected.

No Patrick-specific exceptions were introduced. Production R036
(`check_pdf_toc_list_entry_spacing`) is unchanged.

## Phase 6 — Diagnostic ground truth (after fix)

- Known Ester false positives: 24; flagged after fix: **0** (24/24
  suppressed).
- Praneeth production count: **0** (unchanged).
- Anthony production count: **0** (unchanged).
- Production findings at the time of this diagnostic run: 96 (unchanged:
  Muyeed 71, Philip 9,
  Patrick 16).
- Model E diagnostic anomalies: **0** (was 2).
- Model E diagnostic abstentions: **99** (was 28) — the increase is LOF/LOT
  pages with wrapped entries where the clean-neighbor baseline is too
  sparse to score reliably; these are `INSUFFICIENT_CONTEXT`, not
  suppressed findings.
- No new unexplained diagnostic anomalies introduced.
- Section breakdown (Model E): TOC 221 suppressed / 14 abstain (unchanged);
  LOF 109 suppressed / 54 abstain; LOT 19 suppressed / 31 abstain.
- Exact remaining anomaly list: **none**.

## Phase 7 — 18 previously unrepresented findings

After the fix, the two Patrick p11 LOF cases drop out of the
unrepresented set (they are no longer anomalies). The 16 Muyeed TOC
normal-rhythm cases keep their `SUPPRESSED_AS_NORMAL_PAGE_RHYTHM`
classification (TOC behavior is unchanged). Two additional Muyeed TOC
findings (p14 pair 14 and pair 16) now appear in the set, displacing the
two Patrick cases; all 18 are `SUPPRESSED_AS_NORMAL_PAGE_RHYTHM`. No
Muyeed case changed from suppressed to anomaly or vice versa.

## Phase 8 — Model E robustness

After the fix, Model E has zero clean anomalies and zero known false
positives across the seven-dissertation corpus. This means the evaluation
corpus contains **no demonstrated true positive** for R036 under Model E —
it does *not* mean Model E can detect violations. There is still no
Ester-confirmed R036 true positive in the corpus, so Model E's ability to
detect a genuine isolated tight gap is only validated on the synthetic
test in `tests/test_rules/test_r036_page_relative_spacing_experiment.py`
(`test_isolated_genuine_tight_single_line_lof_gap_is_still_detected`), not
on a real document. Do not overclaim production readiness on detection
alone.

## Phase 9 — Constant sensitivity

Sensitivity grid (Model E, after fix), across `min_gaps` ∈ {4, 5, 6} and
`floor` ∈ {0.65, 0.70, 0.72, 0.75, 0.80}:

| min_gaps | floor | known_fp_flagged | anomalies | abstentions |
| ---: | ---: | ---: | ---: | ---: |
| 4 | 0.65 | 0 | 0 | 85 |
| 4 | 0.70 | 0 | 0 | 85 |
| 4 | 0.72 | 0 | 0 | 85 |
| 4 | 0.75 | 0 | 0 | 85 |
| 4 | 0.80 | 0 | 0 | 85 |
| 5 | 0.65 | 0 | 0 | 99 |
| 5 | 0.70 | 0 | 0 | 99 |
| 5 | 0.72 | 0 | 0 | 99 |
| 5 | 0.75 | 0 | 0 | 99 |
| 5 | 0.80 | 0 | 0 | 99 |
| 6 | 0.65 | 0 | 0 | 99 |
| 6 | 0.70 | 0 | 0 | 99 |
| 6 | 0.72 | 0 | 0 | 99 |
| 6 | 0.75 | 0 | 0 | 99 |
| 6 | 0.80 | 0 | 0 | 99 |

The Patrick anomalies exist **only** because of the exact 0.72 floor in the
*pre-fix* neighbor selection (0.68 and 0.70 are both ≤ 0.72 but > 0.65).
After the fix, the result is stable across the entire grid: zero anomalies
and zero known-FP flags at every combination. A small perturbation of the
constants does not materially change the conclusion. The constants appear
stable enough for a later production-design investigation, but they are
not productionized by this experiment.

## Tests

- New focused tests in
  `tests/test_rules/test_r036_page_relative_spacing_experiment.py`:
  - `test_paired_wrapped_entry_lof_anomalies_resolve_to_structural_abstain`
    (real-style Patrick p11 pair-2/pair-7 shape, generalized).
  - `test_clean_single_line_lof_page_uniform_rhythm_has_no_anomaly`.
  - `test_isolated_genuine_tight_single_line_lof_gap_is_still_detected`.
  - `test_sparse_unreliable_neighborhood_abstains`.
- All diagnostic tests: pass.
- All R036 tests: pass.
- Related parser tests: pass.
- Full suite: 3532 passed.
- ruff: clean.
- mypy (src): clean (134 files).

## Original Diagnostic-Run Production Status

- Production R036 code path changed at the time of this diagnostic run: **NO**
- Fixed threshold at the time of this diagnostic run: 1.6
- Production findings at the time of this diagnostic run: 96
- Email sent: NO
- Drive upload performed: NO
- Merged: NO
- Deployed: NO

## Production design readiness

The two Patrick anomalies are resolved as structural grouping artifacts
and are no longer scored by Model E. Model E now has zero clean anomalies
and zero known false positives on the corpus, but it has **no demonstrated
true positive**. Production design is justified as a *suppression*
investigation (the evidence supports suppressing all current R036
findings), not as a *detection* claim. A later production-design
investigation should (a) confirm the suppression policy against additional
reviewed examples, and (b) obtain at least one Ester-confirmed R036 true
positive before claiming detection capability.
