# P064 — References/Citations Structural Check: Scope and Design

> **Implemented in PR #228** (2026-06-08).  Scope history preserved below.
> Module: `src/njit_auditor/rules/pdf_references_citations_structural.py`
> Tests: `tests/test_p064_references_citations_structural.py` (21 tests)
> Synthetic validation: `docs/evaluation/p064_references_citations_structural_synthetic_validation.md`

- **Rule name:** P064 — References/Citations Structural Check
- **Date:** 2026-06-08
- **Baseline commit:** `8cd9abd`
- **Status:** IMPLEMENTED (PR #228) — was SCOPED ONLY
- **Validation baseline:** 889 tests (ruff clean; mypy no issues); post-implementation: 910 tests

---

## 1. Motivation

### EF overlap gap

The EF comment-vs-tool overlap analysis (refreshed after P063; see
`docs/evaluation/ef_overlap_after_p063_evaluation.md`) shows:

- **9 EF annotation objects** in the `references_citations` category across the two
  extractable-comment PDFs (Cibaku Elson 1st Review: 5; Yin Haotian 2nd Review: 4).
- **0 tool findings** in this category at both the P029 era and the P063 era.
- No dedicated P-rule has ever addressed the references/bibliography section.

After eliminating `unclear_or_other` (88 EF comments; semantic/editorial; permanently
out of scope for deterministic rules) and `committee_approval_page` (5 EF comments;
mostly semantic committee-rank checks), `references_citations` is the **highest-priority
automatable EF miss category** remaining.

### Why a conservative scope is required

The NJIT guidelines explicitly state that reference formatting style is advisor- and
discipline-dependent (see Section 3 below). APA, IEEE, ACM, and other citation styles are
all valid; the style choice is made in consultation with the advisor. Automating
style-specific compliance (author ordering, date placement, journal abbreviation) would
produce unacceptable false-positive rates across a diverse dissertation set. A conservative
v1 must restrict itself to structural signals that are invariant across citation styles.

---

## 2. Guideline/Q-Rule Basis

### Source files consulted

| File | Location |
|---|---|
| Self-Assessment Sheet | `data/raw/guidelines/Self-Self Assessment Sheet.pdf` |
| Thesis and Dissertation Formatting Guidelines (WIP) | `data/raw/guidelines/Thesis and Dissertation Formatting Guidelines (WIP).docx` |
| Front Matter Pages Lorem Ipsum | `data/raw/guidelines/Front Matter Pages Lorem Ipsum.pdf` |
| NJIT rule inventory | `data/processed/rules/njit_rule_inventory.json` |

### Guideline findings

**Self-Assessment Sheet (page 4, References section):**

- "The references are consistently formatted and follow a style that is agreed upon with
  your advisor."
- "The style of my references is: _____________________________ [fill-in-blank]"
- "After importing your references from Zotero, EndNote or any other citation management
  software I revised them for consistency."

Interpretation: The guidelines require a references section to exist and to be internally
consistent, but explicitly leave the specific citation style to the advisor.

**Thesis and Dissertation Formatting Guidelines (WIP), para 138–143:**

- Section heading "References" in the document body.
- "Select the style based on your discipline."
- No specific formatting requirements for hanging indent or spacing are stated explicitly,
  beyond the general citation management software recommendation.

**Thesis and Dissertation Formatting Guidelines (WIP), para 69:**

- "The page numbers should continue sequentially from the first page of your text through
  the last page of your references."

Interpretation: References are part of the body page-number sequence (Arabic numerals),
not separate end matter. This confirms references appear after the body chapters and share
body pagination.

**Front Matter Pages Lorem Ipsum (page 9, TOC example):**

- REFERENCES appears as the last TOC entry before the document ends, at the same level
  as chapters and appendices.
- Formatted as "REFERENCES. ...... 60" in the sample TOC, indicating the heading should
  appear in all-caps at the body section level.

**Self-Assessment Sheet (page 2, Biographical Sketch):**

- "The presentations and publications listed on this page follow the same style used in
  the Reference section."
- This cross-reference confirms the References section is the canonical citation style
  anchor for the document.

**Q-rules in njit_rule_inventory.json:**

No Q-rules in the inventory (Q001–Q079) directly address the references/bibliography
section. The closest Q-rules are in the Biographical Sketch section:
- Q028: Bio Sketch "Publications and Presentations" entries single-spaced with blank line
  between entries — partially implemented by P045.
- Q029: Bio Sketch entries use a hanging indent — partially implemented by P045.
- Q030: Bio Sketch entries follow one consistent citation pattern — not implemented;
  manual/style-dependent.

The analogy to Q028/Q029 in the References section is the structural basis for P064's
hanging-indent and inter-entry spacing checks: if hanging indent is required for Bio
Sketch publication entries, it is reasonable to check for the same structural pattern
in the main References section. However, no Q-rule explicitly codifies this for the
References section, so the automatable evidence is indirect.

### Q-rule and guideline basis summary

| Requirement | Source | Automatable in v1? |
|---|---|---|
| References section must exist (heading present) | Self-Assessment Sheet p.4; Front Matter Lorem Ipsum p.9 (REFERENCES in TOC); Guidelines para 138 | Yes — automatable in v1 |
| Citation style is advisor/discipline-dependent | Self-Assessment Sheet p.4 (explicit fill-in-blank) | Out of scope — manual/style-dependent |
| Entries must be internally consistent | Self-Assessment Sheet p.4 ("consistently formatted") | Partially automatable (hanging-indent geometry only) |
| Hanging indent for citation entries | Self-Assessment Sheet p.4 bio-sketch/references cross-reference; Q028/Q029 analogy | Automatable in v1 (geometry only) |
| Inter-entry spacing consistency | Q028 analogy (Bio Sketch single-spaced with blank line between) | Automatable in v1 (geometry only) |
| Page-number sequence continues through references | Guidelines para 69 | Already covered by P013/P019/P028 — not duplicated in P064 |
| Placement after body/appendices | Front Matter Lorem Ipsum TOC structure | Deferred — needs more Q-rule evidence and reliable body-end detection |
| Content of references (author names, dates, etc.) | Out of scope — requires semantic parsing | Out of scope |
| BibTeX/TeX citation consistency | Out of scope — TeX-layer check only | Deferred |

---

## 3. P064 v1 Scope

### What P064 WILL check (conservative v1)

1. **`references_section_heading_not_detected`** — No REFERENCES, BIBLIOGRAPHY, WORKS
   CITED, or LITERATURE CITED heading is found in the document body pages. A dissertation
   must have a references section; its absence is a structural error.

2. **`references_entry_indentation_inconsistent`** — Within the detected references
   section page range, the majority of multi-line reference entries do not exhibit a
   consistent hanging-indent pattern (first line at one x-offset, continuation lines
   indented further right — or the reverse). This is checked only if at least three
   multi-line entry candidates are found and if the text layer provides reliable
   x-coordinate data.

3. **`references_entry_spacing_inconsistent`** — Within the detected references section,
   inter-entry vertical gaps are highly irregular (some entries have no gap between them
   while others have large gaps), suggesting inconsistent spacing. This is checked only
   if at least five entry candidates are found.

### What P064 will NOT check

- Citation style compliance (APA / IEEE / ACM / MLA / Chicago) — advisor/discipline-
  dependent; explicitly left open by the guidelines; would produce unacceptable false
  positives.
- Reference entry content: author names, journal titles, year placement, volume/issue
  notation, DOI/URL format.
- In-text citation markers (numbers, author-year) — body text parsing; out of scope.
- Completeness: every in-text citation has a corresponding reference entry — requires
  full cross-document semantic parsing.
- BibTeX/TeX source citation checking (e.g., @article missing fields) — deferred to a
  future TeX-layer rule.
- References placement relative to appendices — deferred; requires reliable detection
  of both the references section and the last appendix page, and stronger Q-rule
  evidence for the ordering constraint.
- Capitalization of the REFERENCES heading beyond detecting it — P014 covers heading
  style (bold/all-caps/centered) for named headings; if the references heading were
  added to P014's heading list that could extend coverage, but P064 v1 focuses only on
  presence.
- Number of references — no guideline specifies a minimum; deferred.

### Input type

PDF text layer only for v1. No OCR, no image analysis, no external API calls.

---

## 4. Detection Algorithm

### 4a. Detect the references section heading

Scan all body pages (pages at or after the body-start page as detected by the existing
`_find_body_start_page` pattern used in P063) for a line that:

- Matches one of the accepted heading keywords in any case:
  `REFERENCES`, `BIBLIOGRAPHY`, `WORKS CITED`, `LITERATURE CITED`
- Is a short line (fewer than 60 characters after stripping) — to avoid matching
  "see references" in body text.
- Appears as a standalone line or near the top of a text block — to distinguish heading
  from body prose.
- Is reasonably centered or left-aligned (not indented as a reference entry itself).

Accepted heading keywords (case-insensitive, strip trailing punctuation):
`REFERENCES`, `BIBLIOGRAPHY`, `WORKS CITED`, `LITERATURE CITED`

If no heading is found anywhere in the body pages, emit
`references_section_heading_not_detected` and return (no sub-checks run).

### 4b. Infer the references section page range

Once the heading page is found:

- Start page: the page where the heading appears.
- End page: the next page where a major structural heading is detected
  (another all-caps section heading such as an appendix, a chapter, or the final page
  of the document), whichever comes first.
- If the heading appears on the last body page, the section consists of that single page.

### 4c. Extract reference entry candidates

Within the references section page range, identify candidate reference entries using
a line-grouping heuristic:

- A "first line" is a line that begins at the dominant left-margin x-coordinate (or
  slightly to the right if a hanging indent is present) and is preceded by a vertical
  gap larger than the median within-entry gap.
- A "continuation line" is a line that follows a first line with a small vertical gap
  and whose x-start is indented further right than the first line (for standard hanging
  indent) or further left (for reverse hanging indent).
- Skip lines that appear to be the section heading itself.
- Skip lines shorter than 20 characters (likely wrap artifacts or page numbers).

### 4d. Hanging-indent metric

For each multi-line entry candidate (first line + at least one continuation line):

- Record `first_line_x`: the x-coordinate of the start of the first line.
- Record `continuation_line_x`: the median x-coordinate of all continuation lines.
- Compute `indent_delta = continuation_line_x - first_line_x`.

Across all multi-line candidates:

- If the majority of entries have a consistent non-zero `indent_delta` in the same
  direction (positive = continuation lines indented right = standard hanging indent),
  the section is consistent — no finding.
- If `indent_delta` varies widely (standard deviation > threshold, e.g., > 10pt) or
  if some entries are indented and others are not, emit
  `references_entry_indentation_inconsistent`.
- Gate: require at least 3 multi-line entry candidates before checking. If fewer, skip.

### 4e. Inter-entry spacing metric

Collect all inter-entry vertical gaps (gap between the last continuation/first line of
one entry and the first line of the next entry) across the references section:

- Compute median inter-entry gap.
- Compute outlier count: entries whose gap is more than 2× the median (indicating
  a double-space break where single-space is expected, or vice versa).
- If the outlier count exceeds 20% of total entries and the absolute gap range exceeds
  a threshold (e.g., 15pt from median to max outlier), emit
  `references_entry_spacing_inconsistent`.
- Gate: require at least 5 entry candidates before checking.

### 4f. Confidence scoring and conservative skip conditions

Each sub-check emits a `confidence` field (`low` / `medium` / `high`) reflecting:

- `high`: clear heading detected, section spans multiple pages, many comparable entries,
  clean x-coordinate geometry.
- `medium`: heading detected, section spans 1–2 pages, 3–5 entries, geometry marginally
  reliable.
- `low`: heading detected but section is very short, or fewer entries than ideal, or
  x-coordinate variance is high from PDF extraction artifacts.

Low-confidence findings are emitted with `triage_tier: low` rather than suppressed
entirely, so reviewers can decide.

### 4g. Avoiding false positives on body in-text citations

In-text citations (e.g., "[1]", "(Author, 2023)") are short, appear inline within
body paragraphs, and do not form multi-line grouped blocks. The entry-candidate
extraction heuristic (grouping based on inter-line gaps and minimum line length)
naturally excludes in-text citations because they are embedded in prose paragraphs
rather than isolated at the left margin.

### 4h. Privacy: no reference text in findings

Findings must never include reference entry text, author names, journal titles, DOI
strings, URLs, or any citation content. All finding fields are geometric/structural
metadata only (page numbers, x-coordinates, counts, gap values, confidence). This is
consistent with the privacy model used across all existing P-rules.

---

## 5. Issue Types (privacy-safe)

Only types justified by the v1 scope:

| Issue type | Condition | Severity |
|---|---|---|
| `references_section_heading_not_detected` | No REFERENCES / BIBLIOGRAPHY / WORKS CITED / LITERATURE CITED heading found in body pages | WARNING |
| `references_entry_indentation_inconsistent` | Heading detected; inconsistent hanging-indent pattern across multi-line entries | WARNING |
| `references_entry_spacing_inconsistent` | Heading detected; irregular inter-entry vertical spacing across entry candidates | WARNING |

---

## 6. Finding Fields (privacy-safe only)

### Fields that MUST be included

| Field | Description |
|---|---|
| `issue_type` | One of the three issue types above |
| `page_number` | Page where the references heading was detected (or first references page) |
| `section_page_count` | Number of pages spanned by the detected references section |
| `entry_candidate_count` | Number of reference entry candidates identified in the section |
| `affected_entry_count` | Number of entries contributing to the flagged inconsistency (spacing/indent checks) |
| `median_indent_px` | Median `indent_delta` across all multi-line entry candidates (geometry metric) |
| `first_line_x` | Median x-start of first lines across entry candidates |
| `continuation_line_x` | Median x-start of continuation lines across entry candidates |
| `median_gap` | Median inter-entry vertical gap (points) |
| `gap_outlier_count` | Count of entries whose gap exceeds 2× median |
| `confidence` | `low` / `medium` / `high` |
| `triage_tier` | `low` / `medium` / `high` |
| `source_q_rule_ids` | Comma-separated IDs of relevant Q-rules (e.g., `Q028,Q029`) or `none` for heading check |

### Fields that MUST be EXCLUDED

The following fields must never appear in P064 findings:

- Reference entry text or any substring thereof
- Citation text (author names, journal names, conference names, book titles)
- Author names (from entries or any other source)
- Article, book, or dissertation titles from the references list
- DOI strings
- URL strings from references
- Labels or ref-keys from any citation management system
- Body text from any other part of the dissertation

---

## 7. Conservative Skip Conditions

P064 must skip (return no findings) under any of the following conditions:

1. **No body pages detected** — body-start page detection (using the same
   `_find_body_start_page` pattern as P063) fails entirely.
2. **No clear references heading detected** — none of the accepted heading keywords
   found in body pages; emit `references_section_heading_not_detected` instead of
   sub-checks, then return.
3. **Fewer than 3 reference entry candidates** — insufficient data to assess
   indentation consistency.
4. **Fewer than 5 reference entry candidates** — insufficient data to assess spacing
   consistency (higher threshold than for indentation because spacing patterns require
   more data points).
5. **Image-only or flattened pages** — PDF text layer returns no text blocks on
   references section pages; skip silently.
6. **Inconsistent text-layer geometry** — standard deviation of x-coordinates across
   all lines in the section exceeds a threshold (e.g., > 50pt) suggesting the text layer
   is unreliable (e.g., two-column layout, rotated content, or extraction artifacts from
   a compressed PDF).
7. **References section too short** — fewer than 2 pages and fewer than 5 entry
   candidates (very short reference lists may reflect a clean short thesis rather than
   a formatting problem; skip to avoid false positives).
8. **Mixed column layout detected** — if the page geometry suggests two-column text
   (multiple distinct left-margin clusters), skip to avoid misinterpreting column
   boundaries as indent patterns.

---

## 8. False-Positive and False-Negative Risks

### False-positive risks

| Risk | Mitigation |
|---|---|
| Discipline-specific citation styles produce legitimate non-hanging-indent layouts (e.g., IEEE numbered list with flush-left entries) | Calibrate `indent_delta` threshold conservatively; require a large majority of entries to be inconsistent before flagging; emit `confidence: low` for borderline cases |
| Multi-line entries with long URLs or DOIs cause wrapping that looks like missing continuation indent | URL/DOI patterns are long tokens that may appear on continuation lines; the geometry metric should handle them correctly if x-coordinates are measured from the PDF text layer; the skip condition for high x-variance handles extreme cases |
| PDF extraction artifacts from LaTeX-generated bibliographies (BibTeX/biblatex column alignment, microtype kerning) | Skip condition for high x-coordinate standard deviation; conservative thresholds; `confidence: low` for marginally consistent cases |
| Short dissertations with fewer than 10 references | Skip condition: require at least 5 entry candidates for spacing check, 3 for indentation check |
| Compressed or flattened PDFs with coordinate artifacts | Skip condition: image-only pages and high x-variance |
| Section heading detected in a body chapter (e.g., section titled "Background and References") | Short-line filter for heading detection: require heading line length < 60 chars; require it to be a standalone line rather than a subsection header with numbering prefix |

### False-negative risks

| Risk | Description |
|---|---|
| References heading uses non-standard phrasing (e.g., "LITERATURE") | Only the four standard keywords are checked in v1; unusual headings will cause `references_section_heading_not_detected` even when a section exists |
| Very short reference lists (< 3 entries) | Skip condition means these are never checked for indentation/spacing |
| LaTeX-generated PDFs where BibTeX spacing is consistent across all entries but noncompliant | If all entries are consistently badly formatted in the same way, the variance-based metrics will not flag them (e.g., all entries with zero hanging indent are consistently zero — not inconsistent) — this is an inherent limitation of consistency-only checks |
| References section split across non-consecutive pages (very rare) | Section end-detection heuristic ends at the first subsequent major heading; if a major heading interrupts the section temporarily, the section range may be cut short |

---

## 9. Synthetic Test Plan (minimum 12 tests)

All synthetic PDFs use placeholder text only; no real dissertation content.

| Test | Scenario | Expected outcome |
|---|---|---|
| 1 | PDF with a clear all-caps REFERENCES heading on a body page, followed by consistently hanging-indented entries | No findings |
| 2 | PDF with body pages but no REFERENCES / BIBLIOGRAPHY / WORKS CITED heading anywhere | `references_section_heading_not_detected` |
| 3 | PDF with REFERENCES heading and multi-line entries that consistently have continuation lines indented further right (standard hanging indent) | No `references_entry_indentation_inconsistent` finding |
| 4 | PDF with REFERENCES heading and multi-line entries where continuation lines are at the same x-position as first lines (no hanging indent, no pattern) — enough entries to trigger the gate | `references_entry_indentation_inconsistent` |
| 5 | PDF with REFERENCES heading and mixed entries: some with hanging indent, some without (inconsistent indentation across entries) | `references_entry_indentation_inconsistent` |
| 6 | PDF with REFERENCES heading and consistent uniform inter-entry gaps (e.g., all gaps within 15% of the median) | No `references_entry_spacing_inconsistent` finding |
| 7 | PDF with REFERENCES heading and highly irregular inter-entry gaps (some entries adjacent with zero gap, others with 3× median gap) — at least 5 entries | `references_entry_spacing_inconsistent` |
| 8 | PDF with REFERENCES heading but only 2 reference entry candidates | Rule skips indentation and spacing checks (too few entries); no `indentation_inconsistent` or `spacing_inconsistent` finding; possibly emits no finding at all |
| 9 | PDF where references section pages are image-only (no text layer) | Rule skips; no finding |
| 10 | PDF with in-text citation markers (e.g., "[1]", "[2]") in body paragraphs but REFERENCES heading present and entries properly formatted | Body in-text citation markers not mistaken for reference list entries; no false finding from in-text citations |
| 11 | Privacy test: PDF that triggers `references_entry_indentation_inconsistent` | No finding field contains any reference entry text, author name, journal name, title, DOI, URL, or citation content; all field values are numeric metrics or structural identifiers |
| 12 | Privacy test: REFERENCES heading detected; entry candidates counted | Synthetic placeholder DOI/URL text (e.g., "https://example.org/doi/placeholder") not reproduced in any finding field |
| 13 (bonus) | PDF with BIBLIOGRAPHY heading (not REFERENCES) | Heading detected; no `references_section_heading_not_detected` |
| 14 (bonus) | PDF with WORKS CITED heading | Heading detected; no `references_section_heading_not_detected` |
| 15 (bonus) | PDF with entries that are all single-line (no continuation lines) | Indentation check skips (no multi-line candidates); no false indentation finding |

---

## 10. Current-Dataset Evaluation Plan

After P064 is implemented (in a subsequent PR), the following evaluation steps should
be performed. Evaluation is aggregate-only; no reference entry text, author names, or
citation content is quoted in the evaluation document.

### Evaluation steps

1. Run `njit-audit pdf` with P064 enabled on the five evaluation PDFs
   (four tracked EF-commented PDFs plus Sebastian Fine clean baseline extracted from
   the tracked ZIP).
2. Collect per-file P064 finding counts by issue type.
3. Compare with EF `references_citations` annotation counts (Cibaku: 5, Yin Haotian: 4)
   at the page/category level only.
4. Produce `docs/evaluation/p064_references_structure_current_dataset_evaluation.md`
   with aggregate counts only.

### Expected behavior

P064 is likely to fire on 1–3 of the 5 evaluation PDFs, depending on whether the
references sections in those PDFs have extractable text-layer geometry and whether
any heading or spacing inconsistencies exist. Two of the five PDFs have compressed or
flattened text layers that may trigger the skip conditions (image-only pages or high
x-variance). On the Sebastian Fine clean baseline, P064 should fire 0 findings if the
references section is consistently formatted.

### Privacy constraints for evaluation doc

- Do not quote any reference entry text from real dissertations.
- Do not quote EF annotation text.
- Report counts by file label, rule, and issue type only.
- Page numbers may be reported as counts, not as lists of specific page numbers.
- Generated evaluation JSON/MD outputs must remain under `data/evaluation/generated/`
  (gitignored) and must not be committed.

---

## 11. Implementation Checklist

When P064 is implemented (in a subsequent PR), the following files should be created
or modified:

| Action | Path |
|---|---|
| NEW module | `src/njit_auditor/rules/pdf_references_structure.py` |
| Wire into collect function | `src/njit_auditor/audit_runner.py` — add import and call `check_pdf_references_structure()` in `collect_pdf_layout_findings()`; update `PDF_AUDIT_POST_P054_RULE_IDS` and `PDF_AUDIT_POST_P054_CALLABLE_NAMES` tuples |
| Evaluation category mapping | `src/njit_auditor/evaluation.py` — add `"P064": "references_citations"` to the mapping dict |
| Rule metadata | `data/processed/rules/project_added_rules.json` — add P064 entry with `implementation_status: "implemented"`, correct module path, Q-rule basis |
| Tests | `tests/test_p064_references_structure.py` — at least 12 synthetic tests per the test plan in Section 9 |
| Synthetic validation doc | `docs/evaluation/p064_references_structure_synthetic_validation.md` |
| Status docs update | `docs/status/current_project_state_and_next_steps.md` — add P064 entry |
| Full repository audit update | `docs/status/full_repository_audit_after_p063.md` — note P064 status or link to new full_repository_audit_after_p064.md |
| Current-dataset evaluation doc | `docs/evaluation/p064_references_structure_current_dataset_evaluation.md` — after running evaluation |

### Validation commands (run after implementation)

```
python -m pip install -e ".[dev]"
ruff check .
mypy src
python -m pytest
```

All three must pass with the new test count (889 + ≥12 new = ≥901 pytest).

---

## 12. Recommendation

**YES — P064 is ready for implementation in the next PR.**

The scope is now clearly defined and bounded. The v1 is conservative:

- Only three issue types, all grounded in guideline text and EF comment support.
- Strong skip conditions prevent false positives on short or poorly extractable PDFs.
- Privacy model is explicit and consistent with all existing P-rules.
- Analogy to P045 (Bio Sketch hanging indent / inter-entry spacing) provides an
  implementation template for the detection algorithm.
- 12 synthetic test cases cover the key scenarios.

Implement as: `rules/p064-references-citations-structural-check`

The rule fills the highest-priority EF coverage gap with no risk to current audit
behavior (it is additive only). It does not change any existing finding format, rule
wiring, or test behavior.

---

## Cross-References

- EF overlap after P063: `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- Full repository audit after P063: `docs/status/full_repository_audit_after_p063.md`
- Current project state: `docs/status/current_project_state_and_next_steps.md`
- Q-rule inventory: `data/processed/rules/njit_rule_inventory.json`
- Project-added rules: `data/processed/rules/project_added_rules.json`
- P045 (Bio Sketch publication layout — implementation analogy): `src/njit_auditor/rules/pdf_biosketch_publication_layout.py`
- P063 (most recent rule — style reference): `src/njit_auditor/rules/pdf_appendix_body_headings.py`
- P063 test style reference: `tests/test_p063_appendix_body_headings.py`
- Guideline sources: `data/raw/guidelines/Self-Self Assessment Sheet.pdf`, `data/raw/guidelines/Thesis and Dissertation Formatting Guidelines (WIP).docx`
