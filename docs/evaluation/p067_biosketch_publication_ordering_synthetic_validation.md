# P067 Biographical Sketch Publication Ordering — Synthetic Validation

- **Rule:** P067 — Bio Sketch publication/presentation reverse-chronology check
- **Q-rule basis:** Q027
- **Module:** `njit_auditor.rules.pdf_biosketch_publication_ordering`
- **Issue type:** `biosketch_publication_order_suspicious`
- **Validation date:** 2026-06-08

## Purpose

P067 provides conservative PDF-only coverage for the NJIT requirement that Biographical
Sketch publication/presentation entries appear from most recent to oldest. The rule is
limited to structural year-order checks on grouped citation-like entries and does not read
or reproduce publication titles, venues, authors, DOI strings, URL strings, or Bio Sketch
prose.

## Scope

Implemented in v1:

- unique `BIOGRAPHICAL SKETCH` page detection
- clear Publications/Presentations subsection boundary detection
- grouped citation-like entry extraction from that zone only
- representative 4-digit year extraction when an entry yields exactly one unique year
- descending-order check with equal years allowed

Explicitly out of scope:

- publication correctness or completeness
- venue correctness or ranking
- author parsing or authorship checks
- title parsing or semantic classification
- DOI/URL parsing or validation
- citation-style consistency (`Q030`)
- OCR or image-only recovery

## Synthetic Coverage

`tests/test_p067_biosketch_publication_ordering.py` covers 13 scenarios:

| Test | Scenario | Expected result |
|---|---|---|
| 1 | No BIOGRAPHICAL SKETCH heading | No findings |
| 2 | Bio Sketch page without Publications zone | No findings |
| 3 | Descending publication years | No findings |
| 4 | Ascending publication years | `biosketch_publication_order_suspicious` |
| 5 | Equal adjacent years | No findings |
| 6 | Fewer than 3 comparable entries | No findings |
| 7 | Multi-year entry block | Entry skipped; no finding when comparables become too sparse |
| 8 | Image-only / empty text layer | No findings |
| 9 | Multiple BIOGRAPHICAL SKETCH headings | No findings |
| 10 | Education-zone years above Publications boundary | No findings |
| 11 | Long prose line with a year token | Excluded; no finding |
| 12 | Privacy: no Bio Sketch/publication text in findings | Pass |
| 13 | Privacy: DOI/URL strings not leaked | Pass |

## Finding Payload

When P067 fires, details are limited to privacy-safe metadata:

- `issue_type`
- `entry_candidate_count`
- `comparable_entry_count`
- `first_entry_year`
- `last_entry_year`
- `inversion_count`
- `first_inversion_index`
- `expected_order`
- `confidence`
- `triage_tier`
- `source_q_rule_ids`

No publication text, author names, titles, venue names, DOI strings, URL strings, or
biographical prose are included in findings.

## Limitations

- Requires a unique machine-readable `BIOGRAPHICAL SKETCH` heading.
- Requires a clear machine-readable Publications/Presentations subsection boundary.
- Skips ambiguous multi-year entries rather than inferring the intended representative year.
- Skips DOI/URL-heavy entries and suspected nonstandard/multi-column layouts.
- Zero findings do not prove Q027 compliance on flattened, image-heavy, or boundary-missing
  Bio Sketch pages.
