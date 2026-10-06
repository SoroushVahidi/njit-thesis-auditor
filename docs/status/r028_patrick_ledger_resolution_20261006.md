# R028 Patrick p13 Ledger Resolution (2026-10-06)

**Base:** `integration/pre-r045-safe-stack-20261006` at `4a2420b`. Ledger
data and migration code only; no detector, rule JSON, Q coverage or public
mapping change.

## Case

| Field | Value |
|---|---|
| Case ID | `CASE-b32f9a16bf5a` (Patrick, thesis version `TV-1edaca2a09dd`) |
| Rule | P028 / R028, `arabic_number_on_frontmatter_page` |
| Page | physical 13, printed 1 |
| Locator | `page_footer:page_number_regime` |
| Prior current verdict | `NEEDS_CLARIFICATION` (the sheet cell reads "CORRECT: but ...") |

## Authority (already on record, no new reviewer input)

- R028 sheet (2026-09-01 export): the real error is not the page number but
  the absence of the CHAPTER 1 heading.
- R019 sheet (2026-09-08, `r019_ester_sheet_authority_20260908.md`): the same
  page-1 situation marked "FALSE POSITIVE:" with the same explanation.
- `patrick_chapter1_rule_gap_20260902.md`: resolved as policy by Ester; P085
  was built from it.

So the page-number finding is not a violation, and the missing CHAPTER 1
heading is Patrick's separate P085 `TRUE_VIOLATION` case
(`CASE-4ce2161a9aab`, `body_chapter:first_heading`).

## Change

`KNOWN_ADJUDICATION_SUPERSESSIONS` (`review_ledger/importers/known_cases.py`)
records the settled verdict, and `migrate` appends a `FALSE_POSITIVE`
adjudication that supersedes the original one on the same case. The original
adjudication and the historical `KnownHistoricalCase` entry are unchanged.
The step is idempotent and refuses to supersede any unexpected current
verdict.

Replay (scratch copy of the private ledger): reviewed false positives
46 → 47 (0 remaining), reviewed true violations 4 (0 missing), unresolved
policy cases 1 → 0, identity ambiguities 0; P028 PARTIAL → CLEAN, P085 CLEAN.

The local private ledger is updated by running `migrate` with this code.

ASK_ESTER: NO.
