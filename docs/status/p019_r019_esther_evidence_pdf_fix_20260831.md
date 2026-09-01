# R019/P019 2026-08-31: Evidence-PDF Diagnosis + Repair (Not a Correctness Judgment)

**Date:** 2026-08-31
**Baseline:** R015/P015 checkpoint `9dce0079358045995a5f3743b9cb884dbfea86b6`
**Scope:** R019 human-review evidence packaging only. P019's detector logic
(`src/njit_auditor/rules/pdf_page_numbers.py`) gained only additive,
non-semantic metadata (see below) -- no finding was added, removed,
reclassified, or changed in confidence/message/rule_id/page.

## Why this task exists

Ester Flaim reported that she reviewed every prepared feedback sheet through
R033 except R019: the R019 review PDF (Drive file
`1CWOYO4Hy4ULjbE6YTdXzBkRmgorwpTko`, `R019_Ester_Auditor_Feedback.pdf`,
~10.8 KB) was "effectively empty" from her perspective -- she asked whether
the PDF could be populated, or whether she should review the rule some other
way. **This is not a report that R019's finding is wrong.** Per the task
brief for this work: do not assume R019 is wrong, do not tune P019 based on
our own interpretation, and do not use Ester's inability to review the PDF
as evidence the finding is false. This document diagnoses and repairs the
evidence-packaging gap only; no correctness label is recorded here.

## What R019/P019 means

- **Human-facing rule text** (`data/processed/rules/project_added_rules.json`,
  `id: P019`): "Do visible page numbers show inconsistent style, position,
  or sequence across the document?" Remediation: "front matter should use
  lowercase Roman numerals in sequence; the main body should use Arabic
  numerals starting at 1." Notes: "Conservative candidate-based
  sequence/style check; **does not yet enforce full NJIT policy**."
- **Implementation** (`check_pdf_page_number_sequence`): detects page-number
  *candidates* per page (position, style, value), then emits five distinct
  issue types, each independently gated: `sequence_gap`,
  `missing_page_number`, `mixed_numbering_style` (both **per-page** -- two+
  styles/positions on one page -- and **document-wide** -- two+ styles
  anywhere across the whole document), and `multiple_page_numbers`.
- **Per-page vs. document-wide**: the per-page checks (`sequence_gap`,
  `missing_page_number`, `multiple_page_numbers`, per-page
  `mixed_numbering_style`, `inconsistent_position`) all carry a real
  `page=N` and a `bbox`. The **document-wide** `mixed_numbering_style`
  finding is emitted once per document with `page` unset (`None`) and
  `confidence: "low"` -- it fires whenever two or more numbering styles
  appear anywhere among the document's plausible candidates, **with no
  awareness of where front matter ends and body begins**. This is the
  finding that was unreviewable.
- **Why it is "document-level"**: the check has no page-region model. It
  counts styles across the whole candidate set and, separately, computes
  `_style_transition_pages` -- the exact point(s) where the *primary*
  style changes from one page-with-a-candidate to the next. That transition
  data was already being computed and formatted into a
  `transition_pages` string (e.g. `"17:roman_lower->18:arabic"`) as of the
  2026-08-25 batch (see `tests/test_p019_location_evidence.py`), but the
  finding itself still had `page=None`, and no bbox for either boundary
  page was attached anywhere.
- **What evidence a reviewer needs**: per
  `docs/evaluation/ester_feedback/README.md`'s own standard (physical page +
  printed page + location + confidence + highlighted excerpt), a reviewer
  needs to *see* the two pages where the style change happens: the last
  page in the earlier style and the first page in the new style, each with
  its real printed page-number token highlighted.

## Current seven-document R019 output (real corpus, unchanged by this work)

