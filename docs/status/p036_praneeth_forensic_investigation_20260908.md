# P036/Praneeth: Forensic Investigation of the Last Ground-Truth Blocker (2026-09-08)

> **Superseded 2026-09-14**: the ambiguity this document's "Decision: no
> code change" left open is resolved — Ester reviewed all 12 candidates
> described below and confirmed all 12 false positive, with an explicit
> governing rule. See
> `docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md`. This
> document is kept as-is below for its forensic record (the recovered
> exact reviewed pair, the arbitrary x-coordinate selection mechanism);
> only its "no code change" conclusion no longer holds.

## Why this document exists

After the P027/P030/P036 fixes in PR #535 (merged as `efd32d9`), the ground-truth
replay reported `ESTER_FP_REMAINING = 1`: one P036 finding on Praneeth's page 11
still replays as a regression. Because that page has 12 currently-firing P036
findings sharing the identical measured gap ratio (~1.19), it was initially unclear
whether this was (A) a genuine detector regression on the specific reviewed case, or
(B) a ground-truth replay-matching artifact (page-level granularity conflating an
already-fixed reviewed case with 11 other, never-reviewed findings). This document
records the forensic investigation that resolved that question, and the explicit
decision not to change any code based on its result.

## Recovering the exact reviewed finding

The live sheet's `R036` tab (`data/evaluation/private/ester_sheet_exports/
audito_feedback_20260908_live.xlsx`, cell B6) gives only generic evidence text
("Location: Top of page", gap ratio 1.19) -- insufficient on its own to identify
which of the 12 candidate pairs was shown to Ester.

The older, repository-tracked `docs/evaluation/ester_feedback/
R036_Ester_Auditor_Feedback.xlsx` -- whose `Correct?`/`Notes` columns are blank
(as established in PR #534's migration work) -- still carries the original evidence
text in column B, populated by `scripts/ester_batch/build_rule_package.py`'s
`_fallback_affected_lines()` (added in commit `6d68f8b`, "fix: improve Ester R036
evidence context"). That function copies a finding's `details["previous_entry_preview"]`
/`details["next_entry_preview"]` verbatim into "Previous entry: ..." / "Next entry: ..."
lines. For Praneeth, row 5:

```
Physical PDF page: 11
Location: body text
Affected content:
  1. "Previous entry: Characterization ………………………. …………………………………………"
  2. "Next entry: 1.2 Protein Quantification Using Mass Spectrometry……………………………"
Measured amount: 1.19 (gap ratio)
```

This text is a **verbatim, exact match** to one specific finding in the current
auditor's real output on the real PDF (confirmed by running the current auditor and
comparing `previous_entry_preview`/`next_entry_preview` directly, not by inspection
alone). The exact reviewed pair is therefore recovered with certainty: the gap
between the wrapped continuation line of entry "1.1 Biological Importance of
Proteins and Need for Quantification and Characterization ..." and the following
entry "1.2 Protein Quantification Using Mass Spectrometry...".

**That exact pair is still emitted by the current auditor today.** This rules out
explanation (B) (pure replay-matching artifact) for the specific reviewed instance --
see "Root cause classification" below for why it is not simply (A) either.

## Why an arbitrary-looking pair was the one shown to Ester

`scripts/ester_batch/lib.py`'s `select_weakest_finding()` -- the function that
picked which single finding, out of every P036 finding on the whole document, was
shown to Ester for review -- sorts candidates by confidence rank (LOW < MEDIUM <
HIGH), then page, then the x-coordinate of the finding's first highlight box as a
deterministic tie-break. P036 findings do not report a graded `confidence` field, so
`finding_confidence()`'s documented fallback ("this rule does not report graded
confidence at all -- treat as HIGH") applies uniformly, and all 12 same-page
candidates tie on confidence and page. **The specific pair shown to Ester was
therefore selected by an x-coordinate tie-break, not because it was judged more
likely to be a false positive than its siblings.**

## The 12 candidates are structurally indistinguishable

All 12 currently-firing P036 findings on Praneeth's page 11 share the same ~1.19
gap ratio. None of them involve a chapter/appendix/top-level heading transition (the
mechanism already fixed generically for R036/Anthony in PR #535 -- see
`docs/evaluation/ESTER_FEEDBACK_MIGRATION.md`). Ester's own written explanation for
*why* the Anthony case is a false positive (sheet row D3: "I think this is happening
because the next line is all caps... when the following line is a chapter title or
an appendix, this is not flagged") does not apply to any of Praneeth's 12 candidates
-- neither entry in the reviewed pair, nor in any of its siblings, is an all-caps
structural row. Her Praneeth comment is only "same as above," with no independently
re-derived mechanism. No other structural signal (entry level, wrap-adjacency, page
position) was found that distinguishes the reviewed pair from its 11 siblings.

## Root cause classification

```
ROOT_CAUSE = DETECTOR_REGRESSION, for the specific reviewed instance --
             AND that instance is computationally inseparable, by any
             structural signal actually evidenced, from 11 sibling
             findings on the same page that were never individually
             reviewed.
```

Neither the pure `REPLAY_EQUIVALENCE_AMBIGUITY` label (the exact case was in fact
recovered, not merely indistinguishable in the ledger's matching key) nor
`HISTORICAL_CASE_NOT_RECOVERABLE` (it was recovered, with high confidence, via an
exact text match) fits cleanly. The honest classification is a hybrid: the specific
regression is real and identified, but any general (non-hardcoded) fix for it
necessarily also changes behavior for 11 never-reviewed, structurally-identical
findings -- which is a materially different, larger decision than the P027/P030/P036
(Anthony) fixes, each of which had a clear, evidenced, narrowly-scoped structural
justification.

## Decision: no code change

Presented with this finding, the task owner explicitly chose not to implement a fix
of any of the three candidate shapes considered (page-wide-uniform-ratio exemption,
narrowly-targeted single-pair suppression, or a global threshold change) rather than
accept a generalization not fully justified by evidence alone. **No detector code,
ground-truth replay matcher, or ledger data was changed as part of this
investigation.** This preserves the existing, honest state:

```
ESTER_FP_REMAINING          = 1   (P036/Praneeth p11, unchanged)
CASE_EQUIVALENCE_UNRESOLVED = 1   (unchanged)
```

A future task, if it chooses to revisit this, should treat the evidence above (the
recovered exact pair, the arbitrary x-coordinate selection mechanism, and the lack of
a structural differentiator among the 12 candidates) as the starting point rather
than re-deriving it.
