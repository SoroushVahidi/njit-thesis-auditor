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
  Ester decisions for all of these. R018's row previously read as
  UNRESOLVED here (`r018_finding_level_review_20260907.md` — no
  implementing commit or returned xlsx was found in-repo). The live Ester
  feedback sheet was checked directly the same day and does carry explicit
  verdicts: Anthony's and Praneeth's reviewed R018 findings are both false
  positives. Both are now confirmed absent from current output — see
  `r018_r024_ester_sheet_authority_20260907.md`, which supersedes
  `r018_finding_level_review_20260907.md`'s conclusion (not its method).
  At that time, Ester's note that sections 1.3.3/1.3.4/1.3.5 "do not align"
  was a question, not a confirmed second verdict; she resolved the alignment
  question on 2026-09-23. See `ester_final_three_clarifications_20260923.md`.
- **R024**: previously "NO ESTER DECISION FOUND". The live Ester feedback
  sheet was checked directly on 2026-09-07 and does carry explicit
  verdicts: Anthony's and Praneeth's reviewed R024 findings are both false
  positives (proper nouns/species names; hyphenated-fragment
  capitalization, respectively). The general hardening already committed
  at `b80eff7` (reimplemented from `main`'s uncommitted work before any
  authority was known) matches both rationales and is confirmed against
  the fresh seven-document audit — see
  `r018_r024_ester_sheet_authority_20260907.md`.
- **R024 (2026-10-05, latest):** Ester answered that List of Tables titles
  and List of Figures titles both use title case, and that the two checks
  need different codes. List of Tables is R024D and List of Figures is
  R024E; both enforce title case. This supersedes the earlier List of
  Figures sentence-case reading of Q074 (and P017's List of Figures
  sentence-case check, now removed). The Muyeed p16 lowercase List of
  Tables word stays a true violation the student may ignore. See
  `ester_feedback_round_20261005.md`.
- **R037 (2026-09 live workbook, later than the dated matrix):** the
  Biographical Sketch page is iv. Every later numbered front-matter page
  continues the Roman sequence, including continuation pages; section types
  do not have fixed later numerals. The detector already followed this rule.
  Its public card and finding prose were synchronized in
  `r037_q029_q074_authority_consistency_20261006.md`. The dated matrix's
  `NO ESTER DECISION FOUND` entry is retained as historical provenance.
- **R045 (2026-10-05, latest):** single spacing within an entry is
  mandatory; a hanging indent is optional and never reported. Ester resolved
  numbering on 2026-10-06: Biographical Sketch publications must not be
  numbered. See `r045_no_numbering_ester_20261006.md`. The dated 2026-09-02
  matrix row describing a required hanging indent is historical.
- **R018/R075 engineering ownership (PR #558):** the tested genuine TOC-wide
  missing-leader consistency case belongs to R075. R018 keeps alignment,
  continuation, and leader-placement checks; the tested case has no duplicate
  report. This updates the current implementation pointer, not the dated
  matrix's historical Ester judgments; see [`CURRENT_STATUS.md`](CURRENT_STATUS.md#historical-ester-reconciliation-pr-558).
