# R018 Finding-Level Review (2026-09-07)

## Why this exists

`docs/status/ester_authority_matrix_20260902.md`'s R018 row reads:

> Suppress the selected Anthony and Praneeth false positives; verify and
> retain the actual 1.3.3/1.3.4/1.3.5 misalignment behavior.

This is a **task directive**, not a confirmation that the work was done —
contrast with e.g. R033's row, which reads "Yes; current live output is
clean." This document records an exhaustive attempt to determine whether the
directive was ever carried out, and why it cannot currently be resolved
either way from repository evidence alone.

## What was searched

- `docs/status/*` for any R018/P018-specific record.
- `docs/evaluation/ester_feedback/R018_Ester_Auditor_Feedback.xlsx` — last
  touched 2026-09-02; `Correct?`/`Notes` columns are blank. Ester's actual
  reply, if any, is not recorded here.
- `git log --all --grep` (case-insensitive) for r018, p018, and terms tied to
  the directive (anthony, praneeth, hierarchy, misalignment) — no commit
  message documents implementing an Anthony/Praneeth-specific suppression.
- The two candidate implementation commits found (`dfb0cf0`, generic geometry
  work predating the 2026-09-02 matrix; `57f0cbe`, which changes which
  finding gets highlighted as evidence, not classification logic) are both
  confirmed unrelated by reading their diffs.

## Current behavior (fresh audit, correct PyMuPDF >=1.25.0 venv)

| Document | Page | Issue type | Current result |
|---|---|---|---|
| Anthony | 14 | `inconsistent_hierarchy_indent` (4 entries) | Reported, MEDIUM |
| Praneeth | 11 | `inconsistent_leader_dots` (5 entries, includes a line whose visible section number is 1.3.3) | Reported, MEDIUM |
| Praneeth | 12, 16, 18 | `missing_page_number` | Reported, MEDIUM |

## The specific ambiguity

The matrix wants "1.3.3/1.3.4/1.3.5 misalignment" retained. Praneeth's
page-11 finding includes a 1.3.3-numbered entry, but it is classified as
`inconsistent_leader_dots`, not `inconsistent_hierarchy_indent`. Checked the
raw (pre-filter) candidate list directly: Praneeth produces **zero**
`inconsistent_hierarchy_indent` candidates anywhere on her TOC page, even
suppressed ones (`_find_hierarchy_indent_outliers` in
`src/njit_auditor/rules/pdf_toc_alignment.py` never fires for her page at
all). Two readings are equally consistent with everything on record:

1. "Misalignment" was always meant to describe the leader-dots
   inconsistency, and current behavior already satisfies the directive.
2. A genuine indent-misalignment violation Ester actually confirmed is not
   detected under any issue type for Praneeth — a possible true-positive gap
   or a case that was never implemented.

Nothing in the repository can distinguish these two readings. Guessing which
one is correct and "fixing" toward it risks either leaving a real regression
in place or introducing a new one where none exists.

## Test coverage

`tests/test_pdf_rules.py` has independent synthetic coverage for
`inconsistent_hierarchy_indent`, `inconsistent_leader_dots`,
`misaligned_page_number_column`, and `missing_page_number` classification,
but no test specifically encodes an "Anthony-shape" or "Praneeth-shape" false
positive being suppressed, because no such case has ever been identified in
committed code or tests.

## Resolution path

This needs Ester's actual R018 response — the live Sheet or Gmail thread
this repo's tooling was built to summarize, not something recoverable from
what's tracked here. Until then, R018 is classified **UNRESOLVED**, not
CLEAN and not REGRESSED. No code change was made for R018 in this pass.
