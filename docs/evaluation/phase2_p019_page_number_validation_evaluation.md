# Phase 2 P019 Page-Number Validation Evaluation

- Date: 2026-05-23
- Source filename: `clean_without_annotations.pdf`

## Result Summary

- `P019` finding count: `15`

## High-Level Issue Types

- `multiple_page_numbers` (`7`)
- `inconsistent_position` (`2`)
- `mixed_numbering_style` (`5`)
- `sequence_gap` (`1`)

## Heuristic Scope (Conservative)

- Candidate-based checks only (built on page-number candidate detection).
- Focuses on obvious sequence/style/position inconsistencies.
- Does not yet enforce full NJIT policy-specific page-number rules.

## Caveat

- `P019` is heuristic and does not replace manual page-number review.

## Privacy Note

- No dissertation body text is included.
- Generated report artifacts under `data/evaluation/generated/...` are ignored by git.
