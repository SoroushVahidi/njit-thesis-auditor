# R011/P011: Esther Resolves the ~9.2pt Bottom-Margin Boundary Question

**Date:** 2026-08-31
**Baseline:** `origin/main` @ `368d14f4271048a82b5cd2d27f00b5e6375a4ce1` (`main`, "docs(eval):
finalize R011/R015 Esther review package")
**Scope:** R011/P011 margin-overflow only. R015/P015 and R016+ not touched.

## Ground truth

Esther answered both previously unresolved R011 questions from
`docs/evaluation/ester_feedback/next_targeted_followup_after_r011_r015_20260825.md`
via the shared "R011-R015 Follow-up" sheet.

| Case | Location | Measured | Esther's judgment |
|---|---|---|---|
| Muyeed | physical PDF page 36 (printed page 15), bottom margin, "clustering algorithm." | ~9.2pt (9.17pt raw), MEDIUM | **FALSE POSITIVE** — do not report |
| Patrick | physical PDF page 88 (printed page 76), right margin, Weng Cho Chew reference entry | ~18.0pt, HIGH | **CORRECT** — report |

Both are now human ground truth. R011 is the human-facing rule ID; P011 is the internal
implementation ID (`src/njit_auditor/rules/pdf_margins.py`).

## Reproduction at baseline HEAD (before this change)

Re-ran the current auditor (`run_audit_for_uploaded_file`) against the real PDFs in
`data/evaluation/private/` (gitignored, never committed):

- **Muyeed page 36:** still present. `bottom_margin`, MEDIUM, `worst_overflow_pt=9.2`
  (raw 9.17), 1 line, `affected_line_texts="clusteringalgorithm."`,
  bbox `137.6,717.2,243.7,729.2`. Exact match to the follow-up sheet's recorded values.
- **Patrick page 88:** still present. `right_margin`, HIGH, `worst_overflow_pt=18.0`, 1
  line, Weng Cho Chew reference entry, bbox `137.9,304.7,558.0,316.7`. Exact match.

No discrepancies vs. the follow-up sheet.

## 8-12pt bottom-margin distribution audit (before any change)

Every emitted P011 bottom-margin finding with `worst_overflow_pt` in 8-12pt, across all
seven private evaluation dissertations, was inventoried (85 findings). None fell in
8.0-9.0pt (already suppressed by the existing 9.0pt tolerance at the time). Grouping by
the *raw*, unrounded overflow value (not the 1-decimal display value) reveals sharp,
repeated spikes sitting on a sparse, mostly-unique-valued background:

| Raw overflow (pt) | Count | Displays as |
|---|---|---|
| 9.05 | 1 | 9.1 |
| **9.17** | **47** | **9.2** |
| 9.28-9.29 | 3 | 9.3 |
| *(gap: nothing 9.30-9.43)* | 0 | — |
| 9.44 | 1 | 9.4 |
| **9.54** | **24** | **9.5** |
| 9.62-10.01 | 3 | 9.6-10.0 |
| **10.09/10.13** | **16** | **10.1** |
| 10.26+ | mostly 1-2 each | 10.3+ |

The single largest spike, **raw 9.17pt with 47 occurrences**, is exactly the Muyeed
page-36 value and recurs identically (same bbox `y1`, same page height, same 1" margin)
across **two independent LaTeX-compiled dissertations** (Muyeed, Philip) on prose,
equations, table-of-contents dot-leader rows, section-heading rows, and reference
URLs/DOIs alike — content-independent, which is the signature of a fixed line-box/leading
constant tied to one common font/line-height combination, not real content placed outside
the margin. It is also, numerically, the exact value the follow-up sheet's "representative
additional example" (Philip physical page 6, "Pennsylvania, USA, 2025.") shares with
Muyeed page 36.

Every value in the 9.05-9.29pt raw band is followed by a **clean, empty gap** (no findings
at all from 9.30-9.43pt raw) before the next, structurally distinct cluster begins at
9.44/9.54pt. Above ~12pt the distribution becomes a smooth, unbroken continuum with no
further natural gaps (consistent with
`docs/status/p011_precision_false_negative_audit_20260710.md`'s prior finding for the
7-30pt+ range) — so, per that prior audit and the current task's own instruction, no
single global magnitude cutoff can safely resolve "genuine vs. slack" above ~12pt from
geometry alone; only the specific, gap-bounded 9.05-9.29pt cluster that Esther's new
ground truth actually covers is resolved here.

## Root-cause analysis

1. **Same-family as the confirmed FP, not a new pattern.** Content across the 9.05-9.29pt
   raw cluster is predominantly `text_paragraph` (prose), plus a handful of
   `references_hanging_indent` bottom-margin lines and one `figure_layout` caption line.
   It is not concentrated in one content type — it is a *last-line-on-the-page* geometric
   effect, independent of what that line contains, exactly matching Cause 1 from
   `docs/status/p011_r011_batch_2026_08_false_positive_fix.md` ("bottom-margin
   single-trailing-line slack"), just at a slightly larger magnitude than that batch's
   confirmed 3.9-8.2pt range.
2. **Predominantly single-line.** Of the 30 findings at display value "9.2pt", 24 are a
   single violating line; the remaining multi-line groups (2-3 lines) are, on inspection,
   PDF-extraction artifacts of one visual line split into multiple `PdfTextLine` objects
   (e.g. a table-of-contents row's section number / title / dot-leader each extracted as
   separate lines, all sharing the identical bottom `y1`), not independent violations.
3. **Not a LaTeX-vs-Word or content-type classifier question.** The prior batch already
   established this slack occurs in both Word and LaTeX source PDFs and both prose and
   equation content; this audit adds table-of-contents rows and reference URLs to that
   list without finding a source- or content-based split, reinforcing that a uniform,
   source-agnostic magnitude tolerance remains the right shape of fix (per that report's
   "why not simpler/broader fixes" reasoning).
4. **The old 9.0pt tolerance did create an artificial cliff.** 47+ content-independent,
   identically-valued findings sat immediately above the old cutoff, indistinguishable in
   kind from the already-accepted false-positive population immediately below it.
5. **The separation that does exist is empirical, not source/content-based.** The natural
   gap at raw 9.30-9.43pt is what separates the confirmed cluster from the next,
   unconfirmed one — not document format, rule content, or any fragile classifier.

## Fix (`src/njit_auditor/rules/pdf_margins.py`)

`BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT`: **9.0 -> 9.3pt.**

This is the same "anchor just above the highest confirmed point, with a small disclosed
buffer" methodology the 8.2pt-anchored 9.0pt tolerance itself used. The new anchor is the
top of the confirmed 9.05-9.29pt raw cluster (9.29pt), with the buffer landing in the
empty 9.30-9.43pt gap rather than at an arbitrary round number. Nothing else in
`pdf_margins.py` changed:

- `OVERFLOW_TOLERANCE_PT` (3.0, generic left/top/right) — unchanged.
- `REFERENCES_MARGIN_EXTRA_TOLERANCE_PT` (6.0, references left/right) — unchanged (see
  "Reference policy" below).
- The artifact guard, `_group_confidence`, low-confidence suppression, and all
  highlight/presentation geometry — unchanged.

## Why not other fixes

- **A single wider flat bump to cover more of the distribution (e.g. to 10.1 or 12pt)**
  was rejected: the 9.5pt and 10.1pt clusters were never reviewed by Esther, the task
  explicitly warns against choosing a threshold from one sample, and the smooth
  above-12pt continuum means a broader cutoff would start silently absorbing likely-genuine
  overflow with no empirical gap to justify it.
- **A content/geometry-aware exemption keyed to "last line on the page"** was considered,
  since that is the actual mechanism, but a robust content-independent "is this the last
  visible line before the margin" detector would be a materially larger, less-tested
  change for the same resolved cluster the flat-tolerance bump already covers exactly;
  deferred as unnecessary for this specific ground-truth resolution.
- **A Word-vs-LaTeX or per-document classifier** was rejected: the phenomenon already
  spans both source types per the 2026-08 batch, and the task explicitly disallows
  treating LaTeX documents as automatically compliant or using a fragile source
  classifier.
- **Hard-coding Muyeed page 36 or its text** was rejected per the task's explicit
  instruction; the fix is a single numeric constant with no document-, page-, or
  text-specific logic.

## Reference policy — no change

Esther's Patrick page-88 confirmation is a right-margin `references_hanging_indent`
finding; `REFERENCES_MARGIN_EXTRA_TOLERANCE_PT` (bottom-margin-unrelated, right/left-only)
was not touched. Verified: at 18.0pt overflow, Patrick page 88 is far outside the existing
bounded reference exception (`OVERFLOW_TOLERANCE_PT + REFERENCES_MARGIN_EXTRA_TOLERANCE_PT`
= 9.0pt) and was never suppressed by it — it is a plain high-confidence right-margin
finding. No reference-policy change was needed to keep it flagged, and none was made.

## Boundary tests added (`tests/test_p011_esther_r011_batch_2026_08.py`)

Synthetic geometry fixtures only — no private dissertation text in runtime logic or test
assertions:

1. `test_bottom_margin_overflow_at_esther_confirmed_9_2pt_cluster_suppressed` — ~9.17pt
   raw (Muyeed-style) — NOT reported.
2. `test_bottom_margin_overflow_just_inside_new_tolerance_suppressed` — ~9.29pt raw (top
   of the confirmed cluster) — NOT reported.
3. `test_bottom_margin_overflow_just_over_tolerance_still_flagged` — ~9.7pt (past the
   natural gap) — still reported (updated from the prior ~9.3pt fixture, which the new
   tolerance now legitimately suppresses).
4. `test_bottom_margin_large_overflow_still_high_confidence` — ~13pt — unchanged, still
   reported, high confidence.
5. `test_references_entry_esther_confirmed_18pt_overflow_still_flagged` — ~18pt
   references right-margin (Patrick-style) — still reported (new).
6. `test_right_margin_trailing_space_only_overflow_suppressed` — unchanged, still
   suppressed.
7. `test_right_margin_real_ink_overflow_without_trailing_space_still_flagged` — unchanged,
   still reported.

`tests/test_p011_bottom_margin_synthetic.py::test_bottom_margin_violation_detected` was
updated to use a clearly-above-tolerance fixture (~13.3pt instead of ~9.3pt, which the new
tolerance now suppresses); it was a generic "detection works" smoke test, not boundary
coverage, so boundary behavior at the new cutoff belongs in the tests above instead.

## Real-corpus before/after (all seven private evaluation dissertations)

| Document | Old P011 | New P011 | High old/new | Medium old/new | Low old/new |
|---|---|---|---|---|---|
| Youra | 1 | 1 | 1/1 | 0/0 | 0/0 |
| Anthony | 38 | 38 | 38/38 | 0/0 | 0/0 |
| Muyeed | 34 | 18 | 15/15 | 19/3 | 0/0 |
| Philip | 63 | 53 | 18/18 | 45/35 | 0/0 |
| Praneeth | 69 | 68 | 53/53 | 16/15 | 0/0 |
| Sebastian | 6 | 6 | 5/5 | 1/1 | 0/0 |
| Patrick | 5 | 5 | 2/2 | 3/3 | 0/0 |
| **Total** | **216** | **189** | **132/132** | **84/57** | **0/0** |

**No high-confidence finding disappeared on any document.** All 27 removed findings were
medium confidence.

### Every P011 finding removed as a side effect (27 total)

All 27 measure raw overflow 9.17-9.29pt (display 9.2-9.3pt), single-side bottom-margin,
medium confidence — the exact confirmed cluster plus its immediate gap-bounded neighbors.

**Same-family correction supported by Ester's new ground truth (26):**

- Muyeed pages 11, 12, 13, 14, 31, 32, **36 (the confirmed case itself)**, 37, 38, 66, 97,
  99, 102, 106, 139, 141 — all `text_paragraph`, 9.2pt.
- Philip pages 1, **6 (the follow-up sheet's own representative example)**, 22, 53, 87,
  99, 112, 117, 143, 144 — all `text_paragraph`, 9.2-9.3pt.

**Likely correction (1):**

- Praneeth page 95 — `figure_layout` (figure-caption text line), 9.3pt raw. Same recurring
  geometric signature (single trailing line, raw value inside the confirmed
  gap-bounded cluster) as the confirmed cases, but a different content kind (caption, not
  prose) than any of Esther's directly reviewed examples, so classified one notch below
  "same-family."

**Uncertain / possible true-positive loss: none.** Every removed finding shares the
identical raw-value signature (9.17-9.29pt, matching the natural-gap-bounded cluster) with
the Ester-confirmed Muyeed and Philip-representative cases; none showed a distinguishing
pattern (different magnitude cluster, multi-line paragraph genuinely running off the page,
different font/geometry constant) that would suggest a different mechanism.

### Confirmations

- **Muyeed page 36: SUPPRESSED.** Re-ran with the fix; the finding no longer appears
  (`worst_overflow_pt=9.2` no longer clears `BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT=9.3`).
- **Patrick page 88: STILL EMITTED.** Re-ran with the fix; `right_margin`, HIGH,
  `worst_overflow_pt=18.0`, unchanged — bottom-margin-only tolerance change does not touch
  right-margin logic.

## Sample A/B (in-repo, committed) fixtures

The built-in `ester_sample_a` fixture independently contains the identical 9.17pt raw
signature on pages 11, 42, 66, and 71 (and 194/195/198/200-equivalent already-not-visible
bottom findings rolled up under a co-located left-margin reference finding, unaffected).
Visible P011 count: 15 -> 11 (pages 11, 42, 66, 71 suppressed; pages 82 at 9.8pt and 83 at
11.0pt — past the natural gap, a different, unconfirmed magnitude — remain flagged).
`ester_sample_b` has no bottom-margin findings in the affected range; its visible P011
count (26) is unchanged.

## Validation

- `PYTHONPATH=src python -m pytest tests/test_p011_esther_r011_batch_2026_08.py -q` — 13
  tests, all pass.
- `PYTHONPATH=src python -m pytest tests/ -k "p011 or margin" -q` — pass.
- `ruff check .` — pass.
- `mypy src` — pass, 113 files.
- Full `pytest` — **3160 passed**, 3 warnings (baseline was 3157; +3 new boundary tests).
  Only the tests listed above needed count/fixture updates; all other suites unaffected.

## Remaining open questions for Esther

1. The 9.44-10.13pt+ bottom-margin clusters (e.g. Praneeth pages 37/40/54/59/70/94/104,
   Philip pages 19/28/32/37/etc.) remain unreviewed and unresolved; this fix deliberately
   stops at the natural gap below them.
2. Whether the same "last visible line on the page" mechanism, if formalized as a
   geometry-aware rule rather than a flat tolerance, should eventually replace the flat
   `BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT` — deferred; the current fix resolves the specific
   ground truth without that larger change.
3. Praneeth's recurring ~23.9pt single-line bottom-margin finding at a fixed x/y position
   across ~19 pages (a running footer-like element, distinct from and well outside the
   9.2pt cluster) was not part of this task's scope and remains flagged as before; it may
   warrant a separate Esther review of its own.
