# R055: Email-Sourced Policy Guidance (2026-09-04)

## Why this document exists

`docs/status/ester_authority_matrix_20260902.json` records R055 as
`ester_decision_exists: NO` / "NO ESTER DECISION FOUND" as of 2026-09-02.
That was an accurate read of the sources checked at the time (the live
sheet's `R055` tab and the repository prose docs). It is not the complete
picture: Ester separately emailed an explicit, rule-wide policy statement
about R055 on 2026-09-04, reported by the repository owner (who received
and has direct access to the email; it is not independently re-derivable
from any source stored in this checkout — the live sheet and Gmail are
both outside this repository by design, consistent with this project's
existing sourcing convention, see the authority matrix's own
`source_limitations` field). This document records that provenance so the
ledger's policy resolution cites something reviewable in-repo rather than
a bare, uncheckable assertion.

## Source

- **Sender:** Ester Flaim <ester.flaim@njit.edu>
- **Date:** 2026-09-04
- **Subject:** `Re: Thesis Auditor – Feedback on R035, R036, and R055`

## Policy statement (as reported)

> For List of Tables / List of Figures entry type, entries should always
> appear with the word "Table" or "Figure" before the X.x number.

## Why this is policy guidance, not a case-level adjudication

The live sheet's `R055` tab (`data/evaluation/private/ester_sheet_exports/
audito_feedback_20260908_live.xlsx`, checked cell-by-cell on 2026-09-08)
has zero populated findings for any of the seven documents — every row
reads exactly `"No current auditor R055 finding."` in column B and both
`Comment`/`Ester Question 1` are blank for all seven. Per this migration's
own normalization rule E ("No current auditor finding" is historical
auditor state only, not an Ester verdict), there is no document/page to
attach a `ReviewCase`/`Adjudication` to. The policy statement above is
real and rule-wide, so it is recorded as a `Resolution` with
`case_id=None` and `policy_reference="R055@email:2026-09-04"` — the same
shape `importers.authority_matrix` uses for matrix-sourced policy — via
`importers.known_policies`. It is **not** counted in
`ESTER_REVIEWED_FP_TOTAL`/`ESTER_REVIEWED_TP_TOTAL` (those are case-level
metrics only) and no `TRUE_VIOLATION`/`FALSE_POSITIVE` was fabricated for
any of the seven documents on R055.

## Relationship to the existing P055 implementation

`docs/planning/p055_scope_and_design.md` (2026-06-05, predates this
policy statement) already implements a related but distinct check:
`check_pdf_lot_lof_entry_type` flags a List-of-Tables entry that starts
with "Figure" (or a List-of-Figures entry that starts with "Table") —
cross-*type* consistency. Ester's 2026-09-04 statement is about entry
*format* (the literal word "Table"/"Figure" must appear before the `X.x`
number at all), which is not the same check and is not verified here to
be already covered by P055's current implementation. No detector code was
changed as part of recording this policy — whether P055 (or a new rule)
should enforce the format requirement is deferred to a future scoping
task, consistent with this migration's constraint not to change detector
semantics.
