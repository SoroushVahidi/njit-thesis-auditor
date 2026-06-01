# P033 Front-Matter Title Consistency — Synthetic Validation

- **Rule:** P033 — cross-page dissertation title consistency (Title Page, Abstract, Approval)
- **Date:** 2026-06-01
- **Scope:** Conservative partial PDF heuristic for cross-page title spelling consistency

## Intent

P033 compares normalized title-like text extracted from the Title Page, the region above
the ABSTRACT heading, and the region above the APPROVAL PAGE heading. It flags material
differences only when at least two high-confidence candidates are present. Findings never
include dissertation title text.

## Synthetic scenarios

| Scenario | Expected P033 behavior |
|----------|------------------------|
| Same title with different line breaks on three pages | No finding |
| Same title with case/punctuation differences only | No finding |
| Materially different title on Abstract page | Warning (`frontmatter_title_mismatch`) |
| Materially different title on Approval page | Warning |
| Only Title Page candidate extracted | No finding |
| Short/ambiguous title (low confidence) | No finding |
| No extractable title text (metadata only) | No finding |
| Privacy-safe finding details | No raw title, author, or body text in message/details |

## Limitations

- PDF text-layer extraction only; image-only titles are skipped.
- Title Page heuristic uses lines before degree/author/metadata markers; unusual layouts may
  be skipped or mis-grouped.
- Normalization removes punctuation and compares similarity (threshold 0.92); near-miss
  typos may be missed or over-flagged.
- Does not verify semantic equivalence, subtitle wording policy, or committee-page titles.
- Requires named front-matter headings (ABSTRACT, APPROVAL PAGE) for page roles.

## Test references

See `tests/test_pdf_rules.py` (P033 section) and `tests/test_rule_inventory.py`.
