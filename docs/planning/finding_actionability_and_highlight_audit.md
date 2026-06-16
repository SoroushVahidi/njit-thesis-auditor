# Finding Actionability and Highlight Audit

**Date:** 2026-06-16  
**PR:** #320 — Clickable actionable findings  
**Baseline:** main at 802350d (PR #319)

---

## Summary

This document describes the actionability model added in PR #320.
Every finding now has a clear, honest action. No finding card is empty or ambiguous.

---

## Actionability Model

Each finding is classified into one of three action kinds:

| Action kind | When it applies | Button label | URL pattern |
|---|---|---|---|
| `highlight` | Finding has a valid drawable bbox (x0,y0,x1,y1) | "Open highlighted PDF page" | `/audits/{job_id}/pdf/highlighted?...` |
| `page` | Finding has a known page number but no bbox | "Open PDF page" | `/audits/{job_id}/pdf#page=N` |
| `explanation` | Finding is document-level (no page, no bbox) | "Read explanation" | — (explanation shown inline) |

All three action kinds are consistently applied on:

- Main result page (grouped problems and individual findings)
- Category problem pages
- Rule problem pages

---

## Finding-by-finding Classification

### Exact highlight (action_kind = "highlight")

| rule_id | issue_type | Notes |
|---|---|---|
| P012 | pdf_annotation_detected | Stores annotation `rect` as `(x0, y0, x1, y1)` in details; parsed by `_parse_bbox_from_details` |

### Page-only navigation (action_kind = "page")

Most rules. Representative examples:

| rule_id | Representative issue types |
|---|---|
| P011 | margin_boundary_violation |
| P013 | page_number_candidate, missing_page_number, multiple_page_numbers, inconsistent_position, mixed_numbering_style, sequence_gap |
| P019 | page_number_sequence_error |
| P021 | abstract_word_count_exceeded |
| P022 | frontmatter_page_has_page_number |
| P023 | body_spacing_issue |
| P026 | possible_body_font_family_issue, possible_body_font_size_issue |
| P027 | heading_style_issue |
| P028 | frontmatter_page_number_style_issue, body_page_roman_number, frontmatter_arabic_number |
| P029 | roman_sequence_gap |
| P030 | missing_continued_heading, toc_missing_continued_heading |
| P033 | title_page_mismatch, title_consistency_mismatch |
| P034 | copyright_year_mismatch, copyright_author_not_found, copyright_year_not_found |
| P038 | heading_phrase_not_exact |
| P063 | appendix_letter_sequence_gap, appendix_letter_sequence_repeat |
| P064 | references_structural_issue |
| P065 | dedication_text_not_centered, dedication_text_not_italic |
| P078 | abstract_pdf_forbidden_term, abstract_pdf_first_person_pronoun |

### Document-level explanation only (action_kind = "explanation")

| rule_id | issue_type | Notes |
|---|---|---|
| P013 | p013_document_overview | No page or bbox; summary of document-wide patterns |

---

## Detailed Explanations

The module `src/njit_auditor/finding_explanations.py` provides:

- `build_detailed_explanation(rule_id, issue_type, details, page)` — finding-level explanation
- `build_group_explanation(rule_id, issue_type)` — group-level explanation for grouped cards
- `get_action_kind(has_bbox, page)` — "highlight" | "page" | "explanation"
- `get_action_label(has_bbox, page)` — button label string
- `get_no_highlight_reason(has_bbox, page)` — why no highlight is available

### Key special cases

**P021 (abstract word count):**
The finding details include `word_count`, `limit`, and `inferred_degree_type` but do not set `issue_type`.
`_resolve_issue_type` detects this case and normalizes to `"abstract_word_count_exceeded"` so the template
substitutes the actual observed count and limit values.

Example explanation:
> The abstract appears to contain 420 words. For the detected degree type (PhD), the allowed maximum is 350 words. This is 70 words over the limit. Note: if the abstract spans multiple pages, the word count shown may be an undercount. Review the abstract text and shorten it before submission.

**P012 (annotations):**
Already stores `rect` in details; parsed as a drawable bbox by `_parse_bbox_from_details`.
Renders as a highlighted PDF page with the annotation rectangle visually marked.

**P026 (font compliance):**
No per-span coordinates stored in details. Page-only navigation with explanation mentioning Times New Roman 12pt.

**P011 (margins):**
Stores `side` and `worst_overflow_pt` but not individual line coordinates.
Page-only navigation; explanation names the side and NJIT margin requirements.

---

## No-highlight Reasons

When highlight is not available, the UI shows an honest note:

| Situation | Note shown |
|---|---|
| Page known, no bbox | "Exact highlight is not available for this finding, but the relevant page is known." |
| No page, no bbox | "This finding is document-level and does not correspond to a specific page or visual location." |
| Highlight available | (no note shown) |

---

## Deferred: Metadata Plumbing

The following rules have coordinate data internally in their detectors but do not currently expose it
in `AuditFinding.details`. Adding this would require changing the detector outputs (not just
presentation layer). Deferred to future P rules.

| rule_id | What the detector knows | Reason deferred |
|---|---|---|
| P011 | Per-line violation `PdfTextLine.bbox` | Would change details structure; line bboxes need validation before exposure |
| P013 | Per-candidate token positions | Detection is pattern-based; positions not currently captured in details |
| P026 | Per-span bboxes from `PdfTextSpan` | Would change details structure; deferred to a future font-highlight rule |

---

## Mobile/Desktop Parity

Same data, same actions, different layout only. No `mobile-only` / `desktop-only` content branch.

The following are verified by `tests/test_finding_actionability.py`:

- Same action labels on mobile (390px) and desktop (1440px)
- Same PDF links on both viewports
- Same rule IDs on both viewports
- Same issue-type labels on both viewports
- Same detailed explanations on both viewports
- No forbidden responsive classes in templates

---

## Known Limitations

1. **P011, P013, P026** do not have exact highlight coordinates. Finding-level precision
   requires detector changes (deferred).

2. **Multi-page abstracts (P021)**: the word count is an undercount when the abstract spans
   multiple pages. The explanation notes this caveat explicitly.

3. **Playwright/real browser coverage**: parity is tested at the server-rendered HTML level.
   CSS layout behavior (stacking, wrapping) on actual devices is not tested.

4. **Highlighted PDF caching**: highlighted copies are cached per `(page, rule_id, issue_type,
   finding_index)` tuple. Cache is per-job in the runtime directory and is cleaned up with
   the job on TTL expiry.

---

## Validation

```
ruff check .    → All checks passed!
mypy src        → Success: no issues found in 92 source files
python -m pytest → 1357 passed, 1 warning
```
