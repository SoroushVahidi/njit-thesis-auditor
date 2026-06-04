# Q-Rule Coverage Audit After P044

- **Date:** 2026-06-03
- **Auditor scope:** P001–P044 implemented
- **Inventory:** `data/processed/rules/njit_rule_inventory.json` (updated during this audit)
- **Baseline main:** `5edabf9` (PR #122)

---

## Executive Summary

After implementing P001–P044, this audit maps every Q001–Q079 guideline requirement to its
true coverage status. The raw `implementation_status` in `njit_rule_inventory.json` was
significantly stale: 40 Q-rules marked `not_implemented` were actually receiving heuristic
coverage from existing P-rules. The inventory has been updated to reflect this.

| Status | Count | Notes |
|--------|------:|-------|
| `implemented` | 2 | Q004, Q005 (TeX abstract language/pronoun checks) |
| `partially_implemented` | 51 | Heuristic coverage by one or more P-rules; gaps remain |
| `not_implemented` | 26 | 9 manual/semantic; 17 automatable gaps |
| **Total** | **79** | |

**17 automatable Q-rule gaps remain.** Most are visual formatting details (column alignment,
centering, italic) with medium-to-high false-positive risk; some are biographical/acknowledgements
content checks with semantic/privacy constraints.

**Recommendation:** P045 should target the highest-value low-FP automatable gap. The leading
candidates are Dedication text centering/italic (Q033/Q034 — high FP risk), biographical
sketch hanging indent in publications (Q029 — medium FP), or a refine/extend existing P-rule.

---

## Q001–Q079 Coverage Table

### Legend

- **impl** = implemented
- **partial** = partially_implemented
- **auto** = not_implemented, automatable
- **manual** = not_implemented, manual/semantic only

| Q-ID | Short requirement | Status | Covering P-rule(s) | Remaining gap | Next action |
|------|-------------------|--------|-------------------|---------------|-------------|
| Q001 | Abstract: no visible page number | partial | P022 | Heading-detection dependent | No action |
| Q002 | Abstract: first para flush-left | partial | P044 | Short/single-para abstracts below gate | No action |
| Q003 | Abstract: subsequent paras indented | partial | P044 | Gate skips single-para abstracts | No action |
| Q004 | Abstract: no forbidden words | **impl** | TeX checks | — | No action |
| Q005 | Abstract: no first-person pronouns | **impl** | TeX checks | — | No action |
| Q006 | Title page: valid graduation month | partial | P025 (latex_metadata) | Month check in TeX; not PDF | No action |
| Q007 | Title page: institutional identity | **manual** | — | Content semantic check | Manual review |
| Q008 | Title page: no page number | partial | P022 | Heading-detection dependent | No action |
| Q009 | Copyright: no top-margin header | partial | P034 | Medium confidence; may miss flattened PDFs | No action |
| Q010 | Copyright: year matches title page | partial | P034 | Year extraction heuristic; may miss compressed | No action |
| Q011 | Copyright: author matches title page | partial | P034 | Hash-based; middle-initial tolerance | No action |
| Q012 | Copyright: no page number | partial | P022 | Copyright page detection dependent | No action |
| Q013 | Approval Page: exact "APPROVAL PAGE" phrase | partial | P038 | Phrase-variant tolerance; flattened PDF gate | No action |
| Q014 | Approval Page: no page number | partial | P022 | Detection dependent | No action |
| Q015 | Committee: honorifics (Dr., etc.) | **manual** | — | Content/privacy | Manual review |
| Q016 | Committee: advisor listed first | **manual** | — | Content/privacy | Manual review |
| Q017 | Committee: descending rank order | **manual** | — | Content/privacy | Manual review |
| Q018 | Committee: same-rank alphabetical | **manual** | — | Content/privacy | Manual review |
| Q019 | Committee: non-NJIT members after NJIT | **manual** | — | Content/privacy | Manual review |
| Q020 | Committee: non-NJIT includes institution | **manual** | — | Content/privacy | Manual review |
| Q021 | Bio Sketch: exact "BIOGRAPHICAL SKETCH" phrase | partial | P038 | Phrase-variant tolerance | No action |
| Q022 | Bio Sketch: correct Roman numeral page | partial | P037 | Section-anchor detection; flattened PDF gate | No action |
| Q023 | Bio Sketch: no birthplace/date | **auto** | — | High privacy risk; NLP needed for reliability | Defer |
| Q024 | Bio Sketch: no work experience | **auto** | — | High privacy risk; NLP needed | Defer |
| Q025 | Bio Sketch: degrees most-recent-first | **auto** | — | Date parsing; moderate FP risk | Defer |
| Q026 | Bio Sketch: bullet items single-spaced | **auto** | — | Spacing pattern; medium FP risk | Consider P045 |
| Q027 | Bio Sketch: publications most-recent-first | **manual** | — | Date semantic; privacy | Manual review |
| Q028 | Bio Sketch: publications single-spaced + blank line | **auto** | — | Spacing pattern in bio section; medium FP | Consider P045 |
| Q029 | Bio Sketch: publications hanging indent | **auto** | — | Indentation pattern in bio section; medium FP | Consider P045 |
| Q030 | Bio Sketch: consistent citation style | **manual** | — | Citation format semantic | Manual review |
| Q031 | Dedication: correct Roman numeral page | partial | P037 | Detection dependent on heading presence | No action |
| Q032 | Dedication: no top-margin header | partial | P041 | Detection dependent on DEDICATION heading | No action |
| Q033 | Dedication: text block centered | **auto** | — | High FP (no centering signal in text layer) | Low priority |
| Q034 | Dedication: text italicized | **auto** | — | High FP (italic metadata unreliable in many PDFs) | Low priority |
| Q035 | Acknowledgements: correct Roman numeral page | partial | P037 | Detection dependent | No action |
| Q036 | Acknowledgements: exact heading phrase | partial | P038 | Variant spelling tolerance | No action |
| Q037 | Ack: first para thanks advisor | **manual** | — | Semantic/privacy | Manual review |
| Q038 | Ack: second para thanks committee | **manual** | — | Semantic/privacy | Manual review |
| Q039 | Ack: third para mentions tech/financial support | **auto** | — | Semantic keyword heuristic; high FP/privacy risk | Defer |
| Q040 | Ack: grant support includes agency/number | **auto** | — | High FP/privacy risk | Defer |
| Q041 | Ack: fifth para thanks peers | **auto** | — | High FP/privacy risk | Defer |
| Q042 | Ack: sixth para mentions family | **auto** | — | High FP/privacy risk | Defer |
| Q043 | Ack: full name for all named persons | **auto** | — | NLP needed; high privacy risk | Defer |
| Q044 | Ack: first para flush-left | partial | P043 | INDENT_THRESHOLD_PT=18pt; flattened PDF gate | No action |
| Q045 | Ack: subsequent paras indented | partial | P043 | Gate skips <2 paragraph blocks | No action |
| Q046 | TOC: correct Roman numeral continuation | partial | P037 | TOC page detection dependent | No action |
| Q047 | TOC: exact heading on first page | partial | P038 | Phrase-variant detection | No action |
| Q048 | TOC: "(Continued)" on continuation pages | partial | P030 | Variant heading detection; single-page TOCs exempt | No action |
| Q049 | TOC: L1 entries all-caps | partial | P024 | Text-layer rendering quality dependent | No action |
| Q050 | TOC: L2 entries title case | partial | P024 | APA title-case tolerance; FP risk on acronyms | No action |
| Q051 | TOC: L3 entries sentence case | partial | P027 | Conservative; checks identified L3 entries only | No action |
| Q052 | TOC/List: consistent leader style | partial | P018 | `inconsistent_leader_dots`; detects mixed usage | No action |
| Q053 | TOC: wrapped L1 entries single-spaced | partial | P032 | Conservative gap detection | No action |
| Q054 | TOC: wrapped L2 entries single-spaced | partial | P032 | Conservative gap detection | No action |
| Q055 | TOC: wrapped L3 entries single-spaced | partial | P032 | Conservative gap detection | No action |
| Q056 | TOC: L2/L3 indented to show hierarchy | partial | P039 | Gate ≥2 child entries; conservative tolerance | No action |
| Q057 | TOC: double spacing between section entries | partial | P036 | Visual double-spacing check; conservative threshold | No action |
| Q058 | TOC: single appendix = APPENDIX + title | partial | P042 | TOC-only; appendix detection heuristic | No action |
| Q059 | TOC: multiple appendices = letters (A, B…) | partial | P042 | TOC-only | No action |
| Q060 | LoT: correct Roman numeral continuation | partial | P037 | LoT page detection dependent | No action |
| Q061 | LoT: exact heading on first page | partial | P038 | Phrase-variant detection | No action |
| Q062 | LoT: "(Continued)" on continuation pages | partial | P030 | Variant detection | No action |
| Q063 | LoT: "Table" label left-aligned | partial | P031 | Presence and approximate alignment; bold not verified | No action |
| Q064 | LoT: "Page" label right-aligned | partial | P031 | Presence and approximate alignment; bold not verified | No action |
| Q065 | LoT: titles title case, no terminal period | partial | P024 | APA title-case and period checks | No action |
| Q066 | LoT: wrapped table titles single-spaced | partial | P032 | Conservative gap detection | No action |
| Q067 | LoT: double spacing between table entries | partial | P036 | Visual double-spacing check | No action |
| Q068 | LoT: table numbers left-column aligned | **auto** | P018 (partial) | No specific left-column number alignment check | Consider |
| Q069 | LoT: page numbers right-column aligned | partial | P018 | `misaligned_page_number_column` check | No action |
| Q070 | LoF: exact heading on first page | partial | P038 | Phrase-variant detection | No action |
| Q071 | LoF: "(Continued)" on continuation pages | partial | P030 | Variant detection | No action |
| Q072 | LoF: "Figure" label left-aligned | partial | P031 | Presence and approximate alignment | No action |
| Q073 | LoF: "Page" label right-aligned | partial | P031 | Presence and approximate alignment | No action |
| Q074 | LoF: descriptions sentence case | partial | P024 | `list_of_figures_sentence_case`; conservative | No action |
| Q075 | LoF: terminal punctuation on descriptions | partial | P040 | Wrap-continuation and short-line gates | No action |
| Q076 | LoF: wrapped descriptions single-spaced | partial | P032 | Conservative gap detection | No action |
| Q077 | LoF: double spacing between figure entries | partial | P036 | Visual double-spacing check | No action |
| Q078 | LoF: figure numbers left-column aligned | **auto** | P018 (partial) | No specific left-column number alignment check | Consider |
| Q079 | LoF: page numbers right-column aligned | partial | P018 | `misaligned_page_number_column` check | No action |

---

## Remaining Automatable Gaps (17 Q-rules not yet implemented)

### High false-positive risk — defer

| Q-rule | Requirement | FP risk | Why deferred |
|--------|-------------|---------|--------------|
| Q033 | Dedication text block centered | **High** | No centering signal in PDF text layer; would require image analysis |
| Q034 | Dedication text italicized | **High** | Italic metadata unreliable in many PDFs; systematic false negatives |
| Q039 | Ack third para mentions support | **High** | Semantic keyword heuristic; privacy risk (content reading) |
| Q040 | Ack grant support includes agency/number | **High** | Same as Q039 |
| Q041 | Ack fifth para thanks peers | **High** | Semantic; high FP; privacy risk |
| Q042 | Ack sixth para mentions family | **High** | Semantic; high FP; privacy risk |
| Q043 | Ack full name for all named persons | **High** | NLP required; privacy (names in findings) |

### Medium false-positive risk — consider for P045

| Q-rule | Requirement | FP risk | Notes |
|--------|-------------|---------|-------|
| Q026 | Bio sketch bullet items single-spaced | Medium | Spacing pattern; requires bio section detection |
| Q028 | Bio sketch publications single-spaced + blank line | Medium | Entry-level spacing; bio section scope |
| Q029 | Bio sketch publications hanging indent | Medium | Indentation pattern; bio section; builds on P043/P044 |
| Q068 | LoT table numbers left-column aligned | Medium | X0 variance check across LoT entries; extends P018 |
| Q078 | LoF figure numbers left-column aligned | Medium | X0 variance check across LoF entries; extends P018 |

### Content/privacy/semantic — defer or manual review

| Q-rule | Requirement | Why |
|--------|-------------|-----|
| Q023 | Bio sketch: no birthplace/date | Content reading; high privacy risk |
| Q024 | Bio sketch: no work experience | Content reading; high privacy risk |
| Q025 | Bio sketch: degrees most-recent-first | Date parsing; ordering semantic |

### Manual/semantic only (9 Q-rules)

Q007, Q015, Q016, Q017, Q018, Q019, Q020, Q037, Q038 — committee and advisor content
checks, rank ordering, institutional affiliations. These require human review of dissertation
content and must not be automated (high privacy risk; no reliable heuristic without reading
private content).

---

## Recommended Implementation Order for Remaining Automatable Q-Rules

### Tier 1 — Medium risk, new coverage value

1. **Q029 — Bio sketch publications hanging indent**
   - Extends P043/P044 indentation pattern to the Publications section of the Bio Sketch
   - Moderate FP risk; gate: skip if Bio Sketch section not detected
   - Privacy: geometry metadata only (x0 positions), no text content
   - Candidate for P045

2. **Q068/Q078 — Table/Figure number left-column alignment**
   - Extends P018's alignment checking to the entry-number column
   - X0 variance check across LoT/LoF entry prefixes
   - Candidate for a single P-rule covering both

3. **Q026 — Bio sketch bullet items single-spaced**
   - Spacing heuristic within bio sketch bullet blocks
   - Moderate FP risk if bullet detection is imprecise

4. **Q028 — Bio sketch publications single-spaced + blank line between**
   - Spacing pattern in publications list
   - Could pair with Q029 in the same P-rule

### Tier 2 — High FP risk, defer

Q023–Q025 (content/privacy), Q033–Q034 (visual/italic), Q039–Q043 (semantic/privacy)

---

## P045 Recommendation

**Recommended P045 scope: Bio Sketch paragraph layout check (Q026/Q028/Q029)**

- Scope the Bio Sketch page via `find_named_frontmatter_headings` (BIOGRAPHICAL SKETCH is
  in EXPECTED_HEADINGS)
- Check the Publications/Presentations section for hanging indent (Q029) and inter-entry
  spacing (Q028)
- Optionally check bullet single-spacing (Q026)
- Privacy-safe: geometry metadata only; no bio text content
- Builds on P043/P044 pattern (heading detection → paragraph/section extraction → geometry check)
- Low implementation risk; 2–3 Q-rule coverage at once

**Alternative P045:** TOC/LoT/LoF column number alignment (Q068/Q078) — extends P018 with
left-column alignment checks for table/figure number prefixes. Simpler scope but covers only
2 Q-rules.

**If data is the priority:** Mount the Sebastian Fine ZIP to extract all five evaluation
PDFs, then run a canonical P001–P044 five-PDF audit before adding more P-rules.

---

## Data/Evaluation Blocker Note

The five-PDF canonical aggregate (1,446 findings) was established before P035. P035–P044
have no canonical finding counts yet. The Sebastian Fine Revised PDF is ZIP-only, blocking
a canonical five-PDF rerun. A canonical run would clarify:
- Whether any of the new P-rules (P035–P044) produce findings on real data
- Whether any rules over-fire on clean dissertations

---

## Privacy Notes

- All Q-rule coverage descriptions in this doc use rule IDs, P-rule IDs, categories, and
  aggregate descriptions only.
- No dissertation body text, abstract text, author names, committee names, annotation
  contents, captions, TOC entry text, LoF entry text, or private student content was quoted.
- The 9 manual Q-rules are explicitly excluded from automation because they require reading
  private student content.

## Generated-Output Safety Notes

- No generated audit outputs (`data/evaluation/generated/`) were produced during this audit.
- `generated_for_commit` remains `00b9c2d`.
- Generated outputs remain gitignored.
