# P035 Figure/Table Body Layout — Synthetic Validation

- **Rule:** P035 — PDF figure/table body layout (centering and caption placement)
- **Date:** 2026-06-01
- **Module:** `src/njit_auditor/rules/pdf_figure_table_layout.py`

## Scope

P035 runs on **body pages** only (skips TOC, LoT, LoF, references). It reuses caption
detection from `pdf_captions.py`, clusters adjacent single-line text blocks into inferred
float bodies, and checks:

1. **Table:** caption above body; body horizontally centered in text area
2. **Figure:** caption below body; body horizontally centered in text area

Findings report geometry metadata only (`issue_type`, `float_type`, `float_number`,
`center_delta_points`) — no caption or body text.

## Issue types

| `issue_type` | Meaning |
|---|---|
| `table_body_not_centered` | Inferred table body drift from text-area center |
| `figure_body_not_centered` | Inferred figure body drift from text-area center |
| `table_caption_not_above_body` | Table body detected above caption |
| `figure_caption_not_below_body` | Figure body detected below caption |

## Synthetic scenarios

| Scenario | Expected P035 behavior |
|---|---|
| Centered table body, caption above | No finding |
| Off-center table body | `table_body_not_centered` |
| Table caption below body | `table_caption_not_above_body` |
| Centered figure body, caption below | No finding |
| Off-center figure body | `figure_body_not_centered` |
| Figure caption above body | `figure_caption_not_below_body` |
| Caption only (no text-layer body) | No finding (skip) |
| TOC page with table-like line | No finding (non-body context) |
| Finding details | No caption/body text or `line_preview` |

## Tests

See `tests/test_pdf_rules.py` (P035 section) and `tests/test_rule_inventory.py`.

## Limitations (v1)

- Text-layer bodies only; **image-only floats are skipped** until image bbox extraction exists.
- Same-page floats only; multi-page floats not handled.
- Single confident body cluster per caption; ambiguous multi-cluster pages skipped.
- Does not check caption punctuation/case (P017) or list/front-matter formatting rules.

## Current-dataset note

Local four-PDF subset results (0 / 0 / 0 / 13) are documented in
`docs/evaluation/p035_current_dataset_evaluation.md`. That doc is **not** a canonical
five-PDF aggregate rerun; the pre-P035 baseline (**1,446** findings) remains unchanged.

Regenerate full five-PDF counts locally into gitignored
`data/evaluation/generated/current_auditor_after_p035/` when needed.
