# Ester Review Data Model

Foundation phase (2026-09-07). Code: `src/njit_auditor/review_ledger/`.
Tests: `tests/test_review_ledger/`.

## Purpose

Ester's review feedback is currently scattered across dated status docs
under `docs/status/` and per-rule `.xlsx`/`.pdf` packages under
`docs/evaluation/ester_feedback/`. Both are real, valuable artifacts, but
neither is a durable *source of truth* that code can query: there is no
way to ask "has this exact case already been adjudicated?" or "does the
auditor still agree with every reviewed false positive?" without a human
re-reading prose.

This module is that durable source of truth: a small, explicit domain
model plus an append-only, privacy-safe, on-disk store. It exists so that
three later phases (not built yet -- see "What this enables next" below)
can be built *on* it instead of *around* another ad hoc spreadsheet:

1. Migrating historical Ester feedback into it.
2. A ground-truth replay gate that checks current auditor behavior against
   every stored adjudication.
3. Projecting it into a human-friendly Excel/Google Sheets workbook.

## Why the workbook is not the source of truth

A workbook (or a Google Sheet) is what a human reviewer reads and
annotates. It is excellent for that and bad for almost everything else:
it has no enforced schema, nothing stops two rows from silently
describing "the same" violation differently, and there is no way to
prove an old adjudication was preserved rather than overwritten when the
sheet was regenerated. Treating it as canonical means every regeneration
is a chance to lose history.

The ledger inverts this: the JSONL files under a ledger root are
canonical; a workbook (when phase 3 builds one) is a *generated,
disposable projection* of the ledger, the same way an HTML report is a
projection of `AuditFinding`s. Regenerating the workbook must never be
able to lose data, because the workbook is not where the data lives.

## Entities

See `src/njit_auditor/review_ledger/models.py` for exact fields; this is
the relationship summary.

```
Thesis 1---* ThesisVersion 1---* AuditorRun
                    |                  |
                    |                  *
                    |             ReviewCase *---1 ReviewRound
                    |                  |
                    |                  *---* Adjudication (linear chain via supersedes_adjudication_id)
                    |                  |
                    |                  *---* Resolution (or policy_reference, no case)
                    |                  |
                    |                  *---* RegressionResult
                    |
                    (any entity) *---* HistoryEvent
```

- **Thesis** -- one logical dissertation, independent of which PDF was
  last submitted. Identity does not change as the student revises.
- **ThesisVersion** -- one specific submitted PDF, identified by its
  content hash. A thesis has many versions over time; exactly one is
  `current` at once (by convention, not an enforced invariant yet).
- **AuditorRun** -- one execution of the auditor against one
  `ThesisVersion`, tagged with the exact `code_sha` that produced it. Two
  runs of identical code against identical input are still two distinct
  `AuditorRun`s -- re-running is not free with respect to provenance.
- **ReviewRound** -- one prepared batch sent for human review (what
  today's `scripts/ester_batch/build_rule_package.py` produces one rule
  at a time, generalized across rules and given a stable id).
- **ReviewCase** -- one specific candidate violation prepared for review,
  tied to the exact run and thesis version that produced it, carrying
  both `internal_rule_id` (`Pxxx`/`PxxxX`) and `public_rule_id`
  (`Rxxx`/`RxxxX`, via `njit_auditor.report_outputs.public_display_rule_id`
  -- see "Public vs internal rule ids" below), plus its fingerprint (see
  below).
- **Adjudication** -- one human verdict on one `ReviewCase`. See
  "Append-only history" below for why there can be more than one per case.
