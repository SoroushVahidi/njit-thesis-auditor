# P065 Current-Dataset Evaluation — Dedication Page Centering and Italic Style

**Date:** 2026-06-08  
**Baseline commit:** `414a774` (PR #232 — P065 implemented)  
**Validation status:** ruff clean, mypy clean, 925 pytest passed  
**Rule:** P065 — Dedication Page Centering/Italic Formatting Check  
**Issue types:** `dedication_text_not_centered`, `dedication_text_not_italic`  
**Source Q-rules:** Q033 (centering), Q034 (italic)  
**Module:** `src/njit_auditor/rules/pdf_dedication_centering_italic.py`

---

## Evaluated Files

| File label | Pages | Accessible | Source |
|---|---|---|---|
| Cibaku Elson 1st Review | 99 | Yes | tracked PDF |
| Yin H 2nd Review (flattened) | 108 | Yes | tracked PDF |
| Yin Haotian 2nd Review | 108 | Yes | tracked PDF |
| Yin H 4th Review (compressed) | 137 | Yes | tracked PDF |
| Sebastian Fine clean baseline | 29 | Yes | extracted from tracked ZIP |

All five evaluation PDFs were accessible. Sebastian Fine was extracted from
`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`
into `data/evaluation/generated/p065_evaluation/sebastian_fine_clean.pdf`
(gitignored; not committed).

---

## P065 Findings by File

| File label | Dedication detected | Centering check | Italic check | P065 findings |
|---|---|---|---|---|
| Cibaku Elson 1st Review | None | Skipped | Skipped | 0 |
| Yin H 2nd Review (flattened) | None | Skipped | Skipped | 0 |
| Yin Haotian 2nd Review | None | Skipped | Skipped | 0 |
| Yin H 4th Review (compressed) | None | Skipped | Skipped | 0 |
| Sebastian Fine clean baseline | None | Skipped | Skipped | 0 |

**Total P065 findings: 0**

---

## Issue Type Breakdown

| Issue type | Count |
|---|---|
| `dedication_text_not_centered` | 0 |
| `dedication_text_not_italic` | 0 |

---

## Dedication-Page Detection Analysis

P065 uses `_find_dedication_page_unique()`, which scans the first
`_MAX_SCAN_PAGES = 15` pages for a single page containing exactly one text
line that normalizes to the string `"DEDICATION"` (case-insensitive, using
`normalize_heading_text()`). If 0 or 2+ such pages are found, P065 returns
no findings.

**Cibaku Elson, Yin H 2nd (flat), Yin Haotian 2nd, Yin H 4th (compressed):**
No text line containing "DEDICATION" was found in the first 15 pages of
any of these four PDFs. The dedication page — if present — is either
image-rendered (no text layer), located beyond page 15, or absent.

**Sebastian Fine clean baseline:**
One occurrence of the substring "DEDICATION" was found on page 8, but the
containing line is 82 characters long and is body prose — the word appears
within a running sentence, not as a standalone page heading. After
`normalize_heading_text()` normalization, the line does not equal
`"DEDICATION"`, so no unique DEDICATION heading was detected and P065
correctly skipped.

P041 (`pdf_dedication_page.py`) was also queried for all five PDFs and
returned no dedication page match on any file, confirming the detection
limitation is shared across both dedication-related rules on this dataset.

---

## Interpretation

**Zero findings do not indicate compliance.** All five evaluation PDFs
skipped P065 because no machine-readable standalone DEDICATION heading was
detected in the first 15 pages. The rule's gate condition was not met for
any file; no centering or italic analysis was performed.

Possible explanations for the detection failure:

1. **Image-only dedication page.** Dedication pages are commonly scanned or
   image-rendered in submitted PDFs. If the "DEDICATION" heading is part of
   an image rather than the text layer, PyMuPDF returns no matching text span
   and the gate fails.

2. **Absent dedication section.** Some dissertations in this dataset may
   genuinely not have a Dedication section (it is optional under NJIT
   guidelines).

3. **Heading variant or formatting.** If the heading uses a phrase other than
   the exact word "DEDICATION" (e.g., "DEDICATION PAGE", or mixed-case not
   normalized by the current logic), the gate fails.

4. **Heading beyond page 15.** Unlikely given standard front-matter structure,
   but cannot be excluded for atypical layouts.

**Result:** P065 does not produce actionable findings on this dataset at the
current detection threshold. Coverage will improve on future PDFs where the
dedication page has a machine-readable text layer.

---

## Generated Output Path

```
data/evaluation/generated/p065_evaluation/
```

Contents (gitignored, not committed):
- `sebastian_fine_clean.pdf` — extracted from tracked ZIP for evaluation

The `.gitignore` entry `data/evaluation/generated/` covers this directory.
No generated JSON, Markdown, or extracted PDF files are committed.

---

## Privacy Model

- No dedication text, body prose, author names, committee names, title text,
  EF comment text, DOI strings, or URLs from any evaluated file are quoted
  in this document.
- The one "DEDICATION" occurrence in Sebastian Fine is described by its
  character count and structural role only.
- All reported values are counts, page numbers, and detection-gate statuses.
- Real dissertation files were not modified.
- No OCR was performed. No external network calls were made.

---

## Limitations

- P065 requires a machine-readable DEDICATION heading in the text layer of
  the first 15 pages. Image-only pages are invisible to the rule.
- None of the five evaluation PDFs provided a detectable heading, so the
  rule's centering and italic logic was never exercised on real data.
- The `_MIN_TEXT_LINES = 2` (centering) and `_MIN_SPANS = 3` (italic) gates
  are untested against real dedication content on this dataset.
- Synthetic test coverage (15/15 passing) validates gate logic but cannot
  substitute for real-dataset exercise.

---

## Companion Rule

P041 (`pdf_dedication_page.py`) covers Q032 (no header in the top margin of
the Dedication page) and uses the same heading-detection pattern as P065.
P041 also found no dedication pages on this dataset, confirming that the
limitation is at the detection layer, not at the centering/italic logic.