All seven documents' **weakest surviving R019 finding** (the one the
evaluation protocol selects -- lowest confidence, `LOW < MEDIUM < HIGH`,
never chosen by page-presence) is the document-wide `mixed_numbering_style`
finding, LOW confidence, `page=None`. Each document also has additional,
stronger (MEDIUM), page-anchored R019 findings that are *not* selected under
the protocol (see `docs/evaluation/ester_feedback/README.md`, "Lowest
Confidence Target").

| Document | Total P019 findings | Weakest (selected) finding | Transition named |
|---|---:|---|---|
| Youra | 1 | doc-wide mixed_numbering_style, LOW | p.17 (`xv`, roman_lower) -> p.18 (`1`, arabic) |
| Anthony | 3 | doc-wide mixed_numbering_style, LOW | p.14 (`xii`, roman_lower) -> p.15 (`1`, arabic) |
| Muyeed | 2 | doc-wide mixed_numbering_style, LOW | p.21 (`xix`, roman_lower) -> p.22 (`1`, arabic) |
| Philip | 12 | doc-wide mixed_numbering_style, LOW | p.16 (`xiv`, roman_lower) -> p.17 (`1`, arabic) |
| Praneeth | 2 | doc-wide mixed_numbering_style, LOW | p.19 (`xvi`, roman_lower) -> p.20 (`1`, arabic) |
| Sebastian | 1 | doc-wide mixed_numbering_style, LOW | p.15 (`xiii`, roman_lower) -> p.16 (`1`, arabic) |
| Patrick | 4 | doc-wide mixed_numbering_style, LOW | p.12 (`xi`, roman_lower) -> p.13 (`1`, arabic) |

**Every one of the seven documents' selected finding is a single,
clean, lowercase-Roman-then-Arabic transition at exactly one page
boundary** -- the `expected_or_context` detail in all seven cases lists
exactly two styles (`arabic`, `roman_lower`) with one transition point each
(Philip and Patrick also have a small count of `roman_upper` candidates
elsewhere in the document from other sources, e.g. embedded front matter in
a bound appendix, but their *selected* weakest finding's own transition is
still the single roman_lower->arabic point above).

## Does a normal Roman-to-Arabic transition explain these findings?

**Evidence for "yes, structurally" -- presented for Ester's judgment, not
asserted as a verdict:**

- P019's own catalog `remediation` text states this transition (Roman front
  matter -> Arabic body starting at 1) *is* the expected convention.
- The catalog `notes` field states the check "does not yet enforce full
  NJIT policy" -- an acknowledged, documented simplification, not a hidden
  bug.
- `tests/test_p019_location_evidence.py::test_correct_uniform_roman_then_arabic_transition_produces_no_mixed_style_finding`
  (pre-existing, unchanged by this work) explicitly documents and asserts
  that even a clean, textbook-correct single front-matter/body transition
  **still fires** this LOW-confidence document-wide finding "by
  construction," because the check requires only that 2+ styles exist
  anywhere among plausible candidates -- it has no logic to recognize "this
  is one legitimate boundary" versus "these are genuinely inconsistent."
- The detector has **no page-region model** for this specific check: it
  does not know where front matter ends or body begins. (A *different*
  helper, `_front_matter_pages_for_toc_filter`, exists elsewhere in the same
  file for a different purpose -- filtering TOC destination numbers -- and
  is not used to gate this check.)

**This is not a conclusion that all seven findings are false positives.**
The detector's own LOW confidence and "manual review recommended" framing
(`_P019_TRIAGE_MAP`) exist precisely because it cannot make this
determination automatically. Only Ester can judge, per document, whether
the observed single-transition shape is the legitimate, expected boundary
or reflects some other inconsistency the current evidence would now let her
see and check herself (e.g., a page inserted at the wrong style, missing
numbers immediately around the boundary, etc.) -- the fix in this task
makes that judgment possible; it does not make it for her.

## Root cause of the unusable PDF

Traced through `scripts/ester_batch/`:

1. `build_rule_package.py::build_rule_rows` selects the weakest finding per
   document via `lib.select_weakest_finding` (confidence-only, correct per
   policy -- verified this is not the bug; see
   `docs/evaluation/ester_feedback/page_less_findings_qa.md` for the prior,
   separate fix that made selection itself page-blind).
