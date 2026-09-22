# Pre-Ester-Email Unresolved Backlog Audit (2026-09-22)

> **Purpose:** before sending the next Ester email, determine exactly what
> remains technically unresolved, what can still be solved without reviewer
> input, and what genuinely must be asked of Ester. Audit-only — no detector,
> threshold, or rule-ID change; no email sent; no feedback workbook edit; no
> deploy.

**Baseline:** `main` @ `681ed0440c985cf9a0418e93581228552e2d4558` (merged
through PR #548 / R068).

## R018 — sections 1.3.3/1.3.4/1.3.5 open alignment question

**Already investigated in depth** by
`docs/status/r018_r024_ester_sheet_authority_20260907.md`. Re-verified here,
no new evidence changes the conclusion.

- Current implementation: `src/njit_auditor/rules/pdf_toc_alignment.py`
  (`_find_hierarchy_indent_outliers` for indentation, leader-dot-weight
  scoring for dot presence, page-number right-column alignment).
- Geometry audit (privacy-safe, structural only): after the 2026-09-07
  leader-dot-extraction fix, Praneeth's TOC entries 1.3.3, 1.3.4, and 1.3.5
  all have identical left indent to their level-3 peers (129.0pt) and a
  page-number column aligned to x1=550.9pt with no outliers. Zero geometric
  defect exists under any of the three current P018 checks (dot presence,
  hierarchy indent, column alignment).
- Detection behavior: no P018-family finding fires on these three entries,
  and this is correct given the geometry above — not a detection gap.
- Rule ownership: this is squarely P018's domain (TOC alignment); R039
  (level-2/3 indentation-to-show-hierarchy) is the closest adjacent rule and
  is already satisfied (129.0pt indent matches peers).
- Authority: no NJIT written source or existing Ester policy defines a
  stricter requirement here. The best available explanation is a rendering
  artifact (1.3.3's leader dots render as a visually broken two-cluster run)
  that could look "misaligned" to a human eye without being a structural
  defect — but this is inference, not a confirmed verdict, and the project's
  own no-hardcoding policy rules out forcing a finding keyed to these three
  specific section numbers.

**Classification: GENUINELY_REQUIRES_ESTER.**

**Minimal question:** "For Praneeth's TOC entries 1.3.3/1.3.4/1.3.5 — after
fixing a leader-dot text-extraction bug, we now measure their indentation,
leader-dot presence, and page-number-column alignment as all consistent with
their peers. Can you confirm there's nothing further to flag there, or tell
us more specifically what looked misaligned?"

## R034 — Copyright Page metadata/layout (top-margin header, year/author match)

- Current implementation: `src/njit_auditor/rules/pdf_copyright_page.py`
  (`check_pdf_copyright_page` for P034; sibling advisories P051/P052 for
  year/author-not-found). Conservative: requires a confidently-identified
  Copyright Page AND Title Page, hashes author names (never stores raw
  names), and already has a middle-initial/suffix tolerance for author
  comparison (added 2026-06-01 after a self-diagnosed false-positive
  investigation, `docs/evaluation/p034_author_mismatch_investigation.md`).
- Corpus findings (fresh, all seven private dissertations): **zero** P034,
  P051, or P052 findings on any of Youra, Anthony, Muyeed, Philip, Praneeth,
  Sebastian, Patrick. There is nothing currently flagged and nothing to send
  Ester.
- Why it shows "NO ESTER DECISION FOUND": there has never been a live
  finding on the current evaluation corpus for her to review — not a stuck
  or ambiguous rule definition. The two historical P034 findings that ever
  fired (on different, older fixtures, not this corpus) were self-diagnosed
  and fixed as a false-positive pattern before any reviewer package was
  needed.
- Overlap check: distinct from R033 (title consistency across Title/
  Abstract/Approval pages, already clean) and R051/R052 (year/author
  *presence*, not *match*) — no duplication.

**Classification: ALREADY_RESOLVED_NO_ACTION.** Nothing to fix, nothing to
ask Ester right now. Revisit only if a future document actually produces a
P034/P051/P052 finding.

## R026 — Latin Modern / font-alias expansion

- Current implementation already accepts Latin Modern (LMRoman/LMBX/LMTTI/
  "latinmodern"/"latinmodernroman") as equivalent to Computer Modern, plus
  several near-equivalent Times-family serif aliases (NimbusRomNo9L, TeX
  Gyre Termes, Liberation Serif, FreeSerif, STIX), with embedded PDF
  subset-name prefixes (`ABCDEF+...`) already stripped before matching
  (`src/njit_auditor/rules/pdf_font_compliance.py`). This has been live
  since commit `85c5da3` (2026-07-01), attributed to "Ester guidance" at the
  time.
- `docs/status/ester_policy_review_p021_p026.md` (2026-07-03) documents the
  precise gap: Ester's literal sheet names only "Times New Roman, Arial, and
  Computer Modern Typeface family" — Latin Modern and the serif aliases are
  *not* on that literal list, even though they are functionally the same
  underlying LaTeX/Overleaf-default family under different embedded PDF font
  names. That doc's own "Implementation guardrails" say: do not change P026
  accepted-font detection until policy is confirmed.
- Corpus findings (fresh, all seven private dissertations): **zero** P026
  findings anywhere. No document in the current corpus uses Computer
  Modern/Latin Modern or triggers a font-size/family issue at all, so this
  is a live-behavior risk with **no current corpus impact** — a forward
  policy-confirmation gap, not an active false-positive/negative generator
  today.
- Split classification: the *technical* subset-prefix normalization is
  already correctly implemented (nothing to fix there); only the *policy*
  question — whether Latin Modern (and the other near-equivalent serif
  aliases) should be explicitly authorized alongside Computer Modern, versus
  tightened to Ester's literal three-name list — remains open.

**Classification: GENUINELY_REQUIRES_ESTER** (policy authorization of an
already-implemented, currently low-risk permissive default).

**Minimal question:** "Our tool currently treats Latin Modern (Overleaf's
LaTeX default) as equivalent to Computer Modern, plus a few visually
near-identical serif fonts, beyond the three families your sheet names
(Times New Roman, Arial, Computer Modern). Is that OK to keep, or should we
tighten to exactly your three names?"

### Additional item found in the same investigation: P021 abstract word limits

Not one of the five originally-named candidates, but surfaced directly while
reading the same policy-review doc (which bundles P021 and P026 together as
the two rules "intentionally deferred" from wording-only work because both
are constants/policy conflicts, not wording issues):

- `src/njit_auditor/rules/latex_abstract.py`: `PHD_WORD_LIMIT = 350`,
  `MS_WORD_LIMIT = 150` — **still unchanged** as of this audit.
- Ester's sheet (per `docs/status/ester_feedback_source_of_truth.md`): PhD
  ≤400 words, MS ≤200 words.
- This is a real, live constants conflict, not wording: the tool currently
  tells students to shorten their abstract to a *stricter* limit than
  Ester's actual stated policy, which is a concrete potential-harm risk
  (over-trimming a compliant abstract), not just a permissiveness question
  like R026.
- A full draft question already exists, unsent, in
  `docs/status/ester_policy_review_p021_p026.md` ("Proposed message to
  Ester" section).

**Classification: GENUINELY_REQUIRES_ESTER** (constants conflict; degree-type
inference is also heuristic, per the same doc, so the exact applicability
scope should be confirmed too).

**Minimal question:** "Our tool currently flags PhD abstracts over 350 words
and MS abstracts over 150 words. Your sheet says PhD ≤400 and MS ≤200. Can
you confirm 400/200 are correct, and whether they apply to every NJIT
program or vary by department?"

## LEADER_PLACEMENT_RULE_GAP

Already fully recorded by
`docs/status/p040_r040_ester_lof_terminal_punctuation_followup_20260919.md`.
Re-verified: no rule currently owns "LoF/LoT/TOC leader dots must begin
immediately after the semantic title text" — R040/R053/R054 are punctuation-
only rules and explicitly do not claim this. Only one reviewer-confirmed
example exists (Sebastian's List of Figures case), and several scope
questions remain genuinely open and would require inventing an unvalidated
threshold to resolve alone: LoF-only vs. also LoT/TOC; wrapped-title handling;
whether a tolerance (some visual gap is normal kerning) vs. a hard
zero-gap rule is intended; and there is no second example to cross-validate
a chosen tolerance against.

**Classification: GENUINELY_REQUIRES_ESTER** (per the project's own standing
policy: prefer asking over inventing a threshold/scope from one example).

**Minimal question:** "Sebastian's List of Figures entries have a visible
gap between the title and the leader dots. Is that itself a violation we
should flag? If so: List of Figures only, or also List of Tables/Table of
Contents? And how should a wrapped (multi-line) title be handled?"

## UNNUMBERED_BOLD_HEADING_GAP

Already recorded by
`docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md`
("Separate Bold-Heading Observation"). Re-verified rule-ownership audit: P020
(title-case style of *recognized* headings) does not report unnumbered bold
run-in phrases; P027 (numbered-heading level/style) cannot own an unnumbered
phrase by definition; P026 (font family/size) has no concept of "bold
reserved for headings." No existing rule owns this.

Ester's stated policy ("bold should be reserved for numbered titles/
headings") is a clear rule in principle, but the scope is not precise
enough to implement safely: does "reserved exclusively"
mean flagging *every* other bold span in the document (which would very
likely produce large numbers of false positives on legitimate bold use —
table headers, defined-term emphasis, "Note:"-style labels, captions), or
only a bold, standalone, heading-shaped phrase (short line, no numbered
prefix, followed by body text) — the shape of the one known example from the
R015 review? Implementing the broad reading now would require inventing that
scope distinction without reviewer confirmation.

**Classification: GENUINELY_REQUIRES_ESTER** (scope confirmation needed
before a new rule can be safely implemented; the underlying exclusion
patterns for captions/bullets/table content already exist elsewhere in the
codebase and could be reused once scope is confirmed).

**Minimal question:** "You mentioned bold should be reserved for numbered
heading levels 1-4. Should we flag every other bold phrase in the document
(table headers, emphasis, labels), or only a phrase that looks like a
heading — a short standalone bold line with no body continuation — but has
no section number?"

## Additional search for other current unresolved items (Phase 8)

Bounded search across `docs/status/` for "unresolved", "needs Ester", "rule
gap", "no Ester decision", "open policy question", etc., reconciled against
current `main`:

- **R035** (figure/table centering/caption position) and **R036*** rows in
  `ester_authority_matrix_20260902.md` still say "NO ESTER DECISION FOUND" —
  genuinely true (no live judgment was ever supplied), but there is no known
  live finding or reviewer-flagged case driving either one right now, so
  neither needs to go in the next email. (*R036 nonetheless already runs a
  conservative, zero-report production policy — see `CURRENT_STATUS.md` — so
  it is closed from an engineering-risk standpoint even though formally
  un-adjudicated.)
- **R055** was found to be stale in the *opposite* direction: the authority
  matrix's row and its 2026-09-02 "Unresolved Items" footer said "no live
  Ester judgment," but `docs/status/r018_r024_ester_sheet_authority_20260907.md`
  (five days later) recorded that the live sheet *did* separately confirm
  the general R055 rule. Fixed in this pass (see Canonical Status Cleanup
  below) — this was stale documentation, not a live gap.
- No other genuinely current unresolved reviewer-driven item was found
  beyond the five investigated above plus P021.

## Decision matrix

| Item | Current state | Existing authority sufficient? | Engineering work needed? | Ester needed? | Recommended next action |
|---|---|---|---|---|---|
| R018 (1.3.3/1.3.4/1.3.5) | No geometric defect found under any current check | No | No | **Yes** | Ask minimal question above |
| R034 | Zero live findings on corpus; conservative, tested implementation | N/A (nothing to decide) | No | No | None — already resolved |
| R026 (Latin Modern) | Already implemented, permissive, zero live corpus impact | No (policy, not technical) | No | **Yes** | Ask minimal question above |
| P021 (abstract word limits) | Live constants conflict (150/350 vs. 200/400) | No | No (once confirmed, a 2-constant change) | **Yes** | Ask minimal question above |
| LEADER_PLACEMENT_RULE_GAP | No rule owns it; one example only | No | Only after scope confirmed | **Yes** | Ask minimal question above |
| UNNUMBERED_BOLD_HEADING_GAP | No rule owns it; one example only | No | Only after scope confirmed | **Yes** | Ask minimal question above |
| R035, R036, R055 (Phase 8 sweep) | No live case; R055 was a stale-doc false alarm (now fixed) | N/A | No | No | None for now |

## Engineering before email

**Nothing.** No item is TECHNICALLY_RESOLVABLE_WITH_EXISTING_AUTHORITY. R034
needs no action. Every other item genuinely needs an Ester decision before
any further code change, per this project's standing policy against
inventing thresholds/scope from a single example.

## Questions for Ester (minimal final set)

1. **R018** — 1.3.3/1.3.4/1.3.5 TOC alignment (see wording above).
2. **R026** — Latin Modern/serif-alias authorization (see wording above).
3. **P021** — abstract word-limit constants (see wording above).
4. **LEADER_PLACEMENT_RULE_GAP** — Sebastian's List of Figures leader-gap
   scope (see wording above).
5. **UNNUMBERED_BOLD_HEADING_GAP** — bold-reservation scope (see wording
   above).

No email was drafted or sent in this pass — audit-only, per task scope.

## Canonical status cleanup performed in this pass

`docs/status/CURRENT_STATUS.md` and `docs/status/ester_authority_matrix_20260902.md`
(+ `.json`) were updated to fix stale facts found during this audit:

- `origin/main` SHA corrected to `681ed04` (was `fce5868`, three merges
  stale).
- R040/R046/R048/R078/R066/R068 sections corrected from "not merged"/
  ambiguous wording to explicitly state their merging PR (#543/#544/#545/
  #546/#547/#548).
- Authority-matrix rows for R040, R053, R054, and R055 corrected from stale
  "NO ESTER DECISION FOUND" to the explicit decisions already documented
  elsewhere in the repo (leader-dot false positives for R040/R053/R054; the
  live-sheet general-rule confirmation for R055).
- "Feedback-Cycle Rule State" table and "Next Work Sequence" section
  refreshed to reflect all-merged status and point here.

No historical/dated document was rewritten; only the two canonical
current-only status documents were corrected, and only for facts
contradicted by verified current repository/GitHub state.

## Safety

No private PDFs committed. No dissertation prose quoted (only structural/
geometric metadata: page numbers, pt coordinates, font-name strings, word
counts). No reviewer verdict was invented — every classification above is
traceable to a specific existing repository record or a fresh, privacy-safe
corpus re-audit. No email sent. No feedback workbook modified. No deploy. PR
#523 untouched. No new rule ID started.
