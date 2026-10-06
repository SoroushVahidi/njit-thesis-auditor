# Public Card Ownership and R028 Patrick p13 Authority (2026-10-06)

**Base:** `fix/ester-20261005-r024-r045-reconciliation` at `6b70aae`.
**Trigger:** the 2026-10-05 closed-rule integrity audit found three emitted
issue types with no `/rules` card and one non-replayable historical case
(R028 Patrick p13).

No detector logic, threshold, rule ID or canonical rule JSON changed. The
seven-document corpus raw findings are byte-identical before and after.

## Ownership table

| Issue type | Internal rule | Current owner (before) | Possible owner | Source Q | Ester authority | Semantic fit | Risk | Decision |
|---|---|---|---|---|---|---|---|---|
| `unexpected_indent_on_continuation_line` | P015 | none | R015A / R015B / new R015C | none | Muyeed p144 and Philip p17 FALSE POSITIVE (row-split extraction artifacts, fixed 2026-08-25; Philip p21 replays under the p17 verdict); no confirmed true positive; four representative current findings (Sample B p22, Yin H 3rd p26, Pennock p121, Termini p116) are already queued for her review in the 10-05 reconciliation package | R015A covers the first paragraph after a heading; R015B says paragraphs *should* be indented. Neither describes "a continuation line must not be indented" | Mapping to R015B would tell students the opposite of the finding; a new card would state a requirement no NJIT text, Q row or confirmed Ester verdict states | **GENUINELY_AMBIGUOUS** — left unmapped |
| `misaligned_page_number_column`, Table of Contents page | P018 | none | R075 | Q052 | Q052 (Ester's matrix) restates the NJIT guideline's TOC bullet: "Page numbers should be right-aligned ... Use leaders ... to connect the section title to the page number." Ester split LoT/LoF alignment into Q069/Q079 but kept TOC alignment inside Q052 | R075 is Q052's public TOC card; its remediation already says "Right-align page numbers" | Low: link only. Not R048 (LoT/LoF only, `docs/planning/p048_scope_and_design.md` excludes TOC) | **OWNED_BY_ANOTHER_EXISTING_PUBLIC_RULE → R075** |
| `misaligned_page_number_column`, LoT/LoF page | P018 | none (bug) | R018N / R018Q | Q069 / Q079 | Ester rows Q069/Q079 | exact | The routing existed but read `section_type`; P018 emits `page_type`, so it never fired | **MAP_TO_EXISTING_R018_ATOMIC_CARD** (key fix) |
| `missing_page_number`, Table of Contents page | P018 | none | R075 | Q052 | Q052: "Every TOC entry must connect to a right-aligned page number" | R075's question asks whether each TOC entry is connected to its page number | Low; zero current corpus findings on TOC pages | **OWNED_BY_ANOTHER_EXISTING_PUBLIC_RULE → R075** |
| `missing_page_number`, LoT/LoF page | P018 | none | R018D? | none | No NJIT or Ester presence rule for list pages (guideline LoT/LoF sections are silent; Q069/Q079 cover alignment only); current findings are in the 10-05 package awaiting review | R018D's list scope comes from a project extension of Q052, not from Ester | Would assert a policy no authority states | **GENUINELY_AMBIGUOUS** — left unmapped |

`missing_page_number` emitted by P019 (page footers) is a different issue and
keeps its R019 owner.

## Changes

- `web_app._resolve_p018_public_card`: read `page_type` as well as
  `section_type`; route P018 `misaligned_page_number_column` and
  `missing_page_number` on Table of Contents pages to P075.
- R018N/R018Q card specs list `misaligned_page_number_column`.
- R075 public "what it checks" (override, canonical JSON untouched) now names
  missing page numbers and the right-aligned column.
- `tests/test_public_card_ownership_20261006.py`.

## R028 Patrick physical page 13

| Field | Value |
|---|---|
| Document | Patrick |
| Physical page | 13 |
| Printed page | 1 |
| Issue type | `arabic_number_on_frontmatter_page` (P028, historical) |
| Structural location | page footer, first Arabic-numbered page; top heading is INTRODUCTION, the literal CHAPTER 1 heading first appears on physical page 16 |
| Current detector result | P028: no finding. P085 `missing_first_chapter_one_heading`: reported (TRUE_VIOLATION, replayed) |
| Why not replayable | the ledger recorded it as NEEDS_CLARIFICATION because Ester's cell says "CORRECT" while explaining the page number is not the error |

Authority already on record:

1. R028 sheet, this exact case: "the real error is not the page number but
   the absence of the header CHAPTER 1".
2. R019 sheet, same page and same failure mode: marked FALSE POSITIVE with
   the same explanation (`docs/status/r019_ester_sheet_authority_20260908.md`).
3. `docs/status/patrick_chapter1_rule_gap_20260902.md`: "already resolved as
   policy by Ester, not an Ester follow-up question"; P085 was built from it.

The page number is right and the defect belongs to R085. Current output
matches: P028 silent, P085 reports. `tests/test_p085_first_chapter_heading.py::
test_introduction_before_later_chapter_one_is_reported` already locks this
shape (P085 fires; P019 and P028 stay silent), so no new test was needed.

**Result: R028_PATRICK_ALREADY_RESOLVED_EXACT. Ask Ester: no.**

## Canonical JSON follow-up (not changed here)

CANONICAL_JSON_FOLLOWUP_REQUIRED:
- P075 `rule_definition`: add TOC missing page numbers and page-number column
  (currently only in the web override).
- P018 `notes`/`remediation`: record that TOC page-number column and presence
  findings are shown under R075.
