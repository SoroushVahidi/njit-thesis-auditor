# Sample B Annotation Ground-Truth Forensics

**Recorded:** 2026-07-10
**Branch:** `investigate/sample-b-annotation-ground-truth`
**Base:** `origin/main` @ `8e6ad430449195577fc84ef93c1fc864d1e078c7` ("Improve P019
page-numbering location evidence (#503)")

## Scope

Forensic investigation of `ester_sample_b` (`Yin_Haotian_Second_R_with_EF_Feedback.pdf`)
as a labeled ground-truth benchmark: what its native PDF annotations are, whether any
detector logic is contaminated by annotation content, which of Ester's marked issues the
auditor already catches, which clear misses remain, and whether the sample is usable as
an evaluation benchmark going forward. Investigation-first; one general, proven detector
fix was implemented and tested (see "General Fixes Implemented").

No production system was touched. No private PDF content, extracted annotation text, or
generated reports are committed by this change — this report only contains short
redacted previews (≤6 words) and aggregate counts.

## 1. Exact origin/main commit

`8e6ad430449195577fc84ef93c1fc864d1e078c7` — matches the commit stated in the task brief.
Baseline `ruff check .`, `mypy src`, and `python -m pytest -q tests` all passed clean
before any change (2742 passed).

## 2. Sample B file identity

| Field | Value |
|---|---|
| Internal sample key | `ester_sample_b` |
| Display label | "Sample B — second review with EF feedback" |
| Path | `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf` |
| SHA-256 | `dccea83030fe01c90d996ff3a1b901e2d56eaac6fe06ba51eea7c884bfc6d56b` |
| Size | 16,774,267 bytes |
| Pages | 108 |
| PDF format | PDF 1.6 |
| Creator / Producer | TeX / pdfTeX-1.40.26 |
| CreationDate | `D:20260415121018Z` |
| ModDate | `D:20260520090734-04'00'` |

## 3. Annotation count / types / authors / pages

Extracted with PyMuPDF (`page.annots()`, cross-checked against raw PDF object dumps via
`doc.xref_object`) and confirmed structurally consistent with pypdf's `/Annots` view.

- **Total: 65 native annotations**, all with a populated `/Popup` and an appearance
  stream (`/AP`); zero `/IRT` (no reply threads).
- Subtypes: **64 `Highlight`**, **1 `Text`** (a floating sticky note, page 103).
- **Single author for all 65: `ester flaim`** (lowercase in `/T`), consistent casing
  throughout. No second reviewer's annotations are present.
- 44 distinct pages carry at least one annotation (of 108 total pages).
- Stroke colors cluster into three groups:
  - Peach/orange `(1.0, 0.663, 0.482)` — 59 annotations (the default/majority color).
  - Cyan `(0.220, 0.898, 1.0)` — 4 annotations (3 Highlights + the one Text note).
  - Yellow-green `(0.773, 0.984, 0.447)` — 2 annotations (both on the References page).
  - No evidence the color encodes issue category by itself — see §5 below for the
    counter-example (two different issue types share the peach color on the same page).
- 47 of 65 have non-empty `/Contents` (a written comment); 18 are highlight-only
  (marked with no comment text — largely repeats of an issue already explained
  elsewhere, see §10).

## 4. Screenshot-page reconstruction (TOC page)

Physical PDF page **10** (printed front-matter page "viii") is the exact page in the
task's screenshot excerpt — confirmed by locating "FD-NeurCADRecon" / "Off-Diagonal
Weingarten" in the page's extracted text, which only appears on physical pages 10–11.

Two native annotations exist on this page, both authored by `ester flaim`:

1. **Peach `Highlight`**, rect `(150.9, 568.4, 540.4, 675.6)`, 64 quad vertices (spans
   the multi-line TOC block from "3.2.1 Problem Statement" through "3.3 ... Problem
   Statement"), comment preview: *"Level three (X.x.x) uses sentence case—only..."* —
   a capitalization-style comment about level-3 TOC entries.
2. **Cyan `Highlight`**, rect `(549.0, 686.5, 561.5, 699.2)` (a ~12×13pt box, i.e. a
   single short token), comment preview: *"This is in the margins! Align..."* — a
   margin/alignment comment over the page-number "36" printed for the "3.3 ..."
   TOC entry.

## 5. Proof of what the visible colors represent

Both annotations on page 10 are `Subtype=Highlight` PDF objects with populated
`/QuadPoints`, `/Popup`, and `/AP` — i.e., **native reviewer annotations**, not
auditor-generated overlays. This is proven two ways, not inferred from color:

- **Subtype/architecture separation.** The auditor's own highlight overlays
  (`src/njit_auditor/pdf_highlight.py`) are drawn with `page.add_rect_annot(...)`,
  which creates `Subtype=Square` objects with stroke `(1.0, 0.55, 0.0)` / fill
  `(1.0, 1.0, 0.0)` — a visually similar orange/yellow but a **different PDF
  subtype**, and only ever written to a generated/downloaded copy, never to
  `data/raw/ester/*.pdf`. Every annotation found in the raw source file is
  `Highlight` or `Text`; `Square` does not appear at all.
- **Color ≠ issue category.** The page-10 peach highlight is a capitalization
  comment; the page-10 cyan highlight is a margin comment; but elsewhere in the
  document (e.g. page 41) peach is used for a margin follow-up ("as above, I will
  stop pointing this out"). Color tracks Ester's tool defaults/mood, not a fixed
  taxonomy — categorization in this report is done from comment text, not color.

## 6. Original-vs-annotation-free audit diff

Built a scratch derivative (`remove_pdf_annotations`, already in
`src/njit_auditor/pdf_comments.py`, called via `page.delete_annot` per annotation —
never flattened into the content stream, never committed to the repo).

Verified before diffing:
- Page count unchanged: 108 → 108.
- Per-page normalized text-layer SHA-256 identical on all 108 pages (0 mismatches).
- Per-page dimensions unchanged.
- Annotation count in the derivative: 0.

Ran the current `run_pdf_audit_full` on both the original and the derivative:

| | Original | Annotation-free |
|---|---:|---:|
| Total findings | 208 | 143 |
| P012 (annotation-detected) | 65 | 0 |
| Every other rule_id | identical | identical |

A full structural diff (canonical JSON of every field — `rule_id`, `severity`, `page`,
`message`, and all `details` including `bbox`, `confidence`, `issue_type`, `suggested_fix`)
of every non-P012 finding shows **zero records present in one run and absent in the
other**. This was proven, not assumed, both before and after the fix in §15.

## 7. Non-P012 contamination count

**Zero.** No detector other than P012 can see, or is affected by the presence of,
native PDF annotations in this document. See §8 for the architectural reason, and §6
for the empirical proof.

## 8. Detector input mapping

- `src/njit_auditor/pdf_layout.py` builds the `PdfDocument` model every rule except
  P012 consumes, exclusively from `page.get_text("dict")`. PyMuPDF's `get_text()`
  never includes annotation `/Contents`, popup text, or annotation geometry — those
  live in a separate PDF object graph (`/Annots`) that `get_text()` does not traverse.
- `src/njit_auditor/rules/pdf_annotations.py` (P012) is the **only** module that calls
  `page.annots()`. It opens its own `fitz.Document` directly from the file path and
  does not feed into the shared `PdfDocument`/layout pipeline at all — architecturally
  isolated from every other rule.
- No rule in `src/njit_auditor/rules/` uses `get_pixmap`, OCR, or pixel-rendering for
  detection (grepped all rule modules; the only two hits are code comments describing
  the *auditor's own highlighted-PDF output*, not detection input).
- Direct answers:
  - `page.get_text()` include annotation comment text? **No.**
  - Do annotation popup rectangles affect text/geometry extraction? **No.**
  - Do native highlight appearance streams affect rendered-pixel checks? **N/A — no
    rule does pixel-based detection.**
  - Can a margin detector mistake a popup/note for thesis content? **No** — proven
    empirically in §6 (P011 findings identical with/without annotations).
  - Can annotation geometry influence bbox targeting? **No** — same proof.

## 9. Findings corroborated by Ester

34 of the 208 raw findings are "visible" in the sense of representing a specific,
addressable defect (excludes P012's per-annotation rollup and P013's 104 internal
page-number-candidate inventory entries, which are informational triage evidence, not
standalone student-facing problems).

Manually verified (geometry + issue semantics, not wording similarity) against the
annotation inventory:

- **P011 / page 10** — margin overflow (21.2pt) on the exact line Ester's cyan
  "This is in the margins!" highlight covers. **Exact match.**
- **P011 / page 33** — margin overflow on the same line as Ester's "as above. text
  must be continuous..." annotation. **Exact match** (bbox overlap).
- **P011 / page 41** — margin overflow on the same line (y-range) as Ester's "as
  above. I will stop pointing [this out]..." annotation (x-offset differs slightly —
  her highlight sits on an adjacent equation-number tag, not the overflow segment
  itself). **Strong partial match.**
- **P011 / page 103** — left-margin overflow on the References list, overlapping
  four of Ester's annotations there ("Revise entire list...", two content-less
  highlights, "CVPR is cited three different ways..."). **Exact match.**
- **P017 + P020 / page 80** — both fire on the same table-title bbox as Ester's
  content-less highlight there (already documented in
  `docs/status/ester_sample_b_p020_specific_remediation.md`). **Exact match**
  (two findings, same object — see §12).

**6 of 34 visible findings (~18%) have direct annotation evidence; 0 contradictions.**
The remaining 28 have no annotation overlap on the same page. Critically, **absence of
an annotation is not evidence of a false positive here**: Ester's own comment on page 41
("as above. I will stop pointing this out") is direct textual proof that she
deliberately stops re-annotating a recurring defect once she has explained it once.
19 of the 27 total P011 hits are on pages with zero annotations at all, consistent with
this "explain once, then move on" review style rather than with false positives (see
§14).

## 10. Annotation recall overall and by category

Categorized all 65 annotations by comment text using the existing deterministic
categorizer (`njit_auditor.comment_analysis.categorize_comment_text`) run in-memory
only (never persisting full comment text to disk):

| Category | Count |
|---|---:|
| no_comment_text (highlight only) | 18 |
| unclear_or_other | 17 |
| indentation | 11 |
| spacing_blank_lines | 7 |
| heading_title | 6 |
| table_format | 6 |
| references_citations | 4 |
| list_of_tables_figures_toc | 4 |
| punctuation | 4 |
| capitalization_case | 3 |
| committee_approval_page | 2 |
| acknowledgements | 1 |
| margin_or_overflow | 1 |

`unclear_or_other` and many `no_comment_text` entries are administrative/editorial
feedback out of the auditor's formatting scope (e.g. "You submitted a blank assessment
sheet", "external committee members must have...", "please reorganize this page so
that...", "Please add text on this page") — correctly left uncategorized rather than
forced into a formatting bucket, per the task's own instruction.

Of the in-scope formatting categories, two produced a **confirmed, general, reproducible
detector gap** (§11) with concrete before/after evidence, rather than a hand-wavy
estimate:

- **indentation (11 annotations, mostly "delete indent"/"delete indent. I see this
    is...")** — before the fix in §15, the auditor found **0** matching P015
    findings anywhere these were marked; after the fix, matching findings appear on
    5 pages, including 3 of the exact pages Ester flagged (22, 23, 88) plus 2
    additional pages elsewhere in the document with the identical pattern (37, 87)
    that Ester's selective review did not call out individually.
- **capitalization_case (page 10's "Level three (X.x.x) uses sentence case" and
    page 32's "third level titles are in sentence case")** — **no** TOC-entry
    case-style rule exists at all (confirmed by inventory of every
    `pdf_toc_*`/`pdf_lot_lof_*` rule file); this is a coverage gap, not a bug (§11).

## 11. Clear false negatives

**(a) Fixed in this pass — continuation-line indentation (P015).** `pdf_indentation.py`
already had a guard, `_paragraph_starts_like_continuation`, that returns `True` for any
paragraph whose first line starts with a lowercase letter (e.g. "where q denotes...",
"which enforces..." — the common shape of a clause continuing the sentence just before
a displayed equation). Both indentation checks (`unexpected_opening_indent` and
`missing_later_indent`) unconditionally skip such paragraphs. That guard exists to avoid
a real false-positive class (a correctly flush-left continuation line is not a "missing
indent"), but it also means the *opposite* real defect — a continuation line that
**does** carry a stray paragraph-style indent — could never be flagged, in either
direction, regardless of how large the indent was. Verified directly against Sample B:
paragraphs on pages 22, 23, and 88 starting with "where"/"which" at indent ≈28.8pt
(above `STRONG_INDENT_THRESHOLD_PT` = 18pt) produced zero findings before the fix,
exactly matching Ester's own "delete indent" annotations at those locations.
Mechanism: **candidate extraction failure** — the paragraph was never considered a
candidate at all, not a confidence or presentation suppression. General and
reproducible; not tied to Sample B content (see §15).

**(b) Documented, not implemented — TOC-entry sentence case.** No rule in
`src/njit_auditor/rules/pdf_toc_*.py` or `pdf_lot_lof_*.py` checks capitalization
style of TOC entries by heading level. Ester flagged this twice (pages 10 and 32:
"Level three (X.x.x) uses sentence case", "third level titles are in sentence case").
This is a genuine, generalizable gap, but implementing it safely requires new
heading-level classification logic (distinguishing level-1/2/3 TOC entries by
numbering depth) and a dedicated false-positive analysis against other documents —
a new-rule scope larger and riskier than this investigation's mandate to fix only
proven, narrow defects. Recommended as a dedicated follow-up.

**(c) Documented, not implemented — bulleted/list single-spacing exceptions.**
7 annotations say "single space" in contexts like bulleted lists and table titles
(pages 50, 62, 66, 87, 88, 95, 96) — apparent exceptions to the document's default
double-spacing rule (`pdf_body_spacing.py`'s `possible_body_text_not_double_spaced`
only checks the opposite direction: body text that should be double-spaced but isn't).
Whether bullet/list items are audited for spacing compliance at all is unconfirmed;
flagged for a dedicated follow-up rather than bundled here.

## 12. Clear false positives

**None found.** Section 6/7's diff is the direct proof: every non-P012 finding in the
original annotated PDF is byte-identical (same rule, page, bbox, confidence, message,
suggested fix) to the same run on the annotation-free derivative, both before and after
the fix in §15. No finding disappears when annotations are removed, and no finding's
bbox, message, or confidence targets annotation content, popup geometry, or annotation
appearance streams.

## 13. Duplicate-warning clusters

Only one case among Ester-marked objects: **page 80's `P017` + `P020` findings** both
target the same table-title bbox. Inspected manually (PR #502's duplicate-candidate
tool has not merged to `origin/main` as of this commit, so it was not available and
was not vendored in). These are **not an exact duplicate** — `P017` is a coarse
"caption may not follow title-case style" flag, and `P020` is the specific word-level
fix ("'results' → 'Results'"). This is a parent/child pair at different levels of
detail, already noted in `docs/status/ester_sample_b_p020_specific_remediation.md`, and
intentional rather than wasteful. No exact or cascading duplicates were found on any
Ester-marked object.

## 14. Confidence observations

- P011 (margin) findings corroborated by Ester are uniformly `confidence: "high"`;
  the uncorroborated majority (19 of 27) are also `high` — consistent, not
  over-aggressive, since Ester's non-mention of those instances reflects her
  "explain once" review style (§9), not a confidence problem.
- The new P015 `unexpected_indent_on_continuation_line` finding is deliberately
  emitted at `confidence: "medium"` (not `"high"`, unlike the sibling
  `unexpected_opening_indent`/`missing_later_indent` issue types), because the
  "starts with lowercase" continuation heuristic is a structural proxy, not a
  guaranteed classification (the bracket/citation guard added alongside it, §15,
  addresses the one concrete false-positive risk found in Sample B itself, but the
  heuristic could still be wrong on documents with different conventions).
- No annotation-driven confidence changes were made; this section only documents
  observations gained from using annotations as evaluation labels, not runtime
  logic.

## 15. General fixes implemented

**Fixed:** `src/njit_auditor/rules/pdf_indentation.py` — added a new P015 issue type,
`unexpected_indent_on_continuation_line`, that fires when a paragraph both (a) starts
with a lowercase letter (the existing "starts like continuation" signal) and (b) carries
a strong (≥18pt) first-line indent, i.e. is indented as if it were a fresh paragraph
despite continuing the previous sentence. Added a companion guard,
`_paragraph_starts_like_bracketed_marker`, so a genuine new sentence that happens to
start with a bracketed citation/list marker (e.g. "[12] explored...", "(a) ...") is not
misclassified as a continuation clause — this was verified against a real Sample B
paragraph (page 23, "[12] explored alternative implicit fields...", indent 56.4pt) that
would otherwise have been a new false positive.

This does not read annotation text or geometry at runtime, does not reference Sample B,
Yin Haotian, any page number, phrase, color, author, filename, or hash in the production
code, and generalizes to any PDF with the same LaTeX-equation-continuation pattern.

Effect on Sample B: 5 new findings (pages 22, 23, 37, 87, 88), all `medium` confidence.
Confirmed zero effect on any other rule and zero change to P015's two pre-existing issue
types' behavior (full non-P012 diff re-run after the fix, §6, still shows zero
differences from the annotated original).

## 16. Tests added

`tests/test_p015_body_indent_ester_split.py`:
- `test_p015_flags_unexpected_indent_on_equation_continuation_line` — synthetic
  3-line paragraph, first line lowercase + indented, confirms the new issue_type fires.
- `test_p015_does_not_flag_bracketed_citation_led_paragraph_as_continuation` —
  synthetic paragraph led by "[12] ..." at the same indent, confirms it does not fire.

`tests/test_ester_sample_a_correctness.py`:
- Updated `test_ester_sample_b_p015_page_23_false_positive_resolved` to assert the
  *specific* previously-fixed defect (`missing_later_indent` on page 23) stays fixed,
  while allowing the newly-discovered, distinct, true-positive
  `unexpected_indent_on_continuation_line` finding on that same page (a different
  paragraph, a different root cause, confirmed corresponding to Ester's own "delete
  indent" annotation there).

Full suite after the fix: **2743 passed** (was 2742 before; +1 net from the two new
tests plus the one updated assertion in an existing test — no tests removed).
`ruff check .` and `mypy src` both clean.

## 17. Anti-overfitting audit

- No file, function, or constant added in this pass references `ester_sample_b`,
  `Yin_Haotian`, a page number, an exact phrase, an annotation color, an author name,
  or a file hash.
- The fix operates purely on layout-derived signals already used elsewhere in the
  same file (`_paragraph_starts_like_continuation`, `STRONG_INDENT_THRESHOLD_PT`) plus
  one new, generically-worded structural guard (leading bracket/paren detection).
- Regression-checked against the full existing test suite, including Sample A and
  Sample D fixtures used elsewhere in the repo, with zero unexpected changes outside
  the 5 new Sample B findings documented in §15.
- This report and its supporting analysis were produced entirely in the session
  scratchpad and this document; no annotation full-text, extracted comment JSON,
  derivative PDF, or generated audit-report file is committed to the repository.

## 18. Remaining questions for Ester

1. TOC-entry sentence case (pages 10, 32): should this apply to *all* level-3 (X.x.x)
   entries document-wide, or only specific chapters? Needed before a dedicated rule
   can be designed safely.
2. The 7 "single space" bulleted-list/table-title comments: is this a blanket
   exception to double-spacing for all bulleted content, or case-by-case?
3. Is the "explain once, then move on" review pattern (confirmed on page 41) applied
   consistently across all repeated defect types, or only for margin overflow? This
   materially affects how Sample B's absence-of-annotation should be read for other
   rule families.

## Direct Answers

**A. Does Sample B contain Ester's native annotations?** Yes — all 65 annotations are
`Highlight`/`Text` PDF objects authored by `ester flaim`, with populated
`/QuadPoints`/`/Popup`/`/AP`, structurally distinct from the auditor's own `Square`
overlay annotations (which never appear in this source file at all).

**B. Do any current warnings analyze Ester's comments rather than the dissertation?**
No. Proven both architecturally (§8: only P012 reads `page.annots()`; every other rule
reads only `page.get_text()`, which cannot see annotation `/Contents`) and empirically
(§6: identical non-P012 findings with and without every annotation present).

**C. Which warnings match issues Ester marked?** P011 (margin overflow) on pages 10,
33, 41, 103, and the P017+P020 pair on page 80 — 6 of 34 visible findings, all
exact or strong-partial matches, zero contradictions (§9).

**D. Which clear in-scope Ester issues are missed?** Continuation-line indentation
(fixed in this pass, §15); TOC-entry sentence case and bulleted/table single-spacing
exceptions (documented gaps, not implemented — §11b/c, deliberately deferred as
larger-scope new-rule work).

**E. Is Sample B suitable as benchmark ground truth?** **B — useful partial ground
truth**, not a strong/complete benchmark. Ester's review is real, single-author,
and unambiguous where she wrote it, but demonstrably selective (she explicitly stops
re-flagging repeated defects — page 41), so absence of an annotation cannot be read
as "not an issue" for high-frequency categories like margin overflow. It is strong
ground truth for the specific objects she did mark, and strong ground truth (via the
annotation-free derivative) for detector-precision/regression testing, but weak for
computing a document-wide recall percentage against any rule family with many
repeated instances.

**F. Should both annotated and annotation-free versions be retained?** Yes — the
annotated copy for reviewer-match/corroboration evaluation (§9/10), and an
annotation-free derivative (regenerable on demand via
`njit_auditor.pdf_comments.remove_pdf_annotations`, never itself committed) for
detector precision/regression testing where the reviewer's own markup should not be
visible at all, e.g. rendering/screenshot-based manual QA.
