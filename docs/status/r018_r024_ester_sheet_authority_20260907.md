# R018 and R024: Reconciliation Against the Live Ester Feedback Sheet (2026-09-07)

## Why this supersedes the earlier same-day R018/R024 records

`docs/status/r018_finding_level_review_20260907.md` and the R024 rows in
`docs/status/ester_authority_matrix.md` concluded, from repository evidence
alone, that no recoverable Ester verdict existed for R018's Anthony/Praneeth
findings or for R024 at all. Later the same day, the live shared Ester
feedback Google Sheet was checked directly and found to contain explicit
verdicts for both. This document records that authority and what was done
about it. It does not retract the earlier document's method (repo-only
evidence really was insufficient) — it supersedes its conclusion now that an
external, authoritative source has been consulted.

## R018

**Sheet authority:**

- Anthony's reviewed R018 finding: **false positive**.
- Praneeth's reviewed R018 finding (Section 1.1 area, visible leader-dot
  alignment): **false positive**. Ester additionally noted that sections
  1.3.3, 1.3.4, and 1.3.5 appeared not to align, and asked whether the
  auditor detects that.

**Root cause found (both cases traced to the same class of bug, not a
policy question):**

1. `_has_leader_dot_pattern` (in `pdf_toc_alignment.py`) only recognized a
   literal run of ASCII `.` characters. Many TOC/List pages render leader
   dots as Unicode horizontal-ellipsis characters (`…`), and a wrapped
   (two-line) entry's leader often extracts as two dot clusters joined by a
   single space. Entries using either shape were misread as having no
   leader dots at all, which is exactly the shape of Praneeth's reviewed
   Section 1.1 finding. Fixed generally (dot presence is now scored by
   visible dot weight — an ellipsis counts as 3, a period as 1 — over a
   run that may contain single-space gaps), not by excluding any specific
   entry, page, or document.
2. `NUMERIC_PREFIX_RE` / `SECTION_NUMBER_PREFIX_RE` required whitespace
   immediately after the section/figure number, so a number written with a
   trailing period (`"2.1. Title"`, the style Anthony's List of Figures
   uses) never qualified as a wrap-mergeable entry start. A two-line entry
   in that style split into two unrelated rows, and the continuation's
   hanging-indent x-position was misread as a hierarchy-indent outlier —
   exactly Anthony's reviewed finding. Fixed by accepting an optional
   trailing period before the delimiter, for any document using this
   numbering style.

Both fixes are committed with synthetic regression tests reproducing the
general shape (`tests/test_rules/test_r018.py`) — not the private text —
confirming each is now correctly read as a leader-dot / mergeable-entry
case, and confirming a genuinely dot-less entry or a genuinely misaligned
indent is still flagged.

**Verified against the fresh seven-document audit (correct PyMuPDF venv):**

- Anthony: 0 P018 findings (previously 1, the reviewed case). Absent.
- Praneeth: the Section-1.1-area leader-dots finding is gone entirely from
  her TOC page. Her 3 remaining P018 findings (`missing_page_number` on
  three List of Figures pages) are a different issue type, were never part
  of this reviewed case, and are left as unreviewed findings.

**On "does the auditor detect 1.3.3/1.3.4/1.3.5":** after the leader-dot
fix, every entry on Praneeth's page — including 1.3.3, 1.3.4, and 1.3.5 —
is correctly read as having a leader-dot run, their left indents are
identical to their level-3 peers (129.0pt), and their page-number column is
perfectly aligned with the rest of the page (x1=550.9pt, no outliers). No
current P018 check has a geometric basis to flag these three entries, and
none of dot-presence, indentation, or column-alignment shows a defect
there once the extraction bug above is fixed. Rendering the region at high
resolution shows 1.3.3's leader is visually a broken/two-cluster dot run
(the same extraction artifact fixed above) where 1.3.4/1.3.5 are not,
which is a plausible reason it read as "not aligned" to a human reviewer
at the time — but this is inference, not a confirmed second verdict. No
detector change was made to force a finding here: doing so with only three
known section numbers as the target would be fitting the code to those
numbers rather than to a demonstrated geometric rule, which the project's
existing policy (never hardcode identity) rules out. This is recorded as
an open policy question, not folded into either FP or TP counts.

```
R018_ESTER_REVIEWED_FP_TOTAL = 2   (Anthony, Praneeth Section-1.1-area)
R018_ESTER_FP_REMAINING = 0
R018_ESTER_REVIEWED_TP_TOTAL = 0   (the 1.3.3/1.3.4/1.3.5 note is a question, not a confirmed verdict)
R018_UNRESOLVED_POLICY_CASES = 1   (1.3.3/1.3.4/1.3.5 — see above)
R018_STATUS = resolved (both confirmed reviewed false positives); one open, unforced policy question remains
```

## R024

**Sheet authority:**

- Anthony's reviewed R024 finding: **false positive** — the flagged
  capitalized words are proper nouns / species names.
- Praneeth's reviewed R024 finding: **false positive** — the word
  following a hyphen in the flagged term is not supposed to be
  capitalized.

**Status found:** both fixes already existed on this branch, committed at
`b80eff7` earlier the same session as proactive general hardening (at the
time, with no confirmed Ester authority) — `check_apa_title_case_phrase`'s
`skip_hyphenated_fragments` option (a non-Latin hyphenated prefix dropped
by text extraction should not make the suffix look like an
under-capitalized standalone word) and `_sentence_case_violation_words`'s
parenthesis-depth tracking (a parenthetical list of proper nouns/species
names should not count toward the sentence-case word sample). Anthony's
current P024 findings are exactly zero, confirming his reviewed case is
absent, and it matches the parenthetical-proper-noun shape the sheet
describes. Praneeth's current draft no longer contains a hyphenated term
in her List of Tables matching the reviewed shape (her List of Tables in
this "3rd review" draft has no hyphen-adjacent word at all), so the exact
reviewed instance cannot be directly re-confirmed against her PDF; the fix
is instead verified with a synthetic regression test reproducing the
described shape exactly (`test_p024_lot_non_latin_hyphenated_term_is_not_split_for_title_case`
in `tests/test_pdf_rules.py`, already present from `b80eff7`).

Praneeth still has 7 other P024 findings (page 14, List of Tables) —
unrelated word-capitalization and terminal-punctuation issues (garbled
extraction tokens, ordinary lowercase common words), none hyphen-adjacent.
Their presence confirms the fix is narrowly scoped and did not blanket-
suppress the check.

```
R024_ESTER_REVIEWED_FP_TOTAL = 2   (Anthony, Praneeth)
R024_ESTER_FP_REMAINING = 0
R024_STATUS = resolved against both reviewed decisions
```

## R055

Not part of this reconciliation's reviewed-case set (no specific
document/page was sent to Ester for R055), but the sheet separately
confirmed the general rule: List of Tables/Figures entries must carry the
literal word "Table"/"Figure" before the `X.x` number. That rule was
already implemented at `83ba2cd` (2026-09-05), predating this session's
`4f9f96f` baseline. The tracked review package
(`docs/evaluation/ester_feedback/R055_Ester_Auditor_Feedback.*`) still
dated from before that fix (2026-09-02) and has been regenerated against
current code. Six of seven documents now show a current P055 finding
(Sebastian is clean); this is expected and correct, not over-detection —
these documents' List of Tables/Figures entries are numbered `"2.1."`
style with no "Table"/"Figure" word at all, which is precisely what the
rule (and the sheet) describes as a violation.
