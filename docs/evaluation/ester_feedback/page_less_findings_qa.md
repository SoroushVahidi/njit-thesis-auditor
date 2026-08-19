# Page-less finding audit

Enumerates every user-visible finding, across all 60 applicable rules and 7
dissertations, where the *independently recomputed* weakest surviving
finding has `page: None` (a document-level finding, not anchored to a
single physical page).

## Method

Re-derived directly from the raw cached per-document audit JSON
(`data/evaluation/generated/ester_all_rules_batch_20260819/*.json`),
independently of the batch runner's own selection code
(`scripts/ester_batch/qa/selection_qa.py`). Policy applied: select strictly
by lowest confidence (LOW < MEDIUM < HIGH); page is never a selection
criterion.

## A real bug was found and fixed

During preflight testing (before this QA pass), `lib.select_weakest_finding`
was written to prefer any page-anchored finding over a page-less one,
regardless of confidence, on the reasoning that a page-less finding
"provides no evidence page." This directly violated the evaluation policy
("never substitute a different finding merely because it is easier to
visualize") and was caught by this same audit: for **R019 (P019, page
numbering)**, 5 of 7 documents (Philip, Muyeed, Anthony, Praneeth, Patrick)
have a document-level LOW-confidence finding ("Mixed numbering styles
detected across candidate page-number regions.") that is strictly weaker
than any of their page-anchored MEDIUM findings, but the batch had
substituted a MEDIUM page-anchored finding instead.

**Fix applied:** `scripts/ester_batch/lib.py::select_weakest_finding` no
longer treats "has a page" as a selection criterion at all -- selection is
purely by confidence rank, matching the stated policy. R019 was regenerated
after the fix.

## Result after the fix

| Rule | Document | Expected confidence | Other paged candidates existed? | Generated output matches? |
|---|---|---|---|---|
| R019 | Philip | LOW | yes | ✅ |
| R019 | Muyeed | LOW | yes | ✅ |
| R019 | Anthony | LOW | yes | ✅ |
| R019 | Praneeth | LOW | yes | ✅ |
| R019 | Patrick | LOW | yes | ✅ |
| R019 | Youra | LOW | no (only finding) | ✅ |
| R019 | Sebastian | LOW | no (only finding) | ✅ |

All 7 page-less-expected rows now classify as **OK_DOCUMENT_LEVEL**: the
xlsx correctly records `Physical PDF page: not applicable (document-level
finding)` with the real message/confidence, and the combined PDF's
per-document evidence page is a text-only metadata panel (document name,
rule ID, confidence, the finding's own message) rather than a fabricated or
guessed page render. No page number was invented anywhere.

No other rule (of the 60 applicable) has a page-less finding as its
independently-recomputed weakest surviving finding, so no other rule was at
risk from this bug. This is not a sampling claim -- `selection_qa.py`
enumerates all 420 rule-document rows exhaustively.

## Classification legend applied above

- `OK_DOCUMENT_LEVEL` -- correctly selected and faithfully represented as a
  document-level finding.
- `WRONGLY_REPLACED` -- would have been the case for the 5 R019 rows before
  the fix; none remain after regeneration.
- `NOT_SELECTED`, `UNSUPPORTED_RENDERING`, `OTHER` -- not observed in this
  dataset.
