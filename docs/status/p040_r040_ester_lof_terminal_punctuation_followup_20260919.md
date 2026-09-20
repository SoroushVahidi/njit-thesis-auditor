# R040/P040 Ester LoF Terminal-Punctuation Follow-Up

**Updated:** 2026-09-19
**Branch:** `fix/r040-ester-lof-terminal-punctuation-followup-20260919`
**Scope:** R040/P040 List of Figures terminal-punctuation detection only. R053
and R054 were rerun as regressions; no deployment, merge, or reviewer email was
performed.

R040 is the reviewer-facing rule identifier. P040 is the internal detector in
`src/njit_auditor/rules/pdf_lof_terminal_punctuation.py`.

## Reviewer Ground Truth

Ester adjudicated three R040 cases:

- Anthony: false positive. The reviewed List of Figures entry must not be
  reported by R040.
- Praneeth: false positive. The reviewed List of Figures entry must not be
  reported by R040.
- Sebastian: true formatting error, but the reviewer explanation is leader
  placement: the leader dots should start right after the last letter of the
  title.

No private figure descriptions, thesis text, or dissertation excerpts are
included in this record.

## Rule Semantics

R040/P040 remains Q075: a List of Figures figure description must end with
terminal punctuation. It does not own List of Figures leader placement,
spacing between a title and its leaders, page-number alignment, entry-number
alignment, sentence case, wrapped-entry spacing, or inter-entry spacing.

Sebastian's reviewed case therefore exposes a rule gap rather than a reason to
redefine R040. Existing related rules cover:

- P018/P075: TOC leader consistency, not LoF leader adjacency;
- P048: LoT/LoF page-number right-column alignment;
- P046: LoT/LoF entry-number left-column alignment;
- P032/P036: wrapped-entry and inter-entry spacing.

No current rule owns "LoF/LoT leader dots begin immediately after the semantic
title text." Record: **LEADER_PLACEMENT_RULE_GAP**.

## Root Cause

P040 stripped page numbers and a legacy ASCII leader pattern before checking
for terminal punctuation. That was too blunt for LoF entries:

- a semantic period immediately before separated ASCII leaders could be
  stripped with the leaders;
- a semantic period attached to Unicode/ellipsis leaders could be treated as
  part of the leader run;
- wrapped entries had to be judged from the reconstructed semantic title, not
  from only the final physical row;
- Sebastian's visible gap before leader dots was being surfaced as a missing
  punctuation warning even though the reviewer identified a leader-placement
  issue.

## Implemented Policy

The fix is scoped to P040. It reconstructs the List of Figures description by
removing the page number and trailing visual dot leaders while preserving the
terminal punctuation signal required by R040:

1. Strip trailing leaders made from ASCII periods, Unicode ellipses, or middle
   dots when the suffix has visible leader weight of at least two dots.
2. Preserve a semantic terminal `.`, `?`, or `!` before leaders.
3. Preserve one leading ASCII period from an attached/separated leader suffix
   when the remaining suffix is still visibly a leader run; this prevents a
   leader-placement defect from being mislabeled as R040 punctuation.
4. Keep R040 limited to LoF complete entries with page-number tokens.
5. Use no dissertation-, page-, title-, or student-specific exceptions.

## Seven-Document Corpus Result

The seven private evaluation dissertations were rerun for R040. Elbert remains
excluded.

| Document | Before | After | Delta |
|---|---:|---:|---:|
| Youra | 40 | 3 | -37 |
| Anthony | 10 | 0 | -10 |
| Muyeed | 44 | 5 | -39 |
| Philip | 16 | 3 | -13 |
| Praneeth | 13 | 7 | -6 |
| Sebastian | 1 | 0 | -1 |
| Patrick | 55 | 25 | -30 |
| **Total** | **179** | **43** | **-136** |

The broad reduction is explained by leader-dot artifacts previously treated as
missing terminal punctuation. The Anthony reviewed false positive is removed.
The Praneeth reviewed false positive is removed; remaining Praneeth R040
findings are separate unreviewed entries. Sebastian no longer receives the
wrong R040 punctuation explanation; the true leader-placement issue is recorded
as a rule gap.

## Regression Coverage

Privacy-safe synthetic tests cover:

- Anthony-like wrapped entry with terminal punctuation before leaders;
- Praneeth-like Unicode/ellipsis leaders attached to terminal punctuation;
- Sebastian-like visible gap before dot leaders, with no R040 punctuation
  report;
- correct leader placement with terminal punctuation;
- genuine punctuation violation with Unicode leaders only;
- wrapped semantic-title reconstruction;
- detached punctuation span associated with the semantic title;
- existing P053 and P054 leader-dot regressions.

## R053/R054 Regression

R053 remains unchanged on the seven-document corpus: Youra 0, Anthony 0,
Muyeed 1, Philip 0, Praneeth 0, Sebastian 0, Patrick 0; total 1.

R054 remains unchanged on the seven-document corpus: Youra 1, Anthony 0,
Muyeed 1, Philip 2, Praneeth 0, Sebastian 0, Patrick 0; total 4.

## Validation Snapshot

- `ruff check .`: pass.
- `mypy src`: pass.
- `python -m pytest`: 3563 passed, 3 warnings.
- Targeted P040 tests: 21 passed, 781 deselected.
- Targeted P053 tests: 19 passed, 783 deselected.
- Targeted P054 tests: 20 passed, 782 deselected.
- Combined P040/P053/P054 slice: 57 passed, 745 deselected.
- Seven-document R040 corpus audit: total 179 to 43.
- Seven-document R053 corpus audit: unchanged at total 1.
- Seven-document R054 corpus audit: unchanged at total 4.

No private PDFs, private figure descriptions, or verbatim thesis text are
committed.
