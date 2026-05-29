# Phase 2 P020 Title and Heading Capitalization Evaluation

- Date: 2026-05-29
- Rule: P020 — PDF title and heading capitalization

## Purpose

P020 checks whether title-like and heading-like text regions in a compiled PDF
follow NJIT title-case formatting requirements. The goal is to surface obvious
under-capitalization in Level 2 headings and table titles that would be visible
on submission review.

## Guideline Sources Consulted

Both sources are now committed to `data/raw/guidelines/`:

- `Titles Examples Level 1 to 5.docx` — primary source for heading level formatting
- `Thesis and Dissertation Formatting Guidelines (WIP).docx` — secondary source
  confirming table title and TOC capitalization rules

### Key Rules Extracted

| Element | Capitalization Style | Checked by P020 |
|---------|----------------------|:--------------:|
| Chapter titles (Level 1) | ALL CAPS bold centered | No (P014 covers front-matter) |
| Level 2 headings (X.x) | **Title Case** bold centered | **Yes** |
| Level 3 headings (X.x.x) | Sentence case bold | No (sentence case — not checked) |
| Level 4–5 headings | Sentence case, various | No (sentence case — not checked) |
| Table titles | **Title Case**, no period | **Yes** |
| Figure descriptions | Sentence case, with punctuation | No (sentence case) |
| TOC entries (Level 2) | Title Case | Not directly (via table/heading detection) |

Title Case definition (per NJIT guidelines): each word is capitalized *except*
articles (a, an, the), prepositions (at, by, in, of, on, per, to, up, via),
and conjunctions (and, but, or, for, nor, as).

## Scope: Title-Like Text Only

P020 does NOT check normal body paragraph text. Applied only to:

- **Bold heading-like lines**: all extracted font spans carry bold style, line is
  ≤150 characters, not an all-caps front-matter label (ABSTRACT, APPROVAL PAGE, etc.).
- **Table caption title bodies**: extracted by the existing P017 caption detection
  logic (table captions only; figure captions are sentence case and are excluded).

P020 does NOT run on:
- Normal body text (non-bold paragraphs).
- Figure captions (sentence case per NJIT guidelines).
- Level 3–5 headings (sentence case — P020 cannot yet distinguish Level 2 from
  Level 3 purely from typography, so it applies conservatively only to bold lines
  and table titles where title case is unambiguous).
- Pages with REFERENCES, BIBLIOGRAPHY, or WORKS CITED headings.
- Pages with TABLE OF CONTENTS heading.
- All-caps front-matter labels.
- Lines over 150 characters.
- Page-number-like lines.

## Conservative Heuristic Limitations

- Bold detection depends on PDF font metadata. Non-standard or embedded fonts
  may not expose reliable bold flags, causing missed headings.
- Cannot distinguish Level 2 (title case) from Level 3 (sentence case) headings
  without semantic numbering analysis (e.g. 1.1 vs 1.1.1). Conservative: only
  bold lines where title case is the expected default.
- One finding per title-like line (first detected violation). Lines with multiple
  violations generate one P020 warning.
- Over-capitalization (e.g. "The" in the middle) is NOT flagged — P020 only
  catches under-capitalization.
- Hyphenated words are skipped entirely to avoid false positives.
- All-caps words of 2+ uppercase letters are treated as acronyms and preserved.

## Synthetic Test Summary

Tests in `tests/test_pdf_rules.py`:

| Test | Result |
|------|--------|
| Correct title case bold heading | No P020 |
| Lowercase major word in bold heading | P020 warning, major_word_requires_capital |
| Lowercase minor word (and) in middle | No P020 |
| First word lowercase in bold heading | P020 warning, first_word_requires_capital, high confidence |
| Word after colon lowercase | P020 warning, word_after_separator_requires_capital |
| All-caps acronym (PDF) in heading | No P020 |
| All-caps front-matter label (ABSTRACT) | No P020 |
| Non-bold body paragraph | No P020 |
| Bold line on references page | No P020 |
| Table title with lowercase major word | P020 warning, source=caption |
| CLI pdf run with P020 violation | P020 in output, exit_code=0 |

Unit tests for helper functions: minor word detection, acronym detection, correct
phrase, minor word in middle, major word lowercase, first word lowercase, word
after colon/em-dash, acronym mixed with lowercase, math/model token suppression,
hyphenated word conservative behavior, too-short phrase.

## Evaluation on Available Ester PDFs

Counts only — no body text reproduced.

| File | P020 Count | first_word_requires_capital | major_word_requires_capital | caption | heading |
|------|:----------:|:---------------------------:|:---------------------------:|:-------:|:-------:|
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | 0 | — | — | — | — |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | 30 | 7 | 23 | 14 | 16 |
| `250218 Cibaku Elson First Review.pdf` | 0 | — | — | — | — |
| `260415 Yin H _2nd_review with EF Comments.pdf` | 0 | — | — | — | — |

Observations:
- The compressed 4th-review PDF produces 30 findings, split across caption and
  heading sources. The high `major_word_requires_capital` count (23) may indicate
  genuine title-case inconsistencies in table titles or Level 2 headings, or may
  include some false positives from headings that use non-title-case styles.
- Three other PDFs produce 0 findings, suggesting either correct title case or
  insufficient bold-font metadata in the extracted text layer.
- Manual review of any P020 findings is required before acting on them.

## Privacy Note

- No dissertation body text is included in this document or in test fixtures.
- All test content uses synthetic PDF content.
