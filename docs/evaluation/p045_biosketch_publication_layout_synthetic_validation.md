# P045 Bio Sketch Publication Layout Synthetic Validation

- **Date:** 2026-06-03
- **Rule:** P045 — Biographical Sketch publication paragraph layout (Q028/Q029)
- **Status:** **Synthetic validation only** — current-dataset audit not run (evaluation PDFs unavailable)
- **Baseline main at implementation:** `6fa22df` (PR #126 — Implement P045 Bio Sketch publication layout checks)

---

## Validation summary

| Check | Result |
|-------|--------|
| Synthetic unit tests | **8 passed** |
| `ruff check .` | ✅ Clean |
| `mypy src` | ✅ Clean (59 source files) |
| `python -m pytest` | ✅ **515 passed** |

---

## Synthetic test coverage

| Test | Scenario | Expected outcome | Pass |
|------|----------|-----------------|------|
| `test_p045_no_biosketch_page_no_findings` | No BIOGRAPHICAL SKETCH heading | No P045 findings | ✅ |
| `test_p045_too_few_blocks_no_findings` | Only 1 multi-line block (gate) | No P045 findings | ✅ |
| `test_p045_correct_hanging_indent_no_findings` | Hanging indent present; adequate inter-entry gap | No P045 findings | ✅ |
| `test_p045_missing_hanging_indent_warns` | All blocks flush (no hanging indent) | `biosketch_publication_missing_hanging_indent` (Q029) | ✅ |
| `test_p045_entry_spacing_too_close_warns` | Hanging indent present; inter-entry gap too small | `biosketch_publication_entry_spacing_not_double` (Q028) | ✅ |
| `test_p045_finding_metadata_no_private_content` | Triggers Q029 finding | Findings contain geometry metadata only; no publication text | ✅ |
| `test_p045_q029_source_q_rule_id` | Missing hanging indent | `source_q_rule_id` = `Q029` in finding | ✅ |
| `test_p045_q028_source_q_rule_id` | Entry spacing too close | `source_q_rule_id` = `Q028` in finding | ✅ |

---

## Issue types

| Issue type | Q-rule | Condition |
|-----------|--------|-----------|
| `biosketch_publication_missing_hanging_indent` | Q029 | ≥2 multi-line blocks on Bio Sketch page; none exhibit hanging indent (`rest_x0 - first_x0 >= HANGING_THRESHOLD_PT = 12pt`) |
| `biosketch_publication_entry_spacing_not_double` | Q028 | Consecutive hanging-indent blocks have inter-block gap < `ENTRY_GAP_THRESHOLD_PT = 20pt` |

---

## P045 v1 scope note

Q026 (within-entry single-spacing) is deferred to v2. In the PDF text-layer representation,
detecting double-spacing within an entry requires distinguishing intra-entry gaps from
inter-entry gaps using the same vertical-gap threshold, which causes ambiguity. v1 covers
the more reliably detectable geometry checks (Q029 hanging indent and Q028 inter-entry gap).

---

## Canonical aggregate baseline (unchanged)

| Field | Value |
|-------|-------|
| Canonical pre-P035/…/P045 five-PDF aggregate | **1,446** total findings |
| `generated_for_commit` | `00b9c2d` |
| Canonical eval doc | `docs/evaluation/current_auditor_after_p034_evaluation.md` |

P045 does not alter the canonical 1,446 baseline.

---

## P045 v1 limitations

| Limitation | Detail |
|-----------|--------|
| Heading detection gate | Emits nothing if BIOGRAPHICAL SKETCH heading absent (compressed/flattened PDFs) |
| Multi-line block gate | Emits nothing if fewer than 2 multi-line blocks on the Bio Sketch page |
| Q029 approach | Checks for absence of hanging indent across ALL multi-line blocks; not per-entry |
| Q028 approach | Checks only consecutive hanging-indent block pairs; single-entry Bio Sketches skipped |
| Q026 | Deferred to v2 — within-entry spacing detection ambiguous with single gap threshold |
| Continuation of Bio Sketch to page 2 | Only the first Bio Sketch page is checked; multi-page Bio Sketches not fully covered |

---

## Current-dataset evaluation

No P045 current-dataset finding counts are available. The full set of five evaluation PDFs
is not directly accessible (Sebastian Fine Revised is ZIP-only).

See `docs/evaluation/p045_current_dataset_evaluation.md` for the current-dataset note.

---

## Privacy

Findings from P045 contain geometry metadata only:
`page_number`, `issue_type`, `multi_line_block_count` (Q029), `entry_index`, `observed_gap_points`,
`required_gap_points` (Q028), `hanging_indent_threshold_points`, `triage_tier`, `source_q_rule_id`.
No Biographical Sketch text, publication titles, author names, citation content, degree
information, or other private content is quoted.

Generated audit outputs remain gitignored under `data/evaluation/generated/`.
