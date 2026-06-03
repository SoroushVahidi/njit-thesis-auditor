# P042 TOC Appendix Entry Format — Synthetic Validation

- **Date:** 2026-06-03
- **Implementation commit:** rules/p042-toc-appendix-format
- **Auditor scope:** P001–P042
- **Validation type:** Synthetic (programmatically generated PDF fixtures)

## 1. Purpose

Confirm that P042 (`check_pdf_toc_appendix_format`) correctly flags incorrectly formatted
appendix entries in the Table of Contents, skips non-TOC pages, and produces privacy-safe
findings.

All synthetic PDFs are generated at test time using PyMuPDF (`fitz`). No real dissertation
content, appendix titles, or private data is used.

## 2. Test matrix

| # | Test | Expected outcome |
|---|------|-----------------|
| 1 | TOC with chapter entries only (no appendix) | No P042 finding |
| 2 | Single appendix entry with title after APPENDIX | No P042 finding |
| 3 | Single appendix entry with no title (just "Appendix") | `single_appendix_missing_title` |
| 4 | Two appendix entries each with letter identifier (A, B) | No P042 finding |
| 5 | Two appendix entries without letter identifiers | `multiple_appendix_missing_letter` |
| 6 | Two appendix entries: one with letter, one with number (not a letter) | `multiple_appendix_missing_letter` for the number entry |
| 7 | LIST OF TABLES page with appendix-like text | No P042 finding (TOC-only rule) |
| 8 | Finding details privacy check | No appendix title text in details |
| 9 | CLI integration | P042 in JSON output when triggered |

All 9 tests pass on implementation commit.

## 3. Finding details schema

P042 findings contain only count and classification metadata — no appendix titles or TOC entry text:

| Field | Type | Example |
|-------|------|---------|
| `issue_type` | str | `multiple_appendix_missing_letter` |
| `page_number` | str | `"1"` |
| `appendix_entry_count` | str | `"2"` |
| `entry_index` | str | `"0"` |
| `expected_pattern` | str | `"APPENDIX <A-Z>"` |
| `triage_tier` | str | `"medium"` |
| `source_q_rule_id` | str | `"Q059"` |

No appendix title text, TOC entry content, or private dissertation content is included.

## 4. Implementation note

The `single_appendix_missing_title` check (Q058) requires the appendix entry to pass
`_likely_entry_line`. All-caps short entries like "APPENDIX" (1 word, all-caps) are
filtered out as heading-like text. Mixed-case entries like "Appendix:" that pass the
filter are checked. In practice, well-formed appendix entries with a title will always
pass the filter.

## 5. v1 known limitations

| Limitation | Notes |
|---|---|
| All-caps short entries | "APPENDIX" alone (all-caps, 1 word) is filtered by `_likely_entry_line`; not detected as an appendix entry |
| Roman numeral appendices | Entries like "APPENDIX I" or "APPENDIX II" (not single letter) would trigger `multiple_appendix_missing_letter` |
| TOC-only | LoT and LoF pages are excluded by design |
| Compressed PDFs | Text extraction may be unreliable |

## 6. Current-dataset evaluation

**Not performed** — evaluation PDFs unavailable in workspace.

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set.
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p042/`.
3. Update a privacy-safe current-dataset doc with aggregate P042 counts only.
4. Do not quote TOC entry text, appendix titles, or any dissertation prose.
