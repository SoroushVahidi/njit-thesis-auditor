# Phase 2 P017 Caption Formatting Check Evaluation

- Date: 2026-05-23
- Source filename: `clean_without_annotations.pdf`

## Result Summary

- `P017` finding count: `0`

## High-Level Issue Types

- none detected in this run

## Heuristic Scope (Conservative)

- Detects caption-like lines starting with `Figure`, `Fig.`, or `Table` with number-like tokens.
- Applies context-aware checks for body pages and list pages (`LIST OF TABLES` / `LIST OF FIGURES`).
- Focuses on strong punctuation signals and only high-confidence case-style hints.

## Caveat

- `P017` is heuristic and conservative; false negatives are possible, especially for multi-line captions or weak text-layer extraction.

## Privacy Note

- No dissertation body text is included.
