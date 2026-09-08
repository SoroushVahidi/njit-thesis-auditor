# R019: Reconciliation Against the Live Ester Feedback Sheet (2026-09-08)

## Why this document exists

The cached export at
`data/evaluation/private/ester_sheet_exports/audito_feedback_20260901.xlsx`
(2026-09-01) has a completely blank `Comment` column on its `R019` tab for
all seven documents -- no Ester verdict recoverable from that snapshot.
The live Google Sheet (id `1ZM7nJcw5KI5YGUkJBdE6hJyT7Y0Le-g1O1jiIb5RfBI`,
Drive `modifiedTime` 2026-09-04T19:51:44Z) was checked directly on
2026-09-08 via the Google Drive connector and found to contain six
explicit "FALSE POSITIVE:" verdicts on that tab. This document records
that authority, matching the precedent set by
`docs/status/r018_r024_ester_sheet_authority_20260907.md`.

## Diff against the cached 2026-09-01 export

A fresh export was downloaded and diffed cell-by-cell against every tab of
the cached 2026-09-01 export (private, gitignored; not committed). Only
four tabs differ:

- `R019`: 12 cells changed (`Comment`/`Ester Question 1` newly populated
  for Youra, Muyeed, Philip, Praneeth, Sebastian, Patrick -- Anthony's row
  is still blank, i.e. NOT_REVIEWED, not an adjudication). This is the
  only tab with genuinely new case-level verdicts.
- `R035`, `R036`: comment cells for Anthony/Praneeth were filled in by
  this point, but the verdicts match what a prior 2026-09-07 direct check
  had already recorded in `known_cases.py` (sourced from
  `docs/status/r035_praneeth_text_fallback_fix_20260907.md`). No new
  information; not re-migrated a second time.
- `R015`: Youra's comment cell (D2, the free-text improvement suggestion)
  gained one extra sentence. Does not change the FALSE_POSITIVE verdict
  already migrated from this row.

No other tab differs at all -- R019 is the only rule whose case-level
authority actually changed between the cached export and this direct
check.

## R019 sheet content (verbatim `Comment` / `Ester Question 1` columns)

All six rows begin with the literal text "FALSE POSITIVE:" (with or
without a trailing colon typo) -- unambiguous per this migration's
verdict-normalization rule A (explicit false/false positive -> case-level
`FALSE_POSITIVE`), not a "CORRECT, but ..." case.

- **Youra** (C2): `FALSE POSITIVE:` / (D2) `SAME AS PHILIP comment`
- **Anthony** (row 3): both columns blank -- NOT_REVIEWED, no adjudication.
- **Muyeed** (C4): `FALSE POSITIVE:` / (D4) `SAME AS PHILIP comment`
- **Philip** (C5): `FALSE POSITIVE:` / (D5) policy guidance: "Can you code
  into the auditor that the page that starts with 'chapter 1' is page 1
  in roman numerals? Also can you code into the auditor that the page
  that starts with 'Approval Page' is page iv in roman numeral? All pages
  are numbered sequentially in roman numerals after this page. Roman
  numerals stop when CHAPTER 1 appears at the top of the page."
- **Praneeth** (C6): `FALSE POSITIVE:` / (D6) `SAME AS PHILIP comment`
- **Sebastian** (C7): `FALSE POSITIVE:` / (D7) `SAME AS PHILIP comment`
- **Patrick** (C8): `FALSE POSITIVE:` / (D8) `This case is a little
  different: There is an error on page 1: the student did not add the
  CHAPTER 1 header and instead wrote introduction.`

Patrick's note names the same defect already migrated separately as his
P085 `TRUE_VIOLATION` case (`missing_first_chapter_one_heading`, sourced
from `docs/status/patrick_chapter1_rule_gap_20260902.md`). It is recorded
as context on the P019 entry, not folded into a second verdict on a
different rule -- consistent with how R028's Patrick case (root cause also
P085) is handled.

## Rule finding shape

R019's populated row for every document (the `Possible R019 violation`
column) is the auditor's document-level "mixed dominant style across
document" warning (`issue_type=mixed_numbering_style`,
`pdf_page_numbers.py`), which is reported with `page=None` by design (see
that function's own comment: "still document-level/None"). The migrated
`KnownHistoricalCase` entries use `physical_page=None` to match.

## Verified against the fresh seven-document audit

Ran the current auditor (`run_audit_for_uploaded_file`) against all seven
private PDFs and filtered for `rule_id == "P019"`:

```
Youra:      0 P019 findings
Anthony:    1 P019 finding (issue_type=multiple_page_numbers, page 94 --
            a different issue_type, not reviewed, no conflict)
Muyeed:     0 P019 findings
Philip:     0 P019 findings
Praneeth:   0 P019 findings
Sebastian:  0 P019 findings
Patrick:    0 P019 findings
```

None of the six reviewed documents currently produces a
`mixed_numbering_style` finding -- all six FALSE_POSITIVE verdicts replay
clean (equivalent current finding absent, as expected). No detector
mismatch found for R019; no code change to rule semantics was made or is
needed.

```
R019_ESTER_REVIEWED_FP_TOTAL = 6   (Youra, Muyeed, Philip, Praneeth, Sebastian, Patrick)
R019_ESTER_FP_REMAINING = 0
R019_ESTER_REVIEWED_TP_TOTAL = 0
R019_UNRESOLVED_POLICY_CASES = 0   (Philip's roman-numeral policy note is preserved as
                                     reviewer_comment context on the migrated cases, not
                                     tracked as a separate unresolved-policy record --
                                     no distinct document/page was sent for a policy-only
                                     review the way R055's LoT/LoF note was)
R019_STATUS = resolved (all six reviewed false positives confirmed absent from current output)
```
