# Ester Feedback Migration and Ground-Truth Replay

Phase 2 of the review-ledger work (2026-09-07). Builds on
`docs/evaluation/ESTER_REVIEW_DATA_MODEL.md` (read that first). Code:
`src/njit_auditor/review_ledger/importers/`, `ground_truth.py`,
`new_review_gate.py`, `cli.py`. Tests: `tests/test_review_ledger/`
(synthetic) plus a real run against the private ledger (not tracked, not
reproducible from CI -- see "Running it yourself" below).

## What actually exists to migrate

Before writing any importer, every plausible source under
`docs/evaluation/ester_feedback/` and `docs/status/` was inventoried. Two
real, structurally different kinds of authority exist, and nothing else:

1. **Rule-level policy** -- `docs/status/ester_authority_matrix_20260902.json`,
   a dated snapshot recording, per public rule (`R001`-`R085`), whether an
   explicit Ester decision existed as of 2026-09-02, its text, and its
   evidence source. This has no per-document, per-page granularity.
2. **Case-level history** -- exists only as prose in dated
   `docs/status/*.md` files (e.g.
   `p011_r011_ester_9_2pt_boundary_resolution_20260831.md`,
   `r018_r024_ester_sheet_authority_20260907.md`,
   `r035_praneeth_text_fallback_fix_20260907.md`,
   `patrick_chapter1_rule_gap_20260902.md`). No structured export of these
   exists.

**The 72 `Rxxx_Ester_Auditor_Feedback.xlsx` review packages contain zero
recoverable verdicts.** This was verified programmatically, not assumed:
every package's `Correct? (Y/N)` and `Notes` columns are blank across all
504 rows (72 packages × 7 documents) -- `scan_xlsx_packages()` (Phase 2's
generic XLSX importer) confirms this on every run. These are outgoing
packages (sent for review), not returned ones. A row reading
`"No current auditor Rxxx finding."` is a statement about what was sent,
never a verdict -- the importer never treats it as one.

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
  files, not machine-parsed (that prose has no consistent enough
  structure to parse safely). Every entry cites its source document and
  states only what that document actually says. Two real, well-documented
  historical decisions were deliberately **not** given a case-level entry
  (R024's Praneeth hyphenated-fragment case, R035's Anthony
  landscape-geometry case) because neither is confidently re-locatable to
  one specific current page -- see "What was not migrated" below.
  `case_migration.py` turns each entry into a `ReviewCase` (fingerprinted
  from the entry's own recorded page/issue-type/structural facts, **never
  re-derived from a fresh run** -- these are the facts as originally
  documented) plus an `Adjudication` and two `HistoryEvent`s, resolving
  the document short name to a real `ThesisVersion` via
  `importers/thesis_registry.py`.

## What was not migrated (and why that's the honest answer)

- **R024, Praneeth's hyphenated-fragment case**: real, resolved (the
  `skip_hyphenated_fragments` fix), but her current draft's List of
  Tables no longer contains a hyphen-adjacent word matching the reviewed
  shape at all (confirmed by direct search, not assumed) -- there is no
  page to attach a case to without guessing. Migrated as policy only (via
  the authority-matrix path once a matrix snapshot records it), not as a
  case.
- **R035, Anthony's landscape-geometry case**: real, resolved (the
  landscape-aware centering-tolerance fix), but no specific page was
  recorded for it in the cited source at the time it was written. Same
  treatment.

Both are true, resolved false positives with real fix commits; neither is
a case-level `ReviewCase` in this pass. A future pass with either a
returned original review package or a more specific status doc can add
them without any schema change.

## Thesis identity and version matching

`importers/thesis_registry.py` reuses the exact corpus list already
established in `scripts/ester_batch/lib.py` (`DOCS`) and the private-data
convention (`data/evaluation/private/`), computing a real SHA-256 of each
current PDF. Elbert is excluded, matching existing project convention.

Every migrated case in this pass resolved to the corpus's **current** PDF
version -- no `VERSION_UNRESOLVED` case exists, because every one of the
eight curated cases' recorded page/issue-type facts were independently
re-verified against the current file before being added to
`known_cases.py` (see each entry's cited source; the R011/R015 cases were
additionally confirmed present/absent exactly as expected during this
migration's own development). If a corpus PDF is ever replaced with a
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

**Idempotency, verified**: re-running `migrate` twice against the same
ledger creates zero additional `Thesis`/`ThesisVersion`/`ReviewCase`/
`Adjudication`/`Resolution` rows (all deduplicated by deterministic id or,
for the authority matrix, by `policy_reference`) -- the second run's
`cases_created`/`adjudications_created`/`resolutions_created` are all
`0`, with the corresponding `*_already_present` counts matching. Event-
style rows (`AuditorRun`, `RegressionResult`, the `HistoryEvent`s tied to
them) correctly grow with each run -- each execution is a genuinely new
event, not a duplicate of the same one.

### Actual result as of this migration pass

```
Authority matrix: 85 rules, 36 Resolutions created (25 explicit + 11 analogous), 49 skipped (no decision)
Known cases: 8/8 migrated, 0 version_unresolved
XLSX packages: 72 scanned, 504 rows read, 0 with a verdict

ESTER_REVIEWED_FP_TOTAL = 6
ESTER_FP_REMAINING = 0
ESTER_REVIEWED_TP_TOTAL = 2
ESTER_TP_MISSING = 0
UNRESOLVED_POLICY_CASES = 0

RULE | FP_TOTAL | FP_REGRESSIONS | TP_TOTAL | TP_REGRESSIONS | STATUS
P011 | 1 | 0 | 1 | 0 | CLEAN
P015 | 1 | 0 | 0 | 0 | CLEAN
P018 | 2 | 0 | 0 | 0 | CLEAN
P024 | 1 | 0 | 0 | 0 | CLEAN
P035 | 1 | 0 | 0 | 0 | CLEAN
P085 | 0 | 0 | 1 | 0 | CLEAN

New-review gate: allowed=True
```

Every one of the 8 migrated cases replayed correctly against the current
codebase: every reviewed false positive stays suppressed, the one
reviewed true violation (R085/Patrick) stays detected. This was computed,
not assumed going in -- the migration code would have reported a nonzero
`ESTER_FP_REMAINING`/`ESTER_TP_MISSING` and this document would say so if
it had.

## Invariant

**No new Ester review round should be generated while a previously
adjudicated false positive is being reported or a previously adjudicated
true violation is missing.** `check_new_review_gate` is the enforcement
point a future round-generator must call; this phase does not yet contain
that generator.
