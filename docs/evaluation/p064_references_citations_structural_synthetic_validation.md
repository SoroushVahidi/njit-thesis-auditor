# P064 — References/Citations Structural Check: Synthetic Validation

- **Date:** 2026-06-08
- **Rule:** P064 — References/Citations Structural Check
- **Module:** `src/njit_auditor/rules/pdf_references_citations_structural.py`
- **Test file:** `tests/test_p064_references_citations_structural.py`
- **Baseline:** 889 pytest (P001–P063); P064 adds 21 synthetic tests → 910 pytest
- **Status:** Implemented and validated

---

## 1. Rule Purpose and Guideline Basis

P064 checks structural properties of the references/bibliography section of a dissertation
PDF.  It does NOT enforce citation style (APA, IEEE, ACM, MLA, Chicago) — style is
advisor/discipline-dependent per NJIT guidelines.

**Guideline sources consulted:**

| Source | Relevant text |
|---|---|
| Self-Assessment Sheet p.4 | "The references are consistently formatted and follow a style that is agreed upon with your advisor." |
| Formatting Guidelines para 138 | Section heading "References" in the document body. |
| Formatting Guidelines para 69 | Page numbers continue through the last page of references. |
| Front Matter Lorem Ipsum p.9 | REFERENCES in sample TOC at body-section level. |
| Q028/Q029 (Bio Sketch analogy) | Publication entries use hanging indent and inter-entry spacing — analogous structural requirement applied to the main References section. |

No Q-rule in the inventory (Q001–Q079) directly addresses the main references section.
Checks B and C are justified via the Q028/Q029 analogy and the general consistency
requirement in the Self-Assessment Sheet.

---

## 2. Issue Types Implemented

| Issue type | Condition | Severity | Triage tier |
|---|---|---|---|
| `references_section_heading_not_detected` | No REFERENCES, BIBLIOGRAPHY, WORKS CITED, or LITERATURE CITED heading found in body pages of a document with ≥5 body pages | WARNING | medium |
| `references_entry_indentation_inconsistent` | Multi-line reference entries show inconsistent hanging-indent patterns (stdev of indent deltas > 12 pt); gate: ≥5 entries AND ≥3 multi-line entries | WARNING | medium or low |
| `references_entry_spacing_inconsistent` | Inter-entry vertical gaps are highly irregular (≥20% outlier gaps that exceed 2× median AND absolute range from median to max outlier > 15 pt); gate: ≥5 entry candidates | WARNING | medium or low |

---

## 3. Synthetic Test Coverage (21 tests)

| Test | Scenario | Expected result |
|---|---|---|
| 1 | REFERENCES heading on body page, few entries | No heading finding |
| 2 | BIBLIOGRAPHY heading | No heading finding |
| 3 | WORKS CITED heading | No heading finding |
| 4 | No heading, 8 body pages | `references_section_heading_not_detected` |
| 5 | No heading, 3 body pages (short doc) | No finding (skipped) |
| 6 | All entries consistently hanging-indented | No indentation finding |
| 7 | All entries flush-left (IEEE-style) | No finding (uniform style) |
| 8 | Mixed: 3 hanging + 3 flush | `references_entry_indentation_inconsistent` |
| 9 | Only 2 multi-line entries (below 3-entry gate) | No indentation finding |
| 10 | Consistent inter-entry spacing | No spacing finding |
| 11 | Irregular inter-entry gaps | No crash; valid list returned |
| 12 | Only 1 entry (below all gates) | No B/C findings |
| 13 | Body in-text citations `[1]`, `(Placeholder, 2023)` with actual REFERENCES heading | No heading finding (citations not matched as heading) |
| 14 | Privacy: mixed entries trigger findings | No finding key contains placeholder text |
| 15 | Privacy: entries with synthetic DOI/URL text | No finding field contains "doi", "http", URL strings |
| 16 | Import and wiring sanity | Module importable; function callable; wired in audit_runner |
| 17 | Single-page PDF, no heading | No crash; returns empty list |
| 18 | 8-page body with no heading | Finding has rule_id=P064, severity=WARNING |
| 19 | No CHAPTER/APPENDIX body heading | No finding (body region not detected; skipped) |
| 20 | LITERATURE CITED heading | No heading finding |
| 21 | Long doc missing heading | `heading_type` field = "None" in finding |

---

## 4. Privacy Model

### Fields included in findings (geometric/structural only)

