# Post-generation QA: all-rules Ester evaluation packages

Base: `origin/main` = `17d6c219cfd22f367d38b8432d62c9ef152c9476`, worktree
`njit-thesis-auditor-ester-all-rules-batch-20260819`, branch
`chore/ester-all-rules-batch-20260819`.

## Summary

| Metric | Value |
|---|---|
| Rules in catalog | 82 |
| Applicable to this batch | 60 |
| Skipped (not applicable, with reason) | 22 |
| Rule-document rows independently re-checked | 420 (60 x 7) |
| Selection mismatches found | 12 initially -> **0 real defects** after fix (7 remaining are expected R011 tie-break differences, out of scope) |
| Page-less selection issues found | 5 (all in R019) -> **fixed and regenerated** |
| All-zero rules | 34, all classified VERIFIED_ZERO |
| XLSX structural failures | 0 |
| PDF structural failures | 0 |
| Visual QA failures | 0 (12+ pages across 10 rules, 5+ families, visually inspected) |
| Cache/version mismatches | 0 |
| Rule packages fixed/regenerated | 1 (R019); 9 wrongly-generated packages removed (P069-073, P076, P077, P079, P081) |
| Rules READY | 59 |
| Rules READY_WITH_NOTES | 1 (R011) |
| Rules NEEDS_REGENERATION | 0 |
| Rules BLOCKED | 0 |

## What this QA pass found and fixed

### 1. Selection-policy bug (page-less findings wrongly replaced) — real bug, fixed