2. `build_rule_package.py::_fill_evidence` calls
   `lib.build_evidence(pdf_path, row["physical_page"], ...)`. For all seven
   R019 rows, `row["physical_page"]` is `None` (the finding is document-level).
3. `lib.build_evidence`'s very first branch was:
   `if physical_page is None or physical_page < 1: return EvidenceResult([], "", [], None, False)`
   -- an unconditional, immediate empty return. **No dissertation page is
   ever opened**, regardless of anything else in `details`.
4. `_assemble_combined_pdf` then always writes a one-page text-only header
   (`_write_evidence_header_pdf`: document name, "Physical PDF page: n/a",
   confidence, message) and appends the evidence PDF only if
   `evidence_pdf.exists()` -- which it never did for these seven rows.

Result: each of the seven students' R019 section was exactly one page of
generic text with no dissertation content, no highlight, and no way to spot
-check the finding -- exactly matching Ester's "effectively empty"
description and the prior, already-known limitation recorded in
`docs/evaluation/ester_feedback/page_less_findings_qa.md`
("`OK_DOCUMENT_LEVEL`... a text-only metadata panel... No page number was
invented anywhere").

## Evidence-package design and fix

**Detector-side (additive metadata only, `pdf_page_numbers.py`):** the
document-wide `mixed_numbering_style` block already computed
`_style_transition_pages` and the per-page candidate lists it was derived
from (`filtered_by_page`). Six new detail keys were added to the *same*
finding, sourced from that already-computed data, for the *first* named
transition: `transition_prev_page`, `transition_prev_bbox`,
`transition_prev_label`, `transition_prev_style_label`,
`transition_new_page`, `transition_new_bbox`, `transition_new_label`,
`transition_new_style_label`. `rule_id`, `severity`, `page` (still unset),
`message`, `confidence`, and every pre-existing detail key/value are
byte-for-byte unchanged (verified: real corpus rerun below, plus
`tests/test_p019_location_evidence.py`).

**Evidence-side (`scripts/ester_batch/lib.py`, `build_rule_package.py`):**

- `_build_document_level_transition_evidence` (new): when a page-less
  finding's `details` carry a matched `transition_prev_page`/
  `transition_prev_bbox` + `transition_new_page`/`transition_new_bbox`
  pair, render **both** named pages via the existing, real-geometry-only
  `build_highlighted_single_page_pdf` (never a guessed box) and concatenate
  them into one 2-page evidence PDF. Returns `None` (falls through to the
  prior, unchanged empty-result behavior) when the pairing is absent -- true
  for every other page-less finding across the other 59 applicable rules.
- `build_evidence` now tries this path first for any `physical_page is None`
  finding, before falling back to the original empty result.
- `build_rule_package.py`'s xlsx cell (`_structured_block`), the overview
  table, and the per-student header page now show both physical pages and
  both printed-page labels explicitly (e.g. `16 and 17`, `"xiv" (physical
  p.16) / "1" (physical p.17)`) instead of "not applicable (document-level
  finding)", when this evidence is available.

## Pages selected per dissertation

Exactly the two transition-boundary pages already named in the finding's
own `transition_pages` metadata -- the last page in the earlier style and
the first page in the new style -- for all seven documents (see table
above). No other pages were added; no genuinely-inconsistent page exists to
show beyond the single named transition for any of the seven (per the
`expected_or_context` style counts, all seven have exactly one transition
point in their selected finding).

## Replacement PDF

- Path: `docs/evaluation/ester_feedback/R019_Ester_Auditor_Feedback.pdf`
  (existing repository convention; regenerated in place via
  `scripts/ester_batch/build_rule_package.py P019`).
- Structure: 1 overview (2 physical pages, landscape table) + 7 students x
  3 pages (1 text header + 2 highlighted evidence pages) = **23 pages**.
