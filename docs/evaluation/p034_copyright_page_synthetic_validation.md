# P034 Copyright Page — Synthetic Validation

- **Rule:** P034 — Copyright Page metadata and layout (partial Q009–Q011)
- **Date:** 2026-06-01
- **Module:** `src/njit_auditor/rules/pdf_copyright_page.py`

## Scope

P034 runs only when a Copyright Page is confidently identified (explicit
`COPYRIGHT PAGE` heading or copyright/© signal in early front matter with
extractable text). It performs three conservative checks:

1. **Q009** — no header/running text in the top margin (`copyright_top_margin_header_text`)
2. **Q010** — copyright year matches Title Page graduation year when both are confidently extracted (`copyright_year_mismatch`)
3. **Q011** — author name matches Title Page author (line after `by`) when both are confidently extracted (`copyright_author_mismatch`)

Findings report years and stable author hashes only — never raw author names, title text, or body text.

Q012 (no visible page number on the Copyright Page) remains covered by **P022**, not P034.

## Synthetic scenarios

| Scenario | Expected P034 behavior |
|---|---|
| Matching © year and author; no top-margin header | No finding |
| © line with one leading middle initial; title `by` line without it | No finding (middle-initial tolerance) |
| Running header text in top margin | `copyright_top_margin_header_text` |
| © year differs from Title Page `May YYYY` | `copyright_year_mismatch` |
| © author differs from Title Page `by` line | `copyright_author_mismatch` (hashes only) |
| No copyright page detected | No finding |
| Ambiguous multiple years on © line | No year mismatch finding |
| Finding details | No raw author names or dissertation title text |

## Tests

See `tests/test_pdf_rules.py` (P034 section) and `tests/test_rule_inventory.py`.

## Limitations

- PDF text layer only; image-only copyright pages are skipped.
- Author extraction requires a `by` line on the Title Page and a ©/copyright notice pattern on the Copyright Page.
- Does not verify administrative copyright approval or full manual Q009–Q011 compliance.
