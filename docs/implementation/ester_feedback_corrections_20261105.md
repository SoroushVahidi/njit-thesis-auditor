# Historical feedback corrections, November 5, 2026

This implementation addresses the four verified false-positive mechanisms from
Ester Flaim's historical-feedback audit, bounded R036 reporting, the existing
R027/R055 candidates, and missing R039/R040/R045 confidence. It does not claim
completion of the audit's broader semantic/manual-check backlog.

## Authority and behavior

The historical workbook (`1ZM7nJcw5KI5YGUkJBdE6hJyT7Y0Le-g1O1jiIb5RfBI`), the
October workbook (`1J0oOZX-oeMvACP9PCM7k6ELrRACXgOO9aYDr5wzimFM`), and the
September 4, 14, 16 and 22 replies establish the applicable policy. Private
source/target details remain in the November 5 audit directory, outside Git.
No unanswered November 5 question is treated as a decision.

| Mechanism | Correction and controls |
| --- | --- |
| R019/R029 missed Roman folio | An outlined/scanned page with no text layer is insufficient evidence of a missing visible number. R019 abstains on that page; truly blank/readable pages still receive missing-number checks. R029 accounts for intervening physical pages, excluding explicitly unnumbered pages. Repeats, decreases and actual gaps remain detectable. No OCR or invented numeral is introduced. |
| R019 front-matter/body transition | A single lowercase-Roman → Arabic transition at CHAPTER 1 is valid independently of the Arabic value. Numeric sequence defects and reversion to Roman in body remain reportable. |
| R024 minor word before small caps | Word joining uses actual text origins when available. Font-dependent glyph-box offsets on the same baseline no longer masquerade as scripts. Real sub/superscripts and genuine lowercase major-word errors remain controls. Rotated local views discard untransformed baseline metadata. |
| R027 terminal period | Reuses the focused detector/tests from PR #651, head `44f721a`. Geometry-aware bold-prefix reading finds the actual terminal period before ordinary run-in body text; whitespace does not terminate the heading. Missing periods, colons, italic/math continuations and case errors remain controls. |
| R055 list prefixes | Reuses PR #650, head `2ccc598`. Applies the literal Table/Figure policy to singleton and appendix entries; supplies stable entry identity and geometry. High requires an exact prefix and a separate unambiguous numeric folio; uncertain geometry stays Medium. |
| R039/R040/R045 confidence | Assigns explicit canonical Medium to hierarchy, list-ending and publication-spacing heuristics, with a reason. Reviewer agreement and high triage priority do not establish universal High reliability. Existing R045 numbering confidence remains unchanged. |

## Bounded R036 restoration

Ester requires single spacing within wrapped titles and double spacing between
entries. The rejected fixed-ratio detector cannot safely be restored: 24 approved
examples contradicted its cutoff. The existing strong multi-signal gate is now
active, with no numerical threshold changes, for clear isolated tight gaps on
sufficiently populated pages. Reporting additionally requires a clean same-level
entry pair and clean normal support on both sides. Diagnostic gate overrides are
per-call, avoiding process-global mutation during concurrent audits.

Controlled positive tests demonstrate emission for TOC, LoT and LoF. Historical
rejections, uniform rhythm, sparse pages, one-sided evidence, moderate anomalies
and reconstructed/wrapped ambiguity remain negative controls. Reporting confidence
is Medium. Uniformly single-spaced pages cannot be distinguished reliably from
accepted layouts using this page-relative evidence alone; they remain outside
this detector's validated reporting scope. This is partial, functioning coverage,
not a universal double-spacing certification. The original corpus contains no
Ester-adjudicated R036 positive; no such endorsement is claimed.

The shared coverage disclosure and requirement-card status now describe active
partial reporting. Historical reports describing disabled reporting are preserved.

## Verification and delivery

Synthetic tests run in normal CI. Original cases are opt-in through
`NJIT_ESTER_AUDIT_SOURCE_MANIFEST`, pointing to an external approved manifest with
source SHA-256 hashes. They verify the five rejected targets disappear, 15 genuine
findings remain, and the three historical positives receive explicit Medium.
No manuscript text or PDF fixture is added to Git.

The source-baseline repair also improves one R018 highlight from a continuation
line to its owning wrapped entry; the same leader violation remains. Before/after
comparisons normalize only report numbering/anchors to distinguish presentation
renumbering from detector changes. Detailed private execution evidence belongs in
`notes/ester_feedback_implementation_20261105/`, outside the source checkout.

Both web and desktop import these shared detectors. This PR does not deploy the
web, change the published Windows installer, update reviewer sheets, or send mail.
The Windows release must eventually be rebuilt and qualified from the merged
revision. Existing pinned production references remain historical oracles and are
not rewritten to conceal intentional candidate changes.
