# P056 Current-Dataset Evaluation

- **Rule:** P056 — LoT/LoF entry numbering format consistency check
- **Module:** `njit_auditor.rules.pdf_lot_lof_number_format`
- **Issue types:** `lot_mixed_numbering_format`, `lof_mixed_numbering_format`
- **Q-rule basis:** Q063 / Q072
- **Date:** 2026-06-05
- **Status:** **Not run** — only 4 of 5 evaluation PDFs are directly accessible in the workspace; a canonical five-PDF run is not possible.

## Reason

The fifth evaluation PDF (Sebastian Fine Revision 3) is accessible only as an archive-contained file inside a tracked ZIP (`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`) and is not present as a standalone tracked path. Conducting a four-PDF partial run would not constitute a canonical aggregate and could be misleading.

## Expected behavior

P056 emits a `WARNING`-severity finding when a List of Tables or List of Figures page contains a mix of at least two chapter-based (X.Y) and two sequential (N) numbered entries. The check is intentionally conservative (triage_tier: `low`) and is expected to produce zero or near-zero findings on conformant dissertations that use a single consistent numbering convention throughout their LoT/LoF sections.

## Synthetic validation

13 synthetic tests were added in `tests/test_pdf_rules.py` covering:

- Clean LoT with all chapter-based entries → 0 findings
- Clean LoT with all sequential entries → 0 findings
- Mixed LoT with ≥2 of each format type → 1 finding (lot_mixed_numbering_format)
- Mixed LoF with ≥2 of each format type → 1 finding (lof_mixed_numbering_format)
- Boundary cases: fewer than 2 of one format type → 0 findings
- Appendix-prefixed entries (e.g. "Table A.1") correctly skipped
- Wrap-continuation lines (no page_number_token) excluded from counts
- Short entries (< 10 chars) excluded

See `docs/evaluation/p056_lot_lof_number_format_synthetic_validation.md` for detail.

## Privacy note

P056 findings contain only structural metadata: `issue_type`, `page`, `section_type`, `entry_count`, `format_counts` (e.g. `"chapter_based:2,sequential:3"`), `observed_formats`, `dominant_format`, `triage_tier`, `source_q_rule_id`. No entry text, table/figure titles, or other private student content is included in any finding.