- **Resolution** -- the engineering-side record of what was done about a
  case (or a whole policy, via `policy_reference`, when the fix wasn't
  case-specific -- e.g. R055's Table/Figure-prefix rule).
- **RegressionResult** -- one replay: "as of `code_sha`, does the auditor's
  actual behavior still match this case's expected verdict?"
- **HistoryEvent** -- an append-only log entry for any lifecycle
  transition on any of the above. Not required for every mutation (the
  JSONL append itself is already a permanent record), but the place to
  record *why* something changed when that context matters (e.g. "case
  resolved because of commit abc123, superseding a prior WONT_FIX").

## ID grammar

See `src/njit_auditor/review_ledger/identifiers.py` for the authoritative
implementation and docstrings. Summary:

| ID | Format | Deterministic? | Basis |
|---|---|---|---|
| Thesis | `TH-<hash12>` | Yes | hash of a caller-supplied stable alias |
| ThesisVersion | `TV-<hash12>` | Yes | hash of (thesis_id, content sha256) |
| AuditorRun | `RUN-<codesha8>-<ts>-<rand>` | No (unique per execution) | code sha + timestamp + randomness |
| ReviewRound | `ER-YYYYMMDD-NN` | Human-assigned, sortable | caller supplies the sequence (see `next_review_round_sequence`) |
| ReviewCase | `CASE-<hash12>` | Yes | hash of (thesis_version_id, internal_rule_id, fingerprint *equivalence key*) |
| Adjudication | `ADJ-<ts>-<rand>` | No (unique per judgment) | timestamp + randomness |
| Resolution | `RES-<ts>-<rand>` | No | timestamp + randomness |
| RegressionResult | `REG-<ts>-<rand>` | No | timestamp + randomness |
| HistoryEvent | `EVT-<ts-microsecond>-<rand>` | No | timestamp + randomness |

Two design choices worth calling out:

- **`ReviewCase` id is deterministic from the fingerprint's equivalence
  key, not the exact fingerprint.** This is what lets a case keep the
  same id across reruns even when a minor, non-structural detail (a
  slightly shifted bbox, a rounded measurement crossing a bucket) changes
  -- see "Case fingerprint" below. Physical page alone is never the whole
  identity; it is one component folded into the fingerprint along with
  the rule, issue type, and a caller-supplied structural location.
- **`Thesis` id never stores the alias it was derived from.** Only its
  SHA-256 hash appears in the id. The alias itself (e.g. an existing
  corpus short name such as `"praneeth"` -- see `DOCS` in
  `scripts/ester_batch/lib.py`) is the caller's problem to keep wherever
  it already lives; this module does not require or store it.

## Case fingerprint and equivalence

See `src/njit_auditor/review_ledger/fingerprint.py` for the implementation
and full docstring; summary of the semantics:

- Inputs are always structural/numeric: thesis-version id, internal rule
  id, issue type, physical page, a caller-built `structural_location`
  string (e.g. `"table_of_contents:entry_index=3"` -- never quoted
  dissertation text), and an optional `volatile_detail` string for
  fine-grained, expected-to-drift attributes (e.g. a rounded measurement).
- `equivalence_key` hashes everything **except** `volatile_detail`.
- `exact_fingerprint` hashes everything **including** `volatile_detail`.
- Classification (`classify_against_known`) checks exact fingerprints
  first (**SAME** case, byte-identical rerun), then equivalence keys
  (**EQUIVALENT** case -- same underlying violation, a detail drifted),
  and falls back to **NEW** (nothing matches: different page, different
  rule, different issue type, or a different `structural_location` --
  which is exactly what keeps two distinct violations on the same page
  from colliding into one case).

Ground-truth replay also has an additive, versioned `CaseLocator` registry
derived from curated historical-case records. It keys privacy-safe PDF
coordinates, structural role, and provenance to an **existing** case ID.
Live replay retains bbox origin coordinates; it compares locations with a
bounded tolerance and requires a unique one-to-one match within the coarse
thesis-version/rule/issue/page group. The locator is not part of either
fingerprint and does not rewrite historical JSONL. When identity is
ambiguous, replay records an explicit non-scored result and the new-review
gate blocks; this is separate from policy clarification and rule regression.

This is the mechanism that satisfies "a tiny bbox or wording change must
not turn the same reviewed case into a new case" while still keeping
"materially different violations on the same page" distinguishable: the
former only ever touches `volatile_detail`; the latter must differ in
`structural_location`, which the caller is responsible for making granular
enough (e.g. including an entry index or figure/table number).

## Confidence normalization

`src/njit_auditor/review_ledger/confidence.py` maps a detector's raw
confidence string to `ConfidenceLevel.{LOW,MEDIUM,HIGH,UNKNOWN}`, mirroring
(but not importing -- `scripts/` is standalone tooling, not an installed
dependency) the rank/parsing pattern in `scripts/ester_batch/lib.py`'s
`finding_confidence()`. This never changes a detector's own confidence
calculation; it only normalizes an already-computed value for ledger
storage and comparison. Lowest-confidence *selection* logic (a later
phase) is expected to build on `is_weaker_or_equal`.

## Public vs internal rule ids

`ReviewCase` stores both `internal_rule_id` (the detector's own `Pxxx` /
lettered atomic sub-rule `PxxxX`, e.g. `P018D`) and `public_rule_id` (the
`Rxxx`/`RxxxX` form Ester and students see). The latter is always produced
by calling the existing, single canonical helper --
`njit_auditor.report_outputs.public_display_rule_id` -- not a
reimplementation; `tests/test_review_ledger/fixtures.py` demonstrates this
directly, including the atomic-suffix case (`P018D` -> `R018D`).

## Append-only history

Three invariants, enforced by `EsterReviewLedger`
(`src/njit_auditor/review_ledger/store.py`), not just documented:

1. **No collection has an update or delete method.** Only `add_*` and
   `record_history_event`. Appending under an id that already exists --
   even with byte-identical content -- raises `LedgerValidationError`.
2. **A case's adjudication history is a linear, non-overwriting chain.**
   Adding a second `Adjudication` for a case that already has one is
   rejected unless the new one's `supersedes_adjudication_id` names the
   case's current (not-already-superseded) adjudication. The earlier row
   is never edited or removed -- `current_adjudication_for_case` walks the
   chain to find the tip; every prior link stays on disk.
3. **No orphan references.** A `ReviewCase` must name an existing
   `ReviewRound`, `AuditorRun`, and `ThesisVersion`; an `Adjudication` /
   `Resolution` / `RegressionResult` must name an existing `ReviewCase`
   (`Resolution` may instead name a `policy_reference` with no case);
   `ThesisVersion.thesis_id` and `AuditorRun.thesis_version_id` must exist;
   `HistoryEvent.entity_id` must exist for its declared `entity_type`.
   All checked before the append happens, not after.

`docs/status/CURRENT_STATUS.md`'s existing convention of never overwriting
matrix history in place (`ester_authority_matrix_20260902.md` stays, a new
dated file supersedes it, the pointer file is updated) is the same
principle this module makes structurally enforced instead of a naming
convention.

## Storage format

One `.jsonl` file per entity type under a ledger root directory (plus a
`_ledger_meta.json` recording `schema_version`), one canonical
(sort-keys, UTF-8) JSON object per line. Chosen over alternatives for
this phase:

- **Human-inspectable and PR-reviewable**: `git diff` on a `.jsonl` file
  is a legible, line-level audit trail during this foundation phase --
  exactly what the append-only property should look like in a diff.
- **No new service dependency**: a SQLite file was considered and
  rejected for now -- nothing here needs transactions across multiple
  concurrent writers, joins beyond what `EsterReviewLedger`'s in-memory
  indexes already do in a few lines, or a query language. If a future
  phase needs those, JSONL migrates into SQLite trivially (it is already
  one row of structured, schema'd data per line); the reverse (unwinding
  a database into a reviewable diff format) is not the direction this
  project should paint itself into first.
- **Trivial to project into or import from `.xlsx`** later: each JSONL
  file is already "one row per line, one column per key" -- a workbook
  generator (phase 3, not built yet) is a thin reader over this; a
  migration importer (phase 1 of what's next, not built yet) is a thin
  writer into it.

`schema_version` (currently `1`) is checked on load; a mismatch raises
rather than silently reading a shape the code doesn't understand. Bumping
it is expected as the model evolves -- this phase deliberately did not try
to guess the final shape and lock it prematurely.

## Tracked vs. private data

Nothing under `src/njit_auditor/review_ledger/` or
`tests/test_review_ledger/` requires or accepts real dissertation content
-- the tests use only invented synthetic data (`fixtures.py`).

An actual private ledger, once real cases start flowing through this
module (a later phase), belongs under `data/evaluation/private/` --
already `.gitignore`d recursively (see `.gitignore`), the repo's
established location for anything derived from real dissertations, e.g.
`data/evaluation/private/ester_review_ledger/`. No `.gitignore` change was
needed for this phase since that path is already covered; no such
directory was created either, since there is no real data yet to put in
it.

## Reviewer workbook format

Ester's stated preference (2026-10-05) for every review workbook sent to
her:

- The spreadsheet filename starts with the date (for example
  `2026-10-05_R024E_NJIT_Thesis_Auditor_Review.xlsx`).
- One tab per rule.
- When a rule has split public codes, use the specific code (R024D, R024E,
  R018D, ...), never the ambiguous parent (R024).
- Columns: `DOCUMENT`, the possible-violation description, then
  `Question 1`, then `Comment` immediately after the question. Never label
  a column "Ester's questions" or "Ester Question 1".
- Wrap text in every cell, top-aligned, with readable column widths, so
  each entry reads as a block.
- Keep the layout tidy and identical from round to round so it can be
  reused.
- The evidence PDF stays directly linked from the rule's tab.

`scripts/ester_batch/build_rule_package.py` writes this layout for future
packages. A current-case row has a question and a blank `Comment` cell;
`No new review needed.` rows leave both cells blank. The rule tab links to
its highlighted evidence PDF. Batch manifests record the workbook schema and
review date; archived workbooks retain their original filenames and headers.

## What this enables next (not built in this phase)

Explicitly out of scope here, listed so it's clear what "foundation"
means and does not mean:

- Migrating historical Ester feedback (the dated status docs and
  `docs/evaluation/ester_feedback/*.xlsx`) into `EsterReviewLedger` rows.
- A ground-truth replay gate that walks every stored `Adjudication` and
  checks it against current detector output (`ESTER_FP_REMAINING`,
  `ESTER_TP_MISSING`, etc., computed from the ledger instead of manually,
  as this session's earlier reconciliation work had to do).
- Generating a new review round: running the auditor, fingerprinting
  findings, filtering out cases already adjudicated `FALSE_POSITIVE`
  (must stay absent) while leaving `TRUE_VIOLATION` cases alone (must
  stay present), and selecting only the lowest-confidence genuinely new
  case per rule/thesis-version.
- The `.xlsx` workbook generator (Dashboard / Cases / Review Rounds /
  Auditor Runs / Feedback History / Next Review / per-rule tabs).
- Round-to-round comparison reporting.
- Blocking new-round generation on `ESTER_FP_REMAINING != 0` or
  `ESTER_TP_MISSING != 0`.

Each of these reads and writes `EsterReviewLedger`; none of them required
changing anything in this phase to be buildable next.
