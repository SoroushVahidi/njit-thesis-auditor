# Finding Actionability Matrix

> **Historical note:** This document predates later UI/actionability changes,
> including strict highlight policy (PR #321), original-PDF-page actions and
> problem numbering (PR #329), expanded visual highlight coverage (PR #328),
> sub-page location labels (PR #326), and bespoke long-tail remediation
> (PR #330). The matrix table below still describes the **2026-06-16**
> planning snapshot (including removed `"Open PDF page"` labels). It is
> retained as historical planning context and **must not** be treated as the
> current behavior specification. See **Current policy** below.

Generated: 2026-06-16  
Baseline: main at 802350d (PR #319 merged)  
Last reviewed as historical: 2026-06-19 (main @ 5434665)

## Current policy (authoritative as of 2026-06-19)

Every visible finding on the public web UI follows this action model:

| Condition | Action label | Behavior |
|---|---|---|
| Real drawable highlight bbox | **Open highlighted PDF page** | Opens privacy-safe highlighted PDF route |
| Page known, no highlight | **Open original PDF page** | Opens original PDF at the listed page with stronger no-highlight guidance |
| No page / document-level | **Read explanation** | Explanation-only; no PDF navigation button |

Additional current rules:

- Every visible finding has a **stable problem number** (`Problem #N`).
- Fake highlights and old page-only labels are **forbidden**:
  `"Open PDF"`, `"Open PDF page"`, `"Open first example page"`.
- JSON and Markdown exports include the same problem numbers and student-facing wording.
- Mobile and desktop expose the same substantive actions (layout may differ).

Implementation references: `finding_explanations.py`, `report_view.py`,
`tests/test_problem_numbers_and_page_actions.py`,
`tests/test_visual_highlight_coverage.py`.

---

## Column definitions (historical matrix — 2026-06-16)

| Column | Meaning |
|---|---|
| rule_id | P-rule ID |
| issue_type | `details["issue_type"]` value (representative; some rules emit multiple) |
| category | Audit category bucket |
| current location metadata | Fields present in `AuditFinding.details` |
| highlight possible? | Yes / No / Partial |
| desired action | What the UI should offer |
| fallback action | When highlight not possible |
| no-highlight reason | Why highlight is unavailable |
| explanation fields needed | What detail keys are used by `build_detailed_explanation` |
| implementation status | Done / Partial / TODO |

---

## Matrix

| rule_id | issue_type | category | current location metadata | highlight possible? | desired action | fallback action | no-highlight reason | explanation fields needed | implementation status |
|---|---|---|---|---|---|---|---|---|---|
| P011 | margin_boundary_violation | margin_or_overflow | page, side, worst_overflow_pt, affected_line_count, confidence | No | Open PDF page | Open PDF page | Exact highlight coordinates not available; individual line coordinates not currently stored | side, worst_overflow_pt | Done — page-only |
| P012 | pdf_annotation_detected | annotations | page, **rect** (x0,y0,x1,y1), annotation_type, triage_tier | **Yes** | Open highlighted PDF page | Open PDF page | — | annotation_type | Done — highlighted |
| P013 | page_number_candidate | page_numbering | page, position_type, confidence | No | Open PDF page | Open PDF page | Exact highlight coordinates not available; page-number bboxes not currently stored | position_type | Done — page-only |
| P013 | p013_document_overview | page_numbering | None (document-level) | No | Explanation only | Read explanation | Document-level finding; no specific page or location | — | Done — explanation |
| P013 | missing_page_number | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P013 | multiple_page_numbers | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P013 | inconsistent_position | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P013 | mixed_numbering_style | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P013 | sequence_gap | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P019 | page_number_sequence_error | page_numbering | page, observed | No | Open PDF page | Open PDF page | Page-number bbox not stored | — | Done — page-only |
| P021 | abstract_word_count_exceeded | abstract_length | page, **word_count**, **limit**, **inferred_degree_type** | No | Open PDF page + explanation | Open PDF page | No specific span coordinates; abstract is full-page content | word_count, limit, inferred_degree_type | Done — page-only + detailed explanation |
| P022 | frontmatter_page_has_page_number | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P023 | body_spacing_issue | spacing_blank_lines | page | No | Open PDF page | Open PDF page | Spacing is a paragraph-level property, not a single span bbox | — | Done — page-only |
| P026 | possible_body_font_family_issue | font_format | page, confidence | No | Open PDF page | Open PDF page | Per-span bboxes not currently stored in details | — | Done — page-only |
| P026 | possible_body_font_size_issue | font_format | page, confidence | No | Open PDF page | Open PDF page | Per-span bboxes not currently stored in details | — | Done — page-only |
| P027 | (various heading style) | heading_title | page | No | Open PDF page | Open PDF page | Heading bbox not currently stored | — | Done — page-only |
| P028 | frontmatter_page_number_style_issue | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P029 | roman_sequence_gap | page_numbering | page | No | Open PDF page | Open PDF page | Exact highlight not available | — | Done — page-only |
| P030 | missing_continued_heading | list_of_tables_figures_toc | page | No | Open PDF page | Open PDF page | Missing element — nothing to highlight | — | Done — page-only |
| P033 | title_page_mismatch | title_page_metadata | page | No | Open PDF page | Open PDF page | Title comparison is document-level reasoning | — | Done — page-only |
| P034 | copyright_year_mismatch | title_page_metadata | page | No | Open PDF page | Open PDF page | Year/author comparison is document-level | — | Done — page-only |
| P038 | heading_phrase_not_exact | frontmatter_structure | page | No | Open PDF page | Open PDF page | Heading bbox not stored | — | Done — page-only |
| P041 | dedication_text_not_centered | frontmatter_structure | page | No | Open PDF page | Open PDF page | Centering is a layout property, not a span | — | Done — page-only |
| P063 | appendix_letter_sequence_gap | frontmatter_structure | page | No | Open PDF page | Open PDF page | Sequence comparison is structural | — | Done — page-only |
| P064 | references_structural_issue | references_citations | page | No | Open PDF page | Open PDF page | Structural check; no span coordinates | — | Done — page-only |
| P065 | dedication_text_not_centered | frontmatter_structure | page | No | Open PDF page | Open PDF page | Layout property, not a span | — | Done — page-only |
| P078 | abstract_pdf_forbidden_term | abstract_language | page | No | Open PDF page | Open PDF page | Specific word bbox not stored | — | Done — page-only |
| P078 | abstract_pdf_first_person_pronoun | abstract_language | page | No | Open PDF page | Open PDF page | Specific word bbox not stored | — | Done — page-only |

---

## Summary counts

| Category | Count |
|---|---|
| Exact highlight (has bbox/rect) | 1 (P012) |
| Page-only navigation | ~26 (most rules) |
| Document-level explanation only | 1 (P013 document overview) |
| Needs metadata plumbing | 0 (none identified as safe to add without changing detection) |
| Not safely highlightable | 0 (none; all appropriate ones already covered) |

---

## Rules classified as "Needs metadata plumbing" (potential future work)

These rules have coordinate data internally during detection but do not currently
store it in `AuditFinding.details`. Adding bbox exposure would require modifying
detectors but not changing detection semantics.

| rule_id | What the detector knows | Why not done now |
|---|---|---|
| P011 | Per-line violation bboxes (from `PdfTextLine.bbox`) | Conservative; would change the details dict structure; line bboxes require validation |
| P013 | Per-candidate token bboxes (from `fitz` span positions) | Not currently stored; detection is pattern-based not coordinate-based |
| P026 | Per-span bboxes (from `PdfTextSpan`) | Conservative; would change the details dict structure; deferred to a future P rule |

These are deferred — not safe to add in a presentation-layer-only change.

---

## Actionability guarantee (historical — superseded)

The bullets below describe the **2026-06-16** target state after PR #320.
Several labels (`"Open PDF page"`) were later replaced; see **Current policy**
above for the live UI.

After implementing PR #320:

- **Every finding card has a clear action button.** No card is empty.
- **Highlighted findings** (P012) open a highlighted PDF page.
- **Page-known findings** (most rules) open the relevant PDF page and explain why no exact highlight exists.
- **Document-level findings** (P013 overview) show a detailed explanation.
- **All finding cards show a `<details>` explanation** via "What does this mean?".
- **Main result page, grouped problem cards, category pages, and rule pages** all expose the same actionability model.
- **Mobile and desktop** expose the same substantive actions (same data, different layout only).
