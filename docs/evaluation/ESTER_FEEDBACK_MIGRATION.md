# Ester Feedback Migration and Ground-Truth Replay

Phase 2 of the review-ledger work (2026-09-07), corrected 2026-09-07 after
the initial pass was found to be materially incomplete (see "Correction:
the initial migration undercounted the real authority" below), again
2026-09-08 after R019 was found to have been populated in the live sheet
after the 2026-09-01 export was taken (see "Correction 2: R019" below),
and again 2026-09-08 after Ester's R055 policy, sent by email rather than
recorded on the R055 sheet tab, was reported (see "Correction 3: R055
email policy" below). Builds on
`docs/evaluation/ESTER_REVIEW_DATA_MODEL.md` (read that first). Code:
`src/njit_auditor/review_ledger/importers/`, `ground_truth.py`,
`new_review_gate.py`, `cli.py`. Tests: `tests/test_review_ledger/`
(synthetic) plus a real run against the private ledger (not tracked, not
reproducible from CI -- see "Running it yourself" below).

## Correction: the initial migration undercounted the real authority

The first migration pass (below, `known_cases.py` with 8 entries) treated
the repository-tracked `Rxxx_Ester_Auditor_Feedback.xlsx` packages and
`docs/status/*.md` prose as the only available sources, and concluded --
correctly, for those sources -- that they carried almost no case-level
verdicts. **The root cause of the gap was source selection, not parsing:**
those XLSX packages are outgoing snapshots (sent for review) that were
never the destination Ester actually recorded her judgments in. The
live Ester feedback Google Sheet (spreadsheet id
`1ZM7nJcw5KI5YGUkJBdE6hJyT7Y0Le-g1O1jiIb5RfBI`) is the real, current
record, and a populated export of it
(`data/evaluation/private/ester_sheet_exports/audito_feedback_20260901.xlsx`,
gitignored, 2026-09-01 snapshot) contains explicit, dated verdicts across
tabs `R011` through `R036` (and further, mostly-blank tabs beyond that)
that the first pass never looked at.

`known_cases.py` was rewritten from 8 to 44 entries against this export
(see "What actually exists to migrate" and "Actual result", both updated
below). Every new entry's page/issue_type was independently re-verified
against a real run of the current auditor on the real private PDF -- this
surfaced two real matching-granularity bugs (`P011`'s
`margin_boundary_violation` and `P024`'s per-word title-case findings each
collapse multiple, independently-adjudicable variants onto one page) fixed
generically via `ground_truth.qualify_issue_type()`, and surfaced four
genuine, previously-unknown detector regressions (`P027`/Praneeth p69,
`P030`/Anthony p11, `P030`/Praneeth p12, `P036`/Anthony p12, `P036`/Praneeth
p11 -- five regressed cases across three rules) that are real findings of
this migration, not migration bugs -- see "Replay failures: root-caused,
not fixed" below. No detector semantics were changed to make these numbers
better.

## Correction 2: R019

This document originally reported (see "What is still not migrated" below,
now updated) that no populated R019 verdict text existed in any located
source. That was an accurate read of the 2026-09-01 export at the time,
but not of the live sheet: the sheet's Drive `modifiedTime` is
2026-09-04T19:51:44Z, three days after that export was taken, and a direct
check against the live sheet on 2026-09-08 found R019's `Comment` column
populated with six explicit `FALSE POSITIVE:` verdicts (Youra, Muyeed,
Philip, Praneeth, Sebastian, Patrick -- Anthony's row is still blank).
See `docs/status/r019_ester_sheet_authority_20260908.md` for the full
transcription, the cell-by-cell diff against the cached export (confirming
R019 is the only rule with genuinely new case-level verdicts since
2026-09-01), and the fresh-audit verification. `known_cases.py` grew from
44 to 50 entries; `ESTER_REVIEWED_FP_TOTAL` grew from 40 to 46. All six new
cases replay `CLEAN` (P019 finding absent from every reviewed document,
confirmed against a corrected environment -- see "Running it yourself"
below for the PyMuPDF-version note this surfaced). No detector semantics
were changed.

## Correction 3: R055 email policy

This document previously reported R055 as carrying no recoverable
authority at all (see "What is still not migrated" below, now updated).
That was correct for the sheet: `R055`'s tab has zero populated findings
for any of the seven documents in the 2026-09-08 live export -- every row
reads exactly `"No current auditor R055 finding."`, verified cell by
cell, not an adjudication under this migration's own normalization rule
E. It was not correct for Ester's authority as a whole: she separately
emailed an explicit, rule-wide policy statement about R055 on 2026-09-04
(reported by the repository owner, who has direct access to the email;
neither the live sheet nor Gmail is stored in this checkout, consistent
with the authority matrix's own `source_limitations` field -- see
`docs/status/r055_ester_email_policy_20260904.md` for the full record).

Because no document/page finding exists to attach a case to, this is
recorded as **rule-wide policy guidance, not a case-level adjudication**:
a `Resolution` with `case_id=None` and
`policy_reference="R055@email:2026-09-04"`, via the new
`importers.known_policies` module (same shape `importers.authority_matrix`
already uses for the dated-JSON-sourced policy rows). No
`TRUE_VIOLATION`/`FALSE_POSITIVE` was fabricated for R055 on any of the
seven documents, and R055 is deliberately absent from the per-rule
case-level table below -- it has no cases. `POLICY_GUIDANCE_TOTAL` (a new
metric this correction adds, counting every `Resolution` with
`case_id=None` across both `authority_matrix` and `known_policies`) grew
from 36 to 37; `ESTER_REVIEWED_FP_TOTAL`/`ESTER_REVIEWED_TP_TOTAL` are
unchanged at 46/3 (case-level metrics only). No detector code was changed.

## What actually exists to migrate

Before writing the first version of any importer, every plausible source
under `docs/evaluation/ester_feedback/` and `docs/status/` was inventoried.
That inventory was itself incomplete (see the correction above); the
complete picture is:

1. **Rule-level policy** -- `docs/status/ester_authority_matrix_20260902.json`,
   a dated snapshot recording, per public rule (`R001`-`R085`), whether an
   explicit Ester decision existed as of 2026-09-02, its text, and its
   evidence source. This has no per-document, per-page granularity.
2. **Case-level history, prose form** -- dated `docs/status/*.md` files
   (e.g. `p011_r011_ester_9_2pt_boundary_resolution_20260831.md`,
   `r018_r024_ester_sheet_authority_20260907.md`,
   `r035_praneeth_text_fallback_fix_20260907.md`,
   `patrick_chapter1_rule_gap_20260902.md`) -- each records a specific,
   dated relay of an Ester verdict, not a bulk export.
3. **Case-level history, live sheet export** -- the authoritative source:
   `data/evaluation/private/ester_sheet_exports/audito_feedback_20260901.xlsx`,
   a 2026-09-01 export of the live Google Sheet. Tabs `R011` through `R036`
   carry populated `Correct? (Y/N)`/comment cells (a mix of `Y`/`N`,
   `CORRECT`/`FALSE POSITIVE`/`TRUE VIOLATION` spellings, and free-text
   rationale); `R011-R015 Follow-up` is a separate, later round with its
   own distinct cases; tabs beyond `R036` and `R055` were still blank in
   this snapshot -- honestly represented here as *not migrated*, not
   fabricated (see "What is still not migrated" below). `R019` was blank
   in this same snapshot but was populated in the live sheet by
   2026-09-04 (three days after the export) and migrated separately on
   2026-09-08 by checking the live sheet directly -- see "Correction 2:
   R019" above.

**The 72 `Rxxx_Ester_Auditor_Feedback.xlsx` review packages under
`docs/evaluation/ester_feedback/` remain, as originally found, sources
with zero recoverable verdicts** -- verified programmatically, not
assumed: every package's `Correct? (Y/N)` and `Notes` columns are blank
across all 504 rows (72 packages × 7 documents) -- `scan_xlsx_packages()`
confirms this on every run. These are outgoing packages (sent for
review), never returned, and this is the reason the first migration pass
undercounted: it treated "these are blank" as "no case-level authority
exists" instead of going to look for the live sheet the review actually
happened in. A row reading `"No current auditor Rxxx finding."` is a
statement about what was sent, never a verdict -- the importer never
treats it as one.

`docs/evaluation/ester_feedback/live_sheet_pending_content.json` is the
same story in a different format: a snapshot of the *questions sent*
(document + "possible violation" text), not answers. Not imported for the
same reason.

## Three importers, three source shapes

- **`importers/authority_matrix.py`** -- parses the JSON matrix
  mechanically. Each rule with `ester_decision_exists` in `{YES,
  ANALOGOUS}` becomes a `Resolution` with `policy_reference =
  "{public_rule}@{generated_date}"` and `case_id=None` (there is no case
  to attach it to). `ANALOGOUS` (inferred from a repeated, structurally
  similar Ester judgment on another rule) is recorded with that weaker
  provenance in the resolution text, never silently promoted to the same
  confidence as an explicit `YES`. `NO` rows are skipped -- 49 of the 85
  rules carry no decision to migrate, and none was invented.
- **`importers/xlsx_packages.py`** -- generic, reusable `.xlsx` reader
  that *would* pick up a filled-in `Correct?`/`Notes` pair if one ever
  appears; currently finds none, as above. Kept rather than deleted so a
  future returned package needs no code change to be picked up.
- **`importers/known_cases.py`** + **`importers/case_migration.py`** --
  the real case-level history. `known_cases.py` is a curated, reviewable
  Python table, **hand-transcribed** from the cited `docs/status/*.md`
  files and the populated live-sheet export, not machine-parsed (neither
  source has a structure safe to parse mechanically without a human
  transcribing the verdict/rationale text). Every entry cites its source
  document/export and states only what that source actually says.
  `case_migration.py` turns each entry into a `ReviewCase` (fingerprinted
  from the entry's own recorded page/issue-type/structural facts, **never
  re-derived from a fresh run** -- these are the facts as originally
  documented) plus an `Adjudication` and two `HistoryEvent`s, resolving
  the document short name to a real `ThesisVersion` via
  `importers/thesis_registry.py`.

Both of the first pass's two "not migrated" cases (R024's Praneeth
hyphenated-fragment case, R035's Anthony landscape-geometry case) turned
out to have concrete physical pages once checked against the live sheet
export and are now real case-level entries (R024/Praneeth page 14,
R035/Anthony page 60) -- see "What is still not migrated" below for what
genuinely has no page/verdict recorded anywhere yet.

## What is still not migrated (and why that's the honest answer)

- **R019**: migrated 2026-09-08 -- see "Correction 2: R019" above and
  `docs/status/r019_ester_sheet_authority_20260908.md`. (This bullet
  originally reported R019 as unrepresented; that was true only of the
  2026-09-01 export, not the live sheet.)
- **R055**: the sheet tab itself is still blank (no case-level finding
  for any document, confirmed against the 2026-09-08 live export) -- but
  an explicit rule-wide policy was reported by email on 2026-09-04 and is
  now migrated as policy guidance (not a case). See "Correction 3: R055
  email policy" above and `docs/status/r055_ester_email_policy_20260904.md`.
  (This bullet originally reported R055 as carrying no authority at all;
  that was true only of the sheet, not of Ester's authority as a whole.)
- **Everything past `R036`** in the live-sheet export was blank in the
  2026-09-01 snapshot. Not migrated for the same reason as R019/R055: no
  populated source exists yet on this machine.

A future pass with a newer sheet export can extend `known_cases.py`
further without any schema change -- the importer and fingerprinting
design were built generic for exactly this.

## Thesis identity and version matching

`importers/thesis_registry.py` reuses the exact corpus list already
established in `scripts/ester_batch/lib.py` (`DOCS`) and the private-data
convention (`data/evaluation/private/`), computing a real SHA-256 of each
current PDF. Elbert is excluded, matching existing project convention.

Every migrated case in this pass resolved to the corpus's **current** PDF
version -- no `VERSION_UNRESOLVED` case exists, because every one of the
44 curated cases' recorded page/issue-type facts were independently
re-verified against the current file before being added to
`known_cases.py` (see each entry's cited source; every case was confirmed
present/absent exactly as expected -- or, for the five genuine
regressions, confirmed still present with an exact-value cross-check, not
just a page match -- during this migration's own development). If a
corpus PDF is ever replaced with a
different version, the deterministic `ThesisVersion` id changes (new
SHA-256) and any case migrated against the old version's id would need
re-verification before being trusted against the new one -- this is a
real, load-bearing property, not yet exercised in production because
today's corpus hasn't changed since the reviewed cases were written.

## Ground-truth replay: matching granularity

`ground_truth.py` checks "is there a current finding equivalent to this
adjudicated case" using **`(thesis_version_id, internal_rule_id,
issue_type, physical_page)`**, not the ledger's full fingerprint
(`structural_location`/`volatile_detail`). This is a deliberate, documented
simplification: a live auditor run has no way to reconstruct the same
hand-written `structural_location` string a migrated historical case
used, so requiring an exact fingerprint match would report every
migrated case as absent even when it's still there. The coarser
granularity is verified accurate for every case in the current ledger (no
two migrated cases share rule+issue_type+page on the same thesis
version) — but a future rule whose migrated cases *do* collide on one
page would need this tightened; watch for it rather than assuming it
will never happen.

**Two such collisions were found and fixed during this migration pass,**
not hypothetically -- a first, crude verification script that checked
only `(rule_id, page)` flagged several candidate cases as "regressions"
that turned out to be false alarms on closer inspection:

- **`P011`** (`margin_boundary_violation`): a reviewed Praneeth
  right-margin false positive at page 56 (3.0pt overflow, methods-section
  body text) and an unrelated, never-reviewed bottom-margin finding at the
  same page (13.8pt overflow, different text) would otherwise have
  matched as "the same case".
- **`P024`** (`list_of_tables_title_case` / `list_of_figures_sentence_case`):
  these fire once per flagged word on the same List of Tables/Figures
  page. A reviewed Praneeth false positive about the word `'casein'` at
  page 14 and an unrelated, still-present finding about a different word
  (`'peptide'`) on the same page would otherwise have matched.

Both are fixed generically by `ground_truth.qualify_issue_type(rule_id,
issue_type, details, message)`, which appends a rule-specific
discriminator (`P011`: the `side` details field; `P024`: the single-quoted
word extracted from the message) before either a migrated case's
`issue_type` or a live run's `CurrentFinding.issue_type` ever reaches the
matching logic in `replay_ledger`. Both `known_cases.py` (at authoring
time) and `cli.py`'s `run_current_auditor_and_record` (at replay time)
must call it the same way, or matching silently degrades back to the
coarser, collision-prone form -- see the regression tests in
`test_ground_truth.py` (`test_qualify_issue_type_p011_discriminates_by_side`,
`test_qualify_issue_type_p024_discriminates_by_flagged_word`,
`test_p011_side_discrimination_prevents_false_regression_in_replay`) for
the specific collision each one guards against.

## Replay failures: root-caused, not fixed

Five cases across three rules replay as genuine `FP_REGRESSION`s against
the current codebase. Each was investigated individually -- checked at
message/measured-value granularity, not just rule+page -- to rule out a
migration or matching bug before being accepted as a real, currently
unresolved detector issue. Per the task constraint this migration was
scoped under, **no detector code was changed to make any of these zero**;
they are reported here for a separate correction task.

| Case | Root cause found |
|---|---|
| `P027`/Praneeth p69 | The reviewed finding (`level4_sentence_case_or_punctuation_issue`, "period is there but the auditor does not recognize that this title ends on the second line") is still produced verbatim by the current heading-punctuation check -- the multi-line-heading period detection Ester described as broken has not been fixed. A second, unrelated `level4_sentence_case_issue` about "Cytochrome C" capitalization also fires on the same page (a real, never-reviewed possible issue) but does not affect this determination -- the two are distinguished by `issue_type`. |
| `P030`/Anthony p11 | Reviewed as false ("the `(Continued)` text is there"); the current `missing_continued_heading` check still fires at the same page against the same recorded `expected_heading` value (`'TABLE OF CONTENTS (Continued)'`), confirmed by exact-value cross-check against the original review, not just a page match. |
| `P030`/Praneeth p12 | Same root cause and same confirmation method as Anthony's case above. |
| `P036`/Anthony p12 | Reviewed as false; the current `toc_inter_entry_spacing_too_tight` check still fires at the same page with the exact same measured `gap_ratio=1.08` recorded in the original review. |
| `P036`/Praneeth p11 | Same root cause and same confirmation method as Anthony's case above (`gap_ratio=1.19`). |

By contrast, the bulk `(rule_id, page)`-only check's other flagged
candidates (`P011`/Praneeth p56, `P024`/Praneeth p14) were **not** real
regressions once checked in detail -- see the `qualify_issue_type`
discussion above; this is exactly the kind of false alarm careful,
per-case verification is meant to catch before it gets reported as a
detector bug that doesn't exist.

`P028`/Patrick p13 is intentionally excluded from both the regression
count and the clean count: Ester's comment ("CORRECT, but... the real
error is not the page number but the absence of the header 'CHAPTER 1'")
is a nuanced case-adjudication-plus-root-cause record, not a simple
instruction to keep `P028` reporting this page. The actual defect's
responsibility sits with `P085` (already migrated separately as a
`TRUE_VIOLATION`, confirmed still detected -- see the table below), so
this case is recorded with verdict `NEEDS_CLARIFICATION` rather than
forced into either `TRUE_VIOLATION` or `FALSE_POSITIVE` for `P028`
itself. It is counted in `UNRESOLVED_POLICY_CASES`, not in
`ESTER_REVIEWED_FP_TOTAL`/`ESTER_REVIEWED_TP_TOTAL`.

Verdict handling:

| Verdict | Expected current state | FAIL means |
|---|---|---|
| `FALSE_POSITIVE`, `ACCEPTABLE` | equivalent finding absent | `FP_REGRESSION` (still reported) |
| `TRUE_VIOLATION` | equivalent finding present | `TP_REGRESSION` (no longer reported) |
| `NEEDS_CLARIFICATION`, `UNRESOLVED`, `NOT_REVIEWED` | -- | excluded from PASS/FAIL, counted in `UNRESOLVED_POLICY_CASES` |
| `POLICY_GUIDANCE` | -- | never a case-level verdict in this design (see the data model doc); excluded the same way if one is ever created |

Each replay run writes a `RegressionResult` (PASS/FAIL/NOT_APPLICABLE)
and a `HistoryEvent` per case into the ledger -- replay results are
permanent, reviewable history, not a one-off terminal printout.

## The new-review gate

`new_review_gate.check_new_review_gate(report)` is fail-closed: it blocks
(`allowed=False`) whenever `ESTER_FP_REMAINING > 0` or
`ESTER_TP_MISSING > 0`, unless called with both `override=True` and a
non-empty `override_reason` (an unexplained override is rejected the same
as no override). **No new-review-round generator exists yet** -- this
phase only ships the predicate a future generator is required to consult
first; see `docs/evaluation/ESTER_REVIEW_DATA_MODEL.md`'s "what this
enables next" for what's still deferred.

## Running it yourself

```
PYTHONPATH=src python -m njit_auditor.review_ledger.cli migrate   # full import + replay
PYTHONPATH=src python -m njit_auditor.review_ledger.cli replay    # replay only, against the existing ledger
```

Both require the real private corpus at `data/evaluation/private/` (not
tracked; see `docs/status/CURRENT_STATUS.md`) and write to
`data/evaluation/private/ester_review_ledger/` (gitignored, covered by the
existing `data/evaluation/private/` entry -- no `.gitignore` change was
needed). Neither ever prints dissertation body text -- findings are
summarized structurally (rule, issue type, page) only.

**PyMuPDF version note (found 2026-09-08):** the editable install can
silently resolve to a stale sibling worktree's `njit_auditor` package
(`pip show njit-thesis-auditor` reveals the `Location`/egg-link target) if
`pip install -e ".[dev]"` was last run from a different checkout, and that
stale install was pinned to `pymupdf==1.24.6` -- below this project's own
`pyproject.toml` floor of `pymupdf>=1.25.0`. Re-running
`pip install -e ".[dev]"` from *this* checkout fixes both problems at
once (correct source tree, `pymupdf` upgraded to a `>=1.25.0` release).
Always confirm with `python -c "import njit_auditor; print(njit_auditor.__file__)"`
before trusting a real-corpus run's output.

**Idempotency, verified**: re-running `migrate` twice against the same
ledger creates zero additional `Thesis`/`ThesisVersion`/`ReviewCase`/
`Adjudication`/`Resolution` rows (all deduplicated by deterministic id or,
for the authority matrix, by `policy_reference`) -- the second run's
`cases_created`/`adjudications_created`/`resolutions_created` are all
`0`, with the corresponding `*_already_present` counts matching (44/44,
44/44, 36 already-present respectively). Event- style rows (`AuditorRun`,
`RegressionResult`, the `HistoryEvent`s tied to them) correctly grow with
each run -- each execution is a genuinely new event, not a duplicate of
the same one (verified: `auditor_runs.jsonl` 7→14 lines,
`regression_results.jsonl` 43→86, `review_rounds.jsonl` 1→2 across two
consecutive real runs, while every identity-bearing file's line count
stayed fixed).

Re-verified 2026-09-08 after the R019 correction (known cases now 50, not
44): two more consecutive real runs showed `cases_created`/
`adjudications_created` go `6→0` (the 6 new R019 cases, then none) with
`*_already_present` correspondingly `44→50`, `review_cases.jsonl` and
`adjudications.jsonl` both staying fixed at 50 across the second run,
while `auditor_runs.jsonl` (14→28), `regression_results.jsonl` (86→184),
and `review_rounds.jsonl` (2→4) grew as expected -- the same idempotency
property holds after this correction as before it.

Re-verified again after the R055 email-policy correction: two more
consecutive real runs showed `policies_created`/`policies_already_present`
go `1→0`/`0→1`, `resolutions.jsonl` staying fixed at 37 across the second
run (identical to `review_cases.jsonl`/`adjudications.jsonl` staying fixed
at 50), while `auditor_runs.jsonl` (28→42→56), `regression_results.jsonl`
(184→282→380), and `review_rounds.jsonl` (4→6→8) kept growing as
expected. Same property, third time.

One practical note for anyone re-running a *requalified* case (i.e. one
whose `issue_type` in `known_cases.py` changes, as several did in the
correction above when `qualify_issue_type` was introduced): case identity
is fingerprinted from `issue_type` among other fields, so changing it
changes the case's deterministic id. Because the private ledger's own
JSONL files are gitignored, untracked, local working data -- never
committed, never shared -- this is not an append-only-history concern;
the corrected pass simply deleted and regenerated
`data/evaluation/private/ester_review_ledger/` from a clean state rather
than leaving the old, now-orphaned unqualified-`issue_type` cases mixed in
with the new qualified ones. This is not available or appropriate for
anything actually committed to git (the ledger design's append-only
invariant is about the ledger's own row semantics, not about local
regeneration of gitignored derived data).

### Actual result as of this corrective migration pass

```
Authority matrix: 85 rules, 36 Resolutions created (25 explicit + 11 analogous), 49 skipped (no decision)
Known cases: 50/50 migrated, 0 version_unresolved
XLSX packages: 72 scanned, 504 rows read, 0 with a verdict
Known policies (email/manual-record): 1/1 migrated (R055)

ESTER_REVIEWED_FP_TOTAL = 46
ESTER_FP_REMAINING = 5
ESTER_REVIEWED_TP_TOTAL = 3
ESTER_TP_MISSING = 0
UNRESOLVED_POLICY_CASES = 1
POLICY_GUIDANCE_TOTAL = 37   (36 from the authority matrix + 1 email-sourced R055 policy)

RULE | FP_TOTAL | FP_REGRESSIONS | TP_TOTAL | TP_REGRESSIONS | UNRESOLVED | STATUS
P011 | 8 | 0 | 1 | 0 | 0 | CLEAN
P015 | 4 | 0 | 0 | 0 | 0 | CLEAN
P016 | 3 | 0 | 0 | 0 | 0 | CLEAN
P017 | 3 | 0 | 0 | 0 | 0 | CLEAN
P018 | 2 | 0 | 0 | 0 | 0 | CLEAN
P019 | 6 | 0 | 0 | 0 | 0 | CLEAN
P020 | 3 | 0 | 1 | 0 | 0 | CLEAN
P023 | 4 | 0 | 0 | 0 | 0 | CLEAN
P024 | 2 | 0 | 0 | 0 | 0 | CLEAN
P026 | 1 | 0 | 0 | 0 | 0 | CLEAN
P027 | 1 | 1 | 0 | 0 | 0 | REGRESSION
P028 | 1 | 0 | 0 | 0 | 1 | PARTIAL
P030 | 2 | 2 | 0 | 0 | 0 | REGRESSION
P033 | 1 | 0 | 0 | 0 | 0 | CLEAN
P035 | 3 | 0 | 0 | 0 | 0 | CLEAN
P036 | 2 | 2 | 0 | 0 | 0 | REGRESSION
P085 | 0 | 0 | 1 | 0 | 0 | CLEAN

New-review gate: allowed=False
reason=blocked: ESTER_FP_REMAINING=5, ESTER_TP_MISSING=0
(pass override=True and a non-empty override_reason to bypass explicitly)
```

This was computed, not assumed going in, and it is **not** the clean
`FP_REMAINING=0` result the first (incomplete) pass reported. All 3
reviewed true violations (`P011`/Patrick p88, `P020`/Praneeth p20,
`P085`/Patrick p13) still fire correctly. 41 of the 46 reviewed false
positives correctly stay suppressed, including all 6 of R019's. The
remaining 5 are the real, individually-investigated regressions in
"Replay failures: root-caused, not fixed" above (`P027` ×1, `P030` ×2,
`P036` ×2) -- pre-existing (confirmed unchanged by the R019 addition; see
"Correction 2" above), not migration artifacts, not fixed as part of this
task, and the new-review gate correctly reports `allowed=False` as a
direct, honest consequence.

## Invariant

**No new Ester review round should be generated while a previously
adjudicated false positive is being reported or a previously adjudicated
true violation is missing.** `check_new_review_gate` is the enforcement
point a future round-generator must call; this phase does not yet contain
that generator. As of this corrective pass, the gate correctly blocks
(`allowed=False`) because five such false positives are, in fact, still
being reported -- see "Replay failures" above for what a future
correction task needs to fix before the gate can open again without an
explicit override.
