# R068 Ester Approval-Committee-Spacing Follow-Up (2026-09-21)

## Reviewer Ground Truth

Ester Flaim marked the R068 findings for **Anthony**, **Praneeth**, and
**Sebastian** as false positives. She explained that Approval Page
committee-member blocks are spaced according to (a) how many people are on
the committee and (b) how many lines each committee-member entry occupies —
there is not a fixed universal spacing/indicator requirement.

**`ESTER_CONFIRMED_R068_TRUE_POSITIVES = 0`** — no Ester-confirmed R068 true
positive exists in the tracked authority sources
(`docs/evaluation/ester_feedback/R068_Ester_Auditor_Feedback.xlsx`/`.pdf`,
`data/specs/ester_p_rule_feedback.json`,
`docs/evaluation/ester_feedback/live_sheet_pending_content.json`). The
tracked xlsx/pdf snapshot's "Correct? (Y/N)" and "Notes" columns are empty
for all three cases — the verdict above was communicated directly and is
recorded here for the first time; no true positive is invented.

## Canonical Scope

R068/P068 implements a structural extension beyond Q013 (Q013 itself is only
the "APPROVAL PAGE" heading-formatting check, already covered by
`pdf_frontmatter_headings.py`). Q015–Q020 (honorifics, advisor-first
ordering, rank ordering, alphabetization, NJIT-first ordering,
institution/location text) are explicitly manual-only and out of scope; none
of Q013/Q015–Q020 specifies a signature/date indicator-line count
requirement. The `approval_page_signature_blocks_sparse` and
`approval_page_advisor_role_label_missing` issue types were both
implementation heuristics added as a general "approval pages typically look
like this" extension, not derived from a numbered NJIT requirement.

## Old Detector Semantics

`check_pdf_approval_page_committee_blocks` (`src/njit_auditor/rules/
pdf_approval_page_committee_blocks.py`):

1. Detects a unique `APPROVAL PAGE` heading (or, if absent, a single
   structural role-label-density fallback page via P072).
2. Scans body lines below the heading as a **flat list** — it has no concept
   of grouping lines into distinct per-committee-member "blocks" and no
   geometric/bbox measurement at all (confirmed: the module never reads
   `PdfTextLine.bbox`).
3. Counts, across the whole page: `role_label_count` (lines matching a
   curated advisor/committee phrase list), `date_label_count` (lines
   matching `^date\s*:`), `signature_label_count` (lines matching
   `^signature\s*:?`), and `signature_blank_count` (lines ≥8 chars that are
   ≥70% fill characters, e.g. `____`).
4. `approval_page_advisor_role_label_missing` fires when no advisor-specific
   phrase (not just "committee member") is found among ≥2 role labels.
5. `approval_page_signature_blocks_sparse` fired when
   `signature_date_indicator_count < max(2, role_label_count)` — i.e. it
   assumed every role-label line should be matched by roughly one
   text-extractable date/signature/blank indicator line elsewhere on the
   page. This is the false-positive-implicated check.

**What it does not understand** (Phase 2 checklist): it has no concept of
committee size beyond a raw role-label count, no per-entry line-count
awareness, no wrapped-entry/continuation handling, no vertical-distribution
or geometric measurement over the page region, and cannot distinguish
"legitimately shorter entry" from "missing block." Everything is a single
page-wide ratio.

## Root Cause of the False Positives

Structural (non-text) inspection of the three real approval pages under the
old detector, comparing role-label lines against indicator lines:

| Alias | Physical page | role_label_count | advisor_present | date/sig/blank indicator lines found |
|---|---:|---:|---|---:|
| Anthony | 5 | 5 | true | 0 |
| Praneeth | 6 | 5 | true | 0 |
| Sebastian | 5 | 6 | true | 0 |

All three correctly detected role labels and the advisor label, yet **zero**
text-extractable date/signature/blank indicator lines were found on any of
them — not because the entries lack signature/date blocks, but because this
detector's text-pattern matching cannot reliably observe them in these
templates:

- Praneeth's and Sebastian's approval pages have a short (4-character),
  non-colon label line immediately after each role-label line — structurally
  present, but not matched by `_is_date_label`/`_is_signature_label`, which
  require a colon.
- Anthony's approval page has no isolated label line at all following each
  (much longer, name+role-combined) role-label line — consistent with the
  signature/date block being rendered as non-text graphics (a drawn
  underline) rather than extractable text, or embedded inline in a way this
  line-start-anchored matching cannot see.

Neither case is a genuine missing signature/date block; both are limits of
text-pattern extraction across differing institutional/template layouts —
independent technical confirmation of Ester's plain-language explanation
that layout (and therefore this text signal) legitimately varies and is not
governed by a fixed ratio.

## Authority Analysis

**Disposition: RETIRE_OR_DISABLE_RULE**, scoped specifically to the
`approval_page_signature_blocks_sparse` issue type.

- No NJIT/Q-rule source (Q013, Q015–Q020) specifies a fixed
  indicator-count-to-role-label ratio, or any signature/date count
  requirement at all.
- Ester, the authoritative reviewer, confirmed three real findings from this
  exact check as false positives and gave a general (not document-specific)
  reason: legitimate layout variation.
