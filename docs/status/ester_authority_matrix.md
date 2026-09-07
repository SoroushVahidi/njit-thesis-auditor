# Ester Authority Matrix — Current Pointer

> This file is intentionally short. It exists so `docs/status/ester_authority_matrix.md`
> is a stable path; the actual matrix content lives in the dated file below and
> is updated by adding a new dated file plus updating this pointer, never by
> overwriting matrix history in place.

**Current authoritative matrix:** [`ester_authority_matrix_20260902.md`](ester_authority_matrix_20260902.md)
(machine-readable: [`ester_authority_matrix_20260902.json`](ester_authority_matrix_20260902.json)).

## Known deltas since 2026-09-02 not yet folded into a new dated matrix file

- **R035/R036/R055**: the 2026-09-02 matrix rows still read "NOT judged by
  Ester" / "needs Ester judgment." Ester's Sep-4 review resolved all three
  (see commits `97cc8a3`, `1a90501`, `1d24080`, `aea0e81`). R055 requires the
  literal word "Table"/"Figure" before an `X.x` List of Tables/Figures entry
  number. R036 exempts only a heading-to-its-own-first-child spacing
  transition, not the reverse. R035 fixed the reviewed Anthony false
  positives via landscape-aware centering tolerance; **Praneeth still
  produces 4 live centering findings post-fix, and this repo has no record
  of whether those are the same pages Ester reviewed** (the review happened
  outside this repo — Gmail/live Sheet — and the regenerated Sep-5 R035
  package's Correct?/Notes columns were never returned). Treat as open until
  confirmed against Ester's actual response, not as a settled false positive
  or a settled regression.
- **R016, R018, R020, R023, R026, R028, R033**: `CURRENT_STATUS.md`'s
  historical "Friday discussion / frozen for tuning" label predates this
  matrix and is stale; the 2026-09-02 matrix already records explicit
  Ester decisions for all of these.
- **R024**: still "NO ESTER DECISION FOUND" — accurate as of this writing.
  Unrelated, not-yet-Ester-reviewed hardening exists uncommitted on the
  `main` worktree (title-case hyphenated-fragment and parenthetical
  proper-noun handling); not yet ported to the research branch.
