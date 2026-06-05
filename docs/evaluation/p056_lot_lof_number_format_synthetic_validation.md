# P056 LoT/LoF Number Format Synthetic Validation

- **Rule:** P056 — LoT/LoF entry numbering format consistency check (Q063/Q072 extension)
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_number_format.py`
- **Issue types:** `lot_mixed_numbering_format`, `lof_mixed_numbering_format`
- **Validation type:** Synthetic only (no real-data audit run)

---

## Test coverage (13 synthetic tests)

| Test | Expected outcome | Result |
|------|-----------------|--------|
| `test_p056_no_lot_lof_page_no_finding` | No LoT/LoF page → no findings | Pass |
| `test_p056_lot_consistent_sequential_no_finding` | All sequential (N) entries → no finding | Pass |
| `test_p056_lot_consistent_chapter_based_no_finding` | All chapter-based (X.Y) entries → no finding | Pass |
| `test_p056_lot_mixed_format_warns` | Mixed chapter-based and sequential → `lot_mixed_numbering_format` | Pass |
| `test_p056_lof_consistent_no_finding` | Consistent LoF entries → no finding | Pass |
| `test_p056_lof_mixed_format_warns` | Mixed LoF entries → `lof_mixed_numbering_format` | Pass |
| `test_p056_wrap_continuation_skipped` | Entries without page-number token → skipped | Pass |
| `test_p056_sparse_page_skipped` | Page with < 2 entries → skipped | Pass |
| `test_p056_toc_entries_unaffected` | TABLE OF CONTENTS page → P056 does not fire | Pass |
| `test_p056_single_format_type_insufficient_no_finding` | Only 1 entry of each format → below gate → no finding | Pass |
| `test_p056_finding_metadata_privacy_safe` | Finding details contain no entry text or title content | Pass |
| `test_p056_import_and_wiring` | Importable and wired in cli.py | Pass |
| `test_p056_p055_p053_unaffected` | P055 still fires correctly after P056 added | Pass |

---

## Privacy-safe metadata gate

Findings contain only:

- `issue_type` — `lot_mixed_numbering_format` or `lof_mixed_numbering_format`
- `page` — page number string
- `section_type` — `list_of_tables` or `list_of_figures`
- `entry_count` — count of complete classified entries
- `format_counts` — e.g., `chapter_based:2,sequential:3`
- `observed_formats` — `chapter_based,sequential`
- `dominant_format` — the more common format
- `triage_tier` — `low`
- `source_q_rule_id` — `Q063` (LoT) or `Q072` (LoF)

No entry text, figure/table titles, captions, dissertation body content, or private content is included in findings.

---

## Conservative gates applied

| Risk | Gate |
|------|------|
| Wrap continuation lines | Only entries with `page_number_token is not None` are classified |
| Short fragments | Entries shorter than 10 chars after stripping are skipped |
| Appendix-prefixed entries | Entries matching `^(?:table|figure)\s+[a-zA-Z]` are skipped |
| Insufficient mix | Only flag if ≥ 2 entries of each format type are present on the page |
| Sparse pages | Pages with fewer than 2 extracted entries are skipped |
| TOC pages | Only `list_of_tables` and `list_of_figures` page types are processed |
| Low severity | Findings emitted at `triage_tier: low` (advisory only) |

---

## Current dataset evaluation

**Not run.** Only 4/5 evaluation PDFs are directly accessible. A canonical real-data audit was not conducted for P056.

- `generated_for_commit`: `00b9c2d` (unchanged)
- `canonical aggregate`: `1,446` (unchanged)
