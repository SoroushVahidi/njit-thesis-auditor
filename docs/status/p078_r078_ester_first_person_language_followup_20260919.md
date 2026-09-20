# R078 Ester First-Person Language Follow-Up (2026-09-19)

## Reviewer Ground Truth

Ester adjudicated two R078 cases:

- Muyeed: FALSE POSITIVE. The auditor interpreted lowercase `i` in `i.e.` as
  first-person singular language.
- Praneeth: TRUE POSITIVE. The abstract contains genuine first-person plural
  language using `we`.

No private surrounding prose is used by the implementation.

## Reconstructed Rule Semantics

R078/P078 implements Q005 for the Abstract page body only. It checks the
document's first detected Abstract page and does not scan headings, chapters,
references, or acknowledgements. The documented pronoun inventory is:

- standalone capital `I`;
- `me`, `my`, `mine`, `we`, `us`, `our`, and `ours` with ordinary
  case-insensitive word boundaries.

Lowercase standalone `i` is not treated as the singular pronoun because Ester
explicitly required capital standalone `I`. `i.e.` is therefore not a finding.
Standalone `I` with ordinary punctuation remains detectable. Contractions are
not treated as standalone `I` tokens. No new quote or contraction policy was
invented beyond this lexical boundary rule.

## Root Cause and Fix

The previous detector used one case-insensitive regex for `i|me|my|mine|we|us|our|ours`.
That made the `i` in `i.e.` indistinguishable from pronoun `I`.

The detector now uses separate lexical paths: a case-sensitive standalone
capital `I` matcher and the existing case-insensitive matcher for the documented
non-`I` pronouns. This is an R078-local change; shared text tokenization was not
modified.

## Reviewer Matrix

| Case | Ester | Before | After | Result |
|---|---|---:|---:|---|
| Muyeed abbreviation | FALSE POSITIVE | report | no report | PASS |
| Praneeth `we` | TRUE POSITIVE | report | report | PASS |

## Seven-Document Audit

| Dissertation | Before | After | Change |
|---|---:|---:|---:|
| Youra | 0 | 0 | 0 |
| Anthony | 0 | 0 | 0 |
| Muyeed | 1 | 0 | -1 |
| Philip | 0 | 0 | 0 |
| Praneeth | 1 | 1 | 0 |
| Sebastian | 0 | 0 | 0 |
| Patrick | 0 | 0 | 0 |
| **Total** | **2** | **1** | **-1** |

The only changed finding is the reviewed Muyeed lowercase-`i` abbreviation
false positive. The reviewed Praneeth `we` finding remains reportable.

## Validation and Privacy

- Synthetic tests cover `i.e.`, lowercase `i`, uppercase `I`, `we`, internal
  letter `i`, punctuation, abbreviation adjacency, and case distinction.
- No private PDFs or dissertation text are committed.
- `LEADER_PLACEMENT_RULE_GAP` remains separate and unimplemented.
