# P036 TOC/List Inter-Entry Spacing — Synthetic Validation

- **Rule:** P036 — PDF TOC/List inter-entry spacing
- **Date:** 2026-06-01
- **Module:** `src/njit_auditor/rules/pdf_toc_list_entry_spacing.py`

## Scope

P036 runs on detected **Table of Contents**, **List of Tables**, and **List of Figures**
pages. It groups text-layer lines into distinct entries (skipping wrapped internal
continuations handled by P032), measures vertical gap between consecutive entries, and
flags gaps below a conservative double-spacing threshold (ratio `< 1.4×` local line height).

Findings report geometry metadata only — no entry title text.

## Issue types

| `issue_type` | Meaning |
|---|---|
| `toc_inter_entry_spacing_too_tight` | Consecutive TOC entries appear single-spaced |
| `lot_inter_entry_spacing_too_tight` | Consecutive LoT entries appear single-spaced |
| `lof_inter_entry_spacing_too_tight` | Consecutive LoF entries appear single-spaced |

## Synthetic scenarios

| Scenario | Expected P036 behavior |
|---|---|
| TOC entries with acceptable double spacing | No finding |
| TOC consecutive entries too tight | `toc_inter_entry_spacing_too_tight` |
| LoT consecutive entries too tight | `lot_inter_entry_spacing_too_tight` |
| LoF consecutive entries too tight | `lof_inter_entry_spacing_too_tight` |
| Wrapped entry internal lines (same entry) | No finding (P032 domain) |
| Single-entry / sparse page | Skipped |
| Finding details | No entry text; geometry metadata only |

## Tests

See `tests/test_pdf_rules.py` (P036 section) and `tests/test_rule_inventory.py` (36 rules).

## Limitations (v1)

- Text-layer geometry only; does not prove full visual compliance on scanned lists.
- Entry boundary detection is conservative; ambiguous pages are skipped.
- Does not check wrapped **internal** spacing (P032), alignment (P018), capitalization (P024), continued headings (P030), or column headers (P031).

## Current-dataset note

No local or current-dataset P036 audit was run — evaluation PDFs were unavailable in the
workspace at implementation time. See `docs/evaluation/p036_current_dataset_evaluation.md`.

When evaluation PDFs are available, regenerate aggregate counts locally into gitignored
`data/evaluation/generated/current_auditor_after_p036/`. Do not commit generated JSON/MD.
Canonical pre-P035/P036 five-PDF aggregate (**1,446**) remains unchanged until a documented
full P001–P036 rerun.
