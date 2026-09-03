# Patrick CHAPTER 1 Coverage Gap (2026-09-02)

Ester's judgment is explicit: Patrick's first body heading must be the
literal `CHAPTER 1`; `INTRODUCTION` in that position is an error. This is a
structural requirement, not a reason to report a P019 mixed-numbering finding.

## Current trace

| Candidate rule | Question | Implementation | Evaluates Patrick? | Reports missing literal CHAPTER 1? |
|---|---|---|---|---|
| P019 / R019 | Do visible page numbers show inconsistent style, position, or sequence across the document? | `src/njit_auditor/rules/pdf_page_numbers.py` | Yes, page-number candidates; current output is zero | No |
| P028 / R028 | Do front-matter numbered pages use lowercase Roman numerals and body pages use Arabic numerals? | `src/njit_auditor/rules/pdf_page_numbering_regime.py` | Yes; current output is zero | No |
| P027 / R027 | Do numbered headings follow the expected level-specific capitalization and punctuation style? | `src/njit_auditor/rules/pdf_heading_levels.py` | Yes where numbered headings are present | No; an unnumbered `INTRODUCTION` is outside this rule's current heading-style condition |
| P038 / R038 | Do required front-matter section headings appear with their canonical text? | `src/njit_auditor/rules/pdf_frontmatter_headings.py` | Yes for front matter | No; body chapter headings are explicitly outside scope |

Patrick's PDF has `INTRODUCTION` at the first Arabic-numbered body position
(physical page 13, printed page 1), and a later `CHAPTER1` heading is detected
on physical page 16. The existing rules therefore evaluate numbering and
heading-style prerequisites but none reports the missing literal first-body
`CHAPTER 1` requirement. P019 correctly remains clean under Ester's ruling.

## Scoped missing-rule gap

No existing implemented public rule semantically covers this exact condition.
Do not overload P019 or P028, and do not assign a new public rule ID in this
status pass.

If the catalog is later extended, the needed binary rule could be:

> Does the first body page begin with the literal heading `CHAPTER 1`?

Remediation:

> Add the literal `CHAPTER 1` heading at the start of the first body chapter.

This is an implementation-coverage gap already resolved as policy by Ester,
not an Ester follow-up question. No source behavior was changed here because
there is no existing rule to correct without inventing new rule scope.
