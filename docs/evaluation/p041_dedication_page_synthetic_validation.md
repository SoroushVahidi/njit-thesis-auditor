# P041 Dedication Page Top-Margin Header — Synthetic Validation

- **Date:** 2026-06-03
- **Implementation commit:** rules/p041-dedication-page-header
- **Auditor scope:** P001–P041
- **Validation type:** Synthetic (programmatically generated PDF fixtures)

## 1. Purpose

Confirm that P041 (`check_pdf_dedication_page`) correctly flags header text in the
top margin of the Dedication page, skips allowed text (page numbers and the DEDICATION
heading itself), and gates correctly when no Dedication page is detected.

All synthetic PDFs are generated at test time using PyMuPDF (`fitz`). No real dissertation
content, dedication text, author names, or private data is used.

## 2. Test matrix

| # | Test | Expected outcome |
|---|------|-----------------|
| 1 | No DEDICATION heading in document | No P041 finding (gate) |
| 2 | Dedication page with no top-margin text | No P041 finding |
| 3 | Dedication page with stray running header in top margin | `dedication_top_margin_header_text` |
| 4 | Page number candidate (`iv`) in top zone | No finding (excluded) |
| 5 | DEDICATION heading text appearing in top zone | No finding (heading excluded) |
| 6 | Dedication body text placed below top 15% | No finding (below threshold) |
| 7 | Finding details privacy check | No dedication/header/body text in details |
| 8 | CLI integration | P041 in JSON output when triggered |

All 8 tests pass on implementation commit.

## 3. Finding details schema

P041 findings contain only geometry/classification metadata — no dedication or header text:

| Field | Type | Example |
|-------|------|---------|
| `issue_type` | str | `dedication_top_margin_header_text` |
| `page_number` | str | `"1"` |
| `top_region_threshold_points` | str | `"118.8"` |
| `line_y` | str | `"31.4"` |
| `line_x0` | str | `"72.0"` |
| `line_x1` | str | `"285.2"` |
| `triage_tier` | str | `"medium"` |
| `source_q_rule_id` | str | `"Q032"` |

No dedication prose, running header text, or any private content is included.

## 4. v1 known limitations

| Limitation | Notes |
|---|---|
| DEDICATION heading detection | Requires verbatim "DEDICATION" text in the text layer; stylized dedications without a visible heading are missed (false negatives) |
| Scan range | First 15 pages scanned; DEDICATION pages after page 15 would be missed |
| Top zone threshold | Fixed at 15% of page height (~118.8pt for standard 792pt page) |
| Single finding per page | At most one finding emitted per detected Dedication page |
| Compressed/flattened PDFs | Text extraction may fail; DEDICATION heading not detected → gate silently skips |

## 5. Privacy notes

- Test fixtures use synthetic placeholder text ("DEDICATION", "Some Running Header Text", "In memory of those who came before.") — no real dissertation content.
- P041 findings contain only numeric coordinate values and a classification label — no dedication text.
- The `observed_text_kind` field is NOT included in findings (unlike P034); findings contain only coordinates and metadata.

## 6. Current-dataset evaluation

**Not performed** — evaluation PDFs unavailable in workspace. No P041 counts exist
against the five-PDF canonical set. Do not update the **1,446** canonical total until
a full P001–P041 rerun is performed locally when evaluation PDFs are available.

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set.
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p041/`.
3. Update a privacy-safe current-dataset doc with aggregate P041 counts only.
4. Do not quote dedication text, header text, or any dissertation prose.
