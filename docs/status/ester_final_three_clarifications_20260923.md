# Ester Final Three Clarifications (2026-09-23)

> **Scope:** records Ester Flaim's answers to the final three open reviewer
> questions from `pre_ester_email_unresolved_backlog_audit_20260922.md`, and
> the engineering response. The implementation was developed and validated on
> branch `fix/ester-final-three-clarifications-20260923` and **merged to `main`
> via PR #553** (squash commit `72c8e1f`; CI-tested source head `a2e843c`,
> whose tree is identical to the merged tree). At the time of the
> implementation/merge record, deployment had not yet been performed;
> production deployment was subsequently completed on 2026-09-23 (19:29:49
> EDT) at commit `153e819`, and R018R and R018S were verified live. No e-mail
> was sent and the reviewer workbook was not edited.

**Baseline:** `origin/main` @ `6196f7ed81ef0061aceafd86b80f0bd6462aa4f2`
(merged through PR #549). Branch/worktree:
`fix/ester-final-three-clarifications-20260923`.

## Status summary

| Item | Reviewer policy | Engineering implementation |
|---|---|---|
| R018 wrapped-title alignment | `REVIEWER_POLICY_RESOLVED` | `ENGINEERING_IMPLEMENTATION_COMPLETE` (merged via PR #553, `72c8e1f`) |
| R026 Latin Modern | `REVIEWER_POLICY_RESOLVED` | `ENGINEERING_IMPLEMENTATION_COMPLETE` (behavior already live since `85c5da3`; explicit regression coverage added by PR #553, no detector change) |
| Leader placement (TOC/LoT/LoF) | `REVIEWER_POLICY_RESOLVED` | `ENGINEERING_IMPLEMENTATION_COMPLETE` (merged via PR #553, `72c8e1f`) |

None of the three is an open reviewer question any longer.

**Pre-merge branch validation (historical).** Against base `origin/main`
`6196f7e`: `ruff check .` clean, `mypy src` clean, `python -m pytest`
**3680 passed**, 5 skipped, 3 warnings; seven-document corpus audit as below.
GitHub CI (Python 3.10/3.11/3.12) passed on the final head `a2e843c`, which
was squash-merged unchanged as `72c8e1f`. The evaluation manifest's status
snapshot is a separate, older `main` record and was not advanced.

## Reviewer answers (ground truth)

1. **R018.** "When a title runs for more than one line, the second line
   should align with the text of the first line, not the number." Ester
   cited Praneeth's TOC entries 1.3.3, 1.3.4, and 1.3.5 as examples.
2. **R026.** Asked whether Latin Modern is part of the accepted Computer
   Modern-family allowance, Ester answered **YES**.
3. **Leader placement.** The requirement applies to the Table of Contents,
   List of Tables, and List of Figures. For a wrapped title, leader dots
   begin after the final line of the title. One space is allowed between the
   end of the title and the first leader dot. Sebastian's List of Figures
   example (previously confirmed) remains ground truth.

## Shared infrastructure: per-character geometry on leader pages

Both R018 and leader placement need positions *inside* a span: where title
text starts after a section number, and where a title ends and its leader
begins. The corpus showed both are usually inside one extracted span
(Sebastian's title and leader are one span; Praneeth's number and title are
one span).

- `PdfTextSpan.char_x_bounds` (new, optional): per-character `(x0, x1)`.
- `load_pdf_layout` fills it only on pages that contain a dot-leader run
  (an ASCII/ellipsis/middle-dot run in a span, or ≥4 dot-only spans on one
  line — LaTeX dotfill leaders extract one span per dot). It uses PyMuPDF
  `rawdict` for those pages only and keeps the mapping only when the joined
  characters equal the existing `dict` span text, so no text changes.
- Corpus check: 100% of TOC/LoT/LoF spans in all seven documents received
  geometry with exact text agreement; load time unchanged within noise.
- New helper module `src/njit_auditor/toc_entry_geometry.py` (row glyph
  flattening, visible start, title-text start after a numeric label, and
  title-to-leader gap). Any position that is not measurable returns `None`
  and the checks stay silent.

## R018 — wrapped-title continuation alignment

**Previous implementation.** P018 checked leader-dot presence, hierarchy
indent against same-level peers, and the page-number column. It never
compared a wrapped line to its first line's title text; wrapped rows were
merged into one bounding box, losing per-line geometry. That is why the
2026-09-07 audit measured "no defect" for 1.3.3–1.3.5. (Praneeth's rows also
begin with leading space glyphs, so the line box x0 is 129.0 pt while the
visible number starts at 147.0 pt.)

**Check.** P018 issue type `wrapped_title_continuation_misaligned`, Table of
Contents pages only (R018's reviewer statement was about the TOC; List pages
keep R046's entry-number rule and are not silently brought into scope).

- First row: a numbered entry (`SECTION_NUMBER_PREFIX_RE`) that does not end
  on that row (no leader, no page number).
- Continuations: following single-spaced rows (≤ `WRAPPED_ENTRY_Y_GAP_PT`)
  that are not a new entry start, until the entry ends with a leader, page
  number, or detached page-number row within three rows; otherwise skipped.
- Title-text start: the first visible glyph after the label (exact with glyph
  geometry). Without geometry, a documented lower-bound estimate is used
  (confidence `low`).
- **Predicate (symmetric):** report when
  `|continuation_x − title_x| > max(2 pt, 0.25 em)`. Rightward deviations are
  reported only from exact glyph geometry; the lower-bound estimate cannot
  prove a continuation is too far right, so it stays silent there.
- Tolerance rationale: correctly aligned entries agree to ≤ 0.1 pt; a
  number-column alignment is ≥ 0.75 em off. The existing 10–12 pt TOC indent
  tolerances cluster indent levels and would miss single-digit labels.

**Why symmetric (evidence, not "Ester did not complain").**

1. Ester's wording is an alignment rule: the second line "should align with
   the text of the first line".
2. NJIT's own model TOC (`data/raw/guidelines/Front Matter Pages Lorem
   Ipsum.pdf`, pages 8–9) hangs wrapped lines exactly under the title text:
   level 2 at 172.1 → 172.08 pt, level 3 at 215.8 → 215.76 pt (0.0 pt). The
   exemplar produces no new findings (regression test).
3. The LaTeX pattern is real rendered geometry, not an artifact. On the three
   LaTeX-built TOCs with wrapped numbered entries (Patrick's has none) the
   title's first glyph is a visible letter (e.g. 124.8 pt,
   CMR12) and the continuation's first visible letter sits exactly one CMR12
   em (11.7–12.0 pt) further right at every level. There are no invisible or
   space glyphs; high-resolution renders confirm it. Three independent
   theses share identical indents, so it is a shared template's hanging
   indent. No repository or NJIT source authorizes an extra hanging indent.

**Corpus (seven documents, P018 raw page findings).** All pre-existing P018
issue types are unchanged on every document.

| Document | `wrapped_title_continuation_misaligned` | Shape |
|---|---|---|
| Praneeth | physical pages 11 (4 entries), 12 (1), 13 (3) | continuation left of title text (−18 to −51 pt) |
| Philip | physical pages 11 (4), 12 (5) | +11.7 pt past title text |
| Muyeed | physical pages 10–14 (1 each) | +11.7 pt |
| Youra | physical pages 12 (4), 13 (2) | +12.0 pt |
| Anthony, Sebastian, Patrick | 0 | Anthony/Sebastian exactly aligned; Patrick has no wrapped numbered entries |

An earlier left-only draft produced only the 3 Praneeth pages; the symmetric
check adds the 9 LaTeX pages.

- **Reviewer-confirmed TP:** Praneeth page 11 entries 1.3.3, 1.3.4, 1.3.5.
- **STRONG_UNREVIEWED_CANDIDATE:** Praneeth 1.1 (continuation flush with its
  number, the literal case in Ester's sentence); 3.2.2, 3.2.3, 3.3.1, 3.3.2
  (identical shape to 1.3.x).
- **BORDERLINE_UNREVIEWED_CANDIDATE:** the LaTeX one-em right shift (Philip,
  Muyeed, Youra). The geometry is certain; applying the policy to a shared
  template's hanging indent is not reviewer-confirmed. One optional
  confirmation question was drafted outside the repository and not sent; it is not blocking.

## R026 — Latin Modern

Already accepted before this pass: `_CM_ACCEPTS` in
`pdf_font_compliance.py` contains `lmroman`, `lmbx`, `lmtti`, `latinmodern`,
`latinmodernroman`, after subset-prefix stripping (live since `85c5da3`).
Remediation text already names "Computer Modern/Latin Modern". No detector
change. `tests/test_p026_latin_modern_ester_confirmed.py` pins the real
embedded name variants and confirms an unaccepted family is still flagged.
Corpus: zero P026 findings before and after.

**Legacy alias audit (separate policy item, not changed).** `_TIMES_ACCEPTS`
also accepts `nimbusrom`, `texgyretermes`, `liberationserif`, `freeserif`,
`stixgeneral`/`stix`. All date from the original P026 commit `4e73c39`
(2026-05-29), before any Ester guidance: a developer choice of
metric-compatible Times clones. Only NimbusRomNo9L has a test, and the public
P026A card mentions "common near-equivalent serifs". No explicit reviewer
authority exists for them. Corpus impact is zero: no document uses any of
them. Recommended as a separate low-priority policy task, not this branch.

## Leader placement — TOC, List of Tables, List of Figures

**Previous scope.** No rule owned it (`LEADER_PLACEMENT_RULE_GAP`).
R040/R053/R054 are punctuation-only rules and only strip leaders.

**Checks (no new rule ID).** Two P018 issue types:

- `title_to_leader_gap_too_wide`: measured from the last title glyph's right
  edge to the first leader glyph's left edge, on the same row.
- `leader_dots_before_final_title_line`: a leader on a row with no page
  number while the *next* single-spaced wrapped title row carries the page
  number. Confidence `low`.

For a wrapped title, only the final row carries the leader and is measured;
earlier rows are never required to have leaders.

**What the gap measures, and why the allowance has its terms.** The measurement is glyph-box to glyph-box: title end → first
visible dot's advance box. Two effects sit between them that are not typed
spaces:

- *In-cell padding.* A spaced leader cell centers its dot, so the dot box
  starts (pitch − dot advance)/2 into its cell. This is 0 for contiguous
  dots.
- *Grid phase.* Some typesetters lay leader cells on a page-wide grid. This
  was proven, not assumed: on LaTeX TOC/LoT pages and Word tab-leader TOCs,
  every row's first dot x agrees modulo the pitch to within 0.02–0.36 pt. On
  Praneeth's pages, NJIT's model pages, and LaTeX LoF pages the spread is
  1.9–7.3 pt (typed/non-grid leaders).

Allowance = one measured space + in-cell padding + 0.1 em jitter, **plus one
pitch of grid phase only when the page's leaders are grid-aligned** (≥3 rows,
spread ≤ 1.0 pt). Pages with too few rows to tell keep the grid allowance
(the conservative choice).

This replaces an earlier draft's unconditional pitch allowance, which let two
typed spaces (~6 pt) pass on typed-leader pages even though Ester allows one.

**Corpus distribution (exact geometry, all rows).**

- Typed pages: one-space rows measure 3.0–3.2 pt against 4.2–4.7 pt allowed
  (NJIT model pages included). Two spaces (~6 pt) now fail.
- Grid pages: up to 13.4 pt observed (LaTeX 9.23 pt pitch) against 16.4 pt
  allowed. The smallest margin is 3.0 pt.
- The grid-aware change altered no corpus finding.

| Document | `title_to_leader_gap_too_wide` | `leader_dots_before_final_title_line` |
|---|---|---|
| Sebastian | List of Figures physical page 12 (15.0 pt ≈ 5.0 spaces; 8.2 pt allowed); List of Tables physical page 11 (12.4 pt ≈ 4.1 spaces; 8.2 pt allowed; one-row pages, grid undetermined) | 0 |
| Youra, Anthony, Muyeed, Philip, Praneeth, Patrick | 0 | 0 |

- **Reviewer-confirmed TP:** Sebastian List of Figures page 12.
- **STRONG_UNREVIEWED_CANDIDATE:** Sebastian List of Tables page 11 (same
  multi-space gap before the dots).
- `leader_dots_before_final_title_line` has no corpus instance. It is covered
  by synthetic tests (TOC and LoF; two negative controls: a detached lower
  page number, and a following numbered entry).

## Presentation and public `/rules` cards

The P018 public cards (P018A–P018Q) are Ester's atomic TOC/LoT/LoF
questions; an unmapped issue type gets **no** rule link for students. No
existing card fits the new behavior accurately:

- P018H is hierarchy indent levels, not how a wrapped line hangs.
- P018E–G are wrapped-line spacing.
- P018D is TOC-only leader *style consistency*.

Two cards were therefore added under the existing R018 umbrella (card IDs,
not new rule IDs), worded from Ester's 2026-09-23 statements:

- **P018R** (shown as R018R): wrapped TOC title alignment. It maps
  `wrapped_title_continuation_misaligned`.
- **P018S** (shown as R018S): leader dots right after the title, after its
  final line, at most one space; TOC/LoT/LoF. It maps
  `title_to_leader_gap_too_wide` and `leader_dots_before_final_title_line`.

Wording for all three issue types covers the polished comment, short fix,
web card, explanation, and issue label. The wrapped-title wording is
direction-neutral. Tests assert card mapping, R-display, `/rules` presence,
and no P/Q identifiers or generic-fallback text. `missing_page_number` is
still unmapped; that is pre-existing and not in scope.

**Confidence.**

- `wrapped_title_continuation_misaligned`: `medium` with exact geometry
  (both directions), `low` when estimated. This matches P018's convention:
  medium for per-entry geometric checks, high only for the peer-relative
  page-number column.
- `title_to_leader_gap_too_wide`: `medium`.
- `leader_dots_before_final_title_line`: `low`.

**Grouping.** One finding per page per issue type, with
`affected_entry_count`. A full-pipeline check on synthetic pages shows no
other rule re-reports the same defect.

## Performance

Glyph capture runs on 4–16 pages per document. The table compares
`origin/main` with this branch.

| Document | Load time | Retained memory | Full audit |
|---|---|---|---|
| Muyeed | 0.84 → 0.95 s | 110.6 → 113.5 MB | 2.7 → 3.0 s |
| Youra | 5.03 → 5.06 s | 68.0 → 69.9 MB | 5.7 → 5.8 s |
| Praneeth | 0.94 → 0.96 s | — | unchanged |
| Sebastian | 0.04 → 0.04 s | — | unchanged |

No material regression.

## Remaining reviewer-policy questions

None blocking. Optional: confirm the LaTeX one-em hanging indent is also a
violation (drafted outside the repository; not sent). Separately, the legacy
Times-clone aliases lack explicit authority (zero corpus impact).

## Safety

No private PDF, dissertation prose, or title text is recorded here or in
tests (tests use invented titles). Findings are identified only by
document short name, physical page, issue type, and pt geometry. No
student/page/title/section-number hardcoding in code.
