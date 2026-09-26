# P021 and P026 Policy Review

> **Superseded for P021:** The P021 abstract-limit question recorded here is
> historical. Current policy is MS thesis abstract ≤200 words and PhD
> dissertation abstract ≤400 words, and the live detector/catalog use those
> limits. P026 notes in this document remain historical policy-review context.

> **Purpose:** Record the exact policy questions that need Ester/human
> confirmation before P021 (abstract word count) or P026 (body font
> compliance) can be changed. This document is **documentation-only** — it
> does not implement wording changes, detector changes, threshold changes,
> or constant changes.
>
> **Recorded:** 2026-07-03 (post–PR #421 merge; main @ `d1addfb11b4addf24a078b4ba8c018f4a91768be`)
>
> **Related:** [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md) ·
> [ester_language_alignment_audit.md](ester_language_alignment_audit.md) ·
> [ester_current_wording_inventory.md](ester_current_wording_inventory.md) ·
> [ester_wording_alignment_checkpoint.md](ester_wording_alignment_checkpoint.md)

---

## Why this review is needed

- P021 and P026 were **intentionally deferred** from the wording-only
  implementation slices (Slices 1–6, PRs #414–#420). Every other rule in
  those slices had catalog/detector agreement; these two do not.
- Both rules involve **policy or standard interpretation**, not just wording
  polish — the numbers and accepted values themselves are in question, not
  just how they're phrased to students.
- Changing them without confirmation could create **false positives** (a
  compliant document flagged as wrong), **false negatives** (a
  non-compliant document passed as fine), or **incorrect advice to
  students** (telling a student to cut their abstract to a limit that isn't
  actually NJIT's requirement).
- Ester's spreadsheet language, as recorded in
  [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md),
  appears to **differ from current repo/detector assumptions** for both
  rules. The repo needs one clear decision before any implementation touches
  either rule.

---

## P021 — Abstract word-count policy question

### Current repo/catalog wording

From `data/processed/rules/project_added_rules.json` (`id: "P021"`):

- **Question:** "Does the abstract exceed the NJIT word-count limit for the
  detected degree type?"
- **Remediation:** "Shorten the abstract to within the applicable limit.
  PhD: ≤350 words. MS: ≤150 words."
- **`web_app.py` `_RULE_TEXT_OVERRIDES["P021"]` `rule_definition`:** "PhD
  abstract maximum: 350 words. MS/Master abstract maximum: 150 words.
  Degree type is inferred from the document text. Word count uses
  conservative tokenization (letter-containing tokens only)."

### Current detector limits/constants

Found in `src/njit_auditor/rules/latex_abstract.py`:

```python
PHD_WORD_LIMIT = 350
MS_WORD_LIMIT = 150
```

Both the LaTeX-source path (`run_latex_abstract_word_count_check`) and the
compiled-PDF path (`src/njit_auditor/rules/pdf_abstract.py`,
`check_pdf_abstract_word_count`) import and use these same two constants.

### Ester spreadsheet target (per source-of-truth doc)

From [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md)
and [ester_current_wording_inventory.md](ester_current_wording_inventory.md):

- MS thesis abstract: **200 words or less**
- PhD dissertation abstract: **400 words or less**

### Discrepancy

| | Current repo/detector | Ester sheet |
|---|---|---|
| MS limit | 150 words | 200 words |
| PhD limit | 350 words | 400 words |

Both limits differ. This is a **constants conflict**, not a wording
question — no amount of rewording the question/remediation text resolves it
honestly while the underlying number is contested.

### Can the code reliably distinguish MS thesis vs. PhD dissertation?

Not fully. `infer_degree_type()` (LaTeX path) and `_infer_degree_from_pdf()`
(PDF path) both do a **keyword-frequency scan**:

- PhD signals: `ph.d`, `doctor*`, `doctoral`, `dissertation`
- MS signals: `master*`, `m.s.`, `m.eng.`, `thesis` (LaTeX path only; the PDF
  path omits the generic word `thesis` from its MS pattern)
- "dissertation" is weighted above "thesis" since it's PhD-specific at NJIT,
  but a document that never uses "dissertation"/"doctoral"/"Ph.D" and only
  uses generic words like "thesis" could still be misclassified.
- Both functions fall back to `"unknown"` when no signal is found, and both
  callers then **default to the PhD (higher) limit** as the conservative
  choice.

This is a heuristic, not a reliable classifier, and the codebase already
acknowledges this in `pdf_abstract.py`'s module docstring: *"Degree type
(PhD/MS) cannot be reliably inferred from the PDF text layer alone; a
conservative threshold of 350 words (PhD limit) is used."*

### Can the code reliably count abstract words in the intended way?

Partially. `count_abstract_words()` counts whitespace-separated tokens that
contain at least one letter — a conservative approximation, not a true
word-boundary tokenizer. The PDF path only reads the **first page** of the
Abstract section, so a multi-page abstract is undercounted.

### Review questions

1. Should the auditor use **200 words for MS theses and 400 words for PhD
   dissertations** (matching Ester's sheet), replacing the current 150/350?
2. Should those limits apply to **all NJIT submissions**, or only to
   specific programs/degree types (e.g., does every NJIT MS program share
   one abstract limit, or do some departments differ)?
3. If the document type is unclear, should the warning be **shown,
   suppressed, or shown as manual-review** (rather than silently applying
   the higher PhD-style limit as today)?
4. Should the word-count warning be **strict or advisory**?
5. Should the message say **"word count appears to exceed"** rather than
   "exceeds" when extraction/classification confidence is uncertain (e.g.
   degree type is `"unknown"`, or the abstract may span multiple pages)?
6. What exact **student-facing remediation** should be used once the limits
   (and any confidence caveats) are settled?

### Implementation guardrails

- **Do not** change the `PHD_WORD_LIMIT` / `MS_WORD_LIMIT` constants until
  the policy is confirmed.
- **Do not** change P021 detector behavior without a golden-output
  comparison (before/after finding counts on the canonical evaluation set).
- If document type cannot be determined confidently, **do not overstate**
  the result in student-facing wording.
- Any implementation should **preserve existing issue IDs and report
  schema** unless separately reviewed.

---

## P026 — Font policy question

### Current repo/catalog wording

From `data/processed/rules/project_added_rules.json` (`id: "P026"`):

- **Question:** "Does the body text use Times New Roman 12pt (or an
  accepted equivalent)?"
- **Remediation:** "Word users: set body text to Times New Roman or Arial
  at 12pt. Overleaf/LaTeX users: Computer Modern or Latin Modern are
  accepted body fonts."
- **`web_app.py` `_RULE_TEXT_OVERRIDES["P026"]`** carries a longer
  `rule_definition` and a shorter `remediation` that both already mention
  Times New Roman, Arial, Computer Modern, and Latin Modern — this override
  is reasonably aligned with Ester's stated accepted list already.

### Current detector accepted-font behavior

Found in `src/njit_auditor/rules/pdf_font_compliance.py`:

- Font size: accepted range is **11.0–13.0pt** (12pt ± 1pt tolerance).
- Accepted font families (no warning) include, beyond the three Ester
  names:
  - **Times New Roman** and near-equivalent serifs: NimbusRomNo9L, TeX Gyre
    Termes, Liberation Serif, FreeSerif, STIX / STIX General
  - **Arial**
  - **Computer Modern** (CMR/CMBX/CMTI/CMSL/CMB, "computermodern",
    "cmroman")
  - **Latin Modern** (LMRoman/LMBX/LMTTI, "latinmodern",
    "latinmodernroman") — *not* one of Ester's three named families
  - Embedded subset variants (e.g. `ABCDEF+TimesNewRomanPSMT`,
    `ABCDEE+CMR10`) are normalized before classification
  - Math/symbol fonts (CMMI, CMSY, CMEX, MSAM, MSBM, WASY, Symbol,
    ZapfDingbats) are skipped entirely, not classified as body text
- A warning only fires when **both** the violation count is ≥5 **and** the
  violation fraction is ≥50% of body candidate spans on a page (a
  majority-of-page rule, not a single-span rule).
- Named front-matter pages, TOC/list pages, references pages, margins,
  headings, captions, bullets, and short/low-alpha-density lines are all
  excluded from body-span sampling — this is the existing table/figure and
  caption exemption in practice (captions are matched and skipped via
  `_CAPTION_PREFIX_RE`; genuine table/figure body content inside a
  table/figure environment is not separately sampled as "body text").

### Ester spreadsheet / source-of-truth statement

From [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md):

> Accepted font families: **Times New Roman, Arial, and Computer Modern
> Typeface family**. Font size **12 pt** except text in tables and figures.

### The Overleaf/LaTeX practical issue

LaTeX/Overleaf documents very commonly compile with **Latin Modern**
(Overleaf's default modern replacement for Computer Modern) rather than
literal Computer Modern, and the embedded PDF font names for both families
vary by distribution/engine (e.g. `LMRoman10-Regular` vs `CMR10` vs a
subsetted `ABCDEF+LMRoman10-Regular`). The detector already treats Latin
Modern as accepted alongside Computer Modern for exactly this reason, but
Ester's stated list only names "Computer Modern Typeface family."

### Discrepancy

| | Current repo/detector | Ester sheet |
|---|---|---|
| Named accepted families | Times New Roman, Arial, Computer Modern, **Latin Modern**, plus several near-equivalent serif aliases | Times New Roman, Arial, Computer Modern Typeface family |
| Table/figure exemption | Implicit (via caption/heading/short-line exclusion, not an explicit "is this inside a table/figure" check) | Explicit: "except text in tables and figures" |

The practical detector behavior (accepting Latin Modern and several serif
aliases) is almost certainly *more* permissive than what Ester's sheet
literally lists, which lowers false-positive risk for LaTeX users but is a
policy expansion beyond the stated three families that has not been
explicitly confirmed.

### Review questions

1. Should the auditor accept **Times New Roman, Arial, and the Computer
   Modern Typeface family** as valid fonts, per Ester's sheet?
2. Should **Computer Modern variants embedded under different PDF font
   names** (including Latin Modern and the near-equivalent serif aliases
   the detector currently accepts) continue to be accepted, or should the
   family list be tightened to exactly what Ester named?
3. Should font warnings be **strict errors, warnings, or manual-review
   items**?
4. Should **tables and figures be exempt** from the 12pt / main-font
   requirement, as Ester's sheet states explicitly — and if so, should that
   exemption be made an explicit table/figure-region check rather than the
   current implicit caption/heading/short-line exclusion?
5. Should **nonstandard but visually equivalent fonts** be flagged, or
   silently accepted the way near-equivalent serif aliases are today?
6. What exact **student-facing remediation** should be used once the
   accepted-family list (and table/figure exemption scope) are settled?

### Implementation guardrails

- **Do not** change P026 accepted-font detection until policy is confirmed.
- **Do not** add broad font-name aliases without tests.
- **Do not** change table/figure exemptions without review.
- Any future P026 change needs **focused fixtures** covering Times New
  Roman, Arial, Computer Modern, and common PDF embedded-name variants
  (including Latin Modern and subsetted names) before merge.

---

## Proposed message to Ester

*(Draft only — not sent. Place here for later use.)*

> Hi Ester — before we tighten a couple of the automated warnings, I want
> to confirm two policy points against your feedback sheet:
>
> 1. **Abstract word count** — our current tool flags PhD abstracts over
>    350 words and MS abstracts over 150 words. Your sheet says PhD ≤400
>    and MS ≤200. Can you confirm 400/200 are the correct current limits,
>    and let me know if these apply to every NJIT program or only some?
> 2. **Body font** — our tool currently accepts Times New Roman, Arial,
>    Computer Modern, *and* Latin Modern (Overleaf's default), since Latin
>    Modern is extremely common for LaTeX submissions. Your sheet lists
>    Times New Roman, Arial, and "Computer Modern Typeface family." Should
>    Latin Modern (and other Computer-Modern-family variants under
>    different embedded PDF font names) be explicitly accepted too, or
>    should we only accept the three families you named?
> 3. Should text inside **tables and figures stay exempt** from the normal
>    body-font/size rule, matching your sheet?
> 4. For both of these, should a violation be a **strict warning** (as
>    today) or a **manual-review** item, given that degree-type inference
>    and font-name matching are both heuristic?
>
> Once I have your answer I'll update the tool's limits/accepted list in
> one small, tested change and let you know.

---

## Non-goals

- This PR does **not** change P021.
- This PR does **not** change P026.
- This PR does **not** change detector constants.
- This PR does **not** change detector logic.
- This PR does **not** change website wording.
- This PR does **not** change tests.
- This PR does **not** change templates.
- This PR does **not** implement broad presentation splits.
