# Targeted Follow-Up Package: Post-R011/R015 Fixes (2026-08-25)

**Purpose:** three specific, unresolved cases for Esther's review, surfaced
while implementing her R011 and R015 feedback. None of these has been
changed in the detector — each needs her judgment before any further code
change. Wording below is neutral; nothing here is labeled as a confirmed
false positive or true positive.

**Repository state at time of writing:** `main` @ `a23f7093a6c4365539200d0f807a522046a80e7a`
(R011 fix `7090b824`, R015 fix `a23f7093`, both committed, not pushed).

---

## 1. R015 / Youra — physical PDF page 101 (printed page 84)

**Should the auditor report this as an R015 violation?**

- **Location:** middle of the page, second body paragraph in this section.
- **Auditor interpretation:** "Later paragraph appears to be missing expected
  first-line indentation" (`missing_later_indent`).
- **Confidence:** HIGH.
- **Measured geometry:** affected line bbox `(108.4, 376.1, 540.4, 388.1)`;
  expected first-line indent is approximately 36 pt, observed indent is 0.0 pt.
  The current paragraph grouping treats the affected paragraph as 6 lines.
- **Affected line (as the auditor currently reads it):** "counterpart to the
  Type 4 SMFR configuration described by Park et al. (2018), in..." — flush
  against the left margin, immediately followed by several more flush lines,
  on a page where other paragraphs open with a visible first-line indent.

**Surrounding context:** Immediately above this line, on the same printed
row, sits a short bolded phrase ("Comparison with the Type 4 SMFR scenario")
followed on that same row by the start of a sentence ("Case 1 provides an
observational..."). The line the auditor flags is the direct continuation of
that sentence, wrapped onto the next printed row.

**Auditor diagnosis:** The bold lead-in phrase and the sentence start are both
ordinary usable text lines and are not row-remnant fragments. They remain
separate because the heading-like bold text and regular body text do not merge,
and the sentence start is too far right to join the preceding paragraph. Before
the R015 row-remnant fix, this same downstream paragraph segment was only 2
lines and stayed below the auditor's 4-line reporting gate; after the fix, a
later same-row short fragment ("is maintained.") correctly reconnects with "In
this case, MMS observed...", extending the same flush-left paragraph group to 6
lines and making the existing run-in-heading-adjacent limitation visible.

**Why this is ambiguous:** Whether the auditor should treat "counterpart to
the Type 4 SMFR configuration..." as the start of a new paragraph (missing
its indent) or as a mid-sentence continuation of "Case 1 provides an
observational..." depends on how that bolded lead-in phrase and the sentence
after it are meant to read together — a judgment call about the page's own
layout, not something the geometry alone resolves.

**Question for Esther:** Looking at physical PDF page 101 — does the
paragraph beginning "Case 1 provides an observational counterpart to the
Type 4 SMFR configuration..." require a first-line indent, or is it a
continuation that should stay flush?

---

## 2. R011 / Muyeed — physical PDF page 36 (printed page 15)

**Should the auditor report this as an R011 violation?**

- **Location:** bottom of the page, final line of body text.
- **Auditor interpretation:** text crossing the bottom margin.
- **Confidence:** MEDIUM.
- **Measured geometry:** approximately 9.2 pt below the required 1-inch
  bottom margin (roughly 0.13 inch), a single line. Page height is 792 pt,
  required bottom boundary is `y=720.0`, and the affected line bbox is
  `(137.6, 717.2, 243.7, 729.2)`.
- **Affected line:** "...clustering algorithm." (end of paragraph, last line
  on the page).

**Why this is ambiguous:** The current auditor treats bottom-margin overflow
up to 9.0 pt as ordinary single-trailing-line spacing and does not report
it (per Esther's R011 feedback confirming several findings in the 3.9-8.2 pt
range as false positives). This case sits just above that cutoff. A prior
internal review separately flagged this same ~9.2 pt pattern, recurring
across many pages and several dissertations, as an open question rather than
a settled case.

**Representative additional example** (same pattern, different document):
Philip, physical PDF page 6, printed page iv — bottom margin, MEDIUM
confidence, approximately 9.2 pt overflow, single line ("Pennsylvania, USA,
2025."), bbox `(144.4, 717.2, 276.3, 729.2)`.

**Question for Esther:** Looking at Muyeed physical PDF page 36 (and, for
comparison, Philip physical PDF page 6) — is a single line extending about
9.2 pt (roughly 1/8 inch) below the required bottom margin something a
student should be asked to fix, or is this still within an acceptable range?

---

## 3. R011 / Patrick — physical PDF page 88 (printed page 76)

**Should the auditor report this as an R011 violation?**

- **Location:** right edge of a reference-list entry.
- **Auditor interpretation:** text crossing the right margin.
- **Confidence:** HIGH.
- **Measured geometry:** approximately 18.0 pt beyond the required 1-inch
  right margin (roughly 1/4 inch), a single reference entry. Page width is
  612 pt, required right boundary is `x=540.0`, and the affected line bbox is
  `(137.9, 304.7, 558.0, 316.7)`.
- **Affected content:** a citation entry containing a long title ("Weng Cho
  Chew. 'Planarly Layered Media'. In: Waves and Fields...") that does not
  wrap before reaching the margin.

**Why this is ambiguous:** Esther's R011 feedback confirmed a smaller
reference-list right-margin overflow (about 6.9 pt) as a false positive,
reasoning that a reference entry can contain an unbreakable long title that
cannot wrap without altering the citation. The auditor currently extends
that allowance only up to about 9 pt total for reference entries. This case,
and two others in the same document, sit well beyond that bound (10.2-18.0
pt).

**Representative additional example** (same document, smaller overflow):
Patrick, physical PDF page 90, printed page 78 — right margin, MEDIUM
confidence, approximately 10.2 pt overflow, two reference entries, with
affected bboxes `(137.9, 74.6, 548.8, 86.6)` and
`(137.9, 199.1, 550.2, 211.1)`.

**Question for Esther:** Looking at Patrick physical PDF page 88 (and, for
comparison, physical PDF page 90) — should a reference entry still be
required to stay within roughly 9 pt of the right margin even when it
contains a long, unbreakable title, or is additional overflow acceptable for
genuinely unbreakable reference text?

---

## Notes for whoever incorporates Esther's answers

- These are diagnosis-only; no detector code was changed to produce or
  address any of the three cases above.
- If Esther confirms the R015 Youra case either way, it is a single
  data point about a run-in-heading-adjacent paragraph-boundary pattern
  described in `docs/status/p015_r015_esther_feedback_false_positive_fix_20260825.md`
  ("Youra page 101 — investigated in depth"); fixing it generally would be a
  separate, broader change from the row-remnant fix already shipped.
- If Esther says the ~9.2 pt bottom-margin cluster is acceptable, raising
  `BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT` past 9.0 in
  `src/njit_auditor/rules/pdf_margins.py` would need to be re-checked against
  the full real-corpus distribution (hundreds of similarly-sized findings
  across all seven dissertations), not just the two representative pages
  above — see "Deliberately not resolved" in
  `docs/status/p011_r011_batch_2026_08_false_positive_fix.md`.
- If Esther says larger reference-list overflow should also be accepted,
  `REFERENCES_MARGIN_EXTRA_TOLERANCE_PT` in the same file would need a new,
  explicitly chosen bound (not "unlimited") to avoid also hiding a genuinely
  oversized, non-reference-related margin problem.