- `.xlsx` companion regenerated at the matching path; Column C (`Correct?
  (Y/N)`) and Column D (`Notes`) confirmed blank for all 7 rows;
  `validate_package` reported zero problems.

## Visual QA

Rendered and inspected the overview (both pages) and all three documents'
full 3-page blocks (Philip, Muyeed, Youra) at 150 DPI:

- Overview table: all 7 rows present, no clipped/overlapping cells (found
  and fixed one real defect: the "PDF page" column was an unwrapped plain
  string and visually collided with the neighboring column for the two-page
  "16 and 17"-style entries -- fixed by rendering it as a wrapped
  `Paragraph` and widening the column).
- Each student header page: document name, both physical pages, both
  printed-page labels, confidence, location sentence naming both pages and
  styles, both excerpted tokens ("xiv"/"1" etc.) -- legible, not clipped.
- Each evidence page: correct dissertation, correct physical page, real
  printed page-number token visibly yellow-highlighted at the true
  bottom-center location, no blank pages, no incorrect token highlighted
  (spot-checked against the finding's own `transition_*_label` values).
- `validate_package`'s own blank-page check (page has neither text nor
  images) also reported zero problems across all 23 pages.

## Sheet audit (live Google Sheet, read-only this session)

Read `1ZM7nJcw5KI5YGUkJBdE6hJyT7Y0Le-g1O1jiIb5RfBI` (Drive
`read_file_content`, natural-language corpus view -- no Sheets API cell
access available in this session). Confirmed structurally:

- The R019 tab exists with the expected `A1:D8` range: header row +
  7 document rows, matching the live-sheet convention documented in
  `docs/evaluation/ester_feedback/README.md` (`DOCUMENT` / `Possible R019
  violation...` / `Comment` / `Ester Question 1`).
- Could **not** verify individual per-row cell contents (whether Column B's
  link/text is current, or whether Columns C/D are blank per row) from this
  read-only, summarized view -- only the sheet's structure and header/sample
  row. No sheet content was altered.
- Column B's wording ("Mixed numbering styles detected across candidate
  page-number regions.") is accurate but, on its own, gives no hint that
  real page-anchored evidence now exists; the regenerated PDF's own header
  page and location line now supply that missing context. No sheet edit is
  proposed or needed beyond what the linked PDF already fixes.

## Drive update strategy (not executed this session)

Per task instruction, no Drive upload was performed. `ester_drive_pdf_map.json`
still reflects the **old** uploaded file (`1CWOYO4Hy4ULjbE6YTdXzBkRmgorwpTko`,
~10.8 KB, `status: "uploaded"`) and was deliberately left untouched -- updating
it to claim "uploaded" would misrepresent Drive state that has not actually
changed. Recommended path once this package is reviewed and approved:

1. Confirm this local PDF/xlsx pair is final (Ester has not yet been asked to
   re-review; that should happen only after this diagnostic work itself is
   reviewed).
2. Upload the new local PDF **content** to the *same* Drive file ID
   (`1CWOYO4Hy4ULjbE6YTdXzBkRmgorwpTko`) if the available tooling supports an
   in-place content replace for that file -- this is strictly preferred, since
   it preserves the exact link already embedded in the R019 Sheet's column B
   and requires no Sheet edit at all.
3. If in-place replacement is not supported by the available tooling, the
   safe fallback is: upload as a new Drive file, update only the R019 Sheet's
   column-B link to the new file, verify the new link opens correctly, and
   leave every Ester-entered field (there are none yet, for R019) untouched.
4. Update `docs/evaluation/ester_feedback/ester_drive_pdf_map.json`'s R019
   entry (`file_id`, `url`, `size_bytes`, `status`) only after a real upload
   has happened and been verified -- never speculatively.

## Was P019 (detector) logic changed?

**Classification: NO DETECTOR CHANGE YET / EVIDENCE-METADATA FIX ONLY.**

