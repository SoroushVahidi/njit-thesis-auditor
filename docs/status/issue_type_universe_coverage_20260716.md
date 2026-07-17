# Issue-Type Universe Coverage (2026-07-16, follow-up to PR #513)

> **Purpose:** Close the gap between the true set of active runtime
> `(rule_id, issue_type)` pairs (~140-145, per PR #513's manual audit) and
> the subset the static scanner introduced by that PR could mechanically
> discover (72). Architectural/tooling work — no detector, threshold,
> confidence, or rule-ID change.
>
> **Recorded:** 2026-07-16, same-day follow-up to PR #513 (still open,
> unmerged, at `f6f0d79` — this work continues that same branch/PR rather
> than forking a conflicting one).

## Baseline

- Branch: `fix/ester-atomic-presentation-audit`, PR #513, **open, not merged**.
- Starting commit: `f6f0d79e5eddfd3fe9aedfe81833ca67f9d995cf`.
- `ruff check .`: clean. `mypy src`: clean, 110 files. `python -m pytest`:
  **2845 passed**.
- `rule_source_scan.detector_emitted_pairs_by_static_scan()` (as it existed
  in PR #513): **56 raw pairs**; unioned with the catalog's `issue_types`
  field in the ratchet test: **72 pairs**.

## Root causes of the 72-vs-~140 discovery gap

Investigated by running the PR #513 scanner and, for every `AuditFinding(...)`
call site it failed to resolve, reading the actual code to categorize why.
Found five distinct patterns, none of them "truly dynamic" — every one
resolves to a small, closed, developer-authored set of literals if you trace
one or two more hops than the original scanner did:

1. **`details=` built as a local dict-literal variable, not inline**
   (`details: dict[str, str] = {"issue_type": ..., ...}` then
   `AuditFinding(..., details=details)`). The dominant pattern — ~35 call
   sites (P011, P013, P018, P023, P027, P056, P066, P067, and others).
2. **The dict-literal's `"issue_type"` value is itself a function parameter,
   with the real literal(s) only appearing at the function's call site(s)**
   (a `_finding(...)`/`_append_finding(...)`/`_make_finding(...)`-style
   helper). Found in pdf_heading_levels.py (P027), pdf_figure_table_layout.py
   (P035), pdf_lot_lof_column_headers.py (P031),
   pdf_approval_page_committee_blocks.py (P068), and others — sometimes one
   hop, sometimes two (a caller resolves a value from a module dict, then
   passes *that* to a second function, which passes it to a third that
   finally builds the dict).
3. **Module-level "config dict" lookup**, either a direct subscript/`.get()`
   assigned straight to `issue_type` and used as a scalar, or unpacked from a
   tuple value (`issue_type, q_rule = _MAP.get(key)`), sometimes through one
   intermediate variable (`config = _MAP.get(key); issue_type, q = config`).
   Found in pdf_lot_lof_page_number_ordering.py (P057),
   pdf_lot_lof_entry_number_ordering.py (P059),
   pdf_lot_lof_cross_page_entry_ordering.py (P061),
   pdf_toc_cross_page_entry_ordering.py (P062, via `for k, (a,b) in
   MAP.items():`), and pdf_toc_list_entry_spacing.py (P036).
3. **A plain module-level string constant** (`_ISSUE_TYPE = "literal"`) used
   directly, rather than a dict. Found in pdf_toc_cross_page_entry_ordering.py.
4. **The TeX/"source" pipeline (P001–P010) never sets `issue_type` in its own
   `AuditFinding.details` at all** — it is synthesized entirely downstream,
   by `rule_id` alone, in `report_outputs.derive_source_issue_type()`. This
   isn't a gap in the AST scanner's sophistication; it's a structurally
   different, second ground-truth mechanism that needs its own extractor.
5. **An f-string built from a for-loop variable with a finite, statically
   visible domain** (`for level, pattern in [(5, _L5_RE), (4, _L4_RE), ...]:`
   then `issue_type=f"level{level}_sentence_case_issue"`). Found only in
   pdf_heading_levels.py (P027's level-3/4/5 sentence-case issue types).

One true one-off, **not** a repeating pattern: P021's
`abstract_word_count_exceeded` is synthesized inside
`polished_comments.build_polished_comment()` itself, based on the *presence*
of certain detail keys (`word_count`, `limit`), not a literal any detector
ever constructs. Documented as a single named exception
(`KNOWN_NON_DETECTOR_ISSUE_TYPES`), not general machinery.

## Alternatives considered

| # | Approach | Verdict |
|---|---|---|
| 1 | Improve AST scanning for the common patterns above | **Chosen.** Every pattern found in the real codebase is a bounded, provably-terminating, string-literal-provenance resolution — no detector execution, no hand-maintained inventory, works in a fresh clone/CI with zero new runtime dependencies. |
| 2 | Instrument/run detectors against synthetic fixtures, collect emitted issue_types | Rejected: requires constructing a synthetic PDF fixture *for every rule* that reaches *every* issue type, which is exactly the kind of "hand-maintained shadow inventory" (one per rule, needing updates in lockstep with detector changes) the task asked to avoid — and it silently stops being ground truth the moment a fixture fails to trigger a branch, with no static signal that it happened. |
| 3 | Detector-level declarative metadata colocated with each detector (e.g. a `POSSIBLE_ISSUE_TYPES: ClassVar[set[str]]` per rule module) | Rejected for this pass: touches all 68 rule files, is a second source that can independently drift from the real emit sites (the exact failure mode `issue_types` in the JSON catalog already has), and is exactly the kind of "risky broad edit across all detectors" the task explicitly said to avoid. Worth reconsidering as a *future*, opt-in convention for *new* rules only — see recommendation below. |
| 4 | A canonical registry generated from source (e.g. a build step that writes a static list) | Partially chosen: `rule_source_scan.py` *is* generated-from-source in spirit — it's re-derived from the AST on every test run, so it can never go stale the way a checked-in generated file could. Rejected the "write a static list to disk" variant specifically, since that reintroduces a driftable, hand-copy-adjacent artifact. |
| 5 | Hybrid: detectors declare possible issue types; tests verify emitted findings are a *subset* of the declaration | This is effectively what `rule_source_scan.py` + the ratchet test now do, except the "declaration" is the AST-visible literal structure of the code itself (already true today, in every rule file, with zero developer action required) rather than a new explicit declaration developers must remember to add. Chose the zero-new-syntax version. |

The chosen design satisfies every stated principle: one mechanically
verifiable source (the AST of the rule modules themselves); no hand-copied
140-row list; no detector/threshold/confidence/severity/suppression change;
no sample-specific logic (verified: `git diff` of this pass contains zero
references to any student/reviewer name); no dependency on private
dissertation content (reads only `.py` source text); works in a fresh clone
(no network, no generated fixtures); and it fails loudly the moment a new
rule's issue type has no wording coverage, without anyone needing to
remember to update a separate list.

## Exact implementation

`src/njit_auditor/rule_source_scan.py` was rewritten from a single-pass
literal-assignment scanner into a **bounded, same-module, fixed-point
string-literal-provenance resolver**:

- Tracks `(function_name, variable_name) -> set[possible literal values]`,
  monotonically growing across a small, fixed number of iterations (5) —
  guaranteed to terminate, since sets can only grow and the universe of
  literals in one file is finite.
- Resolves, in order of complexity: direct string literals and ternaries →
  module-level dict/constant lookups (subscript, `.get()`, tuple-unpack,
  `for k, (a,b) in D.items():`, one level of intermediate-variable
  indirection) → same-module function-call argument passing (by keyword or
  position, including chains through more than one function) → f-strings
  built from literal text plus slots that each resolve to a finite set
  (Cartesian product of parts) → `details=` arguments that are dict literals,
  local dict-literal variables, wrapper calls that pass a dict literal
  through, or callee functions that build-and-return a dict literal
  internally.
- **Never crosses a module boundary** — not needed by any real pattern in
  this codebase, and keeping the scope to "one file at a time" is what keeps
  the analysis simple enough to reason about and cheap enough to re-run on
  every test invocation.
- Whatever it still cannot resolve is simply omitted — the design is
  deliberately a *safe superset*, never a guess.

A second, independent extractor, `source_pipeline_issue_type_pairs()`,
statically parses `report_outputs.derive_source_issue_type()`'s literal
`if rule_id == "P0xx": return "..."` chain — the TeX pipeline's separate
ground-truth mechanism.

`full_active_issue_type_universe()` unions both extractors with the one
documented non-detector exception (P021).

`tests/test_rule_registry_consistency.py`'s wording-coverage ratchet now
consumes `full_active_issue_type_universe()` (filtered to catalog-known,
non-reporting/non-experimental rule_ids) instead of the catalog's
`issue_types` field. A new sanity test,
`test_catalog_issue_types_are_a_subset_of_the_static_universe`, cross-checks
that the catalog never claims a pair the static sources can't also see.

The leak-check test (`test_public_surfaces_never_leak_raw_rule_id`) is now
parametrized over the **complete** active universe (143 pairs) instead of
the tiny 2-entry known-gaps allowlist it was scoped to before — turning a
narrow check into a comprehensive one.

`scripts/atomic_presentation_inventory.py` was updated to use
`full_active_issue_type_universe()` too, so the diagnostic report's coverage
improved from 72 to 140 classified pairs.

### Known, explicitly bounded limitations

1. **Flow-insensitivity.** The resolver tracks "every literal value a name
   is ever bound to across a whole function," not "the value at this exact
   program point given which `if`/`else` branch we're in." This produces
   three false-positive pairs: `pdf_heading_levels.py`'s `level` loop
   variable ranges over `(2, 3, 4, 5)`, but the f-string issue types are only
   ever built inside an `else: # level 3, 4, 5` branch (never 2), further
   guarded by `if level in (4, 5):` for one of the two f-strings (never 3).
   The scanner cannot see those guards and reports the full cross product.
   Documented, named, and excluded from both the ratchet and the diagnostic
   script as `_SCANNER_OVER_APPROXIMATION_ARTIFACTS` /
   `_SCANNER_OVER_APPROXIMATION_ARTIFACTS` — three pairs, precisely
   identified, proven unreachable by reading the guarding code, not guessed.
2. **No cross-module tracing.** Not needed by any real pattern found in this
   codebase today (every rule's `AuditFinding` construction happens within
   the one module that owns that rule) — but if a future rule split its
   detector logic across two files, this scanner would not follow that.

Both limitations are conservative in the safe direction or precisely bounded
and named — neither hides a real gap silently.

## Files changed

- `src/njit_auditor/rule_source_scan.py` — rewritten resolver (see above).
- `tests/test_rule_source_scan.py` — new: 20 pattern-level regression tests,
  one per supported code shape, using synthetic inline source snippets (not
  real rule files, so decoupled from future detector refactors), plus
  negative cases (no `details=`, unresolvable dynamic value) and two
  integration checks against the real `rules/` tree (P014, P057).
- `tests/test_rule_registry_consistency.py` — ratchet now sources from
  `full_active_issue_type_universe()`; new subset-consistency test; leak-check
  test broadened from 2 to 143 parametrized cases; two new documented
  allowlists (`_SCANNER_OVER_APPROXIMATION_ARTIFACTS`,
  `_KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS` — see "Discovered but
  out-of-scope" below); `_KNOWN_WORDING_GAPS` is now empty (P082 is properly
  excluded from the active-default universe itself, rather than included and
  then allowlisted).
- `scripts/atomic_presentation_inventory.py` — uses the new universe;
  excludes the same three scanner-artifact pairs.
- `tests/test_atomic_presentation_inventory_script.py` — updated to expect
  the ten pre-existing, zero-exposure P001-P010 explanation gaps (see below)
  instead of zero gaps, with a staleness check on that allowlist.

## Discovered but deliberately out of scope (per task instructions)

**Update (2026-07-17): fixed.** See the follow-up branch
`fix/p014-p018-suggested-fix-leaks` — `_ISSUE_REMEDIATION_OVERRIDES` entries
were added in `polished_comments.py` for the six pairs below, exactly as
recommended here. `_KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS` and its staleness
test were removed from `tests/test_rule_registry_consistency.py` since the
allowlist is now empty; `test_public_surfaces_never_leak_raw_rule_id` enforces
zero `suggested_fix` leaks directly.

Broadening the leak-check test's coverage from 2 to 143 pairs surfaced **two
real, pre-existing bugs** that were invisible before (nothing had ever run
the check against these pairs). Per this task's explicit instruction to
isolate and document rather than fold into architectural work, **neither was
fixed at the time**:

- **P014 and P018's `suggested_fix` text leaks raw `P0##`/`Q0##` tokens**
  (e.g. "APPROVAL PAGE (Q013, P038)", "P018A-C (Q049-Q051)"). Root cause:
  the raw catalog `remediation` field for these two rules is written as an
  internal developer cross-reference note, and no per-issue-type
  remediation override exists to replace it with student-appropriate text
  for these six `(rule_id, issue_type)` pairs. **Recommended fix (not
  applied):** add `_ISSUE_REMEDIATION_OVERRIDES` entries in
  `polished_comments.py` for these six pairs — presentation-layer only, no
  raw-JSON edit.
- Both are recorded in `_KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS` in
  `tests/test_rule_registry_consistency.py`, with a staleness check
  (`test_known_pre_existing_suggested_fix_leaks_are_not_stale`) so the
  allowlist is forced to shrink the moment someone fixes it.

## Before/after coverage

| Metric | Before this pass | After this pass |
|---|---|---|
| `detector_emitted_pairs_by_static_scan()` raw pairs | 56 | 134 |
| Same, unioned with catalog `issue_types` | 72 | — (see below; catalog is now a *subset* of the scan, verified by a test, not unioned in separately) |
| `full_active_issue_type_universe()` (scan + TeX dispatch + P021 exception) | did not exist | 145 |
| Ratchet test ground truth | catalog `issue_types` only (26/82 rows populated) | `full_active_issue_type_universe()`, filtered to catalog-known/non-excluded rule_ids |
| Leak-check test coverage | 2 pairs (`_KNOWN_WORDING_GAPS`) | 143 pairs (complete active universe) |
| Diagnostic script (`atomic_presentation_inventory.py`) classified pairs | 72 | 140 |
| Diagnostic script ATOMIC / needs-refinement | 72 / 0 | 130 / 10 (the ten pre-existing, zero-exposure P001-P010 explanation gaps — see PR #513's report for why those are low priority) |

## Detector invariance

Ran all 12 available raw evaluation samples through `njit-audit pdf` before
and after this pass's changes: **`(rule_id, issue_type, page)` finding
signatures are byte-identical on every sample** (101, 83, 71, 258, 197, 317,
142, 314, 161, 263, 454, 207 findings respectively — unchanged counts and
unchanged content). This pass touched zero files under `src/njit_auditor/rules/`,
`src/njit_auditor/polished_comments.py`'s templates, or any detector
threshold/confidence logic — only test/tooling infrastructure — so this
result was expected, not a surprise, and confirms it.

## Is the full active universe now mechanically covered?

**Yes, for the AST-scanner's own scope**: every pair the deep manual PR #513
audit found and every pair currently registered in
`polished_comments._ISSUE_TEMPLATES` is now discoverable by
`full_active_issue_type_universe()` (verified directly: zero pairs in
`_ISSUE_TEMPLATES` are missing from the universe, aside from the two
separately-sourced groups — TeX P001-P010 and P021 — which the universe
covers via its other two components). The three flow-insensitivity false
positives are the only known imprecision, and they are named, bounded, and
proven unreachable rather than silently wrong.

## Remaining architectural duplication

Unchanged from PR #513's report: the 4-way issue-type-source duplication
(catalog `issue_types` / `_ISSUE_TYPE_LABELS` / `_ISSUE_TEMPLATES` keys /
detector source) still has four physically separate places recording
overlapping information. This pass makes the *detector source* copy
mechanically re-derivable and provably a superset of the *catalog* copy (see
`test_catalog_issue_types_are_a_subset_of_the_static_universe`), which
closes the specific failure mode that caused the P014 bug, but does not
unify the four sources into one.

## Recommendation for the next smallest safe step

Fix the two pre-existing `suggested_fix` leaks documented above (P014,
P018) — six `_ISSUE_REMEDIATION_OVERRIDES` entries, presentation-layer only,
with the exact repro already captured in
`test_known_pre_existing_suggested_fix_leaks_are_not_stale`. This is smaller
in scope than this pass, independently testable, and closes the one class of
real (if pre-existing) bug this work surfaced but was explicitly asked not
to fix inline.