- The underlying signal is independently shown to be unreliable across
  templates (zero indicator lines detected on all three FP documents despite
  role labels being correctly found).
- Threshold tuning is rejected: there is no gap-width, ratio, or minimum
  count that reliably separates "sparse" from "normal" here, because the
  measurement itself (text-extractable indicator lines) does not reliably
  track whether a real signature/date block exists. Retuning the ratio would
  only move the false-positive boundary, not remove it, and risks new false
  negatives with zero validated true positives to justify the trade.
- `approval_page_advisor_role_label_missing` is **not** implicated: it never
  fired on any of the seven real documents, no reviewer evidence contradicts
  it, and it rests on a more robust signal (presence of any of several
  curated advisor phrases anywhere on the page, not a count ratio). It
  remains active and unchanged.

This is not a threshold-tuning task and no replacement geometric rule
(overlap, margin, clipping, reading order) is implemented, because none is
supported by any documented NJIT requirement or by Ester's feedback, which
describes a layout-variation false positive, not a structural defect.

## Chosen Disposition and Implementation

Following the established repository pattern for retiring a fixed-threshold
heuristic that produced Ester-confirmed false positives with zero confirmed
true positives (see `docs/status/
r036_production_page_relative_suppression_design_20260916.md` for the R036
precedent), `approval_page_signature_blocks_sparse` reporting is gated off
by a module-level constant,
`_SIGNATURE_BLOCKS_SPARSE_REPORTING_ENABLED = False`, in
`pdf_approval_page_committee_blocks.py`. The counting logic
(`date_label_count`, `signature_label_count`, `signature_blank_count`,
`signature_date_indicator_count`, `required_indicators`, `confidence`) is
left fully in place and still computed — only the `findings.append(...)` for
this issue type is now conditioned on the gate. This:

- preserves the rule's historical identity and documentation instead of
  deleting it;
- keeps the door open for a future, evidence-backed re-enablement (a
  one-constant change) if a real true positive is ever confirmed or a better
  structural signal is found;
- does not add any author/dissertation-specific exception, physical-page
  hardcoding, or private string — the gate applies uniformly to every
  document;
- remains conservative: when ambiguous, the detector now simply says
  nothing about signature/date sparseness, rather than guessing.

## Synthetic Regression Coverage

`tests/test_p068_approval_page_committee_blocks.py` (22 tests) and
`tests/test_p072_approval_page_heading_gate_recall.py` were updated/extended
to cover the retirement:

- the exact false-positive shape (role labels + advisor present, zero
  indicators) no longer reports `approval_page_signature_blocks_sparse`, on
  both the heading-gate and P072 structural-fallback paths;
- a small committee (2 entries) with zero indicators: no finding;
- a large committee (6 entries) with zero indicators: no finding;
- one-line combined role+name+affiliation entries: no finding;
- multi-line/wrapped entries (extra continuation lines): no finding;
- unequal indicator distribution across entries (some have a signature/date
  line, others none): no finding;
- an ambiguous partial-indicator mix: no finding (never resolves to sparse);
- `approval_page_advisor_role_label_missing` is verified to still fire when
  genuinely absent, confirming the retirement did not touch that check.

No genuine "true positive" case was fabricated for the sparse check, per
`ESTER_CONFIRMED_R068_TRUE_POSITIVES = 0`.

## Seven-Document Audit

| Dissertation | Before | After | Change |
|---|---:|---:|---:|
| Youra | 0 | 0 | 0 |
| Anthony | 1 | 0 | -1 |
| Muyeed | 0 | 0 | 0 |
| Philip | 0 | 0 | 0 |
| Praneeth | 1 | 0 | -1 |
| Sebastian | 1 | 0 | -1 |
| Patrick | 0 | 0 | 0 |
| **Total** | **3** | **0** | **-3** |

All three removals are the Ester-confirmed false positives; no new R068
finding appeared anywhere on the corpus.

Youra, Muyeed, Philip, and Patrick already had 0 R068 findings before this
change for an unrelated reason: their approval pages produce
`role_label_count = 0` under the curated phrase list (the `_MIN_ROLE_LABELS`
gate aborts before either check runs), meaning this detector does not
recognize their committee-block role-label wording at all. That is a
pre-existing recall gap, separate from the false-positive issue this task
addresses, and is out of scope here — it is not touched by this change and
is noted for future investigation only.

## Closed-Rule Regression Anchors (same seven-document corpus)

| Rule | Expected | Observed |
|---|---:|---:|
| R066 | 0 | 0 |
| R040 | 43 | 43 |
| R046 | 0 | 0 |
| R048 | 5 | 5 |
| R053 | 1 | 1 |
| R054 | 4 | 4 |
| R078 | 1 | 1 |

All six anchors unchanged; the R078 reviewer-confirmed Praneeth finding is
still present.

## Privacy

No private PDFs or dissertation text are committed. This document and the
structural evidence above contain only aliases, physical page numbers,
line-count/character-class structural measurements, and the four categorical
line tags (`ROLE`/`DATE`/`SIG_LABEL`/`SIG_BLANK`/`OTHER`) already used
internally by the detector — no verbatim approval-page text, committee-member
names, honorifics, or institution names appear anywhere in this record.