- `pdf_page_numbers.py`: additive detail keys only, on the *same* existing
  finding. `rule_id`, `severity`, `page`, `message`, `confidence`, and every
  pre-existing detail key are unchanged. Verified via
  `tests/test_p019_location_evidence.py`'s new assertions and a full real
  seven-document rerun (identical finding counts/pages/messages/confidences
  to the pre-change baseline in every case; see `git diff` for the exact 24
  added lines).
- `scripts/ester_batch/`: evidence-rendering and reviewer-facing text only.
  No change to which finding is selected, no change to any other rule's
  package generation path (confirmed no other `Rxxx_Ester_Auditor_Feedback.*`
  file was touched; new fallback-preserving tests lock this in).
- The underlying policy question ("is a clean Roman-to-Arabic transition,
  with no region-boundary awareness, the right thing to flag at all, even at
  LOW confidence?") is explicitly **not** answered or acted on here. That is
  Ester's call once she can actually see the evidence -- which she now can.

## Files changed

- `src/njit_auditor/rules/pdf_page_numbers.py` (additive detail keys)
- `scripts/ester_batch/lib.py` (transition-pair evidence rendering)
- `scripts/ester_batch/build_rule_package.py` (reviewer-facing text +
  overview-table wrapping fix)
- `tests/test_p019_location_evidence.py` (2 new tests)
- `tests/test_ester_batch_transition_evidence.py` (new, 6 tests)
- `docs/evaluation/ester_feedback/R019_Ester_Auditor_Feedback.pdf` (regenerated)
- `docs/evaluation/ester_feedback/R019_Ester_Auditor_Feedback.xlsx` (regenerated)
- `docs/status/p019_r019_esther_evidence_pdf_fix_20260831.md` (this file)

Not changed: any other rule's detector, any other rule's
`Rxxx_Ester_Auditor_Feedback.*` package, `data/specs/*`, canonical rule
catalog JSON, R016-R018/R020+ artifacts, R017, or any deployment/live
worktree state.

## Validation

- `PYTHONPATH=src python -m pytest tests/test_p019_location_evidence.py -v`
  -- 19 passed (17 pre-existing + 2 new).
- `PYTHONPATH=src python -m pytest tests/test_ester_batch_transition_evidence.py -v`
  -- 6 passed (new file).
- `PYTHONPATH=src python -m pytest tests/ -k "p019 or page_number or ester_batch" -q`
  -- 232 passed.
- `PYTHONPATH=src python -m pytest tests/test_rule_registry_consistency.py tests/test_rule_classification_consistency.py tests/test_ester_rule_consistency_audit.py tests/test_evaluation_data_manifest.py -q`
  -- 176 passed.
- `ruff check .` -- pass (whole repo, including `scripts/`).
- `mypy src` -- pass (113 files).
- Full `pytest` -- **3177 passed** (baseline 3169 + 8 new tests; zero
  pre-existing tests required updating).

## Remaining questions for Ester

1. For each of the seven documents, is the shown last-Roman/first-Arabic
   transition the expected, correct front-matter/body boundary, or does it
   reflect a genuine inconsistency? (This is now directly visible in the
   regenerated PDF for the first time.)
2. Should P019 eventually gain real front-matter/body region awareness so
   this check stops firing on legitimate single transitions -- and if so,
   at what confidence/scope? (Explicitly a follow-up detector-logic
   question, not addressed in this evidence-only task.)
3. Anthony, Philip, and Patrick's non-selected, page-anchored MEDIUM
   findings (missing/multiple/inconsistent page numbers, and a third style
   -- `roman_upper` -- appearing in Philip/Patrick's broader candidate set)
   were not part of this task's evidence fix, since the evaluation protocol
   selects only the weakest finding per document; flagged here only for
   visibility, not as a request to change selection policy.

## Next action

Evidence package is ready for a maintainer to review this diagnostic work
itself (not yet sent to Ester). Once approved: execute the Drive update
strategy above, then ask Ester to review the regenerated R019 PDF using her
existing Drive link (if in-place replacement is used) or a Sheet-link update
(if not).
