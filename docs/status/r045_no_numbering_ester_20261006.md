# R045: Biographical Sketch Publications Must Not Be Numbered (2026-10-06)

**Base:** `integration/pre-r045-safe-stack-20261006` at `08d3513`.

## Authority

Ester Flaim, reply in the "feedback" email thread, 2026-10-06, answering the
2026-10-05 question "MUST be numbered or MUST NOT be numbered?":

> The list of publications on this page MUST NOT BE NUMBERED. There should be
> a different check for the publications on this page and REFERENCES Section.
> On the bio sketch page publications are listed in REVERSE CHRONOLOGICAL
> ORDER and they are not numbered because they are not references. They must
> however be formatted in the same format as the references (if references
> are formatted in IEEE, the biosketch must be formatted in IEEE but without
> the number in front)

The same email confirms the R024D/R024E split (List of Tables and List of
Figures title case, distinct codes). No further clarification is needed.

| Requirement | Older authority | 2026-10-05 | 2026-10-06 | Effective rule |
|---|---|---|---|---|
| Numbering | none | "not numbered" (ambiguous) | MUST NOT BE NUMBERED | Mandatory prohibition; implemented (P045) |
| Single spacing within entries | Q028 | mandatory | — | Mandatory; implemented (P045) |
| Blank line between entries | Q028 | — | — | Unchanged; implemented (P045) |
| Hanging indent | Q029 | optional | — | Optional; never flagged |
| Reverse chronological order | Q027 | — | explicit | Mandatory; already implemented (P067, Q027) |
| Citation format | Q030 | — | same as References, without the number | Authority only; not implemented (Q030 stays unimplemented) |

## Implementation

`pdf_biosketch_publication_layout.py` (P045) emits
`biosketch_publication_entry_numbered` (one finding per page, with the count,
label style and the first numbered row's bbox) when a row at the left edge of
the Publications/Presentations section starts with a list label:

- `[n]` always;
- `(n)`, `n.`, `n)` when the row opens the section or at least two rows carry
  such a label.

Not treated as numbering: four-digit years, numbers inside a row (volume,
issue, pages, DOI, conference years), letters or roman numerals (`(a)`, `I.`).
The check runs before the spacing checks and does not need two separated
entries, so a single numbered entry is reported. The spacing checks and their
gates are unchanged. Only the Biographical Sketch page is inspected; a
numbered References section is not.

Public card R045 (question, what it checks, remediation), the polished
comment, explanations, issue label and the per-finding suggested fix now say
the entries must not be numbered and should keep the References citation
format without the number. The numbering finding cites no Q row (none covers
numbering). Canonical P045 text is updated to match; Q coverage is unchanged.

## Corpus

Seven-document corpus versus `08d3513`: the only change is one new
`biosketch_publication_entry_numbered` finding on Patrick physical page 5
(two `[n]` entries). Patrick's existing single-spacing finding is unchanged;
no hanging-indent finding. All other findings are byte-identical. The 12
other historical PDFs produce no numbering finding.

## Policy state

R045 numbering: POLICY_RESOLVED (2026-10-06). No specific-case adjudication
was recorded; the review ledger holds no R045 case. ASK_ESTER: NO.

Future authority-backed work: a Q030 check that Biographical Sketch entries
use the same citation format as the References section.