`lib.select_weakest_finding` (as shipped in the original batch run) preferred
any page-anchored finding over a page-less one, regardless of confidence.
This violated the stated policy ("never substitute a different finding
merely because it is easier to visualize") and was caught by independently
re-deriving the correct selection from raw cached data
(`scripts/ester_batch/qa/selection_qa.py`, which deliberately does not
import the code under audit).

**Impact:** R019 (P019, page numbering), 5 of 7 documents (Philip, Muyeed,
Anthony, Praneeth, Patrick). Each had a document-level LOW-confidence
finding ("Mixed numbering styles detected across candidate page-number
regions.") that is strictly weaker than any of that document's page-anchored
MEDIUM findings, but the batch had substituted a MEDIUM page-anchored
finding instead.

**Fix:** `scripts/ester_batch/lib.py::select_weakest_finding` — removed the
page-anchored-preference sort key; selection is now purely confidence-rank
based, matching policy. R019's xlsx/pdf were regenerated. See
`page_less_findings_qa.md` for the full row-by-row account.

**No other rule was at risk** — the independent recomputation enumerates
all 420 rows exhaustively; only 7 have a page-less expected selection at
all, and all 7 are in R019.

### 2. Rule-applicability/mapping bug (infrastructure-only rules wrongly evaluated) — real bug, fixed

9 rules in the original "applicable" set — P069, P070, P071, P072, P073,
P076, P077, P079, P081 — are documented in their own catalog notes as
"Infrastructure-only" or "Reporting-only" with "no standalone findings" /
"no standalone issue types." They reorganize or localize *other* rules'
findings (heading-gate infrastructure for P014/P038/etc., triage/report
reorganization for P019/P036/P038/P044/P013/P026) and structurally cannot
ever emit their own violation. The original `discover_rules.py` only
excluded rules by `phase` (tex_source/docx_comments/evaluation_task) and
missed this category, so these 9 were generated as ordinary rule packages —
7 of them silently produced "No current auditor finding" for all 7
documents (technically true, but misleadingly framed: there is no check
here that could ever flag a violation, unlike a real detector that checked
and found nothing), and 2 (R073, R081) had already regenerated identically
before this was caught, since a first attempted fix based on free-text note
matching missed them (their notes say "Reporting-only" without the literal
phrase "no standalone findings").

**Fix:** `discover_rules.py` now determines applicability from
`rule_source_scan.detector_emitted_pairs_by_static_scan()` — a static AST
scan of the actual rule source confirming the rule_id is ever attached to
an `AuditFinding` — instead of notes-text pattern matching. This is
code-grounded rather than free-text-dependent. All 9 rule_ids are correctly
excluded now, with a clear `skip_reason` recorded in the manifest. Their 9
previously-generated packages were deleted (never a valid evaluation
package to begin with).

### Everything else: no defects found

- **Selection semantics** (Phase 2): 420/420 rows match the independently
  recomputed expected selection, except R011's 7 rows, which is the
  pre-existing, human-curated reference using a different (rule-specific,
  documented) tie-break criterion and is explicitly out of scope for
  regeneration.
- **XLSX structure** (Phase 5): all 60 pass — correct sheet name/header,
  exactly 7 rows with the correct document set, blank reviewer columns, no
  formulas, no internal tie-break language, no margin-specific wording on
  non-margin rules, no stale R011-specific text.
- **PDF structure** (Phase 6): all 60 pass — opens cleanly, overview page
  mentions the rule ID, TOC entry count/order matches the documents that
  actually have a finding, no blank pages.
- **All-zero rules** (Phase 4): all 34 classified VERIFIED_ZERO — see
  `all_zero_rules_qa.md` for the full per-rule audit, including a
  structural argument that applies to all 34 (unconditional invocation, no
  swallowed exceptions, static-scan-confirmed rule_id, fresh cache) plus
  direct content verification for the front-matter-heading-dependent
  cluster (P014/P025/P038/P043/P044/P045/P047/P067) and a code-level proof
  for P082 (experimental, disabled by default — a config gate, not a
  content-driven zero).
- **Cache/current-code grounding** (Phase 7): the cached per-document audit
  JSON was built in this worktree at `HEAD == origin/main`, and
  `git status --short src/` was empty for this entire session — no detector
  code was changed at any point, so every selected finding comes from the
  current, real auditor output.
- **Targeted visual QA**: rendered and inspected the overview page plus
  representative evidence pages for R011 (reference/margin), R019
  (page-numbering, LOW-confidence document-level selection), R020 (title
  capitalization), R017 (figure captions, HIGH-only), R036 (TOC/list
  spacing, HIGH-only), R024 and R046 (LOT/LOF entry numbering), and two
  all-zero rules (R012, R064). Highlights land on the correct region in
  every case; no clipped/rotated/blank/duplicated pages; overview table
  wrapping is clean (a real wrapping bug — the "Printed page" column
  overflowing into "Location" — was found and fixed during initial
  construction, before this QA pass).

## Final readiness classification

**READY (59):** R012, R013, R014, R015, R016, R017, R018, R019, R020, R022,
R023, R024, R025, R026, R027, R028, R029, R030, R031, R032, R033, R034,
R035, R036, R037, R038, R039, R040, R041, R042, R043, R044, R045, R046,
R047, R048, R049, R050, R051, R052, R053, R054, R055, R056, R057, R058,
R059, R060, R061, R062, R063, R064, R065, R066, R067, R068, R074, R078,
R082.

**READY_WITH_NOTES (1):** R011 — pre-existing, human-reviewed reference
package, untouched by this batch/QA. Its per-document tie-break criterion
(smallest overflow nearest the 3.0pt threshold) differs from the generic
batch's tie-break (lowest page number) within the same MEDIUM confidence
tier — both are policy-compliant (same confidence tier selected either
way), this is purely a documented, intentional difference, not a defect.

**NEEDS_REGENERATION (0)**

**BLOCKED (0)**

## Caveat / recommended follow-up

All-zero classification for 26 of the 34 all-zero rules rests on the
structural argument (unconditional invocation + no swallowed exceptions +
static-scan-confirmed rule_id + fresh cache) plus plausibility of a narrow
precondition, not on direct per-rule content verification of all 7
documents. 8 of the 34 (the front-matter-heading-dependent cluster) got a
direct, positive content check on 3 of 7 documents. If the task owner wants
stronger certainty on any specific all-zero rule before trusting it, the
efficient next step is a targeted manual look at that rule's specific
section across all 7 PDFs — not a batch regeneration, since nothing here
points at a generator bug for those rows.

## Not done in this pass (per instructions)

No sync to Ester's live Google Sheet, no Drive upload, no email, no commit,
no push. All fixes and regenerated artifacts remain in the working tree of
this isolated worktree for review.
