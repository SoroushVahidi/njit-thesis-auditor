# P039 TOC Entry Hierarchy — Synthetic Validation

- **Date:** 2026-06-03
- **Implementation commit:** rules/p039-toc-entry-hierarchy
- **Auditor scope:** P001–P039
- **Validation type:** Synthetic (programmatically generated PDF fixtures)

## 1. Purpose

Confirm that P039 (`check_pdf_toc_entry_hierarchy`) emits correct findings on synthetic
TABLE OF CONTENTS pages and correctly skips non-TOC pages and pages below gate thresholds.

All synthetic PDFs are generated at test time using PyMuPDF (`fitz`). No real dissertation
content, author names, or private text is used.

## 2. Test matrix

| # | Test | Expected outcome |
|---|------|-----------------|
| 1 | L2 entries indented 18pt right of L1 (l1_x=72, l2_x=90) | No P039 finding |
| 2 | L2 entries at same indent as L1 (l1_x=72, l2_x=72) | `toc_l2_not_indented_relative_to_l1` |
| 3 | L3 entries indented 18pt right of L2 (l2_x=90, l3_x=108) | No P039 L3 finding |
| 4 | L3 entries at same indent as L2 (l2_x=90, l3_x=90) | `toc_l3_not_indented_relative_to_l2` |
| 5 | Only 1 L2 entry (below MIN_CHILD_ENTRIES_TO_CHECK gate) | No finding |
| 6 | No L1 entries — only L2 entries (need parent level to compare) | No L2 hierarchy finding |
| 7 | LIST OF TABLES page (not TABLE OF CONTENTS) | No P039 finding |
| 8 | Finding details privacy check | No entry title text in finding details |
| 9 | CLI integration | P039 present in JSON report when triggered |

All 9 tests pass on implementation commit.

## 3. Finding details schema

All P039 findings include only geometry/metadata — no entry title text or dissertation prose:

| Field | Type | Example |
|-------|------|---------|
| `issue_type` | str | `toc_l2_not_indented_relative_to_l1` |
| `level` | str | `"2"` |
| `parent_level` | str | `"1"` |
| `observed_delta_points` | str | `"0.0"` |
| `required_delta_points` | str | `"6.0"` |
| `l1_entry_count` | str | `"2"` |
| `l2_entry_count` | str | `"4"` |
| `triage_tier` | str | `"high"` |
| `source_q_rule_id` | str | `"Q056"` |

No entry title text, chapter headings, section titles, or other dissertation content is
included in finding details.

## 4. v1 known limitations

| Limitation | Notes |
|---|---|
| Text-pattern level detection | Entries without CHAPTER/APPENDIX prefix (L1) or X.Y numeric pattern (L2/L3) are classified as ambiguous and excluded from the check |
| Gate: ≥2 child entries required | Pages with a single L2 entry are skipped to reduce false positives |
| Gate: both parent and child levels required | If a TOC page has only L2/L3 entries (no L1 to compare), the L2 hierarchy check is skipped |
| TOC pages only | LoT and LoF pages are excluded by design |
| Compressed PDFs | Coordinate extraction may be unreliable; the 6pt minimum threshold reduces artifact noise |
| Unnumbered front-matter headings | Entries like ABSTRACT, DEDICATION appearing in the TOC at L1 position are typically filtered by `_likely_entry_line` (all-caps short text) and thus excluded from level classification |

## 5. Privacy notes

- Test fixtures use synthetic placeholder text ("Chapter 1 Section Heading Title Long",
  "1.1 Subsection Title Entry Here", etc.) — no real dissertation content.
- P039 findings contain only numeric coordinate values and count metadata.
- No entry text, chapter titles, section titles, or biographical content appears in findings.

## 6. Current-dataset evaluation

**Not performed** — evaluation PDFs unavailable in workspace. No P039 counts exist
against the five-PDF canonical set. Do not update the **1,446** pre-P035/P036/P037/P038
canonical total until a full P001–P039 rerun is performed locally when evaluation PDFs
are available.

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set.
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p039/`.
3. Update a privacy-safe current-dataset doc with aggregate P039 counts and issue-type mix only.
4. Do not quote TOC entry text or any dissertation prose.