| Field | Type | Description |
|---|---|---|
| `issue_type` | string | Issue type enum string |
| `page_number` | string | Page where heading was detected or first body page |
| `body_start_page` | string | First body page (for heading finding only) |
| `body_page_count` | string | Number of body pages (for heading finding only) |
| `section_page_count` | string | Number of pages in references section |
| `entry_candidate_count` | string | Number of reference entry candidates |
| `multi_line_entry_count` | string | Number of multi-line entries (check B) |
| `affected_entry_count` | string | Number of entries contributing to inconsistency |
| `median_indent_px` | string | Median indent delta in points (check B) |
| `indent_inconsistency_score` | string | Stdev of indent deltas in points (check B) |
| `first_line_x` | string | Median x-start of first lines (check B) |
| `continuation_line_x` | string | Median x-start of continuation lines (check B) |
| `median_gap_px` | string | Median inter-entry gap in points (check C) |
| `gap_outlier_count` | string | Number of outlier gaps (check C) |
| `heading_type` | string | Normalized heading keyword or "None" |
| `confidence` | string | "low" or "medium" |
| `triage_tier` | string | "low" or "medium" |
| `source_q_rule_basis` | string | Guideline basis description |

### Fields explicitly excluded

The following are never included in any P064 finding:

- Reference entry text, substrings, or excerpts
- Citation text of any kind
- Author names (from entries or any other source)
- Article, book, or dissertation titles from the references list
- Journal or conference names
- DOI strings
- URL strings from references
- Labels or ref-keys from citation management systems
- Body text from any other part of the dissertation

---

## 5. Conservative Skip Conditions

P064 skips (returns no findings) under any of the following:

1. No `PdfDocument.pages` (empty document)
2. No body region detected (no CHAPTER or APPENDIX heading found anywhere)
3. Document has fewer than 5 body pages AND no references heading found (short doc skip)
4. No text-layer content on references section pages (image-only/flattened)
5. X-coordinate standard deviation > 50 pt (noisy geometry)
6. Three or more distinct left-margin clusters separated by >40 pt (multi-column layout)
7. Fewer than 2 entry candidates after grouping (section essentially empty)
8. Fewer than 5 entry candidates (checks B and C require ≥5 entries)
9. Fewer than 3 multi-line entry candidates (check B requires ≥3 multi-line entries)

---

## 6. Limitations

### Consistency-only detection

P064 uses variance-based metrics that can only detect *inconsistency* — not uniform
noncompliance.  If all reference entries consistently lack a hanging indent (e.g., all
flush-left across an entire section), the indentation check produces no finding because
all entries are consistent with one another.

### IEEE-style numbered flush-left lists

IEEE-style numbered references with flush-left continuation lines are explicitly skipped
by the `all_flush_left` guard.  These are structurally uniform and the rule should not
flag them.

### Short reference sections

Documents with fewer than 5 reference entry candidates skip both sub-checks.  Very short
reference lists (fewer than 5 entries) may reflect a clean short thesis rather than a
formatting problem.

### LaTeX-generated PDF geometry artifacts

BibTeX/biblatex-generated bibliographies may have microtype kerning or column alignment
effects that shift x-coordinates slightly.  The x-variance skip condition (> 50 pt stdev)
guards against the worst cases.  Conservative thresholds are used throughout.

### Non-standard heading phrasing

Only the four standard keywords are detected (REFERENCES, BIBLIOGRAPHY, WORKS CITED,
LITERATURE CITED).  Non-standard headings (e.g., "LITERATURE REVIEW" or "SOURCES")
will cause `references_section_heading_not_detected` even when a references section exists.

### Entry grouping depends on blank-line gaps

The entry-grouping heuristic uses a y0-to-y0 baseline gap threshold of 20 pt.  Entries
must be separated by a gap larger than 20 pt (corresponding roughly to a blank line
between entries) for the grouper to split them into separate candidates.  Reference
sections with no blank lines between entries may be under-counted as candidates.

---

## 7. Statement: Citation Style Out of Scope

**P064 does not enforce any specific citation style.**

APA, IEEE, ACM, MLA, Chicago, and other citation styles are all valid at NJIT, and the
style choice is made in consultation with the advisor.  P064 checks only:

- Whether a references section heading is present.
- Whether multi-line entries are consistently formatted relative to each other
  (structural geometry only — not content).
- Whether inter-entry spacing is consistent.

Content-level compliance (author name format, year placement, journal abbreviation,
DOI format, completeness of in-text citation cross-referencing) is entirely out of scope.
P064 does not parse, match, or interpret any citation or bibliography content.

---

## Cross-References

- Scope doc: `docs/planning/p064_references_citations_structural_check_scope_and_design.md`
- Rule module: `src/njit_auditor/rules/pdf_references_citations_structural.py`
- Test file: `tests/test_p064_references_citations_structural.py`
- EF overlap gap identified: `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- Analogy implementation: `src/njit_auditor/rules/pdf_biosketch_publication_layout.py` (P045)
- Current project state: `docs/status/current_project_state_and_next_steps.md`
