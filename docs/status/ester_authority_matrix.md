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
  (see commits `97cc8a3`, `1a90501`, `1d24080`, `aea0e81`, `6facf49`). R055
  requires the literal word "Table"/"Figure" before an `X.x` List of
  Tables/Figures entry number. R036 exempts only a heading-to-its-own-first-child
  spacing transition, not the reverse. R035 fixed the reviewed Anthony false
  positives via landscape-aware centering tolerance; Praneeth's page-72
  finding turned out to be an unrelated structural bug (text fragments used
  as a figure-body proxy when no graphic block was found), fixed at
  `6facf49` — see `r035_praneeth_text_fallback_fix_20260907.md`. Her
  remaining 3 findings (pages 67, 69, 100) were never sent to Ester and are
  not, per project policy, false positives merely for being unreviewed.
- **R016, R018, R020, R023, R026, R028, R033**: `CURRENT_STATUS.md`'s
  historical "Friday discussion / frozen for tuning" label predates this
  matrix and is stale; the 2026-09-02 matrix already records explicit
  Ester decisions for all of these, **except R018**, whose row is a task
  directive that was never confirmed as completed anywhere in this repo —
  see `r018_finding_level_review_20260907.md`. R018 is genuinely
  UNRESOLVED, not settled.
- **R024**: still "NO ESTER DECISION FOUND" — accurate as of this writing.
  The hardening that existed uncommitted on the `main` worktree (title-case
  hyphenated-fragment and parenthetical proper-noun handling) has been
  reimplemented and committed on the research branch at `b80eff7`; it is
  general correctness work, not a response to an Ester decision (none
  exists for R024).
